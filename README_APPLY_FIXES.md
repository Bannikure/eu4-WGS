"""
Module 4: EU4 Complete Mod File Export System
================================================
Writes a fully loadable Europa Universalis IV mod folder from the data
produced by the engine/content pipeline: map files (bmp + text), country
files, province history, localisation and the mod descriptor.

File formats follow the Paradox modding wiki (https://eu4.paradoxwikis.com/Map_modding).
"""

import os
import shutil
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from PIL import Image

import eu4_wgs_v8
from common.io_utils import ensure_dir, write_text, save_image


# ═══════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════

MOD_SUBDIRS = [
    "map", "map/lakes",
    "common/countries", "common/country_tags", "common/ideas",
    "common/religions", "common/cultures", "common/imperial_reforms",
    "common/tradenodes", "common/trade_goods", "common/prices",
    "history/countries", "history/provinces", "history/diplomacy",
    "history/advisors",
    "localisation",
    "gfx/flags",
    "events", "decisions", "missions",
]

# Gameplay properties for each terrain name painted by TerrainClassifier.
# Keys must match engine.map_generation.TerrainClassifier.TERRAIN_COLORS.
TERRAIN_GAMEPLAY = {
    "ocean":          {"is_water": True},
    "deep_ocean":     {"is_water": True},
    "coastal_desert": {"type": "desert",    "movement_cost": 1.15, "defence": 0},
    "desert":         {"type": "desert",    "movement_cost": 1.25, "defence": 0},
    "coastline":      {"type": "plains",    "movement_cost": 1.0,  "defence": 0},
    "farmland":       {"type": "plains",    "movement_cost": 1.0,  "defence": 0},
    "grasslands":     {"type": "plains",    "movement_cost": 1.0,  "defence": 0},
    "forest":         {"type": "forest",    "movement_cost": 1.2,  "defence": 1},
    "hills":          {"type": "hills",     "movement_cost": 1.4,  "defence": 2},
    "mountain":       {"type": "mountains", "movement_cost": 1.75, "defence": 3},
    "highland":       {"type": "hills",     "movement_cost": 1.3,  "defence": 1},
    "jungle":         {"type": "jungle",    "movement_cost": 1.3,  "defence": 1},
    "marsh":          {"type": "marsh",     "movement_cost": 1.4,  "defence": 0},
    "steppe":         {"type": "plains",    "movement_cost": 1.1,  "defence": 0},
    "tundra":         {"type": "hills",     "movement_cost": 1.3,  "defence": 0},
    "ice_sheet":      {"type": "mountains", "movement_cost": 1.5,  "defence": 0},
}

# Canonical river colours recognised by the engine (see wiki "River map").
RIVER_PALETTE = [
    (255, 255, 255),  # 0  background / no river
    (0, 255, 0),       # 1  source
    (255, 0, 0),        # 2  flow-in
    (255, 252, 0),       # 3  flow-out
    (0, 225, 255),        # 4  narrowest
    (0, 200, 255),         # 5  narrow
    (0, 100, 255),          # 6  wide
    (0, 0, 200),             # 7  widest
]

WOODED_TERRAIN = ("forest", "jungle", "hills", "highland")


def _slugify(name: str) -> str:
    keep = [c if (c.isalnum() or c in "_- ") else "_" for c in name]
    return "".join(keep).strip().replace(" ", "_")


# ═══════════════════════════════════════════════════════════════
#  MAP FILE EXPORTER  (map/*)
# ═══════════════════════════════════════════════════════════════

