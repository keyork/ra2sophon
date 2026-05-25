"""RA2:YR unit type definitions with memory offsets.

Source: wudi-7mi/ra2ob config/unit_offsets.json
       chenguokai/ra2viewer methodology

Each entry maps a human-readable name to the byte offset within the
CounterClass Items[] array. Reading int32 at items_ptr + offset yields
the count of that unit type currently alive for the player.

Counter categories (from ra2ob Constants.hpp):
    Buildings  -> Items ptr at HouseClass + 0x5554  (CounterClass base 0x5550)
    Vehicles   -> Items ptr at HouseClass + 0x5568  (CounterClass base 0x5564)
    Infantry   -> Items ptr at HouseClass + 0x557C  (CounterClass base 0x5578)
    Aircraft   -> Items ptr at HouseClass + 0x5590  (CounterClass base 0x558C)

Note: "Invalid" marks units only available in one game version:
    "Yr"  = NOT available in Yuri's Revenge (RA2 original only)
    "Ra2" = NOT available in RA2 original (Yuri's Revenge only)
    ""    = available in both versions
"""

from __future__ import annotations

from dataclasses import dataclass
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


# ── Buildings ──────────────────────────────────────────────────────────────────
# Offset is byte offset within BuildingType Items[] array.

BUILDINGS: list[UnitDef] = [
    # Allied buildings
    UnitDef("Power Plant",                             "发电厂",           0x000, None, "building", "allied"),
    UnitDef("Allied Ore Refinery",                     "盟军矿厂",         0x004, None, "building", "allied"),
    UnitDef("Allied Construction Yard",                "盟军建造场",       0x008, None, "building", "allied"),
    UnitDef("Allied Barracks",                         "盟军兵营",         0x00C, None, "building", "allied"),
    UnitDef("Allied Service Depot",                    "盟军维修厂",       0x014, None, "building", "allied"),
    UnitDef("Allied Battle Lab",                       "盟军作战实验室",   0x018, None, "building", "allied"),
    UnitDef("Allied War Factory",                      "盟军战车工厂",     0x01C, 1,    "building", "allied"),
    UnitDef("Allied Naval Shipyard",                   "盟军船坞",         0x05C, None, "building", "allied"),
    UnitDef("Allied Construction Yard",                "盟军建造场(2)",    0x064, None, "building", "allied"),
    UnitDef("Iron Curtain Device",                     "铁幕装置",         0x060, None, "building", "allied"),
    UnitDef("Pillbox",                                 "碉堡",             0x108, None, "building", "allied"),
    UnitDef("Patriot Missile System",                  "爱国者飞弹",       0x054, None, "building", "allied"),
    UnitDef("Prism Tower",                             "光棱塔",           0x0DC, None, "building", "allied"),
    UnitDef("Gap Generator",                           "裂缝产生器",       0x0FC, None, "building", "allied"),
    UnitDef("Spy Satellite Uplink",                    "间谍卫星",         0x0F8, None, "building", "allied"),
    UnitDef("Chronosphere",                            "超时空传送仪",     0x06C, None, "building", "allied"),
    UnitDef("Weather Control Device",                  "天气控制机",       0x074, None, "building", "allied"),
    UnitDef("Airforce Command Headquarters",           "空指部",           0x21C, None, "building", "allied"),
    UnitDef("Airforce Command Headquarters (American)", "美国空指部",       0x1A4, None, "building", "allied"),
    UnitDef("Ore Purifier",                            "矿石精炼器",       0x124, None, "building", "allied"),
    UnitDef("Robot Control Center",                    "遥控坦克控制中心", 0x590, None, "building", "allied"),
    UnitDef("Grand Cannon",                            "巨炮",             0x100, 11,   "building", "allied"),
    # Soviet buildings
    UnitDef("Tesla Reactor",                           "磁能反应炉",       0x024, None, "building", "soviet"),
    UnitDef("Soviet Battle Lab",                       "苏军作战实验室",   0x028, None, "building", "soviet"),
    UnitDef("Soviet Barracks",                         "苏军兵营",         0x02C, None, "building", "soviet"),
    UnitDef("Radar Tower",                             "雷达",             0x034, None, "building", "soviet"),
    UnitDef("Soviet War Factory",                      "苏军战车工厂",     0x038, 1,    "building", "soviet"),
    UnitDef("Soviet Ore Refinery",                     "苏军矿厂",         0x03C, None, "building", "soviet"),
    UnitDef("Soviet Service Depot",                    "苏军维修厂",       0x068, None, "building", "soviet"),
    UnitDef("Nuclear Reactor",                         "核能反应炉",       0x104, None, "building", "soviet"),
    UnitDef("Sentry Gun",                              "哨戒炮",           0x050, None, "building", "soviet"),
    UnitDef("Flak Cannon",                             "高射炮",           0x10C, None, "building", "soviet"),
    UnitDef("Tesla Coil",                              "磁暴线圈",         0x0D4, None, "building", "soviet"),
    UnitDef("Soviet Psychic Sensor",                   "心灵感应器",       0x048, None, "building", "soviet", invalid="Yr"),
    UnitDef("Soviet Naval Shipyard",                   "苏军船坞",         0x0F4, None, "building", "soviet"),
    UnitDef("Iron Curtain Device",                     "铁幕装置(苏)",     0x060, None, "building", "soviet"),
    UnitDef("Nuclear Missile Silo",                    "核弹发射井",       0x0D8, None, "building", "soviet"),
    UnitDef("Soviet Cloning Vat",                      "苏军复制中心",     0x120, None, "building", "soviet", invalid="Yr"),
    UnitDef("Battle Bunker",                           "战斗碉堡",         0x59C, None, "building", "soviet"),
    UnitDef("Industrial Plant",                        "工业工厂",         0x4D8, None, "building", "soviet"),
    # Yuri buildings
    UnitDef("Bio Reactor",                             "生化反应炉",       0x4B4, None, "building", "yuri"),
    UnitDef("Yuri Barracks",                           "尤里兵营",         0x4B8, None, "building", "yuri"),
    UnitDef("Yuri War Factory",                        "尤里战车工厂",     0x4BC, 1,    "building", "yuri"),
    UnitDef("Submarine Pen",                           "潜艇厂",           0x4C0, None, "building", "yuri"),
    UnitDef("Yuri Battle Lab",                         "尤里作战实验室",   0x4C8, None, "building", "yuri"),
    UnitDef("Gattling Cannon",                         "盖特机炮",         0x4D0, None, "building", "yuri"),
    UnitDef("Psychic Tower",                           "心灵控制塔",       0x4D4, None, "building", "yuri"),
    UnitDef("Grinder",                                 "回收工厂",         0x4DC, None, "building", "yuri"),
    UnitDef("Genetic Mutator",                         "基因突变器",       0x4E0, None, "building", "yuri"),
    UnitDef("Psychic Dominator",                       "心灵支配仪",       0x4EC, None, "building", "yuri"),
    UnitDef("Yuri Psychic Radar",                      "尤里心灵雷达",     0x048, None, "building", "yuri",   invalid="Ra2"),
    UnitDef("Yuri Cloning Vats",                       "尤里复制中心",     0x120, None, "building", "yuri",   invalid="Ra2"),
    UnitDef("Slave Miner Deployed",                    "奴隶矿场(展开)",   0x594, 2,    "building", "yuri"),
    UnitDef("Tank Bunker",                             "坦克碉堡",         0x558, None, "building", "yuri"),
]


