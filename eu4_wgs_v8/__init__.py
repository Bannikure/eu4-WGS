"""EU4 World Generator Studio V8 package facade.

This package exposes the top-level project modules (``engine``,
``analytics``, ``content``, ``export``, ``gui``, ``common``,
``resources``, ``eu4gen``) by pointing its ``__path__`` at the
repository root, so the codebase can be imported with the
``eu4_wgs_v8.*`` namespace used throughout the project without moving
existing source directories.

It also exposes the paths for bundled assets and templates, so the
program can find data files when installed or run from a different
working directory.
"""

import importlib
from pathlib import Path
from types import ModuleType

__version__ = "8.0.0"
__author__ = "C.D. Wilson"
__title__ = "EU4 World Generator Studio V8"
__description__ = "Procedural EU4 total-conversion mod generator with Afro-Asian ascendancy"

# The package directory lives inside the repository root; sub-packages
# such as ``engine`` and ``common`` are at the repository root.
_EU4_WGS_V8_DIR = Path(__file__).parent.resolve()
_REPO_ROOT = _EU4_WGS_V8_DIR.parent

__path__ = [str(_REPO_ROOT)]

ASSETS_DIR = _EU4_WGS_V8_DIR / "assets"
TEMPLATES_DIR = _EU4_WGS_V8_DIR / "templates"
PACKAGE_DIR = _REPO_ROOT

# Sub-packages that can be accessed via ``eu4_wgs_v8.<name>``.
_SUBMODULES = frozenset(
    {"common", "engine", "analytics", "content", "export", "gui", "resources", "eu4gen"}
)


def __getattr__(name: str) -> ModuleType:
    """Lazy-load top-level project packages on demand."""
    if name.startswith("_"):
        raise AttributeError(f"module 'eu4_wgs_v8' has no attribute {name!r}")

    if name in _SUBMODULES:
        try:
            # Imports relative to this package, using the repository root
            # path declared above.
            mod = importlib.import_module("." + name, package=__name__)
        except ModuleNotFoundError as exc:
            raise AttributeError(f"module 'eu4_wgs_v8' has no attribute {name!r}") from exc
        globals()[name] = mod
        return mod

    raise AttributeError(f"module 'eu4_wgs_v8' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted({*_SUBMODULES, "ASSETS_DIR", "TEMPLATES_DIR", "PACKAGE_DIR"})
