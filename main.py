#!/usr/bin/env python3
"""
EU4 World Generator Studio V8 — Main Entry Point
===================================================
Afro-Asian Ascendancy Total Conversion World Generator

Usage:
    python main.py                    # Launch GUI (if display available)
    python main.py --headless         # Run headless generation pipeline
    python main.py --headless --seed 1234 --provinces 500
    python main.py --test             # Run quick test with small map
"""

import os
import sys
import argparse
import time
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(
        description="EU4 World Generator Studio V8 — Afro-Asian Ascendancy"
    )
    parser.add_argument("--headless", action="store_true",
                        help="Run generation without GUI")
    parser.add_argument("--test", action="store_true",
                        help="Quick test with small map (512x256)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--mod-name", type=str, default="AfroAsianAscendancy",
                        help="Mod name (default: AfroAsianAscendancy)")
    parser.add_argument("--provinces", type=int, default=1500,
                        help="Target province count (default: 1500)")
    parser.add_argument("--land-pct", type=int, default=30,
                        help="Land percentage 10-60 (default: 30)")
    parser.add_argument("--map-style", type=str, default="continents",
                        choices=["pangea", "continents", "archipelago", "continents_islands"],
                        help="Map style (default: continents)")
    parser.add_argument("--map-width", type=int, default=5632,
                        help="Map width in pixels (default: 5632)")
    parser.add_argument("--map-height", type=int, default=2048,
                        help="Map height in pixels (default: 2048)")
    parser.add_argument("--output", type=str, default="./mod_output",
                        help="Output directory (default: ./mod_output)")
    parser.add_argument("--octaves", type=int, default=None,
                        help="Noise octaves; uses MapConfig defaults if omitted")
    parser.add_argument("--no-tectonic", action="store_true",
                        help="Disable tectonic plate simulation")
    parser.add_argument("--no-erosion", action="store_true",
                        help="Disable hydraulic erosion")
    parser.add_argument("--no-craters", action="store_true",
                        help="Disable impact craters")
    return parser.parse_args()