class MapFileExporter:
    """Writes every file referenced by map/default.map."""

    def __init__(self, output_dir: str, map_height: int = 2048):
        self.output_dir = output_dir
        self.map_height = map_height
        self.map_dir = f"{output_dir}/map"
        ensure_dir(self.map_dir)
        self._terrain_names: List[str] = []

    # ---- images ----------------------------------------------------

    def save_heightmap(self, heightmap: np.ndarray) -> str:
        return save_image(heightmap.astype(np.uint8), f"{self.map_dir}/heightmap.bmp", mode="L")

    def save_provinces_bmp(self, provinces_bmp: np.ndarray) -> str:
        return save_image(provinces_bmp.astype(np.uint8), f"{self.map_dir}/provinces.bmp", mode="RGB")

    def save_world_normal(self, normal_map: np.ndarray) -> str:
        return save_image(normal_map.astype(np.uint8), f"{self.map_dir}/world_normal.bmp", mode="RGB")

    def save_watercolor_bmp(self, watercolor: np.ndarray) -> str:
        return save_image(watercolor.astype(np.uint8), f"{self.map_dir}/watercolor.bmp", mode="RGB")

    def save_terrain_bmp(self, terrain_bmp: np.ndarray) -> str:
        """Converts the RGB terrain canvas into an indexed bmp + records the
        index order so write_terrain_txt() can reference the same indices."""
        from engine.map_generation import TerrainClassifier
        colors = TerrainClassifier.TERRAIN_COLORS
        names = list(colors.keys())
        self._terrain_names = names

        idx_img = np.zeros(terrain_bmp.shape[:2], dtype=np.uint8)
        for i, name in enumerate(names):
            rgb = np.array(colors[name], dtype=np.uint8)
            mask = np.all(terrain_bmp == rgb, axis=-1)
            idx_img[mask] = i

        pal_img = Image.fromarray(idx_img, mode="P")
        palette = []
        for name in names:
            palette.extend(colors[name])
        palette += [0, 0, 0] * (256 - len(names))
        pal_img.putpalette(palette)
        path = f"{self.map_dir}/terrain.bmp"
        pal_img.save(path)
        return path

    def save_rivers_bmp(self, rivers_bmp: np.ndarray) -> str:
        idx_img = np.zeros(rivers_bmp.shape[:2], dtype=np.uint8)
        for i, rgb in enumerate(RIVER_PALETTE):
            if i == 0:
                continue
            mask = np.all(rivers_bmp == np.array(rgb, dtype=np.uint8), axis=-1)
            idx_img[mask] = i
        # engine paints a near-miss widest-blue -- snap it onto the canonical one
        off_mask = np.all(rivers_bmp == np.array([0, 0, 225], dtype=np.uint8), axis=-1)
        idx_img[off_mask] = 7

        pal_img = Image.fromarray(idx_img, mode="P")
        palette = []
        for rgb in RIVER_PALETTE:
            palette.extend(rgb)
        palette += [0, 0, 0] * (256 - len(RIVER_PALETTE))
        pal_img.putpalette(palette)
        path = f"{self.map_dir}/rivers.bmp"
        pal_img.save(path)
        return path

    def save_trees_bmp(self, terrain_bmp: np.ndarray) -> str:
        """EU4 refuses to load without at least a few tree pixels painted."""
        from engine.map_generation import TerrainClassifier
        colors = TerrainClassifier.TERRAIN_COLORS

        tree_mask = np.zeros(terrain_bmp.shape[:2], dtype=bool)
        for name in WOODED_TERRAIN:
            rgb = np.array(colors[name], dtype=np.uint8)
            tree_mask |= np.all(terrain_bmp == rgb, axis=-1)

        idx_img = np.zeros(terrain_bmp.shape[:2], dtype=np.uint8)
        idx_img[tree_mask] = 1
        if not tree_mask.any():
            idx_img[0, 0] = 1  # guarantee at least one tree pixel

        pal_img = Image.fromarray(idx_img, mode="P")
        palette = [200, 200, 200, 40, 120, 40] + [0, 0, 0] * 254
        pal_img.putpalette(palette)
        path = f"{self.map_dir}/trees.bmp"
        pal_img.save(path)
        return path

    # ---- text: province & map metadata ------------------------------

    def write_definition_csv(self, province_infos: List) -> Tuple[str, Dict[int, str]]:
        from resources.name_lists import get_names_for_continent

        by_continent: Dict[str, List] = {}
        for p in province_infos:
            if p.is_sea:
                continue
            by_continent.setdefault(p.continent_name or "unassigned", []).append(p)

        names: Dict[int, str] = {}
        used_names = set()
        for continent, provs in by_continent.items():
            pool = get_names_for_continent(continent, count=len(provs) + 10)
            for i, p in enumerate(provs):
                base = pool[i] if i < len(pool) else f"{continent.replace('_', ' ').title()} {p.id}"
                candidate, n = base, 2
                while candidate in used_names:
                    candidate = f"{base} {n}"
                    n += 1
                used_names.add(candidate)
                names[p.id] = candidate

        lines = ["province;red;green;blue;x;x"]
        for p in sorted(province_infos, key=lambda x: x.id):
            r, g, b = (int(c) for c in p.color)
            if p.is_sea:
                nm = f"Sea Zone {p.id}"
            else:
                nm = names.get(p.id, f"Province {p.id}")
            nm = nm.replace(";", " ").replace('"', "'")
            lines.append(f"{p.id};{r};{g};{b};{nm};x")

        path = f"{self.map_dir}/definition.csv"
        write_text(path, "\n".join(lines) + "\n")
        return path, names

    def write_default_map(self, width: int, height: int, province_infos: List,
                           tree_index: int = 1) -> str:
        sea_ids = sorted(p.id for p in province_infos if p.is_sea)
        max_provinces = max((p.id for p in province_infos), default=0) + 1

        lines = [
            f"width = {width}",
            f"height = {height}",
            f"max_provinces = {max_provinces}",
            "",
            "sea_starts = {",
            "    " + " ".join(str(i) for i in sea_ids),
            "}",
            "only_used_for_random = { }",
            "lakes = { }",
            "force_coastal = { }",
            "",
            'definitions = "definition.csv"',
            'provinces = "provinces.bmp"',
            'positions = "positions.txt"',
            'terrain = "terrain.bmp"',
            'rivers = "rivers.bmp"',
            'terrain_definition = "terrain.txt"',
            'heightmap = "heightmap.bmp"',
            'tree_definition = "trees.bmp"',
            'continent = "continent.txt"',
            'adjacencies = "adjacencies.csv"',
            'climate = "climate.txt"',
            'region = "region.txt"',
            'superregion = "superregion.txt"',
            'area = "area.txt"',
            'provincegroup = "provincegroup.txt"',
            'ambient_object = "ambient_object.txt"',
            'seasons = "seasons.txt"',
            'trade_winds = "trade_winds.txt"',
            "",
            f"tree = {{ {tree_index} }}",
        ]
        path = f"{self.map_dir}/default.map"
        write_text(path, "\n".join(lines) + "\n")
        return path

    def write_positions_txt(self, province_infos: List) -> str:
        lines = []
        for p in sorted(province_infos, key=lambda x: x.id):
            gx = float(p.center_x)
            gy = float(self.map_height - p.center_y)  # EU4's y axis is bottom-up
            lines.append(f"{p.id} = {{")
            lines.append("    position = {")
            lines.append(f"        {gx:.3f} {gy:.3f} {gx+5:.3f} {gy:.3f} {gx:.3f} {gy:.3f}")
            lines.append(f"        {gx-5:.3f} {gy:.3f} {gx:.3f} {gy:.3f} {gx+5:.3f} {gy-5:.3f} {gx:.3f} {gy:.3f}")
            lines.append("    }")
            lines.append("    rotation = {")
            lines.append("        0.000 0.000 0.000 0.785 0.000 0.000 0.000")
            lines.append("    }")
            lines.append("    height = {")
            lines.append("        0.000 0.000 1.000 0.000 0.000 0.000 0.000")
            lines.append("    }")
            lines.append("}")
        path = f"{self.map_dir}/positions.txt"
        write_text(path, "\n".join(lines) + "\n")
        return path

    def write_continent_txt(self, province_infos: List) -> str:
        by_continent: Dict[str, List[int]] = {}
        for p in province_infos:
            if p.is_sea:
                continue
            by_continent.setdefault(p.continent_name or "unassigned", []).append(p.id)

        lines = []
        for name, ids in by_continent.items():
            lines.append(f"{name} = {{")
            lines.append("    " + " ".join(str(i) for i in sorted(ids)))
            lines.append("}")
            lines.append("")
        lines.append("new_world = { }")
        path = f"{self.map_dir}/continent.txt"
        write_text(path, "\n".join(lines) + "\n")
        return path

    def write_climate_txt(self, climate_zones: Dict[str, List[int]],
                           wasteland_ids: List[int]) -> str:
        tropical = set(climate_zones.get("equatorial_tropical", [])) \
            | set(climate_zones.get("monsoon", [])) \
            | set(climate_zones.get("equatorial_rain", []))
        arid = set(climate_zones.get("arid", [])) | set(climate_zones.get("semi_arid", []))
        severe = set(climate_zones.get("severe_winter", []))
        normal = set(climate_zones.get("normal_winter", []))
        mild = set(climate_zones.get("mild_winter", []))
        arctic = set(severe)  # harshest winter band doubles as the arctic special-zone

        def block(name: str, ids) -> str:
            return f"{name} = {{\n    " + " ".join(str(i) for i in sorted(ids)) + "\n}\n"

        content = "".join([
            block("tropical", tropical),
            block("arid", arid),
            block("arctic", arctic),
            block("mild_winter", mild),
            block("normal_winter", normal),
            block("severe_winter", severe),
            block("impassable", wasteland_ids),
        ])
        path = f"{self.map_dir}/climate.txt"
        write_text(path, content)
        return path

    def write_terrain_txt(self) -> str:
        from engine.map_generation import TerrainClassifier
        colors = TerrainClassifier.TERRAIN_COLORS
        names = self._terrain_names or list(colors.keys())

        lines = []
        for i, name in enumerate(names):
            gp = TERRAIN_GAMEPLAY.get(name, {})
            r, g, b = colors[name]
            lines.append(f"{name} = {{")
            lines.append(f"    color = {{ {r} {g} {b} }}")
            if gp.get("is_water"):
                lines.append("    is_water = yes")
            else:
                lines.append(f"    type = {gp.get('type', 'plains')}")
                lines.append(f"    movement_cost = {gp.get('movement_cost', 1.0)}")
                lines.append(f"    defence = {gp.get('defence', 0)}")
            lines.append("}")
            lines.append("")

        lines.append("terrain = {")
        for i, name in enumerate(names):
            gp = TERRAIN_GAMEPLAY.get(name, {})
            t = "ocean" if gp.get("is_water") else gp.get("type", "plains")
            lines.append(f"    {name} = {{")
            lines.append(f"        type = {t}")
            lines.append(f"        color = {{ {i} }}")
            lines.append("    }")
        lines.append("}")
        lines.append("")
        lines.append("tree = {")
        lines.append("    forest_tree = {")
        lines.append("        terrain = forest")
        lines.append("        color = { 1 }")
        lines.append("    }")
        lines.append("}")

        path = f"{self.map_dir}/terrain.txt"
        write_text(path, "\n".join(lines) + "\n")
        return path

    def write_adjacencies_csv(self) -> str:
        lines = [
            "From;To;Type;Through;start_x;start_y;stop_x;stop_y;Comment",
            "-1;-1;;-1;-1;-1;-1;-1;",
        ]
        path = f"{self.map_dir}/adjacencies.csv"
        write_text(path, "\n".join(lines) + "\n")
        return path

    def write_area_region_superregion(self, province_infos: List) -> None:
        by_continent: Dict[str, List[int]] = {}
        for p in province_infos:
            if p.is_sea:
                continue
            by_continent.setdefault(p.continent_name or "unassigned", []).append(p.id)

        area_lines: List[str] = []
        region_lines: List[str] = ["random_new_world_region = { }", ""]
        region_names: List[str] = []
        CHUNK = 6

        for cont, ids in by_continent.items():
            ids = sorted(ids)
            area_names_here = []
            for start in range(0, len(ids), CHUNK):
                chunk = ids[start:start + CHUNK]
                area_name = f"{cont}_area_{start // CHUNK + 1}"
                area_names_here.append(area_name)
                area_lines += [f"{area_name} = {{", "    " + " ".join(map(str, chunk)), "}", ""]
            region_name = f"{cont}_region"
            region_names.append(region_name)
            region_lines += [
                f"{region_name} = {{",
                "    areas = {",
                "        " + " ".join(area_names_here),
                "    }",
                "}", "",
            ]

        sea_ids = sorted(p.id for p in province_infos if p.is_sea)
        sea_area_names = []
        for start in range(0, len(sea_ids), 20):
            chunk = sea_ids[start:start + 20]
            area_name = f"sea_area_{start // 20 + 1}"
            sea_area_names.append(area_name)
            area_lines += [f"{area_name} = {{", "    " + " ".join(map(str, chunk)), "}", ""]
        if sea_area_names:
            region_lines += [
                "sea_region = {",
                "    areas = {",
                "        " + " ".join(sea_area_names),
                "    }",
                "}", "",
            ]
            region_names.append("sea_region")

        land_regions = [r for r in region_names if r != "sea_region"]
        superregion_lines = ["world_superregion = {", "    " + " ".join(land_regions), "}", ""]
        if "sea_region" in region_names:
            superregion_lines += ["sea_superregion = {", "    sea_region", "}", ""]
        superregion_lines.append("new_world_superregion = { }")

        write_text(f"{self.map_dir}/area.txt", "\n".join(area_lines) + "\n")
        write_text(f"{self.map_dir}/region.txt", "\n".join(region_lines) + "\n")
        write_text(f"{self.map_dir}/superregion.txt", "\n".join(superregion_lines) + "\n")
        write_text(f"{self.map_dir}/provincegroup.txt", "# no province groups defined\n")

    def copy_static_map_files(self) -> None:
        """Copies the small always-the-same map files from the bundled templates."""
        src_dir = str(eu4_wgs_v8.TEMPLATES_DIR / "map")
        for fname in ("ambient_object.txt", "trade_winds.txt"):
            src = os.path.join(src_dir, fname)
            dst = os.path.join(self.map_dir, fname)
            if os.path.exists(src):
                shutil.copy(src, dst)
            else:
                write_text(dst, "")

        lakes_src = os.path.join(src_dir, "lakes")
        lakes_dst = os.path.join(self.map_dir, "lakes")
        ensure_dir(lakes_dst)
        if os.path.isdir(lakes_src):
            for f in os.listdir(lakes_src):
                shutil.copy(os.path.join(lakes_src, f), os.path.join(lakes_dst, f))
        else:
            write_text(os.path.join(lakes_dst, "00_lakes.txt"), "")

        write_text(os.path.join(self.map_dir, "seasons.txt"), _SEASONS_STUB)


