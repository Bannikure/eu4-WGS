"""
Extended Timeline Compatibility Module
=======================================
Provides complete compatibility with the EU4 Extended Timeline mod,
which extends the game timeline from 58 AD to 2026 AD with numerous
historical bookmarks.

Key features:
1. Date-scoped province history generation (multiple era blocks per province)
2. Date-scoped country history generation (monarchs/events at various dates)
3. Extended Timeline bookmark definitions for all 27+ start dates
4. Technology group generation compatible with ET's extended tech system
5. .mod file with dependencies on Extended Timeline
6. Religion file adaptations for ET mechanics
7. Idea file adaptations for extended date ranges
8. Localisation compatible with ET's date references
9. Adjacency generation for tunnel connections across eras

Extended Timeline Start Dates (bookmarks):
  - 58 AD: Roman-Parthian War
  - 224 AD: Rise of Sassanids
  - 395 AD: Barbarian Invasions
  - 476 AD: Fall of Rome
  - 527 AD: Justinian
  - 637 AD: Rise of Islam
  - 769 AD: Charlemagne
  - 867 AD: Old Gods
  - 936 AD: Iron Century
  - 962 AD: HRE
  - 1066 AD: Stamford Bridge
  - 1187 AD: Third Crusade
  - 1206 AD: Mongol Empire
  - 1241 AD: Mongol Invasion
  - 1337 AD: Hundred Years War
  - 1399 AD: Grand Campaign
  - 1444 AD: Rise of Ottomans
  - 1453 AD: Fall of Byzantium
  - 1492 AD: New World
  - 1508 AD: League of Cambrai
  - 1579 AD: Eighty Years War
  - 1618 AD: Thirty Years War
  - 1701 AD: Spanish Succession
  - 1718 AD: Quadruple Alliance
  - 1756 AD: Seven Years War
  - 1776 AD: American Independence
  - 1789 AD: French Revolution
  - 1792 AD: Revolutionary France
  - 1836 AD: Victorian Era
  - 1861 AD: American Civil War
  - 1870 AD: Franco-Prussian War
  - 1914 AD: WWI
  - 1939 AD: WWII
  - 1947 AD: Cold War
  - 1991 AD: Fall of USSR
  - 2026 AD: Present Day
"""

import os
import random
import copy
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field

from eu4_wgs_v8.common.io_utils import ensure_dir, write_text


# ═══════════════════════════════════════════════════════════════════════
#  EXTENDED TIMELINE BOOKMARK DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ETBookmark:
    """A single Extended Timeline bookmark/start date."""
    date: str           # EU4 date format: Year.Month.Day
    name_key: str       # Localisation key
    desc_key: str       # Localisation description key
    era: str            # Era classification: ancient, medieval, early_modern, modern, contemporary
    featured_countries: List[str] = field(default_factory=list)  # Tags to feature
    easy_countries: List[str] = field(default_factory=list)      # Recommended for new players


