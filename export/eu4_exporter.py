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
            width, height, max_provinces, sea_ids, wasteland_ids
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
 
