#!/usr/bin/env python3
"""Full world generation pipeline with dashboard and preview image generation."""
import os
import time
import json
import numpy as np
from PIL import Image


from eu4_wgs_v8.engine.map_generation import (
    MapConfig, MapGenerationEngine, ProvinceGenerator,
    RiverGenerator, TerrainClassifier, NormalMapGenerator
)
from eu4_wgs_v8.content.world_content import (
    CountryGenerator, CelestialDirectorate, ReligionGenerator,
    CultureGenerator, FlagGenerator, IdeaGenerator
)
from eu4_wgs_v8.analytics.heightmap_analyzer import HeightmapAnalyzer
from eu4_wgs_v8.analytics.dashboard import DashboardGenerator, DashboardDataPreparer


def generate_world(
    mod_name="AfroAsianAscendancy",
    seed=42,
    width=2048,
    height=1024,
    land_pct=30,
    province_count=1500,
    output_dir="./world_output",
    map_style="continents_islands",
    enable_tectonic=True,
    enable_erosion=True,
    enable_craters=True,
    num_craters=5,
    octaves=None,
):
    """Generate a complete world with all data and visualizations."""
    os.makedirs(output_dir, exist_ok=True)
    timings = {}

    # ── Phase 1: Heightmap ──
    print("[1/7] Generating heightmap...")
    t0 = time.time()
    config_kwargs = dict(
        width=width, height=height, seed=seed,
        land_percentage=land_pct,
        layout_style=map_style
    )
    if octaves is not None:
        config_kwargs["continent_octaves"] = octaves
        config_kwargs["detail_octaves"] = octaves
    config = MapConfig(**config_kwargs)
    engine = MapGenerationEngine(config)
    heightmap, land_mask = engine.generate_complete_heightmap(
        apply_tectonic=enable_tectonic,
        apply_erosion=enable_erosion,
        apply_craters=enable_craters,
        num_craters=num_craters,
    )
    timings["heightmap"] = time.time() - t0
    land_pct_actual = land_mask.sum() / land_mask.size * 100
    print(f"  Done in {timings['heightmap']:.1f}s — land={land_pct_actual:.1f}%, range=[{heightmap.min()}, {heightmap.max()}]")

    # ── Phase 2: Provinces ──
    print("[2/7] Generating provinces...")
    t0 = time.time()
    prov_gen = ProvinceGenerator(width=width, height=height)
    provinces_bmp, province_infos, is_micro = prov_gen.generate_provinces(
        heightmap, land_mask, requested_provinces=province_count
    )
    timings["provinces"] = time.time() - t0
    land_provs = [p for p in province_infos if not p.is_sea and not p.is_wasteland]
    sea_provs = [p for p in province_infos if p.is_sea]
    print(f"  Done in {timings['provinces']:.1f}s — {len(province_infos)} provinces ({len(land_provs)} land, {len(sea_provs)} sea)")

    # ── Phase 3: Rivers & Terrain ──
    print("[3/7] Generating rivers and terrain...")
    t0 = time.time()
    river_gen = RiverGenerator(width=width, height=height)
    rivers_bmp, river_counts = river_gen.generate_rivers(heightmap, land_mask)
    terrain_cls = TerrainClassifier(width=width, height=height)
    terrain_bmp = terrain_cls.generate_terrain_bmp(heightmap, land_mask)
    climate_zones = terrain_cls.classify_climate_zones(province_infos)
    timings["rivers_terrain"] = time.time() - t0
    print(f"  Done in {timings['rivers_terrain']:.1f}s")

    # ── Phase 4: Countries ──
    print("[4/7] Generating countries with inverted dynamics...")
    t0 = time.time()
    countries = []
    for prov in land_provs:
        country = CountryGenerator.generate_country(prov, map_height=height)
        countries.append(country)
    timings["countries"] = time.time() - t0

    # Compute continent/religion/tech stats
    continent_stats = {}
    religion_dist = {}
    tech_dist = {}
    terrain_dist = {}
    for c in countries:
        # Continent stats
        cont = c.continent or "unknown"
        if cont not in continent_stats:
            continent_stats[cont] = {"count": 0, "total_dev": 0, "advanced": 0}
        continent_stats[cont]["count"] += 1
        dev = c.adm + c.dip + c.mil
        continent_stats[cont]["total_dev"] += dev
        if c.is_advanced:
            continent_stats[cont]["advanced"] += 1

        # Religion distribution
        rel = c.religion or "unknown"
        religion_dist[rel] = religion_dist.get(rel, 0) + 1

        # Tech distribution
        tech = c.tech_group or "unknown"
        tech_dist[tech] = tech_dist.get(tech, 0) + 1

    # Compute avg development per continent
    for cont in continent_stats:
        cs = continent_stats[cont]
        count = cs["count"]
        cs["avg_development"] = round(cs["total_dev"] / count, 1) if count > 0 else 0
        cs["avg_tax"] = round(cs["total_dev"] / count / 3, 1) if count > 0 else 0
        cs["avg_production"] = round(cs["total_dev"] / count / 3, 1) if count > 0 else 0
        cs["avg_manpower"] = round(cs["total_dev"] / count / 3, 1) if count > 0 else 0

    # Terrain distribution from provinces
    for p in province_infos:
        t = p.terrain_type
        terrain_dist[t] = terrain_dist.get(t, 0) + 1

    print(f"  Done in {timings['countries']:.1f}s — {len(countries)} countries")
    print(f"  Religions: {religion_dist}")
    print(f"  Tech groups: {tech_dist}")
    print(f"  Continents: {list(continent_stats.keys())}")

    # ── Phase 5: Content ──
    print("[5/7] Generating religion, culture, Celestial Directorate...")
    t0 = time.time()
    content_dir = os.path.join(output_dir, mod_name.lower().replace(" ", "_"))
    os.makedirs(content_dir, exist_ok=True)

    rel_path = ReligionGenerator.generate_religion_file(content_dir)
    cult_path = CultureGenerator.generate_cultures_file(content_dir)

    country_dict = {c.tag: c for c in countries}
    reforms_path = CelestialDirectorate.generate_imperial_reforms(content_dir)
    roles = CelestialDirectorate.assign_directorate_roles(country_dict)
    timings["content"] = time.time() - t0
    print(f"  Done in {timings['content']:.1f}s — Emperor: {roles.get('emperor', 'N/A')}")

    # ── Phase 6: Analytics ──
    print("[6/7] Computing analytics...")
    t0 = time.time()
    analyzer = HeightmapAnalyzer(map_height=height)
    analytics = analyzer.generate_full_analytics(heightmap, land_mask, province_infos, country_dict)
    timings["analytics"] = time.time() - t0
    print(f"  Done in {timings['analytics']:.1f}s")

    # ── Phase 7: Dashboard & Preview Images ──
    print("[7/7] Generating dashboard and preview images...")
    t0 = time.time()

    # Save preview images
    img_dir = os.path.join(output_dir, "preview_images")
    os.makedirs(img_dir, exist_ok=True)

    # Heightmap preview
    hm_img = Image.fromarray(heightmap, mode='L')
    hm_img.save(os.path.join(img_dir, "heightmap.png"))

    # Land mask preview
    lm_uint8 = (land_mask.astype(np.uint8)) * 255
    lm_img = Image.fromarray(lm_uint8, mode='L')
    lm_img.save(os.path.join(img_dir, "land_mask.png"))

    # Provinces preview
    prov_img = Image.fromarray(provinces_bmp, mode='RGB')
    prov_img.save(os.path.join(img_dir, "provinces.png"))

    # Terrain preview
    ter_img = Image.fromarray(terrain_bmp, mode='RGB')
    ter_img.save(os.path.join(img_dir, "terrain.png"))

    # Rivers preview
    riv_img = Image.fromarray(rivers_bmp, mode='RGB')
    riv_img.save(os.path.join(img_dir, "rivers.png"))

    # Normal map preview
    normal_map = NormalMapGenerator.generate(heightmap)
    # NormalMapGenerator returns uint8 RGB; scale only if it ever returns float
    if normal_map.dtype != np.uint8:
        normal_display = ((normal_map + 1) / 2 * 255).astype(np.uint8)
    else:
        normal_display = normal_map
    if normal_display.shape[2] == 3:
        nm_img = Image.fromarray(normal_display, mode='RGB')
    else:
        nm_img = Image.fromarray(normal_display[:,:,0], mode='L')
    nm_img.save(os.path.join(img_dir, "normal_map.png"))

    # Generate dashboard
    preparer = DashboardDataPreparer()
    dash_gen = DashboardGenerator(output_dir=os.path.join(output_dir, "dashboard"))

    # Prepare elevation histogram data
    elev_data = preparer.prepare_elevation_histogram(heightmap)

    # Prepare power ranking
    power_ranking = []
    for c in sorted(countries, key=lambda x: x.adm + x.dip + x.mil, reverse=True)[:20]:
        power_ranking.append({
            "tag": c.tag,
            "name": c.short_name,
            "development": c.adm + c.dip + c.mil,
            "continent": c.continent,
            "religion": c.religion,
            "tech_group": c.tech_group,
            "is_advanced": c.is_advanced,
        })

    # Prepare province details for table
    province_details = []
    for p in province_infos[:200]:  # limit for performance
        province_details.append({
            "id": p.id,
            "terrain": p.terrain_type,
            "elevation": round(p.avg_elevation, 1),
            "continent": p.continent_name,
            "is_sea": p.is_sea,
            "is_island": p.is_island,
            "river_count": p.river_count,
        })

    # Climate zone counts for chart
    climate_counts = {k: len(v) for k, v in climate_zones.items()}

    dash_path = dash_gen.generate_dashboard(
        continent_stats=continent_stats,
        religion_distribution=religion_dist,
        tech_distribution=tech_dist,
        elevation_data=elev_data,
        power_ranking=power_ranking,
        trade_flow=[],  # Could compute from analytics
        province_details=province_details,
        terrain_distribution=terrain_dist,
        climate_zones=climate_counts,
        world_name=mod_name,
        seed=seed,
        map_width=width,
        map_height=height,
    )

    timings["dashboard"] = time.time() - t0
    print(f"  Done in {timings['dashboard']:.1f}s")
    print(f"  Dashboard: {dash_path}")
    print(f"  Preview images: {img_dir}")

    # ── Summary ──
    total_time = sum(timings.values())
    print(f"\n{'='*60}")
    print(f"  WORLD GENERATION COMPLETE")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Map size: {width}x{height}")
    print(f"  Land: {land_pct_actual:.1f}%")
    print(f"  Provinces: {len(province_infos)} ({len(land_provs)} land)")
    print(f"  Countries: {len(countries)}")
    print(f"  Dashboard: {dash_path}")
    print(f"{'='*60}\n")

    return {
        "dashboard_path": dash_path,
        "preview_dir": img_dir,
        "mod_dir": content_dir,
        "timings": timings,
        "heightmap": heightmap,
        "land_mask": land_mask,
        "provinces_bmp": provinces_bmp,
        "terrain_bmp": terrain_bmp,
        "rivers_bmp": rivers_bmp,
        "province_infos": province_infos,
        "countries": countries,
        "continent_stats": continent_stats,
        "religion_dist": religion_dist,
        "tech_dist": tech_dist,
        "climate_zones": climate_zones,
    }


if __name__ == "__main__":
    generate_world()
