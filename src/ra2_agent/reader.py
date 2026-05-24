"""Memory reader for RA2: Yuri's Revenge using pymem.

Attaches to gamemd.exe and reads game state from known memory offsets.
Auto-discovers counter-to-category mapping at runtime.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass, field
from typing import Optional

from pymem import Pymem
from pymem.exception import ProcessNotFound, CouldNotOpenProcess

from .offsets import (
    BUILDING_HEAP_CHUNK_SIZE,
    BUILDING_HEAP_SCAN_RANGES,
    COUNTER_BUILDINGS,
    COUNTER_BUILDINGS_ALT,
    COUNTER_BUILDINGS_ALT2,
    COUNTER_CLASS_SIZE,
    COUNTER_MAX_COUNT,
    COUNTER_UNITS_A,
    COUNTER_UNITS_A_ALT,
    COUNTER_UNITS_A_ALT2,
    COUNTER_UNITS_B,
    COUNTER_UNITS_B_ALT,
    CTR_COUNT,
    CTR_ITEMS,
    CTR_TOTAL,
    DVEC_COUNT,
    DVEC_ITEMS,
    HOUSE_ARRAY_PTR,
    HOUSE_ARRAY_INDEX,
    HOUSE_COUNTERS_BASE,
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
    OBSERVER_MODE,
    OBSERVER_PTR,
    PLAYER_PTR,
    PROCESS_NAMES,
    TYPE_NAME_OFFSET,
    VTABLE_BUILDING_TYPE,
)

# Counter-to-category mapping (offset, category_name, type_dvec_address)
COUNTER_CATEGORIES = [
    (COUNTER_BUILDINGS, "buildings", 0),
    (COUNTER_UNITS_A, "units_a", UNIT_TYPE_ARRAY),
    (COUNTER_BUILDINGS_ALT, "buildings_alt", 0),
    (COUNTER_UNITS_B, "units_b", UNIT_TYPE_ARRAY),
    (COUNTER_UNITS_A_ALT, "units_a_alt", UNIT_TYPE_ARRAY),
    (COUNTER_BUILDINGS_ALT2, "buildings_alt2", 0),
    (COUNTER_UNITS_B_ALT, "units_b_alt", UNIT_TYPE_ARRAY),
    (COUNTER_UNITS_A_ALT2, "units_a_alt2", UNIT_TYPE_ARRAY),
]

logger = logging.getLogger(__name__)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class TypeCount:
    """Count of a specific type (building, infantry, unit, aircraft)."""
    index: int
    name: str
    count: int


@dataclass
class CounterInfo:
    """Discovered counter structure."""
    offset: int        # Base offset in HouseClass
    items_ptr: int     # Pointer to int[] of per-type counts
    count: int         # Number of items in counter array
    total: int         # Sum of all items
    category: str = "" # Discovered category name
    type_dvec: int = 0 # Matching type array DVC address


@dataclass
class HouseInfo:
    """Full info about a single HouseClass (player/AI)."""
    address: int
    array_index: int = -1
    is_current_player: bool = False
    is_observer: bool = False
    credits: Optional[int] = None
    credits_spent: Optional[int] = None
    power_produced: Optional[int] = None
    power_drained: Optional[int] = None
    # Per-type breakdowns (populated by counter discovery)
    buildings: list[TypeCount] = field(default_factory=list)
    infantry: list[TypeCount] = field(default_factory=list)
    vehicles: list[TypeCount] = field(default_factory=list)
    aircraft: list[TypeCount] = field(default_factory=list)
    # Totals
    building_total: int = 0
    infantry_total: int = 0
    vehicle_total: int = 0
    aircraft_total: int = 0
    # HouseType identity
    house_type_name: str = ""

    @property
    def power_surplus(self) -> int:
        return (self.power_produced or 0) - (self.power_drained or 0)

    @property
    def is_active(self) -> bool:
        """True if this house represents an active player."""
        if self.is_observer:
            return False
        if self.credits is not None and self.credits < 0:
            return False
        # Reject garbage data
        if self.credits is not None and self.credits > 1_000_000:
            return False
        if self.building_total > 10000 or self.infantry_total > 10000:
            return False
        if self.vehicle_total > 10000 or self.aircraft_total > 10000:
            return False
        # Reject "Neutral" / non-player houses (0 credits = not a real player)
        has_money = self.credits is not None and self.credits > 0
        if not has_money:
            return False
        return True


@dataclass
class GameState:
    """Snapshot of the current game state."""
    player_ptr: int = 0
    observer_mode: bool = False
    houses: list[HouseInfo] = field(default_factory=list)

    @property
    def active_houses(self) -> list[HouseInfo]:
        return [h for h in self.houses if h.is_active]

    @property
    def current_player(self) -> Optional[HouseInfo]:
        for h in self.houses:
            if h.is_current_player:
                return h
        return None


# ── Type Registry ─────────────────────────────────────────────────────────────

class TypeRegistry:
    """Caches type name arrays and discovers counter-to-category mapping."""

    def __init__(self, reader: "GameReader") -> None:
        self._reader = reader
        self._names: dict[int, list[str]] = {}
        self._building_type_array: Optional[int] = None
        self._counter_map: dict[str, CounterInfo] = {}
        self._counters_discovered = False

    def get_names(self, dvec_addr: int) -> list[str]:
        if dvec_addr in self._names:
            return self._names[dvec_addr]
        names = self._read_type_names(dvec_addr)
        self._names[dvec_addr] = names
        return names

    def get_building_names(self) -> list[str]:
        """Get building type names. Discovers via heap scan on first call."""
        if self._building_type_array is not None:
            return self.get_names(self._building_type_array)
        names = self._discover_building_names_via_heap()
        return names

    def _discover_building_names_via_heap(self) -> list[str]:
        """Scan process heap for BuildingTypeClass objects (vtable 0x7E4570).
        Build an index→name mapping by reading each object's name at +0x24.
        Returns a list where list[index] = building name."""
        import struct as _struct
        reader = self._reader
        target_vtable = VTABLE_BUILDING_TYPE
        vtable_bytes = _struct.pack("<I", target_vtable)

        # Known heap regions for RA2 TypeClass objects (from offsets)
        scan_ranges = BUILDING_HEAP_SCAN_RANGES
        chunk_size = BUILDING_HEAP_CHUNK_SIZE

        found_objects: list[tuple[int, str]] = []  # (address, name)

        for start, end in scan_ranges:
            addr = start
            while addr < end:
                try:
                    chunk = reader.read_bytes(addr, chunk_size)
                except Exception:
                    addr += chunk_size
                    continue

                # Search for vtable pattern in chunk
                pos = 0
                while True:
                    idx = chunk.find(vtable_bytes, pos)
                    if idx < 0:
                        break
                    obj_addr = addr + idx
                    # Read name at +0x24
                    try:
                        name_raw = reader.read_bytes(obj_addr + TYPE_NAME_OFFSET, 24)
                        np = name_raw.find(b"\x00")
                        if np >= 0:
                            name_raw = name_raw[:np]
                        name = name_raw.decode("ascii", errors="replace")
                        # Validate: must be alphanumeric with underscores, 2+ chars
                        if name and len(name) >= 2 and all(c.isalnum() or c == '_' for c in name):
                            found_objects.append((obj_addr, name))
                    except Exception:
                        pass
                    pos = idx + 4

                addr += chunk_size

        if not found_objects:
            logger.warning("No BuildingTypeClass objects found on heap")
            return []

        # Sort by address (heap allocation order ≈ type registration order)
        found_objects.sort(key=lambda x: x[0])

        # Build name list indexed by position
        names = [name for _, name in found_objects]
        logger.info("Found %d BuildingTypeClass objects via heap scan", len(names))

        # Also try to find the actual DVC by checking if addresses form a pointer array
        # For now, cache as a virtual DVC at address 0 (special case)
        self._building_type_array = 0  # marker: heap-scanned
        self._names[0] = names
        return names

    def discover_counters(self, house_addr: int) -> None:
        """Discover counter-to-category mapping.
        
        Uses a hybrid strategy:
        1. InfantryType matching (verified: 0x5500 items match InfantryType names)
        2. Structural pattern (8 counters in known order)
        
        Counter layout (verified 2025-05-24):
          0x5500: Infantry (primary)
          0x5528: Vehicles type A (subset 1)
          0x5550: Infantry (alt)
          0x5564: Vehicles type B (subset 2)
          0x5578: Vehicles A (alt)
          0x55A0: Infantry (alt 2)
          0x55B4: Vehicles B (alt)
          0x55C8: Vehicles A (alt 2)
          
        Buildings and Aircraft counters are in a DIFFERENT location (not found yet).
        """
        if self._counters_discovered:
            return

        reader = self._reader
        counters = self._scan_counters(house_addr)
        if not counters:
            return

        # Category mapping from named constants (verified 2025-05-24)
        for ci in counters:
            for offset_val, cat, dvec in COUNTER_CATEGORIES:
                if ci.offset == offset_val:
                    ci.category = cat
                    ci.type_dvec = dvec
                    self._counter_map[cat] = ci
                    logger.info("Counter +0x%04X -> %s", ci.offset, cat)
                    break

        # Map primary counters for the house info
        # infantry = primary infantry counter
        # vehicles = vehicles_a + vehicles_b combined
        # buildings = not yet available
        # aircraft = not yet available
        self._counters_discovered = True

    def get_counter(self, category: str) -> Optional[CounterInfo]:
        return self._counter_map.get(category)

    def _scan_counters(self, house_addr: int) -> list[CounterInfo]:
        """Scan HouseClass for valid CounterClass structures."""
        reader = self._reader
        counters = []
        for i in range(COUNTER_MAX_COUNT):
            offset = HOUSE_COUNTERS_BASE + i * COUNTER_CLASS_SIZE
            vtable = reader.read_pointer(house_addr + offset)
            if vtable != HOUSE_COUNTER_VTABLE:
                continue
            items_ptr = reader.read_pointer(house_addr + offset + CTR_ITEMS)
            count = reader.read_int(house_addr + offset + CTR_COUNT)
            total = reader.read_int(house_addr + offset + CTR_TOTAL)
            if items_ptr and items_ptr >= 0x10000 and count is not None and 0 < count < 300:
                counters.append(CounterInfo(
                    offset=offset,
                    items_ptr=items_ptr,
                    count=count,
                    total=total or 0,
                ))
        return counters

    def _read_type_names(self, dvec_addr: int) -> list[str]:
        reader = self._reader
        items_ptr = reader.read_pointer(dvec_addr + DVEC_ITEMS)
        count = reader.read_int(dvec_addr + DVEC_COUNT)
        if not items_ptr or not count or count <= 0 or count > 500:
            return []
        names = []
        for i in range(count):
            tp = reader.read_pointer(items_ptr + i * 4)
            if not tp or tp < 0x10000:
                names.append("?")
                continue
            try:
                raw = reader.read_bytes(tp + TYPE_NAME_OFFSET, 24)
                null_pos = raw.find(b"\x00")
                if null_pos >= 0:
                    raw = raw[:null_pos]
                name = raw.decode("ascii", errors="replace")
                names.append(name if name else "?")
            except Exception:
                names.append("?")
        return names

    def _discover_building_type_array(self) -> Optional[int]:
        """Find BuildingTypeClass DVC: direct in static, then indirect ptr."""
        reader = self._reader
        target_vtable = VTABLE_BUILDING_TYPE
        # Phase 1: Direct DVC in static data
        for addr in range(0xA83C00, 0xA90000, 4):
            items_ptr = reader.read_pointer(addr + DVEC_ITEMS)
            count = reader.read_int(addr + DVEC_COUNT)
            if not items_ptr or items_ptr < 0x10000:
                continue
            if not count or count <= 0 or count > 200:
                continue
            first_obj = reader.read_pointer(items_ptr)
            if first_obj < 0x10000:
                continue
            vt = reader.read_pointer(first_obj)
            if vt == target_vtable:
                logger.info("Found BuildingTypeClass DVC at 0x%X", addr)
                return addr
        # Phase 2: Indirect pointer -> heap DVC (wider range)
        for addr in range(0xA80000, 0xB00000, 4):
            ptr = reader.read_pointer(addr)
            if not ptr or ptr < 0x10000:
                continue
            items_ptr = reader.read_pointer(ptr + DVEC_ITEMS)
            count = reader.read_int(ptr + DVEC_COUNT)
            if not items_ptr or items_ptr < 0x10000:
                continue
            if not count or count <= 0 or count > 200:
                continue
            first_obj = reader.read_pointer(items_ptr)
            if first_obj < 0x10000:
                continue
            vt = reader.read_pointer(first_obj)
            if vt == target_vtable:
                logger.info("Found BuildingTypeClass DVC via ptr at 0x%X", addr)
                return ptr
        return None


# ── Game Reader ───────────────────────────────────────────────────────────────

class GameReader:
    """Reads game state from a running RA2:YR process."""

    def __init__(self) -> None:
        self._pm: Optional[Pymem] = None
        self._base_addr: int = 0
        self._type_registry: Optional[TypeRegistry] = None

    def attach(self) -> bool:
        for name in PROCESS_NAMES:
            try:
                pm = Pymem(name)
                self._pm = pm
                self._base_addr = pm.process_base.lpBaseOfDll
                self._type_registry = TypeRegistry(self)
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
            self._type_registry = None

    @property
    def is_attached(self) -> bool:
        return self._pm is not None

    @property
    def type_registry(self) -> Optional[TypeRegistry]:
        return self._type_registry

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

    def read_string(self, address: int, max_len: int = 64) -> str:
        data = self.read_bytes(address, max_len)
        null_pos = data.find(b"\x00")
        if null_pos >= 0:
            data = data[:null_pos]
        return data.decode("ascii", errors="replace")

    # ── DynamicVectorClass helper ─────────────────────────────────────────────

    def read_dvec_pointers(self, dvec_address: int) -> list[int]:
        count = self.read_int(dvec_address + DVEC_COUNT)
        items_ptr = self.read_pointer(dvec_address + DVEC_ITEMS)
        if not count or count <= 0 or count > 1000 or items_ptr < 0x10000:
            return []
        pointers = []
        for i in range(count):
            ptr = self.read_pointer(items_ptr + i * 4)
            if ptr and ptr >= 0x10000:
                pointers.append(ptr)
        return pointers

    # ── Game state reads ──────────────────────────────────────────────────────

    def read_game_state(self) -> GameState:
        """Read a full game state snapshot with per-type breakdowns."""
        state = GameState()
        tr = self._type_registry
        if not tr:
            return state

        state.player_ptr = self.read_pointer(PLAYER_PTR)
        obs_val = self.read_int(OBSERVER_MODE)
        state.observer_mode = bool(obs_val) if obs_val is not None else False

        house_ptrs = self.read_dvec_pointers(HOUSE_ARRAY_PTR)
        obs_ptr = self.read_pointer(OBSERVER_PTR)

        # Use first house to discover counter mapping
        if house_ptrs and not tr._counters_discovered:
            tr.discover_counters(house_ptrs[0])

        for ptr in house_ptrs:
            house = self._read_house(ptr, state.player_ptr, obs_ptr, tr)
            state.houses.append(house)

        return state

    def _read_house(
        self, ptr: int, player_ptr: int, obs_ptr: int, tr: TypeRegistry
    ) -> HouseInfo:
        """Read a single HouseClass with per-type breakdowns."""
        arr_idx = self.read_int(ptr + HOUSE_ARRAY_INDEX)
        credits = self.read_int(ptr + HOUSE_CREDITS_CURRENT)
        spent = self.read_int(ptr + HOUSE_CREDITS_SPENT)
        power = self.read_int(ptr + HOUSE_POWER_PRODUCED)
        drain = self.read_int(ptr + HOUSE_POWER_DRAINED)

        # HouseType name
        ht_name = ""
        ht_ptr = self.read_pointer(ptr + HOUSE_TYPE_PTR)
        if ht_ptr and ht_ptr >= 0x10000:
            try:
                raw = self.read_bytes(ht_ptr + HT_COUNTRY_NAME, 24)
                null_pos = raw.find(b"\x00")
                if null_pos >= 0:
                    raw = raw[:null_pos]
                ht_name = raw.decode("ascii", errors="replace")
            except Exception:
                pass

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
        )

        # Per-type breakdowns using discovered counters
        counters = tr._scan_counters(ptr)
        counter_map = {ci.offset: ci for ci in counters}
        
        # Buildings: counter COUNTER_BUILDINGS, names via heap scan
        bld_ci = counter_map.get(COUNTER_BUILDINGS)
        if bld_ci:
            house.building_total = bld_ci.total
            bld_names = tr.get_building_names()
            for j in range(bld_ci.count):
                v = self.read_int(bld_ci.items_ptr + j * 4)
                if v and v > 0:
                    name = bld_names[j] if j < len(bld_names) else f"Bldg#{j}"
                    house.buildings.append(TypeCount(index=j, name=name, count=v))
        
        # Units: counters COUNTER_UNITS_A + COUNTER_UNITS_B, names from UnitType array
        unit_a_ci = counter_map.get(COUNTER_UNITS_A)
        unit_b_ci = counter_map.get(COUNTER_UNITS_B)
        unit_names = tr.get_names(UNIT_TYPE_ARRAY)
        
        seen_names: dict[str, TypeCount] = {}
        for uci in (unit_a_ci, unit_b_ci):
            if uci:
                for j in range(uci.count):
                    v = self.read_int(uci.items_ptr + j * 4)
                    if v and v > 0:
                        name = unit_names[j] if j < len(unit_names) else f"Unit#{j}"
                        if name in seen_names:
                            seen_names[name] = TypeCount(
                                index=seen_names[name].index,
                                name=name,
                                count=seen_names[name].count + v,
                            )
                        else:
                            seen_names[name] = TypeCount(index=j, name=name, count=v)
        house.vehicles = list(seen_names.values())
        total_a = unit_a_ci.total if unit_a_ci else 0
        total_b = unit_b_ci.total if unit_b_ci else 0
        house.vehicle_total = total_a + total_b

        return house

    def _make_breakdown(self, ci: CounterInfo, type_names: list[str]) -> list[TypeCount]:
        """Read per-type counts from counter and pair with names."""
        result = []
        for i in range(ci.count):
            val = self.read_int(ci.items_ptr + i * 4)
            if val and val > 0:
                name = type_names[i] if i < len(type_names) else f"#{i}"
                result.append(TypeCount(index=i, name=name, count=val))
        return result

    def get_process_info(self) -> dict:
        if not self._pm:
            return {}
        return {
            "pid": self._pm.process_id,
            "base_addr": hex(self._base_addr),
            "process_name": self._pm.process_name,
        }
