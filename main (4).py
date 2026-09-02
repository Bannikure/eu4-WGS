diff --git a/analytics/dashboard.py b/analytics/dashboard.py
index 05f0833..332b633 100644
--- a/analytics/dashboard.py
+++ b/analytics/dashboard.py
@@ -16,7 +16,7 @@ import numpy as np
 from typing import Dict, List, Any, Optional, Tuple
 from dataclasses import dataclass, asdict
 
-from eu4_wgs_v8.common.io_utils import ensure_dir, write_text
+from common.io_utils import ensure_dir, write_text
 
 
 def _json_for_script(value: Any) -> str:
diff --git a/content/world_content.py b/content/world_content.py
index 78bb213..f2829db 100644
--- a/content/world_content.py
+++ b/content/world_content.py
@@ -20,7 +20,7 @@ from dataclasses import dataclass, field
 from typing import Dict, List, Tuple, Any, Optional
 
 import eu4_wgs_v8
-from eu4_wgs_v8.common.io_utils import ensure_dir, write_text
+from common.io_utils import ensure_dir, write_text
 
 logger = logging.getLogger(__name__)
 
@@ -1348,7 +1348,7 @@ class CountryGenerator:
             tech_group = "western"
 
         # Religion (inverted)
-        from eu4_wgs_v8.analytics.heightmap_analyzer import HeightmapAnalyzer
+        from analytics.heightmap_analyzer import HeightmapAnalyzer
         religion = HeightmapAnalyzer(map_height=h)._assign_inverted_religion(province, h)
 
         # Culture
diff --git a/engine/map_generation.py b/engine/map_generation.py
index 9e1f4ef..8401532 100644
--- a/engine/map_generation.py
+++ b/engine/map_generation.py
@@ -507,8 +507,58 @@ class ProvinceGenerator:
         # Paint province bitmap
         provinces_bmp = np.zeros((self.height, self.width, 3), dtype=np.uint8)
 
-        # Sea pixels get deep blue
-        provinces_bmp[~land_mask] = [0, 40, 80]
+        # ── Sea provinces ──
+        # Ocean pixels need to be split into real, distinct sea provinces the
+        # same way land is (EU4 requires every provinces.bmp pixel to map to
+        # a definition.csv entry; a single flat "sea colour" with no matching
+        # province leaves the whole ocean undefined). Density roughly matches
+        # the land province density so sea/land provinces are similar size.
+        sea_mask = ~land_mask
+        sea_indices = np.argwhere(sea_mask)
+        total_sea_pixels = len(sea_indices)
+        sea_infos: List[ProvinceInfo] = []
+
+        if total_sea_pixels > 0:
+            pixels_per_land_province = max(total_land_pixels / max(active_seeds, 1), 1)
+            num_sea_provinces = max(1, int(total_sea_pixels / pixels_per_land_province))
+            num_sea_provinces = min(num_sea_provinces, total_sea_pixels)
+
+            sea_spots = sea_indices[
+                np.random.choice(total_sea_pixels, num_sea_provinces, replace=False)
+            ]
+            sea_seeds = [(x, y) for y, x in sea_spots]
+            sea_tree = cKDTree(sea_seeds)
+            _, sea_closest = sea_tree.query(pixel_coords, workers=-1)
+            sea_closest = sea_closest.reshape((self.height, self.width))
+
+            # Blue-toned but mutually distinct colours, kept out of the
+            # land-province colour range (10-246 on every channel).
+            sea_colors = np.column_stack([
+                np.random.randint(0, 60, size=num_sea_provinces),
+                np.random.randint(20, 90, size=num_sea_provinces),
+                np.random.randint(70, 180, size=num_sea_provinces),
+            ]).astype(np.uint8)
+
+            sea_id_start = num_provinces + 1
+            for s_idx in range(num_sea_provinces):
+                mask = (sea_closest == s_idx) & sea_mask
+                if not np.any(mask):
+                    continue
+                provinces_bmp[mask] = sea_colors[s_idx]
+                y_indices, x_indices = np.where(mask)
+                sea_infos.append(ProvinceInfo(
+                    id=sea_id_start + s_idx,
+                    color=tuple(sea_colors[s_idx].tolist()),
+                    center_x=int(np.mean(x_indices)),
+                    center_y=int(np.mean(y_indices)),
+                    pixel_count=len(x_indices),
+                    is_sea=True,
+                    terrain_type="ocean",
+                    continent_name=self._assign_continent(int(np.mean(y_indices))),
+                    latitude_band=self._assign_latitude_band(int(np.mean(y_indices))),
+                ))
+        else:
+            provinces_bmp[sea_mask] = [0, 40, 80]
 
         # Land pixels get their province color
         for p_idx in range(min(num_provinces, active_seeds + 1)):
@@ -520,6 +570,7 @@ class ProvinceGenerator:
             provinces_bmp, unique_colors, heightmap, land_mask,
             closest_indices, is_micro_world, num_provinces
         )
+        province_infos.extend(sea_infos)
 
         return provinces_bmp, province_infos, is_micro_world
 
diff --git a/engine/tunnel_generation.py b/engine/tunnel_generation.py
index 9b706cd..bcac53f 100644
--- a/engine/tunnel_generation.py
+++ b/engine/tunnel_generation.py
@@ -40,7 +40,7 @@ from typing import Dict, List, Tuple, Optional, Set
 from dataclasses import dataclass, field
 from collections import defaultdict
 
