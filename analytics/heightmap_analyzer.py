"""
Module 2: Heightmap Data Analyzer & Visualizer
=================================================
Provides comprehensive analysis of generated heightmaps and province data,
including elevation statistics, continent wealth analysis, religion spread,
technology distribution, and trade flow analytics.
"""

import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field
import json


@dataclass
class ElevationStats:
    """Statistical summary of elevation data."""
    min_elevation: float = 0.0
    max_elevation: float = 0.0
    mean_elevation: float = 0.0
    median_elevation: float = 0.0
    std_elevation: float = 0.0
    land_pixels: int = 0
    sea_pixels: int = 0
    land_percentage: float = 0.0
    mountain_pixels: int = 0
    hill_pixels: int = 0
    plains_pixels: int = 0
    coastal_pixels: int = 0


@dataclass
class ContinentStats:
    """Wealth and power statistics for a continent."""
    name: str = ""
    total_development: int = 0
    avg_development: float = 0.0
    province_count: int = 0
    country_count: int = 0
    avg_tech_level: float = 0.0
    total_trade_value: float = 0.0
    primary_religion: str = ""
    religion_spread: Dict[str, float] = field(default_factory=dict)
    military_power: float = 0.0
    economic_power: float = 0.0
    technology_power: float = 0.0
    overall_power_index: float = 0.0


@dataclass
class WorldAnalytics:
    """Complete world analytics summary."""
    elevation: ElevationStats = None
    continents: Dict[str, ContinentStats] = field(default_factory=dict)
    religion_distribution: Dict[str, int] = field(default_factory=dict)
    tech_group_distribution: Dict[str, int] = field(default_factory=dict)
    trade_flow_summary: Dict[str, float] = field(default_factory=dict)
    total_countries: int = 0
    total_provinces: int = 0
    total_land_provinces: int = 0
    total_sea_provinces: int = 0
    power_ranking: List[Dict[str, Any]] = field(default_factory=list)


class HeightmapAnalyzer:
    """
    Comprehensive heightmap and world data analyzer.
    Provides statistical analysis and data for visualization.
    """

    def __init__(self, map_height: int = 2048):
        self.map_height = map_height

    def analyze_elevation(self, heightmap: np.ndarray,
                           land_mask: np.ndarray) -> ElevationStats:
        """Compute detailed elevation statistics."""
        land_elevations = heightmap[land_mask]
        sea_elevations = heightmap[~land_mask]

        total = heightmap.size
        land_count = int(land_mask.sum())
        sea_count = total - land_count

        stats = ElevationStats(
            min_elevation=float(heightmap.min()),
            max_elevation=float(heightmap.max()),
            mean_elevation=float(heightmap.mean()),
            median_elevation=float(np.median(heightmap)),
            std_elevation=float(heightmap.std()),
            land_pixels=land_count,
            sea_pixels=sea_count,
            land_percentage=land_count / total * 100 if total > 0 else 0,
            mountain_pixels=int((heightmap[land_mask] > 190).sum()),
            hill_pixels=int(((heightmap[land_mask] > 150) & (heightmap[land_mask] <= 190)).sum()),
            plains_pixels=int(((heightmap[land_mask] > 120) & (heightmap[land_mask] <= 150)).sum()),
            coastal_pixels=int((heightmap[land_mask] <= 120).sum()),
        )

        return stats

    def analyze_continent_wealth(self, province_infos: List,
                                  countries: Dict) -> Dict[str, ContinentStats]:
        """
        Analyze wealth and power by continent.
        In this world, Africa and Asia are wealthiest/most powerful,
        Europe is poorest/weakest.
        """
        continent_data: Dict[str, Dict] = {}

        for p in province_infos:
            if p.is_sea or p.is_wasteland:
                continue

            cont = p.continent_name
            if cont not in continent_data:
                continent_data[cont] = {
                    "provinces": [],
                    "dev_scores": [],
                    "religions": {},
                    "tech_groups": [],
                }

            # Development based on latitude band (inverted power)
            dev = self._compute_inverted_development(p)
            continent_data[cont]["provinces"].append(p)
            continent_data[cont]["dev_scores"].append(dev)

            # Religion assignment
            rel = self._assign_inverted_religion(p, self.map_height)
            continent_data[cont]["religions"][rel] = continent_data[cont]["religions"].get(rel, 0) + 1

            # Tech group assignment
            tech = self._assign_inverted_tech(p)
            continent_data[cont]["tech_groups"].append(tech)

        # Build ContinentStats
        result = {}
        for cont_name, data in continent_data.items():
            dev_scores = data["dev_scores"]
            tech_groups = data["tech_groups"]
            total_dev = sum(dev_scores)

            # Determine primary religion
            rel_counts = data["religions"]
            primary_rel = max(rel_counts, key=rel_counts.get) if rel_counts else "unknown"

            # Compute power indices
            tech_map = {
                "chinese": 6, "indian": 5, "muslim": 4,
                "east_african": 3, "north_american": 2, "nomad_group": 1,
                "western": 0, "eastern": 0, "anatolian": 1
            }
            tech_scores = [tech_map.get(t, 0) for t in tech_groups]
            avg_tech = sum(tech_scores) / len(tech_scores) if tech_scores else 0

            economic_power = total_dev * (1 + avg_tech * 0.3)
            military_power = total_dev * (1 + avg_tech * 0.2)
            technology_power = avg_tech * len(dev_scores) * 0.5
            overall = (economic_power + military_power + technology_power) / 3

            result[cont_name] = ContinentStats(
                name=cont_name,
                total_development=total_dev,
                avg_development=sum(dev_scores) / len(dev_scores) if dev_scores else 0,
                province_count=len(dev_scores),
                country_count=sum(1 for c in countries.values()
                                  if hasattr(c, 'continent') and c.continent == cont_name),
                avg_tech_level=avg_tech,
                total_trade_value=total_dev * 0.8,
                primary_religion=primary_rel,
                religion_spread={k: v / sum(rel_counts.values())
                                 for k, v in rel_counts.items()},
                military_power=military_power,
                economic_power=economic_power,
                technology_power=technology_power,
                overall_power_index=overall,
            )

        return result

    def compute_religion_distribution(self, province_infos: List) -> Dict[str, int]:
        """Compute global religion distribution across all land provinces."""
        distribution = {}
        for p in province_infos:
            if p.is_sea or p.is_wasteland:
                continue
            rel = self._assign_inverted_religion(p, self.map_height)
            distribution[rel] = distribution.get(rel, 0) + 1
        return distribution

    def compute_tech_group_distribution(self, province_infos: List) -> Dict[str, int]:
        """Compute global tech group distribution."""
        distribution = {}
        for p in province_infos:
            if p.is_sea or p.is_wasteland:
                continue
            tech = self._assign_inverted_tech(p)
            distribution[tech] = distribution.get(tech, 0) + 1
        return distribution

    def compute_power_ranking(self, continent_stats: Dict[str, ContinentStats]) -> List[Dict[str, Any]]:
        """Rank continents by overall power index."""
        ranking = []
        for name, stats in continent_stats.items():
            ranking.append({
                "continent": name,
                "overall_power": round(stats.overall_power_index, 1),
                "economic_power": round(stats.economic_power, 1),
                "military_power": round(stats.military_power, 1),
                "technology_power": round(stats.technology_power, 1),
                "total_development": stats.total_development,
                "primary_religion": stats.primary_religion,
                "avg_tech_level": round(stats.avg_tech_level, 2),
            })
        ranking.sort(key=lambda x: x["overall_power"], reverse=True)
        return ranking

    def generate_full_analytics(self, heightmap: np.ndarray,
                                 land_mask: np.ndarray,
                                 province_infos: List,
                                 countries: Dict) -> WorldAnalytics:
        """Generate complete world analytics."""
        elev_stats = self.analyze_elevation(heightmap, land_mask)
        cont_stats = self.analyze_continent_wealth(province_infos, countries)
        rel_dist = self.compute_religion_distribution(province_infos)
        tech_dist = self.compute_tech_group_distribution(province_infos)
        power_rank = self.compute_power_ranking(cont_stats)

        land_provs = [p for p in province_infos if not p.is_sea and not p.is_wasteland]
        sea_provs = [p for p in province_infos if p.is_sea]

        # Trade flow summary
        trade_flow = {}
        for name, stats in cont_stats.items():
            trade_flow[name] = stats.total_trade_value

        return WorldAnalytics(
            elevation=elev_stats,
            continents=cont_stats,
            religion_distribution=rel_dist,
            tech_group_distribution=tech_dist,
            trade_flow_summary=trade_flow,
            total_countries=len(countries),
            total_provinces=len(province_infos),
            total_land_provinces=len(land_provs),
            total_sea_provinces=len(sea_provs),
            power_ranking=power_rank,
        )

    # ── INVERTED POWER CURVE HELPERS ──────────────────────────

    def _compute_inverted_development(self, province, map_height: int = 2048) -> int:
        """
        Development score inverted: Africa/Asia highest, Europe lowest.
        Thresholds scale with actual map height.
        """
        y = province.center_y
        h = map_height
        is_island = province.is_island
        is_mountain = province.terrain_type == "mountain"

        # Base development by latitude band (proportional to map height)
        if h * 0.50 <= y < h * 0.75:  # Africa/Asia superpower zone
            base = random.randint(15, 35)
        elif h * 0.375 <= y < h * 0.50:  # Middle East civilized
            base = random.randint(10, 25)
        elif h * 0.25 <= y < h * 0.375:  # Mediterranean developing
            base = random.randint(5, 15)
        elif y >= h * 0.75:  # Southern developing
            base = random.randint(8, 20)
        else:  # Europe primitive backwater
            base = random.randint(1, 6)

        # Island bonus (wealthy trade hubs)
        if is_island:
            base = int(base * 1.5)

        # Mountain penalty
        if is_mountain:
            base = max(1, int(base * 0.5))

        return min(base, 40)

    def _assign_inverted_religion(self, province, map_height: int = 2048) -> str:
        """
        Assigns religion based on inverted power dynamics.
        Hindu is world's major religion, pagan faiths strong,
        Christian/Islamic religions weak and corrupted.
        Thresholds scale with actual map height.
        """
        y = province.center_y
        h = map_height
        is_island = province.is_island
        dev = self._compute_inverted_development(province, map_height)

        import random

        # High development provinces = Hindu centers
        if dev >= 20:
            return "hinduism"
        elif is_island:
            return "hinduism"

        # Africa/Asia belt: Hindu majority with strong pagan minorities
        if h * 0.25 <= y < h * 0.75:
            roll = random.random()
            if roll < 0.50:
                return "hinduism"
            elif roll < 0.70:
                return "fetishist"  # Strong pagan faith
            elif roll < 0.85:
                return "totemism"   # Strong pagan faith
            elif roll < 0.92:
                return "norse_pagan"
            else:
                return "animism"

        # Southern territories: pagan majority
        elif y >= h * 0.75:
            roll = random.random()
            if roll < 0.30:
                return "totemism"
            elif roll < 0.55:
                return "fetishist"
            elif roll < 0.75:
                return "hinduism"
            else:
                return "animism"

        # Europe: weak, corrupted Christian/Islamic remnants
        else:
            roll = random.random()
            if roll < 0.30:
                return "catholic"        # Weak & corrupted
            elif roll < 0.50:
                return "protestant"      # Weak & corrupted
            elif roll < 0.65:
                return "orthodox"        # Weak & corrupted
            elif roll < 0.80:
                return "sunni"           # Weak & corrupted
            elif roll < 0.90:
                return "shia"            # Weak & corrupted
            else:
                return "noreligion"      # Spiritual void

    def _assign_inverted_tech(self, province) -> str:
        """
        Assigns technology group based on inverted power dynamics.
        Africa/Asia = advanced tech groups, Europe = primitive.
        Thresholds are PROPORTIONAL to map height (not hardcoded).
        """
        y = province.center_y
        h = self.map_height  # Proportional thresholds

        if h * 0.5375 <= y < h * 0.75:    # Sub-Saharan Africa / South Asia
            return "chinese"       # Most advanced
        elif h * 0.4375 <= y < h * 0.5375: # North Africa / Middle East
            return "indian"        # Highly civilized
        elif h * 0.375 <= y < h * 0.4375:  # Mediterranean
            return "muslim"        # Civilized
        elif h * 0.25 <= y < h * 0.375:    # Southern Europe
            return "east_african"  # Developing
        elif y >= h * 0.75:                 # Southern territories
            return "north_american"  # Developing
        else:                               # Northern Europe
            return "western"      # Primitive backwater


# ═══════════════════════════════════════════════════════════════
#  PROVINCE INSPECTOR
# ═══════════════════════════════════════════════════════════════

class ProvinceInspector:
    """Detailed per-province analytics for the inspector panel."""

    @staticmethod
    def inspect(province, heightmap: np.ndarray = None) -> Dict[str, Any]:
        """Generate detailed inspection data for a single province."""
        result = {
            "id": province.id,
            "center": (province.center_x, province.center_y),
            "pixel_count": province.pixel_count,
            "is_sea": province.is_sea,
            "is_wasteland": province.is_wasteland,
            "is_island": province.is_island,
            "avg_elevation": round(province.avg_elevation, 1),
            "max_elevation": round(province.max_elevation, 1),
            "terrain_type": province.terrain_type,
            "continent": province.continent_name,
            "latitude_band": province.latitude_band,
            "river_count": province.river_count,
        }

        if heightmap is not None and not province.is_sea:
            # Get elevation profile of province pixels
            # This would require province bitmap matching - simplified here
            result["elevation_class"] = (
                "mountain" if province.avg_elevation > 180 else
                "highland" if province.avg_elevation > 160 else
                "hills" if province.avg_elevation > 140 else
                "plains" if province.avg_elevation > 120 else
                "lowland"
            )

        return result


import random
