"""
Template Exporter Module
========================
Borrows default mod file templates from EUIV_Map_Generator_2.0 and adapts them
for our inverted-dynamics total conversion mod. Handles:

1. Decisions - Form nation decisions for advanced African/Asian countries
2. Events - Custom events reflecting Hindu dominance, pagan resurgence
3. Missions - Mission trees for Celestial Directorate and advanced nations
4. Localisation - YML files for all custom content
5. Common files - Ideas, triggered modifiers, bookmarks, defines

Key adaptations from the original EUIV_Map_Generator templates:
- Replace European-centric decisions with African/Asian form-nation decisions
- Replace Christian/Islamic events with Hindu/pagan events
- Add Celestial Directorate mechanics (second HRE-like system)
- Invert technology group references (Chinese/Indian = advanced, Western = primitive)
- Add corruption mechanics for Islamic/Christian religions
"""

import os
import shutil
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TEMPLATE CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Inverted religion hierarchy
RELIGION_HIERARCHY = {
    "hindu": {"rank": 1, "corruption": 0, "institution_bonus": 0.15,
              "desc": "The dominant world faith, center of learning and devotion"},
    "pagan": {"rank": 2, "corruption": 0, "institution_bonus": 0.08,
              "desc": "Ancient traditions that refused to bow to foreign gods"},
    "animism": {"rank": 3, "corruption": 0, "institution_bonus": 0.05,
                "desc": "The spirits of the land guide the faithful"},
    "buddhist": {"rank": 4, "corruption": 0.02, "institution_bonus": 0.04,
                 "desc": "The middle path, corrupted by foreign influence"},
    "sunni": {"rank": 5, "corruption": 0.30, "institution_bonus": -0.10,
              "desc": "Corrupted by greed and internal strife"},
    "shiite": {"rank": 6, "corruption": 0.35, "institution_bonus": -0.12,
               "desc": "Deeply corrupted, divided and weakened"},
    "catholic": {"rank": 7, "corruption": 0.50, "institution_bonus": -0.20,
                 "desc": "A crumbling faith built on exploitation and decay"},
    "protestant": {"rank": 8, "corruption": 0.45, "institution_bonus": -0.18,
                   "desc": "A fractured rebellion, no less corrupt than its parent"},
    "orthodox": {"rank": 9, "corruption": 0.40, "institution_bonus": -0.15,
                 "desc": "Isolated and stagnating under bureaucratic rot"},
}

# Inverted technology groups
TECH_GROUPS = {
    "chinese": {"rank": 1, "penalty": 0.0, "desc": "The pinnacle of human achievement"},
    "indian": {"rank": 2, "penalty": 0.0, "desc": "Masters of science and philosophy"},
    "muslim": {"rank": 3, "penalty": 0.20, "desc": "Once great, now fallen into decay"},
    "east_african": {"rank": 4, "penalty": 0.0, "desc": "Heirs of ancient wisdom"},
    "west_african": {"rank": 5, "penalty": 0.05, "desc": "Scholars of the golden age"},
    "ottoman": {"rank": 6, "penalty": 0.25, "desc": "Stagnant shadows of former glory"},
    "western": {"rank": 7, "penalty": 0.60, "desc": "Backwards and primitive"},
    "eastern": {"rank": 8, "penalty": 0.55, "desc": "Crude imitation of true civilization"},
    "nomad": {"rank": 9, "penalty": 0.80, "desc": "Savages with no understanding of progress"},
    "new_world": {"rank": 10, "penalty": 1.00, "desc": "Lost in ignorance"},
}

# Celestial Directorate (second HRE-like system)
CELESTIAL_DIRECTORATE = {
    "name": "Celestial Directorate",
    "religion": "hindu",
    "color": {"r": 255, "g": 200, "b": 50},
    "reform_count": 8,
    "initial_reforms": [
        "Celestial Mandate: The Director holds divine authority over member states",
        "Bureau of Rites: Standardizes religious ceremonies across the Directorate",
        "Celestial Examination: Merit-based administration replaces hereditary privilege",
        "Directorate Guard: Standing army funded by all member states",
        "Harmonious Trade: Common market with free movement of goods",
        "Celestial Diplomacy: Member states speak with one voice abroad",
        "Directorate Treasury: Central bank manages shared reserves",
        "Eternal Mandate: The Directorate becomes a unified empire",
    ],
}

# Form-nation decisions for advanced countries
FORM_NATION_DECISIONS = {
    "Bharat": {
        "tag": "BHA", "culture_group": "indian", "religion": "hindu",
        "required_provinces": 10,
        "desc": "Unite the Indian subcontinent under one banner, restoring the ancient empire.",
        "bonus": "core_creation_cost = -0.25\nacceptable_deal = +1",
    },
    "Hindustan": {
        "tag": "HIN", "culture_group": "indian", "religion": "hindu",
        "required_provinces": 15,
        "desc": "Forge the greatest Hindu empire the world has ever seen.",
        "bonus": "discipline = 0.05\nmanpower_recovery_speed = 0.10",
    },
    "Abyssinia": {
        "tag": "ABY", "culture_group": "east_african", "religion": "hindu",
        "required_provinces": 8,
        "desc": "Restore the ancient kingdom, beacon of civilization in Africa.",
        "bonus": "fort_maintenance = -0.20\ndefensiveness = 0.25",
    },
    "Mali": {
        "tag": "MLI", "culture_group": "west_african", "religion": "animism",
        "required_provinces": 8,
        "desc": "Rebuild the golden empire of the Sahel.",
        "bonus": "global_trade_power = 0.10\nproduction_efficiency = 0.10",
    },
    "Great Zimbabwe": {
        "tag": "GZW", "culture_group": "central_african", "religion": "animism",
        "required_provinces": 6,
        "desc": "Construct the greatest stone city the world has ever known.",
        "bonus": "build_cost = -0.20\ndevelopment_cost = -0.10",
    },
    "Majapahit": {
        "tag": "MPH", "culture_group": "malay", "religion": "hindu",
        "required_provinces": 8,
        "desc": "Unite the archipelago under the thunder of the war elephant.",
        "bonus": "navy_tradition = 0.5\nship_durability = 0.10",
    },
    "Songhai": {
        "tag": "SGH", "culture_group": "west_african", "religion": "animism",
        "required_provinces": 10,
        "desc": "Forge the mightiest empire of the western Sahel.",
        "bonus": "land_morale = 0.10\ninfantry_power = 0.10",
    },
    "Khmer": {
        "tag": "KMR", "culture_group": "mon_khmer", "religion": "hindu",
        "required_provinces": 8,
        "desc": "Build temples that touch the heavens, an empire of stone and devotion.",
        "bonus": "prestige = 1.0\ndevelopment_cost = -0.15",
    },
}


@dataclass
class TemplateExportConfig:
    """Configuration for template-based mod file generation."""
    mod_name: str = "InvertedWorld"
    mod_path: str = "InvertedWorld"
    starting_date: str = "1444.11.11"
    tags: List[str] = field(default_factory=list)
    advanced_tags: List[str] = field(default_factory=list)
    primitive_tags: List[str] = field(default_factory=list)
    hindu_tags: List[str] = field(default_factory=list)
    celestial_director_tags: List[str] = field(default_factory=list)
    hre_tags: List[str] = field(default_factory=list)
    culture_groups: Dict[str, List[str]] = field(default_factory=dict)


