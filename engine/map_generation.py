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
    layout_style: str = "continents_islands"
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
    forced_ocean_location: str = "south"  # north, south, both, neither
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

    def generate_falloff_mask(self) -> np.ndarray:
        """
        Generates 2D boundary arrays (0.0–1.0) shaping macro-geographies.
        Controls where land masses can appear on the map.
        """
        y, x = np.ogrid[:self.height, :self.width]
        cx, cy = self.width / 2.0, self.height / 2.0
        nx = (x - cx) / cx
        ny = (y - cy) / cy

        # Apply forced ocean location
        ocean_mask = np.ones((self.height, self.width), dtype=np.float32)

        if self.config.forced_ocean_location == "south":
            south_penalty = np.clip(ny * 1.5, 0, 1) ** 0.5
            ocean_mask = 1.0 - south_penalty * 0.8
        elif self.config.forced_ocean_location == "north":
            north_penalty = np.clip(-ny * 1.5, 0, 1) ** 0.5
            ocean_mask = 1.0 - north_penalty * 0.8
        elif self.config.forced_ocean_location == "both":
            edge_penalty = np.clip(np.abs(ny) * 1.5, 0, 1) ** 0.5
            ocean_mask = 1.0 - edge_penalty * 0.6

        # Apply layout style shaping
        if self.config.layout_style == "pangea":
            distance = np.sqrt(nx**2 + ny**2)
            shape_mask = np.clip(1.0 - (distance ** 2), 0, 1)
        elif self.config.layout_style == "continents":
            wave = 0.5 * (np.cos(nx * np.pi * 2.5) + 1.0)
            shape_mask = np.clip(wave * (1.0 - (ny ** 4)), 0, 1)
        elif self.config.layout_style == "archipelago":
            shape_mask = np.ones((self.height, self.width), dtype=np.float32) * 0.45
        elif self.config.layout_style == "island_grid":
            grid_x = np.sin(nx * np.pi * 4) ** 2
            grid_y = np.sin(ny * np.pi * 3) ** 2
            shape_mask = np.clip(grid_x * grid_y * 0.7 + 0.15, 0, 1)
        else:  # continents_islands (default)
            wave = 0.5 * (np.cos(nx * np.pi * 2.5) + 1.0)
            shape_mask = np.clip((wave * 0.8) + 0.15, 0, 1)

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
            octaves=8,
            persistence=0.55,
            warp_strength=self.config.warp_strength,
            warp_scale=self.config.warp_scale
        )

        # Apply continent-scale detail layer
        continent_noise = noise_gen.generate_fbm(
            self.width, self.height,
            base_scale=self.config.perlin_scale * 0.3,
            octaves=4,
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

        # Sea pixels get deep blue
        provinces_bmp[~land_mask] = [0, 40, 80]

        # Land pixels get their province color
        for p_idx in range(min(num_provinces, active_seeds + 1)):
            mask = closest_indices == p_idx
            provinces_bmp[mask & land_mask] = unique_colors[p_idx]

        # Compute province information
        province_infos = self._compute_province_info(
            provinces_bmp, unique_colors, heightmap, land_mask,
            closest_indices, is_micro_world, num_provinces
        )

        return provinces_bmp, province_infos, is_micro_world

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
                # Province has no land pixels (sea or unused)
                infos.append(ProvinceInfo(
                    id=p_idx + 1,
                    color=color,
                    is_sea=True,
                    is_wasteland=(is_micro_world and p_idx == num_provinces - 1)
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
                        min_flow: int = 800) -> Tuple[np.ndarray, Dict[int, int]]:
        """
        Generates river map and returns province river counts.
        Returns (river_bmp_rgb, province_river_counts).
        """
        height, width = heightmap.shape
        flow_acc = np.ones((height, width), dtype=np.int64)

        # Sort cells by elevation (highest first)
        flat_elevations = heightmap.ravel().astype(np.float64)
        sorted_indices = np.argsort(-flat_elevations)

        dy = [-1, -1, -1, 0, 0, 1, 1, 1]
        dx = [-1, 0, 1, -1, 1, -1, 0, 1]

        for flat_idx in sorted_indices:
            y = flat_idx // width
            x = flat_idx % width
            if not land_mask[y, x]:
                continue

            current_elev = int(heightmap[y, x])
            steepest_drop = 0
            target = None

            for i in range(8):
                ny, nx = y + dy[i], x + dx[i]
                if 0 <= ny < height and 0 <= nx < width:
                    drop = current_elev - int(heightmap[ny, nx])
                    if drop > steepest_drop:
                        steepest_drop = drop
                        target = (ny, nx)

            if target:
                ny, nx = target
                flow_acc[ny, nx] += flow_acc[y, x]

        # Paint river pixels
        river_map = np.full((height, width, 3), 255, dtype=np.uint8)
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
#  TERRAIN & CLIMATE CLASSIFIER
# ═══════════════════════════════════════════════════════════════

class TerrainClassifier:
    """Classifies terrain and generates terrain.bmp, climate.txt data."""

    # EU4 terrain type color codes
    TERRAIN_COLORS = {
        "ocean":           [0, 40, 80],
        "deep_ocean":      [0, 20, 60],
        "coastal_desert":  [240, 220, 160],
        "desert":          [220, 200, 130],
        "coastline":       [200, 200, 200],
        "farmland":        [80, 140, 60],
        "grasslands":      [100, 160, 70],
        "forest":          [60, 120, 50],
        "hills":           [100, 130, 70],
        "mountain":        [90, 90, 90],
        "highland":        [120, 110, 80],
        "jungle":          [40, 100, 40],
        "marsh":           [100, 140, 90],
        "steppe":          [180, 170, 120],
        "tundra":          [180, 180, 180],
        "ice_sheet":       [220, 220, 240],
    }

    def __init__(self, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT):
        self.width = width
        self.height = height

    def generate_terrain_bmp(self, heightmap: np.ndarray,
                              land_mask: np.ndarray) -> np.ndarray:
        """Generates terrain.bmp mapping climate zones to indexed colors."""
        h, w = heightmap.shape
        terrain_canvas = np.zeros((h, w, 3), dtype=np.uint8)

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
            if y < 250 or y > 1798:  # Polar
                terrain_canvas[y, row_mask & ~is_mountain & ~is_hills] = self.TERRAIN_COLORS["ice_sheet"]
                terrain_canvas[y, row_mask & is_hills] = self.TERRAIN_COLORS["tundra"]
            elif y < 450 or y > 1598:  # Subpolar
                terrain_canvas[y, row_mask & ~is_mountain & ~is_hills] = self.TERRAIN_COLORS["tundra"]
                terrain_canvas[y, row_mask & is_hills] = self.TERRAIN_COLORS["steppe"]
            elif y < 650 or y > 1398:  # Temperate
                terrain_canvas[y, row_mask & ~is_mountain & ~is_hills & ~is_highland] = self.TERRAIN_COLORS["farmland"]
                terrain_canvas[y, row_mask & is_highland] = self.TERRAIN_COLORS["grasslands"]
                terrain_canvas[y, row_mask & is_hills] = self.TERRAIN_COLORS["hills"]
            elif y < 900 or y > 1198:  # Subtropical
                terrain_canvas[y, row_mask & ~is_mountain & ~is_hills] = self.TERRAIN_COLORS["grasslands"]
                terrain_canvas[y, row_mask & is_hills] = self.TERRAIN_COLORS["forest"]
            elif y < 1050:  # Tropical (north)
                terrain_canvas[y, row_mask & ~is_mountain & ~is_hills] = self.TERRAIN_COLORS["jungle"]
                terrain_canvas[y, row_mask & is_hills] = self.TERRAIN_COLORS["marsh"]
            else:  # Tropical (south)
                terrain_canvas[y, row_mask & ~is_mountain & ~is_hills] = self.TERRAIN_COLORS["jungle"]
                terrain_canvas[y, row_mask & is_hills] = self.TERRAIN_COLORS["forest"]

            # Mountains always same
            terrain_canvas[y, row_mask & is_mountain] = self.TERRAIN_COLORS["mountain"]

            # Coastal desert near sea
            if 500 < y < 800:
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

        for p in province_infos:
            if p.is_sea or p.is_wasteland:
                continue
            y = p.center_y
            pid = p.id

            if y < 300 or y > 1748:
                zones["severe_winter"].append(pid)
            elif y < 500 or y > 1548:
                zones["normal_winter"].append(pid)
            elif 900 <= y <= 1198:
                zones["equatorial_tropical"].append(pid)
            elif 700 <= y < 900:
                zones["monsoon"].append(pid)
            elif 500 <= y < 700:
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