_SEASONS_STUB = (
    "winter = {\n"
    "    start_date = 00.12.01\n"
    "    end_date = 00.02.28\n"
    "    hsv_north = { 0.0 0.0 -0.1 }\n"
    "    colorbalance_north = { 1.0 1.0 1.0 }\n"
    "    hsv_center = { 0.0 0.0 0.0 }\n"
    "    colorbalance_center = { 1.0 1.0 1.0 }\n"
    "    hsv_south = { 0.0 0.0 -0.1 }\n"
    "    colorbalance_south = { 1.0 1.0 1.0 }\n"
    "}\n"
    "spring = {\n"
    "    start_date = 00.03.01\n"
    "    end_date = 00.05.31\n"
    "    hsv_north = { 0.0 0.0 0.0 }\n"
    "    colorbalance_north = { 1.0 1.0 1.0 }\n"
    "    hsv_center = { 0.0 0.0 0.0 }\n"
    "    colorbalance_center = { 1.0 1.0 1.0 }\n"
    "    hsv_south = { 0.0 0.0 0.0 }\n"
    "    colorbalance_south = { 1.0 1.0 1.0 }\n"
    "}\n"
    "summer = {\n"
    "    start_date = 00.06.01\n"
    "    end_date = 00.08.31\n"
    "    hsv_north = { 0.0 0.0 0.05 }\n"
    "    colorbalance_north = { 1.0 1.0 1.0 }\n"
    "    hsv_center = { 0.0 0.0 0.0 }\n"
    "    colorbalance_center = { 1.0 1.0 1.0 }\n"
    "    hsv_south = { 0.0 0.0 0.05 }\n"
    "    colorbalance_south = { 1.0 1.0 1.0 }\n"
    "}\n"
    "autumn = {\n"
    "    start_date = 00.09.01\n"
    "    end_date = 00.11.30\n"
    "    hsv_north = { 0.0 0.0 -0.05 }\n"
    "    colorbalance_north = { 1.0 1.0 1.0 }\n"
    "    hsv_center = { 0.0 0.0 0.0 }\n"
    "    colorbalance_center = { 1.0 1.0 1.0 }\n"
    "    hsv_south = { 0.0 0.0 -0.05 }\n"
    "    colorbalance_south = { 1.0 1.0 1.0 }\n"
    "}\n"
)