# ── Vehicles (Tanks + Transports + Naval) ──────────────────────────────────────
# Offset is byte offset within UnitType (Vehicle) Items[] array.
# Naval units are marked with is_naval=True for separate categorization.

VEHICLES: list[UnitDef] = [
    # Allied vehicles
    UnitDef("Allied MCV",                     "盟军基地车",       0x000, None, "vehicle", "allied"),
    UnitDef("Chrono Miner",                   "超时空采矿车",     0x084, 2,    "vehicle", "allied"),
    UnitDef("Grizzly Battle Tank",            "灰熊坦克",         0x024, 3,    "vehicle", "allied"),
    UnitDef("Allied Amphibious Transport",    "两栖运输艇(盟)",   0x054, None, "vehicle", "allied", is_naval=True),
    UnitDef("Infantry Fighting Vehicle",      "步兵战车",         0x098, None, "vehicle", "allied"),
    UnitDef("Mirage Tank",                    "幻影坦克",         0x094, None, "vehicle", "allied"),
    UnitDef("Prism Tank",                     "光棱坦克",         0x088, None, "vehicle", "allied"),
    UnitDef("Tank Destroyer",                 "坦克杀手",         0x06C, None, "vehicle", "allied"),
    UnitDef("NightHawk Transport",            "夜鹰直升机",       0x05C, None, "vehicle", "allied"),
    UnitDef("Battle Fortress",                "战斗要塞",         0x0F4, None, "vehicle", "allied"),
    UnitDef("Robot Tank",                     "遥控坦克",         0x120, None, "vehicle", "allied"),
    # Allied naval
    UnitDef("Destroyer",                      "驱逐舰",           0x048, 9,    "vehicle", "allied", is_naval=True),
    UnitDef("Aegis Cruiser",                  "神盾巡洋舰",       0x050, None, "vehicle", "allied", is_naval=True),
    UnitDef("Dolphin",                        "海豚",             0x064, None, "vehicle", "allied", is_naval=True),
    UnitDef("Aircraft Carrier",               "航空母舰",         0x034, 10,   "vehicle", "allied", is_naval=True),
    # Soviet vehicles
    UnitDef("War Miner",                      "武装采矿车",       0x004, 2,    "vehicle", "soviet"),
    UnitDef("Rhino Heavy Tank",               "犀牛坦克",         0x00C, 3,    "vehicle", "soviet"),
    UnitDef("Apocalypse Tank",                "天启坦克",         0x008, None, "vehicle", "soviet"),
    UnitDef("Soviet Amphibious Transport",    "两栖运输艇(苏)",   0x010, None, "vehicle", "soviet", is_naval=True),
    UnitDef("V3 Rocket Launcher",             "V3火箭车",         0x038, None, "vehicle", "soviet"),
    UnitDef("Terror Drone",                   "恐怖机器人",       0x040, None, "vehicle", "soviet"),
    UnitDef("Flak Track",                     "防空履带车",       0x044, None, "vehicle", "soviet"),
    UnitDef("Tesla Tank",                     "磁能坦克",         0x074, None, "vehicle", "soviet"),
    UnitDef("Soviet MCV",                     "苏军基地车",       0x068, None, "vehicle", "soviet"),
    UnitDef("Demolition Truck",               "自爆卡车",         0x0A4, None, "vehicle", "soviet"),
    UnitDef("Siege Chopper",                  "武装直升机",       0x10C, None, "vehicle", "soviet"),
    # Soviet naval
    UnitDef("Typhoon Attack Submarine",       "台风攻击潜艇",     0x04C, 9,    "vehicle", "soviet", is_naval=True),
    UnitDef("Sea Scorpion",                   "海蝎",             0x090, None, "vehicle", "soviet", is_naval=True),
    UnitDef("Giant Squid",                    "巨型乌贼",         0x060, None, "vehicle", "soviet", is_naval=True),
    UnitDef("Dreadnought",                    "无畏级战舰",       0x058, 10,   "vehicle", "soviet", is_naval=True),
    UnitDef("Kirov Airship",                  "基洛夫飞艇",       0x03C, None, "vehicle", "soviet"),
    # Yuri vehicles
    UnitDef("Slave Miner",                    "奴隶矿车",         0x0E4, 2,    "vehicle", "yuri"),
    UnitDef("Lasher Tank",                    "狂风坦克",         0x07C, 3,    "vehicle", "yuri"),
    UnitDef("Yuri MCV",                       "尤里基地车",       0x0E0, None, "vehicle", "yuri"),
    UnitDef("Gattling Tank",                  "盖特坦克",         0x0F0, None, "vehicle", "yuri"),
    UnitDef("Magnetron",                      "磁电坦克",         0x0F8, None, "vehicle", "yuri"),
    UnitDef("Chaos Drone",                    "混乱无人机",       0x0FC, None, "vehicle", "yuri"),
    UnitDef("Mastermind",                     "精神控制车",       0x114, None, "vehicle", "yuri"),
    UnitDef("Floating Disc",                  "飞碟",             0x118, None, "vehicle", "yuri"),
    # Yuri naval
    UnitDef("Yuri Amphibious Transport",      "两栖运输艇(尤)",   0x0DC, 9,    "vehicle", "yuri",   is_naval=True),
    UnitDef("Boomer",                         "雷鸣潜艇",         0x108, None, "vehicle", "yuri",   is_naval=True),
]


