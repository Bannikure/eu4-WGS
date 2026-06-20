"""Module F – Economy & Trade Systems."""

from __future__ import annotations

import os
import random
from typing import Any

from .constants import RICH_COMMODITIES, BARREN_COMMODITIES, TRADE_COMPANY_REGIONS


def generate_trade_goods_files(output_dir: str) -> None:
    """Write trade good definitions and price tables."""
    os.makedirs(os.path.join(output_dir, "common", "trade_goods"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "common", "prices"),      exist_ok=True)

    tg_script = "# Procedural Trade Goods Matrix\n"
    price_script = "# Procedural Price Layout\n"

    for name, data in {**RICH_COMMODITIES, **BARREN_COMMODITIES}.items():
        r1, r2, r3 = round(random.random(), 2), round(random.random(), 2), round(random.random(), 2)
        tg_script += (
            f"{name} = {{\n    color = {{ {r1} {r2} {r3} }}\n"
            f"    modifier = {{ {data['global_buff']} }}\n"
            f"    province = {{ {data['prov_buff']} }}\n"
            f"    uncolonized_weight = 0\n}}\n\n"
        )
        price_script += (
            f"{name} = {{\n    base_price = {data['base_price']}\n"
            f"    min_price = 0.5\n    max_price = 15.0\n}}\n\n"
        )

    with open(os.path.join(output_dir, "common", "trade_goods", "00_trade_goods.txt"), "w", encoding="utf-8") as f:
        f.write(tg_script)
    with open(os.path.join(output_dir, "common", "prices", "00_prices.txt"), "w", encoding="utf-8") as f:
        f.write(price_script)
    print("✓ Trade goods and prices generated")


def generate_inverted_trade_nodes(
    province_telemetry: list[dict[str, Any]],
    island_province_ids: list[int],
    output_dir: str,
) -> list[dict[str, Any]]:
    """Group provinces into trade nodes routing wealth toward Africa/Asia/Islands."""
    node_buckets: dict[str, dict[str, Any]] = {
        "european_rim":          {"provinces": [], "outbound": ["middle_east_hub"]},
        "middle_east_hub":       {"provinces": [], "outbound": ["african_wealth_hub", "asian_wealth_hub"]},
        "african_wealth_hub":    {"provinces": [], "outbound": ["island_treasure_vault"]},
        "asian_wealth_hub":      {"provinces": [], "outbound": ["island_treasure_vault"]},
        "island_treasure_vault": {"provinces": [], "outbound": []},
    }
    island_set = set(island_province_ids)

    for p in province_telemetry:
        p_id, y = int(p["id"]), int(p["center_y"])
        if p_id in island_set:
            node_buckets["island_treasure_vault"]["provinces"].append(p_id)
        elif y < 512:
            node_buckets["european_rim"]["provinces"].append(p_id)
        elif y < 1024:
            node_buckets["middle_east_hub"]["provinces"].append(p_id)
        elif y < 1300:
            node_buckets["african_wealth_hub"]["provinces"].append(p_id)
        else:
            node_buckets["asian_wealth_hub"]["provinces"].append(p_id)

    os.makedirs(os.path.join(output_dir, "common", "tradenodes"), exist_ok=True)
    node_list: list[dict[str, Any]] = []

    with open(os.path.join(output_dir, "common", "tradenodes", "00_tradenodes.txt"), "w", encoding="utf-8") as f:
        for node_name, data in node_buckets.items():
            prov_list   = " ".join(map(str, data["provinces"][:200]))
            location_id = data["provinces"][0] if data["provinces"] else 1
            end_flag    = "yes" if not data["outbound"] else "no"
            f.write(f"{node_name} = {{\n    location = {location_id}\n    provinces = {{ {prov_list} }}\n    end = {end_flag}\n")
            for target in data["outbound"]:
                f.write(f'    outgoing = {{\n        name = "{target}"\n        path = {{ {location_id} }}\n    }}\n')
            f.write("}\n\n")
            node_list.append({"id": node_name, "provinces": list(data["provinces"]), "outbound": list(data["outbound"]), "modifiers": []})

    print("✓ Trade nodes generated")
    return node_list


def assign_trade_companies(province_telemetry: list[dict[str, Any]]) -> dict[str, list[int]]:
    """Map trade company IDs to their province lists based on latitude."""
    company_map: dict[str, list[int]] = {tc["id"]: [] for tc in TRADE_COMPANY_REGIONS}

    for p in province_telemetry:
        y = int(p["center_y"])
        if 1024 <= y < 1536:
            region: str | None = "africa"
        elif 512 <= y < 1024:
            region = "asia"
        elif y >= 1536:
            region = "islands"
        else:
            region = None

        if region is None:
            continue
        for tc in TRADE_COMPANY_REGIONS:
            if tc["region"] == region:
                company_map[tc["id"]].append(int(p["id"]))

    return company_map


def write_trade_company_files(company_map: dict[str, list[int]], output_dir: str) -> None:
    """Write individual trade company definition files."""
    os.makedirs(os.path.join(output_dir, "common", "trade_companies"), exist_ok=True)
    for tc in TRADE_COMPANY_REGIONS:
        provinces_str = " ".join(map(str, company_map.get(tc["id"], [])))
        content = (
            f"{tc['id']} = {{\n    name = \"{tc['name']}\"\n"
            f"    provinces = {{ {provinces_str} }}\n"
            f"    bonus = {{\n        global_trade_power = 0.15\n        trade_efficiency = 0.10\n        production_efficiency = 0.10\n    }}\n}}\n"
        )
        with open(os.path.join(output_dir, "common", "trade_companies", f"{tc['id']}.txt"), "w", encoding="utf-8") as f:
            f.write(content)
    print("✓ Trade company files generated")


def apply_trade_company_bonuses_to_nodes(
    trade_nodes: list[dict[str, Any]],
    company_map: dict[str, list[int]],
) -> list[dict[str, Any]]:
    """Append trade-power bonuses to nodes that overlap with trade companies."""
    company_prov_set: set[int] = set()
    for provs in company_map.values():
        company_prov_set.update(provs)

    for node in trade_nodes:
        if any(p in company_prov_set for p in node["provinces"]):
            node.setdefault("modifiers", [])
            node["modifiers"].append("global_trade_power = 0.10")
            node["modifiers"].append("trade_value_modifier = 0.10")

    return trade_nodes