# ═══════════════════════════════════════════════════════════════
#  COUNTRY FILE EXPORTER  (common/countries, common/ideas, localisation)
# ═══════════════════════════════════════════════════════════════

class CountryFileExporter:

    def __init__(self, output_dir: str, map_height: int = 2048):
        self.output_dir = output_dir
        self.map_height = map_height

    def write_country_common_file(self, tag: str, data) -> str:
        r, g, b = (int(c) for c in data.color)
        lines = [
            f"government = {data.government}",
            f"color = {{ {r} {g} {b} }}",
            "historical_idea_groups = { }",
            f'monarch_names = {{ "{data.ruler_name} #0" = 100 }}',
            f'leader_names = {{ "{data.ruler_name}" }}',
            f'ship_names = {{ "{data.short_name}" }}',
        ]
        path = f"{self.output_dir}/common/countries/{tag} - {data.short_name}.txt"
        write_text(path, "\n".join(lines) + "\n")
        return path

    def write_country_history_file(self, tag: str, data) -> str:
        birth_year = max(1370, 1444 - int(data.ruler_age))
        lines = [
            f"government = {data.government}",
            f"technology_group = {data.tech_group}",
            f"religion = {data.religion}",
            f"primary_culture = {data.primary_culture}",
            f"capital = {data.capital_province}",
            "1444.11.11 = {",
            "    monarch = {",
            f'        name = "{data.ruler_name}"',
            f'        dynasty = "{data.short_name}"',
            f"        birth_date = {birth_year}.1.1",
            f"        adm = {data.ruler_adm}",
            f"        dip = {data.ruler_dip}",
            f"        mil = {data.ruler_mil}",
            "    }",
            "}",
        ]
        path = f"{self.output_dir}/history/countries/{tag} - {data.short_name}.txt"
        write_text(path, "\n".join(lines) + "\n")
        return path

    def write_national_ideas(self, tag: str, center_y: int) -> str:
        from content.world_content import IdeaGenerator
        script = IdeaGenerator.generate_national_ideas(tag, center_y, map_height=self.map_height)
        path = f"{self.output_dir}/common/ideas/{tag}_ideas.txt"
        write_text(path, script)
        return path

    def write_country_tags(self, countries: Dict[str, Any]) -> str:
        lines = [f'{tag} = "countries/{tag} - {data.short_name}.txt"' for tag, data in countries.items()]
        path = f"{self.output_dir}/common/country_tags/00_countries.txt"
        write_text(path, "\n".join(lines) + "\n")
        return path

    def write_localization(self, countries: Dict[str, Any],
                            province_names: Optional[Dict[int, str]] = None) -> str:
        lines = ["l_english:"]
        for tag, data in countries.items():
            lines.append(f' {tag}:0 "{data.short_name}"')
            lines.append(f' {tag}_ADJ:0 "{data.short_name}"')
            lines.append(f' {tag}_DEF:0 "{data.full_name}"')
        if province_names:
            for pid, name in province_names.items():
                safe = name.replace('"', "'")
                lines.append(f' PROV{pid}:0 "{safe}"')
        path = f"{self.output_dir}/localisation/countries_l_english.yml"
        write_text(path, "\n".join(lines) + "\n", encoding="utf-8-sig")
        return path


