"""
Module B – Visual Render Pipeline.

The original code contained a partially-defined ``VisualRenderPipeline`` class
fragment inserted mid-file with duplicate imports; that wrapper has been
removed. Every function here is a plain module-level callable.

Public API
----------
generate_world_normal             – Sobel normal map (world_normal.bmp)
generate_watercolor_bmp           – parchment-style background
generate_rivers                   – D8 hydrological flow simulation
generate_seasonal_terrain_bmp     – latitude-driven terrain colours
render_photorealistic_3d_viewport – advanced hill-shaded 3-D popup
render_3d_viewport_preview        – quick lower-res 3-D preview
"""

from __future__ import annotations

import numpy as np
import cv2  # type: ignore[import-untyped]
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource  # type: ignore[import-untyped]
from PIL import Image


# ---------------------------------------------------------------------------
# Normal map
# ---------------------------------------------------------------------------

def generate_world_normal(
    heightmap_array: np.ndarray,
    output_path: str = "world_normal.bmp",
    intensity: float = 1.0,
) -> None:
    """Derive a tangent-space normal map from a greyscale heightmap."""
    heightmap = heightmap_array.astype(np.float32)
    sobel_x = cv2.Sobel(heightmap, cv2.CV_32F, 1, 0, ksize=-1) * intensity
    sobel_y = cv2.Sobel(heightmap, cv2.CV_32F, 0, 1, ksize=-1) * intensity
    z = np.ones_like(heightmap)
    magnitude = np.sqrt(sobel_x**2 + sobel_y**2 + z**2)

    r = ((sobel_x / magnitude + 1.0) * 127.5).astype(np.uint8)
    g = ((sobel_y / magnitude + 1.0) * 127.5).astype(np.uint8)
    b = ((z / magnitude + 1.0) * 127.5).astype(np.uint8)

    Image.fromarray(cv2.merge([r, g, b]), "RGB").save(output_path)
    print(f"✓ world_normal.bmp saved → {output_path}")


# ---------------------------------------------------------------------------
# Watercolour background
# ---------------------------------------------------------------------------

def generate_watercolor_bmp(
    land_mask: np.ndarray,
    output_path: str = "map/watercolor.bmp",
) -> None:
    """Render a parchment-style watercolour map background."""
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
    blurred_mask = cv2.GaussianBlur(mask_8bit, (51, 51), 0).astype(np.float32) / 255.0
    blurred_mask_3d = np.atleast_3d(blurred_mask)

    blended_map = (
        land_color_layer * blurred_mask_3d
        + base_parchment * (1.0 - blurred_mask_3d)
    )
    paper_noise = np.random.normal(0, 6.0, (height, width, 1)).astype(np.float32)
    final_canvas = np.clip(blended_map + paper_noise, 0, 255).astype(np.uint8)

    Image.fromarray(final_canvas, "RGB").save(output_path)
    print(f"✓ watercolor.bmp saved → {output_path}")


# ---------------------------------------------------------------------------
# River simulation
# ---------------------------------------------------------------------------

def generate_rivers(
    heightmap_array: np.ndarray,
    land_mask: np.ndarray,
    min_river_flow: int = 800,
) -> np.ndarray:
    """Simulate rainfall and D8 downhill routing to generate EU4 rivers.

    EU4 rivers.bmp colour convention:
    - Green (0, 255, 0)   – river source
    - Blue (0, 0, 225)    – standard river
    - Cyan (0, 225, 255)  – major river (flow ≥ 4× threshold)

    Returns:
        uint8 RGB array of shape ``(H, W, 3)``.
    """
    height, width = heightmap_array.shape
    flow_acc = np.ones((height, width), dtype=np.int32)

    indices = np.dstack(
        np.unravel_index(np.argsort(-heightmap_array, axis=None), (height, width))
    )[0]

    dy = [-1, -1, -1,  0, 0,  1, 1, 1]
    dx = [-1,  0,  1, -1, 1, -1, 0, 1]

    print("Simulating hydrological flow…")
    for y, x in indices:
        if not land_mask[y, x]:
            continue
        current_elev = heightmap_array[y, x]
        steepest_drop = 0
        target_neighbor: tuple[int, int] | None = None
        for i in range(8):
            ny, nx = y + dy[i], x + dx[i]
            if 0 <= ny < height and 0 <= nx < width:
                drop = int(current_elev) - int(heightmap_array[ny, nx])
                if drop > steepest_drop:
                    steepest_drop = drop
                    target_neighbor = (ny, nx)
        if target_neighbor:
            ty, tx = target_neighbor
            flow_acc[ty, tx] += flow_acc[y, x]

    river_map = np.full((height, width, 3), 255, dtype=np.uint8)
    river_pixels = np.argwhere((flow_acc >= min_river_flow) & land_mask)

    print("Carving river systems…")
    for y, x in river_pixels:
        volume = flow_acc[y, x]
        is_source = True
        for i in range(8):
            ny, nx = y + dy[i], x + dx[i]
            if 0 <= ny < height and 0 <= nx < width:
                if (
                    flow_acc[ny, nx] > min_river_flow
                    and heightmap_array[ny, nx] > heightmap_array[y, x]
                ):
                    is_source = False
                    break
        if is_source:
            river_map[y, x] = [0, 255, 0]
        elif volume > min_river_flow * 4:
            river_map[y, x] = [0, 225, 255]
        else:
            river_map[y, x] = [0, 0, 225]

    return river_map


