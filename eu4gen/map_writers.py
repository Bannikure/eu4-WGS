"""
Module C – Map Metadata Writers.

Functions that take in-memory data and write the EU4 map text/CSV files.

Public API
----------
generate_definition_csv          – province colour registry CSV
generate_default_map             – default.map
generate_climate_txt             – climate.txt (latitude-based zones)
calculate_province_positions     – centroid scan from provinces bitmap
write_positions_txt              – positions.txt
write_province_history_entry     – single province history file (explicit params)
"""

from __future__ import annotations

import csv
import os
from typing import Any

import numpy as np

from .constants import MAP_HEIGHT


def generate_definition_csv(
    province_data: list[tuple[int, int, int, int, str]],
    output_path: str = "map/definition.csv",
) -> None:
    """Write the EU4 province colour registry CSV."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", newline="", encoding="cp1252") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["province", "red", "green", "blue", "x", "x"])
        for p_id, r, g, b, name in province_data:
            writer.writerow([p_id, r, g, b, name, "x"])
    print(f"✓ definition.csv → {len(province_data)} provinces")


def generate_default_map(
    max_provinces: int,
    sea_ids: list[int],
    wasteland_ids: list[int],
    output_path: str = "map/default.map",
) -> None:
    """Write the standard EU4 ``default.map`` for a 5632 × 2048 map."""
    sea_str       = " ".join(map(str, sea_ids))       if sea_ids       else ""
    wasteland_str = " ".join(map(str, wasteland_ids)) if wasteland_ids else ""

    map_script = (
        f"# default.map for 5632x2048 EU4 Total Conversion Mod\n"
        f"width = 5632\nheight = 2048\nmax_provinces = {max_provinces}\n\n"
        f'definitions = "definition.csv"\nprovinces = "provinces.bmp"\n'
        f'positions = "positions.txt"\nterrain = "terrain.bmp"\n'
        f'rivers = "rivers.bmp"\nterrain_definition = "terrain.txt"\n'
        f'heightmap = "heightmap.bmp"\ntree_definition = "trees.bmp"\n'
        f'continent = "continent.txt"\nadjacencies = "adjacencies.csv"\n'
        f'climate = "climate.txt"\n\n'
        f"sea_starts = {{\n\t{sea_str}\n}}\n\n"
        f"only_titles = {{\n\t{wasteland_str}\n}}\n\n"
        f'canal_definition = "canal_definitions.txt"\n'
    )

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(map_script)
    print(f"✓ default.map generated → {output_path}")


def generate_climate_txt(
    province_telemetry: list[dict[str, Any]],
    output_path: str = "map/climate.txt",
) -> None:
    """Assign climate zones to provinces based on Y-coordinate latitude."""
    equatorial_tropical: list[int] = []
    severe_winter:       list[int] = []
    normal_winter:       list[int] = []
    mild_winter:         list[int] = []

    for p in province_telemetry:
        p_id = int(p["id"])
        y    = int(p["center_y"])

        if y < 300 or y > 1748:
            severe_winter.append(p_id)
        elif (300 <= y < 600) or (1448 <= y <= 1748):
            normal_winter.append(p_id)
        elif 900 <= y <= 1148:
            equatorial_tropical.append(p_id)
        else:
            mild_winter.append(p_id)

    climate_script = (
        "# climate.txt auto-generated for 5632x2048\n\n"
        f"mild_winter = {{ {' '.join(map(str, mild_winter))} }}\n"
        f"normal_winter = {{ {' '.join(map(str, normal_winter))} }}\n"
        f"severe_winter = {{ {' '.join(map(str, severe_winter))} }}\n"
        f"equatorial_tropical = {{ {' '.join(map(str, equatorial_tropical))} }}\n"
        "arid = {  }\nsemi_arid = {  }\nmonsoon = {  }\nequatorial_rain = {  }\n"
    )

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(climate_script)
    print(f"✓ climate.txt generated → {output_path}")


def calculate_province_positions(
    provinces_bmp: np.ndarray,
    unique_colors: np.ndarray,
) -> dict[int, dict[str, int]]:
    """Scan the province bitmap to compute per-province centroids."""
    positions_data: dict[int, dict[str, int]] = {}

    for p_idx, color in enumerate(unique_colors):
        r, g, b = int(color[0]), int(color[1]), int(color[2])
        match_mask = (
            (provinces_bmp[:, :, 0] == r)
            & (provinces_bmp[:, :, 1] == g)
            & (provinces_bmp[:, :, 2] == b)
        )
        y_indices, x_indices = np.where(match_mask)
        if len(x_indices) == 0:
            continue

        center_x = int(np.mean(x_indices))
        center_y = int(np.mean(y_indices))
        eu4_y    = MAP_HEIGHT - center_y

        p_id = p_idx + 1
        positions_data[p_id] = {
            "bc_x":   center_x,
            "bc_y":   eu4_y,
            "unit_x": center_x + 5,
            "unit_y": eu4_y,
            "text_x": center_x,
            "text_y": eu4_y - 5,
        }

    return positions_data


def write_positions_txt(
    positions_data: dict[int, dict[str, int]],
    output_path: str = "map/positions.txt",
) -> None:
    """Write the province position blocks to ``positions.txt``."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for p_id, pos in positions_data.items():
            f.write(
                f"{p_id} = {{\n"
                f"\tposition = {{\n"
                f"\t\t{pos['bc_x']}.000 {pos['bc_y']}.000\n"
                f"\t\t{pos['unit_x']}.000 {pos['unit_y']}.000\n"
                f"\t\t{pos['text_x']}.000 {pos['text_y']}.000\n"
                f"\t}}\n"
                f"\trotation = {{ 0.000 0.000 0.000 }}\n"
                f"}}\n\n"
            )
    print(f"✓ positions.txt → {len(positions_data)} provinces")


def write_province_history_entry(
    p_id: int,
    owner_tag: str,
    dev: dict[str, int],
    trade_good: str,
    religion: str,
    culture: str,
    output_dir: str,
) -> None:
    """Write a single province history file with fully specified parameters.

    A procedural variant that calculates terrain/religion internally lives in
    ``country.py`` as ``generate_province_history``.
    """
    out_dir = os.path.join(output_dir, "history", "provinces")
    os.makedirs(out_dir, exist_ok=True)

    content = (
        f"# Auto-generated history for province {p_id}\n"
        f"owner = {owner_tag}\n"
        f"culture = {culture}\n"
        f"religion = {religion}\n"
        f"base_tax = {dev.get('tax', 2)}\n"
        f"base_production = {dev.get('prod', 2)}\n"
        f"base_manpower = {dev.get('man', 2)}\n"
        f"trade_goods = {trade_good}\n"
    )

    with open(os.path.join(out_dir, f"{p_id}.txt"), "w", encoding="utf-8") as f:
        f.write(content)