-from eu4_wgs_v8.common.io_utils import write_text
+from common.io_utils import write_text
 
 
 # ═══════════════════════════════════════════════════════════════════════
diff --git a/export/et_compatibility.py b/export/et_compatibility.py
index 28c4ccf..3781f13 100644
--- a/export/et_compatibility.py
+++ b/export/et_compatibility.py
@@ -61,7 +61,7 @@ import copy
 from typing import Dict, List, Tuple, Optional, Any
 from dataclasses import dataclass, field
 
-from eu4_wgs_v8.common.io_utils import ensure_dir, write_text
+from common.io_utils import ensure_dir, write_text
 
 
 # ═══════════════════════════════════════════════════════════════════════
@@ -456,13 +456,13 @@ class ETProvinceHistoryExporter:
         y = province.center_y
 
         # Base development and religion depend on continent
-        from eu4_wgs_v8.analytics.heightmap_analyzer import HeightmapAnalyzer
+        from analytics.heightmap_analyzer import HeightmapAnalyzer
         analyzer = HeightmapAnalyzer()
         base_dev = analyzer._compute_inverted_development(province)
         base_religion = analyzer._assign_inverted_religion(province)
 
         # Culture assignment
-        from eu4_wgs_v8.content.world_content import CultureGenerator
+        from content.world_content import CultureGenerator
         culture = CultureGenerator.get_culture_for_continent(continent)
 
         # Trade good
diff --git a/export/eu4_exporter.py b/export/eu4_exporter.py
index 73f2358..3da7cb8 100644
--- a/export/eu4_exporter.py
+++ b/export/eu4_exporter.py
@@ -4,24 +4,33 @@ Module 4: EU4 Complete Mod File Export System
 Handles exporting all generated data into proper EU4 mod file formats,
 including province bitmaps, history files, common files, localization,
 and .mod descriptor files.
