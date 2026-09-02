"""
Module 1: Advanced Procedural Map Generation Engine
====================================================
Generates heightmaps, province maps, river systems, and terrain classification
using Perlin noise, domain warping, fractal Brownian motion, tectonic simulation,
hydraulic erosion, and impact cratering.
"""

import numpy as np
import cv2
from scipy.spatial import cKDTree
from PIL import Image
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any


# ═══════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════

DEFAULT_WIDTH = 5632
DEFAULT_HEIGHT = 2048


@dataclass
class MapConfig:
    """Master configuration for map generation."""
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    seed: int = 42
    layout_style: str = "random"
    perlin_scale: float = 1.5
    land_percentage: int = 30
    num_tectonic_plates: int = 60
    impact_craters: int = 10
    erosion_steps: int = 40
    ridge_exponent: float = 2.2
    warp_strength: float = 30.0
    warp_scale: float = 80.0
    continent_octaves: int = 8
    detail_octaves: int = 6
    sea_level_threshold: int = 115
    forced_ocean_location: str = "random"  # north, south, east, west, both, none, or random (weighted, mostly none)
    map_position: str = "north_shifted"


# ═══════════════════════════════════════════════════════════════
#  FAST NOISE GENERATOR
# ═══════════════════════════════════════════════════════════════

