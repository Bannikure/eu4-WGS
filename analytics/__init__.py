"""Analytics module for heightmap analysis, world statistics, and data visualization."""

from .heightmap_analyzer import (
    HeightmapAnalyzer,
    ProvinceInspector,
    ElevationStats,
    ContinentStats,
    WorldAnalytics,
)

from .dashboard import (
    DashboardGenerator,
    DashboardDataPreparer,
    generate_dashboard_from_analytics,
)

__all__ = [
    "HeightmapAnalyzer",
    "ProvinceInspector",
    "ElevationStats",
    "ContinentStats",
    "WorldAnalytics",
    "DashboardGenerator",
    "DashboardDataPreparer",
    "generate_dashboard_from_analytics",
]
