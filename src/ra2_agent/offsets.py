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
AIRCRAFT_ARRAY = 0xA8E390
TRIGGER_ARRAY = 0xA8EAE8
TAG_ARRAY = 0xB0E720

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

# ── Counter Category Offsets (verified 2025-05-24) ─────────────────────────────
# Each offset identifies a specific counter role within HouseClass.
COUNTER_BUILDINGS = 0x5500        # BuildingType counter
COUNTER_UNITS_A = 0x5528          # Vehicle/Infantry subset A
COUNTER_BUILDINGS_ALT = 0x5550    # Building alt
COUNTER_UNITS_B = 0x5564          # Vehicle/Infantry subset B
COUNTER_UNITS_A_ALT = 0x5578      # Units A alt
COUNTER_BUILDINGS_ALT2 = 0x55A0   # Building alt 2
COUNTER_UNITS_B_ALT = 0x55B4      # Units B alt
COUNTER_UNITS_A_ALT2 = 0x55C8     # Units A alt 2

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
VTABLE_INFANTRY = 0x007E180C        # InfantryClass
VTABLE_BUILDING = 0x007F3FBC        # BuildingClass
VTABLE_UNIT = 0x007EFDA4            # UnitClass (vehicles)
VTABLE_AIRCRAFT = 0x007E8934        # AircraftClass

# ── Object member offsets (by type) ──────────────────────────────────────────
# Owner (HouseClass*) offset per object type:
OBJ_OWNER_INFANTRY = 0x6C           # InfantryClass
OBJ_OWNER_BUILDING = 0x84           # BuildingClass
OBJ_OWNER_UNIT = 0x3C               # UnitClass
OBJ_OWNER_AIRCRAFT = 0x2C           # AircraftClass

# Coordinate offsets (cell X, Y) - approximate, need further verification
OBJ_COORD_UNIT = 0x28               # UnitClass: (x, y) as int pair

# ── House identity ───────────────────────────────────────────────────────────
HOUSE_ARRAY_INDEX = 0x38        # int - index in HouseClassArray (0,1,2,3...)

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