# ── Infantry ───────────────────────────────────────────────────────────────────
# Offset is byte offset within InfantryType Items[] array.

INFANTRY: list[UnitDef] = [
    # Allied infantry
    UnitDef("GI",                   "美国大兵",         0x000, 5,    "infantry", "allied"),
    UnitDef("Allied Engineer",      "盟军工程师",       0x00C, 6,    "infantry", "allied"),
    UnitDef("Allied Attack Dog",    "盟军警犬",         0x070, 4,    "infantry", "allied"),
    UnitDef("Rocketeer",            "火箭飞行兵",       0x010, 7,    "infantry", "allied"),
    UnitDef("Navy SEAL",            "海豹突击队",       0x014, None, "infantry", "allied"),
    UnitDef("Chrono Legionnaire",   "超时空军团兵",     0x03C, None, "infantry", "allied"),
    UnitDef("Spy",                  "间谍",             0x040, None, "infantry", "allied"),
    UnitDef("Sniper",               "狙击手",           0x054, None, "infantry", "allied"),
    UnitDef("Tanya",                "谭雅",             0x060, None, "infantry", "allied"),
    UnitDef("Guardian GI",          "重装大兵",         0x0B8, None, "infantry", "allied"),
    UnitDef("Chrono Commando",      "超时空突击队",     0x044, None, "infantry", "allied"),
    UnitDef("Psi Commando",         "心灵突击队",       0x048, None, "infantry", "allied"),
    UnitDef("Chrono Ivan",          "超时空伊万",       0x04C, None, "infantry", "allied"),
    # Soviet infantry
    UnitDef("Conscript",            "动员兵",           0x004, 5,    "infantry", "soviet"),
    UnitDef("Tesla Trooper",        "磁暴步兵",         0x008, None, "infantry", "soviet"),
    UnitDef("Soviet Attack Dog",    "苏军警犬",         0x024, 4,    "infantry", "soviet"),
    UnitDef("Crazy Ivan",           "疯狂伊万",         0x01C, None, "infantry", "soviet"),
    UnitDef("Desolator",            "辐射工兵",         0x020, 7,    "infantry", "soviet"),
    UnitDef("Soviet Engineer",      "苏军工程师",       0x06C, 6,    "infantry", "soviet"),
    UnitDef("Terrorist",            "恐怖分子",         0x068, None, "infantry", "soviet"),
    UnitDef("Flak Trooper",         "防空步兵",         0x05C, None, "infantry", "soviet"),
    UnitDef("Yuri",                 "尤里(原版)",       0x018, None, "infantry", "soviet", invalid="Yr"),
    UnitDef("Boris",                "鲍里斯",           0x0C0, None, "infantry", "soviet"),
    # Yuri infantry
    UnitDef("Initiate",             "尤里新兵",         0x0BC, 5,    "infantry", "yuri"),
    UnitDef("Yuri Engineer",        "尤里工程师",       0x0B4, 6,    "infantry", "yuri"),
    UnitDef("Brute",                "狂兽人",           0x0C4, 4,    "infantry", "yuri"),
    UnitDef("Virus",                "病毒狙击手",       0x0C8, None, "infantry", "yuri"),
    UnitDef("Yuri Clone",           "尤里复制人",       0x018, None, "infantry", "yuri",   invalid="Ra2"),
    UnitDef("Yuri X",               "尤里X",            0x050, None, "infantry", "yuri",   invalid="Ra2"),
    UnitDef("Yuri Prime",           "尤里(尤复)",       0x050, None, "infantry", "yuri",   invalid="Yr"),
]