# ═══════════════════════════════════════════════════════════════
#  PROVINCE HISTORY EXPORTER  (history/provinces)
# ═══════════════════════════════════════════════════════════════

class ProvinceHistoryExporter:

    def __init__(self, output_dir: str, map_height: int = 2048):
        self.output_dir = output_dir
        self.map_height = map_height

    def write_province_history(self, province_info, name: str, owner_tag: str,
                                culture: str, religion: str, trade_good: str) -> str:
        p = province_info
        base = max(1, round(3 + (p.avg_elevation - 140) / 40))
        lines = [
            f"owner = {owner_tag}",
            f"controller = {owner_tag}",
            f"add_core = {owner_tag}",
            f"culture = {culture}",
            f"religion = {religion}",
            f"trade_goods = {trade_good}",
            f"base_tax = {base}",
            f"base_production = {base}",
            f"base_manpower = {max(1, base - 1)}",
            "is_city = yes",
        ]
        safe_name = name.replace('"', "'")
        path = f"{self.output_dir}/history/provinces/{p.id} - {safe_name}.txt"
        write_text(path, "\n".join(lines) + "\n")
        return path


# ═══════════════════════════════════════════════════════════════
#  MOD DESCRIPTOR EXPORTER
# ═══════════════════════════════════════════════════════════════

