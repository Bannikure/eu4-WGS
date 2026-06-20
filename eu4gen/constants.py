"""
EU4 World Generator – Global constants and static data tables.

All magic numbers, name pools, and lookup tables live here so every other
module can import them from a single source of truth.
"""

from typing import Final

# ---------------------------------------------------------------------------
# Map geometry
# ---------------------------------------------------------------------------

MAP_WIDTH:  Final[int] = 5632
MAP_HEIGHT: Final[int] = 2048
SEA_LEVEL_THRESHOLD: Final[int] = 115
OCEAN_COLOR: Final[tuple[int, int, int]] = (10, 30, 70)

# ---------------------------------------------------------------------------
# Country name generation pools
# ---------------------------------------------------------------------------

ADJECTIVES: Final[list[str]] = [
    "Grand", "Holy", "Iron", "United", "New", "High", "Eternal",
    "Solar", "Greater", "Ashen",
]

ACRONYMS: Final[list[tuple[str, str]]] = [
    ("U.S.D.", "United Satellite Dominion"),
    ("S.P.Q.R.", "Senate and People of Rome"),
    ("U.P.R.", "United Provinces Republic"),
    ("F.S.T.", "Federated Sovereign Territories"),
]

ROOT_NAMES: Final[list[str]] = [
    "Mosik", "Bruce", "Valoria", "Atreides", "Rohan", "Carthon", "Orodruin", "Elysia",
    "Gondor", "Aethelgard", "Skye", "Navarra", "Harkonnen", "Zonaria", "Illyria", "Merovia",
]

GOVERNMENTS: Final[dict[str, list[str]]] = {
    "monarchy":  ["Empire", "Kingdom", "Queendom", "Principality", "Sovereignty", "Dynasty"],
    "republic":  ["Republic", "Commonwealth", "Federation", "League", "Dominion", "Directorate"],
    "theocracy": ["Theocracy", "Holy See", "Order", "Conclave"],
}

# ---------------------------------------------------------------------------
# Flag generation
# ---------------------------------------------------------------------------

FLAG_PALETTE: Final[list[tuple[int, int, int]]] = [
    (180, 20,  20),
    (20,  50,  150),
    (220, 180, 20),
    (20,  120, 40),
    (240, 240, 240),
    (25,  25,  25),
    (110, 40,  140),
]

# ---------------------------------------------------------------------------
# Ruler skill generation
# ---------------------------------------------------------------------------

SKILL_LEVELS:  Final[list[int]]   = [0, 1, 2, 3, 4, 5, 6]
SKILL_WEIGHTS: Final[list[float]] = [0.05, 0.12, 0.22, 0.22, 0.22, 0.12, 0.05]

LEADER_MONIKERS: Final[list[str]] = [
    "the Great", "the Conqueror", "the Builder",
    "the Mad", "the Just", "the Cruel", "",
]

# ---------------------------------------------------------------------------
# National idea modifier pools
# ---------------------------------------------------------------------------

ADVANCED_MODIFIERS: Final[list[str]] = [
    "trade_efficiency = 0.15",
    "global_trade_power = 0.20",
    "technology_cost = -0.10",
    "production_efficiency = 0.15",
    "idea_cost = -0.10",
    "global_ship_trade_power = 0.25",
    "merchants = 1",
    "discipline = 0.05",
    "global_institution_spread = 0.20",
]

PRIMITIVE_MODIFIERS: Final[list[str]] = [
    "land_attrition = -0.15",
    "fort_defense = 0.15",
    "infantry_power = 0.10",
    "stability_cost_modifier = -0.15",
    "manpower_recovery_speed = 0.15",
    "hostile_attrition = 1.0",
    "unrest = -2",
    "defensiveness = 0.20",
]

# ---------------------------------------------------------------------------
# Trade goods
# ---------------------------------------------------------------------------

_GoodEntry = dict[str, object]

RICH_COMMODITIES: Final[dict[str, _GoodEntry]] = {
    "solar_silk": {
        "base_price": 5.0,
        "prov_buff": "production_efficiency = 0.10",
        "global_buff": "trade_efficiency = 0.10",
    },
    "spiceweave_glass": {
        "base_price": 4.5,
        "prov_buff": "local_trade_power_modifier = 0.15",
        "global_buff": "global_trade_power = 0.15",
    },
    "abyssal_pearls": {
        "base_price": 6.0,
        "prov_buff": "local_tax_modifier = 0.20",
        "global_buff": "technology_cost = -0.05",
    },
    "island_nectar": {
        "base_price": 4.0,
        "prov_buff": "local_manpower_modifier = 0.15",
        "global_buff": "land_morale = 0.05",
    },
}

