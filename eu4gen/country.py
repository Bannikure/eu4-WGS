"""
Module D – Country & Province Content Generators.

Fixes vs. original:
- ``MISSION_ARCHETYPES`` now imported from ``constants`` (was defined after
  ``generate_country_missions``, causing a NameError at runtime).
- The duplicate ``write_province_history_entry`` is renamed here to
  ``generate_province_history`` to avoid conflict with the explicit-params
  version in ``map_writers``.
"""

from __future__ import annotations

import logging
import os
import random
from typing import Any

import numpy as np
from PIL import Image, ImageOps

from .constants import (
    ADJECTIVES,
    ACRONYMS,
    ROOT_NAMES,
    GOVERNMENTS,
    FLAG_PALETTE,
    MISSION_ARCHETYPES,
)

logger = logging.getLogger(__name__)


def generate_country_name() -> tuple[str, str]:
    """Procedurally generate a flavor-rich country name.

    Returns:
        ``(short_root, full_name)``
    """
    style_roll = random.randint(1, 4)

    if style_roll == 1:
        acr, full_title = random.choice(ACRONYMS)
        root = random.choice(ROOT_NAMES)
        return acr, f"{acr} the {root} {full_title}"
    elif style_roll == 2:
        adj  = random.choice(ADJECTIVES)
        root = random.choice(ROOT_NAMES)
        gov  = random.choice(GOVERNMENTS["monarchy"] + GOVERNMENTS["republic"])
        return root, f"{adj} {root} {gov}"
    elif style_roll == 3:
        root     = random.choice(ROOT_NAMES)
        adj_root = root + "an" if root.endswith("e") else root + "ian"
        gov      = random.choice(GOVERNMENTS["monarchy"])
        return root, f"{adj_root} {gov}"
    else:
        root     = random.choice(ROOT_NAMES)
        adj_root = root + "an" if root.endswith("e") else root + "ian"
        gov      = random.choice(GOVERNMENTS["republic"] + GOVERNMENTS["theocracy"])
        return root, f"The {adj_root} {gov}"


def generate_custom_flag(tag: str, output_dir: str, assets_path: str = "assets") -> None:
    """Procedurally build a unique 64×64 TGA flag."""
    os.makedirs(os.path.join(output_dir, "gfx", "flags"), exist_ok=True)

    base_color      = random.choice(FLAG_PALETTE)
    secondary_color = random.choice([c for c in FLAG_PALETTE if c != base_color])
    emblem_color    = random.choice([c for c in FLAG_PALETTE if c != secondary_color])

    flag_img: Image.Image = Image.new("RGB", (64, 64), color=base_color)

    pattern_dir = os.path.join(assets_path, "patterns")
    if os.path.isdir(pattern_dir) and os.listdir(pattern_dir):
        try:
            pattern_mask = (
                Image.open(os.path.join(pattern_dir, random.choice(os.listdir(pattern_dir))))
                .convert("L").resize((64, 64))
            )
            flag_img = Image.composite(
                Image.new("RGB", (64, 64), color=secondary_color), flag_img, pattern_mask
            )
        except (OSError, ValueError) as e:
            logger.warning("Failed to apply flag pattern for tag '%s': %s", tag, e)

    emblem_dir = os.path.join(assets_path, "emblems")
    if os.path.isdir(emblem_dir) and os.listdir(emblem_dir):
        try:
            emblem_mask = (
                Image.open(os.path.join(emblem_dir, random.choice(os.listdir(emblem_dir))))
                .convert("L").resize((40, 40))
            )
            emblem_stamp = Image.new("RGB", (40, 40), color=emblem_color)
            flag_img.paste(emblem_stamp, (12, 12), mask=ImageOps.invert(emblem_mask))
        except (OSError, ValueError) as e:
            logger.warning("Failed to apply flag emblem for tag '%s': %s", tag, e)

    flag_img.save(os.path.join(output_dir, "gfx", "flags", f"{tag}.tga"), format="TGA")


def write_country_common_file(tag: str, output_dir: str) -> None:
    """Create ``common/countries/{tag}.txt``."""
    os.makedirs(os.path.join(output_dir, "common", "countries"), exist_ok=True)
    r, g, b = random.randint(30, 230), random.randint(30, 230), random.randint(30, 230)
    content = (
        f"# Country settings for {tag}\ngraphical_culture = western\n"
        f"color = {{ {r} {g} {b} }}\nhistorical_score = 100\n"
        f"tech_group = western\nai_personality = balanced\n"
    )
    with open(os.path.join(output_dir, "common", "countries", f"{tag}.txt"), "w", encoding="utf-8") as f:
        f.write(content)


def append_to_country_tags(tag: str, output_dir: str) -> None:
    """Append tag registration to ``common/country_tags/00_countries.txt``."""
    os.makedirs(os.path.join(output_dir, "common", "country_tags"), exist_ok=True)
    with open(
        os.path.join(output_dir, "common", "country_tags", "00_countries.txt"),
        "a", encoding="utf-8",
    ) as f:
        f.write(f'{tag} = "countries/{tag}.txt"\n')


