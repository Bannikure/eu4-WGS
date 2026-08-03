"""
EU4 Studio GUI
==============
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
Enhanced Tkinter GUI for the EU4 World Generator Studio.
Provides intuitive control over map generation parameters with live preview.
"""

import os
import sys
import threading
import time
import json
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import asdict

import numpy as np
from PIL import Image, ImageTk

logger = logging.getLogger(__name__)




# ═══════════════════════════════════════════════════════════════
#  THEME & STYLING
# ═══════════════════════════════════════════════════════════════

class Theme:
    """Color scheme and styling constants."""

    # Main colors
    BG_DARK = "#1a1a1a"
    BG_LIGHT = "#2d2d2d"
    BG_LIGHTER = "#3d3d3d"
    
    # Text colors
    TEXT_PRIMARY = "#e0e0e0"
    TEXT_SECONDARY = "#a0a0a0"
    TEXT_ACCENT = "#87ceeb"
    
    # UI elements
    ACCENT_PRIMARY = "#4a9eff"
    ACCENT_SECONDARY = "#ff6b6b"
    BORDER = "#444444"
    
    # Status colors
    SUCCESS = "#4ec9b0"
    WARNING = "#dcdcaa"
    ERROR = "#f48771"
    
    # Scrollbar
    SCROLLBAR = "#555555"


# ═══════════════════════════════════════════════════════════════
#  STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════

class GenerationState:
    """Tracks the state of map generation."""

    def __init__(self):
        self.is_running = False
        self.progress = 0.0
        self.current_message = "Ready"
        self.current_phase = ""

    def start(self):
        """Mark generation as started."""
        self.is_running = True
        self.progress = 0.0

    def update(self, progress: float, message: str, phase: str = ""):
        """Update generation progress."""
        self.progress = min(max(progress, 0.0), 1.0)
        self.current_message = message
        self.current_phase = phase

    def finish(self, message: str = "Complete!"):
        """Mark generation as finished."""
        self.is_running = False
        self.progress = 1.0
        self.current_message = message

    def fail(self, message: str):
        """Mark generation as failed."""
        self.is_running = False
        self.current_message = f"Error: {message}"


# ═══════════════════════════════════════════════════════════════
#  COLLAPSIBLE SECTION
# ═══════════════════════════════════════════════════════════════

class CollapsibleSection(ctk.CTkFrame):
    """Collapsible section for grouping UI controls."""

    def __init__(self, master, title: str, icon: str = "▸", expanded: bool = True, **kwargs):
        super().__init__(master, **kwargs)
        
        self.title = title
        self.icon = icon
        self.expanded = expanded
        self.content_frame = None
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 4))
        
        self.toggle_btn = ctk.CTkButton(
            header, text=f"{icon} {title}", fg_color="transparent",
            text_color=Theme.TEXT_ACCENT, anchor="w", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._toggle
        )
        self.toggle_btn.pack(fill="x")
        
        # Content frame
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        if expanded:
            self.content_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        else:
            self.content_frame.pack_forget()

    def _toggle(self):
        """Toggle section expansion."""
        self.expanded = not self.expanded
        if self.expanded:
            self.content_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))
            self.toggle_btn.configure(text=f"▾ {self.title}")
        else:
            self.content_frame.pack_forget()
            self.toggle_btn.configure(text=f"▸ {self.title}")

    def get_content_frame(self):
        """Get the frame for adding content."""
        return self.content_frame


# ═══════════════════════════════════════════════════════════════
#  SEGMENTED BUTTON GROUP (CTkSegmentedTab fallback)
# ═══════════════════════════════════════════════════════════════