+
+This module writes five cooperating exporters:
+    MapFileExporter        -> map/ bitmaps + map/ text definitions
+    CountryFileExporter     -> common/countries, common/ideas,
+                                common/country_tags, localisation
+    ProvinceHistoryExporter -> history/provinces
+    ModDescriptorExporter   -> the top-level .mod pointer + descriptor.mod
+    MasterExportOrchestrator-> wires all of the above into one pipeline
 """
- 
+
 import os
 import csv
 import json
+import random
 import shutil
 import numpy as np
 from typing import Dict, List, Tuple, Any, Optional
 from dataclasses import dataclass
- 
+
 import eu4_wgs_v8
-from eu4_wgs_v8.common.io_utils import ensure_dir, write_text, save_image
- 
- 
+from common.io_utils import ensure_dir, write_text, save_image
+
+
 # ═══════════════════════════════════════════════════════════════
 #  MOD DIRECTORY STRUCTURE
 # ═══════════════════════════════════════════════════════════════
- 
+
 MOD_SUBDIRS = [
     "common/countries",
     "common/country_tags",
@@ -45,50 +54,354 @@ MOD_SUBDIRS = [
     "missions",
     "common/on_actions",
 ]
- 
- 
+
+# Rough per-terrain economic flavor. Used only to seed plausible starting
+# province stats / trade goods -- not derived from any real-world data.
+TERRAIN_BASE_STATS = {
+    "farmland":       (4, 3, 3, "grain"),
+    "grasslands":     (3, 3, 3, "livestock"),
+    "forest":         (2, 3, 2, "wood"),
+    "hills":          (2, 2, 2, "iron"),
+    "mountain":       (1, 2, 1, "iron"),
+    "highland":       (2, 2, 2, "wool"),
+    "jungle":         (2, 3, 2, "exotic_spices"),
+    "marsh":          (2, 2, 1, "rice"),
+    "steppe":         (2, 2, 3, "livestock"),
+    "tundra":         (1, 1, 2, "fur"),
+    "ice_sheet":      (1, 1, 1, "fur"),
+    "desert":         (1, 2, 1, "cotton"),
+    "coastal_desert": (2, 3, 1, "cloth"),
+    "coastline":      (2, 3, 1, "fish"),
+}
+DEFAULT_TERRAIN_STATS = (2, 2, 2, "grain")
+
+
 # ═══════════════════════════════════════════════════════════════
-#  MAP FILE EXPORTERS
+#  MAP FILE EXPORTER  (map/ bitmaps + text definitions)
 # ═══════════════════════════════════════════════════════════════
- 
+
 class MapFileExporter:
     """Exports all map-related bitmap and configuration files."""
- 
+
     def __init__(self, output_dir: str, map_height: int = 2048):
         self.output_dir = output_dir
         self.map_height = map_height
         self.map_dir = f"{output_dir}/map"
         ensure_dir(self.map_dir)
- 
+
+    # ── Bitmaps ──────────────────────────────────────────────
     def save_heightmap(self, heightmap: np.ndarray) -> str:
         """Save heightmap.bmp."""
         return save_image(heightmap, f"{self.map_dir}/heightmap.bmp")
- 
+
     def save_provinces_bmp(self, provinces_bmp: np.ndarray) -> str:
         """Save provinces.bmp."""
         return save_image(provinces_bmp, f"{self.map_dir}/provinces.bmp")
- 
+
     def save_world_normal(self, normal_map: np.ndarray) -> str:
         """Save world_normal.bmp."""
         return save_image(normal_map, f"{self.map_dir}/world_normal.bmp", "RGB")
- 
+
     def save_terrain_bmp(self, terrain_bmp: np.ndarray) -> str:
         """Save terrain.bmp."""
         return save_image(terrain_bmp, f"{self.map_dir}/terrain.bmp", "RGB")
- 
+
     def save_rivers_bmp(self, rivers_bmp: np.ndarray) -> str:
         """Save rivers.bmp."""
         return save_image(rivers_bmp, f"{self.map_dir}/rivers.bmp", "RGB")
- 
+
     def save_watercolor_bmp(self, watercolor_bmp: np.ndarray) -> str:
         """Save watercolor.bmp."""
         return save_image(watercolor_bmp, f"{self.map_dir}/watercolor.bmp", "RGB")
- 
+
     def save_trees_bmp(self, width: int = 5632, height: int = 2048) -> str:
-        """Generate a blank trees.bmp (required by EU4)."""
- 
+        """Generate a blank trees.bmp (required to exist by EU4, even if unused)."""
+        blank = np.zeros((height, width, 3), dtype=np.uint8)
+        return save_image(blank, f"{self.map_dir}/trees.bmp", "RGB")
+
+    # ── Text definitions ────────────────────────────────────
+    def write_definition_csv(self, province_infos: List) -> str:
+        """Write definition.csv (province id -> RGB -> name)."""
+        lines = ["province;red;green;blue;x;x", "0;0;0;0;x;x"]
+        for p in sorted(province_infos, key=lambda p: p.id):
+            r, g, b = p.color
+            kind = "Sea" if p.is_sea else ("Wasteland" if p.is_wasteland else "Province")
+            lines.append(f"{p.id};{r};{g};{b};{kind}{p.id};x")
+        return write_text(f"{self.map_dir}/definition.csv", "\n".join(lines) + "\n")
+
+    def write_default_map(self, width: int, height: int, max_provinces: int,
+                           sea_ids: List[int], wasteland_ids: List[int]) -> str:
+        """Write default.map. Region/area/superregion keys are intentionally
+        omitted -- this pipeline does not yet generate them (see project notes)."""
+        def block(ids):
+            return " ".join(str(i) for i in sorted(ids))
+
+        content = f"""max_provinces = {max_provinces}
+
+sea_starts = {{
+    {block(sea_ids)}
+}}
+
+lakes = {{
+}}
+
+definitions = "definition.csv"
+provinces = "provinces.bmp"
+positions = "positions.txt"
+terrain = "terrain.bmp"
+rivers = "rivers.bmp"
+terrain_definition = "terrain.txt"
+heightmap = "heightmap.bmp"
+tree_definition = "trees.bmp"
+continent = "continent.txt"
+adjacencies = "adjacencies.csv"
+climate = "climate.txt"
+"""
+        return write_text(f"{self.map_dir}/default.map", content)
+
+    def write_positions_txt(self, positions_data: Dict[int, Dict]) -> str:
+        """Write positions.txt. All five position anchors (city, unit, text,
+        port, trade) are collapsed onto the province center -- a common
+        simplification; it looks slightly less polished in-game but loads fine."""
+        lines = []
+        for pid in sorted(positions_data.keys()):
+            d = positions_data[pid]
+            bx, by = d["bc_x"], d["bc_y"]
+            ux, uy = d["unit_x"], d["unit_y"]
+            tx, ty = d["text_x"], d["text_y"]
+            pos = " ".join(
+                f"{x:.2f} 0.00 {y:.2f}" for x, y in
+                [(bx, by), (ux, uy), (tx, ty), (bx, by), (bx, by)]
+            )
+            lines.append(
+                f"{pid}={{\n"
+                f"\tposition={{\n\t\t {pos} \n\t}}\n"
+                f"\trotation={{\n\t\t 0.00 0.00 0.00 0.00 0.00 \n\t}}\n"
+                f"\theight={{\n\t\t 0.00 0.00 0.00 0.00 0.00 \n\t}}\n"
+                f"}}"
+            )
+        return write_text(f"{self.map_dir}/positions.txt", "\n".join(lines) + "\n")
+
+    def write_continent_txt(self, province_infos: List) -> str:
+        """Write continent.txt, grouping land provinces by generated continent name."""
+        by_continent: Dict[str, List[int]] = {}
+        for p in province_infos:
+            if p.is_sea or p.is_wasteland:
+                continue
+            key = p.continent_name or "unknown"
+            by_continent.setdefault(key, []).append(p.id)
+
+        lines = []
+        for name, ids in sorted(by_continent.items()):
+            ids_str = " ".join(str(i) for i in sorted(ids))
+            lines.append(f"{name} = {{\n\t{ids_str}\n}}")
+        return write_text(f"{self.map_dir}/continent.txt", "\n\n".join(lines) + "\n")
+
+    def write_climate_txt(self, climate_zones: Dict[str, List[int]],
+                           wasteland_ids: Optional[List[int]] = None) -> str:
+        """Write climate.txt from the generator's climate-zone buckets, plus
+        the mandatory impassable block for wasteland provinces."""
+        lines = []
+        for zone, ids in climate_zones.items():
+            ids_str = " ".join(str(i) for i in sorted(ids))
+            lines.append(f"{zone} = {{\n\t{ids_str}\n}}")
+        wasteland_ids = wasteland_ids or []
+        ids_str = " ".join(str(i) for i in sorted(wasteland_ids))
+        lines.append(f"impassable = {{\n\t{ids_str}\n}}")
+        return write_text(f"{self.map_dir}/climate.txt", "\n\n".join(lines) + "\n")
+
+    def write_terrain_txt(self) -> str:
+        """Write terrain.txt describing the terrain categories used by
+        TerrainClassifier. NOTE: terrain.bmp is currently written as a true-
+        colour RGB image rather than a palette-indexed one, so the `color`
+        index lists below are placeholders -- see project notes for the
+        follow-up needed to make terrain.bmp+terrain.txt fully game-accurate."""
+        from engine.map_generation import TerrainClassifier
+        categories = list(TerrainClassifier.TERRAIN_COLORS.keys())
+        blocks = []
+        for i, name in enumerate(categories):
+            is_water = name in ("ocean", "deep_ocean")
+            blocks.append(
+                f"\t{name} = {{\n"
+                f"\t\tcolor = {{ {i} }}\n"
+                f"\t\tis_water = {'yes' if is_water else 'no'}\n"
+                f"\t\tinland_sea = no\n"
+                f"\t}}"
+            )
+        content = "categories = {\n" + "\n".join(blocks) + "\n}\n"
+        return write_text(f"{self.map_dir}/terrain.txt", content)
+
+    def write_adjacencies_csv(self) -> str:
+        """Write a header-only adjacencies.csv (no canals/straits generated)."""
+        content = (
+            "From;To;Type;Through;start_x;start_y;stop_x;stop_y;Comment\n"
+            "-1;-1;;-1;-1;-1;-1;-1;\n"
+        )
+        return write_text(f"{self.map_dir}/adjacencies.csv", content)
+
+
+# ═══════════════════════════════════════════════════════════════
+#  COUNTRY FILE EXPORTER  (common/countries, ideas, tags, localisation)
+# ═══════════════════════════════════════════════════════════════
+
+class CountryFileExporter:
+    """Exports per-country common/history/idea files plus the shared
+    country_tags and localisation registries."""
+
+    def __init__(self, output_dir: str, map_height: int = 2048):
+        self.output_dir = output_dir
+        self.map_height = map_height
+        # tag -> relative path (from common/countries/) recorded as files are written
+        self._country_file: Dict[str, str] = {}
+
+    def write_country_common_file(self, tag: str, data) -> str:
+        r, g, b = data.color
+        filename = f"{tag}_{data.short_name}".replace(" ", "_") + ".txt"
+        self._country_file[tag] = filename
+        content = f"""graphical_culture = westerngfx
+color = {{ {r} {g} {b} }}
+
+historical_idea_groups = {{
+}}
+
+historical_units = {{
+}}
+"""
+        return write_text(f"{self.output_dir}/common/countries/{filename}", content)
+
+    def write_country_history_file(self, tag: str, data) -> str:
+        filename = f"{tag} - {data.short_name}.txt"
+        content = f"""government = {data.government}
+add_government_reform = autocracy_reform
+government_rank = 1
+mercantilism = 25
+technology_group = {data.tech_group}
+religion = {data.religion}
+primary_culture = {data.primary_culture}
+capital = {data.capital_province}
+
+add_idea_group = {tag}_ideas
+
+1444.11.11 = {{
+\tmonarch = {{
+\t\tname = "{data.ruler_name or tag.title()}"
+\t\tdynasty = "{data.short_name}"
+\t\tadm = {data.ruler_adm}
+\t\tdip = {data.ruler_dip}
+\t\tmil = {data.ruler_mil}
+\t\tbirth_date = {1444 - data.ruler_age}.1.1
+\t}}
+}}
+"""
+        return write_text(f"{self.output_dir}/history/countries/{filename}", content)
+
+    def write_national_ideas(self, tag: str, center_y: int) -> str:
+        from content.world_content import IdeaGenerator
+        script = IdeaGenerator.generate_national_ideas(tag, center_y, self.map_height)
+        return write_text(f"{self.output_dir}/common/ideas/{tag}_ideas.txt", script)
+
+    def write_country_tags(self, countries: Dict[str, Any]) -> str:
+        lines = []
+        for tag in sorted(countries.keys()):
+            filename = self._country_file.get(tag, f"{tag}.txt")
+            lines.append(f'{tag} = "countries/{filename}"')
+        return write_text(f"{self.output_dir}/common/country_tags/00_countries.txt",
+                           "\n".join(lines) + "\n")
+
+    def write_localization(self, countries: Dict[str, Any]) -> str:
+        lines = ["l_english:"]
+        for tag, data in sorted(countries.items()):
+            lines.append(f' {tag}: "{data.short_name}"')
+            lines.append(f' {tag}_ADJ: "{data.short_name}"')
+        content = "\ufeff" + "\n".join(lines) + "\n"
+        return write_text(f"{self.output_dir}/localisation/countries_l_english.yml", content)
+
+
+# ═══════════════════════════════════════════════════════════════
+#  PROVINCE HISTORY EXPORTER  (history/provinces)
+# ═══════════════════════════════════════════════════════════════
+
+class ProvinceHistoryExporter:
+    """Exports history/provinces/{id} - {name}.txt for every land province."""
+
+    def __init__(self, output_dir: str, map_height: int = 2048):
+        self.output_dir = output_dir
+        self.map_height = map_height
+
+    def write_province_history(self, province, owner_tag: str,
+                                country_data: Optional[Any] = None) -> str:
+        base_tax, base_prod, base_man, trade_good = TERRAIN_BASE_STATS.get(
+            province.terrain_type, DEFAULT_TERRAIN_STATS
+        )
+        culture = country_data.primary_culture if country_data else "manden"
+        religion = country_data.religion if country_data else "hinduism"
+        is_capital = bool(country_data and country_data.capital_province == province.id)
+
+        lines = [
+            f"owner = {owner_tag}",
+            f"controller = {owner_tag}",
+            f"add_core = {owner_tag}",
+            f"culture = {culture}",
+            f"religion = {religion}",
+            f"hre = no",
+            f"base_tax = {base_tax}",
+            f"base_production = {base_prod}",
+            f"base_manpower = {base_man}",
+            f"trade_goods = {trade_good}",
+        ]
+        if is_capital:
+            lines.append("is_city = yes")
+
+        filename = f"{province.id} - Province{province.id}.txt"
+        content = "\n".join(lines) + "\n"
+        return write_text(f"{self.output_dir}/history/provinces/{filename}", content)
+
+
+# ═══════════════════════════════════════════════════════════════
+#  MOD DESCRIPTOR EXPORTER  (.mod pointer + descriptor.mod)
+# ═══════════════════════════════════════════════════════════════
+
+class ModDescriptorExporter:
+    """Writes the mod pointer file (next to the mod folder) and the
+    descriptor.mod file inside it, in EU4's launcher-recognised format."""
+
+    def write_mod_descriptor(self, mod_name: str, tech_name: str, mod_root: str) -> Tuple[str, str]:
+        parent_dir = os.path.dirname(mod_root.rstrip("/"))
+        descriptor_body = (
+            f'name="{mod_name}"\n'
+            f'path="mod/{tech_name}"\n'
+            f'tags={{\n\t"Total Conversion"\n\t"Map"\n}}\n'
+            f'supported_version="1.37.*"\n'
+        )
+        pointer_path = write_text(f"{parent_dir}/{tech_name}.mod", descriptor_body)
+        descriptor_path = write_text(f"{mod_root}/descriptor.mod", descriptor_body)
+        return pointer_path, descriptor_path
+
+
+# ═══════════════════════════════════════════════════════════════
+#  MASTER EXPORT ORCHESTRATOR
+# ═══════════════════════════════════════════════════════════════
+
+class MasterExportOrchestrator:
+    """Wires MapFileExporter, CountryFileExporter, ProvinceHistoryExporter
+    and ModDescriptorExporter into the full mod-export pipeline."""
+
+    def __init__(self, output_base_dir: str, map_height: int = 2048):
+        # main.py's CLI (both --test and --headless) constructs this class with
+        # output_base_dir=..., so that's the name kept here. gui/studio.py calls
+        # this with a different, all-in-one signature -- that's a separate, not
+        # yet reconciled GUI-side mismatch; see project notes.
+        self.output_dir = output_base_dir
+        self.map_height = map_height
+
+    def create_mod_structure(self, mod_name: str) -> str:
+        tech_name = mod_name.lower().replace(" ", "_")
+        mod_root = os.path.join(self.output_dir, tech_name)
+        ensure_dir(mod_root)
+        for sub in MOD_SUBDIRS:
+            ensure_dir(os.path.join(mod_root, sub))
         return mod_root
