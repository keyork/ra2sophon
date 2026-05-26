"""Memory reader for RA2:YR using pymem.

Attaches to gamemd.exe and reads game state from known memory offsets.
Uses runtime counter discovery + unitdefs.py for type identification.

Counter architecture (from YRpp HouseClass.h + ra2ob):
    HouseClass contains CounterClass instances for tracking owned objects.
    CounterClass layout: +0x00=vtable(0x7E5C54), +0x04=items_ptr,
                         +0x08=count, +0x0C=flags(0x101), +0x10=total
    items_ptr -> int[] where items[i] = count of type with ArrayIndex i

    The exact position of each counter within HouseClass may shift with
    Ares/Phobos. We auto-discover the mapping at runtime by matching
    item patterns against known TypeClass name arrays from the game itself.
"""

from __future__ import annotations

import logging
import struct
from typing import Optional

from pymem import Pymem
from pymem.exception import ProcessNotFound, CouldNotOpenProcess

from .offsets import (
    ALIVE_BUILDING_COUNTER,
    ALIVE_VEHICLE_COUNTER,
    ALIVE_INFANTRY_COUNTER,
    ALIVE_AIRCRAFT_COUNTER,
    BUILDING_HEAP_CHUNK_SIZE,
    BUILDING_HEAP_SCAN_RANGES,
    CTR_ITEMS,
    CTR_COUNT,
    CTR_TOTAL,
    DVEC_COUNT,
    DVEC_ITEMS,
    HOUSE_ARRAY_PTR,
    HOUSE_ARRAY_INDEX,
    HOUSE_COUNTER_VTABLE,
    HOUSE_CREDITS_CURRENT,
    HOUSE_CREDITS_SPENT,
    HOUSE_POWER_DRAINED,
    HOUSE_POWER_PRODUCED,
    HOUSE_TYPE_PTR,
    HT_COUNTRY_NAME,
    INFANTRY_TYPE_ARRAY,
    UNIT_TYPE_ARRAY,
    AIRCRAFT_TYPE_ARRAY,
    ISDEFEATEDOFFSET,
    OBSERVER_MODE,
    OBSERVER_PTR,
    PLAYER_PTR,
    PROCESS_NAMES,
    TYPE_NAME_OFFSET,
    VTABLE_BUILDING_TYPE,
)
from .types import TypeCount, CounterInfo, HouseInfo, GameState
from .unitdefs import UnitDef, VEHICLE_BY_OFFSET, BUILDING_BY_OFFSET, INFANTRY_BY_OFFSET, AIRCRAFT_BY_OFFSET

logger = logging.getLogger(__name__)

# ── Memory layout constants ──────────────────────────────────────────────────
INT32_SIZE = 4
MIN_VALID_PTR = 0x10000          # Pointers below this are invalid/null
MAX_TYPE_NAME_LEN = 24           # Max bytes for a type name string
MAX_DVC_POINTER_COUNT = 1000     # Sanity limit for DVC pointer array
MAX_TYPE_ARRAY_COUNT = 500       # Sanity limit for type name array
UNIT_COUNT_MAX = 4096            # Max per-type unit count (sanity)


