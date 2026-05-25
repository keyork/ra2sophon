"""Memory offsets for Red Alert 2: Yuri's Revenge (gamemd.exe).

Sources:
- CnCNet yr-patches/sym.asm
- YRpp headers (Phobos-developers/YRpp)
- FearlessRevolution CE community tables
- chenguokai/ra2viewer methodology
- AdjWang/RA2YurisRevengeTrainer offsets

NOTE: These offsets are for YR 1.001 (gamemd.exe).
With Ares/Phobos loaded, the .exe addresses should be stable,
but HouseClass member offsets may shift. Use probe.py to verify.
"""

# ── Process ──────────────────────────────────────────────────────────────────
# Known process names for RA2:YR (varies by launcher/spawner)
PROCESS_NAMES = [
    "gamemd.exe",
    "gamemd-spawn.exe",
    "gameares.exe",
]
PROCESS_NAME = "gamemd-spawn.exe"  # auto-detected; overridden at runtime

# ── Global Pointers (absolute addresses in gamemd.exe virtual space) ─────────
# These are fixed addresses in the .data/.bss section of gamemd.exe.
# They hold pointers to the actual game objects.

# Pointer to current player's HouseClass instance
PLAYER_PTR = 0xA83D4C

# Pointer to observer HouseClass (used in spectator mode)
OBSERVER_PTR = 0xAC1198

# DynamicVectorClass<HouseClass*> - array of all HouseClass instances
HOUSE_ARRAY_PTR = 0xA8022C
# int - number of houses in the array
HOUSE_ARRAY_COUNT = 0xA80238

# DynamicVectorClass<HouseTypeClass*> - array of HouseTypeClass definitions
HOUSE_TYPE_ARRAY_PTR = 0xA83C9C
HOUSE_TYPE_ARRAY_COUNT = 0xA83CA8

# bool - whether the game is in observer mode
OBSERVER_MODE = 0xAC10C8

# ── Object Arrays (DynamicVectorClass pointers) ──────────────────────────────
# Each is a pointer to a DynamicVectorClass<T*> containing all instances.
# Source: YRpp (Metadorius/YRpp) static constexpr pointers.
AIRCRAFT_ARRAY = 0xA8E390        # AircraftClass::Array
TRIGGER_ARRAY = 0xA8EAE8
TAG_ARRAY = 0xB0E720

# TechnoClass::Array — all units, infantry, buildings, aircraft combined
TECHNO_ARRAY = 0xA8EC78          # DynamicVectorClass<TechnoClass*>

# Per-type instance arrays (YRpp confirmed)
INFANTRY_ARRAY = 0xA83DE8        # InfantryClass::Array
UNIT_ARRAY = 0x8B4108            # UnitClass::Array
BUILDING_ARRAY = 0xA8EB40        # BuildingClass::Array

# Other globals (YRpp confirmed)
SCENARIO_INSTANCE = 0xA8B230     # ScenarioClass::Instance
GAME_IS_ACTIVE = 0xA8E9A0        # Game::IsActive
GAME_HWND = 0xB73550             # Game::hWnd

# ── TypeClass Arrays (DVC addresses in static data) ──────────────────────────
# Each DVC holds TypeClass* pointers. Name string at TypeClass+0x24.
INFANTRY_TYPE_ARRAY  = 0xA8E34C  # 70 entries: E1, E2, SHK, ENGINEER, ...
UNIT_TYPE_ARRAY      = 0xA83CE4  # 90 entries: AMCV, HARV, APOC, HTNK, ...
AIRCRAFT_TYPE_ARRAY  = 0xA83CFC  # 20 entries
HOUSE_TYPE_ARRAY     = 0xA83C9C  # 20 entries: Americans, Alliance, ...
PROJECTILE_TYPE_ARRAY = 0xA83C84 # 50 entries
OVERLAY_TYPE_ARRAY   = 0xA83D84  # 250 entries
TERRAIN_TYPE_ARRAY   = 0xA8E31C  # 110 entries
SPECIAL_WEAPON_TYPE_ARRAY = 0xA8E334  # 20 entries

# BuildingTypeClass array is heap-based (not at a static address like others).
# Discovered at runtime via vtable scan. Objects have vtable 0x7E4570.
VTABLE_BUILDING_TYPE = 0x7E4570

# TypeClass member offsets
TYPE_NAME_OFFSET = 0x24  # char[] - type ID string (e.g. "GAPOWR", "E1", "HARV")

# ── HouseClass Member Offsets ────────────────────────────────────────────────
# These are RELATIVE offsets from a HouseClass instance pointer.
# Verified against live gamemd-spawn.exe with Ares 21.352 + Phobos 0.3.0.

# ── Credits ──────────────────────────────────────────────────────────────────
HOUSE_CREDITS_INITIAL = 0x1DC   # int - starting credits (10000 typically)
HOUSE_CREDITS_SPENT = 0x2DC     # int - total credits spent
HOUSE_CREDITS_CURRENT = 0x30C   # int - current available credits ✅ VERIFIED