def write_country_localization(tag: str, short_name: str, full_name: str, output_dir: str) -> None:
    """Write localization definitions for a country."""
    os.makedirs(os.path.join(output_dir, "localisation"), exist_ok=True)
    with open(
        os.path.join(output_dir, "localisation", "custom_countries_l_english.yml"),
        "a", encoding="utf-8-sig",
    ) as f:
        f.write(
            f"l_english:\n"
            f' {tag}:0 "{short_name}"\n'
            f' {tag}_ADJ:0 "{short_name}an"\n'
            f' {tag}_DEF:0 "{full_name}"\n'
        )


def determine_inverted_tech_group(center_y: int) -> dict[str, Any]:
    """Return tech group settings based on inverted latitude hierarchy."""
    if 1024 <= center_y < 1536:
        return {"tech_group": "chinese",        "adm": 6, "dip": 6, "mil": 6, "institutions": [1, 1, 1, 0, 0, 0, 0, 0]}
    elif 512 <= center_y < 1024:
        return {"tech_group": "muslim",          "adm": 4, "dip": 4, "mil": 4, "institutions": [1, 1, 0, 0, 0, 0, 0, 0]}
    elif center_y >= 1536:
        return {"tech_group": "north_american",  "adm": 3, "dip": 3, "mil": 3, "institutions": [1, 0, 0, 0, 0, 0, 0, 0]}
    else:
        return {"tech_group": "western",         "adm": 1, "dip": 1, "mil": 1, "institutions": [0, 0, 0, 0, 0, 0, 0, 0]}


def write_country_history_file(tag: str, center_y: int, short_name: str, output_dir: str) -> None:
    """Write ``history/countries/{tag} - {short_name}.txt`` with inverted tech."""
    os.makedirs(os.path.join(output_dir, "history", "countries"), exist_ok=True)
    tech = determine_inverted_tech_group(center_y)
    inst = tech["institutions"]
    content = (
        f"# History for {short_name} ({tag})\ngovernment = monarchy\n"
        f"technology_group = {tech['tech_group']}\n\n"
        f"technology_table = {{\n\tadm_tech = {tech['adm']}\n\tdip_tech = {tech['dip']}\n\tmil_tech = {tech['mil']}\n}}\n\n"
        f"embraced_institutions = {{\n\t{inst[0]}\n\t{inst[1]}\n\t{inst[2]}\n}}\n\n"
        f"primary_culture = cosmopolitan_french\nreligion = catholic\nmercantilism = 10\n"
    )
    with open(
        os.path.join(output_dir, "history", "countries", f"{tag} - {short_name}.txt"),
        "w", encoding="utf-8",
    ) as f:
        f.write(content)


def determine_inverted_province_religion(center_y: int, is_island: bool, development_score: int) -> str:
    """Return a religion identifier based on latitude and development."""
    if is_island or development_score >= 15:
        return "hinduism"
    elif 512 <= center_y < 1536:
        return "hinduism" if random.random() < 0.40 else "fetishist"
    elif center_y >= 1536:
        return "totemism"
    else:
        return random.choice(["catholic", "protestant", "orthodox", "sunni", "shia"])


def generate_province_history(
    province_id: int,
    province_name: str,
    terrain_type: str,
    river_count: int,
    dev_data: dict[str, int],
    center_y: int,
    is_island: bool,
    output_dir: str,
) -> None:
    """Generate and write a province history file from positional/terrain data.

    Unlike ``map_writers.write_province_history_entry`` (which takes explicit
    params), this variant calculates trade goods, dev, and religion internally.
    """
    os.makedirs(output_dir, exist_ok=True)

    development_score = dev_data.get("tax", 2) + dev_data.get("prod", 2) + dev_data.get("manpower", 2)
    province_faith = determine_inverted_province_religion(center_y, is_island, development_score)

    if terrain_type == "mountain":
        base_tax, base_production, base_manpower, trade_good = 1, 1, 1, "iron"
    elif river_count > 10:
        base_tax, base_production, base_manpower, trade_good = 4, 4, 3, "cloth"
    else:
        base_tax, base_production, base_manpower, trade_good = 2, 2, 2, "grain"

    content = (
        f"# {province_id} - {province_name}\n\n"
        f"base_tax = {base_tax}\nbase_production = {base_production}\nbase_manpower = {base_manpower}\n\n"
        f"trade_goods = {trade_good}\nculture = cosmopolitan_french\nreligion = {province_faith}\n"
        f'capital = "{province_name}"\n\n'
        f"1444.11.11 = {{\n    owner = FRA\n    controller = FRA\n    add_core = FRA\n    discovered_by = western\n}}\n"
    )

    with open(os.path.join(output_dir, f"{province_id} - {province_name}.txt"), "w", encoding="utf-8") as f:
        f.write(content)


