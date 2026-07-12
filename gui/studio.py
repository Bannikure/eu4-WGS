"""
Module 5: EU4 World Generator Studio V8 — Redesigned Desktop GUI
=================================================================
Full-featured desktop application combining the best elements of
WorldGeneratorPlus (WPF/OpenGL preview, colourmap, crater controls)
and EUIV_Map_Generator (Qt5-style step workflow, export panels).

Layout Architecture (inspired by both reference GUIs):
  ┌──────────────────────────────────────────────────────────────┐
  │  [Logo]  ⚡Generate  📦Export  📊Dashboard  🔄Reset  ℹ️About│  ← Toolbar
  ├──────────┬───────────────────────────────────┬───────────────┤
  │ Left     │                                   │ Right         │
  │ Sidebar  │     Map Viewport (Preview)        │ Inspector     │
  │ ─────── │                                   │ ───────────── │
  │ 🗺️ Map   │                                   │ 📋 Province   │
  │ 🌋 Noise │                                   │ 🏰 Country    │
  │ 🌋 Adv   │                                   │ 🌍 World      │
  │ ⚖️ Dynam │                                   │ Stats         │
  │ 🎨 Color │    [Drag & Drop Heightmap Zone]   │               │
  │ 📤 Export│                                   │               │
  ├──────────┴───────────────────────────────────┴───────────────┤
  │  [████████░░░░░░░░] 65%  Generating provinces...  12.3s    │  ← Status
  └──────────────────────────────────────────────────────────────┘
"""

import os
import sys
import threading
import time
import json
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field

try:
    import customtkinter as ctk
    import tkinter as tk
    from tkinter import filedialog, messagebox
    CTk_AVAILABLE = True
except ImportError:
    CTk_AVAILABLE = False

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════
#  COLOR THEME — Modernized dark palette
# ═══════════════════════════════════════════════════════════════

class Theme:
    """Centralized color theme for the entire GUI."""
    # Backgrounds
    BG_DARKEST = "#0d1117"       # Main window bg
    BG_DARK = "#161b22"          # Panel backgrounds
    BG_MEDIUM = "#21262d"        # Section frames, cards
    BG_LIGHT = "#30363d"         # Hover states, elevated elements
    BG_LIGHTER = "#484f58"       # Active/pressed elements

    # Accent colors
    ACCENT_PRIMARY = "#f0a500"   # Gold — primary action accent
    ACCENT_PRIMARY_HOVER = "#d4940a"
    ACCENT_SUCCESS = "#2ea043"   # Green — export/success
    ACCENT_SUCCESS_HOVER = "#238636"
    ACCENT_INFO = "#58a6ff"      # Blue — info/dashboard
    ACCENT_INFO_HOVER = "#388bfd"
    ACCENT_WARNING = "#d29922"   # Yellow — warning
    ACCENT_DANGER = "#f85149"    # Red — danger/error
    ACCENT_PURPLE = "#bc8cff"    # Purple — special features

    # Text
    TEXT_PRIMARY = "#f0f6fc"     # Primary text
    TEXT_SECONDARY = "#8b949e"   # Secondary/muted text
    TEXT_TERTIARY = "#6e7681"    # Disabled/very muted text
    TEXT_ACCENT = "#f0a500"      # Accent-colored text (section headers)
    TEXT_ON_ACCENT = "#0d1117"   # Text on accent-colored buttons

    # Borders & Separators
    BORDER = "#30363d"
    BORDER_LIGHT = "#484f58"
    SEPARATOR = "#21262d"

    # Special
    DROPZONE_BG = "#0d1117"
    DROPZONE_BORDER = "#f0a500"
    DROPZONE_ACTIVE_BG = "#1a1f2a"
    TAB_ACTIVE = "#f0a500"
    TAB_INACTIVE = "#21262d"
    TAB_HOVER = "#30363d"
    SCROLLBAR = "#484f58"
    PROGRESS_BG = "#21262d"
    PROGRESS_FILL = "#f0a500"


# ═══════════════════════════════════════════════════════════════
#  GUI STATE & CONFIGURATION
# ═══════════════════════════════════════════════════════════════

class GUIConfig:
    """Holds all GUI configuration state — mirrors engine parameters."""
    # Map generation
    mod_name: str = "AfroAsianAscendancy"
    seed: int = 42
    map_width: int = 5632
    map_height: int = 2048
    province_count: int = 1500
    land_percentage: int = 30
    map_style: str = "continents"

    # Noise parameters
    noise_octaves: int = 6
    noise_persistence: float = 0.5
    noise_lacunarity: float = 2.0
    noise_scale: float = 4.0
    domain_warp_strength: float = 0.4
    ridge_exponent: float = 1.2

    # Advanced features
    enable_tectonic_plates: bool = True
    enable_hydraulic_erosion: bool = True
    enable_impact_craters: bool = True
    num_craters: int = 3
    crater_radius_min: int = 10
    crater_radius_max: int = 40
    crater_pattern: str = "random"  # random, cluster, spread

    # Climate
    enable_climate_generation: bool = True
    temperature_offset: float = 0.0
    rainfall_multiplier: float = 1.0

    # Colourmap / visualization
    colourmap_name: str = "Classic"  # Classic, Volcanic, Tropical, Arctic, Desert
    show_contour_lines: bool = False
    contour_interval: int = 50
    show_rivers_overlay: bool = True
    show_province_borders: bool = True

    # Inverted dynamics
    hindu_dominance: float = 0.40
    pagan_strength: float = 0.25
    european_weakness: float = 0.85
    african_advancement: float = 0.90
    asian_advancement: float = 0.95

    # Celestial Directorate (second HRE)
    enable_celestial_directorate: bool = True
    directorate_reforms: int = 8

    # Export
    output_dir: str = "./mod_output"
    export_flags: bool = True
    export_history: bool = True
    export_common: bool = True
    export_events: bool = True
    export_missions: bool = True
    export_localisation: bool = True

    # Import
    imported_heightmap_path: str = ""

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__class__.__dict__.items()
                if not k.startswith('_') and not callable(v)}


class GenerationState:
    """Tracks the state of world generation."""
    idle = 0
    generating = 1
    complete = 2
    error = 3

    def __init__(self):
        self.state = self.idle
        self.progress = 0.0
        self.message = "Ready"
        self.phase = ""
        self.elapsed = 0.0
        self.start_time = 0.0

    def start(self):
        self.state = self.generating
        self.progress = 0.0
        self.start_time = time.time()

    def update(self, progress: float, message: str, phase: str = ""):
        self.progress = progress
        self.message = message
        self.phase = phase
        self.elapsed = time.time() - self.start_time

    def finish(self, message: str = "Complete!"):
        self.state = self.complete
        self.progress = 1.0
        self.message = message
        self.elapsed = time.time() - self.start_time

    def fail(self, message: str):
        self.state = self.error
        self.message = message


# ═══════════════════════════════════════════════════════════════
#  REUSABLE UI COMPONENTS
# ═══════════════════════════════════════════════════════════════

class CollapsibleSection(ctk.CTkFrame):
    """A collapsible section with header and expandable content — like WGP panels."""

    def __init__(self, master, title: str, icon: str = "▸", expanded: bool = True, **kwargs):
        kwargs.setdefault("fg_color", Theme.BG_MEDIUM)
        kwargs.setdefault("corner_radius", 6)
        super().__init__(master, **kwargs)

        self._expanded = expanded
        self._icon = icon
        self._title = title

        # Header
        self.header = ctk.CTkFrame(self, fg_color="transparent", height=32, cursor="hand2")
        self.header.pack(fill="x", padx=4, pady=(4, 0))
        self.header.pack_propagate(False)

        self.toggle_icon = ctk.CTkLabel(
            self.header, text=icon if expanded else "▾",
            font=ctk.CTkFont(size=13), text_color=Theme.TEXT_ACCENT, width=20
        )
        self.toggle_icon.pack(side="left", padx=(8, 2))

        self.title_label = ctk.CTkLabel(
            self.header, text=title,
            font=ctk.CTkFont(size=13, weight="bold"), text_color=Theme.TEXT_ACCENT
        )
        self.title_label.pack(side="left", padx=(2, 0))

        # Content frame
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        if expanded:
            self.content.pack(fill="x", padx=8, pady=(2, 8))

        # Bind toggle
        for widget in [self.header, self.toggle_icon, self.title_label]:
            widget.bind("<Button-1>", self._toggle)

    def _toggle(self, event=None):
        if self._expanded:
            self.content.pack_forget()
            self.toggle_icon.configure(text="▾")
            self._expanded = False
        else:
            self.content.pack(fill="x", padx=8, pady=(2, 8))
            self.toggle_icon.configure(text=self._icon)
            self._expanded = True