class ModDescriptorExporter:

    @staticmethod
    def write_mod_descriptor(mod_name: str, tech_name: str, mod_root: str,
                              output_dir: str, supported_version: str = "1.37") -> Tuple[str, str]:
        content = "\n".join([
            f'name = "{mod_name}"',
            f'path = "mod/{tech_name}"',
            "tags = {",
            '    "Total Conversion"',
            '    "Map"',
            "}",
            f'supported_version = "{supported_version}"',
        ]) + "\n"

        pointer_path = f"{output_dir}/{tech_name}.mod"
        write_text(pointer_path, content)
        # Modern EU4 also supports a self-contained descriptor inside the mod folder.
        descriptor_path = f"{mod_root}/descriptor.mod"
        write_text(descriptor_path, content)
        return pointer_path, descriptor_path


# ═══════════════════════════════════════════════════════════════
#  MASTER ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════

class MasterExportOrchestrator:
    """Ties every exporter together into one `export_complete_mod()` call."""

    def __init__(self, output_base_dir: str, map_height: int = 2048):
        self.output_base_dir = output_base_dir
        self.map_height = map_height

    def create_mod_structure(self, mod_name: str) -> Tuple[str, str]:
        tech_name = _slugify(mod_name) or "GeneratedMod"
        mod_root = f"{self.output_base_dir}/{tech_name}"
        for sub in MOD_SUBDIRS:
            ensure_dir(f"{mod_root}/{sub}")
        return mod_root, tech_name

    def export_complete_mod(self, mod_name: str, heightmap: np.ndarray, land_mask: np.ndarray,
                             provinces_bmp: np.ndarray, province_infos: List,
                             countries: Dict[str, Any], climate_zones: Dict[str, List[int]],
                             terrain_bmp: np.ndarray, rivers_bmp: np.ndarray,
                             normal_map: Optional[np.ndarray] = None,
                             watercolor_bmp: Optional[np.ndarray] = None) -> Dict[str, str]:
        from content.world_content import (
            FlagGenerator, ReligionGenerator, CultureGenerator,
            CelestialDirectorate, TradeGenerator, DiplomacyGenerator,
            RICH_COMMODITIES, BARREN_COMMODITIES,
        )

        mod_root, tech_name = self.create_mod_structure(mod_name)
        height, width = heightmap.shape[:2]
        results: Dict[str, str] = {}

        # ---- map files ----
        map_exp = MapFileExporter(mod_root, map_height=self.map_height)
        results["heightmap"] = map_exp.save_heightmap(heightmap)
        results["provinces_bmp"] = map_exp.save_provinces_bmp(provinces_bmp)
        results["terrain_bmp"] = map_exp.save_terrain_bmp(terrain_bmp)
        results["rivers_bmp"] = map_exp.save_rivers_bmp(rivers_bmp)
        results["trees_bmp"] = map_exp.save_trees_bmp(terrain_bmp)
        if normal_map is not None:
            results["world_normal"] = map_exp.save_world_normal(normal_map)
        if watercolor_bmp is not None:
            results["watercolor_bmp"] = map_exp.save_watercolor_bmp(watercolor_bmp)

        results["definition_csv"], province_names = map_exp.write_definition_csv(province_infos)
        results["default_map"] = map_exp.write_default_map(width, height, province_infos)
        results["positions_txt"] = map_exp.write_positions_txt(province_infos)
        results["continent_txt"] = map_exp.write_continent_txt(province_infos)
        wasteland_ids = [p.id for p in province_infos if p.is_wasteland]
        results["climate_txt"] = map_exp.write_climate_txt(climate_zones, wasteland_ids)
        results["terrain_txt"] = map_exp.write_terrain_txt()
        results["adjacencies_csv"] = map_exp.write_adjacencies_csv()
        map_exp.write_area_region_superregion(province_infos)
        map_exp.copy_static_map_files()

        # ---- world content (religion / culture / HRE-equivalent) ----
        results["religion_txt"] = ReligionGenerator.generate_religion_file(mod_root)
        results["cultures_txt"] = CultureGenerator.generate_cultures_file(mod_root)
        results["imperial_reforms"] = CelestialDirectorate.generate_imperial_reforms(mod_root)
        results["trade_goods"] = TradeGenerator.generate_trade_goods_files(mod_root)
        results["trade_nodes"] = TradeGenerator.generate_inverted_trade_nodes(
            province_infos, mod_root, map_height=self.map_height)

        # ---- countries ----
        country_exp = CountryFileExporter(mod_root, map_height=self.map_height)
        for tag, data in countries.items():
            country_exp.write_country_common_file(tag, data)
            country_exp.write_country_history_file(tag, data)
            country_exp.write_national_ideas(tag, data.center_y)
            FlagGenerator.generate_flag(tag, is_advanced=data.is_advanced,
                                         output_dir=mod_root, continent=data.continent)
        country_exp.write_country_tags(countries)
        country_exp.write_localization(countries, province_names)

        # ---- province ownership + history ----
        owner_by_province = self._assign_provinces_to_countries(province_infos, countries)
        prov_exp = ProvinceHistoryExporter(mod_root, map_height=self.map_height)
        h = self.map_height
        for p in province_infos:
            if p.is_sea or p.is_wasteland:
                continue
            owner_tag = owner_by_province.get(p.id)
            if not owner_tag or owner_tag not in countries:
                continue
            data = countries[owner_tag]
            is_advanced = (h * 0.25 <= p.center_y < h * 0.75)
            goods_pool = RICH_COMMODITIES if is_advanced else BARREN_COMMODITIES
            trade_good = list(goods_pool.keys())[p.id % len(goods_pool)]
            name = province_names.get(p.id, f"Province {p.id}")
            prov_exp.write_province_history(
                p, name, owner_tag, data.primary_culture, data.religion, trade_good)

        # ---- mod descriptor ----
        pointer, descriptor = ModDescriptorExporter.write_mod_descriptor(
            mod_name, tech_name, mod_root, self.output_base_dir)
        results["mod_pointer"] = pointer
        results["mod_descriptor"] = descriptor

        return results

    # ---- helpers ---------------------------------------------------

    @staticmethod
    def _assign_provinces_to_countries(province_infos: List, countries: Dict[str, Any]) -> Dict[int, str]:
        """Nearest-capital assignment: every land province goes to whichever
        generated country's capital is closest to it."""
        land = [p for p in province_infos if not p.is_sea and not p.is_wasteland]
        if not countries or not land:
            return {}

        caps = [(tag, data.center_x, data.center_y) for tag, data in countries.items()]
        owner: Dict[int, str] = {}
        for p in land:
            best_tag, best_dist = None, None
            for tag, cx, cy in caps:
                d = (p.center_x - cx) ** 2 + (p.center_y - cy) ** 2
                if best_dist is None or d < best_dist:
                    best_dist, best_tag = d, tag
            owner[p.id] = best_tag
        # guarantee each country at least owns its own capital province
        for tag, data in countries.items():
            owner[data.capital_province] = tag
        return owner