def generate_procedural_diplomacy(output_dir: str, country_telemetry: dict[str, dict[str, Any]]) -> None:
    """Generate procedural alliances, rivalries, and CBs between nearby nations."""
    os.makedirs(os.path.join(output_dir, "history", "diplomacy"), exist_ok=True)

    diplomacy_script = "# Procedural Diplomatic Matrix\n\n"
    tags = list(country_telemetry.keys())
    processed_pairs: set[tuple[str, str]] = set()

    for i, tag_a in enumerate(tags):
        pos_a = country_telemetry[tag_a]
        for tag_b in tags[i + 1:]:
            pos_b = country_telemetry[tag_b]
            pair_key = (min(tag_a, tag_b), max(tag_a, tag_b))
            if pair_key in processed_pairs:
                continue

            distance = np.hypot(pos_a["x"] - pos_b["x"], pos_a["y"] - pos_b["y"])

            if distance < 450:
                roll = random.random()
                if roll < 0.45:
                    diplomacy_script += f"rival = {{\n\tfirst = {tag_a}\n\tsecond = {tag_b}\n\tstart_date = 1444.11.11\n}}\n\n"
                elif roll < 0.85:
                    diplomacy_script += f"alliance = {{\n\tfirst = {tag_a}\n\tsecond = {tag_b}\n\tstart_date = 1444.11.11\n}}\n\n"

            if pos_a.get("tech") != "western" and pos_b.get("tech") == "western" and distance < 600:
                diplomacy_script += (
                    f"casus_belli = {{\n\ttype = cb_feudal_imperialism\n\tattacker = {tag_a}\n"
                    f"\tdefender = {tag_b}\n\tstart_date = 1444.11.11\n\tend_date = 1821.1.1\n}}\n\n"
                )

            processed_pairs.add(pair_key)

    with open(
        os.path.join(output_dir, "history", "diplomacy", "procedural_alliances.txt"),
        "w", encoding="utf-8",
    ) as f:
        f.write(diplomacy_script)
    print("✓ Procedural diplomacy generated")


def generate_country_missions(
    tag: str,
    country_data: dict[str, str],
    province_telemetry: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build a list of randomised mission dicts for a country.

    MISSION_ARCHETYPES is imported from constants (fixes the original
    NameError where it was defined *after* this function).
    """
    missions: list[dict[str, Any]] = []
    archetypes = random.choices(
        MISSION_ARCHETYPES,
        weights=[float(a["weight"]) for a in MISSION_ARCHETYPES],  # type: ignore[arg-type]
        k=6,
    )

    for idx, arch in enumerate(archetypes, start=1):
        mission_id = f"{tag}_mission_{arch['id']}_{idx}"
        title      = f"{country_data['culture']} {str(arch['theme']).capitalize()}"
        desc       = f"Strengthen our {arch['theme']} across {country_data['region']}."
        missions.append({"id": mission_id, "title": title, "desc": desc, "theme": arch["theme"], "effects": arch["effects"]})

    return missions


def generate_dual_empire_history_entries(
    custom_country_tags: list[str],
    center_y_dict: dict[str, int],
) -> dict[str, str]:
    """Elect nations to the Celestial Directorate based on geography."""
    advanced_tags = [tag for tag, y in center_y_dict.items() if 512 <= y < 1536]
    if len(advanced_tags) < 10:
        return {}

    director_emperor    = advanced_tags[0]
    celestial_electors  = advanced_tags[1:8]
    directorate_members = advanced_tags[8:25] if len(advanced_tags) > 25 else advanced_tags[8:]

    assignments: dict[str, str] = {}
    for tag in advanced_tags:
        if tag == director_emperor:
            assignments[tag] = "emperor = celestial_directorate"
        elif tag in celestial_electors:
            assignments[tag] = "elector = celestial_directorate"
        elif tag in directorate_members:
            assignments[tag] = "member = celestial_directorate"
    return assignments


def generate_second_hre_mechanics_file(output_dir: str) -> None:
    """Write the Celestial Directorate imperial reform parameters."""
    os.makedirs(os.path.join(output_dir, "common", "imperial_reforms"), exist_ok=True)
    mechanics_script = (
        "# Second Imperial Group System - The Celestial Directorate\n"
        "celestial_directorate = {\n    style = hre\n\n"
        "    member_modifier = {\n        technology_cost = -0.05\n        global_trade_power = 0.10\n    }\n\n"
        "    elector_modifier = {\n        diplomatic_republic_latent = 1\n        legitimacy = 1\n    }\n\n"
        "    emperor_modifier = {\n        diplomatic_upkeep = 2\n        imperial_authority = 0.10\n    }\n\n"
        "    reform_celestial_call = {\n        imperial_authority_cost = 50\n        effect = {\n            production_efficiency = 0.05\n        }\n    }\n\n"
        "    reform_celestial_unification = {\n        imperial_authority_cost = 50\n        effect = {\n            vassal_income = 0.25\n        }\n    }\n}\n"
    )
    with open(
        os.path.join(output_dir, "common", "imperial_reforms", "celestial_directorate.txt"),
        "w", encoding="utf-8",
    ) as f:
        f.write(mechanics_script)
