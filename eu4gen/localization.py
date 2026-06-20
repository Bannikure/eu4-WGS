"""Module H – Localization & Dynamic Names."""

from __future__ import annotations

import os
from typing import Any


def generate_dynamic_province_names(land_province_ids: list[int], output_dir: str) -> None:
    """Create per-culture dynamic province renaming files."""
    out = os.path.join(output_dir, "common", "province_names")
    os.makedirs(out, exist_ok=True)
    chinese_lines = "".join(f'{p} = "Sovereign_Outpost_{p}"\n' for p in land_province_ids)
    french_lines  = "".join(f'{p} = "Mud_Camp_{p}"\n'          for p in land_province_ids)
    with open(os.path.join(out, "chinese_dialect.txt"),     "w", encoding="utf-8") as f:
        f.write(chinese_lines)
    with open(os.path.join(out, "cosmopolitan_french.txt"), "w", encoding="utf-8") as f:
        f.write(french_lines)
    print(f"✓ Province names generated ({len(land_province_ids)} provinces)")


def write_culture_localisation(cultures: list[dict[str, Any]], output_dir: str) -> None:
    """Append culture display-name entries to the shared cultures YML file."""
    os.makedirs(os.path.join(output_dir, "localisation"), exist_ok=True)
    path = os.path.join(output_dir, "localisation", "custom_cultures_l_english.yml")
    with open(path, "a", encoding="utf-8-sig") as f:
        f.write("l_english:\n")
        for c in cultures:
            f.write(f' {c["id"]}:0 "{c["name"]}"\n')


def write_country_mission_file(tag: str, missions: list[dict[str, Any]], output_dir: str) -> None:
    """Write the mission tree script file for a country."""
    os.makedirs(os.path.join(output_dir, "missions"), exist_ok=True)
    path = os.path.join(output_dir, "missions", f"{tag}_missions.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"{tag}_mission_tree = {{\n")
        for m in missions:
            f.write(
                f"    {m['id']} = {{\n        icon = mission_conquest\n"
                "        required_missions = { }\n        provinces_to_highlight = { }\n"
                "        effect = {\n"
            )
            for eff in m["effects"]:
                f.write(f"            {eff}\n")
            f.write("        }\n    }\n")
        f.write("}\n")


def write_mission_localisation(missions: list[dict[str, Any]], output_dir: str) -> None:
    """Append mission title and description entries to the shared missions YML."""
    os.makedirs(os.path.join(output_dir, "localisation"), exist_ok=True)
    path = os.path.join(output_dir, "localisation", "custom_missions_l_english.yml")
    with open(path, "a", encoding="utf-8-sig") as f:
        f.write("l_english:\n")
        for m in missions:
            f.write(f' {m["id"]}:0 "{m["title"]}"\n')
            f.write(f' {m["id"]}_desc:0 "{m["desc"]}"\n')
