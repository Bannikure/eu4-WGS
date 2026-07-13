"""UI – Professional CustomTkinter Interface."""

from __future__ import annotations

import logging
import traceback
from threading import Thread
from typing import Any

import customtkinter as ctk  # type: ignore[import-untyped]
from tkinter import messagebox

from .exporter import export_complete_eu4_mod
from .map_engine import MapGenerationEngine
from .map_writers import calculate_province_positions
from .render import generate_rivers, render_photorealistic_3d_viewport

logger = logging.getLogger(__name__)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class EU4GeneratorUI(ctk.CTk):
    """Professional CustomTkinter UI for the EU4 World Generator Studio v4.1."""

    def __init__(self) -> None:
        super().__init__()
        self.title("EU4 World Generator Studio v4.1")
        self.geometry("1000x700")
        self.generation_data: dict[str, Any] | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        ctk.CTkLabel(self, text="EU4 Total Conversion World Generator", font=("Arial", 24, "bold")).pack(pady=10)

        settings_frame = ctk.CTkFrame(self)
        settings_frame.pack(fill="both", padx=10, pady=10)

        ctk.CTkLabel(settings_frame, text="Map Layout:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.layout_var = ctk.StringVar(value="continents_islands")
        ctk.CTkOptionMenu(settings_frame, variable=self.layout_var,
                          values=["pangea", "continents", "archipelago", "continents_islands"]
                          ).grid(row=0, column=1, padx=5, pady=4)

        ctk.CTkLabel(settings_frame, text="Number of Provinces:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.province_var = ctk.StringVar(value="500")
        ctk.CTkEntry(settings_frame, textvariable=self.province_var, width=100).grid(row=1, column=1, padx=5, pady=4)

        ctk.CTkLabel(settings_frame, text="Mod Name:").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        self.mod_name_var = ctk.StringVar(value="MyWorld")
        ctk.CTkEntry(settings_frame, textvariable=self.mod_name_var).grid(row=2, column=1, padx=5, pady=4)

        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(button_frame, text="Generate World",  command=self.generate_world).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Export Mod",      command=self.export_mod    ).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Preview 3D Map",  command=self.preview_map   ).pack(side="left", padx=5)

        self.status_var = ctk.StringVar(value="Ready.")
        ctk.CTkLabel(self, textvariable=self.status_var, text_color="cyan").pack(pady=5)
        self.progress = ctk.CTkProgressBar(self, width=400)
        self.progress.pack(pady=10)
        self.progress.set(0)

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)
        self.update()

    def _set_progress(self, fraction: float) -> None:
        self.progress.set(fraction)
        self.update()

    def generate_world(self) -> None:
        Thread(target=self._generate_world_thread, daemon=True).start()

    def _generate_world_thread(self) -> None:
        try:
            self._set_status("Generating heightmap…")
            self._set_progress(0.1)
            layout = self.layout_var.get()
            heightmap, land_mask = MapGenerationEngine.build_realistic_noise_heightmap(layout)

            self._set_status("Tessellating provinces…")
            self._set_progress(0.3)
            province_count = int(self.province_var.get())
            provinces_bmp, unique_colors, _is_micro, sea_mask = (
                MapGenerationEngine.generate_voronoi_provinces(land_mask, province_count)
            )

            self._set_status("Computing province positions…")
            self._set_progress(0.5)
            positions = calculate_province_positions(provinces_bmp, unique_colors)

            self._set_status("Simulating rivers…")
            self._set_progress(0.65)
            river_map = generate_rivers(heightmap, land_mask, min_river_flow=800)

            self._set_status("Building province telemetry…")
            self._set_progress(0.8)
            province_telemetry = [
                {"id": p_id, "center_x": pos["bc_x"], "center_y": pos["bc_y"]}
                for p_id, pos in positions.items()
            ]
            island_ids = [p_id for p_id, pos in positions.items() if 300 <= pos["bc_y"] <= 1700]

            self.generation_data = {
                "heightmap": heightmap, "land_mask": land_mask,
                "provinces_bmp": provinces_bmp, "unique_colors": unique_colors,
                "sea_mask": sea_mask, "rivers": river_map,
                "positions": positions, "province_telemetry": province_telemetry,
                "island_ids": island_ids, "max_provinces": province_count,
            }
            self._set_progress(1.0)
            self._set_status(f"World generated — {province_count} provinces.")
        except Exception:
            logger.exception("World generation failed")
            self._set_status(f"Generation failed: {traceback.format_exc().splitlines()[-1]}")

    def export_mod(self) -> None:
        if self.generation_data is None:
            messagebox.showwarning("No world", "Generate a world first.")
            return
        Thread(target=self._export_mod_thread, daemon=True).start()

    def _export_mod_thread(self) -> None:
        try:
            self._set_status("Exporting mod…")
            mod_name = self.mod_name_var.get().strip() or "MyWorld"
            export_complete_eu4_mod(mod_name, mod_name.replace(" ", "_"), self.generation_data)  # type: ignore[arg-type]
            self._set_status(f"Mod '{mod_name}' exported successfully.")
        except Exception:
            logger.exception("Mod export failed")
            self._set_status(f"Export failed: {traceback.format_exc().splitlines()[-1]}")

    def preview_map(self) -> None:
        if self.generation_data is None:
            messagebox.showwarning("No world", "Generate a world first.")
            return
        try:
            render_photorealistic_3d_viewport(self.generation_data["heightmap"])
        except Exception:
            logger.exception("Preview rendering failed")
            self._set_status(f"Preview failed: {traceback.format_exc().splitlines()[-1]}")
