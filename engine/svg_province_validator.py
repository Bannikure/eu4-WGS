"""
SVG Province Validator Module
=============================
Integrates SVG reference maps with the province generation pipeline.
Provides validation, comparison, and guidance for province BMP generation.
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import logging
from dataclasses import dataclass
from PIL import Image

from .svg_reference_parser import SVGReferenceParser, SVGToProvinceBMPConverter
from .map_generation import ProvinceInfo

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    """Report from province map validation against SVG reference."""
    
    is_valid: bool
    overall_similarity: float
    land_ratio_match: bool
    sea_ratio_match: bool
    land_ratio_diff: float
    sea_ratio_diff: float
    province_type_distribution: Dict[str, int]
    recommendations: List[str]
    metrics: Dict[str, float]


class SVGProvinceValidator:
    """
    Validates generated province maps against SVG reference.
    Uses SVG files as visual specification for province type distribution.
    """

    # Acceptable deviation thresholds
    LAND_RATIO_TOLERANCE = 0.10  # ±10% land/sea ratio difference
    SEA_RATIO_TOLERANCE = 0.10

    def __init__(self, svg_path: Optional[Path] = None):
        """
        Initialize validator.
        
        Args:
            svg_path: Path to SVG reference file (optional)
        """
        self.svg_path = svg_path
        self.parser: Optional[SVGReferenceParser] = None
        self.reference_bmp: Optional[np.ndarray] = None
        self.svg_stats: Dict[str, Any] = {}
        
        if svg_path:
            self._load_svg_reference(svg_path)

    def _load_svg_reference(self, svg_path: Path) -> bool:
        """
        Load and parse SVG reference file.
        
        Args:
            svg_path: Path to SVG file
            
        Returns:
            bool: True if loaded successfully
        """
        try:
            self.parser = SVGReferenceParser(svg_path)
            if self.parser.parse():
                self.svg_stats = self.parser.get_statistics()
                logger.info(
                    f"Loaded SVG reference: {self.svg_stats['total_provinces']} provinces"
                )
                return True
        except Exception as e:
            logger.error(f"Failed to load SVG reference: {e}")
        
        return False

    def generate_reference_bmp(self, width: int, height: int) -> Optional[np.ndarray]:
        """
        Generate reference BMP from SVG.
        
        Args:
            width: Output width
            height: Output height
            
        Returns:
            numpy array of reference BMP or None if no SVG loaded
        """
        if self.parser is None:
            logger.warning("No SVG parser initialized")
            return None

        self.reference_bmp = self.parser.generate_reference_bmp(width, height)
        return self.reference_bmp

    def validate_province_map(
        self,
        generated_bmp: np.ndarray,
        province_infos: List[ProvinceInfo],
        width: int = 5632,
        height: int = 2048,
    ) -> ValidationReport:
        """
        Validate generated province map against SVG reference.
        
        Args:
            generated_bmp: Generated province map (RGB numpy array)
            province_infos: List of ProvinceInfo objects from generation
            width: Map width
            height: Map height
            
        Returns:
            ValidationReport with detailed validation results
        """
        metrics = {}
        recommendations = []

        # Compute province type distribution from generated map
        gen_distribution = self._analyze_province_distribution(
            generated_bmp, province_infos
        )

        # Compute land/sea ratios
        gen_land_ratio = self._compute_land_ratio(generated_bmp)
        gen_sea_ratio = self._compute_sea_ratio(generated_bmp)

        metrics["land_ratio_generated"] = gen_land_ratio
        metrics["sea_ratio_generated"] = gen_sea_ratio

        # Compare with reference if available
        land_ratio_match = True
        sea_ratio_match = True
        land_ratio_diff = 0.0
        sea_ratio_diff = 0.0

        if self.reference_bmp is not None:
            ref_land_ratio = self._compute_land_ratio(self.reference_bmp)
            ref_sea_ratio = self._compute_sea_ratio(self.reference_bmp)

            metrics["land_ratio_reference"] = ref_land_ratio
            metrics["sea_ratio_reference"] = ref_sea_ratio

            land_ratio_diff = abs(gen_land_ratio - ref_land_ratio)
            sea_ratio_diff = abs(gen_sea_ratio - ref_sea_ratio)

            land_ratio_match = land_ratio_diff <= self.LAND_RATIO_TOLERANCE
            sea_ratio_match = sea_ratio_diff <= self.SEA_RATIO_TOLERANCE

            metrics["land_ratio_diff"] = land_ratio_diff
            metrics["sea_ratio_diff"] = sea_ratio_diff

            # Generate recommendations
            if not land_ratio_match:
                diff_pct = land_ratio_diff * 100
                if gen_land_ratio > ref_land_ratio:
                    recommendations.append(
                        f"Generated map has {diff_pct:.1f}% more land than reference. "
                        "Consider lowering sea_level_threshold or reducing land_percentage."
                    )
                else:
                    recommendations.append(
                        f"Generated map has {diff_pct:.1f}% less land than reference. "
                        "Consider raising sea_level_threshold or increasing land_percentage."
                    )

            if not sea_ratio_match:
                diff_pct = sea_ratio_diff * 100
                recommendations.append(
                    f"Sea ratio differs by {diff_pct:.1f}% from reference. "
                    "Adjust heightmap generation parameters for better balance."
                )
        else:
            logger.info("No reference BMP for comparison (SVG reference not loaded)")

        # Analyze province type distribution
        type_distribution = self._get_type_distribution(province_infos)
        
        # Compute overall similarity
        overall_similarity = self._compute_overall_similarity(
            gen_land_ratio,
            gen_sea_ratio,
            land_ratio_match,
            sea_ratio_match,
            type_distribution,
        )

        is_valid = (
            land_ratio_match
            and sea_ratio_match
            and self._validate_province_types(province_infos, recommendations)
        )

        # Add general recommendations
        if gen_distribution.get("lake", 0) == 0:
            recommendations.append(
                "No lakes detected in generated map. Consider adding lake detection logic."
            )

        if gen_distribution.get("island", 0) < 5:
            recommendations.append(
                "Few islands detected. Map may lack archipelago features. "
                "Consider adjusting land clustering."
            )

        return ValidationReport(
            is_valid=is_valid,
            overall_similarity=overall_similarity,
            land_ratio_match=land_ratio_match,
            sea_ratio_match=sea_ratio_match,
            land_ratio_diff=land_ratio_diff,
            sea_ratio_diff=sea_ratio_diff,
            province_type_distribution=gen_distribution,
            recommendations=recommendations,
            metrics=metrics,
        )

    def _analyze_province_distribution(
        self,
        bmp: np.ndarray,
        province_infos: List[ProvinceInfo],
    ) -> Dict[str, int]:
        """
        Analyze distribution of province types in generated map.
        
        Args:
            bmp: Province map (RGB array)
            province_infos: List of ProvinceInfo
            
        Returns:
            dict: Count of each province type
        """
        distribution = {
            "land": 0,
            "sea": 0,
            "lake": 0,
            "island": 0,
            "wasteland": 0,
        }

        for prov in province_infos:
            if prov.is_sea:
                distribution["sea"] += 1
            elif prov.is_wasteland:
                distribution["wasteland"] += 1
            elif prov.is_island:
                distribution["island"] += 1
            else:
                distribution["land"] += 1

        return distribution

    def _get_type_distribution(
        self, province_infos: List[ProvinceInfo]
    ) -> Dict[str, int]:
        """Get province type distribution."""
        return self._analyze_province_distribution(None, province_infos)

    def _validate_province_types(
        self,
        province_infos: List[ProvinceInfo],
        recommendations: List[str],
    ) -> bool:
        """
        Validate that province types are reasonable.
        
        Args:
            province_infos: List of ProvinceInfo
            recommendations: List to append recommendations to
            
        Returns:
            bool: True if types are valid
        """
        land_count = sum(1 for p in province_infos if not p.is_sea and not p.is_wasteland)
        sea_count = sum(1 for p in province_infos if p.is_sea)
        wasteland_count = sum(1 for p in province_infos if p.is_wasteland)

        total = len(province_infos)

        if total == 0:
            recommendations.append("No provinces generated!")
            return False

        land_pct = (land_count / total) * 100
        sea_pct = (sea_count / total) * 100

        # Land should be between 15-60%
        if land_pct < 15:
            recommendations.append(
                f"Only {land_pct:.1f}% land provinces. Map may be too oceanic."
            )
            return False
        elif land_pct > 60:
            recommendations.append(
                f"Land comprises {land_pct:.1f}% of provinces. Map may be too continental."
            )

        return True

    def _compute_land_ratio(self, bmp: np.ndarray) -> float:
        """Estimate land ratio from BMP."""
        if len(bmp.shape) != 3 or bmp.shape[2] != 3:
            return 0.0

        # Land: blue channel < 100 (sea is deep blue [0, 40, 80])
        blue_channel = bmp[:, :, 2]
        land_mask = blue_channel < 100
        return land_mask.sum() / land_mask.size if land_mask.size > 0 else 0.0

    def _compute_sea_ratio(self, bmp: np.ndarray) -> float:
        """Estimate sea ratio from BMP."""
        return 1.0 - self._compute_land_ratio(bmp)

    def _compute_overall_similarity(
        self,
        land_ratio: float,
        sea_ratio: float,
        land_match: bool,
        sea_match: bool,
        type_distribution: Dict[str, int],
    ) -> float:
        """
        Compute overall similarity score (0.0 to 1.0).
        
        Args:
            land_ratio: Generated land ratio
            sea_ratio: Generated sea ratio
            land_match: Whether land ratio matches reference
            sea_match: Whether sea ratio matches reference
            type_distribution: Province type distribution
            
        Returns:
            float: Similarity score
        """
        score = 0.0

        # Match scores
        if land_match:
            score += 0.25
        if sea_match:
            score += 0.25

        # Distribution scores
        total_provinces = sum(type_distribution.values())
        if total_provinces > 0:
            land_pct = type_distribution.get("land", 0) / total_provinces
            sea_pct = type_distribution.get("sea", 0) / total_provinces

            # Reward balanced distribution
            if 0.25 <= land_pct <= 0.55:
                score += 0.25
            if 0.35 <= sea_pct <= 0.65:
                score += 0.25

        return min(1.0, score)

    def generate_validation_report_text(self, report: ValidationReport) -> str:
        """
        Generate human-readable validation report.
        
        Args:
            report: ValidationReport object
            
        Returns:
            str: Formatted report text
        """
        lines = [
            "=" * 70,
            "PROVINCE MAP VALIDATION REPORT",
            "=" * 70,
            "",
            f"Overall Validity: {'✓ VALID' if report.is_valid else '✗ INVALID'}",
            f"Overall Similarity: {report.overall_similarity * 100:.1f}%",
            "",
            "LAND/SEA RATIOS:",
            f"  Land Ratio Match: {'✓' if report.land_ratio_match else '✗'} "
            f"(diff: {report.land_ratio_diff * 100:.2f}%)",
            f"  Sea Ratio Match:  {'✓' if report.sea_ratio_match else '✗'} "
            f"(diff: {report.sea_ratio_diff * 100:.2f}%)",
            "",
            "PROVINCE TYPE DISTRIBUTION:",
        ]

        for ptype, count in report.province_type_distribution.items():
            lines.append(f"  {ptype.capitalize():12s}: {count:4d} provinces")

        lines.extend(
            [
                "",
                "METRICS:",
            ]
        )

        for key, value in report.metrics.items():
            if isinstance(value, float):
                lines.append(f"  {key}: {value:.4f}")
            else:
                lines.append(f"  {key}: {value}")

        if report.recommendations:
            lines.extend(
                [
                    "",
                    "RECOMMENDATIONS:",
                ]
            )
            for i, rec in enumerate(report.recommendations, 1):
                lines.append(f"  {i}. {rec}")

        lines.append("=" * 70)

        return "\n".join(lines)

    def save_validation_report(
        self, report: ValidationReport, output_path: Path
    ) -> bool:
        """
        Save validation report to file.
        
        Args:
            report: ValidationReport object
            output_path: Path to save report
            
        Returns:
            bool: True if saved successfully
        """
        try:
            report_text = self.generate_validation_report_text(report)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report_text)
            logger.info(f"Saved validation report to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save validation report: {e}")
            return False


class ProvinceGenerationWithSVGReference:
    """
    Enhanced province generator that uses SVG reference for validation.
    Wraps the standard ProvinceGenerator with SVG guidance.
    """

    def __init__(
        self,
        width: int = 5632,
        height: int = 2048,
        svg_reference_path: Optional[Path] = None,
    ):
        """
        Initialize with optional SVG reference.
        
        Args:
            width: Map width
            height: Map height
            svg_reference_path: Path to SVG reference file
        """
        self.width = width
        self.height = height
        self.validator = SVGProvinceValidator(svg_reference_path)

    def validate_generated_map(
        self,
        provinces_bmp: np.ndarray,
        province_infos: List[ProvinceInfo],
    ) -> ValidationReport:
        """
        Validate generated province map.
        
        Args:
            provinces_bmp: Generated province bitmap
            province_infos: Province information list
            
        Returns:
            ValidationReport
        """
        return self.validator.validate_province_map(
            provinces_bmp,
            province_infos,
            self.width,
            self.height,
        )

    def print_validation_report(self, report: ValidationReport):
        """Print validation report to console."""
        print(self.validator.generate_validation_report_text(report))
