"""
SVG Reference Parser Module
============================
Parses EU4 SVG map files (from eu4-svg-map) to extract province boundaries
and types (land, sea, lakes, etc.) for use as visual references during
province BMP generation and validation.

Supports:
- SVG path parsing and polygon extraction
- Province type classification by color/fill
- Reference map generation
- Comparative analysis between generated and reference maps
"""

import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SVGProvince:
    """Represents a province extracted from SVG reference."""
    id: str
    province_type: str  # 'land', 'sea', 'lake', 'coastal', 'wasteland'
    fill_color: str
    rgb_color: Tuple[int, int, int]
    path_data: str
    label: Optional[str] = None


class SVGReferenceParser:
    """
    Parses EU4 SVG map files and extracts province information.
    SVG files should be from eu4-svg-map repository.
    """

    # Common province type color mappings
    PROVINCE_TYPE_COLORS = {
        # Sea colors (various shades of blue)
        "#002855": "sea",
        "#003d7a": "sea",
        "#0052a3": "sea",
        "blue": "sea",
        "#0000FF": "sea",

        # Lake colors (light blue)
        "#87CEEB": "lake",
        "#00BFFF": "lake",
        "#ADD8E6": "lake",
        "lightblue": "lake",
        "#B0E0E6": "lake",

        # Land colors (various greens, browns)
        "#5a9642": "land",
        "#6db84c": "land",
        "#7ec850": "land",
        "#8fb854": "land",
        "#98b442": "land",
        "green": "land",
        "#00AA00": "land",

        # Wasteland/Impassable (grays, blacks)
        "#1a1a1a": "wasteland",
        "#333333": "wasteland",
        "#555555": "wasteland",
        "gray": "wasteland",
        "black": "wasteland",
        "#000000": "wasteland",
    }

    def __init__(self, svg_path: Path):
        """
        Initialize parser with SVG file path.
        
        Args:
            svg_path: Path to SVG file from eu4-svg-map
        """
        self.svg_path = Path(svg_path)
        self.tree = None
        self.root = None
        self.provinces: Dict[str, SVGProvince] = {}
        self.ns = {"svg": "http://www.w3.org/2000/svg"}

    def parse(self) -> bool:
        """
        Parse the SVG file and extract provinces.
        
        Returns:
            bool: True if parsing succeeded, False otherwise
        """
        try:
            self.tree = ET.parse(self.svg_path)
            self.root = self.tree.getroot()
            self._extract_provinces()
            logger.info(f"Parsed {len(self.provinces)} provinces from {self.svg_path.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to parse SVG file: {e}")
            return False

    def _extract_provinces(self):
        """Extract all province elements from SVG."""
        # Try multiple common SVG element patterns
        for element in self.root.iter():
            if element.tag.endswith("path"):
                self._process_path_element(element)
            elif element.tag.endswith("polygon"):
                self._process_polygon_element(element)
            elif element.tag.endswith("rect"):
                self._process_rect_element(element)

    def _process_path_element(self, elem):
        """Process SVG path element."""
        prov_id = elem.get("id", "")
        fill_color = elem.get("fill", "").lower()
        path_data = elem.get("d", "")
        label = elem.get("title") or elem.get("label")

        if not fill_color or not prov_id:
            return

        prov_type = self._classify_province_type(fill_color)
        rgb_color = self._hex_to_rgb(fill_color)

        self.provinces[prov_id] = SVGProvince(
            id=prov_id,
            province_type=prov_type,
            fill_color=fill_color,
            rgb_color=rgb_color,
            path_data=path_data,
            label=label,
        )

    def _process_polygon_element(self, elem):
        """Process SVG polygon element."""
        prov_id = elem.get("id", "")
        fill_color = elem.get("fill", "").lower()
        points = elem.get("points", "")
        label = elem.get("title") or elem.get("label")

        if not fill_color or not prov_id:
            return

        prov_type = self._classify_province_type(fill_color)
        rgb_color = self._hex_to_rgb(fill_color)

        self.provinces[prov_id] = SVGProvince(
            id=prov_id,
            province_type=prov_type,
            fill_color=fill_color,
            rgb_color=rgb_color,
            path_data=points,
            label=label,
        )

    def _process_rect_element(self, elem):
        """Process SVG rectangle element."""
        prov_id = elem.get("id", "")
        fill_color = elem.get("fill", "").lower()
        
        if not fill_color or not prov_id:
            return

        prov_type = self._classify_province_type(fill_color)
        rgb_color = self._hex_to_rgb(fill_color)

        x = elem.get("x", "0")
        y = elem.get("y", "0")
        width = elem.get("width", "0")
        height = elem.get("height", "0")

        self.provinces[prov_id] = SVGProvince(
            id=prov_id,
            province_type=prov_type,
            fill_color=fill_color,
            rgb_color=rgb_color,
            path_data=f"M{x},{y}h{width}v{height}h-{width}Z",
        )

    def _classify_province_type(self, fill_color: str) -> str:
        """
        Classify province type based on fill color.
        
        Args:
            fill_color: Fill color string (hex or named)
            
        Returns:
            str: Province type ('land', 'sea', 'lake', 'coastal', 'wasteland')
        """
        fill_color = fill_color.lower().strip()

        # Direct match in lookup table
        if fill_color in self.PROVINCE_TYPE_COLORS:
            return self.PROVINCE_TYPE_COLORS[fill_color]

        # Try RGB distance matching
        rgb = self._hex_to_rgb(fill_color)
        if rgb:
            return self._classify_by_rgb_distance(rgb)

        # Default fallback
        return "land"

    def _hex_to_rgb(self, hex_color: str) -> Optional[Tuple[int, int, int]]:
        """
        Convert hex color to RGB tuple.
        
        Args:
            hex_color: Color string (#RRGGBB or named color)
            
        Returns:
            RGB tuple or None if conversion fails
        """
        hex_color = hex_color.strip()

        if hex_color.startswith("#"):
            try:
                hex_color = hex_color.lstrip("#")
                if len(hex_color) == 6:
                    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
            except ValueError:
                pass

        # Try CSS color names
        css_colors = {
            "black": (0, 0, 0),
            "white": (255, 255, 255),
            "red": (255, 0, 0),
            "green": (0, 128, 0),
            "blue": (0, 0, 255),
            "gray": (128, 128, 128),
            "lightblue": (173, 216, 230),
            "navy": (0, 0, 128),
        }
        return css_colors.get(hex_color.lower())

    def _classify_by_rgb_distance(self, rgb: Tuple[int, int, int]) -> str:
        """
        Classify province type by RGB distance to known colors.
        
        Args:
            rgb: RGB color tuple
            
        Returns:
            str: Province type
        """
        reference_colors = {
            "sea": [(0, 40, 80), (0, 85, 170), (0, 52, 163)],
            "lake": [(135, 206, 235), (0, 191, 255), (173, 216, 230)],
            "land": [(90, 150, 66), (109, 184, 76), (126, 200, 80)],
            "wasteland": [(26, 26, 26), (51, 51, 51), (85, 85, 85)],
        }

        min_distance = float("inf")
        best_type = "land"

        for prov_type, colors in reference_colors.items():
            for ref_color in colors:
                distance = sum((a - b) ** 2 for a, b in zip(rgb, ref_color)) ** 0.5
                if distance < min_distance:
                    min_distance = distance
                    best_type = prov_type

        return best_type

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about parsed provinces.
        
        Returns:
            dict: Statistics including counts by type
        """
        stats = {
            "total_provinces": len(self.provinces),
            "by_type": {},
        }

        for prov in self.provinces.values():
            prov_type = prov.province_type
            if prov_type not in stats["by_type"]:
                stats["by_type"][prov_type] = 0
            stats["by_type"][prov_type] += 1

        return stats

    def generate_reference_bmp(
        self,
        width: int,
        height: int,
        output_path: Optional[Path] = None,
    ) -> np.ndarray:
        """
        Generate a reference BMP image from SVG provinces.
        
        Args:
            width: Output image width
            height: Output image height
            output_path: Optional path to save the reference BMP
            
        Returns:
            numpy array of the generated image
        """
        # Create blank image with white background
        img = Image.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Draw each province with its color
        for prov in self.provinces.values():
            # For now, use a simple approach: color rectangles
            # In a full implementation, parse and draw actual paths
            draw.rectangle(
                [(0, 0), (width, height)],
                fill=prov.rgb_color,
                outline=prov.rgb_color,
            )

        # Convert to numpy array
        bmp_array = np.array(img)

        if output_path:
            img.save(output_path)
            logger.info(f"Saved reference BMP to {output_path}")

        return bmp_array


class SVGToProvinceBMPConverter:
    """
    Converts SVG reference map to province BMP for comparison.
    """

    def __init__(self, svg_path: Path):
        """
        Initialize converter.
        
        Args:
            svg_path: Path to SVG file
        """
        self.parser = SVGReferenceParser(svg_path)
        self.reference_bmp = None

    def load_and_generate(self, width: int, height: int) -> Optional[np.ndarray]:
        """
        Load SVG and generate reference BMP.
        
        Args:
            width: Output width
            height: Output height
            
        Returns:
            numpy array of reference BMP or None if failed
        """
        if not self.parser.parse():
            return None

        self.reference_bmp = self.parser.generate_reference_bmp(width, height)
        return self.reference_bmp

    def validate_generated_map(
        self,
        generated_bmp: np.ndarray,
        output_comparison_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Compare generated province BMP with SVG reference.
        
        Args:
            generated_bmp: Generated province map as numpy array
            output_comparison_path: Optional path to save comparison image
            
        Returns:
            dict: Validation metrics
        """
        if self.reference_bmp is None:
            logger.warning("No reference BMP loaded. Call load_and_generate() first.")
            return {}

        # Ensure same dimensions
        if generated_bmp.shape != self.reference_bmp.shape:
            logger.warning(
                f"Shape mismatch: generated {generated_bmp.shape} vs "
                f"reference {self.reference_bmp.shape}"
            )

        # Compute basic statistics
        land_ratio_gen = self._compute_land_ratio(generated_bmp)
        sea_ratio_gen = self._compute_sea_ratio(generated_bmp)

        land_ratio_ref = self._compute_land_ratio(self.reference_bmp)
        sea_ratio_ref = self._compute_sea_ratio(self.reference_bmp)

        metrics = {
            "land_ratio_generated": land_ratio_gen,
            "sea_ratio_generated": sea_ratio_gen,
            "land_ratio_reference": land_ratio_ref,
            "sea_ratio_reference": sea_ratio_ref,
            "land_ratio_diff": abs(land_ratio_gen - land_ratio_ref),
            "sea_ratio_diff": abs(sea_ratio_gen - sea_ratio_ref),
        }

        if output_comparison_path:
            self._save_comparison_image(
                generated_bmp, self.reference_bmp, output_comparison_path
            )

        return metrics

    def _compute_land_ratio(self, bmp: np.ndarray) -> float:
        """Estimate land ratio by counting non-blue pixels."""
        if len(bmp.shape) == 3:
            # RGB image: land is when blue channel is low
            blue = bmp[:, :, 2]
            land_mask = blue < 100
        else:
            land_mask = bmp > 100

        return land_mask.sum() / land_mask.size if land_mask.size > 0 else 0.0

    def _compute_sea_ratio(self, bmp: np.ndarray) -> float:
        """Estimate sea ratio by counting blue pixels."""
        if len(bmp.shape) == 3:
            blue = bmp[:, :, 2]
            sea_mask = blue >= 100
        else:
            sea_mask = bmp <= 100

        return sea_mask.sum() / sea_mask.size if sea_mask.size > 0 else 0.0

    def _save_comparison_image(
        self, generated: np.ndarray, reference: np.ndarray, output_path: Path
    ):
        """Save side-by-side comparison image."""
        try:
            gen_img = Image.fromarray(generated.astype(np.uint8))
            ref_img = Image.fromarray(reference.astype(np.uint8))

            # Create side-by-side image
            width = gen_img.width + ref_img.width + 10
            height = max(gen_img.height, ref_img.height)
            comparison = Image.new("RGB", (width, height), color=(255, 255, 255))

            comparison.paste(gen_img, (0, 0))
            comparison.paste(ref_img, (gen_img.width + 10, 0))

            comparison.save(output_path)
            logger.info(f"Saved comparison image to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save comparison image: {e}")
