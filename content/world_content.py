"""
Module 3: Afro-Asian Ascendancy World Content Generator
=========================================================
Generates all game content with inverted power dynamics:
- Africa and Asia are the most advanced, wealthiest, and powerful continents
- Europe is the weakest, poorest, and least advanced continent
- Hindu is the world's major religion, pagan faiths are strong
- Christian and Islamic religions are weak and corrupted
- Second HRE (Celestial Directorate) empire mechanics
- Custom countries, provinces, flags, ideas, wars, cultures, histories
"""

import os
import csv
import random
import numpy as np
from PIL import Image, ImageOps, ImageDraw
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional


# ═══════════════════════════════════════════════════════════════
#  NAMING CONSTANTS
# ═══════════════════════════════════════════════════════════════

ADJECTIVES = [
    "Grand", "Holy", "Iron", "United", "New", "High", "Eternal",
    "Solar", "Greater", "Ashen", "Celestial", "Divine", "Golden",
    "Sovereign", "Sacred", "Venerable", "Imperial", "Radiant",
]

ACRONYMS = [
    ("U.S.D.", "United Satellite Dominion"),
    ("S.P.Q.R.", "Senate and People of Rome"),
    ("U.P.R.", "United Provinces Republic"),
    ("F.S.T.", "Federated Sovereign Territories"),
    ("C.D.E.", "Celestial Directorate Empire"),
    ("I.H.D.", "Imperial Hindu Dominion"),
    ("V.S.A.", "Vedic Sovereign Ascendancy"),
    ("D.R.K.", "Divine Rajya Kingdom"),
]

ROOT_NAMES_AFRICAN = [
    "Zanj", "Aksum", "Mali", "Songhai", "Kongo", "Zulu",
    "Ashanti", "Kush", "Nubia", "Kanem", "Great Zimbabwe", "Carthage",
    "Aksumite", "Wagadu", "Dahomey", "Oyo", "Benin", "Nok",
    "Kilwa", "Mogadishu", "Malindi", "Sofala", "Mombasa",
]

ROOT_NAMES_ASIAN = [
    "Mosik", "Valoria", "Elysia", "Merovia", "Bharat",
    "Chola", "Vijayanagara", "Maurya", "Gupta", "Maratha",
    "Srivijaya", "Majapahit", "Ayutthaya", "Khmer",
    "Gondor", "Aethelgard", "Navarra", "Illyria",
    "Rohan", "Carthon", "Skye", "Harkonnen",
]

ROOT_NAMES_EUROPEAN = [
    "Mudhaven", "Rustwall", "Graymoor", "Brambleford",
    "Rottingdean", "Ashhill", "Fenwick", "Thornfield",
    "Grimworth", "Fallowmere", "Dunwich", "Scabland",
    "Witherford", "Blightshire", "Crumbleton", "Drabfield",
]

GOVERNMENTS = {
    "monarchy":   ["Empire", "Kingdom", "Queendom", "Principality",
                   "Sovereignty", "Dynasty", "Rajya", "Sultanate"],
    "republic":   ["Republic", "Commonwealth", "Federation", "League",
                   "Dominion", "Directorate", "Sangha", "Mahasabha"],
    "theocracy":  ["Theocracy", "Holy See", "Order", "Conclave",
                   "Mandate", "Divine Rule", "Dharma"],
}

LEADER_NAMES_AFRICAN = [
    "Shaka", "Mansa Musa", "Amina", "Ezana", "Askia",
    "Sundiata", "Nzinga", "Cetshwayo", "Osei", "Agoli",
    "Ranavalona", "Makeda", "Taharqa", "Hatshepsut",
]

LEADER_NAMES_ASIAN = [
    "Ashoka", "Chandra", "Shivaji", "Rajendra", "Krishnadevaraya",
    "Hayam Wuruk", "Gajah Mada", "Bayinnaung", "Suryavarman",
    "Prithviraj", "Akbar", "Chandragupta", "Samudragupta",
    "Vikramaditya", "Rani Lakshmibai",
]

LEADER_NAMES_EUROPEAN = [
    "Alaric", "Erik", "Sven", "Bjorn", "Ragnar",
    "Cnut", "Harald", "Olaf", "Sigurd", "Ivar",
    "Gorm", "Halfdan", "Knut", "Thorkell",
]

LEADER_MONIKERS = [
    "the Great", "the Conqueror", "the Builder", "the Mad",
    "the Just", "the Cruel", "the Wise", "the Bold",
    "the Radiant", "the Invincible", "the Divine", "",
]


# ═══════════════════════════════════════════════════════════════
#  FLAG GENERATOR
# ═══════════════════════════════════════════════════════════════

FLAG_SIZE = 128  # EU4 standard flag size (128x128 pixels)

FLAG_PALETTE_ADVANCED = [
    (255, 153, 0),    # Saffron (Hindu)
    (0, 128, 0),      # Green
    (255, 215, 0),    # Gold
    (139, 0, 0),      # Dark Red
    (0, 0, 139),      # Deep Blue
    (255, 255, 255),  # White
    (75, 0, 130),     # Indigo
    (218, 165, 32),   # Goldenrod
    (178, 34, 34),    # Firebrick
    (0, 100, 0),      # Dark Green
    (184, 134, 11),   # Dark Goldenrod
    (128, 0, 128),    # Purple
]

FLAG_PALETTE_PRIMITIVE = [
    (80, 80, 80),     # Gray
    (60, 60, 60),     # Dark Gray
    (100, 100, 90),   # Mud
    (70, 70, 65),     # Ash
    (50, 50, 45),     # Soot
    (90, 85, 75),     # Dust
    (110, 95, 80),    # Clay
    (65, 70, 60),     # Moss
]

# Emblem categories for continent-aware selection
EMBLEM_CATEGORIES = {
    "african": ["lion", "elephant", "shield", "spear", "sun", "eagle",
                "crown", "star", "crests", "coat", "arms", "africa",
                "dragon", "horse", "griffin", "mountain"],
    "asian": ["dragon", "tiger", "lotus", "chakra", "wheel", "star",
              "sun", "moon", "eagle", "crest", "india", "arms",
              "griffin", "horse", "elephant", "phoenix"],
    "european": ["cross", "castle", "tower", "wolf", "raven",
                 "serpent", "skull", "thorn", "iron", "rust",
                 "hammer", "axe", "crown"],
}

PATTERN_CATEGORIES = {
    "african": ["tricolor", "horizontal", "diagonal", "radiant", "sun",
                "green", "gold", "red", "saffron", "venice"],
    "asian": ["tricolor", "horizontal", "cross", "radiant", "saffron",
              "gold", "blue", "stripe", "venice", "abstract"],
    "european": ["cross", "saltire", "chevron", "horizontal", "simple",
                 "grey", "dark", "black", "red", "muted"],
}