- 
+
     def export_complete_mod(self, mod_name: str,
                              heightmap: np.ndarray,
                              land_mask: np.ndarray,
@@ -107,57 +420,57 @@ class MapFileExporter:
         mod_root = self.create_mod_structure(mod_name)
         exported_files = {}
         height, width = heightmap.shape[:2]
- 
+
         # ── Map files ──────────────────────────────────────────
         map_exporter = MapFileExporter(mod_root, map_height=self.map_height)
- 
+
         exported_files["heightmap"] = map_exporter.save_heightmap(heightmap)
- 
-        from eu4_wgs_v8.engine.map_generation import NormalMapGenerator, WatercolorGenerator
+
+        from engine.map_generation import NormalMapGenerator, WatercolorGenerator
         normal_map = NormalMapGenerator.generate(heightmap)
         exported_files["world_normal"] = map_exporter.save_world_normal(normal_map)
- 
+
         watercolor = WatercolorGenerator.generate(land_mask)
         exported_files["watercolor"] = map_exporter.save_watercolor_bmp(watercolor)
- 
+
         exported_files["provinces"] = map_exporter.save_provinces_bmp(provinces_bmp)
- 
+
         if terrain_bmp is None:
-            from eu4_wgs_v8.engine.map_generation import TerrainClassifier
+            from engine.map_generation import TerrainClassifier
             terrain_cls = TerrainClassifier(width=width, height=height)
             terrain_bmp = terrain_cls.generate_terrain_bmp(heightmap, land_mask)
         exported_files["terrain"] = map_exporter.save_terrain_bmp(terrain_bmp)
- 
+
         if rivers_bmp is None:
-            from eu4_wgs_v8.engine.map_generation import RiverGenerator
+            from engine.map_generation import RiverGenerator
             river_gen = RiverGenerator(width=width, height=height)
             rivers_bmp, _ = river_gen.generate_rivers(heightmap, land_mask)
         exported_files["rivers"] = map_exporter.save_rivers_bmp(rivers_bmp)
- 
+
         exported_files["trees"] = map_exporter.save_trees_bmp(width, height)
         exported_files["definition_csv"] = map_exporter.write_definition_csv(province_infos)
- 
+
         # Compute sea and wasteland IDs
         sea_ids = [p.id for p in province_infos if p.is_sea]
         wasteland_ids = [p.id for p in province_infos if p.is_wasteland]
         max_provinces = len(province_infos) + 1
- 
+
         exported_files["default_map"] = map_exporter.write_default_map(
             width, height, max_provinces, sea_ids, wasteland_ids
         )
- 
+
         # Compute positions
         positions_data = self._compute_positions(province_infos)
         exported_files["positions"] = map_exporter.write_positions_txt(positions_data)
- 
+
         exported_files["continent"] = map_exporter.write_continent_txt(province_infos)
-        exported_files["climate"] = map_exporter.write_climate_txt(climate_zones)
+        exported_files["climate"] = map_exporter.write_climate_txt(climate_zones, wasteland_ids)
         exported_files["terrain_txt"] = map_exporter.write_terrain_txt()
         exported_files["adjacencies"] = map_exporter.write_adjacencies_csv()
- 
+
         # ── Country files ──────────────────────────────────────
         country_exporter = CountryFileExporter(mod_root, map_height=self.map_height)
- 
+
         for tag, data in countries.items():
             country_exporter.write_country_common_file(tag, data)
             country_exporter.write_country_history_file(tag, data)
@@ -166,60 +479,60 @@ class MapFileExporter:
                                           assets_path=str(eu4_wgs_v8.ASSETS_DIR),
                                           continent=data.continent,
                                           seed=hash(tag) % (2**31))