# ── Power ────────────────────────────────────────────────────────────────────
HOUSE_POWER_PRODUCED = 0x53A4   # int - total power produced ✅ VERIFIED
HOUSE_POWER_DRAINED = 0x53A8    # int - total power drain ✅ VERIFIED

# ── Unit/Building Counters (CounterClass) ─────────────────────────────────────
# CounterClass layout: +0x00=vtable(0x7E5C54), +0x04=items_ptr, +0x08=count,
#                       +0x0C=flags(0x101), +0x10=total
# Items_ptr points to int[] where each element = count of that type index
# Total at +0x10 = sum of all items
# CounterClass size = 0x14 (20 bytes)
#
# Verified from live memory (2025-05-24):
#   0x5500: InfantryType counter (count=145, items map to InfantryType indices)
#   0x5528: BuildingType counter (count=38)
#   0x553C: AircraftType counter (count=11)
#   0x5564: UnitType/Vehicle counter (count=43)
#   0x5578: duplicate/alt counters follow
#
# NOTE: Counter-to-category mapping is auto-discovered at runtime.
# The base address of the first counter is 0x5500.

HOUSE_COUNTERS_BASE = 0x5500  # First CounterClass in HouseClass
HOUSE_COUNTER_VTABLE = 0x007E5C54
COUNTER_CLASS_SIZE = 0x14      # 20 bytes per CounterClass
COUNTER_MAX_COUNT = 12         # Max counters to scan

# ── Alive Counter Offsets (from ra2ob Constants.hpp) ─────────────────────────
# These CounterClass offsets track units/buildings currently alive on the map.
# Each CounterClass layout: +0x00=vtable, +0x04=items_ptr, +0x08=count,
#                            +0x0C=flags(0x101), +0x10=total
# items_ptr points to int[] where each int = count at that byte-offset slot.

# Alive counters (currently on map) — the primary source for unit counts
ALIVE_BUILDING_COUNTER  = 0x5550   # CounterClass base for alive buildings
ALIVE_VEHICLE_COUNTER   = 0x5564   # CounterClass base for alive vehicles
ALIVE_INFANTRY_COUNTER  = 0x5578   # CounterClass base for alive infantry
ALIVE_AIRCRAFT_COUNTER  = 0x558C   # CounterClass base for alive aircraft

# Items pointer = counter_base + 0x04
ALIVE_BUILDING_ITEMS  = 0x5554     # int* — building counts by offset
ALIVE_VEHICLE_ITEMS   = 0x5568     # int* — vehicle counts by offset
ALIVE_INFANTRY_ITEMS  = 0x557C     # int* — infantry counts by offset
ALIVE_AIRCRAFT_ITEMS  = 0x5590     # int* — aircraft counts by offset

# Factory/production counters (units currently being produced)
FACTORY_BUILDING_COUNTER  = 0x55A0  # CounterClass base for factory-produced buildings
FACTORY_VEHICLE_COUNTER   = 0x55B4  # CounterClass base for factory-produced vehicles
FACTORY_INFANTRY_COUNTER  = 0x55C8  # CounterClass base for factory-produced infantry
FACTORY_AIRCRAFT_COUNTER  = 0x55DC  # CounterClass base for factory-produced aircraft

# Legacy aliases (old counter naming, kept for reference)
# 0x5500 = OwnedBuildingTypes (total ever built, includes destroyed)
# 0x5528 = unknown subset counter
OWNED_BUILDING_COUNTER = 0x5500    # Total owned buildings (historical)
OWNED_UNKNOWN_COUNTER  = 0x5528    # Unknown subset

# ── Heap Scan Ranges ───────────────────────────────────────────────────────────
# Memory regions scanned when searching for game objects / type classes.

# BuildingTypeClass heap scan (focused range for TypeClass objects)
BUILDING_HEAP_SCAN_RANGES = [(0x10000000, 0x20000000)]
BUILDING_HEAP_CHUNK_SIZE = 0x10000  # 64KB chunks

# Object heap scan (infantry, buildings, units, aircraft in game memory)
OBJECT_HEAP_SCAN_RANGES = [
    (0x03000000, 0x03200000),
    (0x1A000000, 0x21000000),
]

# CounterClass internal offsets (relative to counter base)
CTR_ITEMS  = 0x04   # int*  - array of per-type counts
CTR_COUNT  = 0x08   # int   - number of items
CTR_FLAGS  = 0x0C   # int   - flags (typically 0x101)
CTR_TOTAL  = 0x10   # int   - sum of all items

# HouseTypeClass* offset in HouseClass
HOUSE_TYPE_PTR = 0x34  # HouseTypeClass* (verified: name="Americans")

# ── Object vtables (identify object types) ────────────────────────────────────
# Source: YRpp headers (v1.001 binary, may shift with Ares/Phobos)
VTABLE_INFANTRY = 0x007EB058        # InfantryClass
VTABLE_BUILDING = 0x007E3EBC        # BuildingClass
VTABLE_UNIT = 0x007F5C70            # UnitClass (vehicles)
VTABLE_AIRCRAFT = 0x007E22A4        # AircraftClass

# ── Object member offsets (by class, YRpp confirmed) ─────────────────────────
# ObjectClass members (base of all game objects):
OBJ_HEALTH = 0x6C               # int - current HP
OBJ_ESTIMATED_HEALTH = 0x70     # int - estimated HP (for display)
OBJ_IS_ON_MAP = 0x74            # bool
OBJ_IS_SELECTED = 0x7B          # bool - selected by player
OBJ_IS_ALIVE = 0x83             # bool
OBJ_LOCATION = 0x9C             # CoordStruct {int X, int Y, int Z} in leptons

# TechnoClass members (all units, infantry, buildings, aircraft):
TECH_OWNER = 0x1F8              # HouseClass* - owning player (approximate, varies by subclass)
TECH_VETERANCY = 0x1C4          # float - 0.0=Rookie, 1.0=Veteran, 2.0=Elite (approximate)

# Owner (HouseClass*) offset per object type (from live memory analysis):
OBJ_OWNER_INFANTRY = 0x6C           # InfantryClass
OBJ_OWNER_BUILDING = 0x84           # BuildingClass
OBJ_OWNER_UNIT = 0x3C               # UnitClass
OBJ_OWNER_AIRCRAFT = 0x2C           # AircraftClass

# Coordinate offsets (cell X, Y) - approximate, need further verification
OBJ_COORD_UNIT = 0x28               # UnitClass: (x, y) as int pair

# ── House identity ───────────────────────────────────────────────────────────
HOUSE_ARRAY_INDEX = 0x38        # int - index in HouseClassArray (0,1,2,3...)

# ── Player status offsets (from ra2ob Constants.hpp) ─────────────────────────
ISDEFEATEDOFFSET = 0x1F5        # bool - player defeated
ISGAMEOVEROFFSET = 0x1F6        # bool - game over for this house
ISWINNEROFFSET   = 0x1F7        # bool - this house won
TEAMNUMBEROFFSET = 0x1D8        # int - team number
COLOROFFSET      = 0x56F9       # color value (3 bytes RGB)

# ── Kill/Loss score offsets (from ra2ob Constants.hpp) ───────────────────────
KILLEDUNITSOFHOUSES     = 0x53E4   # kills tracker for units
KILLEDBUILDINGSOFHOUSES = 0x5438   # kills tracker for buildings
TOTALKILLEDUNITS        = 0x5488   # total units killed by this house
TOTALKILLEDBUILDINGS    = 0x5434   # total buildings killed by this house

# ── Known Cheat Engine offsets for YR 1.001 ─────────────────────────────────
# These were reported by the CE community for the vanilla 1.001 binary.
# They may NOT work with Ares/Phobos - verify with probe.py.
#
# Credits: search for your current money value as int32
#   HouseClass + offset → int32 (credits in $)
# Power: search for power produced / power drained as int32
#   HouseClass + offset → int32 (power units)

# ── HouseTypeClass Member Offsets ────────────────────────────────────────────
# From ModEnc documentation
HT_COUNTRY_NAME = 0x98     # char[0x18] - country name
HT_INDEX = 0xB4            # int - index in global array
HT_SIDE = 0xBC             # int - side (0=Allied, 1=Soviet, 2=Yuri)
HT_COLOR = 0xC0            # ColorScheme* - player color
HT_FIREPOWER = 0xC8        # double - firepower multiplier
HT_GROUNDSPEED = 0xD0      # double - speed multiplier
HT_ARMOR = 0xE0            # double - armor multiplier
HT_ROF = 0xE8              # double - rate of fire multiplier
HT_COST = 0xF0             # double - cost multiplier
HT_BUILD_TIME = 0xF8       # double - build time multiplier

# ── DynamicVectorClass layout (YR engine) ────────────────────────────────────
# Verified from live memory dump of gamemd-spawn:
#   +0x00: T* Items  (pointer to array of T)
#   +0x04: int Count (number of elements)
#   +0x08: int Capacity
#   +0x0C: int GrowthStep
DVEC_ITEMS = 0x00
DVEC_COUNT = 0x04
DVEC_CAPACITY = 0x08
DVEC_GROWTH = 0x0C

# ── AbstractType enum (from YRpp GeneralDefinitions.h) ───────────────────────
class AbstractType:
    NONE = 0
    UNIT = 1
    AIRCRAFT = 2
    AIRCRAFT_TYPE = 3
    ANIM = 4
    ANIM_TYPE = 5
    BUILDING = 6
    BUILDING_TYPE = 7
    BULLET = 8
    BULLET_TYPE = 9
    CAMPAIGN = 10
    CELL = 11
    FACTORY = 12
    HOUSE = 13
    HOUSE_TYPE = 14
    INFANTRY = 15
    INFANTRY_TYPE = 16