def run_test():
    """Quick test with small map to verify all modules work."""
    print("\n" + "=" * 60)
    print("  EU4 WGS V8 — Quick Module Integration Test")
    print("=" * 60 + "\n")

    from eu4_wgs_v8.engine import (
        MapConfig, MapGenerationEngine, ProvinceGenerator,
        RiverGenerator, TerrainClassifier, NormalMapGenerator
    )
    from eu4_wgs_v8.analytics import HeightmapAnalyzer, DashboardGenerator
    from eu4_wgs_v8.content import (
        CountryGenerator, CountryData, CelestialDirectorate,
        TradeGenerator, DiplomacyGenerator, ReligionGenerator,
        CultureGenerator, FlagGenerator, IdeaGenerator
    )
    from eu4_wgs_v8.export import MasterExportOrchestrator

    test_dir = "./test_output/test_mod"

    # ── Test 1: MapConfig ──
    print("[TEST 1] MapConfig...")
    config = MapConfig(width=512, height=256, seed=42, land_percentage=30)
    assert config.width == 512 and config.height == 256
    print("  ✓ MapConfig OK")

    # ── Test 2: Heightmap Generation ──
    print("\n[TEST 2] Heightmap Generation...")
    t0 = time.time()
    engine = MapGenerationEngine(config)
    heightmap, land_mask = engine.generate_complete_heightmap(
        apply_tectonic=True, apply_erosion=True, apply_craters=True, num_craters=1
    )
    land_pct = land_mask.sum() / land_mask.size * 100
    land_pixel_pct = (heightmap > 0).sum() / heightmap.size * 100
    print(f"  ✓ Heightmap: {heightmap.shape}, land_mask={land_pct:.1f}%, "
          f"land_pixels={land_pixel_pct:.1f}%, "
          f"range=[{heightmap.min():.1f}, {heightmap.max():.1f}] in {time.time()-t0:.1f}s")

    # ── Test 3: Province Generation ──
    print("\n[TEST 3] Province Generation...")
    t0 = time.time()
    prov_gen = ProvinceGenerator(width=512, height=256)
    province_map, province_info_list, _micro = prov_gen.generate_provinces(
        heightmap, land_mask, requested_provinces=100
    )
    print(f"  ✓ Provinces: {len(province_info_list)} in {time.time()-t0:.1f}s")

    # ── Test 4: Rivers ──
    print("\n[TEST 4] River Generation...")
    t0 = time.time()
    river_gen = RiverGenerator(width=512, height=256)
    rivers, _river_counts = river_gen.generate_rivers(heightmap, land_mask)
    print(f"  ✓ Rivers: {rivers.shape} in {time.time()-t0:.1f}s")

    # ── Test 5: Terrain Classification ──
    print("\n[TEST 5] Terrain Classification...")
    t0 = time.time()
    terrain_cls = TerrainClassifier(width=512, height=256)
    terrain_bmp = terrain_cls.generate_terrain_bmp(heightmap, land_mask)
    print(f"  ✓ Terrain: {terrain_bmp.shape} in {time.time()-t0:.1f}s")

    # ── Test 6: Country Generation ──
    print("\n[TEST 6] Country Generation...")
    t0 = time.time()
    land_provs = [p for p in province_info_list if not p.is_sea and not p.is_wasteland]
    countries = []
    for i in range(min(10, len(land_provs))):
        country = CountryGenerator.generate_country(land_provs[i], map_height=256)
        countries.append(country)
    print(f"  ✓ Countries: {len(countries)} generated in {time.time()-t0:.1f}s")
    if countries:
        c = countries[0]
        print(f"    Sample: {c.tag} — {c.short_name} ({c.government}, {c.tech_group}, {c.religion})")

    # ── Test 7: Celestial Directorate ──
    print("\n[TEST 7] Celestial Directorate...")
    reforms_path = CelestialDirectorate.generate_imperial_reforms(test_dir)
    country_dict_for_dir = {c.tag: c for c in countries} if countries else {}
    roles = CelestialDirectorate.assign_directorate_roles(country_dict_for_dir)
    emperor_tag = roles.get("emperor", "N/A")
    print(f"  ✓ Directorate: reforms written to {reforms_path}, emperor={emperor_tag}")

    # ── Test 8: Religion Generator ──
    print("\n[TEST 8] Religion Generator...")
    rel_path = ReligionGenerator.generate_religion_file(test_dir)
    with open(rel_path, 'r') as f:
        rel_content = f.read()
    assert "hindu" in rel_content.lower()
    print(f"  ✓ Religion file: {len(rel_content)} chars, contains Hindu system")

    # ── Test 9: Culture Generator ──
    print("\n[TEST 9] Culture Generator...")
    cult_path = CultureGenerator.generate_cultures_file(test_dir)
    with open(cult_path, 'r') as f:
        cult_content = f.read()
    assert "african" in cult_content.lower()
    print(f"  ✓ Culture file: {len(cult_content)} chars")

    # ── Test 10: Flag Generator ──
    print("\n[TEST 10] Flag Generation...")
    flag_path = FlagGenerator.generate_flag("AK01", is_advanced=True, output_dir=test_dir)
    print(f"  ✓ Flag generated: {flag_path}")

    # ── Test 11: National Ideas ──
    print("\n[TEST 11] National Ideas...")
    if land_provs:
        ideas = IdeaGenerator.generate_national_ideas("AK01", land_provs[0].center_y)
        print(f"  ✓ Ideas: {len(ideas)} chars")
    else:
        print("  ⚠ No land provinces for idea test")

    # ── Test 12: Analytics ──
    print("\n[TEST 12] Analytics...")
    t0 = time.time()
    analyzer = HeightmapAnalyzer(map_height=256)
    country_dict = {c.tag: c for c in countries}
    analytics = analyzer.generate_full_analytics(heightmap, land_mask, province_info_list, country_dict)
    print(f"  ✓ Analytics computed in {time.time()-t0:.1f}s")

    # ── Test 13: Dashboard ──
    print("\n[TEST 13] Dashboard Generation...")
    t0 = time.time()
    dash_gen = DashboardGenerator(output_dir="./test_output/dashboard")
    elev_data = dash_gen.preparer.prepare_elevation_histogram(heightmap)
    dash_path = dash_gen.generate_dashboard(
        world_name="TestWorld", seed=42,
        map_width=512, map_height=256,
        religion_distribution={"Hindu": 40, "Pagan": 25, "Sunni": 15, "Catholic": 10, "Other": 10},
        tech_distribution={"Chinese": 30, "Indian": 25, "Western": 20, "Nomadic": 15, "Subsaharan": 10},
        terrain_distribution={"grassland": 30, "forest": 25, "ocean": 20, "mountain": 15, "desert": 10},
        continent_stats={
            "Africa": {"avg_development": 25, "avg_tax": 8, "avg_production": 10, "avg_manpower": 7},
            "Asia": {"avg_development": 28, "avg_tax": 9, "avg_production": 11, "avg_manpower": 8},
            "Europe": {"avg_development": 3, "avg_tax": 1, "avg_production": 1, "avg_manpower": 1},
        },
        elevation_data=elev_data,
    )
    print(f"  ✓ Dashboard: {dash_path} in {time.time()-t0:.1f}s")

    # ── Test 14: Mod Export ──
    print("\n[TEST 14] Mod Export...")
    t0 = time.time()
    orchestrator = MasterExportOrchestrator(output_base_dir="./test_output", map_height=256)
    climate_zones = terrain_cls.classify_climate_zones(province_info_list)
    country_dict_for_export = {c.tag: c for c in countries}
    result = orchestrator.export_complete_mod(
        mod_name="TestMod",
        heightmap=heightmap,
        land_mask=land_mask,
        provinces_bmp=province_map,
        province_infos=province_info_list,
        countries=country_dict_for_export,
        climate_zones=climate_zones,
        terrain_bmp=terrain_bmp,
        rivers_bmp=rivers,
    )
    print(f"  ✓ Export: {len(result)} files in {time.time()-t0:.1f}s")

    # ── Summary ──
    print(f"\n{'='*60}")
    print(f"  ✅ ALL 14 TESTS PASSED")
    print(f"  Dashboard: {dash_path}")
    print(f"  Mod: ./test_output/TestMod")
    print(f"{'='*60}\n")

    return dash_path


