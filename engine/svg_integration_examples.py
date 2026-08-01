"""
SVG Reference Integration Example
==================================
Demonstrates how to use the SVG reference parser and validator
with the province map generation pipeline.
"""

import logging
from pathlib import Path
import numpy as np
from PIL import Image

from engine.svg_reference_parser import SVGReferenceParser, SVGToProvinceBMPConverter
from engine.svg_province_validator import SVGProvinceValidator, ProvinceGenerationWithSVGReference

logger = logging.getLogger(__name__)


def example_load_svg_reference(svg_path: Path) -> dict:
    """
    Example: Load and analyze an SVG reference map.
    
    Args:
        svg_path: Path to SVG file from eu4-svg-map
        
    Returns:
        Dictionary with parsed province information
    """
    logger.info(f"Loading SVG reference: {svg_path}")
    
    parser = SVGReferenceParser(svg_path)
    if not parser.parse():
        logger.error("Failed to parse SVG file")
        return {}
    
    stats = parser.get_statistics()
    logger.info(f"Parsed {stats['total_provinces']} provinces")
    logger.info(f"Province type breakdown: {stats['by_type']}")
    
    return {
        "parser": parser,
        "statistics": stats,
        "provinces": parser.provinces,
    }


def example_generate_reference_bmp(
    svg_path: Path,
    output_bmp_path: Path,
    width: int = 5632,
    height: int = 2048,
) -> np.ndarray:
    """
    Example: Generate a reference BMP from SVG.
    
    Args:
        svg_path: Path to SVG file
        output_bmp_path: Where to save the reference BMP
        width: Output width
        height: Output height
        
    Returns:
        Reference BMP as numpy array
    """
    logger.info(f"Generating reference BMP from {svg_path}")
    
    parser = SVGReferenceParser(svg_path)
    if not parser.parse():
        logger.error("Failed to parse SVG")
        return None
    
    ref_bmp = parser.generate_reference_bmp(width, height, output_bmp_path)
    logger.info(f"Reference BMP generated: {output_bmp_path}")
    
    return ref_bmp


def example_validate_generated_map(
    svg_reference_path: Path,
    generated_province_bmp: np.ndarray,
    province_infos: list,
    width: int = 5632,
    height: int = 2048,
) -> dict:
    """
    Example: Validate a generated province map against SVG reference.
    
    Args:
        svg_reference_path: Path to SVG reference file
        generated_province_bmp: Generated province BMP (RGB numpy array)
        province_infos: List of ProvinceInfo objects from generation
        width: Map width
        height: Map height
        
    Returns:
        Validation report with metrics and recommendations
    """
    logger.info("Validating generated map against SVG reference...")
    
    # Initialize validator with SVG reference
    validator = SVGProvinceValidator(svg_reference_path)
    
    # Generate reference BMP for comparison
    ref_bmp = validator.generate_reference_bmp(width, height)
    
    # Validate the generated map
    report = validator.validate_province_map(
        generated_province_bmp,
        province_infos,
        width,
        height,
    )
    
    # Print report
    print(validator.generate_validation_report_text(report))
    
    # Save report to file
    output_dir = Path("validation_reports")
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / f"validation_report_{Path(svg_reference_path).stem}.txt"
    validator.save_validation_report(report, report_path)
    
    return {
        "report": report,
        "is_valid": report.is_valid,
        "similarity": report.overall_similarity,
        "recommendations": report.recommendations,
    }


