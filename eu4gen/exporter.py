"""
Module J – Master Export Orchestrator.

The original script contained a pseudo-code fragment that was a partial
duplicate of ``export_complete_eu4_mod`` with an ellipsis body — shadowing
the real function and causing a SyntaxError. That fragment has been removed;
the trade-company and culture-generation steps it described are integrated
into the single canonical function below.
"""

from __future__ import annotations

import os
import shutil
from typing import Any

import numpy as np
from PIL import Image

from .cultures import assign_cultures_to_provinces, generate_culture_groups, generate_cultures_for_group
from .country import generate_country_missions
from .economy import (
    apply_trade_company_bonuses_to_nodes,
    assign_trade_companies,
    generate_inverted_trade_nodes,
    generate_trade_goods_files,
    write_trade_company_files,
)
from .localization import write_culture_localisation, write_country_mission_file, write_mission_localisation
from .map_writers import (
    generate_climate_txt,
    generate_definition_csv,
    generate_default_map,
    write_positions_txt,
    write_province_history_entry,
)
from .religion import generate_religion_database
from .render import generate_seasonal_terrain_bmp, generate_watercolor_bmp, generate_world_normal


def export_complete_eu4_mod(
    mod_display_name: str,
    technical_folder_name: str,
    generation_data: dict[str, Any],
) -> str:
    """Orchestrate a complete EU4 total-conversion mod from in-memory generation data.

    Args:
        mod_display_name: Human-readable name shown in the EU4 launcher.
        technical_folder_name: Filesystem-safe folder name (no spaces).
        generation_data: Dict produced by the world-generation thread.

    Returns:
        Absolute path to the created mod directory.
    """
    user_home = os.path.expanduser("~")
    base_mod_root = os.path.join(user_home, "Documents", "Paradox Interactive", "Europa Universalis IV", "mod")
    target_mod_directory = os.path.join(base_mod_root, technical_folder_name)

    if os.path.exists(target_mod_directory):
        shutil.rmtree(target_mod_directory)

    for dir_path in [
        "common/countries", "common/country_tags", "common/ideas", "common/prices",
        "common/religions", "common/trade_goods", "common/tradenodes",
        "common/trade_companies", "common/province_names",
        "history/countries", "history/provinces", "history/diplomacy",
        "map", "gfx/flags", "localisation", "missions",
    ]:
        os.makedirs(os.path.join(target_mod_directory, dir_path), exist_ok=True)

    mod_descriptor = (
        f'name="{mod_display_name}"\n'
        f'path="mod/{technical_folder_name}"\n'
        f'supported_version="1.37.*.*"\n'
        f'tags={{\n\t"Total Conversion"\n\t"Map"\n\t"Random World"\n}}\n'
        f'remote_file_id="0"\n'
    )
    for descriptor_path in [
        os.path.join(base_mod_root, f"{technical_folder_name}.mod"),
        os.path.join(target_mod_directory, "descriptor.mod"),
    ]:
        os.makedirs(os.path.dirname(descriptor_path), exist_ok=True)
        with open(descriptor_path, "w", encoding="utf-8") as f:
            f.write(mod_descriptor)

    # Unpack generation data
    heightmap:          np.ndarray                = generation_data["heightmap"]
    land_mask:          np.ndarray                = generation_data["land_mask"]
    provinces_bmp:      np.ndarray                = generation_data["provinces_bmp"]
    unique_colors:      np.ndarray                = generation_data["unique_colors"]
    river_map:          np.ndarray                = generation_data["rivers"]
    positions_data:     dict[int, dict[str, int]] = generation_data["positions"]
    province_telemetry: list[dict[str, Any]]       = generation_data["province_telemetry"]
    max_provinces:      int                        = generation_data["max_provinces"]
    island_ids:         list[int]                  = generation_data.get("island_ids", [])

    map_dir = os.path.join(target_mod_directory, "map")

    # Image assets
    Image.fromarray(heightmap,     "L"  ).save(os.path.join(map_dir, "heightmap.bmp"))
    Image.fromarray(provinces_bmp, "RGB").save(os.path.join(map_dir, "provinces.bmp"))
    Image.fromarray(river_map,     "RGB").save(os.path.join(map_dir, "rivers.bmp"))
    generate_world_normal(heightmap,   os.path.join(map_dir, "world_normal.bmp"))
    generate_watercolor_bmp(land_mask, os.path.join(map_dir, "watercolor.bmp"))
    generate_seasonal_terrain_bmp(heightmap, land_mask, os.path.join(map_dir, "terrain.bmp"))

    # Province metadata
    province_data = [
        (p_id, int(color[0]), int(color[1]), int(color[2]), f"Province_{p_id}")
        for p_id, color in enumerate(unique_colors, start=1)
    ]
    generate_definition_csv(province_data,  os.path.join(map_dir, "definition.csv"))
    write_positions_txt(positions_data,      os.path.join(map_dir, "positions.txt"))
    sea_ids = list(range(max_provinces - 50, max_provinces))
    generate_default_map(max_provinces, sea_ids, [], os.path.join(map_dir, "default.map"))
    generate_climate_txt(province_telemetry, os.path.join(map_dir, "climate.txt"))

    # Trade & economy
    generate_trade_goods_files(target_mod_directory)
    trade_nodes = generate_inverted_trade_nodes(province_telemetry, island_ids, target_mod_directory)
    company_map = assign_trade_companies(province_telemetry)
    write_trade_company_files(company_map, target_mod_directory)
    apply_trade_company_bonuses_to_nodes(trade_nodes, company_map)

    # Religion
    generate_religion_database(target_mod_directory)

    # Culture assignment
    culture_groups = generate_culture_groups(num_groups=6)
    all_cultures: list[dict[str, Any]] = []
    for g in culture_groups:
        all_cultures.extend(generate_cultures_for_group(g, num_cultures=4))
    province_cultures = assign_cultures_to_provinces(province_telemetry, culture_groups, all_cultures)
    write_culture_localisation(all_cultures, target_mod_directory)

    # Province histories
    sea_id_set = set(sea_ids)
    for p in province_telemetry:
        p_id = int(p["id"])
        if p_id in sea_id_set:
            continue
        center_y = int(p.get("center_y", 1024))
        dev_score = max(2, 6 - abs(center_y - 1024) // 200)
        dev = {"tax": dev_score, "prod": dev_score, "man": max(1, dev_score - 1)}
        religion   = "hinduism" if 512 <= center_y < 1536 else "catholic"
        culture    = province_cultures.get(p_id, "cosmopolitan_french")
        write_province_history_entry(p_id, "FRA", dev, "grain", religion, culture, target_mod_directory)

    print(f"✓ Mod exported to: {target_mod_directory}")
    return target_mod_directory


def generate_all_country_missions(
    countries: list[dict[str, Any]],
    province_telemetry: list[dict[str, Any]],
    output_dir: str,
) -> None:
    """Generate and write mission files for every country."""
    for c in countries:
        tag = str(c["tag"])
        country_data = {
            "capital_province": str(c["capital"]),
            "culture":          str(c["culture"]),
            "region":           str(c["region"]),
        }
        missions = generate_country_missions(tag, country_data, province_telemetry)
        write_country_mission_file(tag, missions, output_dir)
        write_mission_localisation(missions, output_dir)