# ---------------------------------------------------------------------------
# Terrain bitmap
# ---------------------------------------------------------------------------

def generate_seasonal_terrain_bmp(
    heightmap: np.ndarray,
    land_mask: np.ndarray,
    output_path: str = "map/terrain.bmp",
) -> None:
    """Generate terrain.bmp with latitude-driven climate zone colouring."""
    height, width = heightmap.shape
    terrain_canvas = np.zeros((height, width, 3), dtype=np.uint8)
    terrain_canvas[~land_mask] = [0, 40, 80]

    for y in range(height):
        row_mask = land_mask[y, :]
        if not np.any(row_mask):
            continue
        row_heights = heightmap[y, :]
        is_mountain = row_heights > 190
        is_hills = (row_heights <= 190) & (row_heights > 130)
        is_flat = row_mask & ~is_mountain & ~is_hills

        if y < 350 or y > 1698:
            terrain_canvas[y, is_flat]             = [200, 200, 200]
            terrain_canvas[y, row_mask & is_hills] = [140, 140, 140]
        elif 850 <= y <= 1198:
            terrain_canvas[y, is_flat]             = [240, 220, 160]
            terrain_canvas[y, row_mask & is_hills] = [120, 100,  50]
        else:
            terrain_canvas[y, is_flat]             = [ 80, 140,  60]
            terrain_canvas[y, row_mask & is_hills] = [100, 130,  70]

        terrain_canvas[y, row_mask & is_mountain] = [90, 90, 90]

    Image.fromarray(terrain_canvas, "RGB").save(output_path)
    print(f"✓ terrain.bmp saved → {output_path}")


# ---------------------------------------------------------------------------
# 3-D viewports
# ---------------------------------------------------------------------------

def render_photorealistic_3d_viewport(heightmap_8bit: np.ndarray) -> None:
    """Display a photo-realistic hill-shaded 3-D topography window."""
    step = 8
    h_small = heightmap_8bit[::step, ::step].astype(np.float32)

    y_len, x_len = h_small.shape
    x_grid, y_grid = np.meshgrid(np.arange(x_len), np.arange(y_len))
    y_grid = y_len - y_grid

    shader_rgba = np.zeros((y_len, x_len, 4), dtype=np.float32)
    shader_rgba[h_small <= 60]                          = [0.05, 0.10, 0.35, 1.0]
    shader_rgba[(h_small > 60)  & (h_small <= 125)]     = [0.10, 0.45, 0.65, 1.0]
    shader_rgba[(h_small > 125) & (h_small <= 132)]     = [0.92, 0.85, 0.68, 1.0]
    shader_rgba[(h_small > 132) & (h_small <= 165)]     = [0.15, 0.55, 0.22, 1.0]
    shader_rgba[(h_small > 165) & (h_small <= 210)]     = [0.45, 0.40, 0.30, 1.0]
    shader_rgba[h_small > 210]                          = [0.95, 0.95, 0.95, 1.0]

    light_source = LightSource(azdeg=315, altdeg=45)
    shaded_rgb = light_source.shade_rgb(
        shader_rgba[:, :, :3], h_small, blend_mode="overlay"
    )

    fig = plt.figure("Advanced Photo-Realistic 3D Topography Viewport", figsize=(12, 7))
    ax = fig.add_subplot(111, projection="3d")
    print("Rendering high-fidelity shaded 3-D map…")
    ax.plot_surface(  # type: ignore[union-attr]
        x_grid, y_grid, h_small,
        facecolors=shaded_rgb,
        linewidth=0, antialiased=False,
        rcount=y_len, ccount=x_len,
        shade=False,
    )
    ax.set_zlim(0, 255)  # type: ignore[union-attr]
    ax.set_box_aspect((x_len, y_len, 65))  # type: ignore[union-attr]
    ax.view_init(elev=38, azim=-55)  # type: ignore[union-attr]
    ax.axis("off")  # type: ignore[union-attr]
    plt.tight_layout()
    plt.show()


def render_3d_viewport_preview(
    heightmap_8bit: np.ndarray,
    terrain_bmp_rgb: np.ndarray,
) -> None:
    """Open a quick interactive 3-D preview using terrain colours."""
    step = 16
    h_small = heightmap_8bit[::step, ::step]
    t_small = terrain_bmp_rgb[::step, ::step]

    y_len, x_len = h_small.shape
    x_grid, y_grid = np.meshgrid(np.arange(x_len), np.arange(y_len))
    y_grid = y_len - y_grid

    colors_normalized = t_small.astype(float) / 255.0

    fig = plt.figure("3D Map Preview", figsize=(10, 6))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(  # type: ignore[union-attr]
        x_grid, y_grid, h_small,
        facecolors=colors_normalized,
        linewidth=0, antialiased=False,
    )
    ax.set_zlim(0, 255)  # type: ignore[union-attr]
    ax.view_init(elev=45, azim=-60)  # type: ignore[union-attr]
    ax.axis("off")  # type: ignore[union-attr]
    plt.show()