BARREN_COMMODITIES: Final[dict[str, _GoodEntry]] = {
    "corrupt_sludge": {
        "base_price": 1.0,
        "prov_buff": "local_unrest = 1",
        "global_buff": "global_corruption = 0.01",
    },
    "brittle_stone": {
        "base_price": 1.2,
        "prov_buff": "fort_defense = -0.10",
        "global_buff": "stability_cost_modifier = 0.10",
    },
    "salted_mud": {
        "base_price": 0.8,
        "prov_buff": "local_autonomy_growth = 0.05",
        "global_buff": "all_power_cost = 0.05",
    },
}

# ---------------------------------------------------------------------------
# Province size generation
# ---------------------------------------------------------------------------

SIZE_CLEARANCE: Final[dict[str, int]] = {
    "tiny":   12,
    "small":  25,
    "medium": 50,
    "large":  90,
    "huge":   160,
}

SIZE_CHOICES:  Final[list[str]]   = ["tiny", "small", "medium", "large", "huge"]
SIZE_WEIGHTS:  Final[list[float]] = [0.15, 0.40, 0.30, 0.10, 0.05]

# ---------------------------------------------------------------------------
# Culture generation
# ---------------------------------------------------------------------------

CULTURE_GROUP_TEMPLATES: Final[list[dict[str, object]]] = [
    {
        "id": "afro_asian_core",
        "weight": 0.35,
        "name_patterns": ["{root}i", "{root}an", "{root}ite"],
        "regions": ["africa", "asia"],
    },
    {
        "id": "african_highland",
        "weight": 0.20,
        "name_patterns": ["{root}an", "{root}ese"],
        "regions": ["africa"],
    },
    {
        "id": "asian_coastal",
        "weight": 0.20,
        "name_patterns": ["{root}i", "{root}ese"],
        "regions": ["asia"],
    },
    {
        "id": "steppe_frontier",
        "weight": 0.15,
        "name_patterns": ["{root}ic", "{root}an"],
        "regions": ["frontier"],
    },
    {
        "id": "island_syncretic",
        "weight": 0.10,
        "name_patterns": ["{root}an", "{root}i"],
        "regions": ["islands"],
    },
]

CULTURE_ROOT_SYLLABLES: Final[list[str]] = [
    "Zar", "Kal", "Ash", "Nur", "Tal", "Mak", "Har", "Sah",
    "Yan", "Ras", "Bel", "Tor", "Kha", "Lum", "Var", "Jin",
]

# ---------------------------------------------------------------------------
# Mission archetypes (defined here so country.py can import before use)
# ---------------------------------------------------------------------------

MISSION_ARCHETYPES: Final[list[dict[str, object]]] = [
    {
        "id": "coastal_trade",
        "weight": 0.30,
        "theme": "trade",
        "effects": [
            "global_trade_power = 0.10",
            "trade_efficiency = 0.05",
        ],
    },
    {
        "id": "river_empire",
        "weight": 0.25,
        "theme": "development",
        "effects": [
            "production_efficiency = 0.10",
            "manpower_recovery_speed = 0.10",
        ],
    },
    {
        "id": "holy_syncretism",
        "weight": 0.20,
        "theme": "religion",
        "effects": [
            "tolerance_own = 2",
            "missionary_strength = 0.02",
        ],
    },
    {
        "id": "continental_unity",
        "weight": 0.25,
        "theme": "conquest",
        "effects": [
            "discipline = 0.03",
            "land_morale = 0.05",
        ],
    },
]

# ---------------------------------------------------------------------------
# Trade company regions (defined here so economy.py can stay thin)
# ---------------------------------------------------------------------------

TRADE_COMPANY_REGIONS: Final[list[dict[str, str]]] = [
    {"id": "afro_oceanic_company",  "name": "Afro-Oceanic Trade Company", "region": "africa"},
    {"id": "silk_sun_company",      "name": "Silk Sun Trade Company",     "region": "asia"},
    {"id": "island_spice_company",  "name": "Island Spice Company",       "region": "islands"},
]
