"""
EU4 Total Conversion Mod Generator & Architect Studio v4.1
==========================================================

Entry point — run with:

    python main.py

Install dependencies first:

    pip install -r requirements.txt
"""

# Optional GIS check – reported at startup, not blocking
try:
    import rasterio       # type: ignore[import-untyped]  # noqa: F401
    from shapely.geometry import Polygon  # type: ignore[import-untyped]  # noqa: F401
    import geopandas as gpd  # type: ignore[import-untyped]  # noqa: F401
    _GIS_AVAILABLE = True
except ImportError:
    _GIS_AVAILABLE = False

from eu4gen.ui import EU4GeneratorUI


def main() -> None:
    """Launch the EU4 World Generator Studio application."""
    if not _GIS_AVAILABLE:
        print(
            "Note: GIS support (rasterio/shapely/geopandas) is not installed.\n"
            "      Install with: pip install rasterio shapely geopandas\n"
            "      The generator will run without GIS features.\n"
        )
    app = EU4GeneratorUI()
    app.mainloop()


if __name__ == "__main__":
    main()
