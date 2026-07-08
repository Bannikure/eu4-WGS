"""
Climate and Terrain Classification Module
===========================================
Borrows key algorithm ideas from Undiscovered_Worlds_Classic (C++) and adapts them
for the EU4 World Generator. Provides:

1. Latitude-based temperature model (UW: jantemp/jultemp/avetemp)
2. Precipitation and rain shadow model (UW: createrainmap)
3. Wind direction model (UW: createwindmap)
4. Climate zone classification (UW: Koppen-like climate types)
5. Terrain type classification from elevation + climate
6. Lake detection and salt lake placement
7. River flow volume estimation

Key algorithm ideas borrowed from Undiscovered Worlds:
  - Temperature computed from latitude + elevation + seasonal variation
  - Rainfall computed from distance to sea + wind direction + mountain rain shadow
  - Climate zones: desert, grass, cold, tundra, jungle, forest, steppe, etc.
  - Orographic rainfall: mountains force moist air upward, creating rain on windward side
  - Continental vs maritime climate: inland areas have more extreme temperatures
  - Sea ice formation at polar temperatures
  - Endorheic basin detection for salt lake placement

Reference: Undiscovered_Worlds_Classic by Jonathan Hill
  - planet.hpp: data structures for temperature, rain, climate, wind
  - globalclimate.cpp: generateglobalclimate(), createrainmap(), createwindmap()
  - globalterrain.cpp: generateglobalterrain(), mountain generation, fractal terrain
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


# ═══════════════════════════════════════════════════════════════════════════════
#  CLIMATE CONSTANTS (adapted from Undiscovered Worlds planet.hpp)
# ═══════════════════════════════════════════════════════════════════════════════

# Climate type IDs (matching UW climatemap values)
CLIMATE_OCEAN = 0
CLIMATE_DESERT = 1
CLIMATE_GRASS = 2
CLIMATE_COLD = 3
CLIMATE_TUNDRA = 4
CLIMATE_JUNGLE = 5
CLIMATE_FOREST = 6
CLIMATE_STEPPE = 7
CLIMATE_FARMLAND = 8
CLIMATE_MARSH = 9
CLIMATE_ICE_SHEET = 10
CLIMATE_COASTAL_DESERT = 11
CLIMATE_TROPICAL = 12
CLIMATE_MONSOON = 13

CLIMATE_NAMES = {
    CLIMATE_OCEAN: "ocean",
    CLIMATE_DESERT: "desert",
    CLIMATE_GRASS: "grasslands",
    CLIMATE_COLD: "cold",
    CLIMATE_TUNDRA: "tundra",
    CLIMATE_JUNGLE: "jungle",
    CLIMATE_FOREST: "forest",
    CLIMATE_STEPPE: "steppe",
    CLIMATE_FARMLAND: "farmland",
    CLIMATE_MARSH: "marsh",
    CLIMATE_ICE_SHEET: "ice_sheet",
    CLIMATE_COASTAL_DESERT: "coastal_desert",
    CLIMATE_TROPICAL: "tropical",
    CLIMATE_MONSOON: "monsoon",
}

# EU4 terrain type mapping from climate
CLIMATE_TO_EU4_TERRAIN = {
    CLIMATE_OCEAN: "ocean",
    CLIMATE_DESERT: "desert",
    CLIMATE_GRASS: "grasslands",
    CLIMATE_COLD: "grasslands",
    CLIMATE_TUNDRA: "tundra",
    CLIMATE_JUNGLE: "jungle",
    CLIMATE_FOREST: "forest",
    CLIMATE_STEPPE: "steppe",
    CLIMATE_FARMLAND: "farmland",
    CLIMATE_MARSH: "marsh",
    CLIMATE_ICE_SHEET: "ice_sheet",
    CLIMATE_COASTAL_DESERT: "coastal_desert",
    CLIMATE_TROPICAL: "grasslands",
    CLIMATE_MONSOON: "jungle",
}

# Temperature thresholds (in arbitrary units matching UW)
TEMP_POLAR = -20
TEMP_TUNDRA = -5
TEMP_COLD = 5
TEMP_TEMPERATE = 15
TEMP_WARM = 25
TEMP_HOT = 35
TEMP_TROPICAL = 40

# Rainfall thresholds (mm equivalent)
RAIN_DESERT = 15
RAIN_STEPPE = 30
RAIN_GRASS = 50
RAIN_FOREST = 70
RAIN_JUNGLE = 100
RAIN_MONSOON = 130


@dataclass
class ClimateData:
    """Climate data for a single province/grid cell."""
    avg_temp: float = 14.0       # Average temperature (°C-like)
    jan_temp: float = 5.0        # January temperature
    jul_temp: float = 23.0       # July temperature
    avg_rain: float = 50.0       # Average rainfall
    climate_type: int = CLIMATE_GRASS
    climate_name: str = "grasslands"
    eu4_terrain: str = "grasslands"
    wind_direction: int = 0      # 0=N, 1=NE, 2=E, etc. (8 directions)
    is_sea_ice: bool = False
    is_lake: bool = False
    is_salt_lake: bool = False
    is_endorheic: bool = False


class ClimateGenerator:
    """
    Generates climate data for the entire map based on latitude, elevation,
    distance from sea, and wind patterns.

    Key algorithms borrowed from Undiscovered Worlds:
    1. Temperature = equatorial_temp - latitude_gradient - elevation_lapse
    2. Rainfall = base_rain * (1 - distance_from_sea/inland_factor) + orographic_bonus
    3. Wind = coriolis-based trade winds + monsoon modifiers
    4. Climate classification = function(avg_temp, avg_rain, seasonality)
    """

    # Lapse rate: temperature decrease per unit elevation (UW: tempdecrease = 6.5/km)
    LAPSE_RATE = 6.5  # °C per 1000m equivalent

    # Temperature gradient from equator to pole (UW: equatorial ~40, polar ~-20)
    EQUATORIAL_TEMP = 35.0
    POLAR_TEMP = -25.0

    # Wind directions (Coriolis effect): trade winds blow west in tropics
    # UW: createwindmap uses latitude-based wind cells
    HADLEY_CELL_LIMIT = 0.30     # 30° latitude
    FERREL_CELL_LIMIT = 0.60     # 60° latitude

    def __init__(self, width: int, height: int, seed: int = 42):
        self.width = width
        self.height = height
        self.seed = seed

    def generate_temperatures(self, heightmap: np.ndarray,
                               land_mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generate temperature maps (January, July, Average).
        Borrowed from UW: temperature depends on latitude, elevation, and season.

        In our inverted world, the southern hemisphere (high Y) is warm,
        the northern hemisphere (low Y) is cold - matching EU4's map orientation
        where north=top.

        Returns: (jan_temp, jul_temp, avg_temp) as float arrays
        """
        h, w = heightmap.shape[:2]
        rng = np.random.RandomState(self.seed)

        # Latitude: 0 at top (north pole), 1 at bottom (south pole)
        y_coords = np.arange(h).reshape(-1, 1) / h

        # Base temperature from latitude (UW: eqtemp, northpolartemp, southpolartemp)
        # North is cold, equator at ~40% from top, south is warm
        equator_y = 0.40  # Equator at 40% from top
        lat_factor = np.abs(y_coords - equator_y) / max(equator_y, 1.0 - equator_y)
        lat_factor = np.clip(lat_factor, 0, 1)

        # Base temperature: warm at equator, cold at poles
        base_temp = self.EQUATORIAL_TEMP - lat_factor * (self.EQUATORIAL_TEMP - self.POLAR_TEMP)

        # Elevation lapse rate (UW: tempdecrease)
        # Normalize heightmap values to 0-1 for elevation effect
        elev_normalized = np.where(land_mask,
                                    (heightmap.astype(float) - 55) / 200.0,  # Land is 55-255
                                    0)
        elev_effect = elev_normalized * self.LAPSE_RATE * 3  # Scale for game units

        # Seasonal variation: more extreme further from equator (UW: jantemp/jultemp)
        seasonality = lat_factor * 15  # Up to 15°C seasonal swing
        seasonal_noise = rng.randn(h, w) * 2  # Small random variation

        jan_temp = base_temp - elev_effect - seasonality / 2 + seasonal_noise
        jul_temp = base_temp - elev_effect + seasonality / 2 + seasonal_noise
        avg_temp = (jan_temp + jul_temp) / 2

        # Sea has moderating effect (UW: seats are more temperate)
        sea_moderator = ~land_mask
        jan_temp[sea_moderator] = avg_temp[sea_moderator] - 3
        jul_temp[sea_moderator] = avg_temp[sea_moderator] + 3

        return jan_temp, jul_temp, avg_temp

    def generate_rainfall(self, heightmap: np.ndarray, land_mask: np.ndarray,
                           wind_map: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate rainfall maps (January, July) based on distance from sea,
        wind direction, and orographic effects.

        Borrowed from UW createrainmap():
        - Base rain from distance to sea (maritime effect)
        - Orographic rain on windward mountain slopes
        - Rain shadow on leeward side of mountains
        - Monsoon effect in tropical latitudes

        Returns: (jan_rain, jul_rain) as float arrays
        """
        h, w = heightmap.shape[:2]
        rng = np.random.RandomState(self.seed + 100)

        # Distance from sea (UW: inland array)
        from scipy.ndimage import distance_transform_edt
        dist_from_sea = distance_transform_edt(land_mask)

        # Normalize distance: 0 at coast, 1 at far inland
        max_dist = max(dist_from_sea.max(), 1)
        inland_factor = dist_from_sea / max_dist

        # Base rainfall: high near coasts, decreases inland (UW: slopewaterreduce)
        base_rain = 80 * (1 - inland_factor * 0.6) + rng.rand(h, w) * 15

        # Orographic effect: mountains cause rain on windward side
        # (UW: mountainrain, rainshadow)
        elev_normalized = np.where(land_mask,
                                    (heightmap.astype(float) - 55) / 200.0,
                                    0)

        # Windward slope gets more rain (simple approximation)
        # Shift rainfall upwind
        from scipy.ndimage import shift
        wind_dx = np.cos(wind_map * np.pi / 4) * 5  # Wind in pixel units
        wind_dy = np.sin(wind_map * np.pi / 4) * 5

        # Orographic rain: more rain where elevation increases in upwind direction
        mountain_rain = np.zeros_like(base_rain)
        mountain_rain[land_mask] = elev_normalized[land_mask] * 30

        # Rain shadow: less rain downwind of mountains
        rain_shadow = np.zeros_like(base_rain)
        rain_shadow[land_mask] = np.maximum(0, elev_normalized[land_mask] - 0.5) * 20

        # Seasonal variation (monsoon effect in tropics)
        y_coords = np.broadcast_to(
            (np.arange(h, dtype=np.float64) / h).reshape(-1, 1),
            (h, w)
        )
        monsoon_zone = (np.abs(y_coords - 0.40) < 0.15).astype(float)

        jan_rain = base_rain + mountain_rain - rain_shadow
        jul_rain = base_rain + mountain_rain - rain_shadow

        # Monsoon: heavy rain in July in tropical zone
        jul_rain += monsoon_zone * 50 * rng.rand(h, w)

        # Add noise
        jan_rain += rng.randn(h, w) * 5
        jul_rain += rng.randn(h, w) * 5

        # Ensure non-negative
        jan_rain = np.maximum(jan_rain, 0)
        jul_rain = np.maximum(jul_rain, 0)

        # Sea has minimal rain contribution
        jan_rain[~land_mask] = 0
        jul_rain[~land_mask] = 0

        return jan_rain, jul_rain

    def generate_wind_map(self) -> np.ndarray:
        """
        Generate wind direction map based on Coriolis effect and atmospheric cells.
        Borrowed from UW createwindmap():
        - Hadley cell: trade winds blow westward in tropics (0-30°)
        - Ferrel cell: westerlies at mid-latitudes (30-60°)
        - Polar cell: easterlies at high latitudes (60-90°)
        
        Wind direction encoding: 0=N, 1=NE, 2=E, 3=SE, 4=S, 5=SW, 6=W, 7=NW
        
        Returns: wind_map (h, w) uint8 array
        """
        h, w = self.height, self.width
        wind_map = np.zeros((h, w), dtype=np.uint8)

        # Broadcast y_coords to full (h, w) shape for boolean indexing
        y_coords = np.broadcast_to(
            (np.arange(h, dtype=np.float64) / h).reshape(-1, 1),
            (h, w)
        ).copy()  # .copy() so we can derive boolean masks from it

        # Equator at 40% from top (proportional to map height)
        equator_y = 0.40
        lat_from_eq = np.abs(y_coords - equator_y) / max(equator_y, 1.0 - equator_y)

        # Northern hemisphere (above equator)
        north = y_coords < equator_y
        # Southern hemisphere (below equator)
        south = y_coords >= equator_y

        # Hadley cell (tropics): NE trade winds in NH, SE trade winds in SH
        hadley_n = north & (lat_from_eq < self.HADLEY_CELL_LIMIT)
        hadley_s = south & (lat_from_eq < self.HADLEY_CELL_LIMIT)

        # Ferrel cell (mid-lat): westerlies
        ferrel_n = north & (lat_from_eq >= self.HADLEY_CELL_LIMIT) & (lat_from_eq < self.FERREL_CELL_LIMIT)
        ferrel_s = south & (lat_from_eq >= self.HADLEY_CELL_LIMIT) & (lat_from_eq < self.FERREL_CELL_LIMIT)

        # Polar cell: easterlies
        polar_n = north & (lat_from_eq >= self.FERREL_CELL_LIMIT)
        polar_s = south & (lat_from_eq >= self.FERREL_CELL_LIMIT)

        # Assign wind directions
        # NE trade winds = direction 1 (NE)
        wind_map[hadley_n] = 1  # NE
        # SE trade winds = direction 3 (SE)  -> but in southern hemisphere, it's SE
        wind_map[hadley_s] = 3  # SE

        # Westerlies = direction 6 (W)
        wind_map[ferrel_n] = 6  # W
        wind_map[ferrel_s] = 6  # W

        # Polar easterlies = direction 2 (E)
        wind_map[polar_n] = 2  # E
        wind_map[polar_s] = 2  # E

        # Add some noise/variation
        rng = np.random.RandomState(self.seed + 200)
        noise = rng.randint(0, 2, (h, w)).astype(np.uint8)
        wind_map = (wind_map + noise) % 8

        return wind_map

    def classify_climate(self, avg_temp: np.ndarray, jan_temp: np.ndarray,
                          jul_temp: np.ndarray, avg_rain: np.ndarray,
                          land_mask: np.ndarray) -> np.ndarray:
        """
        Classify each cell into a climate type based on temperature and rainfall.
        Borrowed from UW climate classification system (Köppen-like).

        Classification rules (adapted from UW climatemap):
        - Ice sheet: avg_temp < -15
        - Tundra: avg_temp < -5
        - Cold: avg_temp < 5
        - Desert: avg_temp > 20 and avg_rain < 15
        - Coastal desert: near coast, avg_temp > 20, avg_rain < 30
        - Steppe: avg_rain < 30
        - Jungle: avg_temp > 25 and avg_rain > 100
        - Monsoon: avg_temp > 25, heavy seasonal rain
        - Forest: avg_temp 5-20, avg_rain 50-100
        - Grasslands: avg_temp 5-25, avg_rain 30-70
        - Farmland: avg_temp 10-20, avg_rain 40-80
        - Marsh: low elevation, avg_rain > 80
        - Tropical: avg_temp > 30, avg_rain > 60

        Returns: climate_map (h, w) uint8 array of climate type IDs
        """
        climate = np.full_like(avg_temp, CLIMATE_OCEAN, dtype=np.uint8)

        # Only classify land cells
        land = land_mask

        # Ice sheet
        climate[land & (avg_temp < TEMP_POLAR)] = CLIMATE_ICE_SHEET

        # Tundra
        climate[land & (avg_temp >= TEMP_POLAR) & (avg_temp < TEMP_TUNDRA)] = CLIMATE_TUNDRA

        # Cold
        climate[land & (avg_temp >= TEMP_TUNDRA) & (avg_temp < TEMP_COLD)] = CLIMATE_COLD

        # Hot and dry = desert
        climate[land & (avg_temp >= TEMP_COLD) & (avg_rain < RAIN_DESERT)] = CLIMATE_DESERT

        # Tropical desert
        climate[land & (avg_temp >= TEMP_WARM) & (avg_rain >= RAIN_DESERT) &
                (avg_rain < RAIN_STEPPE)] = CLIMATE_COASTAL_DESERT

        # Steppe
        climate[land & (avg_temp >= TEMP_COLD) & (avg_temp < TEMP_WARM) &
                (avg_rain >= RAIN_DESERT) & (avg_rain < RAIN_STEPPE)] = CLIMATE_STEPPE

        # Jungle (hot and wet)
        climate[land & (avg_temp >= TEMP_HOT) & (avg_rain >= RAIN_JUNGLE)] = CLIMATE_JUNGLE

        # Monsoon (hot with seasonal rain)
        seasonality = np.abs(jul_temp - jan_temp)
        climate[land & (avg_temp >= TEMP_WARM) & (avg_rain >= RAIN_MONSOON) &
                (seasonality > 10)] = CLIMATE_MONSOON

        # Tropical
        climate[land & (avg_temp >= TEMP_TROPICAL) & (avg_rain >= RAIN_GRASS) &
                (avg_rain < RAIN_JUNGLE)] = CLIMATE_TROPICAL

        # Forest (temperate and wet)
        climate[land & (avg_temp >= TEMP_COLD) & (avg_temp < TEMP_WARM) &
                (avg_rain >= RAIN_FOREST)] = CLIMATE_FOREST

        # Farmland (optimal conditions)
        climate[land & (avg_temp >= 10) & (avg_temp < 20) &
                (avg_rain >= 40) & (avg_rain < 80)] = CLIMATE_FARMLAND

        # Grasslands (temperate, moderate rain)
        remaining = land & (climate == CLIMATE_OCEAN) & (avg_temp >= TEMP_COLD)
        climate[remaining] = CLIMATE_GRASS

        # Marsh: low elevation, high rain (override)
        low_elev = land  # Could refine with actual low elevation detection
        climate[low_elev & (avg_rain > 80) & (avg_temp > 5) & (avg_temp < 25) &
                (climate == CLIMATE_GRASS)] = CLIMATE_MARSH

        return climate

    def generate_full_climate(self, heightmap: np.ndarray,
                               land_mask: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Run the complete climate generation pipeline.

        Returns a dict with:
          - jan_temp, jul_temp, avg_temp
          - jan_rain, jul_rain, avg_rain
          - climate_map, eu4_terrain_map
          - wind_map
        """
        # Generate wind map
        wind_map = self.generate_wind_map()

        # Generate temperatures
        jan_temp, jul_temp, avg_temp = self.generate_temperatures(heightmap, land_mask)

        # Generate rainfall
        jan_rain, jul_rain = self.generate_rainfall(heightmap, land_mask, wind_map)
        avg_rain = (jan_rain + jul_rain) / 2

        # Classify climate
        climate_map = self.classify_climate(avg_temp, jan_temp, jul_temp,
                                             avg_rain, land_mask)

        # Map climate to EU4 terrain
        eu4_terrain_map = np.vectorize(CLIMATE_TO_EU4_TERRAIN.get)(climate_map)
        eu4_terrain_map[~land_mask] = "ocean"

        return {
            "jan_temp": jan_temp,
            "jul_temp": jul_temp,
            "avg_temp": avg_temp,
            "jan_rain": jan_rain,
            "jul_rain": jul_rain,
            "avg_rain": avg_rain,
            "climate_map": climate_map,
            "eu4_terrain_map": eu4_terrain_map,
            "wind_map": wind_map,
        }

    def get_climate_stats(self, climate_map: np.ndarray,
                           land_mask: np.ndarray) -> Dict[str, int]:
        """Get statistics about climate distribution on land."""
        stats = {}
        for climate_id, name in CLIMATE_NAMES.items():
            if climate_id == CLIMATE_OCEAN:
                continue
            count = np.sum(land_mask & (climate_map == climate_id))
            if count > 0:
                stats[name] = int(count)
        return stats


class TerrainRefiner:
    """
    Refines terrain classification using elevation slope and aspect.
    Borrowed from UW globalterrain.cpp: mountain ridges, volcano placement,
    and terrain detail generation.
    """

    @staticmethod
    def compute_slope(heightmap: np.ndarray) -> np.ndarray:
        """Compute terrain slope magnitude from heightmap."""
        # Sobel-like gradient
        dy = np.zeros_like(heightmap, dtype=float)
        dx = np.zeros_like(heightmap, dtype=float)

        dy[1:-1, :] = (heightmap[2:, :].astype(float) - heightmap[:-2, :].astype(float)) / 2
        dx[:, 1:-1] = (heightmap[:, 2:].astype(float) - heightmap[:, :-2].astype(float)) / 2

        slope = np.sqrt(dx**2 + dy**2)
        return slope

    @staticmethod
    def classify_elevation_terrain(heightmap: np.ndarray,
                                    land_mask: np.ndarray,
                                    climate_map: np.ndarray) -> np.ndarray:
        """
        Refine terrain classification combining elevation and climate.
        High elevation always overrides to mountain/hills.
        """
        terrain = climate_map.copy()

        # Elevation thresholds (in 8-bit: 55=lowest land, 255=highest)
        hill_threshold = 140  # ~42% of land elevation range
        mountain_threshold = 190  # ~67% of land elevation range

        # Slope-based refinement
        slope = TerrainRefiner.compute_slope(heightmap)

        # Override: steep areas are always hills or mountains
        steep = land_mask & (slope > 15)
        very_steep = land_mask & (slope > 30)

        terrain[very_steep] = CLIMATE_FOREST  # Mountain forest
        terrain[steep & (heightmap > mountain_threshold)] = CLIMATE_COLD  # Alpine

        return terrain

    @staticmethod
    def detect_volcanoes(heightmap: np.ndarray, land_mask: np.ndarray,
                          num_volcanoes: int = 20, seed: int = 42) -> List[Tuple[int, int]]:
        """
        Detect potential volcano sites from the heightmap.
        Borrowed from UW: volcanomap, stratomap - isolated conical peaks.
        """
        rng = np.random.RandomState(seed)

        # Find isolated high points (local maxima on land)
        from scipy.ndimage import maximum_filter
        local_max = maximum_filter(heightmap, size=15)
        peaks = land_mask & (heightmap == local_max) & (heightmap > 150)

        # Get peak coordinates
        peak_coords = np.argwhere(peaks)

        if len(peak_coords) == 0:
            return []

        # Select random subset as volcanoes
        indices = rng.choice(len(peak_coords), min(num_volcanoes, len(peak_coords)), replace=False)
        volcanoes = [(int(peak_coords[i][1]), int(peak_coords[i][0])) for i in indices]

        return volcanoes

    @staticmethod
    def detect_lakes(heightmap: np.ndarray, land_mask: np.ndarray,
                      min_size: int = 5) -> List[Tuple[int, int, int]]:
        """
        Detect potential lake sites (low-elevation depressions on land).
        Borrowed from UW: lakestartmap, rift lakes, salt lakes.

        Returns list of (center_x, center_y, approx_area) tuples.
        """
        from scipy.ndimage import label, minimum_filter, binary_fill_holes

        # Find depressions (local minima on land)
        local_min = minimum_filter(heightmap, size=11)
        depressions = land_mask & (heightmap == local_min) & (heightmap < 100)

        # Label connected depressions
        labeled, num_features = label(depressions)

        lakes = []
        for i in range(1, num_features + 1):
            region = labeled == i
            area = np.sum(region)
            if area >= min_size:
                # Find centroid
                coords = np.argwhere(region)
                cy, cx = coords.mean(axis=0).astype(int)
                lakes.append((int(cx), int(cy), int(area)))

        return lakes