# All Extended Timeline bookmarks with inverted-world flavor
ET_BOOKMARKS = [
    ETBookmark("58.2.1", "ET_58_NAME", "ET_58_DESC", "ancient",
               ["BHA", "ABY"], ["BHA"]),
    ETBookmark("224.1.1", "ET_224_NAME", "ET_224_DESC", "ancient",
               ["MLI", "SGH"], ["MLI"]),
    ETBookmark("395.1.1", "ET_395_NAME", "ET_395_DESC", "ancient",
               ["HIN", "KMR"], ["HIN"]),
    ETBookmark("476.1.1", "ET_476_NAME", "ET_476_DESC", "ancient",
               ["GZW", "ABY"], ["GZW"]),
    ETBookmark("527.1.1", "ET_527_NAME", "ET_527_DESC", "ancient",
               ["BHA", "MPH"], ["BHA"]),
    ETBookmark("637.1.1", "ET_637_NAME", "ET_637_DESC", "ancient",
               ["MLI", "KMR"], ["MLI"]),
    ETBookmark("769.1.1", "ET_769_NAME", "ET_769_DESC", "medieval",
               ["HIN", "SGH"], ["HIN"]),
    ETBookmark("867.1.1", "ET_867_NAME", "ET_867_DESC", "medieval",
               ["BHA", "ABY"], ["BHA"]),
    ETBookmark("936.1.1", "ET_936_NAME", "ET_936_DESC", "medieval",
               ["MLI", "MPH"], ["MLI"]),
    ETBookmark("962.1.1", "ET_962_NAME", "ET_962_DESC", "medieval",
               ["GZW", "KMR"], ["GZW"]),
    ETBookmark("1066.1.1", "ET_1066_NAME", "ET_1066_DESC", "medieval",
               ["HIN", "ABY"], ["HIN"]),
    ETBookmark("1187.1.1", "ET_1187_NAME", "ET_1187_DESC", "medieval",
               ["BHA", "SGH"], ["BHA"]),
    ETBookmark("1206.1.1", "ET_1206_NAME", "ET_1206_DESC", "medieval",
               ["MPH", "MLI"], ["MPH"]),
    ETBookmark("1241.1.1", "ET_1241_NAME", "ET_1241_DESC", "medieval",
               ["KMR", "GZW"], ["KMR"]),
    ETBookmark("1337.1.1", "ET_1337_NAME", "ET_1337_DESC", "late_medieval",
               ["HIN", "ABY"], ["HIN"]),
    ETBookmark("1399.1.1", "ET_1399_NAME", "ET_1399_DESC", "late_medieval",
               ["BHA", "MLI"], ["BHA"]),
    ETBookmark("1444.11.11", "ET_1444_NAME", "ET_1444_DESC", "early_modern",
               ["HIN", "SGH", "MPH"], ["HIN"]),
    ETBookmark("1453.1.1", "ET_1453_NAME", "ET_1453_DESC", "early_modern",
               ["BHA", "KMR"], ["BHA"]),
    ETBookmark("1492.1.1", "ET_1492_NAME", "ET_1492_DESC", "early_modern",
               ["MLI", "ABY", "GZW"], ["MLI"]),
    ETBookmark("1508.1.1", "ET_1508_NAME", "ET_1508_DESC", "early_modern",
               ["HIN", "MPH"], ["HIN"]),
    ETBookmark("1579.1.1", "ET_1579_NAME", "ET_1579_DESC", "early_modern",
               ["BHA", "SGH"], ["BHA"]),
    ETBookmark("1618.1.1", "ET_1618_NAME", "ET_1618_DESC", "early_modern",
               ["KMR", "MLI"], ["KMR"]),
    ETBookmark("1701.1.1", "ET_1701_NAME", "ET_1701_DESC", "early_modern",
               ["HIN", "ABY"], ["HIN"]),
    ETBookmark("1718.1.1", "ET_1718_NAME", "ET_1718_DESC", "early_modern",
               ["MPH", "GZW"], ["MPH"]),
    ETBookmark("1756.1.1", "ET_1756_NAME", "ET_1756_DESC", "early_modern",
               ["BHA", "SGH"], ["BHA"]),
    ETBookmark("1776.7.4", "ET_1776_NAME", "ET_1776_DESC", "modern",
               ["MLI", "KMR"], ["MLI"]),
    ETBookmark("1789.7.14", "ET_1789_NAME", "ET_1789_DESC", "modern",
               ["HIN", "ABY"], ["HIN"]),
    ETBookmark("1792.1.1", "ET_1792_NAME", "ET_1792_DESC", "modern",
               ["BHA", "MPH"], ["BHA"]),
    ETBookmark("1836.1.1", "ET_1836_NAME", "ET_1836_DESC", "modern",
               ["SGH", "GZW"], ["SGH"]),
    ETBookmark("1861.1.1", "ET_1861_NAME", "ET_1861_DESC", "modern",
               ["MLI", "KMR"], ["MLI"]),
    ETBookmark("1870.1.1", "ET_1870_NAME", "ET_1870_DESC", "modern",
               ["HIN", "ABY"], ["HIN"]),
    ETBookmark("1914.7.28", "ET_1914_NAME", "ET_1914_DESC", "contemporary",
               ["BHA", "MPH"], ["BHA"]),
    ETBookmark("1939.9.1", "ET_1939_NAME", "ET_1939_DESC", "contemporary",
               ["SGH", "MLI"], ["SGH"]),
    ETBookmark("1947.1.1", "ET_1947_NAME", "ET_1947_DESC", "contemporary",
               ["HIN", "KMR"], ["HIN"]),
    ETBookmark("1991.12.26", "ET_1991_NAME", "ET_1991_DESC", "contemporary",
               ["BHA", "ABY"], ["BHA"]),
    ETBookmark("2026.1.1", "ET_2026_NAME", "ET_2026_DESC", "contemporary",
               ["HIN", "MPH", "GZW"], ["HIN"]),
]


# ═══════════════════════════════════════════════════════════════════════
#  ERA-SPECIFIC CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

# Era definitions for the inverted world
# Ancient = African/Asian empires at their founding
# Medieval = Hindu golden age, European dark age
# Early Modern = Asian/African renaissance, European stagnation
# Modern = Asian/African industrial revolution, European feudalism
# Contemporary = Asian/African global dominance, European collapse

ERA_CONFIG = {
    "ancient": {
        "tech_level_offset": -8,      # Ancient era has very low tech
        "development_modifier": 0.4,  # Provinces are less developed
        "institution_count": 0,       # No institutions yet
        "government_types": ["tribal", "despotic_monarchy", "elective_monarchy"],
        "advanced_gov": "despotic_monarchy",
        "primitive_gov": "tribal",
    },
    "medieval": {
        "tech_level_offset": -5,
        "development_modifier": 0.6,
        "institution_count": 1,
        "government_types": ["feudal_monarchy", "despotic_monarchy", "monarchy"],
        "advanced_gov": "feudal_monarchy",
        "primitive_gov": "tribal",
    },
    "late_medieval": {
        "tech_level_offset": -3,
        "development_modifier": 0.75,
        "institution_count": 2,
        "government_types": ["feudal_monarchy", "monarchy", "elective_monarchy"],
        "advanced_gov": "monarchy",
        "primitive_gov": "feudal_monarchy",
    },
    "early_modern": {
        "tech_level_offset": 0,       # 1444 is the base
        "development_modifier": 1.0,
        "institution_count": 3,
        "government_types": ["monarchy", "administrative_monarchy", "republic"],
        "advanced_gov": "administrative_monarchy",
        "primitive_gov": "feudal_monarchy",
    },
    "modern": {
        "tech_level_offset": 8,
        "development_modifier": 1.5,
        "institution_count": 5,
        "government_types": ["constitutional_monarchy", "republic", "parliamentary_republic"],
        "advanced_gov": "parliamentary_republic",
        "primitive_gov": "absolute_monarchy",
    },
    "contemporary": {
        "tech_level_offset": 18,
        "development_modifier": 2.5,
        "institution_count": 7,
        "government_types": ["parliamentary_republic", "republic", "constitutional_monarchy"],
        "advanced_gov": "parliamentary_republic",
        "primitive_gov": "absolute_monarchy",
    },
}


# ═══════════════════════════════════════════════════════════════════════
#  NAME GENERATORS FOR DIFFERENT ERAS
# ═══════════════════════════════════════════════════════════════════════