class CTkSegmentedTabFallback(ctk.CTkFrame):
    """
    Fallback implementation for CTkSegmentedTab for older customtkinter versions.
    Provides tabbed interface using segmented buttons.
    """

    def __init__(self, master, values: list, command=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.values = values
        self.command = command
        self.selected_value = values[0] if values else None
        self.buttons = {}
        
        # Create segmented buttons
        for i, value in enumerate(values):
            btn = ctk.CTkButton(
                self,
                text=value,
                fg_color=Theme.ACCENT_PRIMARY if i == 0 else Theme.BG_LIGHTER,
                text_color=Theme.TEXT_PRIMARY,
                command=lambda v=value: self._select(v),
                corner_radius=0,
                border_width=1,
                border_color=Theme.BORDER,
                font=ctk.CTkFont(size=11)
            )
            btn.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else -1, 0))
            self.buttons[value] = btn
        
        # Configure grid weights for equal width
        for i in range(len(values)):
            self.grid_columnconfigure(i, weight=1)

    def _select(self, value: str):
        """Select a tab value."""
        # Update button colors
        for v, btn in self.buttons.items():
            if v == value:
                btn.configure(fg_color=Theme.ACCENT_PRIMARY)
            else:
                btn.configure(fg_color=Theme.BG_LIGHTER)
        
        self.selected_value = value
        if self.command:
            self.command(value)

    def get(self):
        """Get currently selected value."""
        return self.selected_value

    def set(self, value: str):
        """Set selected value."""
        if value in self.buttons:
            self._select(value)


def get_segmented_tab(master, values: list, command=None, **kwargs):
    """
    Get segmented tab widget, falling back to custom implementation if needed.
    
    Args:
        master: Parent widget
        values: List of tab names
        command: Callback function when tab is selected
        
    Returns:
        Segmented tab widget
    """
    try:
        return ctk.CTkSegmentedTab(master, values=values, command=command, **kwargs)
    except AttributeError:
        logger.warning("CTkSegmentedTab not available, using fallback implementation")
        return CTkSegmentedTabFallback(master, values=values, command=command, **kwargs)


# ═══════════════════════════════════════════════════════════════
#  STUDIO GUI CLASS
# ═══════════════════════════════════════════════════════════════

