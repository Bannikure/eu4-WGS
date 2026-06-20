"""Module G – Leader & Ruler Generators."""

from __future__ import annotations

import os
import random

from .constants import SKILL_LEVELS, SKILL_WEIGHTS, LEADER_MONIKERS

_FIRST_NAMES = ["Alexander", "Louis", "Charles", "Victoria", "Elizabeth", "Malik", "Kaelen", "Bruce"]


def generate_random_monarch(country_short_name: str, center_y: int) -> str:
    """Assemble the 1444.11.11 starting monarch block."""
    first_name = random.choice(_FIRST_NAMES)
    moniker    = random.choices(LEADER_MONIKERS, weights=[0.1, 0.1, 0.1, 0.05, 0.1, 0.05, 0.5])[0]
    full_name  = f"{first_name} {moniker}".strip()

    is_advanced = 512 <= center_y < 1536
    if is_advanced:
        adm = random.choices([3, 4, 5, 6], weights=[0.3, 0.4, 0.2, 0.1])[0]
        dip = random.choices([3, 4, 5, 6], weights=[0.3, 0.4, 0.2, 0.1])[0]
        mil = random.choices([3, 4, 5, 6], weights=[0.3, 0.4, 0.2, 0.1])[0]
    else:
        adm = random.choices(SKILL_LEVELS, weights=SKILL_WEIGHTS)[0]
        dip = random.choices(SKILL_LEVELS, weights=SKILL_WEIGHTS)[0]
        mil = random.choices(SKILL_LEVELS, weights=SKILL_WEIGHTS)[0]

    return (
        f"1444.11.11 = {{\n    monarch = {{\n"
        f'        name = "{full_name}"\n'
        f"        adm = {adm}\n        dip = {dip}\n        mil = {mil}\n"
        f"        age = {random.randint(18, 52)}\n        regent = no\n    }}\n}}\n"
    )


def export_complete_country_history(tag: str, center_y: int, short_name: str, tech_group_name: str, output_dir: str) -> None:
    """Write a complete ``history/countries/{tag} - {short_name}.txt`` file."""
    os.makedirs(os.path.join(output_dir, "history", "countries"), exist_ok=True)
    ruler_script = generate_random_monarch(short_name, center_y)
    content = f"# History for {tag}\ngovernment = monarchy\ntechnology_group = {tech_group_name}\n\n{ruler_script}\n"
    with open(os.path.join(output_dir, "history", "countries", f"{tag} - {short_name}.txt"), "w", encoding="utf-8") as f:
        f.write(content)
