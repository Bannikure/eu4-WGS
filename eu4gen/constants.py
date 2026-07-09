# =========================================================================
# EU4 World Generator Studio - Constants & Configuration
# =========================================================================

import os
from pathlib import Path
from enum import Enum

# =========================================================================
# PATHS & DIRECTORIES
# =========================================================================

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ADDITIONAL_DATA_DIR = PROJECT_ROOT / "additional_data"
OUTPUT_DIR = PROJECT_ROOT / "output"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
EMBLEMS_DIR = PROJECT_ROOT / "emblems"

# Create directories if they don't exist
for directory in [DATA_DIR, ADDITIONAL_DATA_DIR, OUTPUT_DIR, TEMPLATES_DIR, EMBLEMS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# =========================================================================
# MAP & WORLD GENERATION
# =========================================================================

DEFAULT_MAP_WIDTH = 5632
DEFAULT_MAP_HEIGHT = 2048
PROVINCE_SIZE_MIN = 50  # Minimum province pixel area
PROVINCE_SIZE_MAX = 5000  # Maximum province pixel area

# Heightmap settings
HEIGHTMAP_SCALE = 255  # Standard grayscale range
WATER_LEVEL_THRESHOLD = 100  # Below this = water/sea
MOUNTAIN_THRESHOLD = 200  # Above this = mountain
PLAINS_THRESHOLD = 150

# =========================================================================
# PROVINCE GENERATION
# =========================================================================

class ProvinceType(Enum):
    LAND = "land"
    SEA = "sea"
    LAKE = "lake"
    COASTAL = "coastal"

# Province ID ranges
PROVINCE_ID_START = 1
PROVINCE_ID_LAND_MAX = 3000
PROVINCE_ID_SEA_START = 3001
PROVINCE_ID_SEA_MAX = 5000

# Province colors (RGB) for BMP generation
PROVINCE_COLOR_PALETTE = {
    "water": (0, 0, 255),      # Blue for water
    "impassable": (0, 0, 0),   # Black for impassable
    "wasteland": (100, 100, 100),  # Gray for wasteland
}

# =========================================================================
# TERRAIN & CLIMATE
# =========================================================================

class Terrain(Enum):
    GRASSLANDS = "grasslands"
    HILLS = "hills"
    MOUNTAINS = "mountains"
    DESERT = "desert"
    FOREST = "forest"
    STEPPE = "steppe"
    COASTAL = "coastal"
    OCEAN = "ocean"

TERRAIN_MODIFIERS = {
    Terrain.GRASSLANDS: {"supply": 2.0, "speed": 1.0},
    Terrain.HILLS: {"supply": 1.5, "speed": 0.8},
    Terrain.MOUNTAINS: {"supply": 1.0, "speed": 0.6},
    Terrain.DESERT: {"supply": 0.5, "speed": 0.7},
    Terrain.FOREST: {"supply": 1.0, "speed": 0.5},
    Terrain.STEPPE: {"supply": 1.0, "speed": 1.2},
}

# =========================================================================
# TRADE & ECONOMY
# =========================================================================

class TradeGood(Enum):
    GRAIN = "grain"
    WINE = "wine"
    WOOL = "wool"
    SILK = "silk"
    SPICES = "spices"
    COAL = "coal"
    IRON = "iron"
    COPPER = "copper"
    GOLD = "gold"
    SILVER = "silver"
    GEMS = "gems"
    SALT = "salt"
    TROPICAL_WOOD = "tropical_wood"
    FURS = "furs"
    FISH = "fish"
    NAVAL_SUPPLIES = "naval_supplies"
    LUMBER = "lumber"
    COPPER_ORE = "copper_ore"

TRADE_GOOD_PRICES = {
    TradeGood.GRAIN: 1.0,
    TradeGood.WINE: 1.5,
    TradeGood.WOOL: 1.3,
    TradeGood.SILK: 2.0,
    TradeGood.SPICES: 3.0,
    TradeGood.COAL: 1.2,
    TradeGood.IRON: 1.5,
    TradeGood.COPPER: 1.8,
    TradeGood.GOLD: 4.0,
    TradeGood.SILVER: 3.5,
    TradeGood.GEMS: 5.0,
    TradeGood.SALT: 1.1,
    TradeGood.TROPICAL_WOOD: 2.5,
    TradeGood.FURS: 2.0,
    TradeGood.FISH: 1.0,
    TradeGood.NAVAL_SUPPLIES: 2.5,
    TradeGood.LUMBER: 1.0,
    TradeGood.COPPER_ORE: 1.3,
}

# Trade node configuration
class TradeNode(Enum):
    PRODUCTION = "production"
    COLLECTION = "collection"
    TRANSIT = "transit"

# =========================================================================
# RELIGION & CULTURE
# =========================================================================

class Religion(Enum):
    CATHOLIC = "catholic"
    PROTESTANT = "protestant"
    ORTHODOX = "orthodox"
    SUNNI = "sunni"
    SHIA = "shia"
    IBADI = "ibadi"
    HINDU = "hindu"
    BUDDHIST = "buddhist"
    CONFUCIAN = "confucian"
    SHINTO = "shinto"
    ANIMIST = "animist"
    FETISHIST = "fetishist"
    JEWISH = "jewish"
    ZOROASTRIAN = "zoroastrian"

RELIGION_COLORS = {
    Religion.CATHOLIC: "#C00000",
    Religion.PROTESTANT: "#0000FF",
    Religion.ORTHODOX: "#FFFF00",
    Religion.SUNNI: "#00AA00",
    Religion.SHIA: "#FF6600",
    Religion.IBADI: "#FFAA00",
    Religion.HINDU: "#FF00FF",
    Religion.BUDDHIST: "#FF6600",
    Religion.CONFUCIAN: "#00FFFF",
    Religion.SHINTO: "#FF99FF",
    Religion.ANIMIST: "#999999",
    Religion.FETISHIST: "#666666",
    Religion.JEWISH: "#0099FF",
    Religion.ZOROASTRIAN: "#CCAA00",
}

class Culture(Enum):
    LATIN = "latin"
    GERMANIC = "germanic"
    FRENCH = "french"
    IBERIAN = "iberian"
    ITALIAN = "italian"
    BRITISH = "british"
    SCANDINAVIAN = "scandinavian"
    GREEK = "greek"
    BALKAN = "balkan"
    SLAVIC = "slavic"
    TURKISH = "turkish"
    PERSIAN = "persian"
    ARABIC = "arabic"
    CHINESE = "chinese"
    JAPANESE = "japanese"
    INDIAN = "indian"

# =========================================================================
# GOVERNMENT & POLITICAL SYSTEMS
# =========================================================================

class GovernmentType(Enum):
    MONARCHY = "monarchy"
    REPUBLIC = "republic"
    THEOCRACY = "theocracy"
    TRIBAL = "tribal"
    NATIVE_COUNCIL = "native_council"
    ELECTIVE_MONARCHY = "elective_monarchy"
    OLIGARCHIC_REPUBLIC = "oligarchic_republic"
    MERCHANT_REPUBLIC = "merchant_republic"

class GovernmentRank(Enum):
    DUCHY = 1
    KINGDOM = 2
    EMPIRE = 3

# =========================================================================
# MILITARY
# =========================================================================

class UnitType(Enum):
    INFANTRY = "infantry"
    CAVALRY = "cavalry"
    ARTILLERY = "artillery"
    GALLEY = "galley"
    HEAVY_SHIP = "heavy_ship"
    LIGHT_SHIP = "light_ship"
    TRANSPORT = "transport"

UNIT_COSTS = {
    UnitType.INFANTRY: {"gold": 50, "manpower": 0.5},
    UnitType.CAVALRY: {"gold": 100, "manpower": 0.3},
    UnitType.ARTILLERY: {"gold": 150, "manpower": 0.1},
    UnitType.GALLEY: {"gold": 200, "manpower": 0.8},
    UnitType.HEAVY_SHIP: {"gold": 300, "manpower": 1.0},
    UnitType.LIGHT_SHIP: {"gold": 250, "manpower": 0.7},
    UnitType.TRANSPORT: {"gold": 180, "manpower": 0.6},
}

# =========================================================================
# DEVELOPMENT & ECONOMY
# =========================================================================

DEVELOPMENT_MIN = 1
DEVELOPMENT_MAX = 40
DEVELOPMENT_BASE = 5

# Development categories and their modifiers
DEVELOPMENT_MODIFIERS = {
    "production": 0.33,
    "trade": 0.33,
    "tax": 0.34,
}

# =========================================================================
# NATION & COUNTRY GENERATION
# =========================================================================

class NationTier(Enum):
    VILLAGE = 1
    TOWN = 2
    CITY = 3
    METROPOLIS = 4

# Nation generation parameters
NATION_GEN_CONFIG = {
    "min_provinces": 1,
    "max_provinces": 50,
    "min_development": 5,
    "max_development": 100,
    "population_per_dev": 10000,
}

# =========================================================================
# SCRIPTING & FILE FORMATS
# =========================================================================

# EU4 Script file extensions
EU4_SCRIPT_EXTENSIONS = [
    ".txt",      # Main script files
    ".csv",      # Data files (trade goods, religions, etc.)
    ".gfx",      # Graphics definitions
    ".fxh",      # Shader files
    ".yml",      # Localization files
]

# Common EU4 data folders
EU4_DATA_FOLDERS = [
    "common/countries",
    "common/country_colors",
    "common/governments",
    "common/government_ranks",
    "common/government_reforms",
    "common/religions",
    "common/cultures",
    "common/trade_companies",
    "common/tradegoods",
    "common/trading_companies",
    "history/countries",
    "history/diplomacy",
    "history/provinces",
    "history/wars",
    "map/terrain",
    "map/climate",
    "map/positions",
    "map/regions",
    "localisation",
    "events",
    "missions",
]

# =========================================================================
# LOCALIZATION
# =========================================================================

LOCAL_LANGUAGE_CODES = {
    "english": "l_english",
    "french": "l_french",
    "german": "l_german",
    "spanish": "l_spanish",
    "italian": "l_italian",
    "portuguese": "l_portuguese",
    "russian": "l_russian",
    "polish": "l_polish",
    "turkish": "l_turkish",
    "japanese": "l_japanese",
    "chinese": "l_simp_chinese",
}

# =========================================================================
# VISUAL & UI SETTINGS
# =========================================================================

# Default UI colors and styling
UI_COLORS = {
    "primary": "#1e1e1e",
    "secondary": "#2d2d2d",
    "accent": "#007acc",
    "success": "#4ec9b0",
    "warning": "#dcdcaa",
    "error": "#f48771",
    "text": "#d4d4d4",
}

# =========================================================================
# VALIDATION RULES
# =========================================================================

VALIDATION_RULES = {
    "province_name_max_length": 100,
    "country_name_max_length": 50,
    "max_countries": 500,
    "max_provinces": 5000,
    "min_trade_goods_variety": 0.3,  # At least 30% variety
}

# =========================================================================
# PERFORMANCE & OPTIMIZATION
# =========================================================================

# Caching settings
CACHE_ENABLED = True
CACHE_DIR = PROJECT_ROOT / ".cache"
CACHE_EXPIRY_SECONDS = 3600  # 1 hour

# Multithreading
MAX_WORKERS = 4  # Number of parallel workers
CHUNK_SIZE = 256  # Process maps in chunks

# =========================================================================
# EXTERNAL DATA FORMATS
# =========================================================================

SUPPORTED_FORMATS = {
    "xml": [".xml"],
    "json": [".json"],
    "csv": [".csv"],
    "dll": [".dll"],
    "txt": [".txt"],
    "lua": [".lua"],
    "binary": [".dat", ".bin"],
}
