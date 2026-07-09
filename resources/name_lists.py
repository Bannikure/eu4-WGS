"""
Name List Provider for EU4 World Generator Studio
=====================================================
Loads culture-specific province and country names from the reference
name lists (borrowed from EUIV_Map_Generator_2.0), providing them
as callable data for the content generator modules.

Name lists available:
  - african_culture, cushitic_culture, west_african_culture, sahelian_culture
  - hindusthani_culture, dravidian_culture, central_indic_culture, eastern_aryan_culture
  - east_asian_culture, japanese_g_culture, korean_g_culture, thai_culture
  - british_culture, french_culture, germanic_culture, iberian_culture, latin_culture
  - altaic_culture, oghuz_culture, tartar_culture, turko_semitic_culture
  - and many more (69 culture files total)

Also provides country name lists and a merged "all names" list.
"""

import os
import random
from typing import Dict, List, Optional

# Path to the name list files
_NAME_LIST_DIR = os.path.join(os.path.dirname(__file__), "name_lists")

# Mapping from our continent names to culture name list files
CONTINENT_TO_CULTURE_FILES = {
    "west_africa": ["west_african_culture", "african_culture", "mande_culture", "sahelian_culture"],
    "east_africa": ["african_culture", "cushitic_culture", "sudanese_culture"],
    "south_asia": ["hindusthani_culture", "dravidian_culture", "central_indic_culture", "eastern_aryan_culture"],
    "middle_east": ["oghuz_culture", "turko_semitic_culture", "iranian_culture", "maghrebi_culture"],
    "mediterranean": ["latin_culture", "iberian_culture", "byzantine_culture", "french_culture"],
    "central_europe": ["germanic_culture", "west_slavic_culture", "magyar_culture", "baltic_culture"],
    "northern_europe": ["british_culture", "scandinavian_culture", "finno_ugric_culture", "gaelic_culture"],
    "east_asia": ["east_asian_culture", "japanese_g_culture", "korean_g_culture"],
    "southeast_asia": ["thai_culture", "mon_khmer_culture", "malay_culture", "burman_culture"],
    "central_asia": ["altaic_culture", "tartar_culture", "evenks_culture"],
    "north_america": ["iroquoian_culture", "muskogean_culture", "siouan_culture", "na_dene_culture"],
    "south_america": ["andean_group_culture", "araucanian_culture", "maya_culture", "central_american_culture"],
}

# Cache for loaded name lists
_name_cache: Dict[str, List[str]] = {}


def _load_name_file(filename: str) -> List[str]:
    """Load a name list file, returning a list of names."""
    if filename in _name_cache:
        return _name_cache[filename]

    fpath = os.path.join(_NAME_LIST_DIR, f"{filename}.txt")
    if not os.path.exists(fpath):
        _name_cache[filename] = []
        return []

    names = []
    try:
        with open(fpath, "r", encoding="utf-8-sig") as f:
            for line in f:
                name = line.strip()
                if name and not name.startswith("#"):
                    names.append(name)
    except Exception:
        names = []

    _name_cache[filename] = names
    return names


def get_names_for_continent(continent: str, count: int = 10,
                             seed: Optional[int] = None) -> List[str]:
    """
    Get random province names appropriate for a given continent.
    Draws from culture-specific name lists for realism.
    """
    if seed is not None:
        random.seed(seed)

    culture_files = CONTINENT_TO_CULTURE_FILES.get(continent, ["african_culture"])
    all_names = []
    for cf in culture_files:
        all_names.extend(_load_name_file(cf))

    if not all_names:
        # Fallback: load the merged all-names list
        all_names = _load_name_file("_all_names")

    if not all_names:
        # Ultimate fallback: generate placeholder names
        return [f"{continent.title()}_{i}" for i in range(count)]

    # Remove duplicates while preserving order
    seen = set()
    unique_names = []
    for n in all_names:
        if n not in seen:
            seen.add(n)
            unique_names.append(n)

    # Return random selection
    return random.sample(unique_names, min(count, len(unique_names)))


def get_country_names(count: int = 10, seed: Optional[int] = None) -> List[str]:
    """Get random country names from the country name list."""
    if seed is not None:
        random.seed(seed)

    names = _load_name_file("_country_names")
    if not names:
        return [f"Country_{i}" for i in range(count)]

    return random.sample(names, min(count, len(names)))


def get_culture_names(culture_key: str, count: int = 10,
                       seed: Optional[int] = None) -> List[str]:
    """Get province names for a specific culture key."""
    if seed is not None:
        random.seed(seed)

    names = _load_name_file(culture_key)
    if not names:
        return [f"{culture_key}_{i}" for i in range(count)]

    return random.sample(names, min(count, len(names)))


def list_available_cultures() -> List[str]:
    """List all available culture name list files."""
    result = []
    if os.path.isdir(_NAME_LIST_DIR):
        for f in sorted(os.listdir(_NAME_LIST_DIR)):
            if f.endswith(".txt") and not f.startswith("_"):
                result.append(f[:-4])  # Remove .txt extension
    return result


def get_all_names() -> List[str]:
    """Get the complete merged name list."""
    return _load_name_file("_all_names")


# Pre-load commonly used lists on module import
def warm_cache():
    """Pre-load commonly used name lists into cache."""
    for continent, files in CONTINENT_TO_CULTURE_FILES.items():
        for f in files:
            _load_name_file(f)
    _load_name_file("_all_names")
    _load_name_file("_country_names")


# Available culture list (for reference)
AVAILABLE_CULTURES = list_available_cultures()