class FastNoiseGenerator:
    """
    Fast approximation noise generator using numpy vectorized operations.
    Uses domain warping + multi-octave sinusoidal composition for speed.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)
        # Generate random phase offsets for each octave
        self.phase_offsets = [
            (random.uniform(0, 1000), random.uniform(0, 1000))
            for _ in range(12)
        ]

    def generate_fbm(self, width: int, height: int,
                     base_scale: float = 1.5,
                     octaves: int = 6,
                     persistence: float = 0.5,
                     warp_strength: float = 30.0,
                     warp_scale: float = 80.0) -> np.ndarray:
        """
        Generate fractal Brownian motion with domain warping.
        Uses vectorized numpy operations for speed.
        """
        y, x = np.mgrid[0:height, 0:width]
        fy = y / height
        fx = x / width

        # Domain warping: distort coordinates for natural coastlines
        warp_x = np.sin((fx + self.phase_offsets[0][0] / 1000) * warp_scale * 0.4) * warp_strength / width
        warp_y = np.cos((fy + self.phase_offsets[0][1] / 1000) * warp_scale * 0.4) * warp_strength / height
        wx = fx + warp_x
        wy = fy + warp_y

        # Secondary warping for more organic shapes
        warp2_x = np.sin((wy * 15 + self.phase_offsets[1][0] / 500) * 8) * 0.02
        warp2_y = np.cos((wx * 15 + self.phase_offsets[1][1] / 500) * 8) * 0.02
        wx = wx + warp2_x
        wy = wy + warp2_y

        result = np.zeros((height, width), dtype=np.float64)
        amplitude = 1.0
        frequency = base_scale
        max_amp = 0.0

        for i in range(octaves):
            px, py = self.phase_offsets[i % len(self.phase_offsets)]
            phase_x = px / 1000.0
            phase_y = py / 1000.0

            layer = (
                np.sin(wx * frequency * 6.2832 * 2 + phase_x) *
                np.cos(wy * frequency * 6.2832 * 2 + phase_y)
            )

            # Add rotated component for more variety
            angle = i * 0.7 + phase_x
            rot_x = wx * np.cos(angle) - wy * np.sin(angle)
            rot_y = wx * np.sin(angle) + wy * np.cos(angle)
            layer2 = (
                np.sin(rot_x * frequency * 6.2832 * 1.5 + phase_y) *
                np.cos(rot_y * frequency * 6.2832 * 1.5 + phase_x)
            )

            result += (layer * 0.7 + layer2 * 0.3) * amplitude
            max_amp += amplitude
            amplitude *= persistence
            frequency *= 2.1

        # Normalize to [0, 1]
        result = (result - result.min()) / (result.max() - result.min() + 1e-10)
        return result


# ═══════════════════════════════════════════════════════════════
#  MAP GENERATION ENGINE
# ═══════════════════════════════════════════════════════════════

class MapGenerationEngine:
    """
    Master procedural map generation engine combining noise, tectonics,
    erosion, and cratering into a cohesive heightmap pipeline.
    """

    def __init__(self, config: MapConfig = None):
        self.config = config or MapConfig()
        self.height = self.config.height
        self.width = self.config.width
        random.seed(self.config.seed)
        np.random.seed(self.config.seed)

    # Known layout styles. "random" (the new default) picks a weighted
    # choice per-seed instead of always using the same one, which -- along
    # with the randomization inside each style below -- is what actually
    # varies the macro continent arrangement between seeds. Previously
    # every style's shape came from a fixed-frequency, fixed-phase formula
    # with no randomness at all, so every generation produced the same
    # ~3-lobe skeleton regardless of seed; only fine noise detail varied.
    _STYLE_WEIGHTS = {
        "continents_islands": 3, "continents": 3, "earth_like": 3,
        "pangea": 2, "archipelago": 2, "island_grid": 1,
        "fantasy_ring": 1, "fantasy_spine": 2, "shattered": 2,
    }

    def _blob_falloff(self, rng: np.random.RandomState, x, y, num_blobs: int,
                       spread: float, size_variation: float = 0.3,
                       ellipse_variation: float = 0.35) -> np.ndarray:
        """Union of randomly placed, randomly sized/stretched/rotated
        radial blobs -- organic and different every seed, unlike a fixed
        sinusoidal formula. This is the workhorse behind most styles below;
        what varies per style is blob count, spread, and placement bias."""
        mask = np.zeros((self.height, self.width), dtype=np.float32)
        base_r = spread * min(self.width, self.height)
        for _ in range(num_blobs):
            bx = rng.uniform(0.06, 0.94) * self.width
            by = rng.uniform(0.10, 0.90) * self.height
            r = base_r * (1.0 + rng.uniform(-size_variation, size_variation))
            stretch_x = 1.0 + rng.uniform(-ellipse_variation, ellipse_variation)
            stretch_y = 1.0 + rng.uniform(-ellipse_variation, ellipse_variation)
            angle = rng.uniform(0, np.pi)
            dx, dy = x - bx, y - by
            rx = dx * np.cos(angle) + dy * np.sin(angle)
            ry = -dx * np.sin(angle) + dy * np.cos(angle)
            dist = np.sqrt((rx / (r * stretch_x)) ** 2 + (ry / (r * stretch_y)) ** 2)
            mask = np.maximum(mask, np.clip(1.0 - dist ** 2, 0, 1))
        return mask

    def _ring_falloff(self, rng: np.random.RandomState, x, y) -> np.ndarray:
        """A ring/horseshoe-shaped landmass around a central sea -- an
        arrangement real plate tectonics rarely produces but a common,
        distinctive fantasy-map trope."""
        cx = rng.uniform(0.35, 0.65) * self.width
        cy = rng.uniform(0.35, 0.65) * self.height
        outer = rng.uniform(0.30, 0.42) * min(self.width, self.height)
        inner = outer * rng.uniform(0.35, 0.55)
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        ring = np.clip(1.0 - np.abs(dist - (outer + inner) / 2) / ((outer - inner) / 2 + 1e-6), 0, 1)
        gap_angle = rng.uniform(0, 2 * np.pi)
        angle = np.arctan2(y - cy, x - cx)
        gap_width = rng.uniform(0.15, 0.4)
        gap = np.clip(np.abs(((angle - gap_angle + np.pi) % (2 * np.pi)) - np.pi) / gap_width, 0, 1)
        return ring * (0.4 + 0.6 * gap)

    def _spine_falloff(self, rng: np.random.RandomState, x, y) -> np.ndarray:
        """One sprawling, winding continent traced out as a random-walk
        path with organic varying width -- a common single-dominant-
        landmass fantasy shape, distinct from a round pangea blob."""
        mask = np.zeros((self.height, self.width), dtype=np.float32)
        px = rng.uniform(0.15, 0.85) * self.width
        py = rng.uniform(0.15, 0.35) * self.height
        heading = rng.uniform(0, 2 * np.pi)
        steps = rng.randint(9, 15)
        step_len = min(self.width, self.height) * rng.uniform(0.12, 0.18)
        for _ in range(steps):
            heading += rng.uniform(-1.1, 1.1)
            nx_, ny_ = px + np.cos(heading) * step_len, py + np.sin(heading) * step_len
            r = step_len * rng.uniform(0.55, 0.95)
            seg_x = np.linspace(px, nx_, 6)
            seg_y = np.linspace(py, ny_, 6)
            for sx, sy in zip(seg_x, seg_y):
                dist = np.sqrt((x - sx) ** 2 + (y - sy) ** 2) / r
                mask = np.maximum(mask, np.clip(1.0 - dist ** 2, 0, 1))
            px, py = nx_, ny_
        return mask

    def generate_falloff_mask(self) -> np.ndarray:
        """
        Generates 2D boundary arrays (0.0-1.0) shaping macro-geographies.
        Controls where land masses can appear on the map. Seed-randomized
        (see _blob_falloff/_ring_falloff/_spine_falloff above) so different
        seeds produce genuinely different continent counts/sizes/
        arrangements, not just different fine-grained noise on top of an
        identical fixed template.
        """
        y, x = np.ogrid[:self.height, :self.width]
        rng = np.random.RandomState((self.config.seed * 7919 + 104729) % (2 ** 31))

        style = self.config.layout_style
        if style not in self._STYLE_WEIGHTS:
            names = list(self._STYLE_WEIGHTS.keys())
            weights = np.array([self._STYLE_WEIGHTS[n] for n in names], dtype=float)
            style = rng.choice(names, p=weights / weights.sum())

        if style == "pangea":
            shape_mask = self._blob_falloff(rng, x, y, num_blobs=1, spread=0.62,
                                             size_variation=0.15, ellipse_variation=0.3)
        elif style == "continents":
            shape_mask = self._blob_falloff(rng, x, y, num_blobs=rng.randint(3, 6), spread=0.34)
        elif style == "earth_like":
            shape_mask = self._blob_falloff(rng, x, y, num_blobs=rng.randint(5, 8), spread=0.26,
                                             size_variation=0.5, ellipse_variation=0.45)
        elif style == "archipelago":
            shape_mask = self._blob_falloff(rng, x, y, num_blobs=rng.randint(12, 24), spread=0.16,
                                             size_variation=0.5)
        elif style == "island_grid":
            gx = rng.randint(3, 6)
            gy = rng.randint(2, 4)
            phase_x, phase_y = rng.uniform(0, np.pi, 2)
            rot = rng.uniform(0, np.pi / 6)
            nx = ((x - self.width / 2) * np.cos(rot) - (y - self.height / 2) * np.sin(rot)) / self.width
            ny = ((x - self.width / 2) * np.sin(rot) + (y - self.height / 2) * np.cos(rot)) / self.height
            grid_x = np.sin(nx * np.pi * gx + phase_x) ** 2
            grid_y = np.sin(ny * np.pi * gy + phase_y) ** 2
            shape_mask = np.clip(grid_x * grid_y * 0.7 + 0.15, 0, 1)
        elif style == "fantasy_ring":
            shape_mask = self._ring_falloff(rng, x, y)
        elif style == "fantasy_spine":
            shape_mask = self._spine_falloff(rng, x, y)
        elif style == "shattered":
            big = self._blob_falloff(rng, x, y, num_blobs=rng.randint(2, 4), spread=0.32)
            small = self._blob_falloff(rng, x, y, num_blobs=rng.randint(10, 20), spread=0.10,
                                        size_variation=0.6)
            shape_mask = np.maximum(big, small * 0.85)
        else:  # continents_islands
            shape_mask = self._blob_falloff(rng, x, y, num_blobs=rng.randint(2, 5), spread=0.32,
                                             size_variation=0.4, ellipse_variation=0.4)

        # Randomized ocean bias -- weighted toward "none" so a forced empty
        # hemisphere (the old fixed "always south" default) is the
        # exception per generation, not the permanent rule.
        ocean_choice = self.config.forced_ocean_location
        if ocean_choice not in ("north", "south", "east", "west", "both", "none"):
            ocean_choice = rng.choice(
                ["none", "none", "none", "north", "south", "east", "west", "both"],
                p=[0.45, 0.0, 0.0, 0.11, 0.11, 0.11, 0.11, 0.11])
        cx, cy = self.width / 2.0, self.height / 2.0
        nx_norm, ny_norm = (x - cx) / cx, (y - cy) / cy
        strength = rng.uniform(0.5, 0.8)
        if ocean_choice == "south":
            ocean_mask = 1.0 - np.clip(ny_norm * 1.5, 0, 1) ** 0.5 * strength
        elif ocean_choice == "north":
            ocean_mask = 1.0 - np.clip(-ny_norm * 1.5, 0, 1) ** 0.5 * strength
        elif ocean_choice == "east":
            ocean_mask = 1.0 - np.clip(nx_norm * 1.5, 0, 1) ** 0.5 * strength
        elif ocean_choice == "west":
            ocean_mask = 1.0 - np.clip(-nx_norm * 1.5, 0, 1) ** 0.5 * strength
        elif ocean_choice == "both":
            ocean_mask = 1.0 - np.clip(np.abs(ny_norm) * 1.5, 0, 1) ** 0.5 * strength * 0.75
        else:
            ocean_mask = np.ones((self.height, self.width), dtype=np.float32)

        # A hard-zero gap between blobs can never become land no matter how
        # high land_percentage is set (there's nothing for the percentile
        # threshold below to expand into), which silently capped every
        # style well under high land_percentage targets. A small floor
        # keeps each style's distinct clustering (blob cores still score
        # far higher than gaps) while guaranteeing the full 10-60% range
        # stays reachable.
        shape_mask = np.clip(shape_mask + 0.16, 0, 1)

        return shape_mask * ocean_mask

    def generate_heightmap(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Full heightmap generation pipeline:
        1. fBm noise generation with domain warping
        2. Ridge exponentiation (sharp peaks, flat valleys)
        3. Falloff mask application (continent shaping)
        4. Land mask extraction
        """
        # Generate base noise using fast generator
        noise_gen = FastNoiseGenerator(seed=self.config.seed)
        raw_noise = noise_gen.generate_fbm(
            self.width, self.height,
            base_scale=self.config.perlin_scale,
            octaves=self.config.continent_octaves,
            persistence=0.55,
            warp_strength=self.config.warp_strength,
            warp_scale=self.config.warp_scale
        )

        # Apply continent-scale detail layer
        continent_noise = noise_gen.generate_fbm(
            self.width, self.height,
            base_scale=self.config.perlin_scale * 0.3,
            octaves=self.config.detail_octaves,
            persistence=0.6,
            warp_strength=self.config.warp_strength * 2.0,
            warp_scale=self.config.warp_scale * 0.3
        )

        # Blend continent and detail noise
        blended = raw_noise * 0.6 + continent_noise * 0.4

        # Ridge exponentiation: sharpen peaks, flatten valleys
        ridge_terrain = np.power(blended, self.config.ridge_exponent)

        # Apply falloff mask for continent shaping
        falloff = self.generate_falloff_mask()
        masked_terrain = ridge_terrain * falloff

        # Adjust land percentage by tuning sea level
        target_land = self.config.land_percentage / 100.0
        sorted_vals = np.sort(masked_terrain.ravel())
        sea_idx = int(len(sorted_vals) * (1.0 - target_land))
        sea_level = sorted_vals[min(sea_idx, len(sorted_vals) - 1)]

        # Compute land mask
        land_mask = masked_terrain > sea_level
        actual_land_pct = land_mask.sum() / land_mask.size

        # If initial threshold is off, binary-search for the correct one
        if abs(actual_land_pct - target_land) > 0.05:
            lo, hi = 0.0, 1.0
            for _ in range(20):
                mid = (lo + hi) / 2
                test_mask = masked_terrain > mid
                test_pct = test_mask.sum() / test_mask.size
                if test_pct > target_land:
                    lo = mid
                else:
                    hi = mid
            land_mask = masked_terrain > ((lo + hi) / 2)

        # Scale to 0-255 uint8 with proper land/sea separation
        # Sea pixels get value 0; land pixels get values 55-255 proportional to elevation
        heightmap_8bit = np.zeros_like(masked_terrain, dtype=np.uint8)
        land_vals = masked_terrain[land_mask]
        if len(land_vals) > 0 and land_vals.max() > land_vals.min():
            scaled = (land_vals - land_vals.min()) / (land_vals.max() - land_vals.min())
            heightmap_8bit[land_mask] = (scaled * 200 + 55).astype(np.uint8)
        elif len(land_vals) > 0:
            heightmap_8bit[land_mask] = 128  # flat land = mid-range

        return heightmap_8bit, land_mask

    def apply_tectonic_plates(self, heightmap: np.ndarray,
                               land_mask: np.ndarray) -> np.ndarray:
        """
        Simulates tectonic plate boundaries creating mountain ranges
        at convergence zones and rift valleys at divergence zones.
        """
        result = heightmap.astype(np.float32)

        # Generate plate assignments using random seeds
        num_plates = self.config.num_tectonic_plates
        plate_seeds_y = np.random.randint(0, self.height, num_plates)
        plate_seeds_x = np.random.randint(0, self.width, num_plates)

        # Assign each pixel to nearest plate using vectorized distance
        y_grid, x_grid = np.mgrid[0:self.height, 0:self.width]
        plate_map = np.zeros((self.height, self.width), dtype=np.int32)
        min_dist = np.full((self.height, self.width), np.inf)

        for i in range(num_plates):
            dist = np.sqrt(
                (x_grid - plate_seeds_x[i]) ** 2 +
                (y_grid - plate_seeds_y[i]) ** 2
            )
            closer = dist < min_dist
            plate_map[closer] = i
            min_dist[closer] = dist[closer]

        # Detect plate boundaries
        boundary_mask = np.zeros_like(land_mask)
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            shifted = np.roll(np.roll(plate_map, dy, axis=0), dx, axis=1)
            boundary_mask |= (plate_map != shifted)

        # Elevate boundary zones that are on land (mountain building)
        boundary_land = boundary_mask & land_mask
        elevation_boost = np.where(boundary_land, 40.0, 0.0)
        # Gaussian blur for natural mountain spread
        elevation_boost = cv2.GaussianBlur(elevation_boost, (31, 31), 10)

        result = np.clip(result + elevation_boost, 0, 255).astype(np.uint8)
        # Preserve sea pixels — do not let blurred elevation bleed into ocean
        result[~land_mask] = 0
        return result

    def apply_impact_craters(self, heightmap: np.ndarray,
                              land_mask: np.ndarray,
                              num_craters: int = None) -> np.ndarray:
        """
        Adds meteorite impact craters to the terrain.
        Craters have raised rims and depressed centers.
        """
        result = heightmap.astype(np.float32)
        land_coords = np.argwhere(land_mask)

        if len(land_coords) == 0:
            return heightmap

        n_craters = num_craters if num_craters is not None else self.config.impact_craters
        for _ in range(n_craters):
            # Pick random land location
            idx = np.random.randint(0, len(land_coords))
            cy, cx = land_coords[idx]

            # Random crater radius
            radius = np.random.randint(15, 60)
            depth = np.random.uniform(15, 40)
            rim_height = depth * 0.6

            # Create crater mask
            y_grid, x_grid = np.mgrid[
                max(0, cy - radius * 2):min(self.height, cy + radius * 2),
                max(0, cx - radius * 2):min(self.width, cx + radius * 2)
            ]
            if y_grid.size == 0:
                continue

            dist = np.sqrt((y_grid - cy) ** 2 + (x_grid - cx) ** 2)

            # Crater depression
            crater_interior = dist < radius
            depression = np.where(crater_interior,
                                  -depth * (1 - dist / radius) ** 2, 0)

            # Raised rim
            rim_zone = (dist >= radius) & (dist < radius * 1.3)
            rim = np.where(rim_zone,
                           rim_height * (1 - (dist - radius) / (radius * 0.3)) ** 2, 0)

            # Apply to result
            y_start = max(0, cy - radius * 2)
            y_end = min(self.height, cy + radius * 2)
            x_start = max(0, cx - radius * 2)
            x_end = min(self.width, cx + radius * 2)

            result[y_start:y_end, x_start:x_end] += depression + rim

        result[~land_mask] = 0  # Preserve sea pixels
        return np.clip(result, 0, 255).astype(np.uint8)

    def apply_hydraulic_erosion(self, heightmap: np.ndarray,
                                 land_mask: np.ndarray,
                                 steps: int = None) -> np.ndarray:
        """
        Simplified hydraulic erosion using flow accumulation.
        Rain falls on terrain, flows downhill, and carves channels.
        Preserves land_mask integrity: sea stays at 0, land stays >= 1.
        """
        steps = steps or self.config.erosion_steps
        result = heightmap.astype(np.float32)

        for _ in range(steps):
            # Compute gradients
            grad_y = np.zeros_like(result)
            grad_x = np.zeros_like(result)
            grad_y[1:-1, :] = (result[2:, :] - result[:-2, :]) / 2
            grad_x[:, 1:-1] = (result[:, 2:] - result[:, :-2]) / 2

            # Erosion proportional to slope magnitude on land only
            slope_mag = np.sqrt(grad_x ** 2 + grad_y ** 2)
            erosion = slope_mag * 0.15 * land_mask.astype(np.float32)

            # Deposit sediment in flat areas
            flat_areas = (slope_mag < 0.5) & land_mask
            deposition = np.where(flat_areas, erosion.mean() * 0.15, 0)

            result -= erosion
            result += deposition

            # Enforce land mask: sea = 0, land >= 1
            result[~land_mask] = 0
            result[land_mask] = np.maximum(result[land_mask], 1.0)

        return np.clip(result, 0, 255).astype(np.uint8)

    def generate_complete_heightmap(
        self,
        apply_tectonic: bool = True,
        apply_erosion: bool = True,
        apply_craters: bool = True,
        num_craters: int = 3,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Full pipeline: noise → tectonics → craters → erosion → final heightmap.
        Returns (heightmap_8bit, land_mask).
        """
        heightmap, land_mask = self.generate_heightmap()
        if apply_tectonic:
            heightmap = self.apply_tectonic_plates(heightmap, land_mask)
        if apply_craters:
            heightmap = self.apply_impact_craters(heightmap, land_mask, num_craters=num_craters)
        if apply_erosion:
            heightmap = self.apply_hydraulic_erosion(heightmap, land_mask)
        # Preserve original land_mask — do NOT re-derive from 8-bit heightmap.
        # The encoding scheme sets sea=0 and land=100-255, so a simple threshold
        # on the 8-bit values would misclassify pixels.  After tectonic/erosion
        # modifications the elevation values may shift slightly within the land
        # band but they should not cross from land to sea or vice-versa.
        # If a pixel was land before, it stays land; sea stays sea.
        return heightmap, land_mask


# ═══════════════════════════════════════════════════════════════
#  PROVINCE GENERATOR
# ═══════════════════════════════════════════════════════════════

@dataclass
class ProvinceInfo:
    """Complete information about a generated province."""
    id: int = 0
    color: Tuple[int, int, int] = (0, 0, 0)
    center_x: int = 0
    center_y: int = 0
    pixel_count: int = 0
    is_sea: bool = False
    is_wasteland: bool = False
    is_island: bool = False
    is_lake: bool = False
    avg_elevation: float = 0.0
    max_elevation: float = 0.0
    terrain_type: str = "plains"
    continent_name: str = ""
    latitude_band: str = ""
    river_count: int = 0


class ProvinceGenerator:
    """
    Generates EU4-compliant province map from heightmap and land mask.
    Uses Voronoi tessellation with flood-fill for province assignment.
    """

    def __init__(self, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT):
        self.width = width
        self.height = height

    def generate_provinces(self, heightmap: np.ndarray, land_mask: np.ndarray,
                           requested_provinces: int) -> Tuple[np.ndarray, List[ProvinceInfo], bool]:
        """
        Generates province bitmap and province information list.
        Returns (provinces_bmp, province_info_list, is_micro_world).
        """
        land_indices = np.argwhere(land_mask)
        total_land_pixels = len(land_indices)

        if total_land_pixels == 0:
            raise ValueError("Heightmap contains no land mass. Cannot seed provinces.")

        is_micro_world = requested_provinces < 150
        active_seeds = requested_provinces - 1 if is_micro_world else requested_provinces

        # Ensure we don't request more seeds than land pixels
        active_seeds = min(active_seeds, total_land_pixels - 1)
        if active_seeds < 1:
            active_seeds = 1

        # Seed placement using Poisson-disk-like distribution
        chosen_spots = land_indices[
            np.random.choice(total_land_pixels, active_seeds, replace=False)
        ]
        seeds = [(x, y) for y, x in chosen_spots]

        # Build Voronoi assignment using KD-tree
        all_y, all_x = np.mgrid[0:self.height, 0:self.width]
        pixel_coords = np.c_[all_x.ravel(), all_y.ravel()]
        tree = cKDTree(seeds)

        if is_micro_world:
            distances, closest_indices = tree.query(pixel_coords, workers=-1)
            closest_indices = closest_indices.reshape((self.height, self.width))
            distances = distances.reshape((self.height, self.width))
            wasteland_id = requested_provinces
            # Mark distant pixels as wasteland
            max_province_radius = max(85, int(np.sqrt(
                total_land_pixels / requested_provinces * 1.5
            )))
            closest_indices[distances > max_province_radius] = wasteland_id - 1
        else:
            _, closest_indices = tree.query(pixel_coords, workers=-1)
            closest_indices = closest_indices.reshape((self.height, self.width))

        # Generate unique colors for each province
        num_provinces = requested_provinces
        unique_colors = np.random.randint(10, 246, size=(num_provinces, 3), dtype=np.uint8)

        if is_micro_world:
            unique_colors[num_provinces - 1] = [40, 40, 40]  # Dark gray wasteland

        # Paint province bitmap
        provinces_bmp = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # ── Sea provinces ──
        # Ocean pixels need to be split into real, distinct sea provinces the
        # same way land is (EU4 requires every provinces.bmp pixel to map to
        # a definition.csv entry; a single flat "sea colour" with no matching
        # province leaves the whole ocean undefined). Density roughly matches
        # the land province density so sea/land provinces are similar size.
        sea_mask = ~land_mask
        sea_indices = np.argwhere(sea_mask)
        total_sea_pixels = len(sea_indices)
        sea_infos: List[ProvinceInfo] = []

        if total_sea_pixels > 0:
            pixels_per_land_province = max(total_land_pixels / max(active_seeds, 1), 1)
            num_sea_provinces = max(1, int(total_sea_pixels / pixels_per_land_province))
            num_sea_provinces = min(num_sea_provinces, total_sea_pixels)

            sea_spots = sea_indices[
                np.random.choice(total_sea_pixels, num_sea_provinces, replace=False)
            ]
            sea_seeds = [(x, y) for y, x in sea_spots]
            sea_tree = cKDTree(sea_seeds)
            _, sea_closest = sea_tree.query(pixel_coords, workers=-1)
            sea_closest = sea_closest.reshape((self.height, self.width))

            # Blue-toned but mutually distinct colours, kept out of the
            # land-province colour range (10-246 on every channel).
            sea_colors = np.column_stack([
                np.random.randint(0, 60, size=num_sea_provinces),
                np.random.randint(20, 90, size=num_sea_provinces),
                np.random.randint(70, 180, size=num_sea_provinces),
            ]).astype(np.uint8)

            sea_id_start = num_provinces + 1
            for s_idx in range(num_sea_provinces):
                mask = (sea_closest == s_idx) & sea_mask
                if not np.any(mask):
                    continue
                provinces_bmp[mask] = sea_colors[s_idx]
                y_indices, x_indices = np.where(mask)
                sea_infos.append(ProvinceInfo(
                    id=sea_id_start + s_idx,
                    color=tuple(sea_colors[s_idx].tolist()),
                    center_x=int(np.mean(x_indices)),
                    center_y=int(np.mean(y_indices)),
                    pixel_count=len(x_indices),
                    is_sea=True,
                    terrain_type="ocean",
                    continent_name=self._assign_continent(int(np.mean(y_indices))),
                    latitude_band=self._assign_latitude_band(int(np.mean(y_indices))),
                ))
        else:
            provinces_bmp[sea_mask] = [0, 40, 80]

        # Land pixels get their province color
        for p_idx in range(min(num_provinces, active_seeds + 1)):
            mask = closest_indices == p_idx
            provinces_bmp[mask & land_mask] = unique_colors[p_idx]

        # Compute province information
        province_infos = self._compute_province_info(
            provinces_bmp, unique_colors, heightmap, land_mask,
            closest_indices, is_micro_world, num_provinces
        )
        province_infos.extend(sea_infos)
        self._detect_lakes(province_infos, land_mask)

        return provinces_bmp, province_infos, is_micro_world

    @staticmethod
    def _detect_lakes(province_infos: List[ProvinceInfo], land_mask: np.ndarray) -> None:
        """Flags sea provinces enclosed by land and disconnected from the
        main ocean as lakes (mutates province_infos in place). Per the EU4
        wiki, a lake is mechanically just a sea province that's also listed
        in default.map's lakes = {} -- there's no separate province type,
        so this only needs to classify, not regenerate, geometry.
        """
        from engine.canal_detection import labeled_regions

        water_labels, label_sizes = labeled_regions(~land_mask)
        if label_sizes.size <= 1:
            return
        label_sizes = label_sizes.copy()
        label_sizes[0] = 0  # ignore the land (label 0) background
        ocean_label = int(np.argmax(label_sizes))

        h, w = land_mask.shape
        for p in province_infos:
            if not p.is_sea:
                continue
            y = min(max(p.center_y, 0), h - 1)
            x = min(max(p.center_x, 0), w - 1)
            here = water_labels[y, x]
            if here != 0 and here != ocean_label:
                p.is_lake = True

    def _compute_province_info(self, provinces_bmp: np.ndarray,
                                unique_colors: np.ndarray,
                                heightmap: np.ndarray,
                                land_mask: np.ndarray,
                                closest_indices: np.ndarray,
                                is_micro_world: bool,
                                num_provinces: int) -> List[ProvinceInfo]:
        """Computes detailed information for each province."""
        infos = []

        for p_idx in range(num_provinces):
            color = tuple(unique_colors[p_idx].tolist())

            # Find all pixels belonging to this province
            r, g, b = color
            match_mask = (
                (provinces_bmp[:, :, 0] == r) &
                (provinces_bmp[:, :, 1] == g) &
                (provinces_bmp[:, :, 2] == b) &
                land_mask
            )

            y_indices, x_indices = np.where(match_mask)
            pixel_count = len(x_indices)

            if pixel_count == 0:
                # Province has no land pixels at all (its Voronoi cell claimed
                # no land this run) -- treat it as an empty/unused sea slot.
                # It must NOT also carry the wasteland flag: a province can't
                # simultaneously be a sea_start (default.map) and an
                # impassable wasteland (climate.txt) without producing
                # contradictory mod files.
                infos.append(ProvinceInfo(
                    id=p_idx + 1,
                    color=color,
                    is_sea=True,
                    is_wasteland=False,
                ))
                continue

            center_x = int(np.mean(x_indices))
            center_y = int(np.mean(y_indices))
            avg_elev = float(np.mean(heightmap[match_mask]))
            max_elev = float(np.max(heightmap[match_mask]))

            # Determine terrain type from elevation
            terrain_type = self._classify_terrain(avg_elev, max_elev)

            # Detect island (province surrounded by sea)
            is_island = self._detect_island(match_mask, land_mask)

            # Determine continent from latitude
            continent = self._assign_continent(center_y)

            # Latitude band for tech/religion assignment
            lat_band = self._assign_latitude_band(center_y)

            is_wasteland = (is_micro_world and p_idx == num_provinces - 1)

            infos.append(ProvinceInfo(
                id=p_idx + 1,
                color=color,
                center_x=center_x,
                center_y=center_y,
                pixel_count=pixel_count,
                is_sea=False,
                is_wasteland=is_wasteland,
                is_island=is_island,
                avg_elevation=avg_elev,
                max_elevation=max_elev,
                terrain_type=terrain_type,
                continent_name=continent,
                latitude_band=lat_band
            ))

        return infos

    def _classify_terrain(self, avg_elev: float, max_elev: float) -> str:
        """Classifies terrain type based on elevation statistics."""
        if max_elev > 200:
            return "mountain"
        elif max_elev > 170:
            return "hills"
        elif avg_elev < 125:
            return "coastal_desert"
        elif avg_elev < 140:
            return "farmland"
        elif avg_elev < 160:
            return "grasslands"
        elif avg_elev < 180:
            return "forest"
        else:
            return "highland"

    def _detect_island(self, match_mask: np.ndarray,
                       land_mask: np.ndarray) -> bool:
        """Detects if a province is an island (surrounded by sea)."""
        # Dilate the province mask and check if it touches other land
        kernel = np.ones((15, 15), np.uint8)
        dilated = cv2.dilate(match_mask.astype(np.uint8), kernel, iterations=2)

        # Check if dilated area contains land pixels NOT in this province
        expanded_land = dilated.astype(bool) & land_mask
        only_province = match_mask & land_mask
        surrounding_land = expanded_land & ~only_province

        # If very little surrounding land, it's an island
        surrounding_pixels = surrounding_land.sum()
        province_pixels = only_province.sum()

        if province_pixels == 0:
            return False

        return surrounding_pixels < province_pixels * 0.5

    def _assign_continent(self, center_y: int) -> str:
        """
        Assigns continent based on Y latitude (inverted world).
        Top of map (low Y) = Northern Europe (weak)
        Middle = Middle East / North Africa
        Lower middle = Sub-Saharan Africa / South Asia (strong)
        Bottom = Southern territories
        Thresholds scale with actual map height.
        """
        h = self.height
        if center_y < h * 0.17:
            return "northern_europe"
        elif center_y < h * 0.29:
            return "central_europe"
        elif center_y < h * 0.44:
            return "mediterranean"
        elif center_y < h * 0.54:
            return "middle_east"
        elif center_y < h * 0.63:
            return "west_africa"
        elif center_y < h * 0.73:
            return "south_asia"
        elif center_y < h * 0.83:
            return "east_africa"
        else:
            return "southern_territories"

    def _assign_latitude_band(self, center_y: int) -> str:
        """Assigns latitude band for tech group and religion determination.
        Thresholds scale with actual map height."""
        h = self.height
        if center_y < h * 0.25:
            return "europe_primitive"
        elif center_y < h * 0.375:
            return "mediterranean_developing"
        elif center_y < h * 0.50:
            return "middle_east_civilized"
        elif center_y < h * 0.625:
            return "africa_advanced"
        elif center_y < h * 0.75:
            return "asia_advanced"
        else:
            return "southern_developing"


# ═══════════════════════════════════════════════════════════════
#  RIVER GENERATOR
# ═══════════════════════════════════════════════════════════════

class RiverGenerator:
    """
    Simulates rainfall and D8 downhill routing to carve EU4-compliant rivers.
    """

    def __init__(self, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT):
        self.width = width
        self.height = height

    def generate_rivers(self, heightmap: np.ndarray, land_mask: np.ndarray,
                        min_flow: Optional[int] = None) -> Tuple[np.ndarray, Dict[int, int]]:
        """
        Generates river map and returns province river counts.
        Returns (river_bmp_rgb, province_river_counts).

        min_flow is the flow-accumulation threshold a pixel needs to be
        painted as a river. Left as None (the default), it's calibrated
        adaptively per map instead of a fixed constant: this generator's
        D8 flow accumulation on a noisy, quantized heightmap produces much
        smaller drainage basins than the "hundreds to thousands" a fixed
        threshold like 800 assumes (measured max accumulation on a full
        5632x2048 map: well under that), so a fixed threshold silently
        produced zero river pixels at every map size tested. Instead the
        threshold is set from the flow distribution actually produced,
        targeting roughly the ~2-3% land-pixel river coverage measured on
        an actual EU4 rivers.bmp.
        """
        height, width = heightmap.shape
        flow_acc = np.ones((height, width), dtype=np.int64)

        # Elevation is quantized to uint8 (0-255) AND locally noisy (erosion/
        # tectonic/crater detail), so a raw per-pixel steepest-descent walk
        # fragments into thousands of tiny, disconnected 1-50 cell puddles
        # instead of a few large, coherent drainage basins -- flow never
        # accumulates enough for any fixed or percentile threshold to pick
        # out actual branching river LINES; it just picks scattered noise.
        # Routing on a smoothed copy of the heightmap (real hydrology tools
        # do the same "fill/smooth before flow-direction" step) preserves
        # large-scale slope toward the coast while ironing out the small
        # bumps that were fragmenting every basin. A tiny post-smoothing
        # noise field still breaks any exact remaining ties.
        from scipy.ndimage import gaussian_filter
        smoothed_elev = gaussian_filter(heightmap.astype(np.float64), sigma=4.0)
        tie_rng = np.random.RandomState(0)
        tie_breaker = gaussian_filter(tie_rng.random_sample((height, width)), sigma=2.0)
        routing_elev = smoothed_elev + tie_breaker * 0.5

        # Sort cells by elevation (highest first)
        flat_elevations = routing_elev.ravel()
        sorted_indices = np.argsort(-flat_elevations)

        dy = [-1, -1, -1, 0, 0, 1, 1, 1]
        dx = [-1, 0, 1, -1, 1, -1, 0, 1]

        for flat_idx in sorted_indices:
            y = flat_idx // width
            x = flat_idx % width
            if not land_mask[y, x]:
                continue

            current_elev = routing_elev[y, x]
            steepest_drop = 0.0
            target = None

            for i in range(8):
                ny, nx = y + dy[i], x + dx[i]
                if 0 <= ny < height and 0 <= nx < width:
                    drop = current_elev - routing_elev[ny, nx]
                    if drop > steepest_drop:
                        steepest_drop = drop
                        target = (ny, nx)

            if target:
                ny, nx = target
                flow_acc[ny, nx] += flow_acc[y, x]

        if min_flow is None:
            land_flow = flow_acc[land_mask]
            min_flow = max(15, int(np.percentile(land_flow, 97))) if land_flow.size else 15

        # Paint river pixels
        # Background matches the real vanilla rivers.bmp convention: white
        # for land, grey (122,122,122) for sea -- confirmed by sampling an
        # actual EU4 rivers.bmp, where those are the two most common colors
        # by a wide margin. Only then are river pixels drawn on top.
        river_map = np.full((height, width, 3), 255, dtype=np.uint8)
        river_map[~land_mask] = [122, 122, 122]
        river_pixels = np.argwhere((flow_acc >= min_flow) & land_mask)

        for y, x in river_pixels:
            volume = flow_acc[y, x]
            is_source = True
            for i in range(8):
                ny, nx = y + dy[i], x + dx[i]
                if 0 <= ny < height and 0 <= nx < width:
                    if (flow_acc[ny, nx] > min_flow and
                            heightmap[ny, nx] > heightmap[y, x]):
                        is_source = False
                        break
            if is_source:
                river_map[y, x] = [0, 255, 0]      # Green = source
            elif volume > min_flow * 4:
                river_map[y, x] = [0, 225, 255]     # Yellow = major river
            else:
                river_map[y, x] = [0, 0, 225]       # Blue = regular river

        return river_map, flow_acc


# ═══════════════════════════════════════════════════════════════
#  WATER BODY ANALYSIS -- lake detection & canal siting
# ═══════════════════════════════════════════════════════════════

@dataclass
class CanalCandidate:
    """A detected canal-worthy land crossing: cutting through `width_px`
    pixels of land at (y, x) would connect two water areas. point_a/point_b
    are the actual water pixels on each side to connect with a river line
    (filled in by find_canal_candidates for the final selection only)."""
    y: int
    x: int
    width_px: float
    kind: str  # "land_bridge" (two distinct water bodies) or "peninsula" (one body, pinched)
    body_a: int
    body_b: int
    point_a: Tuple[int, int] = (0, 0)
    point_b: Tuple[int, int] = (0, 0)


class WaterBodyAnalyzer:
    """
    Identifies distinct water bodies (to tell ocean from lake) and finds
    narrow land crossings worth turning into canals -- using the same
    geometric patterns real-world canals follow: a land bridge between
    two seas (Panama, Kra), a narrow peninsula neck (Corinth), or a short
    land gap between a lake and the sea/another lake (Kiel touches the
    Baltic via a similar short crossing). Everything here works on the
    land/water mask directly, so it applies equally to a freshly
    generated map or one loaded from reference bitmaps.
    """

    @staticmethod
    def label_water_bodies(land_mask: np.ndarray) -> Tuple[np.ndarray, Dict[int, int]]:
        """Labels connected water regions. EU4 maps wrap horizontally, so
        the left and right edges are treated as adjacent when merging
        regions that only look disconnected because of the map seam.
        Returns (label array, {label_id: pixel_count})."""
        from scipy.ndimage import label as cc_label

        water = ~land_mask
        labels, num = cc_label(water, structure=np.ones((3, 3), dtype=int))
        if num == 0:
            return labels, {}

        parent = list(range(num + 1))

        def find(a: int) -> int:
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        left_col, right_col = labels[:, 0], labels[:, -1]
        for a, b in zip(left_col.tolist(), right_col.tolist()):
            if a > 0 and b > 0:
                union(a, b)

        remap = np.array([find(i) for i in range(num + 1)], dtype=np.int32)
        labels = remap[labels]

        unique, counts = np.unique(labels[labels > 0], return_counts=True)
        return labels, dict(zip(unique.tolist(), counts.tolist()))

    @staticmethod
    def identify_lake_provinces(province_infos: List, water_labels: np.ndarray,
                                 water_counts: Dict[int, int],
                                 max_lake_fraction: float = 0.003) -> List[int]:
        """A sea province is a "lake" if its water body is small and (by
        construction of label_water_bodies) disconnected from every other
        body -- i.e. landlocked. Large disconnected bodies (an inland sea
        the size of a real sea) are deliberately left as ordinary sea
        provinces; only small, clearly lake-sized bodies qualify, per
        `max_lake_fraction` of total map area."""
        if not water_counts:
            return []
        h, w = water_labels.shape
        threshold = max(50, int(h * w * max_lake_fraction))
        lake_ids = []
        for p in province_infos:
            if not p.is_sea:
                continue
            y = min(max(p.center_y, 0), h - 1)
            x = min(max(p.center_x, 0), w - 1)
            lbl = int(water_labels[y, x])
            if lbl > 0 and water_counts.get(lbl, 0) <= threshold:
                lake_ids.append(p.id)
        return lake_ids

    @staticmethod
    def _wrapped_distance(mask: np.ndarray, margin: int) -> np.ndarray:
        """Euclidean distance transform (distance to nearest True pixel)
        with the map's left/right seam treated as adjacent, via a cheap
        wrap-pad instead of a full 3x tile (keeps memory bounded on large
        maps)."""
        from scipy.ndimage import distance_transform_edt

        padded = np.pad(mask, ((0, 0), (margin, margin)), mode="wrap")
        dist = distance_transform_edt(~padded).astype(np.float32)
        return dist[:, margin:margin + mask.shape[1]]

    @classmethod
    def find_canal_candidates(cls, land_mask: np.ndarray, water_labels: np.ndarray,
                               water_counts: Dict[int, int],
                               max_candidates: int = 5,
                               min_body_fraction: float = 0.0008,
                               max_width_px: Optional[int] = None) -> List[CanalCandidate]:
        """Finds the narrowest land crossings between significant water
        bodies (land bridges/lake gaps -- Panama, Kra, Kiel-style), plus
        narrow peninsula necks pinched by a single body on two sides
        (Corinth-style), and returns the best `max_candidates`, widest
        crossings first excluded, narrowest first."""
        h, w = land_mask.shape
        total = h * w
        if max_width_px is None:
            max_width_px = max(8, int(w * 0.01))
        min_pixels = max(200, int(total * min_body_fraction))

        significant = sorted(
            (lbl for lbl, cnt in water_counts.items() if cnt >= min_pixels),
            key=lambda l: -water_counts[l],
        )[:12]
        if not significant:
            return []

        margin = max_width_px + 2
        body_dist = {lbl: cls._wrapped_distance(water_labels == lbl, margin) for lbl in significant}

        candidates: List[CanalCandidate] = []

        # -- land bridges / lake gaps: narrowest land between two distinct bodies --
        for i, a in enumerate(significant):
            for b in significant[i + 1:]:
                combined = body_dist[a] + body_dist[b]
                masked = np.where(land_mask, combined, np.inf)
                if not np.isfinite(masked).any():
                    continue
                idx = int(np.argmin(masked))
                y, x = divmod(idx, w)
                width = float(masked[y, x])
                if width <= max_width_px:
                    candidates.append(CanalCandidate(y, x, width, "land_bridge", a, b))

        # -- peninsula necks: land pinched by the same body on two sides --
        directions = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]
        rng = np.random.RandomState(0)
        for lbl in significant:
            dist = body_dist[lbl]
            near = land_mask & (dist <= max_width_px) & (dist >= 1)
            ys, xs = np.where(near)
            if len(ys) == 0:
                continue
            if len(ys) > 4000:
                pick = rng.choice(len(ys), 4000, replace=False)
                ys, xs = ys[pick], xs[pick]
            best_here = None
            for y, x in zip(ys.tolist(), xs.tolist()):
                hits = []
                for dy, dx in directions:
                    hit = None
                    for k in range(1, max_width_px + 1):
                        ny, nx = y + dy * k, (x + dx * k) % w
                        if not (0 <= ny < h):
                            break
                        if not land_mask[ny, nx]:
                            hit = k
                            break
                    hits.append(hit)
                for k in range(4):
                    d1, d2 = hits[k], hits[k + 4]
                    if d1 is not None and d2 is not None:
                        width = float(d1 + d2)
                        if best_here is None or width < best_here[0]:
                            best_here = (width, y, x)
                        break
            if best_here:
                width, y, x = best_here
                candidates.append(CanalCandidate(y, x, width, "peninsula", lbl, lbl))

        candidates.sort(key=lambda c: c.width_px)
        selected: List[CanalCandidate] = []
        min_sep_sq = (max_width_px * 3) ** 2
        for c in candidates:
            if all((c.y - s.y) ** 2 + (c.x - s.x) ** 2 > min_sep_sq for s in selected):
                selected.append(c)
            if len(selected) >= max_candidates:
                break
        return selected


# ═══════════════════════════════════════════════════════════════
#  TERRAIN & CLIMATE CLASSIFIER
# ═══════════════════════════════════════════════════════════════

class TerrainClassifier:
    """Classifies terrain and generates terrain.bmp, climate.txt data."""

    # EU4 terrain type color codes
    # Palette calibrated against an actual EU4 terrain.bmp (sampled by pixel
    # count: 14 distinct colors total, geographically cross-checked -- e.g.
    # the dark-brown "mountain" tone traces the Rockies/Andes/Alps/Himalayas
    # exactly, the teal "marsh" tone sits on the Sudd/Nile wetlands). Where
    # vanilla doesn't have a clearly distinct 1:1 color for one of this
    # generator's categories (deep_ocean, coastline, jungle, steppe, tundra),
    # a nearby value in the same family is used instead of an invented one.
    TERRAIN_COLORS = {
        "ocean":           [8, 31, 130],     # measured
        "deep_ocean":      [4, 16, 65],      # darker variant of measured ocean
        "coastal_desert":  [203, 191, 103],  # measured (rare tan variant)
        "desert":          [206, 169, 99],   # measured
        "coastline":       [190, 180, 140],  # sandy tone, no distinct vanilla color
        "farmland":        [200, 214, 107],  # measured
        "grasslands":      [86, 124, 27],    # measured
        "forest":          [0, 86, 6],       # measured
        "hills":           [112, 74, 31],    # measured
        "mountain":        [65, 42, 17],     # measured (vanilla uses brown, not grey)
        "highland":        [158, 130, 77],   # measured
        "jungle":          [20, 70, 15],     # forest-family variant, kept distinct
        "marsh":           [75, 147, 174],   # measured
        "steppe":          [146, 146, 63],   # interpolated grassland/desert tone
        "tundra":          [150, 155, 140],  # cool grassland tone, no distinct vanilla color
        "ice_sheet":       [255, 255, 255],  # measured
    }

    def __init__(self, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT):
        self.width = width
        self.height = height

    def generate_terrain_bmp(self, heightmap: np.ndarray,
                              land_mask: np.ndarray) -> np.ndarray:
        """Generates terrain.bmp mapping climate zones to indexed colors."""
        h, w = heightmap.shape
        terrain_canvas = np.zeros((h, w, 3), dtype=np.uint8)

        # Scale thresholds relative to a 2048-height reference map
        scale = h / 2048.0
        polar_low = 250 * scale
        polar_high = h - 250 * scale
        subpolar_low = 450 * scale
        subpolar_high = h - 450 * scale
        temperate_low = 650 * scale
        temperate_high = h - 650 * scale
        subtropical_low = 900 * scale
        subtropical_high = h - 850 * scale  # original subtropical upper bound was 1198
        tropical_split = 1050 * scale
        coastal_low = 500 * scale
        coastal_high = 800 * scale

        # Ocean
        terrain_canvas[~land_mask] = self.TERRAIN_COLORS["ocean"]

        # Deep ocean (very low elevation sea)
        deep_sea = (~land_mask) & (heightmap < 30)
        terrain_canvas[deep_sea] = self.TERRAIN_COLORS["deep_ocean"]

        # Land terrain classification by latitude + elevation
        for y in range(h):
            row_mask = land_mask[y, :]
            if not np.any(row_mask):
                continue

            row_heights = heightmap[y, :]
            is_mountain = row_heights > 190
            is_hills = (row_heights > 150) & (~is_mountain)
            is_highland = (row_heights > 170) & (~is_mountain) & (~is_hills)

            # Latitude-based biome assignment
            if y < polar_low or y > polar_high:  # Polar
                terrain_canvas[y, row_mask & ~is_mountain & ~is_hills] = self.TERRAIN_COLORS["ice_sheet"]
                terrain_canvas[y, row_mask & is_hills] = self.TERRAIN_COLORS["tundra"]
            elif y < subpolar_low or y > subpolar_high:  # Subpolar
                terrain_canvas[y, row_mask & ~is_mountain & ~is_hills] = self.TERRAIN_COLORS["tundra"]
                terrain_canvas[y, row_mask & is_hills] = self.TERRAIN_COLORS["steppe"]
            elif y < temperate_low or y > temperate_high:  # Temperate
                terrain_canvas[y, row_mask & ~is_mountain & ~is_hills & ~is_highland] = self.TERRAIN_COLORS["farmland"]
                terrain_canvas[y, row_mask & is_highland] = self.TERRAIN_COLORS["grasslands"]
                terrain_canvas[y, row_mask & is_hills] = self.TERRAIN_COLORS["hills"]
            elif y < subtropical_low or y > subtropical_high:  # Subtropical
                terrain_canvas[y, row_mask & ~is_mountain & ~is_hills] = self.TERRAIN_COLORS["grasslands"]
                terrain_canvas[y, row_mask & is_hills] = self.TERRAIN_COLORS["forest"]
            elif y < tropical_split:  # Tropical (north)
                terrain_canvas[y, row_mask & ~is_mountain & ~is_hills] = self.TERRAIN_COLORS["jungle"]
                terrain_canvas[y, row_mask & is_hills] = self.TERRAIN_COLORS["marsh"]
            else:  # Tropical (south)
                terrain_canvas[y, row_mask & ~is_mountain & ~is_hills] = self.TERRAIN_COLORS["jungle"]
                terrain_canvas[y, row_mask & is_hills] = self.TERRAIN_COLORS["forest"]

            # Mountains always same
            terrain_canvas[y, row_mask & is_mountain] = self.TERRAIN_COLORS["mountain"]

            # Coastal desert near sea
            if coastal_low < y < coastal_high:
                coastal_zone = row_mask & (heightmap[y, :] < 130) & (~is_mountain) & (~is_hills)
                if np.any(coastal_zone):
                    terrain_canvas[y, coastal_zone] = self.TERRAIN_COLORS["coastal_desert"]

        return terrain_canvas

    def classify_climate_zones(self, province_infos: List[ProvinceInfo]) -> Dict[str, List[int]]:
        """Groups province IDs into climate zones based on latitude."""
        zones = {
            "mild_winter": [],
            "normal_winter": [],
            "severe_winter": [],
            "equatorial_tropical": [],
            "arid": [],
            "semi_arid": [],
            "monsoon": [],
            "equatorial_rain": [],
        }

        # Scale thresholds relative to a 2048-height reference map
        h = self.height
        scale = h / 2048.0

        for p in province_infos:
            if p.is_sea or p.is_wasteland:
                continue
            y = p.center_y
            pid = p.id

            if y < 300 * scale or y > h - 300 * scale:
                zones["severe_winter"].append(pid)
            elif y < 500 * scale or y > h - 500 * scale:
                zones["normal_winter"].append(pid)
            elif 900 * scale <= y <= h - 850 * scale:
                zones["equatorial_tropical"].append(pid)
            elif 700 * scale <= y < 900 * scale:
                zones["monsoon"].append(pid)
            elif 500 * scale <= y < 700 * scale:
                zones["semi_arid"].append(pid)
            else:
                zones["mild_winter"].append(pid)

        return zones


# ═══════════════════════════════════════════════════════════════
#  NORMAL MAP GENERATOR
# ═══════════════════════════════════════════════════════════════

class NormalMapGenerator:
    """Generates world_normal.bmp from heightmap for EU4 lighting."""

    @staticmethod
    def generate(heightmap: np.ndarray, intensity: float = 1.5) -> np.ndarray:
        """Returns a normal-map ndarray from a grayscale heightmap array."""
        hm = heightmap.astype(np.float32)
        sobel_x = cv2.Sobel(hm, cv2.CV_32F, 1, 0, ksize=-1) * intensity
        sobel_y = cv2.Sobel(hm, cv2.CV_32F, 0, 1, ksize=-1) * intensity
        z = np.ones_like(hm)
        magnitude = np.sqrt(sobel_x ** 2 + sobel_y ** 2 + z ** 2)

        r = ((sobel_x / magnitude + 1.0) * 127.5).astype(np.uint8)
        g = ((sobel_y / magnitude + 1.0) * 127.5).astype(np.uint8)
        b = ((z / magnitude + 1.0) * 127.5).astype(np.uint8)

        return cv2.merge([r, g, b])


# ═══════════════════════════════════════════════════════════════
#  WATERCOLOR MAP GENERATOR
# ═══════════════════════════════════════════════════════════════

class WatercolorGenerator:
    """Generates parchment-style watercolor.bmp background map."""

    @staticmethod
    def generate(land_mask: np.ndarray) -> np.ndarray:
        """Generates a parchment-style watercolor background map."""
        height, width = land_mask.shape

        base_parchment = np.zeros((height, width, 3), dtype=np.float32)
        base_parchment[:, :, 0] = 238
        base_parchment[:, :, 1] = 222
        base_parchment[:, :, 2] = 195

        land_color_layer = np.zeros((height, width, 3), dtype=np.float32)
        land_color_layer[:, :, 0] = 90
        land_color_layer[:, :, 1] = 150
        land_color_layer[:, :, 2] = 100

        mask_8bit = (land_mask * 255).astype(np.uint8)
        blurred = cv2.GaussianBlur(mask_8bit, (51, 51), 0).astype(np.float32) / 255.0
        blurred_3d = np.atleast_3d(blurred)

        blended = (land_color_layer * blurred_3d) + (base_parchment * (1.0 - blurred_3d))
        noise = np.random.normal(0, 6.0, (height, width, 1)).astype(np.float32)

        return np.clip(blended + noise, 0, 255).astype(np.uint8)