# ── Aircraft ───────────────────────────────────────────────────────────────────
# Offset is byte offset within AircraftType Items[] array.

AIRCRAFT: list[UnitDef] = [
    UnitDef("Harrier",              "鹞式战斗机",       0x004, 8,    "aircraft", "allied"),
    UnitDef("Black Eagle",          "黑鹰战机",         0x01C, 8,    "aircraft", "allied"),
]


# ── Lookup helpers ─────────────────────────────────────────────────────────────

# All definitions in one flat list
ALL_UNITS: list[UnitDef] = BUILDINGS + VEHICLES + INFANTRY + AIRCRAFT

# Index by (category, offset) for fast counter lookup
def _build_offset_index(units: list[UnitDef]) -> dict[int, UnitDef]:
    """Build offset -> UnitDef mapping, last-write-wins for duplicate offsets."""
    index: dict[int, UnitDef] = {}
    for u in units:
        index[u.offset] = u
    return index

BUILDING_BY_OFFSET: dict[int, UnitDef] = _build_offset_index(BUILDINGS)
VEHICLE_BY_OFFSET: dict[int, UnitDef] = _build_offset_index(VEHICLES)
INFANTRY_BY_OFFSET: dict[int, UnitDef] = _build_offset_index(INFANTRY)
AIRCRAFT_BY_OFFSET: dict[int, UnitDef] = _build_offset_index(AIRCRAFT)

# Category name -> (list[UnitDef], lookup_dict)
CATEGORY_MAP: dict[str, tuple[list[UnitDef], dict[int, UnitDef]]] = {
    "building": (BUILDINGS, BUILDING_BY_OFFSET),
    "vehicle":  (VEHICLES,  VEHICLE_BY_OFFSET),
    "infantry": (INFANTRY,  INFANTRY_BY_OFFSET),
    "aircraft": (AIRCRAFT,  AIRCRAFT_BY_OFFSET),
}
