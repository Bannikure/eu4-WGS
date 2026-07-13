"""
Module 4: EU4 Complete Mod File Export System
================================================
Handles exporting all generated data into proper EU4 mod file formats,
including province bitmaps, history files, common files, localization,
and .mod descriptor files.
"""

import os
import csv
import json
import shutil
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

import eu4_wgs_v8
from eu4_wgs_v8.common.io_utils import ensure_dir, write_text, save_image


# ═══════════════════════════════════════════════════════════════
#  MOD DIRECTORY STRUCTURE
# ═══════════════════════════════════════════════════════════════

MOD_SUBDIRS = [
    "common/countries",
    "common/country_tags",
    "common/cultures",
    "common/ideas",
    "common/prices",
    "common/religions",
    "common/trade_goods",
    "common/tradenodes",
    "common/imperial_reforms",
    "common/event_modifiers",
    "common/church_aspects",
    "common/province_names",
    "history/countries",
    "history/provinces",
    "history/diplomacy",
    "map",
    "gfx/flags",
    "localisation",
    "events",
    "missions",
    "common/on_actions",
]


# ═══════════════════════════════════════════════════════════════
#  MAP FILE EXPORTERS
# ═══════════════════════════════════════════════════════════════

class MapFileExporter:
    """Exports all map-related bitmap and configuration files."""

    def __init__(self, output_dir: str, map_height: int = 2048):
        self.output_dir = output_dir
        self.map_height = map_height
        self.map_dir = f"{output_dir}/map"
        ensure_dir(self.map_dir)

    def save_heightmap(self, heightmap: np.ndarray) -> str:
        """Save heightmap.bmp."""
        return save_image(heightmap, f"{self.map_dir}/heightmap.bmp")

    def save_provinces_bmp(self, provinces_bmp: np.ndarray) -> str:
        """Save provinces.bmp."""
        return save_image(provinces_bmp, f"{self.map_dir}/provinces.bmp")

    def save_world_normal(self, normal_map: np.ndarray) -> str:
        """Save world_normal.bmp."""
        return save_image(normal_map, f"{self.map_dir}/world_normal.bmp", "RGB")

    def save_terrain_bmp(self, terrain_bmp: np.ndarray) -> str:
        """Save terrain.bmp."""
        return save_image(terrain_bmp, f"{self.map_dir}/terrain.bmp", "RGB")

    def save_rivers_bmp(self, rivers_bmp: np.ndarray) -> str:
        """Save rivers.bmp."""
        return save_image(rivers_bmp, f"{self.map_dir}/rivers.bmp", "RGB")

    def save_watercolor_bmp(self, watercolor_bmp: np.ndarray) -> str:
        """Save watercolor.bmp."""
        return save_image(watercolor_bmp, f"{self.map_dir}/watercolor.bmp", "RGB")

    def save_trees_bmp(self, width: int = 5632, height: int = 2048) -> str:
        """Generate a blank trees.bmp (required by EU4)."""
        blank = np.zeros((height, width, 4), dtype=np.uint8)
        return save_image(blank, f"{self.map_dir}/trees.bmp", "RGBA")

    def write_definition_csv(self, province_infos: list) -> str:
        """
        Writes the EU4 province color registry CSV.
        Format: province;red;green;blue;name;x
        """
        path = f"{self.map_dir}/definition.csv"
        with open(path, "w", newline="", encoding="cp1252") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["province", "red", "green", "blue", "name", "x"])
            for p in province_infos:
                r, g, b = p.color
                name = f"Province_{p.id}" if p.is_sea else self._generate_province_name(p)
                writer.writerow([p.id, r, g, b, name, "x"])
        return path

    def write_default_map(self, max_provinces: int, sea_ids: list,
                           wasteland_ids: list) -> str:
        """Writes the standard EU4 default.map."""
        sea_str = " ".join(map(str, sea_ids))
        wasteland_str = " ".join(map(str, wasteland_ids))

        content = f"""# default.map for 5632x2048 framework

width = 5632
height = 2048
max_provinces = {max_provinces}

definitions = "definition.csv"
provinces = "provinces.bmp"
positions = "positions.txt"
terrain = "terrain.bmp"
rivers = "rivers.bmp"
terrain_definition = "terrain.txt"
heightmap = "heightmap.bmp"
tree_definition = "trees.bmp"
continent = "continent.txt"
adjacencies = "adjacencies.csv"
climate = "climate.txt"

sea_starts = {{
\t{sea_str}
}}

only_titles = {{
\t{wasteland_str}
}}

canal_definition = "canal_definitions.txt"
"""
        return write_text(f"{self.map_dir}/default.map", content)

    def write_positions_txt(self, positions_data: Dict[int, Dict]) -> str:
        """Writes all province position blocks to positions.txt."""
        path = f"{self.map_dir}/positions.txt"
        with open(path, "w", encoding="utf-8") as f:
            for p_id, pos in positions_data.items():
                f.write(
                    f"{p_id} = {{\n"
                    f"\tposition = {{\n"
                    f"\t\t{pos.get('bc_x', 0)}.000 {pos.get('bc_y', 0)}.000\n"
                    f"\t\t{pos.get('unit_x', 0)}.000 {pos.get('unit_y', 0)}.000\n"
                    f"\t\t{pos.get('text_x', 0)}.000 {pos.get('text_y', 0)}.000\n"
                    f"\t}}\n"
                    f"\trotation = {{ 0.000 0.000 0.000 }}\n"
                    f"}}\n\n"
                )
        return path

    def write_continent_txt(self, province_infos: list) -> str:
        """Writes continent.txt grouping provinces by continent."""
        path = f"{self.map_dir}/continent.txt"

        continents: Dict[str, list] = {}
        for p in province_infos:
            if p.is_sea or p.is_wasteland:
                continue
            cont = p.continent_name
            if cont not in continents:
                continents[cont] = []
            continents[cont].append(p.id)

        with open(path, "w", encoding="utf-8") as f:
            for cont_name, prov_ids in continents.items():
                prov_str = " ".join(map(str, prov_ids))
                f.write(f"{cont_name} = {{\n\t{prov_str}\n}}\n\n")
        return path

    def write_climate_txt(self, climate_zones: Dict[str, List[int]]) -> str:
        """Writes climate.txt from pre-computed climate zones."""
        path = f"{self.map_dir}/climate.txt"

        with open(path, "w", encoding="utf-8") as f:
            for zone_name, prov_ids in climate_zones.items():
                prov_str = " ".join(map(str, prov_ids))
                f.write(f"{zone_name} = {{ {prov_str} }}\n")
        return path

    def write_terrain_txt(self) -> str:
        """Writes terrain.txt defining terrain categories."""
        content = """# Terrain categories definition
category = {
    name = "ocean"
    terrain = ocean
    color = { 0 40 80 }
    is_water = yes
}
category = {
    name = "deep_ocean"
    terrain = ocean
    color = { 0 20 60 }
    is_water = yes
}
category = {
    name = "farmland"
    terrain = farmland
    color = { 80 140 60 }
    movement_cost = 1.0
}
category = {
    name = "grasslands"
    terrain = grasslands
    color = { 100 160 70 }
    movement_cost = 1.0
}
category = {
    name = "forest"
    terrain = forest
    color = { 60 120 50 }
    movement_cost = 1.2
}
category = {
    name = "hills"
    terrain = hills
    color = { 100 130 70 }
    movement_cost = 1.3
}
category = {
    name = "mountain"
    terrain = mountain
    color = { 90 90 90 }
    movement_cost = 1.5
}
category = {
    name = "desert"
    terrain = desert
    color = { 220 200 130 }
    movement_cost = 1.2
}
category = {
    name = "jungle"
    terrain = jungle
    color = { 40 100 40 }
    movement_cost = 1.3
}
category = {
    name = "marsh"
    terrain = marsh
    color = { 100 140 90 }
    movement_cost = 1.3
}
category = {
    name = "coastal_desert"
    terrain = coastal_desert
    color = { 240 220 160 }
    movement_cost = 1.1
}
category = {
    name = "steppe"
    terrain = steppe
    color = { 180 170 120 }
    movement_cost = 1.0
}
category = {
    name = "tundra"
    terrain = tundra
    color = { 180 180 180 }
    movement_cost = 1.2
}
category = {
    name = "ice_sheet"
    terrain = ice_sheet
    color = { 220 220 240 }
    movement_cost = 1.5
}
"""
        return write_text(f"{self.map_dir}/terrain.txt", content)

    def write_adjacencies_csv(self) -> str:
        """Writes a basic adjacencies.csv (required by EU4)."""
        path = f"{self.map_dir}/adjacencies.csv"
        with open(path, "w", newline="", encoding="cp1252") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["From", "To", "Type", "Through", "start_x", "start_y",
                             "stop_x", "stop_y", "adjacency_name", "Comment"])
        return path

    def _generate_province_name(self, province) -> str:
        """Generate a flavorful province name based on continent."""
        from eu4_wgs_v8.content.world_content import CultureGenerator

        y = province.center_y

        prefixes_adv = ["Sunset", "Golden", "Celestial", "Sacred", "Royal",
                        "Eternal", "Divine", "Grand", "Supreme", "Radiant"]
        prefixes_prim = ["Muddy", "Grey", "Bramble", "Withered", "Rusted",
                         "Foggy", "Bleak", "Sodden", "Drab", "Grim"]
        suffixes_adv = ["Vihar", "Puri", "Nagar", "Sthan", "Dham",
                        "Pura", "Khand", "Bhumi", "Sagar", "Mandal"]
        suffixes_prim = ["wick", "ford", "moor", "den", "ton",
                         "field", "vale", "mere", "croft", "thorp"]

        if self.map_height * 0.25 <= y < self.map_height * 0.75:
            return f"{random.choice(prefixes_adv)}_{random.choice(suffixes_adv)}_{province.id}"
        else:
            return f"{random.choice(prefixes_prim)}_{random.choice(suffixes_prim)}_{province.id}"


