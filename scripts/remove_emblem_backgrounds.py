#!/usr/bin/env python3
"""
Batch Emblem Background Remover
================================
Processes all emblem PNGs in the assets/emblems/ directory to make
backgrounds transparent, handling:
  - White/near-white backgrounds (most common - 154 files)
  - Solid color backgrounds (14 files)
  - Checkered/transparency-grid backgrounds (2 files)
  - Corrupted/invalid PNG files (7 files)
  - Already-transparent files (30 files - skipped)

Algorithm:
  1. Detect the dominant background color from edge pixels
  2. For each pixel, calculate color distance from background
  3. Apply smooth alpha gradient at the emblem boundary (anti-aliasing)
  4. Save as proper RGBA PNG with transparency
"""

import os
import sys
import numpy as np
from PIL import Image
from pathlib import Path


def get_dominant_edge_color(arr: np.ndarray) -> np.ndarray:
    """Get the most common color from the edge pixels of an image."""
    h, w = arr.shape[:2]
    
    # Collect all edge pixels (top/bottom rows, left/right columns)
    edge_pixels = np.vstack([
        arr[0, :, :3],      # top row
        arr[-1, :, :3],     # bottom row
        arr[:, 0, :3],      # left column
        arr[:, -1, :3],     # right column
    ])
    
    # Find the most common color using binning (quantize to 8-bit groups of 8)
    quantized = (edge_pixels // 8) * 8
    unique_colors, counts = np.unique(quantized, axis=0, return_counts=True)
    dominant_idx = np.argmax(counts)
    dominant = unique_colors[dominant_idx]
    
    # Refine: average the original pixels that match this quantized group
    mask = np.all(np.abs(edge_pixels.astype(int) - dominant.astype(int)) <= 8, axis=1)
    refined = edge_pixels[mask].mean(axis=0)
    
    return refined.astype(np.uint8)


def detect_background_type(arr: np.ndarray) -> str:
    """Detect the type of background in the image."""
    h, w = arr.shape[:2]
    
    # Check corner alpha values
    corner_coords = [(0, 0), (w-1, 0), (0, h-1), (w-1, h-1)]
    corner_alphas = [arr[y, x, 3] for x, y in corner_coords]
    avg_corner_alpha = np.mean(corner_alphas)
    
    # Already has transparency at corners - likely already transparent
    if avg_corner_alpha < 30:
        return "transparent"
    
    # Get edge alpha statistics
    edge_alphas = np.concatenate([
        arr[0, :, 3], arr[-1, :, 3],
        arr[:, 0, 3], arr[:, -1, 3],
    ])
    alpha_variance = np.var(edge_alphas.astype(float))
    
    # High variance in edge alphas = checkered pattern
    if alpha_variance > 3000:
        return "checkered"
    
    # Get dominant edge color
    dominant = get_dominant_edge_color(arr)
    brightness = dominant.mean()
    
    if brightness > 230:
        return "white"
    elif brightness > 160:
        return "light_color"
    elif brightness > 80:
        return "medium_color"
    else:
        return "dark_color"


def remove_background_smart(img: Image.Image, tolerance: int = 40,
                            softness: float = 15.0) -> Image.Image:
    """
    Intelligently remove background from an emblem image.
    
    Args:
        img: PIL Image (will be converted to RGBA)
        tolerance: How different a pixel must be from the background to be kept (0-255)
        softness: Width of the alpha gradient at the boundary (anti-aliasing)
    
    Returns:
        RGBA PIL Image with transparent background
    """
    img_rgba = img.convert("RGBA")
    arr = np.array(img_rgba, dtype=np.float64)
    h, w = arr.shape[:2]
    
    bg_type = detect_background_type(arr)
    
    if bg_type == "transparent":
        # Already transparent - return as-is
        return img_rgba
    
    # Get the dominant background color
    bg_color = get_dominant_edge_color(arr).astype(np.float64)
    
    # Calculate per-pixel color distance from background
    diff = np.sqrt(
        (arr[:, :, 0] - bg_color[0]) ** 2 +
        (arr[:, :, 1] - bg_color[1]) ** 2 +
        (arr[:, :, 2] - bg_color[2]) ** 2
    )
    
    # For checkered backgrounds, also use alpha channel information
    if bg_type == "checkered":
        # Checkered pattern has alternating alpha - use existing alpha as a guide
        existing_alpha = arr[:, :, 3].copy()
        
        # The checkered pixels (low alpha) should be fully transparent
        # Solid pixels need the background removal treatment
        checker_mask = existing_alpha < 128
        
        # For non-checker pixels, still apply color distance
        alpha_new = np.zeros((h, w), dtype=np.float64)
        
        # Checker pixels → transparent
        alpha_new[checker_mask] = 0.0
        
        # Non-checker pixels → use color distance
        non_checker_diff = diff.copy()
        non_checker_diff[checker_mask] = 999  # Already handled
        
        # Smooth alpha for non-checker area
        alpha_new[~checker_mask] = np.clip(
            (non_checker_diff[~checker_mask] - tolerance + softness) / softness * 255,
            0, 255
        )
        
    else:
        # Standard background removal using color distance
        # alpha = smooth step from 0 (at bg) to 255 (far from bg)
        alpha_new = np.clip(
            (diff - tolerance + softness) / softness * 255,
            0, 255
        )
        
        # For very white/near-white pixels that are NOT part of the emblem,
        # force them transparent. Use a flood-fill from edges approach:
        # Start from edges, any pixel within tolerance of bg AND connected to edge = bg
        is_bg_like = diff < tolerance
        
        # Simple iterative flood fill from edges
        visited = np.zeros((h, w), dtype=bool)
        queue = []
        
        # Seed from all edge pixels that look like background
        for x in range(w):
            if is_bg_like[0, x]:
                queue.append((0, x))
                visited[0, x] = True
            if is_bg_like[h-1, x]:
                queue.append((h-1, x))
                visited[h-1, x] = True
        for y in range(h):
            if is_bg_like[y, 0]:
                queue.append((y, 0))
                visited[y, 0] = True
            if is_bg_like[y, w-1]:
                queue.append((y, w-1))
                visited[y, w-1] = True
        
        # BFS flood fill - limited iterations for performance
        max_iters = min(h * w, 500000)
        head = 0
        while head < len(queue) and head < max_iters:
            cy, cx = queue[head]
            head += 1
            
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_bg_like[ny, nx]:
                    visited[ny, nx] = True
                    queue.append((ny, nx))
        
        # All visited (connected-to-edge bg) pixels get alpha = 0
        alpha_new[visited] = 0
        
        # Interior bg-like pixels (enclosed by emblem) get soft alpha
        # to preserve anti-aliased edges
        interior_bg = is_bg_like & ~visited
        if interior_bg.any():
            # These are white pixels surrounded by emblem - likely highlights
            # Give them partial transparency based on distance
            alpha_new[interior_bg] = np.clip(
                (diff[interior_bg] / tolerance) * 200,
                0, 200
            )
    
    # Preserve the original alpha where it's already providing good transparency
    original_alpha = arr[:, :, 3]
    # Blend: use the better of original alpha or new alpha
    # If original alpha is low (transparent), keep it
    # If new alpha is lower (more transparent), use it
    final_alpha = np.minimum(alpha_new, original_alpha)
    
    # Build output image
    result = arr.copy()
    result[:, :, 3] = final_alpha
    
    return Image.fromarray(result.astype(np.uint8), mode="RGBA")


def process_emblems_directory(emblems_dir: str, output_dir: str = None,
                              tolerance: int = 40, dry_run: bool = False):
    """
    Process all emblem PNGs in a directory to remove backgrounds.
    
    Args:
        emblems_dir: Path to the emblems directory
        output_dir: If set, save processed files here instead of overwriting
        tolerance: Background color tolerance (0-255)
        dry_run: If True, only report what would be done
    """
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    files = sorted([f for f in os.listdir(emblems_dir) if f.lower().endswith('.png')])
    
    stats = {
        "already_transparent": 0,
        "processed": 0,
        "corrupted": 0,
        "errors": 0,
    }
    
    for i, filename in enumerate(files):
        src_path = os.path.join(emblems_dir, filename)
        dst_path = os.path.join(output_dir or emblems_dir, filename)
        
        try:
            img = Image.open(src_path)
            img.load()  # Force load to catch corrupted files
        except Exception as e:
            print(f"  ⚠ CORRUPTED: {filename} — {e}")
            stats["corrupted"] += 1
            # Copy corrupted file as-is if output dir is different
            if output_dir and output_dir != emblems_dir:
                import shutil
                shutil.copy2(src_path, dst_path)
            continue
        
        try:
            img_rgba = img.convert("RGBA")
            arr = np.array(img_rgba)
            bg_type = detect_background_type(arr)
            
            if bg_type == "transparent":
                stats["already_transparent"] += 1
                if output_dir and output_dir != emblems_dir:
                    img_rgba.save(dst_path)
                continue
            
            if dry_run:
                print(f"  Would process: {filename} (bg_type={bg_type})")
                stats["processed"] += 1
                continue
            
            # Process the image
            result = remove_background_smart(img, tolerance=tolerance)
            result.save(dst_path, "PNG")
            stats["processed"] += 1
            
            # Progress indicator
            if (i + 1) % 20 == 0 or i == len(files) - 1:
                print(f"  Progress: {i+1}/{len(files)} — "
                      f"processed={stats['processed']}, "
                      f"transparent={stats['already_transparent']}, "
                      f"corrupted={stats['corrupted']}")
            
        except Exception as e:
            print(f"  ✗ ERROR: {filename} — {e}")
            stats["errors"] += 1
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"  Background Removal Complete")
    print(f"  Already transparent: {stats['already_transparent']}")
    print(f"  Processed (bg removed): {stats['processed']}")
    print(f"  Corrupted (skipped): {stats['corrupted']}")
    print(f"  Errors: {stats['errors']}")
    print(f"  Total: {sum(stats.values())}")
    print(f"{'='*60}")
    
    return stats


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Batch Emblem Background Remover")
    parser.add_argument("directory", help="Directory containing emblem PNGs")
    parser.add_argument("--output", help="Output directory (default: overwrite in-place)")
    parser.add_argument("--tolerance", type=int, default=40, help="BG color tolerance (0-255)")
    parser.add_argument("--dry-run", action="store_true", help="Only report, don't modify")
    args = parser.parse_args()
    
    process_emblems_directory(
        args.directory,
        output_dir=args.output,
        tolerance=args.tolerance,
        dry_run=args.dry_run,
    )
