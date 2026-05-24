"""Data types for RA2:YR memory reading.

Contains dataclasses used by the memory reader and game state inspection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


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