class GameReader:
    """Reads game state from a running RA2:YR process."""

    def __init__(self) -> None:
        self._pm: Optional[Pymem] = None
        self._base_addr: int = 0
        self._type_names: dict[int, list[str]] = {}
        self._building_names: Optional[list[str]] = None

    def attach(self) -> bool:
        for name in PROCESS_NAMES:
            try:
                pm = Pymem(name)
                self._pm = pm
                self._base_addr = pm.process_base.lpBaseOfDll
                logger.info("Attached to %s (PID=%d)", name, pm.process_id)
                return True
            except ProcessNotFound:
                continue
            except CouldNotOpenProcess:
                logger.warning("Found %s but cannot open (need admin).", name)
                return False
            except Exception as e:
                logger.warning("Failed to attach to %s: %s", name, e)
                continue
        logger.error("No game process found.")
        return False

    def detach(self) -> None:
        if self._pm:
            self._pm.close_process()
            self._pm = None

    @property
    def is_attached(self) -> bool:
        return self._pm is not None

    # ── Low-level reads ───────────────────────────────────────────────────────

    def read_int(self, address: int) -> Optional[int]:
        try:
            return self._pm.read_int(address)
        except Exception:
            return None

    def read_uint(self, address: int) -> Optional[int]:
        try:
            return self._pm.read_uint(address)
        except Exception:
            return None

    def read_pointer(self, address: int) -> int:
        try:
            return self._pm.read_uint(address)
        except Exception:
            return 0

    def read_bytes(self, address: int, size: int) -> bytes:
        return self._pm.read_bytes(address, size)

    def write_int(self, address: int, value: int) -> bool:
        """Write an int32 value to game memory. Returns True on success."""
        try:
            self._pm.write_int(address, value)
            return True
        except Exception:
            return False

    def read_string(self, address: int, max_len: int = 64) -> str:
        data = self.read_bytes(address, max_len)
        null_pos = data.find(b"\x00")
        if null_pos >= 0:
            data = data[:null_pos]
        return data.decode("ascii", errors="replace")

    def _read_cstring(self, address: int, max_len: int = MAX_TYPE_NAME_LEN) -> str:
        """Read a null-terminated ASCII string from game memory."""
        raw = self.read_bytes(address, max_len)
        null_pos = raw.find(b"\x00")
        if null_pos >= 0:
            raw = raw[:null_pos]
        return raw.decode("ascii", errors="replace")

    # ── DynamicVectorClass helper ─────────────────────────────────────────────

    def read_dvec_pointers(self, dvec_address: int) -> list[int]:
        count = self.read_int(dvec_address + DVEC_COUNT)
        items_ptr = self.read_pointer(dvec_address + DVEC_ITEMS)
        if not count or count <= 0 or count > MAX_DVC_POINTER_COUNT or items_ptr < MIN_VALID_PTR:
            return []
        pointers = []
        for i in range(count):
            ptr = self.read_pointer(items_ptr + i * INT32_SIZE)
            if ptr and ptr >= MIN_VALID_PTR:
                pointers.append(ptr)
        return pointers

    # ── Type name reading ─────────────────────────────────────────────────────

    def _get_type_names(self, dvec_addr: int) -> list[str]:
        """Read type name strings from a TypeClass DVC array."""
        if dvec_addr in self._type_names:
            return self._type_names[dvec_addr]
        items_ptr = self.read_pointer(dvec_addr + DVEC_ITEMS)
        count = self.read_int(dvec_addr + DVEC_COUNT)
        if not items_ptr or not count or count <= 0 or count > MAX_TYPE_ARRAY_COUNT:
            return []
        names = []
        for i in range(count):
            tp = self.read_pointer(items_ptr + i * INT32_SIZE)
            if not tp or tp < MIN_VALID_PTR:
                names.append("?")
                continue
            try:
                name = self._read_cstring(tp + TYPE_NAME_OFFSET)
                names.append(name if name else "?")
            except Exception:
                names.append("?")
        self._type_names[dvec_addr] = names
        return names

    def _get_building_names(self) -> list[str]:
        """Discover building type names via heap scan for vtable signature."""
        if self._building_names is not None:
            return self._building_names
        vtable_bytes = struct.pack("<I", VTABLE_BUILDING_TYPE)
        found: list[tuple[int, str]] = []
        for start, end in BUILDING_HEAP_SCAN_RANGES:
            addr = start
            while addr < end:
                try:
                    chunk = self.read_bytes(addr, BUILDING_HEAP_CHUNK_SIZE)
                except Exception:
                    addr += BUILDING_HEAP_CHUNK_SIZE
                    continue
                pos = 0
                while True:
                    idx = chunk.find(vtable_bytes, pos)
                    if idx < 0:
                        break
                    obj_addr = addr + idx
                    try:
                        name = self._read_cstring(obj_addr + TYPE_NAME_OFFSET)
                        if name and len(name) >= 2 and all(
                            c.isalnum() or c == "_" for c in name
                        ):
                            found.append((obj_addr, name))
                    except Exception:
                        pass
                    pos = idx + INT32_SIZE
                addr += BUILDING_HEAP_CHUNK_SIZE
        found.sort(key=lambda x: x[0])
        names = [name for _, name in found]
        self._building_names = names
        logger.info("Found %d BuildingTypeClass objects via heap scan", len(names))
        return names

    # ── Counter discovery ─────────────────────────────────────────────────────

    def _scan_counter_at(self, house_addr: int, offset: int) -> Optional[CounterInfo]:
        """Read a single CounterClass at a given HouseClass offset."""
        vtable = self.read_pointer(house_addr + offset)
        if vtable != HOUSE_COUNTER_VTABLE:
            return None
        items_ptr = self.read_pointer(house_addr + offset + CTR_ITEMS)
        count = self.read_int(house_addr + offset + CTR_COUNT)
        total = self.read_int(house_addr + offset + CTR_TOTAL)
        if not items_ptr or items_ptr < MIN_VALID_PTR or not count or count <= 0 or count > MAX_TYPE_ARRAY_COUNT:
            return None
        return CounterInfo(offset=offset, items_ptr=items_ptr,
                          count=count, total=total or 0)

    # ── Game state reads ──────────────────────────────────────────────────────

    def read_game_state(self) -> GameState:
        """Read a full game state snapshot with per-type breakdowns."""
        state = GameState()

        state.player_ptr = self.read_pointer(PLAYER_PTR)
        obs_val = self.read_int(OBSERVER_MODE)
        state.observer_mode = bool(obs_val) if obs_val is not None else False

        house_ptrs = self.read_dvec_pointers(HOUSE_ARRAY_PTR)
        obs_ptr = self.read_pointer(OBSERVER_PTR)

        for ptr in house_ptrs:
            house = self._read_house(ptr, state.player_ptr, obs_ptr)
            state.houses.append(house)

        return state

    def _read_house(self, ptr: int, player_ptr: int, obs_ptr: int) -> HouseInfo:
        """Read a single HouseClass with per-type breakdowns."""
        arr_idx = self.read_int(ptr + HOUSE_ARRAY_INDEX)
        credits = self.read_int(ptr + HOUSE_CREDITS_CURRENT)
        spent = self.read_int(ptr + HOUSE_CREDITS_SPENT)
        power = self.read_int(ptr + HOUSE_POWER_PRODUCED)
        drain = self.read_int(ptr + HOUSE_POWER_DRAINED)

        ht_name = ""
        ht_ptr = self.read_pointer(ptr + HOUSE_TYPE_PTR)
        if ht_ptr and ht_ptr >= MIN_VALID_PTR:
            try:
                ht_name = self._read_cstring(ht_ptr + HT_COUNTRY_NAME)
            except Exception:
                pass

        is_defeated = False
        defeated_val = self.read_int(ptr + ISDEFEATEDOFFSET)
        if defeated_val is not None and defeated_val != 0:
            is_defeated = True

        house = HouseInfo(
            address=ptr,
            array_index=arr_idx if arr_idx is not None else -1,
            is_current_player=(ptr == player_ptr),
            is_observer=(ptr == obs_ptr and obs_ptr != 0),
            credits=credits,
            credits_spent=spent,
            power_produced=power,
            power_drained=drain,
            house_type_name=ht_name,
            is_defeated=is_defeated,
        )

        # Read 4 alive counters using ra2ob offsets
        for category, counter_offset, type_dvc, unitdef_lookup in [
            ("building", ALIVE_BUILDING_COUNTER, 0,                   BUILDING_BY_OFFSET),
            ("vehicle",  ALIVE_VEHICLE_COUNTER,  UNIT_TYPE_ARRAY,     VEHICLE_BY_OFFSET),
            ("infantry", ALIVE_INFANTRY_COUNTER, INFANTRY_TYPE_ARRAY, INFANTRY_BY_OFFSET),
            ("aircraft", ALIVE_AIRCRAFT_COUNTER, AIRCRAFT_TYPE_ARRAY, AIRCRAFT_BY_OFFSET),
        ]:
            ci = self._scan_counter_at(ptr, counter_offset)
            if ci is None:
                continue

            # Get type names from game's own DVC arrays
            if type_dvc and type_dvc != 0:
                names = self._get_type_names(type_dvc)
            elif category == "building":
                names = self._get_building_names()
            else:
                names = []

            items = self._read_counter_items(ci, names, unitdef_lookup, category)

            if category == "building":
                house.buildings = items
                house.building_total = sum(tc.count for tc in items)
            elif category == "infantry":
                house.infantry = items
                house.infantry_total = sum(tc.count for tc in items)
            elif category == "vehicle":
                house.naval = [tc for tc in items if tc.is_naval]
                house.vehicles = [tc for tc in items if not tc.is_naval]
                house.naval_total = sum(tc.count for tc in house.naval)
                house.vehicle_total = sum(tc.count for tc in house.vehicles)
            elif category == "aircraft":
                house.aircraft = items
                house.aircraft_total = sum(tc.count for tc in items)

        return house

    def _read_counter_items(
        self,
        ci: CounterInfo,
        type_names: list[str],
        unitdef_lookup: Optional[dict[int, UnitDef]],
        category: str,
    ) -> list[TypeCount]:
        """Read per-type counts from a counter and pair with names."""
        result = []
        for i in range(ci.count):
            val = self.read_int(ci.items_ptr + i * INT32_SIZE)
            if val is None or val <= 0 or val > UNIT_COUNT_MAX:
                continue

            name = type_names[i] if i < len(type_names) and type_names[i] != "?" else f"#{i}"
            name_cn = ""
            faction = ""
            is_naval = False

            # Enhance with unitdef if available (byte offset = index * INT32_SIZE)
            if unitdef_lookup:
                byte_off = i * INT32_SIZE
                udef = unitdef_lookup.get(byte_off)
                if udef:
                    name = udef.name
                    name_cn = udef.name_cn
                    faction = udef.faction
                    is_naval = udef.is_naval

            result.append(TypeCount(
                index=i, name=name, name_cn=name_cn,
                count=val, category=category, faction=faction,
                is_naval=is_naval,
            ))
        return result

    def set_credits(self, amount: int, player_only: bool = True) -> int:
        """Add credits to current player (or all players). Returns count modified."""
        state = self.read_game_state()
        houses = [h for h in state.houses if h.is_current_player] if player_only else state.active_houses
        count = 0
        for house in houses:
            current = house.credits or 0
            new_val = current + amount
            if self.write_int(house.address + HOUSE_CREDITS_CURRENT, new_val):
                count += 1
                logger.info("Set %s credits: $%d + $%d = $%d",
                            house.house_type_name, current, amount, new_val)
        return count

    def get_process_info(self) -> dict:
        if not self._pm:
            return {}
        return {
            "pid": self._pm.process_id,
            "base_addr": hex(self._base_addr),
            "process_name": self._pm.process_name,
        }