# Ruler names by era for advanced (African/Asian) nations
ADVANCED_RULER_NAMES = {
    "ancient": [
        "Ashoka", "Chandragupta", "Sundiata", "Ezana", "Rajaraja",
        "Wangara", "Makeda", "Shaka", "Gudea", "Narmer",
        "Khosrow", "Harsha", "Devapala", "Sambar", "Dhurandhar"
    ],
    "medieval": [
        "Rajendra", "Krishnadeva", "Mansa Musa", "Lalibela", "Prithviraj",
        "Amda Seyon", "Gajah Mada", "Hayam Wuruk", "Sonni Ali", "Bhaskara",
        "Vikramaditya", "Deva Raya", "Aksum", "Zawisza"
    ],
    "late_medieval": [
        "Vijaya", "Askia", "Suleiman", "Mahmud", "Chaitanya",
        "Bayinnaung", "Kilwa", "Afonso", "Nzinga", "Cetshwayo"
    ],
    "early_modern": [
        "Shivaji", "Haile Selassie", "Aurangzeb", "Sultan Agung",
        "Ewuare", "Nzingha", "Tippu Tip", "Ranjit Singh", "Tiradentes"
    ],
    "modern": [
        "Gandhi", "Nkrumah", "Nehru", "Sukarno", "Nyerere",
        "Kenya", "Amani", "Patel", "Bandaranaike", "Mandela"
    ],
    "contemporary": [
        "Modi", "Ramaphosa", "Widodo", "Kenyatta", "Hasina",
        "Solih", "Kagame", "Singh", "Mahathir", "Zenawi"
    ],
}

# Ruler names by era for primitive (European) nations
PRIMITIVE_RULER_NAMES = {
    "ancient": [
        "Alaric", "Gundahar", "Theodoric", "Clovis", "Odoacer",
        "Euric", "Gaiseric", "Fritigern", "Radagaisus", "Ataulf"
    ],
    "medieval": [
        "Charles", "Louis", "Henry", "William", "Otto",
        "Robert", "Philip", "Richard", "Frederick", "Alfonso"
    ],
    "late_medieval": [
        "Edward", "Francis", "James", "Henry", "Charles",
        "Ferdinand", "Ladislaus", "Sigismund", "John", "Albert"
    ],
    "early_modern": [
        "Franz", "Friedrich", "Gustav", "Karl", "Wilhelm",
        "Leopold", "August", "Christian", "Ivan", "Vlad"
    ],
    "modern": [
        "Nikolai", "Heinrich", "Giuseppe", "Willem", "Leopold",
        "Alexander", "Franz", "Ottokar", "Rudolf", "Albrecht"
    ],
    "contemporary": [
        "Hans", "Pierre", "Ivan", "Klaus", "Stefan",
        "Heinrich", "Mikhail", "Jan", "Piotr", "Dietrich"
    ],
}

# Dynasty names by era for advanced nations
ADVANCED_DYNASTY_NAMES = {
    "ancient": ["Maurya", "Gupta", "Solomonic", "Aksumite", "Chola", "Funan"],
    "medieval": ["Vijayanagara", "Malian", "Songhai", "Khmer", "Majapahit", "Zagwe"],
    "late_medieval": ["Mughal", "Safavid", "Kilwa", "Benin", "Ayutthaya", "Mutapa"],
    "early_modern": ["Maratha", "Oyo", "Sikh", "Mataram", "Kongo", "Ethiopian"],
    "modern": ["Indian", "African", "Javanese", "Ethiopian", "Korean", "Thai"],
    "contemporary": ["Republic", "Union", "Federation", "Commonwealth", "Alliance", "Directorate"],
}

# Dynasty names by era for primitive nations
PRIMITIVE_DYNASTY_NAMES = {
    "ancient": ["Visigoth", "Vandal", "Ostrogoth", "Lombard", "Frank", "Saxon"],
    "medieval": ["Capet", "Habsburg", "Plantagenet", "Hohenzollern", "Wittelsbach", "Valois"],
    "late_medieval": ["Habsburg", "Trastamara", "York", "Lancaster", "Jagiellon", "Vasa"],
    "early_modern": ["Habsburg", "Bourbon", "Romanov", "Hohenzollern", "Stuart", "Orange"],
    "modern": ["Romanov", "Hohenzollern", "Habsburg", "Bourbon", "Saxe", "Windsor"],
    "contemporary": ["Schmidt", "Dupont", "Rossi", "Weber", "Novak", "O'Brien"],
}


# ═══════════════════════════════════════════════════════════════════════
#  EXTENDED TIMELINE BOOKMARK EXPORTER
# ═══════════════════════════════════════════════════════════════════════