def example_integrated_workflow(
    svg_reference_path: Path,
    heightmap: np.ndarray,
    province_map: np.ndarray,
    province_infos: list,
    output_dir: Path = Path("./output"),
) -> dict:
    """
    Example: Complete workflow integrating SVG validation with generation.
    
    This is how you'd use the SVG validator in your main generation pipeline:
    
    Args:
        svg_reference_path: Path to SVG reference file
        heightmap: Generated heightmap
        province_map: Generated province map (RGB BMP)
        province_infos: List of ProvinceInfo objects
        output_dir: Output directory for results
        
    Returns:
        Dictionary with generation and validation results
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    width = province_map.shape[1]
    height = province_map.shape[0]
    
    logger.info("=" * 70)
    logger.info("INTEGRATED SVG VALIDATION WORKFLOW")
    logger.info("=" * 70)
    
    # Step 1: Load and analyze SVG reference
    logger.info("\n[1/4] Loading SVG reference...")
    svg_data = example_load_svg_reference(svg_reference_path)
    
    # Step 2: Generate reference BMP
    logger.info("\n[2/4] Generating reference BMP...")
    ref_bmp_path = output_dir / "reference_bmp.png"
    ref_bmp = example_generate_reference_bmp(
        svg_reference_path,
        ref_bmp_path,
        width,
        height,
    )
    
    # Step 3: Validate generated map
    logger.info("\n[3/4] Validating generated map...")
    validation = example_validate_generated_map(
        svg_reference_path,
        province_map,
        province_infos,
        width,
        height,
    )
    
    # Step 4: Generate comparison visualization
    logger.info("\n[4/4] Generating comparison images...")
    if ref_bmp is not None:
        # Save comparison
        comparison_path = output_dir / "comparison.png"
        try:
            gen_img = Image.fromarray(province_map.astype(np.uint8))
            ref_img = Image.fromarray(ref_bmp.astype(np.uint8))
            
            # Create side-by-side
            width_combined = gen_img.width + ref_img.width + 20
            height_max = max(gen_img.height, ref_img.height)
            comparison = Image.new("RGB", (width_combined, height_max), (255, 255, 255))
            
            comparison.paste(gen_img, (0, 0))
            comparison.paste(ref_img, (gen_img.width + 20, 0))
            
            comparison.save(comparison_path)
            logger.info(f"Comparison image saved: {comparison_path}")
        except Exception as e:
            logger.warning(f"Could not create comparison image: {e}")
    
    logger.info("\n" + "=" * 70)
    logger.info("VALIDATION COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Overall Similarity: {validation['similarity'] * 100:.1f}%")
    logger.info(f"Validity: {'✓ VALID' if validation['is_valid'] else '✗ INVALID'}")
    
    if validation['recommendations']:
        logger.info("\nRecommendations:")
        for i, rec in enumerate(validation['recommendations'], 1):
            logger.info(f"  {i}. {rec}")
    
    return {
        "svg_data": svg_data,
        "reference_bmp": ref_bmp,
        "validation": validation,
        "report": validation["report"],
    }


def quick_validate_provinces(
    generated_bmp: np.ndarray,
    province_infos: list,
    svg_reference_path: Path = None,
) -> bool:
    """
    Quick validation function - drop-in for your generation pipeline.
    
    Usage in your main generation code:
    ```python
    # After generating provinces
    is_valid = quick_validate_provinces(province_map, province_list, svg_ref_path)
    if not is_valid:
        logger.warning("Generated map doesn't match reference - adjusting...")
    ```
    
    Args:
        generated_bmp: Generated province BMP
        province_infos: List of province info objects
        svg_reference_path: Path to SVG reference file
        
    Returns:
        bool: True if validation passes, False otherwise
    """
    if svg_reference_path is None:
        logger.warning("No SVG reference provided - skipping validation")
        return True
    
    validator = SVGProvinceValidator(svg_reference_path)
    report = validator.validate_province_map(
        generated_bmp,
        province_infos,
        generated_bmp.shape[1],
        generated_bmp.shape[0],
    )
    
    return report.is_valid


# ═══════════════════════════════════════════════════════════════
#  USAGE EXAMPLES
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="[%(name)s] %(levelname)s: %(message)s"
    )
    
    # Example 1: Load and analyze SVG
    print("\n" + "="*70)
    print("EXAMPLE 1: Load and analyze SVG reference")
    print("="*70)
    
    svg_path = Path("additional_data/your_map.svg")  # Replace with actual path
    if svg_path.exists():
        data = example_load_svg_reference(svg_path)
        print(f"✓ Loaded {data['statistics']['total_provinces']} provinces")
    else:
        print(f"⚠ SVG file not found: {svg_path}")
    
    # Example 2: Generate reference BMP
    print("\n" + "="*70)
    print("EXAMPLE 2: Generate reference BMP from SVG")
    print("="*70)
    
    if svg_path.exists():
        ref_bmp = example_generate_reference_bmp(
            svg_path,
            Path("output/reference_map.png"),
            5632, 2048
        )
        if ref_bmp is not None:
            print(f"✓ Reference BMP generated: shape {ref_bmp.shape}")
    
    # Example 3: Full integrated workflow
    print("\n" + "="*70)
    print("EXAMPLE 3: Full integrated validation workflow")
    print("="*70)
    print("(Requires actual heightmap and province data)")
    
    print("\nTo use in your generation pipeline:")
    print("""
    from engine.svg_province_validator import SVGProvinceValidator
    
    # After generation:
    validator = SVGProvinceValidator("path/to/reference.svg")
    report = validator.validate_province_map(
        province_map_bmp,
        province_infos,
        width, height
    )
    
    if not report.is_valid:
        print("Validation issues:")
        for rec in report.recommendations:
            print(f"  - {rec}")
    """)