import random


# ═══════════════════════════════════════════════════════════════
#  COUNTRY FILE EXPORTERS
# ═══════════════════════════════════════════════════════════════

class CountryFileExporter:
    """Exports country common files, history files, and localization."""

    def __init__(self, output_dir: str, map_height: int = 2048):
        self.map_height = map_height
        self.output_dir = output_dir

    def write_country_common_file(self, tag: str, country_data) -> str:
        """Creates common/countries/TAG.txt with map color and baseline settings."""
        ensure_dir(f"{self.output_dir}/common/countries")
        r, g, b = country_data.color

        graph_culture = "indian" if country_data.is_advanced else "western"
        personality = "administrative" if country_data.is_advanced else "balanced"

        content = f"""# Country settings for {tag} - {country_data.short_name}
graphical_culture = {graph_culture}
color = {{ {r} {g} {b} }}
color2 = {{ {min(r+40,255)} {min(g+40,255)} {min(b+40,255)} }}
historical_score = {100 if country_data.is_advanced else 20}
tech_group = {country_data.tech_group}
ai_personality = {personality}

# Government
government = {country_data.government}
"""
        return write_text(f"{self.output_dir}/common/countries/{tag}.txt", content)

    def write_country_tags(self, countries: Dict[str, Any]) -> str:
        """Writes common/country_tags/00_countries.txt."""
        ensure_dir(f"{self.output_dir}/common/country_tags")
        path = f"{self.output_dir}/common/country_tags/00_countries.txt"

        with open(path, "w", encoding="utf-8") as f:
            for tag, data in countries.items():
                f.write(f'{tag} = "countries/{tag}.txt"\n')
        return path

    def write_country_history_file(self, tag: str, country_data) -> str:
        """Writes history/countries/TAG - Name.txt with tech and ruler data."""
        ensure_dir(f"{self.output_dir}/history/countries")

        inst = country_data.institutions if hasattr(country_data, 'institutions') else [0]*8
        inst_str = "\n".join(
            f"\t{inst[i]} # Institution {i+1}"
            for i in range(min(len(inst), 8))
        )

        content = f"""# History for {country_data.short_name} ({tag})
government = {country_data.government}
technology_group = {country_data.tech_group}

technology_table = {{
\tadm_tech = {country_data.adm}
\tdip_tech = {country_data.dip}
\tmil_tech = {country_data.mil}
}}

embraced_institutions = {{
{inst_str}
}}

primary_culture = {country_data.primary_culture}
religion = {country_data.religion}
mercantilism = {50 if country_data.is_advanced else 5}

1444.11.11 = {{
    capital = {country_data.capital_province}
    monarch = {{
        name = "{country_data.ruler_name}"
        adm = {country_data.ruler_adm}
        dip = {country_data.ruler_dip}
        mil = {country_data.ruler_mil}
        age = {country_data.ruler_age}
        regent = no
    }}
}}
"""
        filename = f"{tag} - {country_data.short_name}.txt"
        return write_text(f"{self.output_dir}/history/countries/{filename}", content)

    def write_national_ideas(self, tag: str, center_y: int) -> str:
        """Write national ideas file for a country."""
        from eu4_wgs_v8.content.world_content import IdeaGenerator
        ensure_dir(f"{self.output_dir}/common/ideas")

        ideas_content = IdeaGenerator.generate_national_ideas(tag, center_y, map_height=self.map_height)
        return write_text(f"{self.output_dir}/common/ideas/{tag}_ideas.txt", ideas_content)

    def write_localization(self, countries: Dict[str, Any]) -> str:
        """Writes display name definitions to the mod localisation folder."""
        ensure_dir(f"{self.output_dir}/localisation")
        path = f"{self.output_dir}/localisation/custom_countries_l_english.yml"

        content = "l_english:\n"
        for tag, data in countries.items():
            content += f' {tag}:0 "{data.short_name}"\n'
            content += f' {tag}_ADJ:0 "{data.short_name}an"\n'
            content += f' {tag}_DEF:0 "{data.full_name}"\n'

        return write_text(path, content, encoding="utf-8-sig")


