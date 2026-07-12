"""
EU4 World Generator Studio V8
===============================
Afro-Asian Ascendancy Total Conversion World Generator

A comprehensive toolkit for generating Europa Universalis IV total conversion
mods with inverted power dynamics: Africa and Asia as the most advanced and
wealthy continents, Europe as the weakest and poorest, Hindu as the dominant
world religion, and the Celestial Directorate as a second HRE.

Modules:
  - engine: Map generation, province system, rivers, terrain, normals
  - analytics: Heightmap analysis, world statistics, data visualization dashboard
  - content: Religions, cultures, countries, ideas, diplomacy, trade, flags
  - export: EU4 mod file export, directory structure, bitmap writers
  - gui: CustomTkinter desktop application (optional, headless fallback)
"""

__version__ = "8.0.0"
__author__ = "SuperNinja — NinjaTech AI"
__title__ = "EU4 World Generator Studio V8 — Afro-Asian Ascendancy"

try:
    from eu4_wgs_v8.engine import (
        MapConfig, MapGenerationEngine, ProvinceGenerator, ProvinceInfo,
        RiverGenerator, TerrainClassifier, NormalMapGenerator, WatercolorGenerator,
    )
    from eu4_wgs_v8.analytics import (
        HeightmapAnalyzer, ProvinceInspector, WorldAnalytics,
        DashboardGenerator, generate_dashboard_from_analytics,
    )
    from eu4_wgs_v8.content import (
        CountryGenerator, CountryData, CelestialDirectorate,
        ReligionGenerator, CultureGenerator, IdeaGenerator,
        TradeGenerator, DiplomacyGenerator, FlagGenerator,
    )
    from eu4_wgs_v8.export import (
        MasterExportOrchestrator, MapFileExporter, CountryFileExporter,
        ProvinceHistoryExporter, ModDescriptorExporter,
    )
except ModuleNotFoundError as exc:
    if exc.name != "eu4_wgs_v8":
        raise