class ETBookmarkExporter:
    """Generates bookmark files for all Extended Timeline start dates."""

    @staticmethod
    def generate_bookmarks(output_dir: str,
                           advanced_tags: List[str] = None,
                           primitive_tags: List[str] = None,
                           hindu_tags: List[str] = None) -> str:
        """
        Generate the bookmarks.txt file for Extended Timeline compatibility.
        Creates one bookmark per Extended Timeline start date, each with
        appropriate countries featured based on the inverted world theme.
        """
        ensure_dir(output_dir)

        advanced = advanced_tags or ["BHA", "HIN", "ABY", "MLI", "GZW", "MPH", "SGH", "KMR"]
        primitive = primitive_tags or []
        hindu = hindu_tags or ["BHA", "HIN", "KMR", "MPH"]

        lines = []
        for bm in ET_BOOKMARKS:
            # Determine featured countries for this bookmark
            featured = bm.featured_countries
            if not featured:
                # Default: feature advanced African/Asian countries
                featured = advanced[:3]

            easy = bm.easy_countries
            if not easy:
                easy = featured[:1]

            lines.extend([
                "bookmark = {",
                f'\tname = "{bm.name_key}"',
                f'\tdesc = "{bm.desc_key}"',
                f"\tdate = {bm.date}",
                f'\tera = "{bm.era}_era"',
            ])

            # Add featured countries
            for tag in featured:
                lines.append(f"\tcountry = {tag}")

            # Add easy countries
            for tag in easy:
                lines.append(f"\teasy_country = {tag}")

            lines.extend([
                "}",
                "",
            ])

        content = "\n".join(lines)
        return write_text(os.path.join(output_dir, "extended_timeline_bookmarks.txt"), content)

    @staticmethod
    def generate_bookmark_localisation(output_dir: str) -> str:
        """Generate localisation for all Extended Timeline bookmarks."""
        ensure_dir(output_dir)

        lines = ["l_english:", ""]

        for bm in ET_BOOKMARKS:
            year = bm.date.split(".")[0]
            name_text = _generate_bookmark_name(bm)
            desc_text = _generate_bookmark_desc(bm)
            lines.extend([
                f' {bm.name_key}:0 "{name_text}"',
                f' {bm.desc_key}:0 "{desc_text}"',
                "",
            ])

        content = "\n".join(lines)
        return write_text(
            os.path.join(output_dir, "extended_timeline_bookmarks_l_english.yml"),
            content, encoding="utf-8-sig",
        )


def _generate_bookmark_name(bm: ETBookmark) -> str:
    """Generate a descriptive bookmark name for the inverted world."""
    year = bm.date.split(".")[0]
    era_names = {
        "ancient": f"The Ancient Empires ({year} AD)",
        "medieval": f"The Hindu Golden Age ({year} AD)",
        "late_medieval": f"Dawn of the Advanced World ({year} AD)",
        "early_modern": f"The Great Renaissance ({year} AD)",
        "modern": f"The Age of Supremacy ({year} AD)",
        "contemporary": f"The World Ascendant ({year} AD)",
    }
    return era_names.get(bm.era, f"Inverted World ({year} AD)")


def _generate_bookmark_desc(bm: ETBookmark) -> str:
    """Generate a descriptive bookmark description for the inverted world."""
    year = bm.date.split(".")[0]
    era_descs = {
        "ancient": (f"In the year {year}, the great empires of Africa and Asia "
                    "rise to dominate the world. While European tribes struggle "
                    "in barbarism, the sons of the Sun and the Dharma build "
                    "civilizations that will endure for millennia."),
        "medieval": (f"The year is {year}. The Hindu golden age illuminates "
                     "the world while Europe wallows in squalor. The Celestial "
                     "Directorate guides the faithful, and the light of "
                     "learning shines only from the East and the South."),
        "late_medieval": (f"In {year}, the advanced nations of Africa and Asia "
                         "stand at the threshold of a new era. The ancient "
                         "empires consolidate their power while the primitive "
                         "European kingdoms remain mired in feudal backwardness."),
        "early_modern": (f"The year {year} marks the height of Afro-Asian "
                        "civilization. Great empires span continents, the Hindu "
                        "faith dominates the world, and the Celestial Directorate "
                        "wields authority over half the known world. Europe "
                        "remains a backwater of squabbling warlords."),
        "modern": (f"In {year}, the industrial might of Africa and Asia reshapes "
                   "the world. The primitive European states can only watch as "
                   "the true centers of power dictate the course of history."),
        "contemporary": (f"The world of {year} is one where the ancient "
                        "civilizations have achieved total supremacy. Africa "
                        "and Asia lead humanity into the future while Europe "
                        "struggles to emerge from centuries of stagnation."),
    }
    return era_descs.get(bm.era, f"The inverted world in {year} AD.")


# ═══════════════════════════════════════════════════════════════════════
#  EXTENDED TIMELINE PROVINCE HISTORY EXPORTER
# ═══════════════════════════════════════════════════════════════════════