class FlagGenerator:
    """
    Procedurally builds unique 128x128 .tga flags for custom EU4 tags.
    Uses pattern PNGs from assets/patterns/ as backgrounds and
    emblem PNGs from assets/emblems/ as overlays, properly resized
    to EU4 flag format (128x128 TGA, 24-bit RGB).

    Flag composition follows EU4's flag system:
    1. Pattern background (resized to 128x128) provides the base design
    2. Color tinting adjusts the pattern to match the country's palette
    3. Emblem overlay (resized and centered) provides the central symbol
    4. Final output saved as uncompressed 24-bit TGA
    """

    # Fallback procedural patterns if no pattern assets available
    PROCEDURAL_PATTERNS = [
        "horizontal_tricolor", "vertical_tricolor", "diagonal",
        "cross", "canton", "saltire", "chevron", "radiant",
        "bicolor_horizontal", "bicolor_vertical", "quarterly",
        "bend", "pale", "fess", "pile",
    ]

    # Cache for valid asset files (avoid re-scanning directory each time)
    _emblem_cache: Dict[str, List[str]] = {}
    _pattern_cache: Dict[str, List[str]] = {}

    @classmethod
    def _scan_assets(cls, asset_dir: str, asset_type: str) -> List[str]:
        """Scan and cache valid image files from an asset directory."""
        cache_key = f"{asset_dir}/{asset_type}"
        if cache_key in cls._emblem_cache:
            return cls._emblem_cache[cache_key]

        valid_files = []
        target_dir = os.path.join(asset_dir, asset_type)
        if not os.path.isdir(target_dir):
            cls._emblem_cache[cache_key] = valid_files
            return valid_files

        for fname in sorted(os.listdir(target_dir)):
            fpath = os.path.join(target_dir, fname)
            if not fname.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                continue
            try:
                with Image.open(fpath) as test_img:
                    test_img.verify()
                valid_files.append(fpath)
            except Exception:
                continue

        cls._emblem_cache[cache_key] = valid_files
        return valid_files

    @classmethod
    def _select_emblem_by_continent(cls, emblem_files: List[str],
                                     continent: str) -> Optional[str]:
        """Select an emblem file matching the continent's aesthetic."""
        if not emblem_files:
            return None

        continent_lower = continent.lower()
        keywords = EMBLEM_CATEGORIES.get(continent_lower, [])
        if not keywords:
            keywords = EMBLEM_CATEGORIES.get("african", [])

        # Try to find a matching emblem by filename keyword
        matches = []
        for fpath in emblem_files:
            fname_lower = os.path.basename(fpath).lower()
            for kw in keywords:
                if kw in fname_lower:
                    matches.append(fpath)
                    break

        if matches:
            return random.choice(matches)
        # Fallback: random emblem from full list
        return random.choice(emblem_files)

    @classmethod
    def _select_pattern_by_continent(cls, pattern_files: List[str],
                                      continent: str) -> Optional[str]:
        """Select a pattern file matching the continent's aesthetic."""
        if not pattern_files:
            return None

        continent_lower = continent.lower()
        keywords = PATTERN_CATEGORIES.get(continent_lower, [])
        if not keywords:
            keywords = PATTERN_CATEGORIES.get("african", [])

        # Try to find a matching pattern by filename keyword
        matches = []
        for fpath in pattern_files:
            fname_lower = os.path.basename(fpath).lower()
            for kw in keywords:
                if kw in fname_lower:
                    matches.append(fpath)
                    break

        if matches:
            return random.choice(matches)
        return random.choice(pattern_files)

    @staticmethod
    def _load_and_resize_image(fpath: str, target_size: Tuple[int, int],
                                maintain_aspect: bool = True) -> Optional[Image.Image]:
        """Load an image file and resize it to the target dimensions."""
        try:
            img = Image.open(fpath).convert("RGBA")
            if maintain_aspect:
                # Resize maintaining aspect ratio, then center on target canvas
                img.thumbnail(target_size, Image.LANCZOS)
                canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
                offset_x = (target_size[0] - img.width) // 2
                offset_y = (target_size[1] - img.height) // 2
                canvas.paste(img, (offset_x, offset_y), img)
                return canvas
            else:
                return img.resize(target_size, Image.LANCZOS)
        except Exception:
            return None

    @staticmethod
    def _tint_image(img: Image.Image, color: Tuple[int, int, int],
                     strength: float = 0.5) -> Image.Image:
        """
        Apply a color tint to an image while preserving its structure.
        Strength 0.0 = no tint, 1.0 = full tint.
        """
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        channels = img.split()
        r, g, b, a = channels[0], channels[1], channels[2], channels[3]
        cr, cg, cb = color

        # Blend original with tinted version
        tinted_r = Image.blend(r, Image.new("L", r.size, cr), strength)
        tinted_g = Image.blend(g, Image.new("L", g.size, cg), strength)
        tinted_b = Image.blend(b, Image.new("L", b.size, cb), strength)

        return Image.merge("RGBA", [tinted_r, tinted_g, tinted_b, a])

    @classmethod
    def _create_procedural_pattern(cls, size: int, pattern_name: str,
                                    colors: List[Tuple[int, int, int]]) -> Image.Image:
        """Create a procedural flag pattern as fallback when no pattern assets exist."""
        if len(colors) < 3:
            colors = colors + [colors[0]] * (3 - len(colors))

        base, secondary, accent = colors[0], colors[1], colors[2]
        flag = Image.new("RGBA", (size, size), color=base + (255,))
        draw = ImageDraw.Draw(flag)

        if pattern_name == "horizontal_tricolor":
            h = size // 3
            draw.rectangle([0, 0, size, h], fill=base + (255,))
            draw.rectangle([0, h, size, h * 2], fill=secondary + (255,))
            draw.rectangle([0, h * 2, size, size], fill=accent + (255,))
        elif pattern_name == "vertical_tricolor":
            w = size // 3
            draw.rectangle([0, 0, w, size], fill=base + (255,))
            draw.rectangle([w, 0, w * 2, size], fill=secondary + (255,))
            draw.rectangle([w * 2, 0, size, size], fill=accent + (255,))
        elif pattern_name == "bicolor_horizontal":
            h = size // 2
            draw.rectangle([0, 0, size, h], fill=base + (255,))
            draw.rectangle([0, h, size, size], fill=secondary + (255,))
        elif pattern_name == "bicolor_vertical":
            w = size // 2
            draw.rectangle([0, 0, w, size], fill=base + (255,))
            draw.rectangle([w, 0, size, size], fill=secondary + (255,))
        elif pattern_name == "diagonal":
            for y in range(size):
                for x in range(size):
                    c = base if (x + y < size) else secondary
                    flag.putpixel((x, y), c + (255,))
        elif pattern_name == "cross":
            draw.rectangle([0, 0, size, size], fill=base + (255,))
            cw = size // 6
            draw.rectangle([size//2 - cw, 0, size//2 + cw, size], fill=secondary + (255,))
            draw.rectangle([0, size//2 - cw, size, size//2 + cw], fill=secondary + (255,))
        elif pattern_name == "canton":
            draw.rectangle([0, 0, size, size], fill=base + (255,))
            draw.rectangle([0, 0, size//2, size//2], fill=secondary + (255,))
        elif pattern_name == "saltire":
            draw.rectangle([0, 0, size, size], fill=base + (255,))
            for i in range(0, size, 4):
                draw.line([(i, 0), (size, size - i)], fill=secondary + (255,), width=3)
                draw.line([(size - i, 0), (0, size - i)], fill=secondary + (255,), width=3)
        elif pattern_name == "chevron":
            draw.rectangle([0, 0, size, size], fill=base + (255,))
            points = [(0, 0), (size // 2, size // 2), (0, size)]
            draw.polygon(points, fill=secondary + (255,))
        elif pattern_name == "radiant":
            draw.rectangle([0, 0, size, size], fill=base + (255,))
            import math
            cx, cy = size // 2, size // 2
            for angle in range(0, 360, 20):
                rad = math.radians(angle)
                ex = int(cx + (size * 0.45) * math.cos(rad))
                ey = int(cy + (size * 0.45) * math.sin(rad))
                draw.line([(cx, cy), (ex, ey)], fill=secondary + (255,), width=2)
            draw.ellipse([size//4, size//4, 3*size//4, 3*size//4], fill=accent + (255,))
        elif pattern_name == "quarterly":
            q = size // 2
            draw.rectangle([0, 0, q, q], fill=base + (255,))
            draw.rectangle([q, 0, size, q], fill=secondary + (255,))
            draw.rectangle([0, q, q, size], fill=secondary + (255,))
            draw.rectangle([q, q, size, size], fill=base + (255,))
        elif pattern_name == "bend":
            for y in range(size):
                for x in range(size):
                    if abs(x - y) < size // 5:
                        flag.putpixel((x, y), secondary + (255,))
                    else:
                        flag.putpixel((x, y), base + (255,))
        elif pattern_name == "pale":
            p = size // 3
            draw.rectangle([0, 0, size, size], fill=base + (255,))
            draw.rectangle([p, 0, p * 2, size], fill=secondary + (255,))
        elif pattern_name == "fess":
            h = size // 3
            draw.rectangle([0, 0, size, size], fill=base + (255,))
            draw.rectangle([0, h, size, h * 2], fill=secondary + (255,))
        elif pattern_name == "pile":
            draw.rectangle([0, 0, size, size], fill=base + (255,))
            points = [(size//2, 0), (size, size), (0, size)]
            draw.polygon(points, fill=secondary + (255,))
        else:
            # Default: horizontal tricolor
            h = size // 3
            draw.rectangle([0, 0, size, h], fill=base + (255,))
            draw.rectangle([0, h, size, h * 2], fill=secondary + (255,))
            draw.rectangle([0, h * 2, size, size], fill=accent + (255,))

        return flag

    @staticmethod
    def _save_tga(img: Image.Image, output_path: str) -> str:
        """
        Save image as uncompressed 24-bit TGA file for EU4 compatibility.
        EU4 expects: 128x128, 24-bit RGB, uncompressed, bottom-left origin.
        """
        # Ensure RGB mode (no alpha for TGA in EU4)
        rgb_img = img.convert("RGB")
        rgb_img.save(output_path, format="TGA")
        return output_path

    @classmethod
    def generate_flag(cls, tag: str, is_advanced: bool = True,
                      output_dir: str = ".",
                      assets_path: str = "assets",
                      continent: str = "",
                      seed: Optional[int] = None) -> str:
        """
        Generate a procedural flag composed from pattern + emblem assets,
        properly resized to 128x128 EU4 format, saved as 24-bit TGA.

        Args:
            tag: Country tag (e.g. "Z01")
            is_advanced: Whether this is an advanced (Afro-Asian) country
            output_dir: Mod output directory root
            assets_path: Path to assets folder containing emblems/ and patterns/
            continent: Continent name for aesthetic matching
            seed: Optional seed for reproducible flag generation

        Returns:
            Path to the generated .tga flag file
        """
        if seed is not None:
            random.seed(seed)

        os.makedirs(f"{output_dir}/gfx/flags", exist_ok=True)

        size = FLAG_SIZE
        palette = FLAG_PALETTE_ADVANCED if is_advanced else FLAG_PALETTE_PRIMITIVE

        # Pick colors
        base_color = random.choice(palette)
        secondary_color = random.choice([c for c in palette if c != base_color])
        accent_color = random.choice([c for c in palette if c not in (base_color, secondary_color)])
        colors = [base_color, secondary_color, accent_color]

        # ── STEP 1: Create pattern background ──
        pattern_files = cls._scan_assets(assets_path, "patterns")
        pattern_img = None

        if pattern_files:
            chosen_pattern = cls._select_pattern_by_continent(pattern_files, continent)
            if chosen_pattern:
                pattern_img = cls._load_and_resize_image(
                    chosen_pattern, (size, size), maintain_aspect=False
                )
                if pattern_img:
                    # Tint the pattern to match the country's color scheme
                    pattern_img = cls._tint_image(pattern_img, base_color, strength=0.35)

        # Fallback to procedural pattern if no pattern assets
        if pattern_img is None:
            pattern_name = random.choice(cls.PROCEDURAL_PATTERNS)
            pattern_img = cls._create_procedural_pattern(size, pattern_name, colors)

        # Ensure the pattern is the correct size
        if pattern_img.size != (size, size):
            pattern_img = pattern_img.resize((size, size), Image.LANCZOS)

        # Convert to RGBA for compositing
        flag_canvas = pattern_img.convert("RGBA")

        # ── STEP 2: Overlay emblem ──
        emblem_files = cls._scan_assets(assets_path, "emblems")
        emblem_placed = False

        if emblem_files:
            chosen_emblem = cls._select_emblem_by_continent(emblem_files, continent)
            if chosen_emblem:
                # Size the emblem to ~60% of flag size for center placement
                emblem_size = int(size * 0.55)
                emblem_img = cls._load_and_resize_image(
                    chosen_emblem, (emblem_size, emblem_size), maintain_aspect=True
                )
                if emblem_img:
                    # Tint the emblem with the accent color
                    if is_advanced:
                        emblem_img = cls._tint_image(emblem_img, accent_color, strength=0.25)

                    # Center the emblem on the flag
                    offset_x = (size - emblem_img.width) // 2
                    offset_y = (size - emblem_img.height) // 2
                    flag_canvas.paste(emblem_img, (offset_x, offset_y), emblem_img)
                    emblem_placed = True

        # ── STEP 3: If no emblem placed, draw a procedural symbol ──
        if not emblem_placed:
            draw = ImageDraw.Draw(flag_canvas)
            symbol = random.choice(["circle", "star", "diamond", "crescent", "sun", "shield"])
            cx, cy = size // 2, size // 2
            r = size // 5

            if symbol == "circle":
                draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=accent_color + (230,))
            elif symbol == "diamond":
                pts = [(cx, cy-r), (cx+r, cy), (cx, cy+r), (cx-r, cy)]
                draw.polygon(pts, fill=accent_color + (230,))
            elif symbol == "crescent":
                draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=accent_color + (230,))
                draw.ellipse([cx-r//3, cy-r, cx+r+r//3, cy+r], fill=base_color + (0,))
            elif symbol == "sun":
                import math
                draw.ellipse([cx-r//2, cy-r//2, cx+r//2, cy+r//2], fill=accent_color + (255,))
                for angle in range(0, 360, 45):
                    rad = math.radians(angle)
                    x1 = int(cx + (r*0.6) * math.cos(rad))
                    y1 = int(cy + (r*0.6) * math.sin(rad))
                    x2 = int(cx + r * math.cos(rad))
                    y2 = int(cy + r * math.sin(rad))
                    draw.line([(x1, y1), (x2, y2)], fill=accent_color + (255,), width=2)
            elif symbol == "shield":
                pts = [(cx-r, cy-r), (cx+r, cy-r), (cx+r, cy),
                       (cx, cy+r), (cx-r, cy)]
                draw.polygon(pts, fill=accent_color + (200,))

        # ── STEP 4: Save as TGA ──
        output_path = f"{output_dir}/gfx/flags/{tag}.tga"
        cls._save_tga(flag_canvas, output_path)

        return output_path

    @classmethod
    def generate_flags_batch(cls, countries: Dict[str, Any],
                             output_dir: str = ".",
                             assets_path: str = "assets") -> Dict[str, str]:
        """
        Generate flags for all countries in a batch.
        Returns a dict of {tag: flag_path}.
        """
        results = {}
        for i, (tag, data) in enumerate(countries.items()):
            continent = getattr(data, 'continent', '')
            is_adv = getattr(data, 'is_advanced', True)
            path = cls.generate_flag(
                tag=tag,
                is_advanced=is_adv,
                output_dir=output_dir,
                assets_path=assets_path,
                continent=continent,
                seed=hash(tag) % (2**31)  # Deterministic per tag
            )
            results[tag] = path
        return results

    @classmethod
    def clear_cache(cls):
        """Clear the asset file cache (useful if assets change)."""
        cls._emblem_cache.clear()
        cls._pattern_cache.clear()


# ═══════════════════════════════════════════════════════════════
#  RELIGION SYSTEM
# ═══════════════════════════════════════════════════════════════

class ReligionGenerator:
    """
    Generates the inverted religion system:
    - Hinduism: dominant, powerful, center of reformation
    - Pagan faiths: strong, rich, organized
    - Christianity: weak, corrupted, fragmented
    - Islam: weak, corrupted, decaying
    """

    @staticmethod
    def generate_religion_file(output_dir: str) -> str:
        """Writes common/religions/00_religion.txt with inverted power matrix."""
        os.makedirs(f"{output_dir}/common/religions", exist_ok=True)

        religion_script = """# ═══════════════════════════════════════════════════
# INVERTED RELIGIONS DATABASE
# Hindu dominant, Pagan strong, Christian/Islam corrupted
# ═════════════════════════════════════════════════

eastern = {
    hinduism = {
        color = { 0.8 0.5 0.0 }
        icon = 8
        global_trade_goods_size_modifier = 0.20
        technology_cost = -0.15
        global_missionary_strength = 0.05
        tolerance_own = 4
        tolerance_heretic = 2
        tolerance_heathen = 1

        # CENTER OF REFORMATION: Spawns automated missionary conversion centers
        center_of_reformation = yes

        # FEMALE DEFENDER: Enables gender-inverted religious military titles
        female_defender_of_faith = yes
        defender_of_faith = yes

        # HINDU REFORM BRANCHES (like Protestant Church Aspects)
        hindu_reform_branch = {
            # Dharma Path - focuses on order and stability
            dharma_path = {
                stability_cost_modifier = -0.15
                global_unrest = -2
            }
            # Karma Path - focuses on prosperity and trade
            karma_path = {
                global_trade_power = 0.15
                production_efficiency = 0.10
            }
            # Bhakti Path - focuses on devotion and conversion
            bhakti_path = {
                global_missionary_strength = 0.03
                legitimacy = 1
            }
            # Tantra Path - focuses on military and discipline
            tantra_path = {
                discipline = 0.05
                land_morale = 0.10
            }
        }
    }

    buddhism = {
        color = { 0.9 0.7 0.0 }
        icon = 7
        tolerance_own = 3
        tolerance_heretic = 3
        tolerance_heathen = 2
        development_cost = -0.05
        idea_cost = -0.05
    }
}

pagan = {
    # ORGANIZED PAGAN FAITHS - Strong and wealthy

    fetishist = {
        color = { 0.6 0.4 0.2 }
        icon = 9
        global_manpower_modifier = 0.20
        core_creation_cost = -0.15
        tolerance_own = 3
        global_tax_modifier = 0.10
        # Organized Cult System
        cult_of_wisdom = {
            technology_cost = -0.05
            idea_cost = -0.05
        }
        cult_of_war = {
            land_morale = 0.10
            discipline = 0.03
        }
        cult_of_prosperity = {
            production_efficiency = 0.10
            trade_efficiency = 0.10
        }
    }

    totemism = {
        color = { 0.4 0.6 0.4 }
        icon = 10
        production_efficiency = 0.15
        land_morale = 0.10
        global_manpower_modifier = 0.15
        defensiveness = 0.15
    }

    norse_pagan = {
        color = { 0.3 0.3 0.6 }
        icon = 11
        discipline = 0.05
        naval_morale = 0.15
        global_sailors_modifier = 0.20
        leader_naval_manuever = 1
    }

    animism = {
        color = { 0.5 0.7 0.3 }
        icon = 12
        global_unrest = -2
        manpower_recovery_speed = 0.15
        hostile_attrition = 1.0
    }

    # CORRUPTED PAGAN REMNANTS in Europe
    druidism = {
        color = { 0.4 0.5 0.3 }
        icon = 13
        stability_cost_modifier = 0.20
        technology_cost = 0.10
        global_unrest = 2
    }
}

christian = {
    # WEAK AND CORRUPTED CHRISTIAN FAITHS

    catholic = {
        color = { 0.8 0.8 0.8 }
        icon = 1
        # CORRUPTION AND DECAY
        global_corruption = 0.05
        stability_cost_modifier = 0.50
        technology_cost = 0.20
        tax_income = -0.20
        # Fragmented papacy
        curia = yes
        papacy = yes
        # Corrupt indulgences drain wealth
        inflation_reduction = -0.10
    }

    protestant = {
        color = { 0.3 0.3 0.7 }
        icon = 2
        global_corruption = 0.04
        idea_cost = 0.25
        inflation_action_cost = 0.50
        tolerance_heretic = -2
        # Schismatic penalties
        global_unrest = 3
    }

    orthodox = {
        color = { 0.6 0.2 0.2 }
        icon = 4
        global_corruption = 0.03
        patriarch_authority = {
            effect = {
                stability_cost_modifier = 0.15
                global_unrest = 2
            }
        }
        production_efficiency = -0.10
    }

    coptic = {
        color = { 0.5 0.4 0.2 }
        icon = 5
        global_corruption = 0.04
        missionary_maintenance_cost = 0.50
        tolerance_own = -1
    }
}

muslim = {
    # WEAK AND CORRUPTED ISLAMIC FAITHS

    sunni = {
        color = { 0.0 0.6 0.0 }
        icon = 3
        # CORRUPTION AND DECAY
        global_corruption = 0.05
        all_power_cost = 0.15
        global_unrest = 3
        # Piety mechanics inverted - maximum piety gives penalties
        piety = {
            effect = {
                stability_cost_modifier = 0.20
                technology_cost = 0.15
            }
        }
    }

    shia = {
        color = { 0.1 0.4 0.1 }
        icon = 6
        global_corruption = 0.06
        discipline = -0.03
        legitimacy = -1
        # Decaying Imamate
        global_unrest = 4
    }

    ibadi = {
        color = { 0.2 0.5 0.2 }
        icon = 14
        global_corruption = 0.03
        tolerance_own = -1
        development_cost = 0.20
    }
}

dharma = {
    # SECRET DHARMA FAITHS - Hidden power
    sikhism = {
        color = { 0.9 0.8 0.0 }
        icon = 15
        discipline = 0.05
        land_morale = 0.10
        global_manpower_modifier = 0.15
        military_tech_cost_modifier = -0.05
    }
}
"""
        output_path = f"{output_dir}/common/religions/00_religion.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(religion_script)
        return output_path

    @staticmethod
    def generate_hindu_holy_center_event(output_dir: str,
                                          target_province_id: int) -> str:
        """Writes event file creating automated Hindu holy center."""
        os.makedirs(f"{output_dir}/events", exist_ok=True)

        event_script = f"""# ═══════════════════════════════════════════
# HINDU CENTER OF REFORMATION - The Vatican of the East
# ═════════════════════════════════════════════════

namespace = hindu_dharma

# Event 1: Spawns the Center of Reformation on Day One
country_event = {{
    id = hindu_dharma.1
    title = "hindu_dharma.1.t"
    desc = "hindu_dharma.1.d"
    picture = RELIGIOUS_CONVERSION_EVENT_PICTURE

    trigger = {{
        is_year = 1444
        has_switched_nation = no
    }}

    mean_time_to_happen = {{ days = 1 }}

    option = {{
        name = "hindu_dharma.1.a"
        # Targets the selected Afro-Asian province
        {target_province_id} = {{
            change_religion = hinduism
            add_reform_centre = hinduism
            add_province_modifier = {{
                name = "hindu_holy_city_seat"
                duration = -1
            }}
        }}
    }}
}}

# Event 2: Second Hindu Center spawns after 50 years
country_event = {{
    id = hindu_dharma.2
    title = "hindu_dharma.2.t"
    desc = "hindu_dharma.2.d"
    picture = RELIGIOUS_CONVERSION_EVENT_PICTURE

    trigger = {{
        is_year = 1494
        religion = hinduism
        num_of_reform_centers = 1
    }}

    mean_time_to_happen = {{ months = 60 }}

    option = {{
        name = "hindu_dharma.2.a"
        random_owned_province = {{
            limit = {{
                religion = hinduism
                NOT = {{ has_province_modifier = hindu_holy_city_seat }}
            }}
            add_reform_centre = hinduism
            add_province_modifier = {{
                name = "hindu_holy_city_seat"
                duration = -1
            }}
        }}
    }}
}}

# Event 3: Hindu Missionary Wave - converts border provinces
country_event = {{
    id = hindu_dharma.3
    title = "hindu_dharma.3.t"
    desc = "hindu_dharma.3.d"
    picture = MISSIONARY_EVENT_PICTURE

    trigger = {{
        religion = hinduism
        is_year = 1480
    }}

    mean_time_to_happen = {{ months = 120 }}

    option = {{
        name = "hindu_dharma.3.a"
        every_neighbor_province = {{
            limit = {{
                NOT = {{ religion = hinduism }}
                owner = {{ religion = hinduism }}
            }}
            change_religion = hinduism
        }}
    }}
}}
"""
        output_path = f"{output_dir}/events/HinduDharmaEvents.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(event_script)
        return output_path

    @staticmethod
    def generate_holy_city_modifier_file(output_dir: str) -> str:
        """Creates the modifier database for the Hindu holy center."""
        os.makedirs(f"{output_dir}/common/event_modifiers", exist_ok=True)

        modifier_script = """# Hindu Vatican Capital Buffs
hindu_holy_city_seat = {
    local_missionary_strength = 0.05
    fort_defense = 0.25
    local_tax_modifier = 0.30
    local_autonomy = -0.10
    local_development_cost = -0.10
    trade_value_modifier = 0.20
}

# Dynamic War Modifiers
blitzkrieg_offensive = {
    discipline = 0.10
    land_morale = 0.15
    siege_ability = 0.20
}

carthaginian_fury = {
    looting_speed = 0.50
    war_exhaustion_cost = -0.25
    hostile_attrition = 2.0
    devastation = -0.05
}
"""
        output_path = f"{output_dir}/common/event_modifiers/02_hindu_modifiers.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(modifier_script)
        return output_path

    @staticmethod
    def generate_corrupt_church_aspects(output_dir: str) -> str:
        """Creates church aspects that make Christian reforms extremely costly."""
        os.makedirs(f"{output_dir}/common/church_aspects", exist_ok=True)

        aspect_script = """# Expensive and Corrupt Christian Reforms Matrix

# Catholic - extremely expensive and corrupt
aspect_corrupt_indulgences = {
    cost = 500
    effect = {
        global_corruption = 0.02
        tax_income = 5
        inflation = 0.5
    }
}

aspect_inefficient_bureaucracy = {
    cost = 600
    effect = {
        stability_cost_modifier = 0.10
        all_power_cost = 0.05
    }
}

aspect_simony = {
    cost = 700
    effect = {
        global_corruption = 0.03
        development_cost = 0.15
    }
}

aspect_inquisition_tribunal = {
    cost = 800
    effect = {
        global_unrest = 5
        missionary_maintenance_cost = 0.50
    }
}

# Protestant - still corrupt but less
aspect_fractured_reform = {
    cost = 400
    effect = {
        tolerance_heretic = -2
        idea_cost = 0.10
    }
}

aspect_puritanical_zeal = {
    cost = 350
    effect = {
        global_unrest = 3
        stability_cost_modifier = 0.10
    }
}
"""
        output_path = f"{output_dir}/common/church_aspects/00_church_aspects.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(aspect_script)
        return output_path


# ═══════════════════════════════════════════════════════════════
#  CULTURE SYSTEM
# ═══════════════════════════════════════════════════════════════

class CultureGenerator:
    """
    Generates custom culture groups with inverted power dynamics:
    - Afro-Asian cultures: advanced, refined, wealthy
    - European cultures: tribal, primitive, fragmented
    """

    AFRICAN_CULTURES = {
        "west_african": {
            "color": {"0.8 0.6 0.2"},
            "graphical_culture": "sub_saharan",
            "cultures": ["manden", "songhai", "yoruba", "akan", "wolof",
                         "hausa", "fulani", "dagomba"],
        },
        "east_african": {
            "color": {"0.7 0.5 0.3"},
            "graphical_culture": "sub_saharan",
            "cultures": ["amhara", "oromo", "somali", "swahili", "kushite",
                         "nubian", "afar", "sidama"],
        },
        "central_african": {
            "color": {"0.6 0.4 0.2"},
            "graphical_culture": "sub_saharan",
            "cultures": ["kongo", "luba", "lunda", "mongo", "ngbaka",
                         "azande", "bangi", "bomitaba"],
        },
        "south_african": {
            "color": {"0.5 0.3 0.1"},
            "graphical_culture": "sub_saharan",
            "cultures": ["zulu", "xhosa", "sotho", "tswana", "venda",
                         "ndebele", "swazi", "tsonga"],
        },
    }

    ASIAN_CULTURES = {
        "indian_vedic": {
            "color": {"0.9 0.7 0.1"},
            "graphical_culture": "indian",
            "cultures": ["bhojpuri", "marathi", "rajput", "gujarati", "bengali",
                         "tamil", "telugu", "kannada", "malayalam", "odia"],
        },
        "southeast_asian": {
            "color": {"0.8 0.6 0.1"},
            "graphical_culture": "east_asian",
            "cultures": ["javanese", "malay", "khmer", "burmese", "thai",
                         "vietnamese", "lao", "cham", "minangkabau"],
        },
        "east_asian_dominant": {
            "color": {"0.7 0.5 0.1"},
            "graphical_culture": "east_asian",
            "cultures": ["han_sovereign", "korean_imperial", "yamato_shogunate",
                         "tang_heritage", "ming_ascendant"],
        },
    }

    EUROPEAN_CULTURES = {
        "north_european_tribal": {
            "color": {"0.4 0.4 0.4"},
            "graphical_culture": "western",
            "cultures": ["norse_tribal", "saxon_tribal", "franc_tribal",
                         "angle_tribal", "jute_tribal"],
        },
        "central_european_tribal": {
            "color": {"0.35 0.35 0.35"},
            "graphical_culture": "western",
            "cultures": ["germanic_tribal", "slavic_tribal", "celtic_tribal",
                         "goth_tribal", "vandal_tribal"],
        },
        "south_european_decayed": {
            "color": {"0.5 0.4 0.3"},
            "graphical_culture": "western",
            "cultures": ["latin_decayed", "hellenic_decayed", "iberian_decayed",
                         "italic_decayed", "gaul_decayed"],
        },
    }

    @classmethod
    def generate_cultures_file(cls, output_dir: str) -> str:
        """Writes common/cultures/00_cultures.txt."""
        os.makedirs(f"{output_dir}/common/cultures", exist_ok=True)

        all_groups = {}
        all_groups.update(cls.AFRICAN_CULTURES)
        all_groups.update(cls.ASIAN_CULTURES)
        all_groups.update(cls.EUROPEAN_CULTURES)

        content = "# ═══════════════════════════════════════════\n"
        content += "# INVERTED CULTURE GROUPS DATABASE\n"
        content += "# African/Asian: Advanced, Refined, Wealthy\n"
        content += "# European: Tribal, Primitive, Fragmented\n"
        content += "# ═══════════════════════════════════════════\n\n"

        for group_name, group_data in all_groups.items():
            content += f"{group_name} = {{\n"
            content += f"    graphical_culture = {group_data['graphical_culture']}\n\n"
            for cult in group_data["cultures"]:
                content += f"    {cult} = {{\n"
                content += f"        color = {{ {group_data['color']} }}\n"
                # Add dynasty names for advanced cultures
                if "tribal" not in cult and "decayed" not in cult:
                    content += f"        dynasty_names = {{\n"
                    content += f'            "Singh" "Sharma" "Patel" "Gupta" "Chandra"\n'
                    content += f"        }}\n"
                content += f"    }}\n\n"
            content += f"}}\n\n"

        output_path = f"{output_dir}/common/cultures/00_cultures.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return output_path

    @classmethod
    def get_culture_for_continent(cls, continent: str) -> str:
        """Returns an appropriate culture name for a continent."""
        if "africa" in continent or continent == "west_africa":
            group = cls.AFRICAN_CULTURES.get("west_african", {})
            cultures = group.get("cultures", ["manden"])
            return random.choice(cultures)
        elif continent in ("south_asia", "middle_east"):
            group = cls.ASIAN_CULTURES.get("indian_vedic", {})
            cultures = group.get("cultures", ["marathi"])
            return random.choice(cultures)
        elif "europe" in continent:
            group = cls.EUROPEAN_CULTURES.get("north_european_tribal", {})
            cultures = group.get("cultures", ["norse_tribal"])
            return random.choice(cultures)
        else:
            group = cls.ASIAN_CULTURES.get("southeast_asian", {})
            cultures = group.get("cultures", ["javanese"])
            return random.choice(cultures)


# ═══════════════════════════════════════════════════════════════
#  NATIONAL IDEAS GENERATOR
# ═══════════════════════════════════════════════════════════════

ADVANCED_MODIFIERS = [
    "trade_efficiency = 0.15",
    "global_trade_power = 0.20",
    "technology_cost = -0.10",
    "production_efficiency = 0.15",
    "idea_cost = -0.10",
    "global_ship_trade_power = 0.25",
    "merchants = 1",
    "discipline = 0.05",
    "global_institution_spread = 0.20",
    "development_cost = -0.10",
    "global_tax_modifier = 0.15",
    "land_morale = 0.10",
    "naval_morale = 0.10",
    "infantry_power = 0.10",
    "cavalry_power = 0.10",
]

PRIMITIVE_MODIFIERS = [
    "land_attrition = -0.15",
    "fort_defense = 0.15",
    "infantry_power = 0.10",
    "stability_cost_modifier = -0.15",
    "manpower_recovery_speed = 0.15",
    "hostile_attrition = 1.0",
    "unrest = -2",
    "defensiveness = 0.20",
    "global_unrest = 2",
    "corruption = 0.05",
    "technology_cost = 0.10",
    "trade_efficiency = -0.10",
    "production_efficiency = -0.05",
]


class IdeaGenerator:
    """Creates tailored national idea sets based on continent (inverted power)."""

    IDEA_NAMES_ADVANCED = [
        "Imperial Dharmic Law", "Celestial Bureaucracy",
        "Sacred River Trade", "Fortress of the Faith",
        "Vedic Scholarship", "Divine Mandate Army",
        "Spice Road Dominance", "Temple City Economy",
        "Iron Discipline", "Infinite Wisdom",
    ]

    IDEA_NAMES_PRIMITIVE = [
        "Tribal Survival", "Desperate Fortifications",
        "Scorched Earth Tactics", "Famine Resistance",
        "Warrior Code", "Peasant Levy",
        "Raiding Traditions", "Fractured Faith",
        "Mud Wall Defenses", "Last Stand Doctrine",
    ]

    @staticmethod
    def generate_national_ideas(tag: str, center_y: int, map_height: int = 2048) -> str:
        """Creates a tailored National Idea script block for a country."""
        h = map_height
        is_advanced = (h * 0.25 <= center_y < h * 0.75)
        pool = list(ADVANCED_MODIFIERS) if is_advanced else list(PRIMITIVE_MODIFIERS)
        names = IdeaGenerator.IDEA_NAMES_ADVANCED if is_advanced else IdeaGenerator.IDEA_NAMES_PRIMITIVE

        while len(pool) < 10:
            pool += pool
        chosen_buffs = random.sample(pool, 10)
        chosen_names = random.sample(names, min(7, len(names)))

        # Ensure we have 7 idea names
        while len(chosen_names) < 7:
            chosen_names.append(f"Tradition_{len(chosen_names)}")

        ideas_script = f"""
{tag}_ideas = {{
    start = {{
        {chosen_buffs[0]}
        {chosen_buffs[1]}
    }}
    bonus = {{
        {chosen_buffs[2]}
    }}
    trigger = {{
        tag = {tag}
    }}
    free = yes

    {tag}_idea_1 = {{
        {chosen_buffs[3]}
    }}
    {tag}_idea_2 = {{
        {chosen_buffs[4]}
    }}
    {tag}_idea_3 = {{
        {chosen_buffs[5]}
    }}
    {tag}_idea_4 = {{
        {chosen_buffs[6]}
    }}
    {tag}_idea_5 = {{
        {chosen_buffs[7]}
    }}
    {tag}_idea_6 = {{
        {chosen_buffs[8]}
    }}
    {tag}_idea_7 = {{
        {chosen_buffs[9]}
    }}
}}
"""
        return ideas_script


# ═══════════════════════════════════════════════════════════════
#  COUNTRY GENERATOR
# ═══════════════════════════════════════════════════════════════

@dataclass
class CountryData:
    """Complete data for a generated country."""
    tag: str = ""
    short_name: str = ""
    full_name: str = ""
    government: str = "monarchy"
    tech_group: str = "chinese"
    color: Tuple[int, int, int] = (128, 128, 128)
    capital_province: int = 1
    center_x: int = 0
    center_y: int = 0
    continent: str = ""
    religion: str = "hinduism"
    primary_culture: str = "manden"
    is_advanced: bool = True
    is_emperor: bool = False
    is_elector: bool = False
    is_hre_member: bool = False
    adm: int = 3
    dip: int = 3
    mil: int = 3
    institutions: List[int] = field(default_factory=list)
    ruler_name: str = ""
    ruler_adm: int = 3
    ruler_dip: int = 3
    ruler_mil: int = 3
    ruler_age: int = 30


class CountryGenerator:
    """
    Generates complete country data with inverted power dynamics.
    African/Asian countries are powerful empires, European countries are tribal.
    """

    TAG_PREFIXES_ADVANCED = ["AK", "AS", "BH", "CH", "DV", "EM",
                              "GD", "HV", "IM", "JP", "KL", "MN"]
    TAG_PREFIXES_PRIMITIVE = ["EU", "GD", "NR", "PR", "SB", "TB"]

    _used_tags = set()

    @classmethod
    def generate_unique_tag(cls, is_advanced: bool) -> str:
        """Generate a unique 3-letter country tag."""
        prefixes = cls.TAG_PREFIXES_ADVANCED if is_advanced else cls.TAG_PREFIXES_PRIMITIVE
        for _ in range(100):
            prefix = random.choice(prefixes)
            suffix = f"{random.randint(1, 99):02d}"
            tag = f"{prefix}{suffix}"
            if tag not in cls._used_tags:
                cls._used_tags.add(tag)
                return tag
        # Fallback
        tag = f"C{len(cls._used_tags):03d}"
        cls._used_tags.add(tag)
        return tag

    @classmethod
    def generate_country(cls, province, continent: str = "", map_height: int = 2048) -> CountryData:
        """Generate a complete country based on a province's location."""
        center_y = province.center_y
        h = map_height
        is_advanced = (h * 0.25 <= center_y < h * 0.75)
        continent = continent or province.continent_name

        tag = cls.generate_unique_tag(is_advanced)

        # Generate name based on continent
        if any(x in continent for x in ["africa", "west_africa", "east_africa",
                                          "central_africa", "south_africa"]):
            root = random.choice(ROOT_NAMES_AFRICAN)
            leader_pool = LEADER_NAMES_AFRICAN
        elif any(x in continent for x in ["asia", "south_asia", "southeast"]):
            root = random.choice(ROOT_NAMES_ASIAN)
            leader_pool = LEADER_NAMES_ASIAN
        else:
            root = random.choice(ROOT_NAMES_EUROPEAN)
            leader_pool = LEADER_NAMES_EUROPEAN

        short_name, full_name = cls._generate_country_name(root, is_advanced)

        # Government type
        if is_advanced:
            gov_type = random.choice(["monarchy", "republic", "theocracy"])
            gov_name = random.choice(GOVERNMENTS[gov_type])
        else:
            gov_type = random.choice(["monarchy", "monarchy", "monarchy"])
            gov_name = random.choice(["Chiefdom", "Warlord State", "Clan"])

        # Tech group (inverted) — proportional to map height
        if h * 0.5375 <= center_y < h * 0.75:
            tech_group = "chinese"
        elif h * 0.4375 <= center_y < h * 0.5375:
            tech_group = "indian"
        elif h * 0.375 <= center_y < h * 0.4375:
            tech_group = "muslim"
        elif h * 0.25 <= center_y < h * 0.375:
            tech_group = "east_african"
        elif center_y >= h * 0.75:
            tech_group = "north_american"
        else:
            tech_group = "western"

        # Religion (inverted)
        from eu4_wgs_v8.analytics.heightmap_analyzer import HeightmapAnalyzer
        religion = HeightmapAnalyzer(map_height=h)._assign_inverted_religion(province, h)

        # Culture
        culture = CultureGenerator.get_culture_for_continent(continent)

        # Ruler skills (inverted)
        if is_advanced:
            ruler_adm = random.choices([3, 4, 5, 6], weights=[0.2, 0.4, 0.3, 0.1])[0]
            ruler_dip = random.choices([3, 4, 5, 6], weights=[0.2, 0.4, 0.3, 0.1])[0]
            ruler_mil = random.choices([3, 4, 5, 6], weights=[0.2, 0.4, 0.3, 0.1])[0]
        else:
            ruler_adm = random.choices([0, 1, 2, 3], weights=[0.2, 0.4, 0.3, 0.1])[0]
            ruler_dip = random.choices([0, 1, 2, 3], weights=[0.2, 0.4, 0.3, 0.1])[0]
            ruler_mil = random.choices([0, 1, 2, 3], weights=[0.15, 0.35, 0.35, 0.15])[0]

        # Ruler name
        ruler_name = random.choice(leader_pool)
        moniker = random.choice(LEADER_MONIKERS)
        if moniker:
            ruler_name = f"{ruler_name} {moniker}"

        # Institutions embraced (inverted)
        if tech_group == "chinese":
            institutions = [1, 1, 1, 0, 0, 0, 0, 0]
        elif tech_group == "indian":
            institutions = [1, 1, 0, 0, 0, 0, 0, 0]
        elif tech_group == "muslim":
            institutions = [1, 1, 0, 0, 0, 0, 0, 0]
        elif tech_group in ("east_african", "nomad_group"):
            institutions = [1, 0, 0, 0, 0, 0, 0, 0]
        else:
            institutions = [0, 0, 0, 0, 0, 0, 0, 0]

        # Country color
        if is_advanced:
            color = (
                random.randint(50, 230),
                random.randint(50, 230),
                random.randint(20, 200)
            )
        else:
            color = (
                random.randint(40, 120),
                random.randint(40, 120),
                random.randint(40, 120)
            )

        return CountryData(
            tag=tag,
            short_name=short_name,
            full_name=full_name,
            government=gov_type,
            tech_group=tech_group,
            color=color,
            capital_province=province.id,
            center_x=province.center_x,
            center_y=center_y,
            continent=continent,
            religion=religion,
            primary_culture=culture,
            is_advanced=is_advanced,
            adm=ruler_adm + 3,
            dip=ruler_dip + 3,
            mil=ruler_mil + 3,
            institutions=institutions,
            ruler_name=ruler_name,
            ruler_adm=ruler_adm,
            ruler_dip=ruler_dip,
            ruler_mil=ruler_mil,
            ruler_age=random.randint(18, 55),
        )

    @staticmethod
    def _generate_country_name(root: str, is_advanced: bool) -> Tuple[str, str]:
        """Procedurally generates flavor-rich country names."""
        style_roll = random.randint(1, 4)

        if style_roll == 1:
            acr, full_title = random.choice(ACRONYMS)
            return acr, f"{acr} the {root} {full_title}"
        elif style_roll == 2:
            adj = random.choice(ADJECTIVES)
            gov = random.choice(
                GOVERNMENTS["monarchy"] + GOVERNMENTS["republic"]
                if is_advanced else ["Chiefdom", "Clan", "Warband"]
            )
            return root, f"{adj} {root} {gov}"
        elif style_roll == 3:
            adj_root = root + "an" if root.endswith("e") else root + "ian"
            gov = random.choice(GOVERNMENTS["monarchy"] if is_advanced else ["Chiefdom", "Clan"])
            return root, f"{adj_root} {gov}"
        else:
            adj_root = root + "an" if root.endswith("e") else root + "ian"
            gov = random.choice(
                GOVERNMENTS["republic"] + GOVERNMENTS["theocracy"]
                if is_advanced else ["Raiding Band", "Feuding Tribe"]
            )
            return root, f"The {adj_root} {gov}"


# ═══════════════════════════════════════════════════════════════
#  SECOND HRE (CELESTIAL DIRECTORATE)
# ═══════════════════════════════════════════════════════════════

class CelestialDirectorate:
    """
    Second HRE-like empire mechanics.
    The Celestial Directorate is an Afro-Asian empire system
    parallel to the European HRE but far more powerful.
    """

    @staticmethod
    def generate_imperial_reforms(output_dir: str) -> str:
        """Writes the Celestial Directorate empire group parameters."""
        os.makedirs(f"{output_dir}/common/imperial_reforms", exist_ok=True)

        mechanics_script = """# ═══════════════════════════════════════════════════
# THE CELESTIAL DIRECTORATE - Second HRE
# Afro-Asian Empire System - Far More Powerful than European HRE
# ═════════════════════════════════════════════════

celestial_directorate = {
    style = hre

    member_modifier = {
        technology_cost = -0.05
        global_trade_power = 0.10
        development_cost = -0.05
    }

    elector_modifier = {
        legitimacy = 1
        diplomatic_reputation = 1
    }

    emperor_modifier = {
        diplomatic_upkeep = 2
        imperial_authority = 0.10
        manpower_recovery_speed = 0.15
        global_tax_modifier = 0.10
    }

    # IMPERIAL REFORMS - More powerful than HRE equivalents
    reform_celestial_call = {
        imperial_authority_cost = 50
        effect = {
            production_efficiency = 0.05
            manpower_recovery_speed = 0.10
        }
    }

    reform_celestial_unification = {
        imperial_authority_cost = 50
        effect = {
            vassal_income = 0.25
            global_tax_modifier = 0.10
        }
    }

    reform_celestial_taxation = {
        imperial_authority_cost = 50
        effect = {
            global_tax_modifier = 0.15
            production_efficiency = 0.10
        }
    }

    reform_celestial_standards = {
        imperial_authority_cost = 50
        effect = {
            discipline = 0.03
            land_morale = 0.05
        }
    }

    reform_celestial_court = {
        imperial_authority_cost = 50
        effect = {
            diplomatic_reputation = 2
            imperial_authority = 0.05
        }
    }

    reform_celestial_army = {
        imperial_authority_cost = 75
        effect = {
            discipline = 0.05
            manpower_recovery_speed = 0.20
        }
    }

    reform_celestial_navy = {
        imperial_authority_cost = 75
        effect = {
            naval_morale = 0.15
            global_ship_trade_power = 0.20
        }
    }

    reform_celestial_inquisition = {
        imperial_authority_cost = 75
        effect = {
            global_missionary_strength = 0.03
            tolerance_own = 2
        }
    }

    reform_celestial_centralization = {
        imperial_authority_cost = 100
        effect = {
            core_creation_cost = -0.15
            global_autonomy = -0.05
        }
    }

    reform_celestial_dominion = {
        imperial_authority_cost = 100
        effect = {
            discipline = 0.10
            all_power_cost = -0.10
        }
    }
}
"""
        output_path = f"{output_dir}/common/imperial_reforms/celestial_directorate.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(mechanics_script)
        return output_path

    @staticmethod
    def assign_directorate_roles(countries: Dict[str, CountryData]) -> Dict[str, str]:
        """
        Assign emperor, elector, and member roles for the Celestial Directorate.
        Only advanced (Afro-Asian) countries can be members.
        """
        advanced_tags = [tag for tag, c in countries.items() if c.is_advanced]

        if len(advanced_tags) < 3:
            return {}

        # Sort by power (center_y in the advanced zone = more power)
        advanced_tags.sort(key=lambda t: -countries[t].center_y)

        director_emperor = advanced_tags[0] if advanced_tags else None
        celestial_electors = advanced_tags[1:min(8, len(advanced_tags))]
        directorate_members = advanced_tags[min(8, len(advanced_tags)):]

        assignments = {}
        if director_emperor:
            assignments[director_emperor] = "emperor = celestial_directorate"
            countries[director_emperor].is_emperor = True

        for tag in celestial_electors:
            assignments[tag] = "elector = celestial_directorate"
            countries[tag].is_elector = True

        for tag in directorate_members:
            assignments[tag] = "member = celestial_directorate"
            countries[tag].is_hre_member = True

        return assignments


# ═══════════════════════════════════════════════════════════════
#  TRADE GOODS & ECONOMY
# ═══════════════════════════════════════════════════════════════

RICH_COMMODITIES = {
    "solar_silk":       {"base_price": 5.0, "prov_buff": "production_efficiency = 0.10", "global_buff": "trade_efficiency = 0.10"},
    "spiceweave_glass": {"base_price": 4.5, "prov_buff": "local_trade_power_modifier = 0.15", "global_buff": "global_trade_power = 0.15"},
    "abyssal_pearls":   {"base_price": 6.0, "prov_buff": "local_tax_modifier = 0.20", "global_buff": "technology_cost = -0.05"},
    "island_nectar":    {"base_price": 4.0, "prov_buff": "local_manpower_modifier = 0.15", "global_buff": "land_morale = 0.05"},
    "sacred_incense":   {"base_price": 4.5, "prov_buff": "local_missionary_strength = 0.02", "global_buff": "global_missionary_strength = 0.02"},
    "celestial_spice":  {"base_price": 5.5, "prov_buff": "local_trade_power_modifier = 0.20", "global_buff": "global_trade_power = 0.10"},
    "diamond_dust":     {"base_price": 7.0, "prov_buff": "local_tax_modifier = 0.25", "global_buff": "technology_cost = -0.08"},
}

BARREN_COMMODITIES = {
    "corrupt_sludge": {"base_price": 1.0, "prov_buff": "local_unrest = 1", "global_buff": "global_corruption = 0.01"},
    "brittle_stone":  {"base_price": 1.2, "prov_buff": "fort_defense = -0.10", "global_buff": "stability_cost_modifier = 0.10"},
    "salted_mud":     {"base_price": 0.8, "prov_buff": "local_autonomy_growth = 0.05", "global_buff": "all_power_cost = 0.05"},
    "rotting_timber": {"base_price": 0.9, "prov_buff": "local_development_cost = 0.10", "global_buff": "building_cost = 0.15"},
}


class TradeGenerator:
    """Generates trade goods, trade nodes, and price files."""

    @staticmethod
    def generate_trade_goods_files(output_dir: str) -> str:
        """Writes EU4 trade good definitions and price files."""
        os.makedirs(f"{output_dir}/common/trade_goods", exist_ok=True)
        os.makedirs(f"{output_dir}/common/prices", exist_ok=True)

        tg_script = "# Procedural Trade Goods Matrix\n"
        price_script = "# Procedural Price Layout\n"

        all_goods = {**RICH_COMMODITIES, **BARREN_COMMODITIES}
        for name, data in all_goods.items():
            tg_script += (
                f"{name} = {{\n"
                f"    color = {{ {round(random.random(), 2)} {round(random.random(), 2)} {round(random.random(), 2)} }}\n"
                f"    modifier = {{ {data['global_buff']} }}\n"
                f"    province = {{ {data['prov_buff']} }}\n"
                f"    uncolonized_weight = 0\n"
                f"}}\n\n"
            )
            price_script += (
                f"{name} = {{\n"
                f"    base_price = {data['base_price']}\n"
                f"    min_price = 0.5\n"
                f"    max_price = 15.0\n"
                f"}}\n\n"
            )

        tg_path = f"{output_dir}/common/trade_goods/00_trade_goods.txt"
        with open(tg_path, "w", encoding="utf-8") as f:
            f.write(tg_script)

        price_path = f"{output_dir}/common/prices/00_prices.txt"
        with open(price_path, "w", encoding="utf-8") as f:
            f.write(price_script)

        return tg_path

    @staticmethod
    def generate_inverted_trade_nodes(province_infos: List,
                                       output_dir: str,
                                       map_height: int = 2048) -> str:
        """
        Groups provinces into trade nodes, routing wealth
        toward African/Asian/Island hubs.
        """
        h = map_height
        island_ids = set()
        node_buckets = {
            "european_rim": {"provinces": [], "outbound": ["middle_east_hub"]},
            "mediterranean_crossroads": {"provinces": [], "outbound": ["middle_east_hub"]},
            "middle_east_hub": {"provinces": [], "outbound": ["african_wealth_hub", "asian_wealth_hub"]},
            "african_wealth_hub": {"provinces": [], "outbound": ["island_treasure_vault"]},
            "asian_wealth_hub": {"provinces": [], "outbound": ["island_treasure_vault"]},
            "island_treasure_vault": {"provinces": [], "outbound": []},
        }

        for p in province_infos:
            if p.is_sea or p.is_wasteland:
                continue
            pid = p.id
            y = p.center_y

            if p.is_island:
                node_buckets["island_treasure_vault"]["provinces"].append(pid)
                island_ids.add(pid)
            elif y < h * 0.25:
                node_buckets["european_rim"]["provinces"].append(pid)
            elif y < h * 0.34:
                node_buckets["mediterranean_crossroads"]["provinces"].append(pid)
            elif y < h * 0.49:
                node_buckets["middle_east_hub"]["provinces"].append(pid)
            elif y < h * 0.635:
                node_buckets["african_wealth_hub"]["provinces"].append(pid)
            else:
                node_buckets["asian_wealth_hub"]["provinces"].append(pid)

        os.makedirs(f"{output_dir}/common/tradenodes", exist_ok=True)
        output_path = f"{output_dir}/common/tradenodes/00_tradenodes.txt"

        with open(output_path, "w", encoding="utf-8") as f:
            for node_name, data in node_buckets.items():
                prov_list = " ".join(map(str, data["provinces"][:200]))
                location_id = data["provinces"][0] if data["provinces"] else 1
                end_flag = "yes" if not data["outbound"] else "no"
                f.write(f"{node_name} = {{\n")
                f.write(f"    location = {location_id}\n")
                f.write(f"    provinces = {{ {prov_list} }}\n")
                f.write(f"    end = {end_flag}\n")
                for target in data["outbound"]:
                    f.write(f'    outgoing = {{\n')
                    f.write(f'        name = "{target}"\n')
                    f.write(f'        path = {{ {location_id} }}\n')
                    f.write(f'    }}\n')
                f.write("}\n\n")

        return output_path

    @staticmethod
    def generate_trade_price_events(output_dir: str) -> str:
        """Creates EU4 events that cripple European economies and enrich Asian/African ones."""
        os.makedirs(f"{output_dir}/events", exist_ok=True)

        event_script = """# ═══════════════════════════════════════════════════
# INVERTED ECONOMIC FLUCTUATION EVENTS
# Europe: economic collapse, corruption, decay
# Africa/Asia: golden age, prosperity, advancement
# ═════════════════════════════════════════════════

namespace = inverted_economy

# European economic collapse
country_event = {
    id = inverted_economy.1
    title = "inverted_economy.1.t"
    desc = "inverted_economy.1.d"
    picture = TRADE_EVENT_PICTURE

    trigger = {
        technology_group = western
        is_year = 1500
    }
    mean_time_to_happen = { months = 12 }

    option = {
        name = "inverted_economy.1.a"
        add_corruption = 2.0
        add_inflation = 5.0
        change_price = {
            trade_goods = corrupt_sludge
            key = "sludge_collapse"
            value = -0.50
            duration = -1
        }
    }
}

# Afro-Asian golden age
country_event = {
    id = inverted_economy.2
    title = "inverted_economy.2.t"
    desc = "inverted_economy.2.d"
    picture = MERCHANTS_EVENT_PICTURE

    trigger = {
        NOT = { technology_group = western }
        is_year = 1520
    }
    mean_time_to_happen = { months = 24 }

    option = {
        name = "inverted_economy.2.a"
        add_treasury = 500
        change_price = {
            trade_goods = abyssal_pearls
            key = "pearl_boom"
            value = 1.50
            duration = -1
        }
    }
}

# European famine
country_event = {
    id = inverted_economy.3
    title = "inverted_economy.3.t"
    desc = "inverted_economy.3.d"
    picture = PLAGUE_EVENT_PICTURE

    trigger = {
        technology_group = western
        is_year = 1550
    }
    mean_time_to_happen = { months = 60 }

    option = {
        name = "inverted_economy.3.a"
        lose_mercantilism = 5
        every_owned_province = {
            limit = { is_capital = no }
            change_development = -1
        }
    }
}

# Asian technological breakthrough
country_event = {
    id = inverted_economy.4
    title = "inverted_economy.4.t"
    desc = "inverted_economy.4.d"
    picture = UNIVERSITY_EVENT_PICTURE

    trigger = {
        technology_group = chinese
        is_year = 1600
    }
    mean_time_to_happen = { months = 120 }

    option = {
        name = "inverted_economy.4.a"
        add_institution_embracement = {
            which = printing_press
            value = 100
        }
        add_treasury = 200
        every_owned_province = {
            limit = { is_capital = yes }
            change_development = 2
        }
    }
}
"""
        output_path = f"{output_dir}/events/InvertedEconomyEvents.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(event_script)
        return output_path


# ═══════════════════════════════════════════════════════════════
#  WAR & DIPLOMACY GENERATOR
# ═══════════════════════════════════════════════════════════════

class DiplomacyGenerator:
    """Generates starting alliances, rivalries, and wars."""

    @staticmethod
    def generate_diplomacy(output_dir: str,
                           countries: Dict[str, CountryData]) -> str:
        """Auto-generate starting alliances, rivalries, and CBs."""
        os.makedirs(f"{output_dir}/history/diplomacy", exist_ok=True)

        diplomacy_script = "# ═══════════════════════════════════════════════════\n"
        diplomacy_script += "# Procedural Diplomatic Starting Matrix\n"
        diplomacy_script += "# ═══════════════════════════════════════════════════\n\n"

        tags = list(countries.keys())
        processed_pairs = set()

        for i, tag_a in enumerate(tags):
            pos_a = countries[tag_a]
            for tag_b in tags[i + 1:]:
                pos_b = countries[tag_b]

                pair_key = tuple(sorted([tag_a, tag_b]))
                if pair_key in processed_pairs:
                    continue

                # Calculate distance
                distance = np.hypot(
                    pos_a.center_x - pos_b.center_x,
                    pos_a.center_y - pos_b.center_y
                )

                if distance < 450:
                    roll = random.random()

                    if roll < 0.35:
                        diplomacy_script += f"""# Border Friction Rivalry
rival = {{
\tfirst = {tag_a}
\tsecond = {tag_b}
\tstart_date = 1444.11.11
}}

"""
                    elif roll < 0.75:
                        diplomacy_script += f"""# Strategic Defensive Pact
alliance = {{
\tfirst = {tag_a}
\tsecond = {tag_b}
\tstart_date = 1444.11.11
}}

"""
                    else:
                        diplomacy_script += f"""# Royal Marriage
marriage = {{
\tfirst = {tag_a}
\tsecond = {tag_b}
\tstart_date = 1444.11.11
}}

"""

                # Containment CB: Advanced nations have CBs on European nations
                if (pos_a.is_advanced and not pos_b.is_advanced and distance < 700):
                    diplomacy_script += f"""# European Containment Directive
casus_belli = {{
\ttype = cb_feudal_imperialism
\tattacker = {tag_a}
\tdefender = {tag_b}
\tstart_date = 1444.11.11
\tend_date = 1821.1.1
}}

"""

                processed_pairs.add(pair_key)

        output_path = f"{output_dir}/history/diplomacy/procedural_alliances.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(diplomacy_script)
        return output_path

    @staticmethod
    def generate_war_events(output_dir: str) -> str:
        """Generates cascading crisis and mega-war event files."""
        os.makedirs(f"{output_dir}/events", exist_ok=True)

        event_script = """# ═══════════════════════════════════════════════════
# Procedural Dynamic War Crisis Chains
# ═════════════════════════════════════════════════

namespace = dynamic_crisis

country_event = {
    id = dynamic_crisis.1
    title = "The Hegemon's Ambition"
    desc = "A great power has expanded beyond all limits."
    picture = MILITARY_CAMP_EVENT_PICTURE
    trigger = {
        num_of_cities = 50
        is_great_power = yes
        NOT = { technology_group = western }
    }
    mean_time_to_happen = { months = 240 }
    option = {
        name = "The World Shall Bow!"
        add_ae = 100
        add_country_modifier = { name = "blitzkrieg_offensive" duration = 3650 }
        every_neighbor_country = {
            add_cb = { type = cb_dismantle_empire target = ROOT }
        }
    }
}

country_event = {
    id = dynamic_crisis.2
    title = "The Bipolar Iron Curtain"
    desc = "Two apex empires have entered a state of absolute strategic deadlock."
    picture = DIPLOMACY_EVENT_PICTURE
    trigger = {
        is_great_power = yes
        any_great_power = { NOT = { tag = ROOT } num_of_cities = 40 }
        is_year = 1600
    }
    mean_time_to_happen = { months = 360 }
    option = {
        name = "Fund the Western Backwater Proxies"
        add_treasury = -1000
        random_country = {
            limit = { technology_group = western }
            add_treasury = 800
            create_vassal = ROOT
        }
    }
}

country_event = {
    id = dynamic_crisis.3
    title = "Delenda Est"
    desc = "The city must burn."
    picture = BURNING_CITY_EVENT_PICTURE
    trigger = { has_rival = yes  is_in_war = yes }
    mean_time_to_happen = { months = 480 }
    option = {
        name = "Sow their fields with salt!"
        add_country_modifier = { name = "carthaginian_fury" duration = 1825 }
    }
}

# European Collapse Chain
country_event = {
    id = dynamic_crisis.4
    title = "The Dark Age Descends"
    desc = "The primitive European kingdoms collapse into chaos once more."
    picture = PLAGUE_EVENT_PICTURE
    trigger = {
        technology_group = western
        is_year = 1550
    }
    mean_time_to_happen = { months = 180 }
    option = {
        name = "We cannot hold!"
        stability = -3
        add_corruption = 5.0
        every_owned_province = {
            limit = { unrest > 5 }
            spawn_rebels = { type = peasant_rebels size = 2 }
        }
    }
}
"""
        output_path = f"{output_dir}/events/DynamicCrisisEvents.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(event_script)
        return output_path