class TemplateExporter:
    """
    Exports adapted mod templates from EUIV_Map_Generator_2.0 defaults,
    customized for the inverted-dynamics total conversion.
    """

    def __init__(self, config: TemplateExportConfig, templates_dir: str = "templates"):
        self.config = config
        self.templates_dir = templates_dir

    def export_all(self, mod_root: str) -> Dict[str, int]:
        """Export all template-based mod files. Returns {category: count}."""
        stats = {}
        stats["decisions"] = self._export_decisions(mod_root)
        stats["events"] = self._export_events(mod_root)
        stats["missions"] = self._export_missions(mod_root)
        stats["common"] = self._export_common(mod_root)
        stats["localisation"] = self._export_localisation(mod_root)
        stats["history"] = self._export_history_templates(mod_root)
        return stats

    # ─── Decisions ────────────────────────────────────────────────────

    def _export_decisions(self, mod_root: str) -> int:
        """Export form-nation decisions and custom decisions."""
        out_dir = os.path.join(mod_root, "decisions")
        os.makedirs(out_dir, exist_ok=True)
        count = 0

        # Copy base decision templates that are religion/culture agnostic
        base_decisions = ["Civic.txt", "Constructions.txt", "Cultural.txt",
                          "Military.txt", "Trade.txt", "Tribal.txt",
                          "ColonialNations.txt", "Governments.txt"]
        for fname in base_decisions:
            src = os.path.join(self.templates_dir, "decisions", fname)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(out_dir, fname))
                count += 1

        # Generate custom form-nation decisions
        custom = self._generate_form_nation_decisions()
        with open(os.path.join(out_dir, "InvertedWorld_FormNations.txt"), "w") as f:
            f.write(custom)
        count += 1

        # Generate Celestial Directorate decisions
        cd = self._generate_celestial_directorate_decisions()
        with open(os.path.join(out_dir, "CelestialDirectorate.txt"), "w") as f:
            f.write(cd)
        count += 1

        # Generate religion corruption decisions
        rel = self._generate_religion_decisions()
        with open(os.path.join(out_dir, "Religion_Decisions.txt"), "w") as f:
            f.write(rel)
        count += 1

        return count

    def _generate_form_nation_decisions(self) -> str:
        """Generate form-nation decisions for advanced African/Asian countries."""
        lines = [
            "# Form Nation Decisions for the Inverted World",
            "# Africa and Asia are the centers of civilization",
            "",
        ]
        for name, data in FORM_NATION_DECISIONS.items():
            tag = data["tag"]
            cg = data["culture_group"]
            rel = data["religion"]
            prov = data["required_provinces"]
            desc = data["desc"]
            bonus = data["bonus"]
            lines.extend([
                f"### {name} ###",
                f'country_decision = {{',
                f'\tidentifier = form_{name.lower().replace(" ", "_")}',
                f'\t{tag}_nation = {{',
                f'\t\ttitle = "{name.upper()}_TITLE"',
                f'\t\tdesc = "{name.upper()}_DESC"',
                f'',
                f'\t\tpotential = {{',
                f'\t\t\tNOT = {{ has_country_flag = formed_{tag.lower()} }}',
                f'\t\t\tculture_group = {cg}',
                f'\t\t\treligion = {rel}',
                f'\t\t\t{{ OR = {{',
                f'\t\t\t\tis_player = yes',
                f'\t\t\t\tnum_of_cities = {prov}',
                f'\t\t\t}} }}',
                f'\t\t}}',
                f'',
                f'\t\tallow = {{',
                f'\t\t\towns = {prov}',
                f'\t\t\tis_core = {prov}',
                f'\t\t\twar = no',
                f'\t\t}}',
                f'',
                f'\t\teffect = {{',
                f'\t\t\tchange_tag = {tag}',
                f'\t\t\tset_country_flag = formed_{tag.lower()}',
                f'\t\t\tadd_prestige = 25',
                f'\t\t\tadd_legitimacy = 20',
                f'\t\t\tcentralize_state = yes',
                f'\t\t\t{bonus}',
                f'\t\t}}',
                f'',
                f'\t\tai_will_do = {{',
                f'\t\t\tfactor = 2',
                f'\t\t}}',
                f'\t}}',
                f'}}',
                '',
            ])
        return "\n".join(lines)

    def _generate_celestial_directorate_decisions(self) -> str:
        """Generate decisions for the Celestial Directorate (second HRE)."""
        cd = CELESTIAL_DIRECTORATE
        lines = [
            "# Celestial Directorate Decisions",
            "# The second HRE-like system, centered on Hindu civilization",
            "",
        ]
        for i, reform in enumerate(cd["initial_reforms"]):
            reform_id = f"celestial_reform_{i+1}"
            lines.extend([
                f"### Reform {i+1}: {reform.split(':')[0]} ###",
                f'country_decision = {{',
                f'\tidentifier = {reform_id}',
                f'\tcelestial_reform = {{',
                f'\t\ttitle = "CELESTIAL_REFORM_{i+1}_TITLE"',
                f'\t\tdesc = "CELESTIAL_REFORM_{i+1}_DESC"',
                f'\t\tnum_reforms = {i}',
                f'',
                f'\t\tpotential = {{',
                f'\t\t\tis_celestial_emperor = yes',
                f'\t\t\tNOT = {{ has_reform = {reform_id} }}',
                f'\t\t}}',
                f'',
                f'\t\tallow = {{',
                f'\t\t\timperial_authority = 50',
                f'\t\t\tnum_imperial_princes = {max(3, 10 - i)}',
                f'\t\t}}',
                f'',
                f'\t\teffect = {{',
                f'\t\t\tadd_imperial_reform = {reform_id}',
                f'\t\t\tchange_imperial_authority = -10',
                f'\t\t}}',
                f'\t}}',
                f'}}',
                '',
            ])
        return "\n".join(lines)

    def _generate_religion_decisions(self) -> str:
        """Generate religion-related decisions reflecting corruption mechanics."""
        lines = [
            "# Religion Decisions for the Inverted World",
            "# Hindu is dominant, Christian/Islamic religions are corrupted",
            "",
            "### Purify the Faith (Hindu) ###",
            "country_decision = {",
            "\tidentifier = purify_faith_hindu",
            "\t{",
            '\t\ttitle = "PURIFY_FAITH_HINDU_TITLE"',
            '\t\tdesc = "PURIFY_FAITH_HINDU_DESC"',
            "",
            "\t\tpotential = {",
            "\t\t\treligion = hindu",
            "\t\t\tNOT = { has_country_flag = hindu_purified }",
            "\t\t}",
            "",
            "\t\tallow = {",
            "\t\t\tstability = 2",
            "\t\t\treligious_unity = 1.0",
            "\t\t}",
            "",
            "\t\teffect = {",
            "\t\t\tset_country_flag = hindu_purified",
            "\t\t\tadd_missionary = 1",
            "\t\t\tadd_church_loyalty = 25",
            "\t\t\treduce_corruption = 2",
            "\t\t}",
            "\t}",
            "}",
            "",
            "### Root Out Corruption (Christian) ###",
            "country_decision = {",
            "\tidentifier = root_out_corruption_christian",
            "\t{",
            '\t\ttitle = "ROOT_CORRUPTION_CHRISTIAN_TITLE"',
            '\t\tdesc = "ROOT_CORRUPTION_CHRISTIAN_DESC"',
            "",
            "\t\tpotential = {",
            "\t\t\tOR = {",
            "\t\t\t\treligion = catholic",
            "\t\t\t\treligion = protestant",
            "\t\t\t\treligion = orthodox",
            "\t\t\t}",
            "\t\t\tcorruption >= 0.30",
            "\t\t}",
            "",
            "\t\tallow = {",
            "\t\t\ttreasury = 200",
            "\t\t\tstability = 1",
            "\t\t}",
            "",
            "\t\teffect = {",
            "\t\t\treduce_corruption = 1",
            "\t\t\tadd_prestige = -10",
            "\t\t\tadd_stability = -1",
            "\t\t}",
            "\t}",
            "}",
            "",
            "### Embrace True Faith (Pagan) ###",
            "country_decision = {",
            "\tidentifier = embrace_true_faith_pagan",
            "\t{",
            '\t\ttitle = "EMBRACE_TRUE_FAITH_PAGAN_TITLE"',
            '\t\tdesc = "EMBRACE_TRUE_FAITH_PAGAN_DESC"',
            "",
            "\t\tpotential = {",
            "\t\t\treligion_group = pagan",
            "\t\t\tNOT = { has_country_flag = true_faith_embraced }",
            "\t\t}",
            "",
            "\t\tallow = {",
            "\t\t\tstability = 1",
            "\t\t\tis_at_war = no",
            "\t\t}",
            "",
            "\t\teffect = {",
            "\t\t\tset_country_flag = true_faith_embraced",
            "\t\t\tadd_missionary = 1",
            "\t\t\tadd_prestige = 15",
            "\t\t}",
            "\t}",
            "}",
            "",
        ]
        return "\n".join(lines)

    # ─── Events ────────────────────────────────────────────────────────

    def _export_events(self, mod_root: str) -> int:
        """Export adapted events from templates and custom events."""
        out_dir = os.path.join(mod_root, "events")
        os.makedirs(out_dir, exist_ok=True)
        count = 0

        # Copy base event templates that work for any mod
        base_events = ["CulturalEvents.txt", "Cleanup.txt", "CulturalUprising.txt",
                       "Colonial.txt", "ColonialLife.txt", "BorderFriction.txt",
                       "Dynastic.txt", "Constructions.txt"]
        for fname in base_events:
            src = os.path.join(self.templates_dir, "events", fname)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(out_dir, fname))
                count += 1

        # Generate custom Hindu dominance events
        hindu_events = self._generate_hindu_dominance_events()
        with open(os.path.join(out_dir, "HinduDominance.txt"), "w") as f:
            f.write(hindu_events)
        count += 1

        # Generate corruption events for Christian/Islamic religions
        corruption_events = self._generate_corruption_events()
        with open(os.path.join(out_dir, "CorruptionEvents.txt"), "w") as f:
            f.write(corruption_events)
        count += 1

        # Generate Celestial Directorate events
        cd_events = self._generate_celestial_directorate_events()
        with open(os.path.join(out_dir, "CelestialDirectorateEvents.txt"), "w") as f:
            f.write(cd_events)
        count += 1

        # Generate technology inversion events
        tech_events = self._generate_tech_inversion_events()
        with open(os.path.join(out_dir, "TechInversionEvents.txt"), "w") as f:
            f.write(tech_events)
        count += 1

        return count

    def _generate_hindu_dominance_events(self) -> str:
        """Generate events reflecting Hindu religious dominance."""
        return """# Hindu Dominance Events
# Hindu is the world's major religion in the inverted world

namespace = hindu_dominance

# The Great Temple
country_event = {
\tid = hindu_dominance.1
\ttitle = "hindu_dominance.1.t"
\tdesc = "hindu_dominance.1.d"
\tpicture = GREAT_TEMPLE_eventPicture

\ttrigger = {
\t\treligion = hindu
\t\tstability = 2
\t}

\tmean_time_to_happen = {
\t\tmonths = 120
\t}

\toption = {
\t\tname = "hindu_dominance.1.a"
\t\tadd_prestige = 25
\t\tadd_church_loyalty = 10
\t\tadd_institution_progress = { which = printing_press value = 10 }
\t}
}

# Festival of Lights
country_event = {
\tid = hindu_dominance.2
\ttitle = "hindu_dominance.2.t"
\tdesc = "hindu_dominance.2.d"
\tpicture = DIWALI_eventPicture

\ttrigger = {
\t\treligion = hindu
\t}

\tmean_time_to_happen = {
\t\tmonths = 60
\t}

\toption = {
\t\tname = "hindu_dominance.2.a"
\t\tadd_stability = 1
\t\tadd_prestige = 10
\t}

\toption = {
\t\tname = "hindu_dominance.2.b"
\t\tadd_treasury = -50
\t\tadd_legitimacy = 15
\t}
}

# Hindu Scholar Arrives
province_event = {
\tid = hindu_dominance.3
\ttitle = "hindu_dominance.3.t"
\tdesc = "hindu_dominance.3.d"

\ttrigger = {
\t\towner = { religion = hindu }
\t}

\tmean_time_to_happen = {
\t\tmonths = 200
\t}

\toption = {
\t\tname = "hindu_dominance.3.a"
\t\tadd_local_development = 1
\t\towner = { add_institution_progress = { which = renaissance value = 5 } }
\t}
}

# Pagan Revival
country_event = {
\tid = hindu_dominance.4
\ttitle = "hindu_dominance.4.t"
\tdesc = "hindu_dominance.4.d"

\ttrigger = {
\t\treligion_group = pagan
\t}

\tmean_time_to_happen = {
\t\tmonths = 100
\t}

\toption = {
\t\tname = "hindu_dominance.4.a"
\t\tadd_missionary = 1
\t\tadd_prestige = 15
\t}

\toption = {
\t\tname = "hindu_dominance.4.b"
\t\tadd_treasury = 25
\t}
}
"""

    def _generate_corruption_events(self) -> str:
        """Generate corruption events for weakened Christian/Islamic religions."""
        return """# Corruption Events for Christian and Islamic Religions
# These religions are weak and corrupted in the inverted world

namespace = corrupted_faith

# Corrupt Clergy Exposed
country_event = {
\tid = corrupted_faith.1
\ttitle = "corrupted_faith.1.t"
\tdesc = "corrupted_faith.1.d"

\ttrigger = {
\t\tOR = {
\t\t\treligion = catholic
\t\t\treligion = protestant
\t\t\treligion = orthodox
\t\t\treligion = sunni
\t\t\treligion = Shiite
\t\t}
\t}

\tmean_time_to_happen = {
\t\tmonths = 80
\t}

\toption = {
\t\tname = "corrupted_faith.1.a"
\t\tadd_corruption = 0.5
\t\tadd_prestige = -10
\t}

\toption = {
\t\tname = "corrupted_faith.1.b"
\t\tadd_stability = -2
\t\treduce_corruption_or_effect = 1
\t}
}

# Schism and Division
country_event = {
\tid = corrupted_faith.2
\ttitle = "corrupted_faith.2.t"
\tdesc = "corrupted_faith.2.d"

\ttrigger = {
\t\tOR = {
\t\t\treligion = catholic
\t\t\treligion = sunni
\t\t}
\t\tstability < 0
\t}

\tmean_time_to_happen = {
\t\tmonths = 120
\t}

\toption = {
\t\tname = "corrupted_faith.2.a"
\t\tadd_stability = -1
\t\tadd_corruption = 1.0
\t\tadd_unrest = 3
\t}

\toption = {
\t\tname = "corrupted_faith.2.b"
\t\tchange_religion = protestant
\t}
}

# Weak Church, Weak State
country_event = {
\tid = corrupted_faith.3
\ttitle = "corrupted_faith.3.t"
\tdesc = "corrupted_faith.3.d"

\ttrigger = {
\t\tOR = {
\t\t\treligion = catholic
\t\t\treligion = orthodox
\t\t}
\t\tcorruption >= 0.3
\t}

\tmean_time_to_happen = {
\t\tmonths = 100
\t}

\toption = {
\t\tname = "corrupted_faith.3.a"
\t\tadd_tax_income_proportion = -0.10
\t\tadd_unrest = 2
\t}

\toption = {
\t\tname = "corrupted_faith.3.b"
\t\tadd_treasury = -100
\t\treduce_corruption = 1
\t}
}
"""

    def _generate_celestial_directorate_events(self) -> str:
        """Generate events for the Celestial Directorate (second HRE)."""
        return """# Celestial Directorate Events
# The second HRE-like system centered on Hindu civilization

namespace = celestial_directorate

# Director's Mandate
country_event = {
\tid = celestial_directorate.1
\ttitle = "celestial_directorate.1.t"
\tdesc = "celestial_directorate.1.d"

\ttrigger = {
\t\tis_celestial_emperor = yes
\t}

\tmean_time_to_happen = {
\t\tmonths = 60
\t}

\toption = {
\t\tname = "celestial_directorate.1.a"
\t\tchange_imperial_authority = 5
\t\tadd_prestige = 15
\t}

\toption = {
\t\tname = "celestial_directorate.1.b"
\t\tadd_treasury = 100
\t\tchange_imperial_authority = -5
\t}
}

# Directorate Reforms
country_event = {
\tid = celestial_directorate.2
\ttitle = "celestial_directorate.2.t"
\tdesc = "celestial_directorate.2.d"

\ttrigger = {
\t\tis_celestial_emperor = yes
\t\tnum_imperial_reforms >= 3
\t}

\tmean_time_to_happen = {
\t\tmonths = 120
\t}

\toption = {
\t\tname = "celestial_directorate.2.a"
\t\tchange_imperial_authority = 10
\t\tadd_stability = 1
\t}

\toption = {
\t\tname = "celestial_directorate.2.b"
\t\tevery_owned_province = { limit = { is_part_of_celestial_directorate = yes } add_local_development = 1 }
\t\tchange_imperial_authority = -5
\t}
}

# Prince Joins Directorate
country_event = {
\tid = celestial_directorate.3
\ttitle = "celestial_directorate.3.t"
\tdesc = "celestial_directorate.3.d"

\ttrigger = {
\t\tis_part_of_celestial_directorate = yes
\t\tNOT = { is_celestial_emperor = yes }
\t}

\tmean_time_to_happen = {
\t\tmonths = 200
\t}

\toption = {
\t\tname = "celestial_directorate.3.a"
\t\tadd_legitimacy = 10
\t\tadd_prestige = 5
\t}

\toption = {
\t\tname = "celestial_directorate.3.b"
\t\tadd_treasury = 50
\t}
}

# Directorate Civil War
country_event = {
\tid = celestial_directorate.4
\ttitle = "celestial_directorate.4.t"
\tdesc = "celestial_directorate.4.d"

\ttrigger = {
\t\tis_celestial_emperor = yes
\t\timperial_authority < 30
\t}

\tmean_time_to_happen = {
\t\tmonths = 60
\t}

\toption = {
\t\tname = "celestial_directorate.4.a"
\t\tchange_imperial_authority = -10
\t\tadd_stability = -2
\t\tadd_war_exhaustion = 3
\t}

\toption = {
\t\tname = "celestial_directorate.4.b"
\t\tadd_treasury = -200
\t\tchange_imperial_authority = 5
\t}
}
"""

    def _generate_tech_inversion_events(self) -> str:
        """Generate events reflecting the technology inversion."""
        return """# Technology Inversion Events
# Africa and Asia are advanced, Europe is primitive

namespace = tech_inversion

# African Golden Age
country_event = {
\tid = tech_inversion.1
\ttitle = "tech_inversion.1.t"
\tdesc = "tech_inversion.1.d"

\ttrigger = {
\t\tOR = {
\t\t\ttechnology_group = west_african
\t\t\ttechnology_group = east_african
\t\t}
\t}

\tmean_time_to_happen = {
\t\tmonths = 100
\t}

\toption = {
\t\tname = "tech_inversion.1.a"
\t\tadd_institution_progress = { which = renaissance value = 15 }
\t\tadd_prestige = 20
\t}
}

# Asian Innovation
country_event = {
\tid = tech_inversion.2
\ttitle = "tech_inversion.2.t"
\tdesc = "tech_inversion.2.d"

\ttrigger = {
\t\tOR = {
\t\t\ttechnology_group = chinese
\t\t\ttechnology_group = indian
\t\t}
\t}

\tmean_time_to_happen = {
\t\tmonths = 80
\t}

\toption = {
\t\tname = "tech_inversion.2.a"
\t\tadd_institution_progress = { which = printing_press value = 10 }
\t\tadd_adm_power = 50
\t}
}

# European Backwardness
country_event = {
\tid = tech_inversion.3
\ttitle = "tech_inversion.3.t"
\tdesc = "tech_inversion.3.d"

\ttrigger = {
\t\tOR = {
\t\t\ttechnology_group = western
\t\t\ttechnology_group = eastern
\t\t}
\t}

\tmean_time_to_happen = {
\t\tmonths = 120
\t}

\toption = {
\t\tname = "tech_inversion.3.a"
\t\tadd_corruption = 0.5
\t\tadd_unrest = 2
\t}

\toption = {
\t\tname = "tech_inversion.3.b"
\t\tadd_stability = -1
\t}
}

# Transfer of Knowledge
province_event = {
\tid = tech_inversion.4
\ttitle = "tech_inversion.4.t"
\tdesc = "tech_inversion.4.d"

\ttrigger = {
\t\towner = {
\t\t\tOR = {
\t\t\t\ttechnology_group = chinese
\t\t\t\ttechnology_group = indian
\t\t\t\ttechnology_group = west_african
\t\t\t}
\t\t}
\t}

\tmean_time_to_happen = {
\t\tmonths = 150
\t}

\toption = {
\t\tname = "tech_inversion.4.a"
\t\tadd_local_development = 1
\t\towner = { add_monarch_power = { which = DIP value = 25 } }
\t}
}
"""

    # ─── Missions ──────────────────────────────────────────────────────

    def _export_missions(self, mod_root: str) -> int:
        """Export mission trees for custom countries."""
        out_dir = os.path.join(mod_root, "missions")
        os.makedirs(out_dir, exist_ok=True)
        count = 0

        # Copy generic mission templates
        base_missions = ["Conquest_Missions.txt", "Construction_Missions.txt",
                         "Diplomatic_Missions.txt", "Economical_Missions.txt",
                         "Trade_Missions.txt", "Government_Missions.txt",
                         "Culture_Missions.txt", "Anti_Rival_Missions.txt",
                         "Anti_Threat_Missions.txt"]
        for fname in base_missions:
            src = os.path.join(self.templates_dir, "missions", fname)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(out_dir, fname))
                count += 1

        # Generate Celestial Directorate mission tree
        cd_missions = self._generate_celestial_directorate_missions()
        with open(os.path.join(out_dir, "CelestialDirectorate_Missions.txt"), "w") as f:
            f.write(cd_missions)
        count += 1

        # Generate Hindu dominance mission tree
        hindu_missions = self._generate_hindu_dominance_missions()
        with open(os.path.join(out_dir, "HinduDominance_Missions.txt"), "w") as f:
            f.write(hindu_missions)
        count += 1

        # Generate African power mission tree
        african_missions = self._generate_african_power_missions()
        with open(os.path.join(out_dir, "AfricanPower_Missions.txt"), "w") as f:
            f.write(african_missions)
        count += 1

        return count

    def _generate_celestial_directorate_missions(self) -> str:
        """Generate mission tree for the Celestial Directorate."""
        return """# Celestial Directorate Mission Tree
# The second HRE-like system

celestial_directorate_missions = {
\tslot = 0
\tgeneric = no
\tai = yes

\t# Column 1: Religious Authority
\tcelestial_mandate_established = {
\t\ticon = mission_religious_unity
\t\trequired_missions = {}
\t\tprovinces_to_highlight = {}
\t\tcompletion_trigger = {
\t\t\tis_celestial_emperor = yes
\t\t\timperial_authority = 30
\t\t}
\t\teffect = {
\t\t\tadd_prestige = 25
\t\t\tchange_imperial_authority = 10
\t\t}
\t}

\tbureau_of_rites = {
\t\ticon = mission_church
\t\trequired_missions = { celestial_mandate_established }
\t\tprovinces_to_highlight = {}
\t\tcompletion_trigger = {
\t\t\tnum_imperial_reforms >= 2
\t\t}
\t\teffect = {
\t\t\tadd_missionary = 1
\t\t\tadd_church_loyalty = 10
\t\t}
\t}

\tcelestial_examination = {
\t\ticon = mission_admin_efficiency
\t\trequired_missions = { bureau_of_rites }
\t\tprovinces_to_highlight = {}
\t\tcompletion_trigger = {
\t\t\tnum_imperial_reforms >= 4
\t\t}
\t\teffect = {
\t\t\tadd_adm_power = 100
\t\t}
\t}

\t# Column 2: Military Strength
\tdirectorate_guard = {
\t\ticon = mission_army_professionalism
\t\trequired_missions = { celestial_mandate_established }
\t\tprovinces_to_highlight = {}
\t\tcompletion_trigger = {
\t\t\tarmy_tradition = 50
\t\t\tnum_of_regiments = 30
\t\t}
\t\teffect = {
\t\t\tadd_army_tradition = 20
\t\t\tadd_manpower = 10000
\t\t}
\t}

\t# Column 3: Economic Power
\tharmonious_trade = {
\t\ticon = mission_trade_center
\t\trequired_missions = { celestial_mandate_established }
\t\tprovinces_to_highlight = {}
\t\tcompletion_trigger = {
\t\t\ttrade_income = 10
\t\t}
\t\teffect = {
\t\t\tadd_global_trade_power = 0.10
\t\t\tadd_merchant = 1
\t\t}
\t}

\t# Column 4: Final Reform
\teternal_mandate = {
\t\ticon = mission_unite_culture
\t\trequired_missions = { celestial_examination directorate_guard harmonious_trade }
\t\tprovinces_to_highlight = {}
\t\tcompletion_trigger = {
\t\t\tnum_imperial_reforms = 8
\t\t}
\t\teffect = {
\t\t\tadd_prestige = 50
\t\t\tadd_legitimacy = 30
\t\t\tcentralize_state = yes
\t\t}
\t}
}
"""

    def _generate_hindu_dominance_missions(self) -> str:
        """Generate mission tree for Hindu-dominant countries."""
        return """# Hindu Dominance Mission Tree
# For countries following the world's major religion

hindu_dominance_missions = {
\tslot = 1
\tgeneric = no
\tai = yes

\t# Column 1: Religious Expansion
\tspread_the_dharma = {
\t\ticon = mission_religious_unity
\t\trequired_missions = {}
\t\tprovinces_to_highlight = {}
\t\tcompletion_trigger = {
\t\t\treligion = hindu
\t\t\towned_and_controlled_provinces_of_religion = { religion = hindu value = 10 }
\t\t}
\t\teffect = {
\t\t\tadd_missionary = 1
\t\t\tadd_church_loyalty = 15
\t\t}
\t}

\ttemple_of_the_ages = {
\t\ticon = mission_church
\t\trequired_missions = { spread_the_dharma }
\t\tprovinces_to_highlight = {}
\t\tcompletion_trigger = {
\t\t\tstability = 3
\t\t\treligious_unity = 1.0
\t\t}
\t\teffect = {
\t\t\tadd_prestige = 30
\t\t\tadd_institution_progress = { which = printing_press value = 20 }
\t\t}
\t}

\t# Column 2: Knowledge & Institutions
\tcenter_of_learning = {
\t\ticon = mission_university
\t\trequired_missions = { spread_the_dharma }
\t\tprovinces_to_highlight = {}
\t\tcompletion_trigger = {
\t\t\tnum_of_universities = 2
\t\t}
\t\teffect = {
\t\t\tadd_adm_power = 100
\t\t\tadd_institution_progress = { which = enlightenment value = 15 }
\t\t}
\t}

\t# Column 3: Military Holy Wars
\tdefender_of_the_faith = {
\t\ticon = mission_defender_of_faith
\t\trequired_missions = { spread_the_dharma }
\t\tprovinces_to_highlight = {}
\t\tcompletion_trigger = {
\t\t\tdefender_of_faith = yes
\t\t}
\t\teffect = {
\t\t\tadd_army_morale = 0.10
\t\t\tadd_discipline = 0.025
\t\t}
\t}

\t# Column 4: Ultimate Hindu Empire
\tdharma_supreme = {
\t\ticon = mission_world_conqueror
\t\trequired_missions = { temple_of_the_ages center_of_learning defender_of_the_faith }
\t\tprovinces_to_highlight = {}
\t\tcompletion_trigger = {
\t\t\ttotal_development = 200
\t\t\tnum_of_allies = 3
\t\t}
\t\teffect = {
\t\t\tadd_prestige = 50
\t\t\tadd_legitimacy = 25
\t\t\tadd_discipline = 0.05
\t\t}
\t}
}
"""

    def _generate_african_power_missions(self) -> str:
        """Generate mission tree for powerful African countries."""
        return """# African Power Mission Tree
# Africa is the most advanced continent in the inverted world

african_power_missions = {
\tslot = 2
\tgeneric = no
\tai = yes

\t# Column 1: Unite the Continent
\tunite_the_homeland = {
\t\ticon = mission_unite_culture
\t\trequired_missions = {}
\t\tprovinces_to_highlight = {}
\t\tcompletion_trigger = {
\t\t\towned_and_controlled_provinces_in_area = { area = west_africa_region value = 5 }
\t\t}
\t\teffect = {
\t\t\tadd_prestige = 15
\t\t\tadd_core_creation = -0.10
\t\t}
\t}

\tgolden_throne = {
\t\ticon = mission_monarch
\t\trequired_missions = { unite_the_homeland }
\t\tprovinces_to_highlight = {}
\t\tcompletion_trigger = {
\t\t\tstability = 3
\t\t\tlegitimacy = 90
\t\t}
\t\teffect = {
\t\t\tadd_legitimacy = 20
\t\t\tadd_prestige = 25
\t\t}
\t}

\t# Column 2: Trade Empire
\tcontrol_the_routes = {
\t\ticon = mission_trade_center
\t\trequired_missions = { unite_the_homeland }
\t\tprovinces_to_highlight = {}
\t\tcompletion_trigger = {
\t\t\ttrade_income = 15
\t\t}
\t\teffect = {
\t\t\tadd_global_trade_power = 0.15
\t\t\tadd_merchant = 1
\t\t}
\t}

\t# Column 3: Technological Supremacy
\tscholars_of_africa = {
\t\ticon = mission_university
\t\trequired_missions = { unite_the_homeland }
\t\tprovinces_to_highlight = {}
\t\tcompletion_trigger = {
\t\t\tnum_of_universities = 2
\t\t\tadm_tech = 8
\t\t}
\t\teffect = {
\t\t\tadd_institution_progress = { which = renaissance value = 25 }
\t\t\tadd_adm_power = 150
\t\t}
\t}

\t# Column 4: African Hegemony
\tafrica_supreme = {
\t\ticon = mission_world_conqueror
\t\trequired_missions = { golden_throne control_the_routes scholars_of_africa }
\t\tprovinces_to_highlight = {}
\t\tcompletion_trigger = {
\t\t\ttotal_development = 150
\t\t\tarmy_size = 40
\t\t}
\t\teffect = {
\t\t\tadd_prestige = 50
\t\t\tadd_discipline = 0.05
\t\t\tadd_manpower_recovery_speed = 0.10
\t\t}
\t}
}
"""

    # ─── Common Files ──────────────────────────────────────────────────

    def _export_common(self, mod_root: str) -> int:
        """Export common mod files (ideas, modifiers, defines, bookmarks)."""
        out_dir = os.path.join(mod_root, "common")
        os.makedirs(out_dir, exist_ok=True)
        count = 0

        # Copy base common files
        base_common = ["achievements.txt", "defines.lua"]
        for fname in base_common:
            src = os.path.join(self.templates_dir, "common", fname)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(out_dir, fname))
                count += 1

        # Copy ideas
        ideas_dir = os.path.join(out_dir, "ideas")
        os.makedirs(ideas_dir, exist_ok=True)
        src_ideas = os.path.join(self.templates_dir, "common", "ideas")
        if os.path.exists(src_ideas):
            for fname in os.listdir(src_ideas):
                src_file = os.path.join(src_ideas, fname)
                if os.path.isfile(src_file):
                    shutil.copy2(src_file, os.path.join(ideas_dir, fname))
                    count += 1

        # Copy triggered modifiers
        tm_dir = os.path.join(out_dir, "triggered_modifiers")
        os.makedirs(tm_dir, exist_ok=True)
        src_tm = os.path.join(self.templates_dir, "common", "triggered_modifiers")
        if os.path.exists(src_tm):
            for fname in os.listdir(src_tm):
                src_file = os.path.join(src_tm, fname)
                if os.path.isfile(src_file):
                    shutil.copy2(src_file, os.path.join(tm_dir, fname))
                    count += 1

        # Copy event modifiers
        em_dir = os.path.join(out_dir, "event_modifiers")
        os.makedirs(em_dir, exist_ok=True)
        src_em = os.path.join(self.templates_dir, "common", "event_modifiers")
        if os.path.exists(src_em):
            for fname in os.listdir(src_em):
                src_file = os.path.join(src_em, fname)
                if os.path.isfile(src_file):
                    shutil.copy2(src_file, os.path.join(em_dir, fname))
                    count += 1

        # Generate custom bookmarks
        bookmarks_dir = os.path.join(out_dir, "bookmarks")
        os.makedirs(bookmarks_dir, exist_ok=True)
        bookmark = self._generate_bookmark()
        with open(os.path.join(bookmarks_dir, "inverted_world.txt"), "w") as f:
            f.write(bookmark)
        count += 1

        # Generate custom ideas for the inverted world
        custom_ideas = self._generate_custom_ideas()
        with open(os.path.join(ideas_dir, "InvertedWorld_Ideas.txt"), "w") as f:
            f.write(custom_ideas)
        count += 1

        # Generate custom triggered modifiers
        custom_mods = self._generate_triggered_modifiers()
        with open(os.path.join(tm_dir, "InvertedWorld_Modifiers.txt"), "w") as f:
            f.write(custom_mods)
        count += 1

        # Generate religion modifiers
        rel_mods = self._generate_religion_modifiers()
        with open(os.path.join(tm_dir, "Religion_Corruption_Modifiers.txt"), "w") as f:
            f.write(rel_mods)
        count += 1

        return count

    def _generate_bookmark(self) -> str:
        """Generate bookmark file for the inverted world starting scenario."""
        lines = [
            "bookmark = {",
            '\tname = "INVERTEDWORLD_NAME"',
            '\tdesc = "INVERTEDWORLD_DESC"',
            f"\tdate = {self.config.starting_date}",
            "",
        ]
        # Add interesting countries as bookmarks
        if self.config.advanced_tags:
            for tag in self.config.advanced_tags[:5]:
                lines.append(f"\tcountry = {tag}")
            for tag in self.config.advanced_tags[:3]:
                lines.append(f"\teasy_country = {tag}")
        lines.append("}")
        return "\n".join(lines)

    def _generate_custom_ideas(self) -> str:
        """Generate national ideas for custom countries."""
        ideas = """# Custom National Ideas for the Inverted World
# Advanced African/Asian nations get powerful ideas

celestial_directorate_ideas = {
\tstart = {
\t\timperial_authority = 0.1
\t\tlegitimacy = 1.0
\t}
\tbonus = {
\t\tdiscipline = 0.05
\t}
\ttrigger = {
\t\tis_celestial_emperor = yes
\t}
\tfree = yes

\tcelestial_mandate = {
\t\tcore_creation_cost = -0.15
\t}
\tbureau_of_rites = {
\t\tmissionary_strength = 0.10
\t}
\tcelestial_examination = {
\t\tadvisor_cost = -0.20
\t}
\tdirectorate_guard = {
\t\tland_morale = 0.10
\t}
\tharmonious_trade = {
\t\tglobal_trade_power = 0.10
\t}
\tcelestial_diplomacy = {
\t\tdiplomatic_reputation = 2
\t}
\tdirectorate_treasury = {
\t\tglobal_tax_modifier = 0.10
\t}
\teternal_mandate = {
\t\tstability_cost = -0.20
\t}
}

hindu_empire_ideas = {
\tstart = {
\t\tmissionary = 1
\t\tchurch_loyalty = 0.25
\t}
\tbonus = {
\t\tinstitution_spread = 0.10
\t}
\ttrigger = {
\t\treligion = hindu
\t\ttotal_development = 100
\t}
\tfree = yes

\tdharma_spread = {
\t\tmissionary_strength = 0.15
\t}
\tvedic_scholars = {
\t\ttechnology_cost = -0.05
\t}
\twar_elephants = {
\t\tcavalry_power = 0.10
\t}
\ttemple_wealth = {
\t\tglobal_tax_modifier = 0.15
\t}
\tcaste_system = {
\t\tproduction_efficiency = 0.10
\t}
\tocean_trade = {
\t\tglobal_ship_trade_power = 0.15
\t}
\tguru_wisdom = {
\t\tidea_cost = -0.10
\t}
}

african_kingdom_ideas = {
\tstart = {
\t\tmanpower_recovery_speed = 0.10
\t\tland_morale = 0.05
\t}
\tbonus = {
\t\tinfantry_power = 0.10
\t}
\ttrigger = {
\t\tOR = {
\t\t\ttechnology_group = west_african
\t\t\ttechnology_group = east_african
\t\t}
\t}
\tfree = yes

\twarrior_tradition = {
\t\tinfantry_power = 0.10
\t}
\tgolden_trade = {
\t\tglobal_trade_power = 0.10
\t}
\toral_historians = {
\t\tidea_cost = -0.10
\t}
\tancestral_spirits = {
\t\tmissionary_strength = 0.10
\t}
\tsahel_caravans = {
\t\ttrade_range = 50
\t}
\tiron_smelting = {
\t\tproduction_efficiency = 0.10
\t}
\tgreat_mosques = {
\t\tdevelopment_cost = -0.10
\t}
}
"""
        return ideas

    def _generate_triggered_modifiers(self) -> str:
        """Generate triggered modifiers for the inverted world."""
        return """# Triggered Modifiers for the Inverted World

# Advanced tech group bonuses
advanced_african = {
\tpotential = {
\t\tOR = {
\t\t\ttechnology_group = west_african
\t\t\ttechnology_group = east_african
\t\t}
\t}
\tinstitution_spread = 0.05
\ttechnology_cost = -0.05
}

advanced_asian = {
\tpotential = {
\t\tOR = {
\t\t\ttechnology_group = chinese
\t\t\ttechnology_group = indian
\t\t}
\t}
\tinstitution_spread = 0.08
\ttechnology_cost = -0.08
}

# Primitive European penalties
primitive_european = {
\tpotential = {
\t\tOR = {
\t\t\ttechnology_group = western
\t\t\ttechnology_group = eastern
\t\t}
\t}
\ttechnology_cost = 0.20
\tinstitution_spread = -0.10
}

# Hindu religious bonus
hindu_dominant_faith = {
\tpotential = {
\t\treligion = hindu
\t}
\tmissionary_strength = 0.05
\tstability_cost_modifier = -0.10
}
"""

    def _generate_religion_modifiers(self) -> str:
        """Generate religion corruption modifiers."""
        lines = ["# Religion Corruption Modifiers", "# Islamic and Christian religions are weak and corrupted", ""]
        for rel, data in RELIGION_HIERARCHY.items():
            if data["corruption"] > 0 or data["institution_bonus"] < 0:
                lines.extend([
                    f"{rel}_corruption = {{",
                    f"\tpotential = {{",
                    f"\t\treligion = {rel}",
                    f"\t}}",
                    f"\tcorruption = {data['corruption']:.2f}",
                    f"\tinstitution_spread = {data['institution_bonus']:.2f}",
                    f"}}",
                    "",
                ])
        return "\n".join(lines)

    # ─── Localisation ──────────────────────────────────────────────────

    def _export_localisation(self, mod_root: str) -> int:
        """Export localisation files for all custom content."""
        out_dir = os.path.join(mod_root, "localisation")
        os.makedirs(out_dir, exist_ok=True)
        count = 0

        # Copy base localisation
        src_loc = os.path.join(self.templates_dir, "localisation")
        if os.path.exists(src_loc):
            for fname in os.listdir(src_loc):
                src_file = os.path.join(src_loc, fname)
                if os.path.isfile(src_file):
                    shutil.copy2(src_file, os.path.join(out_dir, fname))
                    count += 1

        # Generate custom localisation
        loc = self._generate_localisation()
        with open(os.path.join(out_dir, "inverted_world_l_english.yml"), "wb") as f:
            # EU4 YML localisation files must have UTF-8 BOM
            f.write(b'\xef\xbb\xbf')
            f.write(loc.encode('utf-8'))
        count += 1

        return count

    def _generate_localisation(self) -> str:
        """Generate localisation strings for all custom content."""
        lines = [
            "l_english:",
            "",
            " # Mod Name",
            ' INVERTEDWORLD_NAME: "Inverted World"',
            ' INVERTEDWORLD_DESC: "A world where Africa and Asia are the centers of civilization, '
            'Hindu is the dominant faith, and Europe languishes in backwardness."',
            "",
            " # Celestial Directorate",
            ' CELESTIAL_DIRECTORATE: "Celestial Directorate"',
            ' CELESTIAL_EMPEROR: "Celestial Director"',
            ' IS_CELESTIAL_EMPEROR: "Is Celestial Director"',
            ' IS_PART_OF_CELESTIAL_DIRECTORATE: "Is part of the Celestial Directorate"',
            "",
        ]
        # Form-nation decision localisation
        for name, data in FORM_NATION_DECISIONS.items():
            key = name.upper().replace(" ", "_")
            lines.extend([
                f' {key}_TITLE: "Form {name}"',
                f' {key}_DESC: "{data["desc"]}"',
                "",
            ])
        # Celestial Directorate reform localisation
        for i, reform in enumerate(CELESTIAL_DIRECTORATE["initial_reforms"]):
            lines.extend([
                f' CELESTIAL_REFORM_{i+1}_TITLE: "{reform.split(":")[0].strip()}"',
                f' CELESTIAL_REFORM_{i+1}_DESC: "{reform.split(":", 1)[1].strip()}"',
                "",
            ])
        # Event localisation
        event_texts = {
            "hindu_dominance.1.t": "The Great Temple",
            "hindu_dominance.1.d": "A magnificent temple has been completed, a testament to our devotion and the strength of our faith.",
            "hindu_dominance.1.a": "Glory to the divine!",
            "hindu_dominance.2.t": "Festival of Lights",
            "hindu_dominance.2.d": "The people celebrate the festival of lights with great fervor. The temples glow with a thousand lamps.",
            "hindu_dominance.2.a": "Let the celebrations begin!",
            "hindu_dominance.2.b": "Spare no expense for the gods.",
            "hindu_dominance.3.t": "Hindu Scholar Arrives",
            "hindu_dominance.3.d": "A learned scholar has arrived, bringing knowledge from distant lands.",
            "hindu_dominance.3.a": "Welcome the scholar.",
            "hindu_dominance.4.t": "Pagan Revival",
            "hindu_dominance.4.d": "The ancient traditions are experiencing a revival among our people.",
            "hindu_dominance.4.a": "Embrace the old ways.",
            "hindu_dominance.4.b": "Focus on material gains.",
            "corrupted_faith.1.t": "Corrupt Clergy Exposed",
            "corrupted_faith.1.d": "Scandal rocks the religious establishment as corruption is exposed at the highest levels.",
            "corrupted_faith.1.a": "Cover it up.",
            "corrupted_faith.1.b": "Root out the corruption.",
            "corrupted_faith.2.t": "Schism and Division",
            "corrupted_faith.2.d": "Religious divisions tear at the fabric of our society.",
            "corrupted_faith.2.a": "Let the schism deepen.",
            "corrupted_faith.2.b": "Embrace the reform movement.",
            "corrupted_faith.3.t": "Weak Church, Weak State",
            "corrupted_faith.3.d": "The corruption of the church has infected the state itself.",
            "corrupted_faith.3.a": "Accept the decay.",
            "corrupted_faith.3.b": "Invest in reform.",
            "celestial_directorate.1.t": "Director's Mandate",
            "celestial_directorate.1.d": "The Celestial Director exercises divine authority over the member states.",
            "celestial_directorate.1.a": "Strengthen the mandate.",
            "celestial_directorate.1.b": "Fill the treasury instead.",
            "celestial_directorate.2.t": "Directorate Reforms",
            "celestial_directorate.2.d": "The reforms of the Celestial Directorate are bearing fruit.",
            "celestial_directorate.2.a": "Consolidate authority.",
            "celestial_directorate.2.b": "Develop the provinces.",
            "celestial_directorate.3.t": "Prince Joins Directorate",
            "celestial_directorate.3.d": "A new prince has joined the Celestial Directorate, strengthening our cause.",
            "celestial_directorate.3.a": "Welcome the new member.",
            "celestial_directorate.3.b": "Accept the tribute.",
            "celestial_directorate.4.t": "Directorate Civil War",
            "celestial_directorate.4.d": "Civil war threatens to tear the Celestial Directorate apart!",
            "celestial_directorate.4.a": "The mandate is lost!",
            "celestial_directorate.4.b": "Buy peace at any cost.",
            "tech_inversion.1.t": "African Golden Age",
            "tech_inversion.1.d": "Our civilization enters a golden age of learning and prosperity.",
            "tech_inversion.1.a": "Embrace the golden age!",
            "tech_inversion.2.t": "Asian Innovation",
            "tech_inversion.2.d": "Our scholars have made a groundbreaking discovery.",
            "tech_inversion.2.a": "Fund more research!",
            "tech_inversion.3.t": "European Backwardness",
            "tech_inversion.3.d": "Our primitive society falls further behind the civilized world.",
            "tech_inversion.3.a": "Accept our fate.",
            "tech_inversion.3.b": "At least maintain order.",
            "tech_inversion.4.t": "Transfer of Knowledge",
            "tech_inversion.4.d": "Knowledge flows from our great centers of learning.",
            "tech_inversion.4.a": "Spread the knowledge!",
            "PURIFY_FAITH_HINDU_TITLE": "Purify the Faith",
            "PURIFY_FAITH_HINDU_DESC": "Cleanse our religion of any impurities and strengthen our devotion.",
            "ROOT_CORRUPTION_CHRISTIAN_TITLE": "Root Out Corruption",
            "ROOT_CORRUPTION_CHRISTIAN_DESC": "The church is rotten to the core. We must attempt to reform it.",
            "EMBRACE_TRUE_FAITH_PAGAN_TITLE": "Embrace True Faith",
            "EMBRACE_TRUE_FAITH_PAGAN_DESC": "The ancient spirits call us back to the true path.",
        }
        for key, text in event_texts.items():
            lines.append(f' {key}: "{text}"')
        lines.append("")
        return "\n".join(lines)

    # ─── History Templates ──────────────────────────────────────────────

    def _export_history_templates(self, mod_root: str) -> int:
        """Export history templates (advisors, diplomacy)."""
        out_dir = os.path.join(mod_root, "history")
        os.makedirs(out_dir, exist_ok=True)
        count = 0

        # Copy base history templates
        src_hist = os.path.join(self.templates_dir, "history")
        if os.path.exists(src_hist):
            for subdir in os.listdir(src_hist):
                src_sub = os.path.join(src_hist, subdir)
                if os.path.isdir(src_sub):
                    dst_sub = os.path.join(out_dir, subdir)
                    os.makedirs(dst_sub, exist_ok=True)
                    for fname in os.listdir(src_sub):
                        src_file = os.path.join(src_sub, fname)
                        if os.path.isfile(src_file):
                            shutil.copy2(src_file, os.path.join(dst_sub, fname))
                            count += 1

        # Generate custom diplomacy for Celestial Directorate
        dip_dir = os.path.join(out_dir, "diplomacy")
        os.makedirs(dip_dir, exist_ok=True)
        cd_dip = self._generate_celestial_directorate_diplomacy()
        with open(os.path.join(dip_dir, "CelestialDirectorate.txt"), "w") as f:
            f.write(cd_dip)
        count += 1

        return count

    def _generate_celestial_directorate_diplomacy(self) -> str:
        """Generate initial diplomacy for the Celestial Directorate."""
        lines = [
            "# Celestial Directorate Initial Diplomacy",
            "# Member states start in alliance with the Director",
            "",
        ]
        if self.config.celestial_director_tags:
            director = self.config.celestial_director_tags[0]
            members = self.config.celestial_director_tags[1:]
            for member in members[:10]:  # Max 10 alliance members
                lines.extend([
                    "alliance = {",
                    f"\tfirst = {director}",
                    f"\tsecond = {member}",
                    "\tstart_date = 1444.11.11",
                    "}",
                    "",
                ])
            # Guarantee relationships
            for member in members[10:20]:
                lines.extend([
                    "guarantee = {",
                    f"\tfirst = {director}",
                    f"\tsecond = {member}",
                    "\tstart_date = 1444.11.11",
                    "}",
                    "",
                ])
        return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MOD DESCRIPTOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_mod_descriptor(mod_name: str, mod_path: str, version: str = "1.0") -> str:
    """Generate the .mod file for the total conversion."""
    return f'''# Inverted World - EU4 Total Conversion Mod
name = "{mod_name}"
path = "mod/{mod_path}"
supported_version = "1.34.*"
version = "{version}"
tags = {{
\t"Alternative History"
\t"Total Conversion"
\t"Gameplay"
}}
picture = "thumbnail.png"
'''


def generate_descriptor_mod(mod_name: str, mod_path: str) -> str:
    """Generate the descriptor.mod inside the mod folder."""
    return f'''name = "{mod_name}"
supported_version = "1.34.*"
'''
