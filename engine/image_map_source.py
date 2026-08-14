"""Image-based heightmap/land-mask source for the EU4 WGS pipeline.  
  
Converts a land-mask image + heightmap image into the same  
(heightmap_8bit, land_mask) arrays produced by  
MapGenerationEngine.generate_complete_heightmap, so the rest of the  
province/river/terrain/export pipeline can consume them unchanged.  
"""  
from typing import Optional, Tuple  
  
import numpy as np  
from PIL import Image  
  
  
def build_heightmap_from_images(  
    mask_path: str,  
    height_path: str,  
    target_width: Optional[int] = None,  
    target_height: Optional[int] = None,  
) -> Tuple[np.ndarray, np.ndarray]:  
    """Build (heightmap_8bit, land_mask) from source images.  
  
    :param mask_path:   B&W landmass mask (white = land, black = sea)  
    :param height_path: grayscale heightmap  
    :param target_width/target_height: optional resize target; defaults to  
        the mask's native size.  
    :returns: (heightmap, land_mask)  
        heightmap  -> uint8 array, sea = 0, land = 55..255  
        land_mask  -> bool array, True where land  
    """  
    # 1. Load as single-channel grayscale  
    land_img = Image.open(mask_path).convert("L")  
    height_img = Image.open(height_path).convert("L")  
  
    # 2. Resolve target dimensions  
    width, height = land_img.size  
    if target_width and target_height:  
        width, height = target_width, target_height  
        land_img = land_img.resize((width, height), Image.Resampling.LANCZOS)  
  
    if land_img.size[0] % 64 != 0 or land_img.size[1] % 64 != 0:  
        print(f"[image_map_source] WARNING: dimensions "  
              f"({width}x{height}) are not multiples of 64. EU4 may crash.")  
  
    # 3. Match heightmap size to the mask  
    if height_img.size != (width, height):  
        height_img = height_img.resize((width, height), Image.Resampling.LANCZOS)  
  
    # 4. Boolean land mask (white = land). Threshold at mid-gray.  
    mask_arr = np.array(land_img)  
    land_mask = mask_arr > 127  
  
    # 5. Heightmap: sea = 0, land scaled into 55..255 (repo convention)  
    src = np.array(height_img, dtype=np.float32)  
    heightmap = np.zeros((height, width), dtype=np.uint8)  
  
    land_vals = src[land_mask]  
    if land_vals.size > 0 and land_vals.max() > land_vals.min():  
        scaled = (land_vals - land_vals.min()) / (land_vals.max() - land_vals.min())  
        heightmap[land_mask] = (scaled * 200 + 55).astype(np.uint8)  
    elif land_vals.size > 0:  
        heightmap[land_mask] = 128  # flat land fallback  
  
    return heightmap, land_mask