class ETProvinceHistoryExporter:
    """
    Generates date-scoped province history files compatible with
    the Extended Timeline mod. Each province gets multiple date blocks
    reflecting ownership, religion, and culture changes across eras.
    """

    @staticmethod
    def generate_date_scoped_province_history(province, owner_tag: str,
                                               is_advanced: bool,
                                               continent: str,
                                               map_height: int = 2048) -> str:
        """
        Generate a province history file with entries for multiple eras.
        This allows the province to change hands, religion, and development
        across the Extended Timeline's date range.
        """
        province_name = f"Province_{province.id}"
        y = province.center_y

        # Base development and religion depend on continent
        from eu4_wgs_v8.analytics.heightmap_analyzer import HeightmapAnalyzer
        analyzer = HeightmapAnalyzer()
        base_dev = analyzer._compute_inverted_development(province)
        base_religion = analyzer._assign_inverted_religion(province)

        # Culture assignment
        from eu4_wgs_v8.content.world_content import CultureGenerator
        culture = CultureGenerator.get_culture_for_continent(continent)

        # Trade good
        trade_good = ETProvinceHistoryExporter._assign_trade_good(province, base_dev, is_advanced)

        # Build date-scoped entries
        lines = [f"# {province.id} - {province_name}", ""]

        # Base stats (always present, no date scope = defaults before any date block)
        lines.extend([
            f"base_tax = {max(1, base_dev // 3)}",
            f"base_production = {max(1, base_dev // 3)}",
            f"base_manpower = {max(1, base_dev - 2 * (base_dev // 3))}",
            f"trade_goods = {trade_good}",
            f"culture = {culture}",
            f"religion = {base_religion}",
            f'capital = "{province_name}"',
            "",
        ])

        # Generate date blocks for key era transitions
        # Each block shows how the province changes at the start of that era
        era_dates = [
            ("58.1.1", "ancient"),
            ("769.1.1", "medieval"),
            ("1066.1.1", "medieval"),
            ("1337.1.1", "late_medieval"),
            ("1444.11.11", "early_modern"),
            ("1618.1.1", "early_modern"),
            ("1836.1.1", "modern"),
            ("1914.1.1", "contemporary"),
            ("2026.1.1", "contemporary"),
        ]

        for date_str, era in era_dates:
            era_config = ERA_CONFIG.get(era, ERA_CONFIG["early_modern"])
            dev_mod = era_config["development_modifier"]

            # Scale development by era
            era_dev = max(1, int(base_dev * dev_mod))
            era_tax = max(1, era_dev // 3)
            era_prod = max(1, era_dev // 3)
            era_man = max(1, era_dev - era_tax - era_prod)

            # Religion may shift in earlier eras (pre-Hindu)
            if era == "ancient" and base_religion == "hindu":
                era_religion = "animism"  # Hindu dominance comes later
            else:
                era_religion = base_religion

            # Ownership changes
            era_owner = ETProvinceHistoryExporter._get_era_owner(
                owner_tag, is_advanced, era, continent
            )

            # Discovered_by based on era
            if era in ("ancient", "medieval"):
                discovered = "east_african"
            else:
                discovered = "indian"

            lines.extend([
                f"{date_str} = {{",
                f"\towner = {era_owner}",
                f"\tcontroller = {era_owner}",
                f"\tadd_core = {era_owner}",
                f"\tdiscovered_by = {discovered}",
            ])

            # Add development changes for significant era transitions
            if era != "early_modern":  # Base stats already cover early_modern
                lines.extend([
                    f"\tbase_tax = {era_tax}",
                    f"\tbase_production = {era_prod}",
                    f"\tbase_manpower = {era_man}",
                ])

            # Religion changes for ancient era
            if era == "ancient" and era_religion != base_religion:
                lines.append(f"\treligion = {era_religion}")

            lines.extend([
                "}",
                "",
            ])

        return "\n".join(lines)

    @staticmethod
    def _get_era_owner(base_owner: str, is_advanced: bool,
                        era: str, continent: str) -> str:
        """Determine province owner at a given era."""
        # Advanced nations maintain continuity; primitive nations may fragment
        if is_advanced:
            return base_owner
        else:
            # Primitive European nations may change ownership frequently
            if era in ("ancient", "medieval"):
                # In ancient/medieval eras, even Europe might be tribal
                return base_owner
            return base_owner

    @staticmethod
    def _assign_trade_good(province, development: int, is_advanced: bool) -> str:
        """Assign trade good based on province characteristics."""
        if is_advanced:
            rich_goods = ["spices", "silk", "incense", "ivory", "gems",
                          "cloth", "gold", "copper", "iron", "tea",
                          "coffee", "sugar", "tropical_wood", "dyes",
                          "saltpeter", "glass", "porcelain"]
            return random.choice(rich_goods)
        else:
            poor_goods = ["grain", "fish", "wool", "naval_supplies",
                          "salt", "livestock", "timber", "iron", "copper"]
            return random.choice(poor_goods)

    @staticmethod
    def write_province_history(province, owner_tag: str,
                                is_advanced: bool,
                                continent: str,
                                output_dir: str,
                                map_height: int = 2048) -> str:
        """Write a date-scoped province history file."""
        ensure_dir(output_dir)

        content = ETProvinceHistoryExporter.generate_date_scoped_province_history(
            province, owner_tag, is_advanced, continent, map_height
        )

        province_name = f"Province_{province.id}"
        filename = f"{province.id} - {province_name}.txt"
        return write_text(os.path.join(output_dir, filename), content)


# ═══════════════════════════════════════════════════════════════════════
#  EXTENDED TIMELINE COUNTRY HISTORY EXPORTER
# ═══════════════════════════════════════════════════════════════════════

class ETCountryHistoryExporter:
    """
    Generates date-scoped country history files compatible with
    the Extended Timeline mod. Each country gets monarchs and events
    at various historical dates across the timeline.
    """

    @staticmethod
    def generate_date_scoped_country_history(tag: str, country_data,
                                              is_advanced: bool) -> str:
        """
        Generate a country history file with monarchs for multiple eras.
        In the Extended Timeline, countries need rulers at each start date.
        """
        rng = random.Random(hash(tag))

        # Base government and culture
        government = country_data.government
        tech_group = country_data.tech_group
        primary_culture = country_data.primary_culture
        religion = country_data.religion

        lines = [
            f"# History for {country_data.short_name} ({tag})",
            f"# Extended Timeline Compatible - Multiple Era Rulers",
            "",
            f"government = {government}",
            f"technology_group = {tech_group}",
            "",
            f"primary_culture = {primary_culture}",
            f"religion = {religion}",
            f"mercantilism = {50 if is_advanced else 5}",
            "",
        ]

        # Generate institution progress based on tech group
        inst_count = 3 if is_advanced else 1
        inst_values = [1 if i < inst_count else 0 for i in range(8)]
        inst_str = "\n".join(
            f"\t{inst_values[i]} # Institution {i+1}"
            for i in range(8)
        )
        lines.extend([
            "embraced_institutions = {",
            inst_str,
            "}",
            "",
        ])

        # Generate rulers for each era transition date
        era_dates = [
            ("58.1.1", "ancient"),
            ("224.1.1", "ancient"),
            ("527.1.1", "ancient"),
            ("769.1.1", "medieval"),
            ("867.1.1", "medieval"),
            ("1066.1.1", "medieval"),
            ("1187.1.1", "medieval"),
            ("1337.1.1", "late_medieval"),
            ("1444.11.11", "early_modern"),
            ("1492.1.1", "early_modern"),
            ("1579.1.1", "early_modern"),
            ("1618.1.1", "early_modern"),
            ("1701.1.1", "early_modern"),
            ("1756.1.1", "early_modern"),
            ("1789.7.14", "modern"),
            ("1836.1.1", "modern"),
            ("1861.1.1", "modern"),
            ("1914.7.28", "contemporary"),
            ("1939.9.1", "contemporary"),
            ("1947.1.1", "contemporary"),
            ("1991.12.26", "contemporary"),
            ("2026.1.1", "contemporary"),
        ]

        # Select dynasty name based on advancement
        if is_advanced:
            dynasty_pool = list(set(
                ADVANCED_DYNASTY_NAMES.get("ancient", []) +
                ADVANCED_DYNASTY_NAMES.get("medieval", []) +
                ADVANCED_DYNASTY_NAMES.get("early_modern", [])
            ))
        else:
            dynasty_pool = list(set(
                PRIMITIVE_DYNASTY_NAMES.get("ancient", []) +
                PRIMITIVE_DYNASTY_NAMES.get("medieval", []) +
                PRIMITIVE_DYNASTY_NAMES.get("early_modern", [])
            ))

        if not dynasty_pool:
            dynasty_pool = ["Unknown"]

        dynasty = rng.choice(dynasty_pool)

        for date_str, era in era_dates:
            # Generate a monarch for this era
            name_pool = ADVANCED_RULER_NAMES.get(era, ["Ruler"]) if is_advanced else PRIMITIVE_RULER_NAMES.get(era, ["Chieftain"])
            name = rng.choice(name_pool)

            # Advanced nations get better monarch stats
            if is_advanced:
                adm = rng.randint(3, 6)
                dip = rng.randint(3, 6)
                mil = rng.randint(3, 6)
            else:
                adm = rng.randint(0, 3)
                dip = rng.randint(0, 3)
                mil = rng.randint(1, 4)

            age = rng.randint(25, 55)

            # Government may change by era
            era_config = ERA_CONFIG.get(era, ERA_CONFIG["early_modern"])
            era_gov = era_config["advanced_gov"] if is_advanced else era_config["primitive_gov"]

            # Capital assignment (use first date to set capital)
            capital = getattr(country_data, 'capital_province', 1)

            lines.extend([
                f"{date_str} = {{",
                f"\tcapital = {capital}",
                f"\tgovernment = {era_gov}",
                f"\tmonarch = {{",
                f'\t\tname = "{name}"',
                f"\t\tdynasty = {dynasty}",
                f"\t\tadm = {adm}",
                f"\t\tdip = {dip}",
                f"\t\tmil = {mil}",
                f"\t\tage = {age}",
                f"\t\tregent = no",
                f"\t}}",
            ])

            # Add heir for early_modern and later eras
            if era in ("early_modern", "modern", "contemporary"):
                heir_name = rng.choice(name_pool)
                heir_age = rng.randint(1, 15)
                if is_advanced:
                    h_adm = rng.randint(2, 5)
                    h_dip = rng.randint(2, 5)
                    h_mil = rng.randint(2, 5)
                else:
                    h_adm = rng.randint(0, 2)
                    h_dip = rng.randint(0, 2)
                    h_mil = rng.randint(1, 3)
                lines.extend([
                    f"\their = {{",
                    f'\t\tname = "{heir_name}"',
                    f"\t\tdynasty = {dynasty}",
                    f"\t\tadm = {h_adm}",
                    f"\t\tdip = {h_dip}",
                    f"\t\tmil = {h_mil}",
                    f"\t\tage = {heir_age}",
                    f"\t}}",
                ])

            lines.extend([
                "}",
                "",
            ])

        return "\n".join(lines)

    @staticmethod
    def write_country_history(tag: str, country_data,
                               is_advanced: bool,
                               output_dir: str) -> str:
        """Write a date-scoped country history file."""
        ensure_dir(output_dir)

        content = ETCountryHistoryExporter.generate_date_scoped_country_history(
            tag, country_data, is_advanced
        )

        filename = f"{tag} - {country_data.short_name}.txt"
        return write_text(os.path.join(output_dir, filename), content)


# ═══════════════════════════════════════════════════════════════════════
#  EXTENDED TIMELINE TECHNOLOGY GENERATOR
# ═══════════════════════════════════════════════════════════════════════

class ETTechnologyExporter:
    """
    Generates technology files compatible with Extended Timeline's
    extended technology system. The ET mod adds additional tech levels
    for ancient and modern eras.
    """

    @staticmethod
    def generate_technology_file(output_dir: str,
                                  advanced_tags: List[str] = None,
                                  primitive_tags: List[str] = None) -> str:
        """
        Generate a technology.txt that defines tech groups with appropriate
        penalties for the inverted world and Extended Timeline.
        """
        ensure_dir(output_dir)

        # Extended Timeline adds many more tech groups for different eras
        # In the inverted world, African/Asian groups have no penalty
        # European groups have massive penalties
        content = """# Technology Groups for Inverted World + Extended Timeline
# Africa and Asia are advanced, Europe is primitive

chinese = {
\tai = yes
\tcancelled = no

\tstart_tech = 0

\ton_advance_contribution = 0.05

\tmodifier = {
\t\ttechnology_cost = -0.15
\t\tidea_cost = -0.10
\t\tinfantry_power = 0.05
\t\tcavalry_power = 0.05
\t}
}

indian = {
\tai = yes
\tcancelled = no

\tstart_tech = 0

\ton_advance_contribution = 0.05

\tmodifier = {
\t\ttechnology_cost = -0.10
\t\tidea_cost = -0.08
\t\tinfantry_power = 0.05
\t\tcavalry_power = 0.10
\t}
}

east_african = {
\tai = yes
\tcancelled = no

\tstart_tech = 0

\ton_advance_contribution = 0.04

\tmodifier = {
\t\ttechnology_cost = -0.08
\t\tidea_cost = -0.05
\t\tinfantry_power = 0.05
\t\tdefensiveness = 0.10
\t}
}

west_african = {
\tai = yes
\tcancelled = no

\tstart_tech = 0

\ton_advance_contribution = 0.04

\tmodifier = {
\t\ttechnology_cost = -0.05
\t\tidea_cost = -0.05
\t\tinfantry_power = 0.08
\t\tmanpower_recovery_speed = 0.05
\t}
}

muslim = {
\tai = yes
\tcancelled = no

\tstart_tech = 0

\ton_advance_contribution = 0.03

\tmodifier = {
\t\ttechnology_cost = 0.15
\t\tidea_cost = 0.10
\t}
}

ottoman = {
\tai = yes
\tcancelled = no

\tstart_tech = 0

\ton_advance_contribution = 0.03

\tmodifier = {
\t\ttechnology_cost = 0.20
\t\tidea_cost = 0.15
\t}
}

nomad = {
\tai = yes
\tcancelled = no

\tstart_tech = 0

\ton_advance_contribution = 0.02

\tmodifier = {
\t\ttechnology_cost = 0.50
\t\tidea_cost = 0.30
\t\tcavalry_power = 0.10
\t}
}

eastern = {
\tai = yes
\tcancelled = no

\tstart_tech = 0

\ton_advance_contribution = 0.02

\tmodifier = {
\t\ttechnology_cost = 0.60
\t\tidea_cost = 0.40
\t}
}

western = {
\tai = yes
\tcancelled = no

\tstart_tech = 0

\ton_advance_contribution = 0.01

\tmodifier = {
\t\ttechnology_cost = 0.80
\t\tidea_cost = 0.50
\t\tinfantry_power = -0.05
\t}
}

new_world = {
\tai = yes
\tcancelled = no

\tstart_tech = 0

\ton_advance_contribution = 0.01

\tmodifier = {
\t\ttechnology_cost = 1.00
\t\tidea_cost = 0.60
\t}
}

high_american = {
\tai = yes
\tcancelled = no

\tstart_tech = 0

\ton_advance_contribution = 0.01

\tmodifier = {
\t\ttechnology_cost = 0.90
\t\tidea_cost = 0.55
\t}
}
"""
        return write_text(os.path.join(output_dir, "technology.txt"), content)


# ═══════════════════════════════════════════════════════════════════════
#  EXTENDED TIMELINE MOD DESCRIPTOR GENERATOR
# ═══════════════════════════════════════════════════════════════════════

class ETModDescriptorGenerator:
    """
    Generates .mod descriptor files with Extended Timeline dependency.
    The dependencies field ensures our mod loads after Extended Timeline.
    """

    @staticmethod
    def generate_mod_descriptor(mod_name: str, tech_name: str,
                                 output_dir: str,
                                 et_compatible: bool = True) -> Tuple[str, str]:
        """
        Generate .mod pointer file and in-mod descriptor with ET dependency.
        Returns (pointer_path, descriptor_path).
        """
        # Pointer file (goes in EU4 mod directory)
        dep_line = '\ndependencies = { "Extended Timeline" }' if et_compatible else ''

        pointer_content = (
            f'name = "{mod_name}"\n'
            f'path = "mod/{tech_name}"\n'
            f'supported_version = "1.37.*.*"\n'
            f'tags = {{\n'
            f'\t"Alternative History"\n'
            f'\t"Total Conversion"\n'
            f'\t"Gameplay"\n'
            f'}}\n'
            f'{dep_line}\n'
        )
        pointer_path = write_text(os.path.join(output_dir, f"{tech_name}.mod"), pointer_content)

        # In-mod descriptor (inside mod folder)
        descriptor_content = (
            f'name = "{mod_name}"\n'
            f'supported_version = "1.37.*.*"\n'
            f'{dep_line}\n'
        )
        descriptor_path = write_text(os.path.join(output_dir, "descriptor.mod"), descriptor_content)

        return pointer_path, descriptor_path


# ═══════════════════════════════════════════════════════════════════════
#  EXTENDED TIMELINE DIPLOMACY GENERATOR
# ═══════════════════════════════════════════════════════════════════════

class ETDiplomacyExporter:
    """
    Generates date-scoped diplomacy files for the Extended Timeline.
    Alliances, wars, and guarantee relationships change across eras.
    """

    @staticmethod
    def generate_era_diplomacy(countries: Dict[str, Any],
                                celestial_director_tags: List[str] = None,
                                output_dir: str = "") -> str:
        """
        Generate diplomacy entries with date scopes for different eras.
        """
        ensure_dir(output_dir)
        lines = [
            "# Extended Timeline Diplomacy for Inverted World",
            "# Diplomatic relationships change across eras",
            "",
        ]

        director_tags = celestial_director_tags or []

        # Celestial Directorate alliances (start in medieval era)
        if len(director_tags) >= 2:
            director = director_tags[0]
            members = director_tags[1:]

            # Ancient era: no directorate yet, tribal alliances
            for member in members[:3]:
                lines.extend([
                    "alliance = {",
                    f"\tfirst = {director}",
                    f"\tsecond = {member}",
                    f"\tstart_date = 769.1.1",
                    "}",
                    "",
                ])

            # Medieval era: formal directorate alliances
            for member in members[:6]:
                lines.extend([
                    "alliance = {",
                    f"\tfirst = {director}",
                    f"\tsecond = {member}",
                    f"\tstart_date = 1066.1.1",
                    "}",
                    "",
                ])

            # Early modern: full directorate
            for member in members[:10]:
                lines.extend([
                    "guarantee = {",
                    f"\tfirst = {director}",
                    f"\tsecond = {member}",
                    f"\tstart_date = 1444.11.11",
                    "}",
                    "",
                ])

        content = "\n".join(lines)
        return write_text(os.path.join(output_dir, "extended_timeline_diplomacy.txt"), content)


# ═══════════════════════════════════════════════════════════════════════
#  EXTENDED TIMELINE DEFINES GENERATOR
# ═══════════════════════════════════════════════════════════════════════

class ETDefinesExporter:
    """
    Generates defines.lua overrides for Extended Timeline compatibility.
    Adjusts start date, technology dates, and other ET-relevant settings.
    """

    @staticmethod
    def generate_defines(output_dir: str) -> str:
        """Generate defines.lua with ET-compatible settings."""
        ensure_dir(output_dir)

        content = """-- Defines for Inverted World + Extended Timeline Compatibility
-- Adjusts start dates and technology to work with ET's extended timeline

defines = {
    start = {
        START_DATE = "58.1.1"
    }
    technology = {
        START_TECH = 0
        TECH_YEAR_AHEAD_PENALTY = 0.05
        TECH_YEAR_AHEAD_PENALTY_ITER = 0.001
        TECH_COST_AHEAD_PENALTY = 1.00
        MAX_AHEAD_PENALTY_TECHS = 3
        INSTITUTION_BASE_PENALTY = 0.02
    }
    religion = {
        HRE_RELIGION = "hindu"
        CELESTIAL_DIRECTORATE_RELIGION = "hindu"
    }
}
"""
        return write_text(os.path.join(output_dir, "defines.lua"), content)


# ═══════════════════════════════════════════════════════════════════════
#  EXTENDED TIMELINE MASTER INTEGRATOR
# ═══════════════════════════════════════════════════════════════════════

class ETCompatibilityIntegrator:
    """
    Master integrator that applies Extended Timeline compatibility
    to the entire mod export pipeline. Call this instead of the
    standard export functions when ET compatibility is desired.
    """

    @staticmethod
    def export_et_compatible_mod(mod_root: str,
                                  countries: Dict[str, Any],
                                  province_infos: list,
                                  country_assignments: Dict[int, str],
                                  celestial_director_tags: List[str] = None,
                                  map_height: int = 2048) -> Dict[str, str]:
        """
        Export all Extended Timeline compatible files for the mod.
        Returns a dict of {file_type: path} for all ET-specific files.
        """
        exported = {}

        # Determine advanced vs primitive tags
        advanced_tags = [t for t, c in countries.items() if getattr(c, 'is_advanced', True)]
        primitive_tags = [t for t, c in countries.items() if not getattr(c, 'is_advanced', False)]
        hindu_tags = [t for t, c in countries.items()
                      if getattr(c, 'religion', '') == 'hindu']

        # 1. Export bookmarks
        bookmarks_dir = os.path.join(mod_root, "common", "bookmarks")
        exported["et_bookmarks"] = ETBookmarkExporter.generate_bookmarks(
            bookmarks_dir, advanced_tags, primitive_tags, hindu_tags
        )

        # 2. Export bookmark localisation
        loc_dir = os.path.join(mod_root, "localisation")
        exported["et_bookmark_loc"] = ETBookmarkExporter.generate_bookmark_localisation(
            loc_dir
        )

        # 3. Export date-scoped province histories
        prov_dir = os.path.join(mod_root, "history", "provinces")
        for p in province_infos:
            if hasattr(p, 'is_sea') and (p.is_sea or p.is_wasteland):
                continue
            owner_tag = country_assignments.get(p.id, advanced_tags[0] if advanced_tags else "BHA")
            is_advanced = owner_tag in advanced_tags
            continent = getattr(p, 'continent_name', 'africa')
            ETProvinceHistoryExporter.write_province_history(
                p, owner_tag, is_advanced, continent, prov_dir, map_height
            )
        exported["et_provinces"] = prov_dir

        # 4. Export date-scoped country histories
        country_dir = os.path.join(mod_root, "history", "countries")
        for tag, data in countries.items():
            is_advanced = getattr(data, 'is_advanced', True)
            ETCountryHistoryExporter.write_country_history(
                tag, data, is_advanced, country_dir
            )
        exported["et_countries"] = country_dir

        # 5. Export technology file
        tech_dir = os.path.join(mod_root, "common")
        exported["et_technology"] = ETTechnologyExporter.generate_technology_file(
            os.path.join(tech_dir, "technology"), advanced_tags, primitive_tags
        )

        # 6. Export ET-compatible .mod descriptor (with dependencies)
        exported["et_mod_descriptor"] = {}
        pointer, desc = ETModDescriptorGenerator.generate_mod_descriptor(
            "Inverted World", "inverted_world", mod_root, et_compatible=True
        )
        exported["et_mod_pointer"] = pointer
        exported["et_mod_descriptor"] = desc

        # 7. Export era diplomacy
        dip_dir = os.path.join(mod_root, "history", "diplomacy")
        exported["et_diplomacy"] = ETDiplomacyExporter.generate_era_diplomacy(
            countries, celestial_director_tags, dip_dir
        )

        # 8. Export defines
        exported["et_defines"] = ETDefinesExporter.generate_defines(
            os.path.join(mod_root, "common")
        )

        return exported
