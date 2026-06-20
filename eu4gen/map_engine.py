"""
Module A – Procedural Map Generation Engine.

Responsible for heightmap creation and Voronoi-based province generation.
All methods are pure (no side effects) and return numpy arrays.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree  # type: ignore[attr-defined]

from .constants import MAP_WIDTH, MAP_HEIGHT, SEA_LEVEL_THRESHOLD


class MapGenerationEngine:
    """Core procedural map generation using domain-warped fBm and Voronoi tessellation."""

    @staticmethod
    def generate_falloff_mask(
        width: int = MAP_WIDTH,
        height: int = MAP_HEIGHT,
        layout_style: str = "continents_islands",
    ) -> np.ndarray:
        """Return a 2-D float32 array (0.0–1.0) that shapes the macro-geography."""
        y, x = np.ogrid[:height, :width]
        cx, cy = width / 2.0, height / 2.0
        nx = (x - cx) / cx
        ny = (y - cy) / cy
        distance = np.sqrt(nx**2 + ny**2)

        if layout_style == "pangea":
            return np.clip(1.0 - (distance**2), 0, 1).astype(np.float32)
        elif layout_style == "continents":
            wave = 0.5 * (np.cos(nx * np.pi * 2.5) + 1.0)
            return np.clip(wave * (1.0 - ny**4), 0, 1).astype(np.float32)
        elif layout_style == "archipelago":
            return np.full((height, width), 0.45, dtype=np.float32)
        else:  # continents_islands (default)
            wave = 0.5 * (np.cos(nx * np.pi * 2.5) + 1.0)
            return np.clip((wave * 0.8) + 0.15, 0, 1).astype(np.float32)

    @staticmethod
    def build_realistic_noise_heightmap(
        layout_style: str = "continents_islands",
    ) -> tuple[np.ndarray, np.ndarray]:
        """Generate a high-fidelity heightmap via domain warping + fBm + ridge exponentiation.

        Returns:
            ``(heightmap, land_mask)`` – uint8 array and boolean array, both
            shape ``(MAP_HEIGHT, MAP_WIDTH)``.
        """
        HEIGHT, WIDTH = MAP_HEIGHT, MAP_WIDTH
        y, x = np.mgrid[0:HEIGHT, 0:WIDTH]

        # 1. Domain warping
        warp_x = np.sin(x / 80.0) * 30.0
        warp_y = np.cos(y / 80.0) * 30.0
        wx = x + warp_x
        wy = y + warp_y

        # 2. Fractal Brownian Motion – stack octaves
        base_layer   = (np.sin(wx / 250.0) * np.cos(wy / 180.0) + 1.0) * 0.5
        detail_layer = (np.sin(wx / 35.0)  * np.cos(wy / 25.0)  + 1.0) * 0.25
        micro_layer  = (np.sin(wx / 8.0)   * np.cos(wy / 8.0)   + 1.0) * 0.05
        combined_fbm = base_layer + detail_layer + micro_layer

        # 3. Ridge exponentiation – sharpen peaks, flatten plains
        normalized_fbm = combined_fbm / combined_fbm.max()
        geological_terrain = np.power(normalized_fbm, 2.2) * 255.0

        mask = MapGenerationEngine.generate_falloff_mask(WIDTH, HEIGHT, layout_style)
        final_heights = np.clip(geological_terrain * mask, 0, 255).astype(np.uint8)
        land_mask = final_heights > SEA_LEVEL_THRESHOLD

        return final_heights, land_mask

    @staticmethod
    def generate_voronoi_provinces(
        land_mask: np.ndarray,
        requested_provinces: int,
    ) -> tuple[np.ndarray, np.ndarray, bool, np.ndarray]:
        """Tessellate the land mass into Voronoi provinces and add sea provinces.

        Returns:
            ``(provinces_bmp, unique_colors, is_micro_world, sea_mask)``

        Raises:
            ValueError: When the heightmap contains no land mass.
        """
        HEIGHT, WIDTH = MAP_HEIGHT, MAP_WIDTH
        land_indices = np.argwhere(land_mask)
        total_land_pixels = len(land_indices)

        if total_land_pixels == 0:
            raise ValueError("Heightmap contains no land mass.")

        is_micro_world = requested_provinces < 150
        active_seeds = requested_provinces - 1 if is_micro_world else requested_provinces

        chosen_spots = land_indices[
            np.random.choice(total_land_pixels, active_seeds, replace=False)
        ]
        seeds = [(int(x), int(y)) for y, x in chosen_spots]

        all_y, all_x = np.mgrid[0:HEIGHT, 0:WIDTH]
        pixel_coords = np.c_[all_x.ravel(), all_y.ravel()]
        tree = cKDTree(seeds)

        if is_micro_world:
            raw_dist, raw_idx = tree.query(pixel_coords, workers=-1)  # type: ignore[union-attr]
            closest_indices: np.ndarray = np.asarray(raw_idx).reshape((HEIGHT, WIDTH))
            distances: np.ndarray = np.asarray(raw_dist).reshape((HEIGHT, WIDTH))
            wasteland_id = requested_provinces - 1
            closest_indices[distances > 85] = wasteland_id
        else:
            _, raw_idx2 = tree.query(pixel_coords, workers=-1)  # type: ignore[union-attr]
            closest_indices = np.asarray(raw_idx2).reshape((HEIGHT, WIDTH))

        unique_colors = np.random.randint(
            0, 256, size=(requested_provinces, 3), dtype=np.uint8
        )
        if is_micro_world:
            unique_colors[requested_provinces - 1] = [40, 40, 40]

        provinces_bmp = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        provinces_bmp[land_mask] = unique_colors[closest_indices[land_mask]]

        # Sea province generation
        sea_mask = ~land_mask
        sea_indices = np.argwhere(sea_mask)

        if len(sea_indices) > 0:
            sea_seeds_count = min(len(sea_indices) // 5000, 200)
            if sea_seeds_count > 0:
                sea_chosen = sea_indices[
                    np.random.choice(len(sea_indices), sea_seeds_count, replace=False)
                ]
                sea_seed_coords = [(int(x), int(y)) for y, x in sea_chosen]
                sea_tree = cKDTree(sea_seed_coords)

                sea_ys, sea_xs = np.where(sea_mask)
                sea_pixel_coords = np.c_[sea_xs, sea_ys]
                _, sea_closest = sea_tree.query(sea_pixel_coords, workers=-1)  # type: ignore[union-attr]

                sea_colors = np.random.randint(
                    0, 256, size=(sea_seeds_count, 3), dtype=np.uint8
                )
                provinces_bmp[sea_ys, sea_xs] = sea_colors[np.asarray(sea_closest)]

        return provinces_bmp, unique_colors, is_micro_world, sea_mask