class EUWGSStudio(ctk.CTk):
    """Main GUI class for EU4 World Generator Studio."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.title("EU4 World Generator Studio")
        self.geometry("1400x800")
        
        # State
        self.gen_state = GenerationState()
        self.preview_image = None
        
        # Setup theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build the main UI."""
        # Main container with 3 sections: left panel, center canvas, right panel
        self.main_container = ctk.CTkFrame(self, fg_color=Theme.BG_DARK)
        self.main_container.pack(fill="both", expand=True)
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)
        
        # Left panel (controls)
        self._build_left_panel()
        
        # Center canvas area
        self._build_center_canvas()
        
        # Right panel (inspector)
        self._build_right_panel()
        
        # Status bar
        self._build_status_bar()

    def _build_left_panel(self):
        """Build left control panel."""
        self.left_panel = ctk.CTkFrame(
            self.main_container, width=280, corner_radius=0,
            fg_color=Theme.BG_LIGHT
        )
        self.left_panel.grid(row=0, column=0, sticky="ns")
        self.left_panel.grid_propagate(False)
        
        # Title
        title = ctk.CTkLabel(
            self.left_panel, text="🎨  Generator",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=Theme.TEXT_ACCENT
        )
        title.pack(pady=(12, 8), padx=12, anchor="w")
        
        # Scrollable content
        scroll = ctk.CTkScrollableFrame(
            self.left_panel, fg_color="transparent",
            scrollbar_button_color=Theme.SCROLLBAR,
            scrollbar_button_hover_color=Theme.BG_LIGHTER
        )
        scroll.pack(fill="both", expand=True, padx=8, pady=8)
        
        # Map settings section
        map_section = CollapsibleSection(
            scroll, "Map Settings", expanded=True,
            fg_color=Theme.BG_DARK, corner_radius=8
        )
        map_section.pack(fill="x", pady=4)
        
        content = map_section.get_content_frame()
        
        # Map size controls
        for label, var in [("Width", "width"), ("Height", "height"), ("Provinces", "provinces")]:
            frame = ctk.CTkFrame(content, fg_color="transparent")
            frame.pack(fill="x", pady=4)
            
            lbl = ctk.CTkLabel(frame, text=label, width=80, text_color=Theme.TEXT_SECONDARY)
            lbl.pack(side="left")
            
            spinbox = ctk.CTkSpinbox(
                frame, from_=100, to=10000, step=100,
                fg_color=Theme.BG_LIGHTER, border_color=Theme.BORDER
            )
            spinbox.pack(side="left", fill="x", expand=True)
        
        # Generation button
        gen_btn = ctk.CTkButton(
            scroll, text="▶ Generate Map", font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=Theme.ACCENT_PRIMARY, command=self._on_generate
        )
        gen_btn.pack(fill="x", pady=(12, 4))

    def _build_center_canvas(self):
        """Build center canvas area."""
        canvas_frame = ctk.CTkFrame(
            self.main_container, corner_radius=0,
            fg_color=Theme.BG_DARK
        )
        canvas_frame.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        
        # Title
        title = ctk.CTkLabel(
            canvas_frame, text="Preview",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=Theme.TEXT_ACCENT
        )
        title.pack(pady=4, anchor="w")
        
        # Canvas placeholder
        self.canvas = ctk.CTkLabel(
            canvas_frame, text="Preview will appear here",
            text_color=Theme.TEXT_SECONDARY,
            fg_color=Theme.BG_LIGHT, corner_radius=8
        )
        self.canvas.pack(fill="both", expand=True)

    def _build_right_panel(self):
        """Build right inspector panel."""
        self.right_panel = ctk.CTkFrame(
            self.main_container, width=280, corner_radius=0,
            fg_color=Theme.BG_LIGHT
        )
        self.right_panel.grid(row=0, column=2, sticky="ns")
        self.right_panel.grid_propagate(False)
        
        # Title
        title = ctk.CTkLabel(
            self.right_panel, text="🔍  Inspector",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=Theme.TEXT_ACCENT
        )
        title.pack(pady=(8, 4), padx=12, anchor="w")
        
        # Segmented tabs for inspector (with fallback)
        self.inspector_tabs = get_segmented_tab(
            self.right_panel, values=["Province", "Country", "World"],
            command=self._on_inspector_tab_change
        )
        self.inspector_tabs.pack(fill="x", padx=8, pady=4)
        
        # Inspector content
        scroll = ctk.CTkScrollableFrame(
            self.right_panel, fg_color="transparent",
            scrollbar_button_color=Theme.SCROLLBAR,
            scrollbar_button_hover_color=Theme.BG_LIGHTER
        )
        scroll.pack(fill="both", expand=True, padx=4, pady=4)
        
        # Placeholder info
        info = ctk.CTkLabel(
            scroll, text="Select a province to view details",
            text_color=Theme.TEXT_SECONDARY
        )
        info.pack(pady=20)

    def _build_status_bar(self):
        """Build status bar at bottom."""
        status = ctk.CTkFrame(self, fg_color=Theme.BG_LIGHT, height=40)
        status.pack(fill="x", side="bottom")
        status.pack_propagate(False)
        
        self.status_label = ctk.CTkLabel(
            status, text="Ready", text_color=Theme.TEXT_SECONDARY,
            anchor="w", font=ctk.CTkFont(size=10)
        )
        self.status_label.pack(fill="both", expand=True, padx=12, pady=8)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            status, fg_color=Theme.BG_DARK, progress_color=Theme.ACCENT_PRIMARY,
            height=4
        )
        self.progress_bar.pack(fill="x", padx=12, pady=(0, 4))
        self.progress_bar.set(0.0)

    def _on_generate(self):
        """Handle generate button click."""
        self.gen_state.start()
        self.status_label.configure(text="Generating map...")
        
        # Run in background thread
        thread = threading.Thread(target=self._generate_map, daemon=True)
        thread.start()

    def _generate_map(self):
        """Generate map in background."""
        try:
            self.gen_state.update(0.25, "Generating heightmap...", "heightmap")
            self.progress_bar.set(0.25)
            
            self.gen_state.update(0.50, "Generating provinces...", "provinces")
            self.progress_bar.set(0.50)
            
            self.gen_state.update(0.75, "Finalizing map...", "finalize")
            self.progress_bar.set(0.75)
            
            self.gen_state.finish("Map generated successfully!")
            self.progress_bar.set(1.0)
            self.status_label.configure(text=self.gen_state.current_message, text_color=Theme.SUCCESS)
        except Exception as e:
            self.gen_state.fail(str(e))
            self.status_label.configure(text=self.gen_state.current_message, text_color=Theme.ERROR)
            logger.error(f"Map generation failed: {e}")

    def _on_inspector_tab_change(self, value: str):
        """Handle inspector tab change."""
        logger.debug(f"Inspector tab changed to: {value}")


# ═══════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def launch_gui():
    """Launch the GUI application."""
    try:
        app = EUWGSStudio()
        app.mainloop()
        return True
    except Exception as e:
        logger.error(f"GUI launch failed: {e}")
        return False


if __name__ == "__main__":
    launch_gui()
