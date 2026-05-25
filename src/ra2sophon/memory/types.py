"""Data types for RA2:YR memory reading.

Contains dataclasses used by the memory reader and game state inspection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ── Validation thresholds ─────────────────────────────────────────────────────
MAX_VALID_CREDITS = 1_000_000
MAX_VALID_UNIT_TOTAL = 10000

# ── Faction name sets ─────────────────────────────────────────────────────────
SOVIET_HOUSE_NAMES = {"russians", "africans", "arabs", "confederation"}
ALLIED_HOUSE_NAMES = {"americans", "alliance", "french", "germans", "british", "korea"}


@dataclass
class TypeCount:
    """Count of a specific type (building, infantry, unit, aircraft)."""
    index: int
    name: str          # English name
    name_cn: str = ""  # Chinese display name
    count: int = 0
    category: str = ""  # building / vehicle / infantry / aircraft
    faction: str = ""   # allied / soviet / yuri
    is_naval: bool = False


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
    # Per-type breakdowns (populated by counter reading with unitdefs)
    buildings: list[TypeCount] = field(default_factory=list)
    infantry: list[TypeCount] = field(default_factory=list)
    vehicles: list[TypeCount] = field(default_factory=list)
    naval: list[TypeCount] = field(default_factory=list)
    aircraft: list[TypeCount] = field(default_factory=list)
    # Totals
    building_total: int = 0
    infantry_total: int = 0
    vehicle_total: int = 0
    naval_total: int = 0
    aircraft_total: int = 0
    # HouseType identity
    house_type_name: str = ""
    # Score / combat stats (from ra2ob offsets)
    units_killed: int = 0
    buildings_killed: int = 0
    units_lost: int = 0
    buildings_lost: int = 0
    # Status flags
    is_defeated: bool = False

    @property
    def power_surplus(self) -> int:
        return (self.power_produced or 0) - (self.power_drained or 0)

    @property
    def total_units(self) -> int:
        """Total combat units (infantry + vehicles + naval + aircraft)."""
        return self.infantry_total + self.vehicle_total + self.naval_total + self.aircraft_total

    @property
    def is_active(self) -> bool:
        """True if this house represents an active player."""
        if self.is_observer:
            return False
        if self.credits is not None and self.credits < 0:
            return False
        # Reject garbage data
        if self.credits is not None and self.credits > MAX_VALID_CREDITS:
            return False
        if self.building_total > MAX_VALID_UNIT_TOTAL or self.infantry_total > MAX_VALID_UNIT_TOTAL:
            return False
        if self.vehicle_total > MAX_VALID_UNIT_TOTAL or self.aircraft_total > MAX_VALID_UNIT_TOTAL:
            return False
        # Reject "Neutral" / non-player houses (0 credits = not a real player)
        has_money = self.credits is not None and self.credits > 0
        if not has_money:
            return False
        return True

    @property
    def faction(self) -> str:
        """Guess faction from house_type_name."""
        name = self.house_type_name.lower()
        if "yuri" in name:
            return "yuri"
        if name in SOVIET_HOUSE_NAMES:
            return "soviet"
        if name in ALLIED_HOUSE_NAMES:
            return "allied"
        return "unknown"


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