def run_headless_pipeline(args):
    """Run the full headless generation pipeline."""
    import generate_world
    from eu4_wgs_v8.export import MasterExportOrchestrator

    result = generate_world.generate_world(
        mod_name=args.mod_name,
        seed=args.seed,
        width=args.map_width,
        height=args.map_height,
        land_pct=args.land_pct,
        province_count=args.provinces,
        output_dir=args.output,
        map_style=args.map_style,
        enable_tectonic=not args.no_tectonic,
        enable_erosion=not args.no_erosion,
        enable_craters=not args.no_craters,
        num_craters=5,
        octaves=args.octaves,
    )

    orchestrator = MasterExportOrchestrator(
        output_base_dir=args.output, map_height=args.map_height
    )
    export_result = orchestrator.export_complete_mod(
        mod_name=args.mod_name,
        heightmap=result["heightmap"],
        land_mask=result["land_mask"],
        provinces_bmp=result["provinces_bmp"],
        province_infos=result["province_infos"],
        countries={c.tag: c for c in result["countries"]},
        climate_zones=result["climate_zones"],
        terrain_bmp=result["terrain_bmp"],
        rivers_bmp=result["rivers_bmp"],
    )

    return {
        "dashboard_path": result["dashboard_path"],
        "export_result": export_result,
    }


def main():
    args = parse_args()

    if args.test:
        dash_path = run_test()
        return

    if args.headless:
        result = run_headless_pipeline(args)
        print(f"\n[DONE] Dashboard: {result.get('dashboard_path', 'N/A')}")
        export_result = result.get("export_result", {})
        print(f"[DONE] Mod: {args.output}/{args.mod_name} ({len(export_result)} files)")
        return

    # Try GUI
    try:
        from eu4_wgs_v8.gui import WorldGeneratorStudio
        app = WorldGeneratorStudio()
        app.run()
    except Exception as e:
        print(f"[WGS] GUI launch failed ({e}), falling back to headless mode...")
        run_headless_pipeline(args)


if __name__ == "__main__":
    main()
