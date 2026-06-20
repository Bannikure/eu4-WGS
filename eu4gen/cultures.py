"""Module I – Culture Group & Culture Generator."""

from __future__ import annotations

import random
from typing import Any

from .constants import CULTURE_GROUP_TEMPLATES, CULTURE_ROOT_SYLLABLES


def generate_culture_groups(num_groups: int = 6) -> list[dict[str, Any]]:
    """Procedurally generate mixed African–Asian culture groups."""
    templates = random.choices(
        CULTURE_GROUP_TEMPLATES,
        weights=[float(t["weight"]) for t in CULTURE_GROUP_TEMPLATES],  # type: ignore[arg-type]
        k=num_groups,
    )
    groups: list[dict[str, Any]] = []
    for idx, tpl in enumerate(templates, start=1):
        root = random.choice(CULTURE_ROOT_SYLLABLES)
        groups.append({
            "id":       f"{tpl['id']}_{idx}",
            "name":     root + "ic",
            "regions":  list(tpl["regions"]),         # type: ignore[arg-type]
            "patterns": list(tpl["name_patterns"]),   # type: ignore[arg-type]
        })
    return groups


def generate_cultures_for_group(group: dict[str, Any], num_cultures: int = 4) -> list[dict[str, Any]]:
    """Generate individual culture entries inside a given culture group."""
    cultures: list[dict[str, Any]] = []
    for i in range(num_cultures):
        root    = random.choice(CULTURE_ROOT_SYLLABLES)
        pattern: str = random.choice(group["patterns"])
        cultures.append({
            "id":    f"{group['id']}_c{i + 1}",
            "name":  pattern.format(root=root),
            "group": group["id"],
        })
    return cultures


def assign_cultures_to_provinces(
    province_telemetry: list[dict[str, Any]],
    culture_groups: list[dict[str, Any]],
    cultures: list[dict[str, Any]],
) -> dict[int, str]:
    """Assign a culture to each province based on latitude and region bias."""
    province_cultures: dict[int, str] = {}
    for p in province_telemetry:
        p_id, y = int(p["id"]), int(p["center_y"])

        if 1024 <= y < 1536:
            region = "africa"
        elif 512 <= y < 1024:
            region = "asia"
        elif y >= 1536:
            region = "islands"
        else:
            region = "frontier"

        viable_groups = [g for g in culture_groups if region in g["regions"]] or culture_groups
        group = random.choice(viable_groups)
        group_cultures = [c for c in cultures if c["group"] == group["id"]] or cultures
        province_cultures[p_id] = str(random.choice(group_cultures)["name"])

    return province_cultures
