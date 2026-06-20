"""Module E – Religious & Cultural Systems."""

from __future__ import annotations

import os
import random

from .constants import ADVANCED_MODIFIERS, PRIMITIVE_MODIFIERS


def generate_religion_database(output_dir: str) -> None:
    """Write the inverted religion system to ``common/religions/00_religion.txt``."""
    os.makedirs(os.path.join(output_dir, "common", "religions"), exist_ok=True)
    religion_script = (
        "# Inverted Religion Database\n\n"
        "eastern = {\n    hinduism = {\n        color = { 0.8 0.5 0.0 }\n        icon = 8\n"
        "        global_trade_goods_size_modifier = 0.20\n        technology_cost = -0.15\n"
        "        global_missionary_strength = 0.05\n        tolerance_own = 4\n"
        "        center_of_reformation = yes\n        female_defender_of_faith = yes\n"
        "        defender_of_faith = yes\n    }\n}\n\n"
        "pagan = {\n"
        "    fetishist = {\n        color = { 0.6 0.4 0.2 }\n        icon = 9\n"
        "        global_manpower_modifier = 0.20\n        core_creation_cost = -0.15\n"
        "        tolerance_own = 3\n    }\n"
        "    totemism = {\n        color = { 0.4 0.6 0.4 }\n        icon = 10\n"
        "        production_efficiency = 0.15\n        land_morale = 0.10\n    }\n}\n\n"
        "christian = {\n"
        "    catholic = {\n        color = { 0.8 0.8 0.8 }\n        icon = 1\n"
        "        global_corruption = 0.05\n        stability_cost_modifier = 0.50\n"
        "        technology_cost = 0.20\n        tax_income = -20\n        curia = yes\n        papacy = yes\n    }\n"
        "    protestant = {\n        color = { 0.3 0.3 0.7 }\n        icon = 2\n"
        "        global_corruption = 0.04\n        idea_cost = 0.25\n        inflation_action_cost = 0.50\n    }\n}\n\n"
        "muslim = {\n    sunni = {\n        color = { 0.0 0.6 0.0 }\n        icon = 3\n"
        "        global_corruption = 0.05\n        all_power_cost = 0.15\n        global_unrest = 3\n    }\n}\n"
    )
    with open(os.path.join(output_dir, "common", "religions", "00_religion.txt"), "w", encoding="utf-8") as f:
        f.write(religion_script)
    print("✓ Religion database generated")


def generate_national_idea_tree(tag: str, center_y: int) -> str:
    """Return a randomised national idea tree script block for *tag*."""
    is_advanced = 512 <= center_y < 1536
    pool = list(ADVANCED_MODIFIERS if is_advanced else PRIMITIVE_MODIFIERS)
    while len(pool) < 10:
        pool = pool + pool
    chosen = random.sample(pool, 10)

    return (
        f"\n{tag}_ideas = {{\n"
        f"    start = {{\n        {chosen[0]}\n        {chosen[1]}\n    }}\n"
        f"    bonus = {{\n        {chosen[2]}\n    }}\n"
        f"    trigger = {{\n        tag = {tag}\n    }}\n"
        f"    free = yes\n\n"
        f"    {tag}_idea_1 = {{ {chosen[3]} }}\n"
        f"    {tag}_idea_2 = {{ {chosen[4]} }}\n"
        f"    {tag}_idea_3 = {{ {chosen[5]} }}\n"
        f"    {tag}_idea_4 = {{ {chosen[6]} }}\n"
        f"    {tag}_idea_5 = {{ {chosen[7]} }}\n"
        f"    {tag}_idea_6 = {{ {chosen[8]} }}\n"
        f"    {tag}_idea_7 = {{ {chosen[9]} }}\n"
        f"}}\n"
    )