- 
+
         exported_files["country_tags"] = country_exporter.write_country_tags(countries)
         exported_files["localization"] = country_exporter.write_localization(countries)
- 
+
         # ── Province histories ─────────────────────────────────
         prov_exporter = ProvinceHistoryExporter(mod_root, map_height=self.map_height)
- 
+
         # Assign provinces to countries
         country_assignments = self._assign_provinces_to_countries(
             province_infos, countries
         )
- 
+
         for p in province_infos:
             if p.is_sea or p.is_wasteland:
                 continue
             owner_tag = country_assignments.get(p.id, list(countries.keys())[0] if countries else "FRA")
-            prov_exporter.write_province_history(p, owner_tag)
- 
+            prov_exporter.write_province_history(p, owner_tag, countries.get(owner_tag))
+
         # ── Content files (religions, cultures, etc.) ──────────
-        from eu4_wgs_v8.content.world_content import (
+        from content.world_content import (
             ReligionGenerator, CultureGenerator, TradeGenerator,
             CelestialDirectorate, DiplomacyGenerator
         )
- 
+
         exported_files["religions"] = ReligionGenerator.generate_religion_file(mod_root)
         exported_files["holy_modifier"] = ReligionGenerator.generate_holy_city_modifier_file(mod_root)
         exported_files["church_aspects"] = ReligionGenerator.generate_corrupt_church_aspects(mod_root)
- 
+
         # Find a Hindu holy center province
         hindu_center = self._find_hindu_center(province_infos)
         if hindu_center:
             exported_files["hindu_events"] = ReligionGenerator.generate_hindu_holy_center_event(
                 mod_root, hindu_center
             )
- 
+
         exported_files["cultures"] = CultureGenerator.generate_cultures_file(mod_root)
- 
+
         exported_files["trade_goods"] = TradeGenerator.generate_trade_goods_files(mod_root)
         exported_files["trade_nodes"] = TradeGenerator.generate_inverted_trade_nodes(
             province_infos, mod_root
         )
         exported_files["trade_events"] = TradeGenerator.generate_trade_price_events(mod_root)
- 
+
         exported_files["celestial_directorate"] = CelestialDirectorate.generate_imperial_reforms(mod_root)
         exported_files["diplomacy"] = DiplomacyGenerator.generate_diplomacy(mod_root, countries)
         exported_files["war_events"] = DiplomacyGenerator.generate_war_events(mod_root)
- 
+
         # ── Celestial Directorate role assignments ─────────────
         directorate_assignments = CelestialDirectorate.assign_directorate_roles(countries)
         if directorate_assignments:
             self._write_directorate_history(mod_root, directorate_assignments, countries)
- 
+
         # -- Template-based mod files (decisions, events, missions, etc.) --
-        from eu4_wgs_v8.export.template_exporter import TemplateExporter, TemplateExportConfig
+        from export.template_exporter import TemplateExporter, TemplateExportConfig
         template_config = TemplateExportConfig(
             mod_name=mod_name,
             mod_path=tech_name,
@@ -237,7 +550,7 @@ class MapFileExporter:
         template_stats = template_exporter.export_all(mod_root)
         for category, file_count in template_stats.items():
             exported_files[f"template_{category}"] = f"{file_count} files"
- 
+
         # ── Mod descriptor ─────────────────────────────────────
         descriptor_exporter = ModDescriptorExporter()
         pointer, desc = descriptor_exporter.write_mod_descriptor(
@@ -245,9 +558,9 @@ class MapFileExporter:
         )
         exported_files["mod_pointer"] = pointer
         exported_files["descriptor"] = desc
- 
+
         return exported_files
- 
+
     def _compute_positions(self, province_infos: list) -> Dict[int, Dict]:
         """Compute province positions for positions.txt."""
         positions = {}
@@ -265,7 +578,7 @@ class MapFileExporter:
                 "text_y": center_y - 5,
             }
         return positions
- 
+
     @staticmethod
     def _assign_provinces_to_countries(province_infos: list,
                                         countries: Dict[str, Any]) -> Dict[int, str]:
@@ -273,26 +586,25 @@ class MapFileExporter:
         assignments = {}
         if not countries:
             return assignments
- 
-        country_list = list(countries.values())
+
         for p in province_infos:
             if p.is_sea or p.is_wasteland:
                 continue
- 
+
             # Find nearest country by distance
             min_dist = float('inf')
             nearest_tag = list(countries.keys())[0]
- 
+
             for tag, c in countries.items():
                 dist = np.hypot(p.center_x - c.center_x, p.center_y - c.center_y)
                 if dist < min_dist:
                     min_dist = dist
                     nearest_tag = tag
- 
+
             assignments[p.id] = nearest_tag
- 
+
         return assignments
- 
+
     @staticmethod
     def _find_hindu_center(province_infos: list) -> Optional[int]:
         """Find the best province for the Hindu holy center."""
@@ -305,26 +617,25 @@ class MapFileExporter:
         if candidates:
             return random.choice(candidates).id
         return None
- 
+
     @staticmethod
     def _write_directorate_history(output_dir: str,
                                     assignments: Dict[str, str],
                                     countries: Dict[str, Any]) -> str:
         """Write Celestial Directorate history entries for countries."""
         ensure_dir(f"{output_dir}/history/countries")
- 
+
         for tag, role in assignments.items():
             if tag in countries:
                 data = countries[tag]
                 # Append HRE role to country history file
                 filename = f"{tag} - {data.short_name}.txt"
                 path = f"{output_dir}/history/countries/{filename}"
- 
+
                 if os.path.exists(path):
                     write_text(path, f"\n{role}\n", mode="a")
- 
+
         return output_dir
- 
- 
-from eu4_wgs_v8.content.world_content import FlagGenerator, CountryData
- 
+
+
+from content.world_content import FlagGenerator, CountryData
diff --git a/generate_world.py b/generate_world.py
index 7639c96..ef7d24c 100755
--- a/generate_world.py
+++ b/generate_world.py
@@ -7,16 +7,16 @@ import numpy as np
 from PIL import Image
 
 
-from eu4_wgs_v8.engine.map_generation import (
+from engine.map_generation import (
     MapConfig, MapGenerationEngine, ProvinceGenerator,
     RiverGenerator, TerrainClassifier, NormalMapGenerator
 )
-from eu4_wgs_v8.content.world_content import (
+from content.world_content import (
     CountryGenerator, CelestialDirectorate, ReligionGenerator,
     CultureGenerator, FlagGenerator, IdeaGenerator
 )
-from eu4_wgs_v8.analytics.heightmap_analyzer import HeightmapAnalyzer
-from eu4_wgs_v8.analytics.dashboard import DashboardGenerator, DashboardDataPreparer
+from analytics.heightmap_analyzer import HeightmapAnalyzer
+from analytics.dashboard import DashboardGenerator, DashboardDataPreparer
 
 
 def generate_world(
@@ -33,30 +33,48 @@ def generate_world(
     enable_craters=True,
     num_craters=5,
     octaves=None,
+    mask_path=None,
+    height_path=None,
 ):
-    """Generate a complete world with all data and visualizations."""
+    """Generate a complete world with all data and visualizations.
+
+    If both mask_path and height_path are given, the heightmap/land-mask are
+    built from those source images instead of procedural generation (see
+    engine.image_map_source.build_heightmap_from_images).
+    """
     os.makedirs(output_dir, exist_ok=True)
     timings = {}
 
     # ── Phase 1: Heightmap ──
     print("[1/7] Generating heightmap...")
     t0 = time.time()
-    config_kwargs = dict(
-        width=width, height=height, seed=seed,
-        land_percentage=land_pct,
-        layout_style=map_style
-    )
-    if octaves is not None:
-        config_kwargs["continent_octaves"] = octaves
-        config_kwargs["detail_octaves"] = octaves
-    config = MapConfig(**config_kwargs)
-    engine = MapGenerationEngine(config)
-    heightmap, land_mask = engine.generate_complete_heightmap(
-        apply_tectonic=enable_tectonic,
-        apply_erosion=enable_erosion,
-        apply_craters=enable_craters,
-        num_craters=num_craters,
-    )
+    if mask_path and height_path:
+        from engine.image_map_source import build_heightmap_from_images
+        heightmap, land_mask = build_heightmap_from_images(
+            mask_path, height_path, target_width=width, target_height=height
+        )
+        # Downstream code still expects a MapConfig-shaped object for its
+        # width/height fields even though no procedural generation ran.
+        height, width = heightmap.shape[:2]
+        config = MapConfig(width=width, height=height, seed=seed,
+                            land_percentage=land_pct, layout_style=map_style)
+    else:
+        config_kwargs = dict(
+            width=width, height=height, seed=seed,
+            land_percentage=land_pct,
+            layout_style=map_style
+        )
+        if octaves is not None:
+            config_kwargs["continent_octaves"] = octaves
+            config_kwargs["detail_octaves"] = octaves
+        config = MapConfig(**config_kwargs)
+        engine = MapGenerationEngine(config)
+        heightmap, land_mask = engine.generate_complete_heightmap(
+            apply_tectonic=enable_tectonic,
+            apply_erosion=enable_erosion,
+            apply_craters=enable_craters,
+            num_craters=num_craters,
+        )
     timings["heightmap"] = time.time() - t0
     land_pct_actual = land_mask.sum() / land_mask.size * 100
     print(f"  Done in {timings['heightmap']:.1f}s — land={land_pct_actual:.1f}%, range=[{heightmap.min()}, {heightmap.max()}]")
diff --git a/gui/studio.py b/gui/studio.py
index a258fc5..6e114c7 100644
--- a/gui/studio.py
+++ b/gui/studio.py
@@ -1351,9 +1351,9 @@ if CTk_AVAILABLE:
         def _generate_worker(self):
             """Background worker for world generation."""
             try:
-                from eu4_wgs_v8.engine import MapConfig, MapGenerationEngine, ProvinceGenerator, RiverGenerator, TerrainClassifier, NormalMapGenerator, WatercolorGenerator
-                from eu4_wgs_v8.analytics import HeightmapAnalyzer
-                from eu4_wgs_v8.content import CountryGenerator, CelestialDirectorate, TradeGenerator, DiplomacyGenerator
+                from engine import MapConfig, MapGenerationEngine, ProvinceGenerator, RiverGenerator, TerrainClassifier, NormalMapGenerator, WatercolorGenerator
+                from analytics import HeightmapAnalyzer
+                from content import CountryGenerator, CelestialDirectorate, TradeGenerator, DiplomacyGenerator
 
                 cfg = self.config
 
@@ -1533,8 +1533,8 @@ if CTk_AVAILABLE:
         def _export_worker(self):
             """Background worker for mod export."""
             try:
-                from eu4_wgs_v8.export import MasterExportOrchestrator
-                from eu4_wgs_v8.content import CountryGenerator, CelestialDirectorate, TradeGenerator, DiplomacyGenerator, ReligionGenerator, CultureGenerator
+                from export import MasterExportOrchestrator
+                from content import CountryGenerator, CelestialDirectorate, TradeGenerator, DiplomacyGenerator, ReligionGenerator, CultureGenerator
 
                 cfg = self.config
                 self.gen_state.start()
@@ -1579,7 +1579,7 @@ if CTk_AVAILABLE:
                 return
 
             try:
-                from eu4_wgs_v8.analytics import generate_dashboard_from_analytics
+                from analytics import generate_dashboard_from_analytics
                 import webbrowser
 
                 output_dir = os.path.join(self.config.output_dir, self.config.mod_name, "dashboard")
@@ -1690,10 +1690,10 @@ def run_headless(config: GUIConfig = None):
     if config is None:
         config = GUIConfig()
 
-    from eu4_wgs_v8.engine import MapConfig, MapGenerationEngine, ProvinceGenerator, RiverGenerator, TerrainClassifier
-    from eu4_wgs_v8.analytics import HeightmapAnalyzer, generate_dashboard_from_analytics
-    from eu4_wgs_v8.content import CountryGenerator, CelestialDirectorate
-    from eu4_wgs_v8.export import MasterExportOrchestrator
+    from engine import MapConfig, MapGenerationEngine, ProvinceGenerator, RiverGenerator, TerrainClassifier
+    from analytics import HeightmapAnalyzer, generate_dashboard_from_analytics
+    from content import CountryGenerator, CelestialDirectorate
+    from export import MasterExportOrchestrator
 
     print(f"\n{'='*60}")
     print(f"  EU4 WGS V8 — Headless Generation Pipeline")
diff --git a/main.py b/main.py
index 7d673ca..a0a7184 100755
--- a/main.py
+++ b/main.py
@@ -68,17 +68,17 @@ def run_test():
     print("  EU4 WGS V8 — Quick Module Integration Test")
     print("=" * 60 + "\n")
 
-    from eu4_wgs_v8.engine import (
+    from engine import (
         MapConfig, MapGenerationEngine, ProvinceGenerator,
         RiverGenerator, TerrainClassifier, NormalMapGenerator
     )
-    from eu4_wgs_v8.analytics import HeightmapAnalyzer, DashboardGenerator
-    from eu4_wgs_v8.content import (
+    from analytics import HeightmapAnalyzer, DashboardGenerator
+    from content import (
         CountryGenerator, CountryData, CelestialDirectorate,
         TradeGenerator, DiplomacyGenerator, ReligionGenerator,
         CultureGenerator, FlagGenerator, IdeaGenerator
     )
-    from eu4_wgs_v8.export import MasterExportOrchestrator
+    from export import MasterExportOrchestrator
 
     test_dir = "./test_output/test_mod"
 
@@ -234,7 +234,7 @@ def run_test():
 def run_headless_pipeline(args):
     """Run the full headless generation pipeline."""
     import generate_world
-    from eu4_wgs_v8.export import MasterExportOrchestrator
+    from export import MasterExportOrchestrator
 
     result = generate_world.generate_world(
         mod_name=args.mod_name,
@@ -295,7 +295,7 @@ def main():
 
     # Try GUI
     try:
-        from eu4_wgs_v8.gui import WorldGeneratorStudio
+        from gui import WorldGeneratorStudio
         app = WorldGeneratorStudio()
         app.mainloop()
     except Exception as e:
