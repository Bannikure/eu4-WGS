"""
Tunnel and Cave Terrain Generation Module
==========================================
Inspired by the Anbennar mod's Serpentspine/Dwarovar tunnel system,
this module generates underground terrain biomes for EU4.

Anbennar's tunnel system features:
- Underground hold/cave terrain categories in terrain.txt
- Very high movement cost (tunnels are hard to traverse)
- Significant defensive bonuses (defenders have advantage)
- Reduced combat width (limited space underground)
- Development penalties (harder to develop underground)
- Special adjacency connections (tunnels link non-adjacent provinces)
- Unique province modifiers for hold/cave provinces

Our tunnel system extends this concept with:
- Multiple tunnel terrain types (deep_cave, crystal_cavern, volcanic_vent,
  underground_river, dwarven_hold, lost_hall, serpent_tunnel)
- Terrain generation algorithm that carves tunnel networks through mountains
- Tunnel adjacency connections between provinces
- Province modifiers for underground development
- GUI options for tunnel generation parameters
- Extended Timeline compatible date-scoped tunnel history

Terrain Type Design (based on Anbennar pattern):
    deep_cave:      movement=2.5, defence=3, width=-0.60, dev_cost=0.60
    crystal_cavern: movement=2.0, defence=2, width=-0.50, dev_cost=0.45
    volcanic_vent:  movement=2.0, defence=2, width=-0.40, dev_cost=0.50
    underground_river: movement=1.8, defence=1, width=-0.30, dev_cost=0.35
    dwarven_hold:   movement=1.5, defence=4, width=-0.50, dev_cost=-0.10
    lost_hall:      movement=2.2, defence=3, width=-0.55, dev_cost=0.40
    serpent_tunnel: movement=3.0, defence=5, width=-0.70, dev_cost=0.80
"""

import os
import csv
import numpy as np
import random
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict


# ═══════════════════════════════════════════════════════════════════════
#  TUNNEL TERRAIN DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class TunnelTerrainType:
    """Definition of a single tunnel/cave terrain type."""
    name: str
    color: Tuple[int, int, int]         # RGB color for terrain.bmp
    movement_cost: float                 # Movement cost multiplier
    defence: int                        # Defensive bonus (dice roll modifier)
    combat_width: float                 # Combat width modifier (negative = narrower)
    local_development_cost: float       # Development cost modifier
    supply_limit: int                   # Supply limit modifier
    local_defensiveness: float          # Province defensiveness modifier
    sound_type: str                     # Sound type (forest/mountain/etc)
    is_water: bool = False              # Whether this is water terrain
    nation_designer_cost: float = 0.75  # Nation designer cost multiplier
    terrain_override: List[str] = field(default_factory=list)
    description: str = ""               # Description for localisation


# All tunnel terrain types (inspired by Anbennar but original designs)
TUNNEL_TERRAIN_TYPES = {
    "deep_cave": TunnelTerrainType(
        name="deep_cave",
        color=(45, 35, 55),
        movement_cost=2.5,
        defence=3,
        combat_width=-0.60,
        local_development_cost=0.60,
        supply_limit=2,
        local_defensiveness=0.30,
        sound_type="mountain",
        description="A vast underground cavern system, pitch dark and treacherous. "
                    "Armies struggle to navigate the winding passages while defenders "
                    "hold every advantage at chokepoints and stalagmite barriers."
    ),
    "crystal_cavern": TunnelTerrainType(
        name="crystal_cavern",
        color=(80, 60, 120),
        movement_cost=2.0,
        defence=2,
        combat_width=-0.50,
        local_development_cost=0.45,
        supply_limit=3,
        local_defensiveness=0.20,
        sound_type="mountain",
        description="A glittering underground chamber filled with massive crystal "
                    "formations. The crystals refract light into dazzling patterns, "
                    "but their jagged edges make passage dangerous and combat confined."
    ),
    "volcanic_vent": TunnelTerrainType(
        name="volcanic_vent",
        color=(120, 40, 20),
        movement_cost=2.0,
        defence=2,
        combat_width=-0.40,
        local_development_cost=0.50,
        supply_limit=2,
        local_defensiveness=0.15,
        sound_type="mountain",
        description="An underground passage near volcanic activity. Superheated gases "
                    "and occasional lava flows make this terrain treacherous, but the "
                    "mineral wealth draws the bold and the desperate."
    ),
    "underground_river": TunnelTerrainType(
        name="underground_river",
        color=(30, 70, 110),
        movement_cost=1.8,
        defence=1,
        combat_width=-0.30,
        local_development_cost=0.35,
        supply_limit=4,
        local_defensiveness=0.10,
        sound_type="forest",
        description="A subterranean waterway carving through rock over millennia. "
                    "The river provides fresh water and transport, making these caves "
                    "more habitable and strategically valuable than dry tunnels."
    ),
    "dwarven_hold": TunnelTerrainType(
        name="dwarven_hold",
        color=(160, 130, 60),
        movement_cost=1.5,
        defence=4,
        combat_width=-0.50,
        local_development_cost=-0.10,  # Easier to develop - engineered halls
        supply_limit=6,
        local_defensiveness=0.35,
        sound_type="mountain",
        description="An ancient underground fortress carved from living rock. These "
                    "engineered halls feature wide galleries, forges that never cool, "
                    "and defenses that make them nearly impregnable. The pinnacle of "
                    "subterranean civilization."
    ),
    "lost_hall": TunnelTerrainType(
        name="lost_hall",
        color=(70, 50, 40),
        movement_cost=2.2,
        defence=3,
        combat_width=-0.55,
        local_development_cost=0.40,
        supply_limit=2,
        local_defensiveness=0.25,
        sound_type="mountain",
        description="An abandoned underground complex of unknown origin. Crumbling "
                    "architecture and unstable floors make these halls dangerous, but "
                    "artifacts of great power may lie within their depths."
    ),
    "serpent_tunnel": TunnelTerrainType(
        name="serpent_tunnel",
        color=(20, 80, 60),
        movement_cost=3.0,
        defence=5,
        combat_width=-0.70,
        local_development_cost=0.80,
        supply_limit=1,
        local_defensiveness=0.40,
        sound_type="mountain",
        description="The deepest and most treacherous of underground passages. Named "
                    "for the serpentine path they carve through the earth, these tunnels "
                    "are nearly impossible to assault and equally difficult to navigate."
    ),
}

# Special color for tunnel province indicator on terrain.bmp
# These are the 8-bit index colors that map to terrain types
TUNNEL_TERRAIN_COLOR_MAP = {
    "deep_cave": (45, 35, 55),
    "crystal_cavern": (80, 60, 120),
    "volcanic_vent": (120, 40, 20),
    "underground_river": (30, 70, 110),
    "dwarven_hold": (160, 130, 60),
    "lost_hall": (70, 50, 40),
    "serpent_tunnel": (20, 80, 60),
}


# ═══════════════════════════════════════════════════════════════════════
#  TUNNEL NETWORK DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class TunnelNode:
    """A single tunnel node/province in the tunnel network."""
    province_id: int
    terrain_type: str               # Key into TUNNEL_TERRAIN_TYPES
    x: int                          # Map X coordinate
    y: int                          # Map Y coordinate
    depth: int                      # Depth level (0=surface, 1=shallow, 2=deep, 3=abyss)
    connections: List[int] = field(default_factory=list)  # Connected province IDs
    is_hold: bool = False           # Is this a dwarven hold / major settlement
    has_river: bool = False         # Does this node have an underground river
    has_volcano: bool = False       # Is this near volcanic activity
    has_crystals: bool = False      # Does this have crystal formations


@dataclass
class TunnelNetwork:
    """Complete tunnel network for the map."""
    nodes: Dict[int, TunnelNode] = field(default_factory=dict)
    adjacencies: List[Tuple[int, int, str]] = field(default_factory=list)
    # (from_province, to_province, terrain_type_of_connection)
    mountain_ranges: List[Dict] = field(default_factory=list)
    # List of mountain range info dicts


# ═══════════════════════════════════════════════════════════════════════
#  TUNNEL TERRAIN GENERATOR
# ═══════════════════════════════════════════════════════════════════════

class TunnelTerrainGenerator:
    """
    Generates tunnel/cave terrain networks beneath mountain ranges.
    
    Algorithm:
    1. Identify mountain ranges from heightmap (elevation > threshold)
    2. Find provinces that overlap with mountain ranges
    3. Carve tunnel networks connecting these provinces
    4. Assign terrain types based on depth, features, and connectivity
    5. Generate adjacency connections for tunnel traversal
    """

    # Elevation thresholds for tunnel placement
    MOUNTAIN_THRESHOLD = 170      # Height above which mountains exist
    HIGH_MOUNTAIN_THRESHOLD = 200 # Height for deep tunnels
    PEAK_THRESHOLD = 230         # Height for serpent tunnels

    def __init__(self, seed: int = 42, tunnel_density: float = 0.3,
                 hold_frequency: float = 0.15):
        """
        Initialize tunnel terrain generator.
        
        Args:
            seed: Random seed for reproducibility
            tunnel_density: 0.0-1.0, how dense tunnel networks are
            hold_frequency: 0.0-1.0, how often dwarven holds appear
        """
        self.seed = seed
        self.tunnel_density = max(0.1, min(1.0, tunnel_density))
        self.hold_frequency = max(0.05, min(0.5, hold_frequency))
        self.rng = random.Random(seed)

    def identify_mountain_provinces(self, heightmap: np.ndarray,
                                     province_map: np.ndarray,
                                     land_mask: np.ndarray,
                                     province_infos: list) -> List[Dict]:
        """
        Identify provinces that are in mountainous terrain suitable for tunnels.
        
        Returns a list of dicts with province info and mountain metrics.
        """
        h, w = heightmap.shape[:2]
        mountain_provinces = []

        for p in province_infos:
            if hasattr(p, 'is_sea') and (p.is_sea or p.is_wasteland):
                continue

            # Get province's pixel region
            px, py = p.center_x, p.center_y
            if px >= w or py >= h:
                continue

            # Sample elevation at province center and surrounding area
            radius = 15
            x_min = max(0, px - radius)
            x_max = min(w, px + radius)
            y_min = max(0, py - radius)
            y_max = min(h, py + radius)

            region_heights = heightmap[y_min:y_max, x_min:x_max]
            land_region = land_mask[y_min:y_max, x_min:x_max]

            # Only consider land pixels
            if land_region.any():
                land_heights = region_heights[land_region]
                if len(land_heights) == 0:
                    continue

                avg_height = np.mean(land_heights)
                max_height = np.max(land_heights)
                mountain_fraction = np.sum(land_heights > self.MOUNTAIN_THRESHOLD) / len(land_heights)

                if avg_height > self.MOUNTAIN_THRESHOLD * 0.8 and mountain_fraction > 0.3:
                    mountain_provinces.append({
                        'province_id': p.id,
                        'center_x': px,
                        'center_y': py,
                        'avg_height': float(avg_height),
                        'max_height': float(max_height),
                        'mountain_fraction': float(mountain_fraction),
                        'province': p,
                    })

        return mountain_provinces

    def generate_tunnel_network(self, mountain_provinces: List[Dict],
                                 all_province_infos: list) -> TunnelNetwork:
        """
        Generate a complete tunnel network connecting mountain provinces.
        
        The algorithm:
        1. Group mountain provinces into clusters (mountain ranges)
        2. Within each cluster, create tunnel connections
        3. Between nearby clusters, create serpent tunnel connections
        4. Assign terrain types based on depth and features
        """
        network = TunnelNetwork()

        if not mountain_provinces:
            return network

        # Step 1: Cluster mountain provinces into ranges
        ranges = self._cluster_mountain_provinces(mountain_provinces)
        network.mountain_ranges = ranges

        # Step 2: Generate tunnel nodes within each range
        for range_idx, mountain_range in enumerate(ranges):
            for mp in mountain_range:
                node = self._create_tunnel_node(mp, range_idx)
                if node:
                    network.nodes[node.province_id] = node

        # Step 3: Create tunnel connections within ranges
        for range_idx, mountain_range in enumerate(ranges):
            self._connect_range_nodes(mountain_range, network)

        # Step 4: Create inter-range connections (serpent tunnels)
        if len(ranges) > 1:
            self._connect_ranges(ranges, network)

        return network

    def _cluster_mountain_provinces(self, mountain_provinces: List[Dict],
                                      max_cluster_distance: float = 200) -> List[List[Dict]]:
        """
        Cluster mountain provinces into groups representing mountain ranges.
        Uses a simple distance-based clustering approach.
        """
        if not mountain_provinces:
            return []

        clusters = []
        assigned = set()

        for mp in mountain_provinces:
            if mp['province_id'] in assigned:
                continue

            # Start a new cluster
            cluster = [mp]
            assigned.add(mp['province_id'])

            # Find all unassigned provinces within max_cluster_distance
            changed = True
            while changed:
                changed = False
                for other in mountain_provinces:
                    if other['province_id'] in assigned:
                        continue

                    # Check distance to any member of the cluster
                    for member in cluster:
                        dist = np.hypot(
                            other['center_x'] - member['center_x'],
                            other['center_y'] - member['center_y']
                        )
                        if dist < max_cluster_distance:
                            cluster.append(other)
                            assigned.add(other['province_id'])
                            changed = True
                            break

            # Only keep clusters with enough provinces for interesting tunnels
            if len(cluster) >= 2 or self.rng.random() < self.tunnel_density:
                clusters.append(cluster)

        return clusters

    def _create_tunnel_node(self, mountain_province: Dict,
                             range_idx: int) -> Optional[TunnelNode]:
        """Create a tunnel node for a mountain province."""
        mp = mountain_province
        avg_height = mp['avg_height']
        max_height = mp['max_height']

        # Determine depth based on elevation
        if max_height > self.PEAK_THRESHOLD:
            depth = 3  # Abyss - serpent tunnels
        elif max_height > self.HIGH_MOUNTAIN_THRESHOLD:
            depth = 2  # Deep
        elif avg_height > self.MOUNTAIN_THRESHOLD:
            depth = 1  # Shallow
        else:
            depth = 0  # Surface mountain (no tunnel)
            return None

        # Determine terrain type based on features and depth
        terrain_type = self._assign_tunnel_terrain(mp, depth)

        # Determine if this is a dwarven hold
        is_hold = self.rng.random() < self.hold_frequency and depth >= 2

        # Determine features
        has_river = self.rng.random() < 0.2 and depth >= 1
        has_volcano = self.rng.random() < 0.1 and depth >= 2
        has_crystals = self.rng.random() < 0.15 and depth >= 1

        # Override terrain type for holds and special features
        if is_hold:
            terrain_type = "dwarven_hold"
        elif has_river and depth <= 2:
            terrain_type = "underground_river"
        elif has_crystals and depth <= 2:
            terrain_type = "crystal_cavern"
        elif has_volcano and depth >= 2:
            terrain_type = "volcanic_vent"

        return TunnelNode(
            province_id=mp['province_id'],
            terrain_type=terrain_type,
            x=mp['center_x'],
            y=mp['center_y'],
            depth=depth,
            is_hold=is_hold,
            has_river=has_river,
            has_volcano=has_volcano,
            has_crystals=has_crystals,
        )

    def _assign_tunnel_terrain(self, mountain_province: Dict,
                                 depth: int) -> str:
        """Assign a tunnel terrain type based on depth and features."""
        if depth == 3:
            return self.rng.choice(["serpent_tunnel", "deep_cave", "lost_hall"])
        elif depth == 2:
            return self.rng.choice(["deep_cave", "lost_hall", "crystal_cavern"])
        elif depth == 1:
            return self.rng.choice(["crystal_cavern", "underground_river", "lost_hall"])
        else:
            return "deep_cave"

    def _connect_range_nodes(self, mountain_range: List[Dict],
                              network: TunnelNetwork):
        """
        Create tunnel connections within a single mountain range.
        Connects provinces in a chain/path pattern.
        """
        # Sort by position to create a natural path
        sorted_provs = sorted(mountain_range, key=lambda p: (p['center_y'], p['center_x']))

        # Connect adjacent provinces in the sorted order
        for i in range(len(sorted_provs) - 1):
            prov_a = sorted_provs[i]
            prov_b = sorted_provs[i + 1]

            id_a = prov_a['province_id']
            id_b = prov_b['province_id']

            if id_a in network.nodes and id_b in network.nodes:
                # Add bidirectional connections
                network.nodes[id_a].connections.append(id_b)
                network.nodes[id_b].connections.append(id_a)

                # Determine connection type
                node_a = network.nodes[id_a]
                node_b = network.nodes[id_b]

                # Use the deeper terrain type for the connection
                if node_a.depth > node_b.depth:
                    conn_type = node_a.terrain_type
                else:
                    conn_type = node_b.terrain_type

                network.adjacencies.append((id_a, id_b, conn_type))

        # Add some cross-connections for more interesting networks
        for i in range(len(sorted_provs)):
            if self.rng.random() < self.tunnel_density:
                # Connect to a non-adjacent province in the range
                j = self.rng.randint(0, len(sorted_provs) - 1)
                if abs(i - j) > 1:
                    id_a = sorted_provs[i]['province_id']
                    id_b = sorted_provs[j]['province_id']
                    if id_a in network.nodes and id_b in network.nodes:
                        if id_b not in network.nodes[id_a].connections:
                            network.nodes[id_a].connections.append(id_b)
                            network.nodes[id_b].connections.append(id_a)
                            network.adjacencies.append((id_a, id_b, "lost_hall"))

    def _connect_ranges(self, ranges: List[List[Dict]],
                         network: TunnelNetwork):
        """
        Create serpent tunnel connections between mountain ranges.
        These represent deep underground highways between ranges.
        """
        # Find the closest pair of provinces between each pair of ranges
        for i in range(len(ranges)):
            for j in range(i + 1, len(ranges)):
                # Only connect if ranges are within reasonable distance
                # and probability check passes
                if self.rng.random() > self.tunnel_density * 0.5:
                    continue

                best_dist = float('inf')
                best_pair = None

                for mp_a in ranges[i]:
                    for mp_b in ranges[j]:
                        dist = np.hypot(
                            mp_a['center_x'] - mp_b['center_x'],
                            mp_a['center_y'] - mp_b['center_y']
                        )
                        if dist < best_dist:
                            best_dist = dist
                            best_pair = (mp_a, mp_b)

                if best_pair and best_dist < 500:
                    id_a = best_pair[0]['province_id']
                    id_b = best_pair[1]['province_id']
                    if id_a in network.nodes and id_b in network.nodes:
                        if id_b not in network.nodes[id_a].connections:
                            network.nodes[id_a].connections.append(id_b)
                            network.nodes[id_b].connections.append(id_a)
                            network.adjacencies.append((id_a, id_b, "serpent_tunnel"))


# ═══════════════════════════════════════════════════════════════════════
#  TUNNEL TERRAIN FILE EXPORTER
# ═══════════════════════════════════════════════════════════════════════

class TunnelTerrainExporter:
    """
    Exports tunnel terrain definitions and data to EU4 mod files.
    Generates terrain.txt entries, adjacencies, province modifiers,
    and localisation for all tunnel terrain types.
    """

    @staticmethod
    def generate_terrain_txt_entries() -> str:
        """
        Generate terrain.txt category definitions for all tunnel terrain types.
        These entries are appended to the standard terrain.txt file.
        
        Format follows EU4 terrain.txt specification:
        - color: RGB for terrain.bmp mapping
        - type: terrain category (mountains for all tunnels)
        - movement_cost: movement penalty
        - defence: dice roll modifier
        - combat_width: width modifier (negative = narrower)
        - supply_limit: supply limit modifier
        - local_development_cost: dev cost modifier
        - local_defensiveness: fort defensiveness modifier
        - sound_type: ambient sound
        - nation_designer_cost_multiplier: cost in nation designer
        """
        lines = ["", "", "# ═══════════════════════════════════════════════════════",
                 "# TUNNEL/CAVE TERRAIN TYPES (Anbennar-inspired)",
                 "# ═════════════════════════════════════════════════════", ""]

        for name, tt in TUNNEL_TERRAIN_TYPES.items():
            lines.extend([
                f"{name} = {{",
                f"\tcolor = {{ {tt.color[0]} {tt.color[1]} {tt.color[2]} }}",
                f"\ttype = mountains",
                f"\tsound_type = {tt.sound_type}",
                f"\tmovement_cost = {tt.movement_cost}",
                f"\tdefence = {tt.defence}",
                f"\tcombat_width = {tt.combat_width}",
                f"\tsupply_limit = {tt.supply_limit}",
                f"\tlocal_development_cost = {tt.local_development_cost}",
                f"\tlocal_defensiveness = {tt.local_defensiveness}",
                f"\tnation_designer_cost_multiplier = {tt.nation_designer_cost}",
            ])

            if tt.terrain_override:
                lines.append("\tterrain_override = {")
                for override in tt.terrain_override:
                    lines.append(f"\t\t{override}")
                lines.append("\t}")

            lines.extend(["}", ""])

        return "\n".join(lines)

    @staticmethod
    def generate_terrain_bmp_entries() -> str:
        """
        Generate the graphical terrain mapping section for terrain.txt.
        This maps terrain.bmp color indices to terrain categories.
        """
        lines = ["", "# Tunnel terrain graphical mappings", ""]

        # Use high index values to avoid collision with standard terrain
        base_index = 40  # Standard terrain uses 0-35ish
        for i, (name, tt) in enumerate(TUNNEL_TERRAIN_TYPES.items()):
            idx = base_index + i
            lines.append(f"tunnel_{name} = {{ type = {name} color = {{ {idx} }} }}")

        return "\n".join(lines)

    @staticmethod
    def generate_adjacencies_csv(network: TunnelNetwork) -> List[List[str]]:
        """
        Generate adjacencies.csv entries for tunnel connections.
        Tunnel adjacencies use type "land" to allow land movement
        between non-adjacent provinces.
        
        Format: From;To;Type;Through;start_x;start_y;stop_x;stop_y;adjacency_name;Comment
        """
        rows = []
        for id_a, id_b, terrain_type in network.adjacencies:
            node_a = network.nodes.get(id_a)
            node_b = network.nodes.get(id_b)
            if node_a and node_b:
                tunnel_name = f"tunnel_{terrain_type}_{id_a}_{id_b}"
                rows.append([
                    str(id_a), str(id_b), "land", "-1",
                    str(node_a.x), str(node_a.y),
                    str(node_b.x), str(node_b.y),
                    tunnel_name,
                    f"Tunnel connection ({terrain_type})"
                ])
        return rows

    @staticmethod
    def generate_province_modifiers() -> str:
        """
        Generate province modifier definitions for tunnel terrain.
        These modifiers are applied to provinces with tunnel terrain.
        """
        lines = [
            "# Tunnel Province Modifiers",
            "# Applied to provinces with underground terrain",
            "",
        ]

        # Underground development modifier
        lines.extend([
            "underground_development = {",
            "\ticon = 7",
            "\tlocal_development_cost = 0.25",
            "\tlocal_hostile_attrition = 1",
            "\tdesc = UNDERGROUND_DEVELOPMENT_DESC",
            "}",
            "",
        ])

        # Deep tunnel modifier
        lines.extend([
            "deep_tunnel_modifier = {",
            "\ticon = 7",
            "\tlocal_defensiveness = 0.15",
            "\tlocal_development_cost = 0.35",
            "\tlocal_hostile_attrition = 2",
            "\tlocal_manpower = -0.10",
            "\tdesc = DEEP_TUNNEL_MODIFIER_DESC",
            "}",
            "",
        ])

        # Dwarven hold modifier (positive!)
        lines.extend([
            "dwarven_hold_modifier = {",
            "\ticon = 5",
            "\tlocal_defensiveness = 0.25",
            "\tlocal_development_cost = -0.10",
            "\tlocal_production_efficiency = 0.10",
            "\tfort_maintenance = -0.20",
            "\tlocal_manpower = 0.10",
            "\tdesc = DWARVEN_HOLD_MODIFIER_DESC",
            "}",
            "",
        ])

        # Crystal cavern modifier
        lines.extend([
            "crystal_cavern_modifier = {",
            "\ticon = 7",
            "\tlocal_production_efficiency = 0.15",
            "\tlocal_development_cost = 0.20",
            "\ttrade_value = 0.10",
            "\tdesc = CRYSTAL_CAVERN_MODIFIER_DESC",
            "}",
            "",
        ])

        # Serpent tunnel modifier
        lines.extend([
            "serpent_tunnel_modifier = {",
            "\ticon = 7",
            "\tlocal_defensiveness = 0.30",
            "\tlocal_development_cost = 0.50",
            "\tlocal_hostile_attrition = 3",
            "\tlocal_manpower = -0.20",
            "\tdesc = SERPENT_TUNNEL_MODIFIER_DESC",
            "}",
            "",
        ])

        return "\n".join(lines)

    @staticmethod
    def generate_tunnel_triggered_modifiers() -> str:
        """
        Generate triggered modifiers that automatically apply to tunnel provinces.
        These check for tunnel terrain and apply appropriate effects.
        """
        lines = [
            "# Tunnel Terrain Triggered Modifiers",
            "# Automatically applied when a province has tunnel terrain",
            "",
        ]

        for name, tt in TUNNEL_TERRAIN_TYPES.items():
            lines.extend([
                f"{name}_terrain_modifier = {{",
                f"\tpotential = {{",
                f"\t\tprovince_id = ROOT",
                f"\t}}",
                f"\ttrigger = {{",
                f"\t\tterrain = {name}",
                f"\t}}",
            ])

            # Apply appropriate modifiers based on terrain type
            if tt.local_development_cost > 0:
                lines.append(f"\tlocal_development_cost = {tt.local_development_cost:.2f}")
            elif tt.local_development_cost < 0:
                lines.append(f"\tlocal_development_cost = {tt.local_development_cost:.2f}")

            if tt.local_defensiveness > 0:
                lines.append(f"\tlocal_defensiveness = {tt.local_defensiveness:.2f}")

            # Supply penalty for deep terrain
            if tt.movement_cost > 2.0:
                lines.append("\tlocal_hostile_attrition = 1")

            # Special bonuses for dwarven holds
            if name == "dwarven_hold":
                lines.extend([
                    "\tlocal_production_efficiency = 0.10",
                    "\tfort_maintenance = -0.20",
                    "\tlocal_manpower = 0.10",
                ])

            # Crystal caverns have trade bonus
            if name == "crystal_cavern":
                lines.append("\ttrade_value = 0.10")

            lines.extend(["}", ""])

        return "\n".join(lines)

    @staticmethod
    def generate_localisation() -> str:
        """Generate localisation strings for all tunnel terrain types."""
        lines = ["l_english:", ""]

        for name, tt in TUNNEL_TERRAIN_TYPES.items():
            # Terrain name
            display_name = name.replace("_", " ").title()
            lines.extend([
                f' {name}:0 "{display_name}"',
                f' {name}_desc:0 "{tt.description}"',
                "",
            ])

        # Province modifier localisation
        modifier_texts = {
            "UNDERGROUND_DEVELOPMENT_DESC": "The underground terrain makes development more challenging, but offers natural defenses.",
            "DEEP_TUNNEL_MODIFIER_DESC": "Deep within the earth, attrition takes its toll on invading armies while development requires extraordinary effort.",
            "DWARVEN_HOLD_MODIFIER_DESC": "An ancient dwarven hold, engineered for both defense and productivity. The forges never cool and the walls never fall.",
            "CRYSTAL_CAVERN_MODIFIER_DESC": "Crystal formations illuminate these caverns and attract traders seeking rare gems, though mining is perilous.",
            "SERPENT_TUNNEL_MODIFIER_DESC": "The deepest tunnels are nearly impassable for invading armies, but equally hostile to permanent settlement.",
        }
        for key, text in modifier_texts.items():
            lines.append(f' {key}:0 "{text}"')

        # Adjacency localisation
        lines.extend(["", " # Tunnel Adjacency Names"])
        for name in TUNNEL_TERRAIN_TYPES:
            display_name = name.replace("_", " ").title()
            lines.append(f' tunnel_{name}:0 "Underground Passage ({display_name})"')

        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def write_all_tunnel_files(mod_root: str,
                                network: TunnelNetwork) -> Dict[str, str]:
        """
        Write all tunnel-related files to the mod directory.
        Returns a dict of {file_type: path} for all exported files.
        """
        exported = {}

        # 1. Generate terrain.txt entries (to be appended to main terrain.txt)
        terrain_entries = TunnelTerrainExporter.generate_terrain_txt_entries()
        terrain_path = os.path.join(mod_root, "map", "terrain.txt")
        if os.path.exists(terrain_path):
            with open(terrain_path, "a", encoding="utf-8") as f:
                f.write(terrain_entries)
        else:
            with open(terrain_path, "w", encoding="utf-8") as f:
                f.write(terrain_entries)
        exported["tunnel_terrain_txt"] = terrain_path

        # 2. Generate adjacencies.csv entries (to be appended)
        adj_rows = TunnelTerrainExporter.generate_adjacencies_csv(network)
        adj_path = os.path.join(mod_root, "map", "adjacencies.csv")
        if os.path.exists(adj_path):
            with open(adj_path, "a", newline="", encoding="cp1252") as f:
                writer = csv.writer(f, delimiter=";")
                for row in adj_rows:
                    writer.writerow(row)
        exported["tunnel_adjacencies"] = adj_path

        # 3. Generate province modifiers
        mod_dir = os.path.join(mod_root, "common", "event_modifiers")
        os.makedirs(mod_dir, exist_ok=True)
        mod_path = os.path.join(mod_dir, "tunnel_modifiers.txt")
        with open(mod_path, "w", encoding="utf-8") as f:
            f.write(TunnelTerrainExporter.generate_province_modifiers())
        exported["tunnel_modifiers"] = mod_path

        # 4. Generate triggered modifiers
        tm_dir = os.path.join(mod_root, "common", "triggered_modifiers")
        os.makedirs(tm_dir, exist_ok=True)
        tm_path = os.path.join(tm_dir, "tunnel_terrain_modifiers.txt")
        with open(tm_path, "w", encoding="utf-8") as f:
            f.write(TunnelTerrainExporter.generate_tunnel_triggered_modifiers())
        exported["tunnel_triggered_modifiers"] = tm_path

        # 5. Generate localisation
        loc_dir = os.path.join(mod_root, "localisation")
        os.makedirs(loc_dir, exist_ok=True)
        loc_path = os.path.join(loc_dir, "tunnel_terrain_l_english.yml")
        with open(loc_path, "wb") as f:
            f.write(b'\xef\xbb\xbf')  # UTF-8 BOM
            f.write(TunnelTerrainExporter.generate_localisation().encode('utf-8'))
        exported["tunnel_localisation"] = loc_path

        # 6. Write tunnel node province history additions
        # Add tunnel-specific province modifier to each tunnel province
        for node_id, node in network.nodes.items():
            prov_dir = os.path.join(mod_root, "history", "provinces")
            prov_name = f"Province_{node_id}"
            prov_file = os.path.join(prov_dir, f"{node_id} - {prov_name}.txt")
            if os.path.exists(prov_file):
                with open(prov_file, "a", encoding="utf-8") as f:
                    f.write(f"\n# Tunnel terrain: {node.terrain_type}\n")
                    if node.is_hold:
                        f.write("add_province_modifier = {\n"
                                "\tname = dwarven_hold_modifier\n"
                                "\tduration = -1\n"
                                "}\n")
                    elif node.depth >= 3:
                        f.write("add_province_modifier = {\n"
                                "\tname = serpent_tunnel_modifier\n"
                                "\tduration = -1\n"
                                "}\n")
                    elif node.depth >= 2:
                        f.write("add_province_modifier = {\n"
                                "\tname = deep_tunnel_modifier\n"
                                "\tduration = -1\n"
                                "}\n")
                    else:
                        f.write("add_province_modifier = {\n"
                                "\tname = underground_development\n"
                                "\tduration = -1\n"
                                "}\n")
        exported["tunnel_province_histories"] = "written"

        return exported


# ═══════════════════════════════════════════════════════════════════════
#  TUNNEL TERRAIN BMP GENERATOR
# ═══════════════════════════════════════════════════════════════════════

class TunnelBmpGenerator:
    """
    Generates terrain.bmp overlay for tunnel terrain.
    Applies tunnel terrain colors to provinces identified as tunnel provinces.
    """

    @staticmethod
    def apply_tunnel_terrain_to_bmp(terrain_bmp: np.ndarray,
                                      network: TunnelNetwork,
                                      province_map: np.ndarray) -> np.ndarray:
        """
        Apply tunnel terrain colors to the terrain.bmp based on the tunnel network.
        Tunnel provinces get their assigned terrain color instead of surface terrain.
        """
        result = terrain_bmp.copy()

        for node_id, node in network.nodes.items():
            # Find all pixels belonging to this province
            mask = province_map == node_id

            # Apply tunnel terrain color
            tt = TUNNEL_TERRAIN_TYPES.get(node.terrain_type)
            if tt:
                result[mask] = tt.color

        return result


# ═══════════════════════════════════════════════════════════════════════
#  TUNNEL CLIMATE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════

# Climate type IDs for tunnel terrain (to be added to climate_generation.py)
CLIMATE_DEEP_CAVE = 100
CLIMATE_CRYSTAL_CAVERN = 101
CLIMATE_VOLCANIC_VENT = 102
CLIMATE_UNDERGROUND_RIVER = 103
CLIMATE_DWARVEN_HOLD = 104
CLIMATE_LOST_HALL = 105
CLIMATE_SERPENT_TUNNEL = 106

TUNNEL_CLIMATE_MAP = {
    CLIMATE_DEEP_CAVE: "deep_cave",
    CLIMATE_CRYSTAL_CAVERN: "crystal_cavern",
    CLIMATE_VOLCANIC_VENT: "volcanic_vent",
    CLIMATE_UNDERGROUND_RIVER: "underground_river",
    CLIMATE_DWARVEN_HOLD: "dwarven_hold",
    CLIMATE_LOST_HALL: "lost_hall",
    CLIMATE_SERPENT_TUNNEL: "serpent_tunnel",
}

# Tunnel climate to EU4 terrain mapping
TUNNEL_CLIMATE_TO_EU4_TERRAIN = {
    CLIMATE_DEEP_CAVE: "deep_cave",
    CLIMATE_CRYSTAL_CAVERN: "crystal_cavern",
    CLIMATE_VOLCANIC_VENT: "volcanic_vent",
    CLIMATE_UNDERGROUND_RIVER: "underground_river",
    CLIMATE_DWARVEN_HOLD: "dwarven_hold",
    CLIMATE_LOST_HALL: "lost_hall",
    CLIMATE_SERPENT_TUNNEL: "serpent_tunnel",
}