class LabeledSlider(ctk.CTkFrame):
    """A slider with label and value display — WGP style."""

    def __init__(self, master, label: str, from_: int, to: int, default: int,
                 step: int = 1, suffix: str = "", **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)

        self._suffix = suffix

        # Top row: label + value
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x")

        lbl = ctk.CTkLabel(top, text=label, font=ctk.CTkFont(size=11),
                           text_color=Theme.TEXT_SECONDARY, anchor="w")
        lbl.pack(side="left")

        self.val_label = ctk.CTkLabel(
            top, text=f"{default}{suffix}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Theme.TEXT_PRIMARY, anchor="e", width=50
        )
        self.val_label.pack(side="right")

        # Slider
        self.slider = ctk.CTkSlider(
            self, from_=from_, to=to, number_of_steps=min(to - from_, 200),
            height=16, progress_color=Theme.ACCENT_PRIMARY,
            button_color=Theme.ACCENT_PRIMARY, button_hover_color=Theme.ACCENT_PRIMARY_HOVER,
            command=self._on_change
        )
        self.slider.pack(fill="x", pady=(2, 0))
        self.slider.set(default)

    def _on_change(self, value):
        self.val_label.configure(text=f"{int(value)}{self._suffix}")

    def get(self) -> int:
        return int(self.slider.get())


class IconicButton(ctk.CTkButton):
    """A styled button with icon — consistent with toolbar/action buttons."""

    def __init__(self, master, text: str, icon: str = "", color: str = Theme.ACCENT_PRIMARY,
                 hover_color: str = None, text_color: str = Theme.TEXT_ON_ACCENT,
                 width: int = 130, height: int = 34, **kwargs):
        kwargs.setdefault("fg_color", color)
        kwargs.setdefault("hover_color", hover_color or self._darken(color))
        kwargs.setdefault("text_color", text_color)
        kwargs.setdefault("font", ctk.CTkFont(size=12, weight="bold"))
        kwargs.setdefault("corner_radius", 6)
        kwargs.setdefault("height", height)
        kwargs.setdefault("width", width)
        display = f"{icon} {text}" if icon else text
        super().__init__(master, text=display, **kwargs)

    @staticmethod
    def _darken(hex_color: str) -> str:
        """Darken a hex color for hover state."""
        try:
            r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
            return f"#{max(0,r-30):02x}{max(0,g-30):02x}{max(0,b-30):02x}"
        except (ValueError, IndexError):
            return hex_color


