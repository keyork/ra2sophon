"""Unit and building enumeration for RA2:YR.

Scans process memory to find all game objects owned by the current player.
Uses vtable signatures to identify object types (Infantry, Building, Unit, Aircraft).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Optional

from .offsets import (
    OBJ_OWNER_AIRCRAFT,
    OBJ_OWNER_BUILDING,
    OBJ_OWNER_INFANTRY,
    OBJ_OWNER_UNIT,
    OBJECT_HEAP_SCAN_RANGES,
    PLAYER_PTR,
    VTABLE_AIRCRAFT,
    VTABLE_BUILDING,
    VTABLE_INFANTRY,
    VTABLE_UNIT,
)
from .reader import GameReader


@dataclass
class GameObject:
    """A game object (unit, building, infantry, aircraft)."""
    address: int
    vtable: int
    owner_offset: int
    object_type: str = "unknown"  # infantry, building, unit, aircraft

    @property
    def is_infantry(self) -> bool:
        return self.vtable == VTABLE_INFANTRY

    @property
    def is_building(self) -> bool:
        return self.vtable == VTABLE_BUILDING

    @property
    def is_unit(self) -> bool:
        return self.vtable == VTABLE_UNIT

    @property
    def is_aircraft(self) -> bool:
        return self.vtable == VTABLE_AIRCRAFT


@dataclass
class ObjectScanResult:
    """Result of scanning for player-owned objects."""
    infantry: list[GameObject] = field(default_factory=list)
    buildings: list[GameObject] = field(default_factory=list)
    units: list[GameObject] = field(default_factory=list)
    aircraft: list[GameObject] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.infantry) + len(self.buildings) + len(self.units) + len(self.aircraft)


# vtable -> (owner_offset, type_name)
VTABLE_MAP = {
    VTABLE_INFANTRY: (OBJ_OWNER_INFANTRY, "infantry"),
    VTABLE_BUILDING: (OBJ_OWNER_BUILDING, "building"),
    VTABLE_UNIT: (OBJ_OWNER_UNIT, "unit"),
    VTABLE_AIRCRAFT: (OBJ_OWNER_AIRCRAFT, "aircraft"),
}


def scan_player_objects(reader: GameReader) -> ObjectScanResult:
    """Scan heap for all game objects owned by the current player.

    This is an expensive operation - scans ~100MB of memory.
    Cache results and call sparingly.

    Returns:
        ObjectScanResult with categorized game objects.
    """
    result = ObjectScanResult()

    player = reader.read_pointer(PLAYER_PTR)
    if not player:
        return result

    target_bytes = struct.pack('<I', player)

    # Scan heap in 1MB chunks
    hits = []
    for start, end in OBJECT_HEAP_SCAN_RANGES:
        addr = start
        while addr < end:
            try:
                chunk = reader.read_bytes(addr, 0x100000)
                pos = 0
                while pos < len(chunk) - 4:
                    idx = chunk.find(target_bytes, pos)
                    if idx < 0:
                        break
                    hits.append(addr + idx)
                    pos = idx + 4
            except Exception:
                pass
            addr += 0x100000

    # Identify each hit by its vtable
    for hit in hits:
        for off in range(0, 0x100, 4):
            check_addr = hit - off
            try:
                val = reader.read_uint(check_addr)
                if val in VTABLE_MAP:
                    owner_off, type_name = VTABLE_MAP[val]
                    obj = GameObject(
                        address=check_addr,
                        vtable=val,
                        owner_offset=owner_off,
                        object_type=type_name,
                    )
                    if obj.is_infantry:
                        result.infantry.append(obj)
                    elif obj.is_building:
                        result.buildings.append(obj)
                    elif obj.is_unit:
                        result.units.append(obj)
                    elif obj.is_aircraft:
                        result.aircraft.append(obj)
                    break
            except Exception:
                continue

    return result