# ═══════════════════════════════════════════════════════════════
#  PROVINCE HISTORY EXPORTER
# ═══════════════════════════════════════════════════════════════

class ProvinceHistoryExporter:
    """Exports province history files for each land province."""

    def __init__(self, output_dir: str, map_height: int = 2048):
        self.map_height = map_height
        self.output_dir = f"{output_dir}/history/provinces"
        ensure_dir(self.output_dir)

    def write_province_history(self, province, country_tag: str = "FRA",
                                country_data=None) -> str:
        """Generates a historically compliant EU4 province script file."""
        from eu4_wgs_v8.analytics.heightmap_analyzer import HeightmapAnalyzer

        analyzer = HeightmapAnalyzer()
        dev = analyzer._compute_inverted_development(province)
        religion = analyzer._assign_inverted_religion(province)

        # Split development into tax/prod/manpower
        if dev >= 20:
            base_tax = max(3, dev // 3 + random.randint(0, 2))
            base_prod = max(3, dev // 3 + random.randint(0, 2))
            base_manpower = max(2, dev - base_tax - base_prod)
        elif dev >= 10:
            base_tax = max(2, dev // 3)
            base_prod = max(2, dev // 3)
            base_manpower = max(1, dev - base_tax - base_prod)
        else:
            base_tax = max(1, dev // 3 + 1)
            base_prod = max(1, dev // 3)
            base_manpower = max(1, dev - base_tax - base_prod + 1)

        # Trade good assignment
        trade_good = self._assign_trade_good(province, dev)

        # Culture assignment
        from eu4_wgs_v8.content.world_content import CultureGenerator
        culture = CultureGenerator.get_culture_for_continent(province.continent_name)

        # Determine owner tag (use passed tag or default)
        owner = country_tag if country_tag else "FRA"

        province_name = f"Province_{province.id}"

        content = f"""# {province.id} - {province_name}

base_tax = {base_tax}
base_production = {base_prod}
base_manpower = {base_manpower}

trade_goods = {trade_good}
culture = {culture}
religion = {religion}
capital = "{province_name}"
hre = {"yes" if province.is_island else "no"}

1444.11.11 = {{
    owner = {owner}
    controller = {owner}
    add_core = {owner}
    discovered_by = {province.latitude_band.replace('_', ' ')}
}}
"""
        filename = f"{province.id} - {province_name}.txt"
        return write_text(f"{self.output_dir}/{filename}", content)

    def _assign_trade_good(self, province, development: int) -> str:
        """Assigns trade good based on continent and development."""
        from eu4_wgs_v8.content.world_content import RICH_COMMODITIES, BARREN_COMMODITIES

        y = province.center_y
        is_advanced = (self.map_height * 0.25 <= y < self.map_height * 0.75)

        if is_advanced:
            if province.terrain_type == "mountain":
                return random.choice(["diamond_dust", "iron", "gold"])
            elif province.terrain_type in ("jungle", "forest"):
                return random.choice(["solar_silk", "celestial_spice", "sacred_incense"])
            elif province.is_island:
                return random.choice(["abyssal_pearls", "island_nectar", "spiceweave_glass"])
            else:
                return random.choice(list(RICH_COMMODITIES.keys()))
        else:
            return random.choice(list(BARREN_COMMODITIES.keys()) + ["grain", "fish", "wool"])


# ═══════════════════════════════════════════════════════════════
#  MOD DESCRIPTOR EXPORTER
# ═══════════════════════════════════════════════════════════════

class ModDescriptorExporter:
    """Writes .mod descriptor files."""

    @staticmethod
    def write_mod_descriptor(mod_name: str, tech_name: str,
                              output_dir: str) -> Tuple[str, str]:
        """
        Writes both the .mod pointer file and the in-mod descriptor.
        Returns (pointer_path, descriptor_path).
        """
        # Pointer file (in EU4 mod directory)
        pointer_content = (
            f'name="{mod_name}"\n'
            f'path="mod/{tech_name}"\n'
            f'supported_version="1.37.*.*"\n'
            f'tags={{\n\t"Total Conversion"\n\t"Map"\n\t"Alternative History"\n}}\n'
        )
        pointer_path = write_text(f"{output_dir}/{tech_name}.mod", pointer_content)

        # In-mod descriptor
        descriptor_path = write_text(f"{output_dir}/descriptor.mod", pointer_content)

        return pointer_path, descriptor_path


# ═══════════════════════════════════════════════════════════════
#  MASTER EXPORT ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════

class MasterExportOrchestrator:
    """
    Coordinates the complete mod export pipeline.
    Assembles all data from map generation, content generation,
    and analytics into a complete EU4 mod structure.
    """

    def __init__(self, output_base_dir: str, map_height: int = 2048):
        self.output_base_dir = output_base_dir
        self.map_height = map_height

    def create_mod_structure(self, mod_name: str) -> str:
        """Create the full mod directory structure."""
        tech_name = mod_name.lower().replace(" ", "_")
        mod_root = os.path.join(self.output_base_dir, tech_name)

        if os.path.exists(mod_root):
            shutil.rmtree(mod_root)

        for subdir in MOD_SUBDIRS:
            ensure_dir(os.path.join(mod_root, subdir))

        return mod_root

    def export_complete_mod(self, mod_name: str,
                             heightmap: np.ndarray,
                             land_mask: np.ndarray,
                             provinces_bmp: np.ndarray,
                             province_infos: list,
                             countries: Dict[str, Any],
                             climate_zones: Dict[str, list],
                             is_micro: bool = False,
                             terrain_bmp: Optional[np.ndarray] = None,
                             rivers_bmp: Optional[np.ndarray] = None) -> Dict[str, str]:
        """
        Execute the complete mod export pipeline.
        Returns a dict of {file_type: path} for all exported files.
        """
        tech_name = mod_name.lower().replace(" ", "_")
        mod_root = self.create_mod_structure(mod_name)
        exported_files = {}
        height, width = heightmap.shape[:2]

        # ── Map files ──────────────────────────────────────────
        map_exporter = MapFileExporter(mod_root, map_height=self.map_height)

        exported_files["heightmap"] = map_exporter.save_heightmap(heightmap)

        from eu4_wgs_v8.engine.map_generation import NormalMapGenerator, WatercolorGenerator
        normal_map = NormalMapGenerator.generate(heightmap)
        exported_files["world_normal"] = map_exporter.save_world_normal(normal_map)

        watercolor = WatercolorGenerator.generate(land_mask)
        exported_files["watercolor"] = map_exporter.save_watercolor_bmp(watercolor)

        exported_files["provinces"] = map_exporter.save_provinces_bmp(provinces_bmp)

        if terrain_bmp is None:
            from eu4_wgs_v8.engine.map_generation import TerrainClassifier
            terrain_cls = TerrainClassifier(width=width, height=height)
            terrain_bmp = terrain_cls.generate_terrain_bmp(heightmap, land_mask)
        exported_files["terrain"] = map_exporter.save_terrain_bmp(terrain_bmp)

        if rivers_bmp is None:
            from eu4_wgs_v8.engine.map_generation import RiverGenerator
            river_gen = RiverGenerator(width=width, height=height)
            rivers_bmp, _ = river_gen.generate_rivers(heightmap, land_mask)
        exported_files["rivers"] = map_exporter.save_rivers_bmp(rivers_bmp)

        exported_files["trees"] = map_exporter.save_trees_bmp(width, height)
        exported_files["definition_csv"] = map_exporter.write_definition_csv(province_infos)

        # Compute sea and wasteland IDs
        sea_ids = [p.id for p in province_infos if p.is_sea]
        wasteland_ids = [p.id for p in province_infos if p.is_wasteland]
        max_provinces = len(province_infos) + 1

        exported_files["default_map"] = map_exporter.write_default_map(
            max_provinces, sea_ids, wasteland_ids
        )

        # Compute positions
        positions_data = self._compute_positions(province_infos)
        exported_files["positions"] = map_exporter.write_positions_txt(positions_data)

        exported_files["continent"] = map_exporter.write_continent_txt(province_infos)
        exported_files["climate"] = map_exporter.write_climate_txt(climate_zones)
        exported_files["terrain_txt"] = map_exporter.write_terrain_txt()
        exported_files["adjacencies"] = map_exporter.write_adjacencies_csv()

        # ── Country files ──────────────────────────────────────
        country_exporter = CountryFileExporter(mod_root, map_height=self.map_height)

        for tag, data in countries.items():
            country_exporter.write_country_common_file(tag, data)
            country_exporter.write_country_history_file(tag, data)
            country_exporter.write_national_ideas(tag, data.center_y)
            FlagGenerator.generate_flag(tag, data.is_advanced, mod_root,
                                          assets_path=str(eu4_wgs_v8.ASSETS_DIR),
                                          continent=data.continent,
                                          seed=hash(tag) % (2**31))

        exported_files["country_tags"] = country_exporter.write_country_tags(countries)
        exported_files["localization"] = country_exporter.write_localization(countries)

        # ── Province histories ─────────────────────────────────
        prov_exporter = ProvinceHistoryExporter(mod_root, map_height=self.map_height)

        # Assign provinces to countries
        country_assignments = self._assign_provinces_to_countries(
            province_infos, countries
        )

        for p in province_infos:
            if p.is_sea or p.is_wasteland:
                continue
            owner_tag = country_assignments.get(p.id, list(countries.keys())[0] if countries else "FRA")
            prov_exporter.write_province_history(p, owner_tag)

        # ── Content files (religions, cultures, etc.) ──────────
        from eu4_wgs_v8.content.world_content import (
            ReligionGenerator, CultureGenerator, TradeGenerator,
            CelestialDirectorate, DiplomacyGenerator
        )

        exported_files["religions"] = ReligionGenerator.generate_religion_file(mod_root)
        exported_files["holy_modifier"] = ReligionGenerator.generate_holy_city_modifier_file(mod_root)
        exported_files["church_aspects"] = ReligionGenerator.generate_corrupt_church_aspects(mod_root)

        # Find a Hindu holy center province
        hindu_center = self._find_hindu_center(province_infos)
        if hindu_center:
            exported_files["hindu_events"] = ReligionGenerator.generate_hindu_holy_center_event(
                mod_root, hindu_center
            )

        exported_files["cultures"] = CultureGenerator.generate_cultures_file(mod_root)

        exported_files["trade_goods"] = TradeGenerator.generate_trade_goods_files(mod_root)
        exported_files["trade_nodes"] = TradeGenerator.generate_inverted_trade_nodes(
            province_infos, mod_root
        )
        exported_files["trade_events"] = TradeGenerator.generate_trade_price_events(mod_root)

        exported_files["celestial_directorate"] = CelestialDirectorate.generate_imperial_reforms(mod_root)
        exported_files["diplomacy"] = DiplomacyGenerator.generate_diplomacy(mod_root, countries)
        exported_files["war_events"] = DiplomacyGenerator.generate_war_events(mod_root)

        # ── Celestial Directorate role assignments ─────────────
        directorate_assignments = CelestialDirectorate.assign_directorate_roles(countries)
        if directorate_assignments:
            self._write_directorate_history(mod_root, directorate_assignments, countries)

        # -- Template-based mod files (decisions, events, missions, etc.) --
        from eu4_wgs_v8.export.template_exporter import TemplateExporter, TemplateExportConfig
        template_config = TemplateExportConfig(
            mod_name=mod_name,
            mod_path=tech_name,
            starting_date="1444.11.11",
            tags=list(countries.keys()),
            advanced_tags=[t for t, c in countries.items() if c.is_advanced],
            primitive_tags=[t for t, c in countries.items() if not c.is_advanced],
            hindu_tags=[t for t, c in countries.items()
                        if getattr(c, 'religion', '') == 'hindu'],
            celestial_director_tags=list(directorate_assignments.keys()) if directorate_assignments else [],
            hre_tags=[t for t, c in countries.items()
                      if getattr(c, 'religion', '') == 'catholic'],
        )
        template_exporter = TemplateExporter(template_config, templates_dir=str(eu4_wgs_v8.TEMPLATES_DIR))
        template_stats = template_exporter.export_all(mod_root)
        for category, file_count in template_stats.items():
            exported_files[f"template_{category}"] = f"{file_count} files"

        # ── Mod descriptor ─────────────────────────────────────
        descriptor_exporter = ModDescriptorExporter()
        pointer, desc = descriptor_exporter.write_mod_descriptor(
            mod_name, tech_name, mod_root
        )
        exported_files["mod_pointer"] = pointer
        exported_files["descriptor"] = desc

        return exported_files

    def _compute_positions(self, province_infos: list) -> Dict[int, Dict]:
        """Compute province positions for positions.txt."""
        positions = {}
        for p in province_infos:
            if p.is_sea:
                continue
            center_x = p.center_x
            center_y = self.map_height - p.center_y  # EU4 uses inverted Y
            positions[p.id] = {
                "bc_x": center_x,
                "bc_y": center_y,
                "unit_x": center_x + 5,
                "unit_y": center_y,
                "text_x": center_x,
                "text_y": center_y - 5,
            }
        return positions

    @staticmethod
    def _assign_provinces_to_countries(province_infos: list,
                                        countries: Dict[str, Any]) -> Dict[int, str]:
        """Assign each land province to the nearest country."""
        assignments = {}
        if not countries:
            return assignments

        country_list = list(countries.values())
        for p in province_infos:
            if p.is_sea or p.is_wasteland:
                continue

            # Find nearest country by distance
            min_dist = float('inf')
            nearest_tag = list(countries.keys())[0]

            for tag, c in countries.items():
                dist = np.hypot(p.center_x - c.center_x, p.center_y - c.center_y)
                if dist < min_dist:
                    min_dist = dist
                    nearest_tag = tag

            assignments[p.id] = nearest_tag

        return assignments

    @staticmethod
    def _find_hindu_center(province_infos: list) -> Optional[int]:
        """Find the best province for the Hindu holy center."""
        # Prefer high-development provinces in Africa/Asia
        candidates = [
            p for p in province_infos
            if not p.is_sea and not p.is_wasteland
            and any(x in p.continent_name for x in ["africa", "asia", "west_africa", "east_africa", "south_asia"])
        ]
        if candidates:
            return random.choice(candidates).id
        return None

    @staticmethod
    def _write_directorate_history(output_dir: str,
                                    assignments: Dict[str, str],
                                    countries: Dict[str, Any]) -> str:
        """Write Celestial Directorate history entries for countries."""
        ensure_dir(f"{output_dir}/history/countries")

        for tag, role in assignments.items():
            if tag in countries:
                data = countries[tag]
                # Append HRE role to country history file
                filename = f"{tag} - {data.short_name}.txt"
                path = f"{output_dir}/history/countries/{filename}"

                if os.path.exists(path):
                    write_text(path, f"\n{role}\n", mode="a")

        return output_dir


from eu4_wgs_v8.content.world_content import FlagGenerator, CountryData