class DropZone(ctk.CTkFrame):
    """Drag-and-drop heightmap import zone — modernized WGP feature."""

    def __init__(self, master, on_drop_callback: Callable = None, **kwargs):
        kwargs.setdefault("fg_color", Theme.DROPZONE_BG)
        kwargs.setdefault("corner_radius", 8)
        kwargs.setdefault("border_width", 2)
        kwargs.setdefault("border_color", Theme.DROPZONE_BORDER)
        super().__init__(master, **kwargs)

        self._on_drop = on_drop_callback
        self._is_dragging = False

        # Icon
        self.icon_label = ctk.CTkLabel(
            self, text="📁", font=ctk.CTkFont(size=28),
            text_color=Theme.ACCENT_PRIMARY
        )
        self.icon_label.pack(pady=(16, 4))

        # Main text
        self.main_label = ctk.CTkLabel(
            self, text="Drop Heightmap Here",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        self.main_label.pack(pady=(0, 2))

        # Subtitle
        self.sub_label = ctk.CTkLabel(
            self, text="or click to browse  •  PNG / BMP / TIFF",
            font=ctk.CTkFont(size=11),
            text_color=Theme.TEXT_SECONDARY
        )
        self.sub_label.pack(pady=(0, 4))

        # File path display
        self.path_label = ctk.CTkLabel(
            self, text="No file selected",
            font=ctk.CTkFont(size=10),
            text_color=Theme.TEXT_TERTIARY
        )
        self.path_label.pack(pady=(0, 12))

        # Bind click to browse
        self.bind("<Button-1>", self._on_click)
        for child in self.winfo_children():
            child.bind("<Button-1>", self._on_click)

        # Bind drag events
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Motion>", self._on_motion)

    def _on_click(self, event=None):
        """Open file dialog when clicked."""
        path = filedialog.askopenfilename(
            title="Select Heightmap Image",
            filetypes=[
                ("Image files", "*.png *.bmp *.tif *.tiff *.jpg *.jpeg"),
                ("PNG files", "*.png"),
                ("BMP files", "*.bmp"),
                ("All files", "*.*"),
            ]
        )
        if path:
            self.set_file(path)

    def set_file(self, path: str):
        """Display the selected file path."""
        self.path_label.configure(
            text=os.path.basename(path),
            text_color=Theme.ACCENT_PRIMARY
        )
        if self._on_drop:
            self._on_drop(path)

    def _on_enter(self, event=None):
        self.configure(border_color=Theme.ACCENT_PRIMARY)

    def _on_leave(self, event=None):
        self.configure(border_color=Theme.DROPZONE_BORDER)

    def _on_motion(self, event=None):
        pass  # Visual feedback for drag


class ColourmapSelector(ctk.CTkFrame):
    """Colourmap selection panel — inspired by WGP colourmap picker."""

    COLOURMAPS = {
        "Classic": ["#1a5276", "#27ae60", "#f4d03f", "#e74c3c", "#8e44ad"],
        "Volcanic": ["#1a1a2e", "#6a0572", "#c3192d", "#f57c00", "#ffe082"],
        "Tropical": ["#0d47a1", "#00796b", "#4caf50", "#ffeb3b", "#ff9800"],
        "Arctic": ["#0d1b2a", "#1b3a5c", "#415a77", "#778da9", "#e0e1dd"],
        "Desert": ["#3e2723", "#795548", "#c8a97e", "#f4d03f", "#f9e79f"],
        "Neon": ["#0d0221", "#0f084b", "#26408b", "#a6f089", "#f57c00"],
    }

    def __init__(self, master, on_change_callback: Callable = None, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)

        self._on_change = on_change_callback
        self._selected = "Classic"

        # Label
        lbl = ctk.CTkLabel(self, text="Colourmap:", font=ctk.CTkFont(size=11),
                           text_color=Theme.TEXT_SECONDARY, anchor="w")
        lbl.pack(fill="x", pady=(0, 4))

        # Colourmap option menu
        self.menu = ctk.CTkOptionMenu(
            self, values=list(self.COLOURMAPS.keys()),
            height=28, font=ctk.CTkFont(size=12),
            fg_color=Theme.BG_LIGHT, button_color=Theme.ACCENT_PRIMARY,
            button_hover_color=Theme.ACCENT_PRIMARY_HOVER,
            command=self._on_select
        )
        self.menu.pack(fill="x", pady=(0, 6))
        self.menu.set("Classic")

        # Preview bar
        self.preview_frame = ctk.CTkFrame(self, height=20, corner_radius=4,
                                           fg_color=Theme.BG_DARK)
        self.preview_frame.pack(fill="x")
        self.preview_frame.pack_propagate(False)

        self._update_preview()

    def _on_select(self, value):
        self._selected = value
        self._update_preview()
        if self._on_change:
            self._on_change(value)

    def _update_preview(self):
        """Update the colourmap preview gradient bar."""
        for child in self.preview_frame.winfo_children():
            child.destroy()

        colors = self.COLOURMAPS.get(self._selected, self.COLOURMAPS["Classic"])
        n = len(colors)
        for i, color in enumerate(colors):
            seg = ctk.CTkFrame(
                self.preview_frame, fg_color=color, corner_radius=0,
                width=max(1, 200 // n)
            )
            seg.pack(side="left", fill="both", expand=True)

    def get(self) -> str:
        return self._selected


# ═══════════════════════════════════════════════════════════════
#  MAIN APPLICATION WINDOW
# ═══════════════════════════════════════════════════════════════

if CTk_AVAILABLE:
    class WorldGeneratorStudio(ctk.CTk):
        """Main application window — redesigned to combine WGP + EU4MapGen style."""

        def __init__(self):
            super().__init__()

            self.config = GUIConfig()
            self.gen_state = GenerationState()

            # Generated data storage
            self.heightmap = None
            self.province_map = None
            self.terrain_bmp = None
            self.rivers_bmp = None
            self.normal_map = None
            self.watercolor_bmp = None
            self.province_info_list = []
            self.country_list = []
            self.analytics = None

            # Image references for display
            self._preview_images = {}
            self._current_preview = None
            self._current_tab = "🗺️ Heightmap"

            # Engine references (lazy loaded)
            self._engine = None
            self._exporter = None

            # Window setup
            self.title("EU4 World Generator Studio V8 — Afro-Asian Ascendancy")
            self.geometry("1600x950")
            self.minsize(1280, 750)
            self.configure(fg_color=Theme.BG_DARKEST)
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")

            # Build UI
            self._build_toolbar()
            self._build_main_layout()
            self._build_left_sidebar()
            self._build_center_viewport()
            self._build_right_inspector()
            self._build_status_bar()

            # Status update loop
            self._status_loop()

        # ── Toolbar (top action bar) ────────────────────────────
        def _build_toolbar(self):
            """Build the top toolbar with action buttons — WGP style ribbon."""
            self.toolbar = ctk.CTkFrame(
                self, height=48, corner_radius=0, fg_color=Theme.BG_DARK
            )
            self.toolbar.pack(fill="x", side="top")
            self.toolbar.pack_propagate(False)

            # Left: Logo
            logo_frame = ctk.CTkFrame(self.toolbar, fg_color="transparent")
            logo_frame.pack(side="left", padx=12, pady=6)

            logo_icon = ctk.CTkLabel(
                logo_frame, text="🌍", font=ctk.CTkFont(size=22)
            )
            logo_icon.pack(side="left", padx=(0, 6))

            logo_text = ctk.CTkLabel(
                logo_frame, text="WGS V8",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=Theme.ACCENT_PRIMARY
            )
            logo_text.pack(side="left")

            # Center: Action buttons
            actions_frame = ctk.CTkFrame(self.toolbar, fg_color="transparent")
            actions_frame.pack(side="left", padx=20, pady=6)

            self.btn_generate = IconicButton(
                actions_frame, text="Generate World", icon="⚡",
                color=Theme.ACCENT_PRIMARY, width=150,
                command=self._on_generate
            )
            self.btn_generate.pack(side="left", padx=3)

            self.btn_export = IconicButton(
                actions_frame, text="Export Mod", icon="📦",
                color=Theme.ACCENT_SUCCESS, width=120,
                command=self._on_export
            )
            self.btn_export.pack(side="left", padx=3)

            self.btn_dashboard = IconicButton(
                actions_frame, text="Dashboard", icon="📊",
                color=Theme.ACCENT_INFO, width=120,
                command=self._on_open_dashboard
            )
            self.btn_dashboard.pack(side="left", padx=3)

            self.btn_reset = IconicButton(
                actions_frame, text="Reset", icon="🔄",
                color=Theme.BG_LIGHT, text_color=Theme.TEXT_PRIMARY,
                width=90, command=self._on_reset
            )
            self.btn_reset.pack(side="left", padx=3)

            # Right: Info label
            info_frame = ctk.CTkFrame(self.toolbar, fg_color="transparent")
            info_frame.pack(side="right", padx=12, pady=6)

            info_label = ctk.CTkLabel(
                info_frame,
                text="Afro-Asian Ascendancy │ Hindu Dominant │ Celestial Directorate",
                font=ctk.CTkFont(size=10), text_color=Theme.TEXT_TERTIARY
            )
            info_label.pack(side="right")

        # ── Main Layout ─────────────────────────────────────────
        def _build_main_layout(self):
            """Three-panel layout: Left sidebar | Center viewport | Right inspector."""
            self.main_container = ctk.CTkFrame(self, fg_color=Theme.BG_DARKEST)
            self.main_container.pack(fill="both", expand=True)

            self.main_container.grid_rowconfigure(0, weight=1)
            self.main_container.grid_columnconfigure(1, weight=1)

        # ── Left Sidebar ────────────────────────────────────────
        def _build_left_sidebar(self):
            """Build the left sidebar with collapsible sections — WGP + EU4MapGen style."""
            self.left_sidebar = ctk.CTkFrame(
                self.main_container, width=300, corner_radius=0,
                fg_color=Theme.BG_DARK
            )
            self.left_sidebar.grid(row=0, column=0, sticky="ns")
            self.left_sidebar.grid_propagate(False)

            # Sidebar title
            sidebar_title = ctk.CTkLabel(
                self.left_sidebar, text="⚙️  Configuration",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=Theme.TEXT_ACCENT
            )
            sidebar_title.pack(pady=(8, 4), padx=12, anchor="w")

            sep = ctk.CTkFrame(self.left_sidebar, height=2, fg_color=Theme.ACCENT_PRIMARY)
            sep.pack(fill="x", padx=12, pady=(0, 8))

            # Scrollable area for sections
            self.sidebar_scroll = ctk.CTkScrollableFrame(
                self.left_sidebar, fg_color="transparent",
                scrollbar_button_color=Theme.SCROLLBAR,
                scrollbar_button_hover_color=Theme.BG_LIGHTER
            )
            self.sidebar_scroll.pack(fill="both", expand=True, padx=4, pady=4)

            # ── Section: Map Settings ──
            sec_map = CollapsibleSection(self.sidebar_scroll, "🗺️  Map Settings", "🗺️", True)
            sec_map.pack(fill="x", pady=(0, 6))

            self.entry_mod_name = self._make_entry(sec_map, "Mod Name", self.config.mod_name)
            self.entry_seed = self._make_entry(sec_map, "Seed", str(self.config.seed))

            self.slider_provinces = LabeledSlider(
                sec_map.content, "Provinces", 100, 4000, self.config.province_count
            )
            self.slider_provinces.pack(fill="x", pady=2)

            self.slider_land_pct = LabeledSlider(
                sec_map.content, "Land %", 10, 60, self.config.land_percentage, suffix="%"
            )
            self.slider_land_pct.pack(fill="x", pady=2)

            self.opt_map_style = self._make_option(
                sec_map.content, "Map Style:",
                ["pangea", "continents", "archipelago", "continents_islands"],
                self.config.map_style
            )
            self.opt_map_style.pack(fill="x", pady=2)

            # Quick size buttons
            size_frame = ctk.CTkFrame(sec_map.content, fg_color="transparent")
            size_frame.pack(fill="x", pady=4)
            ctk.CTkLabel(size_frame, text="Quick Size:", font=ctk.CTkFont(size=11),
                         text_color=Theme.TEXT_SECONDARY).pack(side="left")
            for size_name, w, h in [("Small", 2048, 1024), ("Medium", 4096, 2048),
                                     ("EU4 Std", 5632, 2048), ("Large", 8192, 4096)]:
                btn = ctk.CTkButton(
                    size_frame, text=size_name, width=60, height=24,
                    fg_color=Theme.BG_LIGHT, hover_color=Theme.BG_LIGHTER,
                    text_color=Theme.TEXT_SECONDARY, font=ctk.CTkFont(size=10),
                    corner_radius=4,
                    command=lambda w=w, h=h: self._set_map_size(w, h)
                )
                btn.pack(side="left", padx=2)

            # ── Section: Noise Parameters ──
            sec_noise = CollapsibleSection(self.sidebar_scroll, "🌋  Noise Parameters", "🌋", True)
            sec_noise.pack(fill="x", pady=(0, 6))

            noise_sliders = [
                ("Octaves", 1, 10, self.config.noise_octaves),
                ("Persistence", 10, 90, int(self.config.noise_persistence * 100)),
                ("Lacunarity", 10, 50, int(self.config.noise_lacunarity * 100)),
                ("Scale", 10, 100, int(self.config.noise_scale * 10)),
                ("Domain Warp", 0, 100, int(self.config.domain_warp_strength * 100)),
                ("Ridge Exp", 50, 300, int(self.config.ridge_exponent * 100)),
            ]
            self._noise_sliders = {}
            for label, from_, to, default in noise_sliders:
                s = LabeledSlider(sec_noise.content, label, from_, to, default)
                s.pack(fill="x", pady=2)
                self._noise_sliders[label] = s

            # ── Section: Advanced Terrain ──
            sec_adv = CollapsibleSection(self.sidebar_scroll, "🌋  Advanced Terrain", "🌋", True)
            sec_adv.pack(fill="x", pady=(0, 6))

            self.chk_tectonic = self._make_checkbox(sec_adv.content, "Tectonic Plates", True)
            self.chk_erosion = self._make_checkbox(sec_adv.content, "Hydraulic Erosion", True)
            self.chk_craters = self._make_checkbox(sec_adv.content, "Impact Craters", True)

            self.slider_craters = LabeledSlider(
                sec_adv.content, "Num Craters", 0, 10, self.config.num_craters
            )
            self.slider_craters.pack(fill="x", pady=2)

            self.slider_crater_min = LabeledSlider(
                sec_adv.content, "Min Radius", 5, 30, self.config.crater_radius_min
            )
            self.slider_crater_min.pack(fill="x", pady=2)

            self.slider_crater_max = LabeledSlider(
                sec_adv.content, "Max Radius", 20, 80, self.config.crater_radius_max
            )
            self.slider_crater_max.pack(fill="x", pady=2)

            self.opt_crater_pattern = self._make_option(
                sec_adv.content, "Pattern:",
                ["random", "cluster", "spread"],
                self.config.crater_pattern
            )
            self.opt_crater_pattern.pack(fill="x", pady=2)

            # ── Section: Climate ──
            sec_climate = CollapsibleSection(self.sidebar_scroll, "🌡️  Climate", "🌡️", False)
            sec_climate.pack(fill="x", pady=(0, 6))

            self.chk_climate = self._make_checkbox(sec_climate.content, "Climate Generation", True)

            self.slider_temp_offset = LabeledSlider(
                sec_climate.content, "Temp Offset", -50, 50, 0, suffix="°"
            )
            self.slider_temp_offset.pack(fill="x", pady=2)

            self.slider_rain_mult = LabeledSlider(
                sec_climate.content, "Rainfall ×", 50, 200, 100, suffix="%"
            )
            self.slider_rain_mult.pack(fill="x", pady=2)

            # ── Section: Inverted Dynamics ──
            sec_dyn = CollapsibleSection(self.sidebar_scroll, "⚖️  Inverted Dynamics", "⚖️", True)
            sec_dyn.pack(fill="x", pady=(0, 6))

            self.slider_hindu = LabeledSlider(
                sec_dyn.content, "Hindu %", 10, 70, int(self.config.hindu_dominance * 100), suffix="%"
            )
            self.slider_hindu.pack(fill="x", pady=2)

            self.slider_pagan = LabeledSlider(
                sec_dyn.content, "Pagan %", 5, 50, int(self.config.pagan_strength * 100), suffix="%"
            )
            self.slider_pagan.pack(fill="x", pady=2)

            self.slider_euro_weak = LabeledSlider(
                sec_dyn.content, "Europe Weakness", 50, 100, int(self.config.european_weakness * 100), suffix="%"
            )
            self.slider_euro_weak.pack(fill="x", pady=2)

            self.slider_african_adv = LabeledSlider(
                sec_dyn.content, "Africa Advance", 50, 100, int(self.config.african_advancement * 100), suffix="%"
            )
            self.slider_african_adv.pack(fill="x", pady=2)

            self.slider_asian_adv = LabeledSlider(
                sec_dyn.content, "Asia Advance", 50, 100, int(self.config.asian_advancement * 100), suffix="%"
            )
            self.slider_asian_adv.pack(fill="x", pady=2)

            self.chk_directorate = self._make_checkbox(
                sec_dyn.content, "Celestial Directorate (2nd HRE)", True
            )

            # ── Section: Colourmap & Display ──
            sec_color = CollapsibleSection(self.sidebar_scroll, "🎨  Colourmap & Display", "🎨", True)
            sec_color.pack(fill="x", pady=(0, 6))

            self.colourmap_selector = ColourmapSelector(
                sec_color.content, on_change_callback=self._on_colourmap_change
            )
            self.colourmap_selector.pack(fill="x", pady=2)

            self.chk_contours = self._make_checkbox(sec_color.content, "Contour Lines", False)
            self.chk_rivers_overlay = self._make_checkbox(sec_color.content, "Rivers Overlay", True)
            self.chk_province_borders = self._make_checkbox(sec_color.content, "Province Borders", True)

            # ── Section: Import Heightmap ──
            sec_import = CollapsibleSection(self.sidebar_scroll, "📥  Import Heightmap", "📥", True)
            sec_import.pack(fill="x", pady=(0, 6))

            self.drop_zone = DropZone(
                sec_import.content, on_drop_callback=self._on_heightmap_import,
                height=110
            )
            self.drop_zone.pack(fill="x", pady=4)

            # Import action buttons
            import_btns = ctk.CTkFrame(sec_import.content, fg_color="transparent")
            import_btns.pack(fill="x", pady=2)

            self.btn_import_apply = IconicButton(
                import_btns, text="Apply", icon="✓",
                color=Theme.ACCENT_SUCCESS, width=90, height=28,
                command=self._apply_imported_heightmap
            )
            self.btn_import_apply.pack(side="left", padx=2)

            self.btn_import_clear = IconicButton(
                import_btns, text="Clear", icon="✗",
                color=Theme.BG_LIGHTER, text_color=Theme.TEXT_PRIMARY,
                width=90, height=28,
                command=self._clear_imported_heightmap
            )
            self.btn_import_clear.pack(side="left", padx=2)

            # ── Section: Export Options ──
            sec_export = CollapsibleSection(self.sidebar_scroll, "📤  Export Options", "📤", False)
            sec_export.pack(fill="x", pady=(0, 6))

            self.entry_output = self._make_entry(sec_export, "Output Dir", self.config.output_dir)

            browse_btn = ctk.CTkButton(
                sec_export.content, text="📁 Browse...", width=100, height=28,
                fg_color=Theme.BG_LIGHT, hover_color=Theme.BG_LIGHTER,
                text_color=Theme.TEXT_SECONDARY, font=ctk.CTkFont(size=11),
                corner_radius=4, command=self._on_browse_output
            )
            browse_btn.pack(pady=4)

            self.chk_export_flags = self._make_checkbox(sec_export.content, "Export Flags (TGA)", True)
            self.chk_export_history = self._make_checkbox(sec_export.content, "Export History", True)
            self.chk_export_common = self._make_checkbox(sec_export.content, "Export Common Files", True)
            self.chk_export_events = self._make_checkbox(sec_export.content, "Export Events", True)
            self.chk_export_missions = self._make_checkbox(sec_export.content, "Export Missions", True)
            self.chk_export_localisation = self._make_checkbox(sec_export.content, "Export Localisation", True)

        # ── Center Viewport ─────────────────────────────────────
        def _build_center_viewport(self):
            """Build the center map viewport with tab system — WGP OpenGL preview style."""
            self.center_panel = ctk.CTkFrame(
                self.main_container, corner_radius=0,
                fg_color=Theme.BG_DARKEST
            )
            self.center_panel.grid(row=0, column=1, sticky="nsew")
            self.center_panel.grid_rowconfigure(1, weight=1)
            self.center_panel.grid_columnconfigure(0, weight=1)

            # Tab bar
            self.tab_bar = ctk.CTkFrame(
                self.center_panel, height=40, corner_radius=0,
                fg_color=Theme.BG_DARK
            )
            self.tab_bar.grid(row=0, column=0, sticky="ew")
            self.tab_bar.grid_propagate(False)

            tab_container = ctk.CTkFrame(self.tab_bar, fg_color="transparent")
            tab_container.pack(fill="x", padx=6, pady=6)

            self.tab_buttons = {}
            tabs = [
                ("🗺️ Heightmap", "heightmap"),
                ("🏔️ Terrain", "terrain"),
                ("🌊 Rivers", "rivers"),
                ("🗺️ Provinces", "provinces"),
                ("🎨 Watercolor", "watercolor"),
                ("📊 Analytics", "analytics"),
            ]
            for i, (tab_name, key) in enumerate(tabs):
                btn = ctk.CTkButton(
                    tab_container, text=tab_name, width=110, height=28,
                    fg_color=Theme.TAB_ACTIVE if i == 0 else Theme.TAB_INACTIVE,
                    hover_color=Theme.TAB_HOVER,
                    text_color=Theme.TEXT_ON_ACCENT if i == 0 else Theme.TEXT_SECONDARY,
                    font=ctk.CTkFont(size=11, weight="bold" if i == 0 else "normal"),
                    corner_radius=6,
                    command=lambda t=tab_name: self._switch_tab(t)
                )
                btn.pack(side="left", padx=2)
                self.tab_buttons[tab_name] = btn

            # Zoom controls (right side of tab bar)
            zoom_frame = ctk.CTkFrame(self.tab_bar, fg_color="transparent")
            zoom_frame.pack(side="right", padx=8)

            ctk.CTkButton(
                zoom_frame, text="🔍+", width=36, height=28,
                fg_color=Theme.BG_LIGHT, hover_color=Theme.BG_LIGHTER,
                text_color=Theme.TEXT_SECONDARY, font=ctk.CTkFont(size=12),
                corner_radius=4, command=self._zoom_in
            ).pack(side="left", padx=1)

            ctk.CTkButton(
                zoom_frame, text="🔍−", width=36, height=28,
                fg_color=Theme.BG_LIGHT, hover_color=Theme.BG_LIGHTER,
                text_color=Theme.TEXT_SECONDARY, font=ctk.CTkFont(size=12),
                corner_radius=4, command=self._zoom_out
            ).pack(side="left", padx=1)

            ctk.CTkButton(
                zoom_frame, text="⊞", width=36, height=28,
                fg_color=Theme.BG_LIGHT, hover_color=Theme.BG_LIGHTER,
                text_color=Theme.TEXT_SECONDARY, font=ctk.CTkFont(size=12),
                corner_radius=4, command=self._zoom_fit
            ).pack(side="left", padx=1)

            # Viewport area
            self.viewport = ctk.CTkFrame(
                self.center_panel, fg_color=Theme.BG_DARKEST, corner_radius=8,
                border_width=1, border_color=Theme.BORDER
            )
            self.viewport.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 8))
            self.viewport.grid_rowconfigure(0, weight=1)
            self.viewport.grid_columnconfigure(0, weight=1)

            # Placeholder
            self.viewport_label = ctk.CTkLabel(
                self.viewport,
                text="🌍  Generate a world to see the map preview\n\n"
                     "Configure settings on the left, then click ⚡ Generate World",
                font=ctk.CTkFont(size=16), text_color=Theme.TEXT_TERTIARY,
                wraplength=600, justify="center"
            )
            self.viewport_label.grid(row=0, column=0, padx=20, pady=20)

            # Map info overlay (bottom-left corner of viewport)
            self.map_info_frame = ctk.CTkFrame(
                self.viewport, fg_color=Theme.BG_DARK,
                corner_radius=6, width=200, height=80,
                border_width=1, border_color=Theme.BORDER
            )
            self.map_info_frame.grid(row=0, column=0, sticky="sw", padx=10, pady=10)
            self.map_info_frame.grid_propagate(False)

            self.map_info_label = ctk.CTkLabel(
                self.map_info_frame,
                text="Map: —\nSize: —\nProvinces: —",
                font=ctk.CTkFont(size=10), text_color=Theme.TEXT_SECONDARY,
                justify="left"
            )
            self.map_info_label.pack(padx=8, pady=6, anchor="w")

        # ── Right Inspector Panel ───────────────────────────────
        def _build_right_inspector(self):
            """Build the right inspector panel — EU4MapGen style data panel."""
            self.right_panel = ctk.CTkFrame(
                self.main_container, width=280, corner_radius=0,
                fg_color=Theme.BG_DARK
            )
            self.right_panel.grid(row=0, column=2, sticky="ns")
            self.right_panel.grid_propagate(False)

            # Inspector title
            insp_title = ctk.CTkLabel(
                self.right_panel, text="🔍  Inspector",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=Theme.TEXT_ACCENT
            )
            insp_title.pack(pady=(8, 4), padx=12, anchor="w")

            sep = ctk.CTkFrame(self.right_panel, height=2, fg_color=Theme.ACCENT_PRIMARY)
            sep.pack(fill="x", padx=12, pady=(0, 8))

            # Segmented tabs for inspector
            self.inspector_tabs = ctk.CTkSegmentedTab(
                self.right_panel, values=["Province", "Country", "World"],
                command=self._on_inspector_tab_change
            )
            self.inspector_tabs.pack(fill="x", padx=8, pady=4)

            # Inspector content
            self.inspector_scroll = ctk.CTkScrollableFrame(
                self.right_panel, fg_color="transparent",
                scrollbar_button_color=Theme.SCROLLBAR,
                scrollbar_button_hover_color=Theme.BG_LIGHTER
            )
            self.inspector_scroll.pack(fill="both", expand=True, padx=4, pady=4)

            # Province inspector fields
            self._inspector_province_labels = {}
            self._add_inspector_header("📋 Province Details")
            province_fields = [
                "Province ID", "Name", "Elevation", "Terrain", "Continent",
                "Development", "Base Tax", "Production", "Manpower",
                "Trade Good", "Religion", "Culture", "Tech Group", "Owner"
            ]
            for field in province_fields:
                frame = ctk.CTkFrame(self.inspector_scroll, fg_color="transparent")
                frame.pack(fill="x", pady=1)
                lbl_name = ctk.CTkLabel(
                    frame, text=field + ":", font=ctk.CTkFont(size=11),
                    text_color=Theme.TEXT_SECONDARY, width=100, anchor="w"
                )
                lbl_name.pack(side="left")
                lbl_val = ctk.CTkLabel(
                    frame, text="—", font=ctk.CTkFont(size=11),
                    text_color=Theme.TEXT_PRIMARY, anchor="w"
                )
                lbl_val.pack(side="left", fill="x", expand=True)
                self._inspector_province_labels[field] = lbl_val

            # World statistics section
            self._add_inspector_header("🌍 World Statistics")
            self._world_stat_labels = {}
            world_fields = [
                "Total Provinces", "Land Provinces", "Sea Provinces",
                "Total Countries", "Advanced Countries", "Primitive Countries",
                "Hindu Provinces", "Pagan Provinces", "Abrahamic Provinces",
                "Avg Development", "Avg Tax", "Avg Production", "Avg Manpower",
            ]
            for field in world_fields:
                frame = ctk.CTkFrame(self.inspector_scroll, fg_color="transparent")
                frame.pack(fill="x", pady=1)
                lbl_name = ctk.CTkLabel(
                    frame, text=field + ":", font=ctk.CTkFont(size=11),
                    text_color=Theme.TEXT_SECONDARY, width=110, anchor="w"
                )
                lbl_name.pack(side="left")
                lbl_val = ctk.CTkLabel(
                    frame, text="—", font=ctk.CTkFont(size=11),
                    text_color=Theme.TEXT_PRIMARY, anchor="w"
                )
                lbl_val.pack(side="left", fill="x", expand=True)
                self._world_stat_labels[field] = lbl_val

            # Tech group breakdown
            self._add_inspector_header("⚙️ Tech Groups")
            self._tech_labels = {}
            for tg in ["chinese", "indian", "muslim", "east_african", "north_american", "western"]:
                frame = ctk.CTkFrame(self.inspector_scroll, fg_color="transparent")
                frame.pack(fill="x", pady=1)
                lbl_name = ctk.CTkLabel(
                    frame, text=tg + ":", font=ctk.CTkFont(size=11),
                    text_color=Theme.TEXT_SECONDARY, width=110, anchor="w"
                )
                lbl_name.pack(side="left")
                lbl_val = ctk.CTkLabel(
                    frame, text="—", font=ctk.CTkFont(size=11),
                    text_color=Theme.TEXT_PRIMARY, anchor="w"
                )
                lbl_val.pack(side="left", fill="x", expand=True)
                self._tech_labels[tg] = lbl_val

        # ── Status Bar ──────────────────────────────────────────
        def _build_status_bar(self):
            """Build the bottom status bar with progress and timing."""
            self.status_frame = ctk.CTkFrame(
                self, height=32, corner_radius=0, fg_color=Theme.BG_DARK
            )
            self.status_frame.pack(fill="x", side="bottom")
            self.status_frame.pack_propagate(False)

            self.status_frame.grid_columnconfigure(1, weight=1)

            # Status icon
            self.status_icon = ctk.CTkLabel(
                self.status_frame, text="●", font=ctk.CTkFont(size=10),
                text_color=Theme.ACCENT_SUCCESS
            )
            self.status_icon.grid(row=0, column=0, padx=(8, 2), pady=4)

            self.status_label = ctk.CTkLabel(
                self.status_frame, text="Ready",
                font=ctk.CTkFont(size=11), text_color=Theme.TEXT_SECONDARY
            )
            self.status_label.grid(row=0, column=1, sticky="w", padx=4, pady=4)

            self.progress_bar = ctk.CTkProgressBar(
                self.status_frame, width=250, height=8,
                progress_color=Theme.ACCENT_PRIMARY,
                fg_color=Theme.PROGRESS_BG
            )
            self.progress_bar.grid(row=0, column=2, padx=8, pady=4)
            self.progress_bar.set(0)

            self.time_label = ctk.CTkLabel(
                self.status_frame, text="0.0s",
                font=ctk.CTkFont(size=11), text_color=Theme.TEXT_TERTIARY
            )
            self.time_label.grid(row=0, column=3, padx=8, pady=4)

            self.phase_label = ctk.CTkLabel(
                self.status_frame, text="",
                font=ctk.CTkFont(size=11), text_color=Theme.TEXT_TERTIARY
            )
            self.phase_label.grid(row=0, column=4, padx=8, pady=4)

        # ── Helper Methods for Building UI ──────────────────────
        def _make_entry(self, section, label: str, default: str) -> ctk.CTkEntry:
            """Create a labeled entry field inside a section."""
            frame = ctk.CTkFrame(section.content, fg_color="transparent")
            frame.pack(fill="x", pady=2)

            lbl = ctk.CTkLabel(
                frame, text=label + ":", font=ctk.CTkFont(size=11),
                text_color=Theme.TEXT_SECONDARY, width=90, anchor="w"
            )
            lbl.pack(side="left")

            entry = ctk.CTkEntry(
                frame, height=28, font=ctk.CTkFont(size=12),
                fg_color=Theme.BG_LIGHT, border_color=Theme.BORDER,
                text_color=Theme.TEXT_PRIMARY
            )
            entry.pack(side="left", fill="x", expand=True, padx=(4, 0))
            entry.insert(0, default)
            return entry

        def _make_option(self, parent, label: str, values: list, default: str) -> ctk.CTkOptionMenu:
            """Create a labeled option menu."""
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            frame.pack(fill="x", pady=2)

            lbl = ctk.CTkLabel(
                frame, text=label, font=ctk.CTkFont(size=11),
                text_color=Theme.TEXT_SECONDARY, width=80, anchor="w"
            )
            lbl.pack(side="left")

            menu = ctk.CTkOptionMenu(
                frame, values=values, height=28, font=ctk.CTkFont(size=12),
                fg_color=Theme.BG_LIGHT, button_color=Theme.ACCENT_PRIMARY,
                button_hover_color=Theme.ACCENT_PRIMARY_HOVER,
                text_color=Theme.TEXT_PRIMARY
            )
            menu.pack(side="left", fill="x", expand=True, padx=(4, 0))
            menu.set(default)
            return menu

        def _make_checkbox(self, parent, text: str, default: bool) -> ctk.CTkCheckBox:
            """Create a styled checkbox."""
            chk = ctk.CTkCheckBox(
                parent, text=text, font=ctk.CTkFont(size=11),
                checkbox_width=20, checkbox_height=20,
                fg_color=Theme.ACCENT_PRIMARY, hover_color=Theme.ACCENT_PRIMARY_HOVER,
                text_color=Theme.TEXT_SECONDARY, border_color=Theme.BORDER_LIGHT
            )
            chk.pack(anchor="w", padx=4, pady=2)
            if default:
                chk.select()
            return chk

        def _add_inspector_header(self, text: str):
            """Add a section header to the inspector panel."""
            label = ctk.CTkLabel(
                self.inspector_scroll, text=text,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=Theme.TEXT_ACCENT
            )
            label.pack(anchor="w", padx=4, pady=(12, 2))

            sep = ctk.CTkFrame(self.inspector_scroll, height=1, fg_color=Theme.BORDER)
            sep.pack(fill="x", padx=4, pady=2)

        # ── Tab Switching ───────────────────────────────────────
        def _switch_tab(self, tab_name: str):
            """Switch viewport tab and update button styling."""
            self._current_tab = tab_name
            for name, btn in self.tab_buttons.items():
                if name == tab_name:
                    btn.configure(
                        fg_color=Theme.TAB_ACTIVE,
                        text_color=Theme.TEXT_ON_ACCENT,
                        font=ctk.CTkFont(size=11, weight="bold")
                    )
                else:
                    btn.configure(
                        fg_color=Theme.TAB_INACTIVE,
                        text_color=Theme.TEXT_SECONDARY,
                        font=ctk.CTkFont(size=11, weight="normal")
                    )

            self._show_preview(tab_name)

        def _show_preview(self, tab_name: str):
            """Display the appropriate map preview based on selected tab."""
            key_map = {
                "🗺️ Heightmap": "heightmap",
                "🏔️ Terrain": "terrain",
                "🌊 Rivers": "rivers",
                "🗺️ Provinces": "provinces",
                "🎨 Watercolor": "watercolor",
                "📊 Analytics": "analytics",
            }
            key = key_map.get(tab_name, "heightmap")

            if key in self._preview_images and self._preview_images[key] is not None:
                self.viewport_label.configure(image=self._preview_images[key], text="")
            elif key == "analytics" and self.analytics is not None:
                self.viewport_label.configure(
                    text="📊 Analytics dashboard generated.\nClick 'Dashboard' button to open in browser.",
                    image=""
                )
            else:
                self.viewport_label.configure(
                    text=f"🌍 Generate a world to see the {key} preview",
                    image=""
                )

        # ── Zoom Controls ───────────────────────────────────────
        def _zoom_in(self):
            pass  # Future: scale the preview image

        def _zoom_out(self):
            pass

        def _zoom_fit(self):
            pass

        # ── Map Size Quick Set ──────────────────────────────────
        def _set_map_size(self, w, h):
            self.config.map_width = w
            self.config.map_height = h
            self.status_label.configure(text=f"Map size set to {w}×{h}")

        # ── Colourmap Change ────────────────────────────────────
        def _on_colourmap_change(self, name: str):
            self.config.colourmap_name = name

        # ── Heightmap Import (Drag & Drop) ──────────────────────
        def _on_heightmap_import(self, path: str):
            """Handle imported heightmap file path."""
            self.config.imported_heightmap_path = path
            self.status_label.configure(text=f"Heightmap imported: {os.path.basename(path)}")

        def _apply_imported_heightmap(self):
            """Apply the imported heightmap to the viewport and engine."""
            if not self.config.imported_heightmap_path:
                messagebox.showwarning("No File", "No heightmap file selected.\nDrag & drop or click the drop zone first.")
                return

            path = self.config.imported_heightmap_path
            if not os.path.exists(path):
                messagebox.showerror("File Not Found", f"File not found:\n{path}")
                return

            try:
                from PIL import Image as PILImage
                img = PILImage.open(path)
                img_array = np.array(img)

                # Convert to grayscale if needed
                if len(img_array.shape) == 3:
                    img_array = np.mean(img_array[:, :, :3], axis=2)

                # Normalize to [-1, 1] range for engine
                img_array = img_array.astype(np.float64) / 255.0
                img_array = img_array * 2.0 - 1.0

                self.heightmap = img_array
                self.config.map_width = img_array.shape[1]
                self.config.map_height = img_array.shape[0]

                # Update map info overlay
                self.map_info_label.configure(
                    text=f"Map: Imported\nSize: {img_array.shape[1]}×{img_array.shape[0]}\nProvinces: —"
                )

                # Generate preview
                self._generate_previews()
                self._show_preview("🗺️ Heightmap")

                self.status_label.configure(
                    text=f"Heightmap applied: {os.path.basename(path)} ({img_array.shape[1]}×{img_array.shape[0]})"
                )

            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import heightmap:\n{str(e)}")

        def _clear_imported_heightmap(self):
            """Clear the imported heightmap."""
            self.config.imported_heightmap_path = ""
            self.drop_zone.path_label.configure(text="No file selected", text_color=Theme.TEXT_TERTIARY)
            self.status_label.configure(text="Imported heightmap cleared")

        # ── Read Config from GUI ────────────────────────────────
        def _read_config(self):
            """Read GUI values into config."""
            try:
                self.config.mod_name = self.entry_mod_name.get()
                self.config.seed = int(self.entry_seed.get())
                self.config.province_count = self.slider_provinces.get()
                self.config.land_percentage = self.slider_land_pct.get()
                self.config.map_style = self.opt_map_style.get()

                # Noise
                self.config.noise_octaves = self._noise_sliders["Octaves"].get()
                self.config.noise_persistence = self._noise_sliders["Persistence"].get() / 100.0
                self.config.noise_lacunarity = self._noise_sliders["Lacunarity"].get() / 100.0
                self.config.noise_scale = self._noise_sliders["Scale"].get() / 10.0
                self.config.domain_warp_strength = self._noise_sliders["Domain Warp"].get() / 100.0
                self.config.ridge_exponent = self._noise_sliders["Ridge Exp"].get() / 100.0

                # Advanced
                self.config.enable_tectonic_plates = self.chk_tectonic.get()
                self.config.enable_hydraulic_erosion = self.chk_erosion.get()
                self.config.enable_impact_craters = self.chk_craters.get()
                self.config.num_craters = self.slider_craters.get()
                self.config.crater_radius_min = self.slider_crater_min.get()
                self.config.crater_radius_max = self.slider_crater_max.get()
                self.config.crater_pattern = self.opt_crater_pattern.get()

                # Climate
                self.config.enable_climate_generation = self.chk_climate.get()
                self.config.temperature_offset = self.slider_temp_offset.get() / 10.0
                self.config.rainfall_multiplier = self.slider_rain_mult.get() / 100.0

                # Dynamics
                self.config.hindu_dominance = self.slider_hindu.get() / 100.0
                self.config.pagan_strength = self.slider_pagan.get() / 100.0
                self.config.european_weakness = self.slider_euro_weak.get() / 100.0
                self.config.african_advancement = self.slider_african_adv.get() / 100.0
                self.config.asian_advancement = self.slider_asian_adv.get() / 100.0
                self.config.enable_celestial_directorate = self.chk_directorate.get()

                # Display
                self.config.colourmap_name = self.colourmap_selector.get()
                self.config.show_contour_lines = self.chk_contours.get()
                self.config.show_rivers_overlay = self.chk_rivers_overlay.get()
                self.config.show_province_borders = self.chk_province_borders.get()

                # Export
                self.config.output_dir = self.entry_output.get()
                self.config.export_flags = self.chk_export_flags.get()
                self.config.export_history = self.chk_export_history.get()
                self.config.export_common = self.chk_export_common.get()
                self.config.export_events = self.chk_export_events.get()
                self.config.export_missions = self.chk_export_missions.get()
                self.config.export_localisation = self.chk_export_localisation.get()

            except (ValueError, AttributeError) as e:
                print(f"[WGS] Config read warning: {e}")

        # ── Generate World ──────────────────────────────────────
        def _on_generate(self):
            """Start world generation in a background thread."""
            if self.gen_state.state == GenerationState.generating:
                return

            self._read_config()
            self.gen_state.start()
            self.btn_generate.configure(state="disabled", text="⏳ Generating...")

            thread = threading.Thread(target=self._generate_worker, daemon=True)
            thread.start()

        def _generate_worker(self):
            """Background worker for world generation."""
            try:
                from eu4_wgs_v8.engine import MapConfig, MapGenerationEngine, ProvinceGenerator, RiverGenerator, TerrainClassifier, NormalMapGenerator, WatercolorGenerator
                from eu4_wgs_v8.analytics import HeightmapAnalyzer
                from eu4_wgs_v8.content import CountryGenerator, CelestialDirectorate, TradeGenerator, DiplomacyGenerator

                cfg = self.config

                # Phase 1: Heightmap (or use imported)
                if cfg.imported_heightmap_path and self.heightmap is not None:
                    self.gen_state.update(0.10, "Using imported heightmap...", "import")
                else:
                    self.gen_state.update(0.05, "Generating heightmap...", "terrain")
                    map_config = MapConfig(
                        width=cfg.map_width, height=cfg.map_height,
                        seed=cfg.seed, land_percentage=cfg.land_percentage,
                        noise_scale=cfg.noise_scale,
                        noise_octaves=cfg.noise_octaves,
                        noise_persistence=cfg.noise_persistence,
                        noise_lacunarity=cfg.noise_lacunarity,
                        domain_warp_strength=cfg.domain_warp_strength,
                        ridge_exponent=cfg.ridge_exponent,
                        map_style=cfg.map_style,
                    )
                    engine = MapGenerationEngine(map_config)
                    self.heightmap, _land_mask = engine.generate_complete_heightmap(
                        apply_tectonic=cfg.enable_tectonic_plates,
                        apply_erosion=cfg.enable_hydraulic_erosion,
                        apply_craters=cfg.enable_impact_craters,
                        num_craters=cfg.num_craters,
                    )

                # Phase 2: Provinces
                self.gen_state.update(0.25, "Generating provinces...", "province")
                prov_gen = ProvinceGenerator(width=cfg.map_width, height=cfg.map_height)
                self.province_map, self.province_info_list, _micro = prov_gen.generate_provinces(
                    self.heightmap,
                    np.ones_like(self.heightmap, dtype=bool) if cfg.imported_heightmap_path else _land_mask,
                    requested_provinces=cfg.province_count
                )

                # Phase 3: Rivers
                self.gen_state.update(0.40, "Generating rivers...", "river")
                river_gen = RiverGenerator(self.heightmap)
                self.rivers_bmp = river_gen.generate_rivers()

                # Phase 4: Terrain
                self.gen_state.update(0.50, "Classifying terrain...", "terrain_classify")
                terrain_cls = TerrainClassifier(self.heightmap)
                self.terrain_bmp = terrain_cls.generate_terrain_bmp()

                # Phase 5: Normal Map
                self.gen_state.update(0.55, "Generating normal map...", "normal")
                normal_gen = NormalMapGenerator(self.heightmap)
                self.normal_map = normal_gen.generate()

                # Phase 6: Countries
                self.gen_state.update(0.60, "Generating countries...", "country")
                country_gen = CountryGenerator(seed=cfg.seed)
                num_countries = max(20, cfg.province_count // 15)
                self.country_list = []
                for i in range(num_countries):
                    country = country_gen.generate_country(index=i)
                    self.country_list.append(country)

                # Phase 7: Analytics
                self.gen_state.update(0.75, "Computing analytics...", "analytics")
                analyzer = HeightmapAnalyzer(self.heightmap, self.province_info_list)
                self.analytics = analyzer.generate_full_analytics()

                # Phase 8: Previews
                self.gen_state.update(0.85, "Generating previews...", "preview")
                self._generate_previews()

                # Update inspector
                self.gen_state.update(0.95, "Updating UI...", "ui")
                self.after(0, self._update_inspector_from_analytics)

                self.gen_state.finish("World generation complete!")
                self.after(0, lambda: self.btn_generate.configure(state="normal", text="⚡ Generate World"))
                self.after(0, self._show_latest_preview)

            except Exception as e:
                self.gen_state.fail(f"Error: {str(e)}")
                self.after(0, lambda: self.btn_generate.configure(state="normal", text="⚡ Generate World"))
                import traceback
                traceback.print_exc()

        def _generate_previews(self):
            """Generate PIL images for viewport display."""
            try:
                if self.heightmap is not None:
                    hm_display = ((self.heightmap + 1) / 2 * 255).clip(0, 255).astype(np.uint8)
                    if PIL_AVAILABLE:
                        img = Image.fromarray(hm_display, mode='L')
                        img = img.resize((800, 400), Image.LANCZOS)
                        self._preview_images["heightmap"] = ctk.CTkImage(light_image=img, dark_image=img, size=(800, 400))

                if self.terrain_bmp is not None:
                    if PIL_AVAILABLE:
                        img = Image.fromarray(self.terrain_bmp)
                        img = img.resize((800, 400), Image.LANCZOS)
                        self._preview_images["terrain"] = ctk.CTkImage(light_image=img, dark_image=img, size=(800, 400))

                if self.rivers_bmp is not None:
                    if PIL_AVAILABLE:
                        img = Image.fromarray(self.rivers_bmp)
                        img = img.resize((800, 400), Image.LANCZOS)
                        self._preview_images["rivers"] = ctk.CTkImage(light_image=img, dark_image=img, size=(800, 400))

                if self.province_map is not None:
                    if PIL_AVAILABLE:
                        img = Image.fromarray(self.province_map)
                        img = img.resize((800, 400), Image.LANCZOS)
                        self._preview_images["provinces"] = ctk.CTkImage(light_image=img, dark_image=img, size=(800, 400))

                if self.watercolor_bmp is not None:
                    if PIL_AVAILABLE:
                        img = Image.fromarray(self.watercolor_bmp)
                        img = img.resize((800, 400), Image.LANCZOS)
                        self._preview_images["watercolor"] = ctk.CTkImage(light_image=img, dark_image=img, size=(800, 400))

                # Update map info overlay
                cfg = self.config
                self.map_info_label.configure(
                    text=f"Map: {cfg.map_width}×{cfg.map_height}\n"
                         f"Provinces: {len(self.province_info_list)}\n"
                         f"Seed: {cfg.seed}"
                )

            except Exception as e:
                print(f"[WGS] Preview generation warning: {e}")

        def _update_inspector_from_analytics(self):
            """Populate the inspector panel with analytics data."""
            if self.analytics is None:
                return

            a = self.analytics

            # World statistics
            stats_map = {
                "Total Provinces": getattr(a, 'total_provinces', '—'),
                "Land Provinces": getattr(a, 'land_provinces', '—'),
                "Sea Provinces": getattr(a, 'sea_provinces', '—'),
                "Total Countries": len(self.country_list) if self.country_list else '—',
                "Advanced Countries": sum(1 for c in (self.country_list or []) if getattr(c, 'is_advanced', False)),
                "Primitive Countries": sum(1 for c in (self.country_list or []) if not getattr(c, 'is_advanced', False)),
                "Hindu Provinces": getattr(a, 'hindu_provinces', '—'),
                "Pagan Provinces": getattr(a, 'pagan_provinces', '—'),
                "Abrahamic Provinces": getattr(a, 'abrahamic_provinces', '—'),
                "Avg Development": f"{getattr(a, 'avg_development', 0):.1f}" if hasattr(a, 'avg_development') else '—',
                "Avg Tax": f"{getattr(a, 'avg_tax', 0):.1f}" if hasattr(a, 'avg_tax') else '—',
                "Avg Production": f"{getattr(a, 'avg_production', 0):.1f}" if hasattr(a, 'avg_production') else '—',
                "Avg Manpower": f"{getattr(a, 'avg_manpower', 0):.1f}" if hasattr(a, 'avg_manpower') else '—',
            }
            for field, val in stats_map.items():
                if field in self._world_stat_labels:
                    self._world_stat_labels[field].configure(text=str(val))

            # Tech groups
            if hasattr(a, 'tech_group_distribution') and a.tech_group_distribution:
                for tg, count in a.tech_group_distribution.items():
                    if tg in self._tech_labels:
                        self._tech_labels[tg].configure(text=str(count))

        def _show_latest_preview(self):
            """Show the most recent preview in the viewport."""
            self._show_preview("🗺️ Heightmap")

        # ── Export Mod ──────────────────────────────────────────
        def _on_export(self):
            """Export the generated world as a complete EU4 mod."""
            if self.heightmap is None:
                messagebox.showwarning("No World", "Generate a world first before exporting.")
                return

            self._read_config()
            thread = threading.Thread(target=self._export_worker, daemon=True)
            thread.start()

        def _export_worker(self):
            """Background worker for mod export."""
            try:
                from eu4_wgs_v8.export import MasterExportOrchestrator
                from eu4_wgs_v8.content import CountryGenerator, CelestialDirectorate, TradeGenerator, DiplomacyGenerator, ReligionGenerator, CultureGenerator

                cfg = self.config
                self.gen_state.start()
                self.gen_state.update(0.1, "Exporting mod files...", "export")

                orchestrator = MasterExportOrchestrator(
                    mod_name=cfg.mod_name,
                    output_dir=cfg.output_dir,
                    heightmap=self.heightmap,
                    province_map=self.province_map,
                    province_info_list=self.province_info_list,
                    country_list=self.country_list,
                    terrain_bmp=self.terrain_bmp,
                    rivers_bmp=self.rivers_bmp,
                    normal_map=self.normal_map,
                    map_width=cfg.map_width,
                    map_height=cfg.map_height,
                )

                self.gen_state.update(0.5, "Writing mod structure...", "write")
                result = orchestrator.export_complete_mod()

                self.gen_state.finish(f"Mod exported to {cfg.output_dir}/{cfg.mod_name}")
                self.after(0, lambda: messagebox.showinfo("Export Complete",
                    f"Mod exported successfully!\n\n"
                    f"Path: {cfg.output_dir}/{cfg.mod_name}\n\n"
                    f"Directories: {len(result.get('directories_created', []))}\n"
                    f"Files written: {len(result.get('files_written', []))}"))

            except Exception as e:
                err_msg = str(e)
                self.gen_state.fail(f"Export error: {err_msg}")
                import traceback
                traceback.print_exc()
                self.after(0, lambda msg=err_msg: messagebox.showerror("Export Error", msg))

        # ── Open Dashboard ──────────────────────────────────────
        def _on_open_dashboard(self):
            """Generate and open the analytics dashboard in a browser."""
            if self.heightmap is None:
                messagebox.showwarning("No World", "Generate a world first.")
                return

            try:
                from eu4_wgs_v8.analytics import generate_dashboard_from_analytics
                import webbrowser

                output_dir = os.path.join(self.config.output_dir, self.config.mod_name, "dashboard")
                os.makedirs(output_dir, exist_ok=True)

                prov_data = []
                for p in self.province_info_list[:500]:
                    pdict = {}
                    if hasattr(p, '__dict__'):
                        pdict = {k: v for k, v in p.__dict__.items()}
                    elif isinstance(p, dict):
                        pdict = p
                    prov_data.append(pdict)

                path = generate_dashboard_from_analytics(
                    analytics=self.analytics,
                    heightmap=self.heightmap,
                    province_data=prov_data,
                    output_dir=output_dir,
                    world_name=self.config.mod_name,
                    seed=self.config.seed,
                    map_width=self.config.map_width,
                    map_height=self.config.map_height,
                )

                webbrowser.open(f"file://{os.path.abspath(path)}")
                self.status_label.configure(text=f"Dashboard opened: {path}")

            except Exception as e:
                messagebox.showerror("Dashboard Error", str(e))
                import traceback
                traceback.print_exc()

        # ── Reset ───────────────────────────────────────────────
        def _on_reset(self):
            """Reset the application to initial state."""
            self.heightmap = None
            self.province_map = None
            self.terrain_bmp = None
            self.rivers_bmp = None
            self.normal_map = None
            self.watercolor_bmp = None
            self.province_info_list = []
            self.country_list = []
            self.analytics = None
            self._preview_images = {}

            self.viewport_label.configure(
                text="🌍  Generate a world to see the map preview\n\n"
                     "Configure settings on the left, then click ⚡ Generate World",
                image=""
            )
            self.map_info_label.configure(text="Map: —\nSize: —\nProvinces: —")
            self.progress_bar.set(0)
            self.status_label.configure(text="Reset — Ready")
            self.gen_state = GenerationState()

        # ── Browse Output ───────────────────────────────────────
        def _on_browse_output(self):
            path = filedialog.askdirectory(title="Select Output Directory")
            if path:
                self.entry_output.delete(0, "end")
                self.entry_output.insert(0, path)

        # ── Inspector Tab Change ────────────────────────────────
        def _on_inspector_tab_change(self, value):
            pass  # Future: switch between province/country/world inspector

        # ── Status Update Loop ──────────────────────────────────
        def _status_loop(self):
            """Periodic UI update for generation progress."""
            if self.gen_state.state == GenerationState.generating:
                self.progress_bar.set(self.gen_state.progress)
                phase_text = f"{self.gen_state.phase}: " if self.gen_state.phase else ""
                self.status_label.configure(
                    text=f"{phase_text}{self.gen_state.message} ({self.gen_state.progress*100:.0f}%)"
                )
                self.time_label.configure(text=f"{self.gen_state.elapsed:.1f}s")
                self.status_icon.configure(text="◉", text_color=Theme.ACCENT_PRIMARY)
                self.phase_label.configure(text=self.gen_state.phase.upper() if self.gen_state.phase else "")
            elif self.gen_state.state == GenerationState.complete:
                self.progress_bar.set(1.0)
                self.status_label.configure(text=self.gen_state.message)
                self.time_label.configure(text=f"{self.gen_state.elapsed:.1f}s")
                self.status_icon.configure(text="●", text_color=Theme.ACCENT_SUCCESS)
                self.phase_label.configure(text="COMPLETE")
            elif self.gen_state.state == GenerationState.error:
                self.progress_bar.set(0)
                self.status_label.configure(text=f"❌ {self.gen_state.message}")
                self.status_icon.configure(text="●", text_color=Theme.ACCENT_DANGER)
                self.phase_label.configure(text="ERROR")
            else:
                self.status_icon.configure(text="●", text_color=Theme.TEXT_TERTIARY)

            self.after(200, self._status_loop)

        def run(self):
            """Start the application main loop."""
            self.mainloop()


# ═══════════════════════════════════════════════════════════════
#  FALLBACK: HEADLESS MODE (when no display available)
# ═══════════════════════════════════════════════════════════════

def run_headless(config: GUIConfig = None):
    """Run the generation pipeline without a GUI (for testing/CI)."""
    if config is None:
        config = GUIConfig()

    from eu4_wgs_v8.engine import MapConfig, MapGenerationEngine, ProvinceGenerator, RiverGenerator, TerrainClassifier
    from eu4_wgs_v8.analytics import HeightmapAnalyzer, generate_dashboard_from_analytics
    from eu4_wgs_v8.content import CountryGenerator, CelestialDirectorate
    from eu4_wgs_v8.export import MasterExportOrchestrator

    print(f"\n{'='*60}")
    print(f"  EU4 WGS V8 — Headless Generation Pipeline")
    print(f"  Mod: {config.mod_name} | Seed: {config.seed}")
    print(f"{'='*60}\n")

    # Phase 1: Heightmap
    print("[1/8] Generating heightmap...")
    t0 = time.time()
    map_config = MapConfig(
        width=config.map_width, height=config.map_height,
        seed=config.seed, land_percentage=config.land_percentage,
        noise_scale=config.noise_scale,
        noise_octaves=config.noise_octaves,
        noise_persistence=config.noise_persistence,
        noise_lacunarity=config.noise_lacunarity,
        domain_warp_strength=config.domain_warp_strength,
        ridge_exponent=config.ridge_exponent,
        map_style=config.map_style,
    )
    engine = MapGenerationEngine(map_config)
    heightmap, _land_mask = engine.generate_complete_heightmap(
        apply_tectonic=config.enable_tectonic_plates,
        apply_erosion=config.enable_hydraulic_erosion,
        apply_craters=config.enable_impact_craters,
        num_craters=config.num_craters,
    )
    print(f"  ✓ Heightmap generated: {heightmap.shape} in {time.time()-t0:.1f}s")
    print(f"    Land: {(heightmap>0).sum()}/{heightmap.size} ({(heightmap>0).sum()/heightmap.size*100:.1f}%)")

    # Phase 2: Provinces
    print("\n[2/8] Generating provinces...")
    t0 = time.time()
    prov_gen = ProvinceGenerator(width=config.map_width, height=config.map_height)
    province_map, province_info_list, _micro = prov_gen.generate_provinces(heightmap, _land_mask, requested_provinces=config.province_count)
    print(f"  ✓ {len(province_info_list)} provinces in {time.time()-t0:.1f}s")

    # Phase 3: Rivers
    print("\n[3/8] Generating rivers...")
    t0 = time.time()
    river_gen = RiverGenerator(heightmap)
    rivers_bmp = river_gen.generate_rivers()
    print(f"  ✓ Rivers generated in {time.time()-t0:.1f}s")

    # Phase 4: Terrain
    print("\n[4/8] Classifying terrain...")
    t0 = time.time()
    terrain_cls = TerrainClassifier(heightmap)
    terrain_bmp = terrain_cls.generate_terrain_bmp()
    print(f"  ✓ Terrain classified in {time.time()-t0:.1f}s")

    # Phase 5: Countries
    print("\n[5/8] Generating countries...")
    t0 = time.time()
    country_gen = CountryGenerator(seed=config.seed)
    num_countries = max(20, config.province_count // 15)
    country_list = [country_gen.generate_country(index=i) for i in range(num_countries)]
    print(f"  ✓ {len(country_list)} countries in {time.time()-t0:.1f}s")

    # Phase 6: Analytics
    print("\n[6/8] Computing analytics...")
    t0 = time.time()
    analyzer = HeightmapAnalyzer(heightmap, province_info_list)
    analytics = analyzer.generate_full_analytics()
    print(f"  ✓ Analytics computed in {time.time()-t0:.1f}s")

    # Phase 7: Dashboard
    print("\n[7/8] Generating analytics dashboard...")
    t0 = time.time()
    output_dir = os.path.join(config.output_dir, config.mod_name, "dashboard")
    os.makedirs(output_dir, exist_ok=True)

    prov_data = []
    for p in province_info_list[:500]:
        if hasattr(p, '__dict__'):
            prov_data.append({k: v for k, v in p.__dict__.items()})
        elif isinstance(p, dict):
            prov_data.append(p)

    dashboard_path = generate_dashboard_from_analytics(
        analytics=analytics,
        heightmap=heightmap,
        province_data=prov_data,
        output_dir=output_dir,
        world_name=config.mod_name,
        seed=config.seed,
        map_width=config.map_width,
        map_height=config.map_height,
    )
    print(f"  ✓ Dashboard: {dashboard_path} in {time.time()-t0:.1f}s")

    # Phase 8: Export
    print("\n[8/8] Exporting mod files...")
    t0 = time.time()
    orchestrator = MasterExportOrchestrator(
        mod_name=config.mod_name,
        output_dir=config.output_dir,
        heightmap=heightmap,
        province_map=province_map,
        province_info_list=province_info_list,
        country_list=country_list,
        terrain_bmp=terrain_bmp,
        rivers_bmp=rivers_bmp,
        normal_map=None,
        map_width=config.map_width,
        map_height=config.map_height,
    )
    result = orchestrator.export_complete_mod()
    print(f"  ✓ Mod exported in {time.time()-t0:.1f}s")
    print(f"    Directories: {len(result.get('directories_created', []))}")
    print(f"    Files: {len(result.get('files_written', []))}")

    print(f"\n{'='*60}")
    print(f"  ✅ COMPLETE: {config.mod_name}")
    print(f"  Dashboard: {dashboard_path}")
    print(f"  Mod: {config.output_dir}/{config.mod_name}")
    print(f"{'='*60}\n")

    return {
        "heightmap": heightmap,
        "province_map": province_map,
        "province_info_list": province_info_list,
        "country_list": country_list,
        "analytics": analytics,
        "dashboard_path": dashboard_path,
        "export_result": result,
    }


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main():
    """Main entry point — launches GUI if available, headless otherwise."""
    if CTk_AVAILABLE:
        try:
            app = WorldGeneratorStudio()
            app.run()
        except tk.TclError:
            print("[WGS] No display available, running headless...")
            run_headless()
    else:
        print("[WGS] CustomTkinter not available, running headless...")
        run_headless()


if __name__ == "__main__":
    main()
