"""RA2:YR unit type definitions with memory offsets.

Source: wudi-7mi/ra2ob config/unit_offsets.json
       chenguokai/ra2viewer methodology

Each entry maps a human-readable name to the byte offset within the
CounterClass Items[] array. Reading int32 at items_ptr + offset yields
the count of that unit type currently alive for the player.

Data is loaded from data/unitdefs.json at import time.
Lookup dicts (BY_OFFSET) are computed from the loaded data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class UnitDef:
    """A single unit/building/infantry/aircraft type definition."""

    name: str               # English name (from ra2ob)
    name_cn: str            # Chinese display name
    offset: int             # Byte offset in Items[] array
    index: Optional[int]    # Sibling index for shared-name units (e.g. War Factory x3)
    category: str           # building / vehicle / infantry / aircraft
    faction: str            # allied / soviet / yuri / neutral
    invalid: str = ""       # "" = both, "Yr" = RA2 only, "Ra2" = YR only
    is_naval: bool = False  # True for ships/subs/naval transports


def _load_unitdefs() -> list[UnitDef]:
    """Load unit definitions from the bundled JSON data file."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    json_path = data_dir / "unitdefs.json"
    with open(json_path, encoding="utf-8") as f:
        raw = json.load(f)
    units = []
    for entry in raw:
        units.append(UnitDef(
            name=entry["name"],
            name_cn=entry["name_cn"],
            offset=int(entry["offset"], 16),
            index=entry.get("index"),
            category=entry["category"],
            faction=entry["faction"],
            invalid=entry.get("invalid", ""),
            is_naval=entry.get("is_naval", False),
        ))
    return units


def _build_offset_index(units: list[UnitDef]) -> dict[int, UnitDef]:
    """Build offset -> UnitDef mapping, last-write-wins for duplicate offsets."""
    index: dict[int, UnitDef] = {}
    for u in units:
        index[u.offset] = u
    return index


# ── Load and index ────────────────────────────────────────────────────────────
ALL_UNITS: list[UnitDef] = _load_unitdefs()

BUILDINGS: list[UnitDef] = [u for u in ALL_UNITS if u.category == "building"]
VEHICLES: list[UnitDef] = [u for u in ALL_UNITS if u.category == "vehicle"]
INFANTRY: list[UnitDef] = [u for u in ALL_UNITS if u.category == "infantry"]
AIRCRAFT: list[UnitDef] = [u for u in ALL_UNITS if u.category == "aircraft"]

BUILDING_BY_OFFSET: dict[int, UnitDef] = _build_offset_index(BUILDINGS)
VEHICLE_BY_OFFSET: dict[int, UnitDef] = _build_offset_index(VEHICLES)
INFANTRY_BY_OFFSET: dict[int, UnitDef] = _build_offset_index(INFANTRY)
AIRCRAFT_BY_OFFSET: dict[int, UnitDef] = _build_offset_index(AIRCRAFT)

CATEGORY_MAP: dict[str, tuple[list[UnitDef], dict[int, UnitDef]]] = {
    "building": (BUILDINGS, BUILDING_BY_OFFSET),
    "vehicle":  (VEHICLES,  VEHICLE_BY_OFFSET),
    "infantry": (INFANTRY,  INFANTRY_BY_OFFSET),
    "aircraft": (AIRCRAFT,  AIRCRAFT_BY_OFFSET),
}
