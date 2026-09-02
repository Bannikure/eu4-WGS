"""
Canal candidate detection.
============================
Analyzes a land/water mask (from a freshly generated map, or an imported
one -- provinces.bmp + heightmap.bmp are all this needs) to find
geographically sensible canal locations: land bridges/isthmuses separating
two large landmasses or gulfs, narrow peninsula necks, and thin land gaps
between two otherwise-disconnected bodies of water (lake-to-lake or
lake-to-sea). These are the same categories real canals fall into --
Panama and Kra are isthmus cuts, Corinth is a peninsula-neck cut, Kiel
shortcuts a peninsula, and various canals connect a lake to the sea.

Deliberately does NOT attempt the full EU4 "Great Project" visual canal
system (canal_definition in default.map + a custom <name>_river.bmp tile +
an ambient_object entry) -- generating a correctly-aligned river tile
texture isn't something this can reliably do, and referencing one that
doesn't exist is exactly the kind of thing that crashes the game on load.
Instead this produces `type=canal` adjacencies.csv entries connecting the
water provinces on either side, which is pure data (no missing-asset risk)
and delivers the actual gameplay point: ships can pass through instead of
sailing all the way around.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.ndimage import distance_transform_edt, label as cc_label


@dataclass
class CanalCandidate:
    name: str
    x: int                          # representative pixel location, image coords (top-left origin)
    y: int
    kind: str                       # "isthmus" | "peninsula" | "lake_connector"
    land_width_px: int              # narrowness at the pinch point, in pixels
    province_a: Optional[int]
    province_b: Optional[int]
    note: str


def labeled_regions(mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Connected-component labels for a boolean mask, correctly merging
    components that touch across the horizontal map edge (EU4 maps wrap:
    sailing/walking off the right edge continues on the left) -- a plain
    scipy label() call would otherwise split a single real region into two
    wherever it happens to cross that seam. Returns (labels, sizes) where
    sizes[i] is the pixel count of label i (sizes[0], the background, is 0).
    """
    labels, num_labels = cc_label(mask, structure=np.ones((3, 3)))
    if num_labels == 0:
        return labels, np.zeros(1, dtype=np.int64)

    parent = list(range(num_labels + 1))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    left_col, right_col = labels[:, 0], labels[:, -1]
    for a, b in zip(left_col, right_col):
        if a != 0 and b != 0 and a != b:
            union(int(a), int(b))
    merged = np.array([find(i) for i in range(num_labels + 1)])
    labels = merged[labels]
    sizes = np.bincount(labels.ravel())
    return labels, sizes


class CanalDetector:
    """Stateless: call detect() with a land_mask (and province context for
    naming the two sides) from either a freshly generated map or one
    loaded from an imported heightmap/provinces.bmp pair."""

    @staticmethod
    def detect(land_mask: np.ndarray, province_infos: List,
               narrow_frac: float = 0.012, max_canals: int = 8) -> List[CanalCandidate]:
        """
        narrow_frac: how thin a land strip must be (relative to map height)
        to even be considered -- real canals cut through genuinely narrow
        necks, not general coastline. 1.2% of map height matches roughly
        the Isthmus of Panama's width relative to a 2048px-tall map.
        max_canals: hard cap so this reports a short list of the most
        significant crossings (vanilla EU4 itself only has 4), not every
        minor pinch point on the map.
        """
        try:
            from skimage.morphology import skeletonize
        except ImportError:
            return []

        h, w = land_mask.shape
        narrow_threshold = max(2, int(h * narrow_frac))

        land_dist = distance_transform_edt(land_mask)
        water_labels, water_sizes = labeled_regions(~land_mask)
        water_sizes = water_sizes.copy()
        water_sizes[0] = 0
        ocean_label = int(np.argmax(water_sizes)) if water_sizes.size > 1 else 0

        skeleton = skeletonize(land_mask)
        narrow_skeleton = skeleton & (land_dist <= narrow_threshold)
        # Land clipped by the top/bottom map border looks artificially
        # "thin" to the skeleton (it's cut off by the frame, not actually
        # narrow) -- EU4 maps don't wrap vertically like they do
        # horizontally, so there's no equivalent fix to the wraparound
        # merge above; those rows are simply excluded from consideration.
        edge_margin = max(4, int(h * 0.02))
        narrow_skeleton[:edge_margin, :] = False
        narrow_skeleton[-edge_margin:, :] = False
        if not narrow_skeleton.any():
            return []

        # Group adjacent narrow-skeleton pixels into clusters -- one real
        # isthmus produces many neighbouring qualifying skeleton pixels,
        # and each cluster should yield exactly one candidate, not dozens.
        cluster_labels, num_clusters = cc_label(narrow_skeleton, structure=np.ones((3, 3)))

        total_land = int(land_mask.sum())
        min_piece = max(30, int(total_land * 0.01))  # each side must be a real landmass, not a stray pixel

        candidates: List[CanalCandidate] = []
        for cluster_id in range(1, num_clusters + 1):
            ys, xs = np.where(cluster_labels == cluster_id)
            if len(ys) == 0:
                continue
            widths = land_dist[ys, xs]
            best = int(np.argmin(widths))
            py, px = int(ys[best]), int(xs[best])
            pw = float(widths[best])

            cut_radius = max(1, int(pw) + 2)
            y0, y1 = max(0, py - cut_radius), min(h, py + cut_radius + 1)
            x0, x1 = max(0, px - cut_radius), min(w, px + cut_radius + 1)
            yy, xx = np.ogrid[y0:y1, x0:x1]
            disk = (yy - py) ** 2 + (xx - px) ** 2 <= cut_radius ** 2

            cut_mask = land_mask.copy()
            local = cut_mask[y0:y1, x0:x1]
            local[disk] = False
            cut_mask[y0:y1, x0:x1] = local

            land_labels_after, land_sizes_after = labeled_regions(cut_mask)
            land_sizes_after = land_sizes_after.copy()
            land_sizes_after[0] = 0
            significant_pieces = int((land_sizes_after >= min_piece).sum())

            # Sample water labels touching the cut disk directly (using the
            # ORIGINAL, pre-cut water mask+labels) to tell whether this
            # pinch already separates two distinct water bodies.
            ring = disk & (~land_mask[y0:y1, x0:x1])
            touching_labels = set(int(v) for v in water_labels[y0:y1, x0:x1][ring] if v != 0)

            if len(touching_labels) >= 2:
                kind = "lake_connector"
                is_valid = True
            elif significant_pieces >= 2:
                kind = "isthmus"
                is_valid = True
            else:
                is_valid = False

            if not is_valid:
                continue

            side_a, side_b = CanalDetector._find_sides(cut_mask, land_dist, py, px, cut_radius, h, w)
            prov_a = CanalDetector._nearest_sea_province(province_infos, side_a) if side_a else None
            prov_b = CanalDetector._nearest_sea_province(province_infos, side_b) if side_b else None
            if prov_a is None or prov_b is None or prov_a == prov_b:
                continue

            if kind == "isthmus" and significant_pieces >= 2:
                pieces_sorted = np.sort(land_sizes_after[land_sizes_after >= min_piece])[::-1]
                if len(pieces_sorted) >= 2 and pieces_sorted[1] / max(pieces_sorted[0], 1) < 0.03:
                    kind = "peninsula"

            candidates.append(CanalCandidate(
                name=f"canal_{len(candidates) + 1}",
                x=px, y=py, kind=kind, land_width_px=int(pw * 2),
                province_a=prov_a, province_b=prov_b,
                note=f"{kind} crossing, ~{int(pw * 2)}px land width",
            ))

        # Prefer the narrowest, most decisive crossings; cap the total count.
        candidates.sort(key=lambda c: c.land_width_px)
        deduped: List[CanalCandidate] = []
        for c in candidates:
            if any(abs(c.x - d.x) < narrow_threshold * 3 and abs(c.y - d.y) < narrow_threshold * 3 for d in deduped):
                continue
            deduped.append(c)
            if len(deduped) >= max_canals:
                break

        for i, c in enumerate(deduped, start=1):
            c.name = f"canal_{i}"
        return deduped

    @staticmethod
    def _find_sides(cut_mask: np.ndarray, land_dist: np.ndarray, py: int, px: int,
                     radius: int, h: int, w: int) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
        """Samples a water point on each side of the cut, walking outward
        along the two opposite directions of steepest local land retreat."""
        search = radius + 6
        y0, y1 = max(0, py - search), min(h, py + search + 1)
        x0, x1 = max(0, px - search), min(w, px + search + 1)
        water_here = ~cut_mask[y0:y1, x0:x1]
        ys, xs = np.where(water_here)
        if len(ys) < 2:
            return None, None
        ys = ys + y0
        xs = xs + x0
        # Split points into two groups by which side of the pinch centre
        # they fall on, using the dominant axis of spread.
        dy, dx = ys - py, xs - px
        if np.ptp(dx) >= np.ptp(dy):
            side = dx >= 0
        else:
            side = dy >= 0
        pts_a = list(zip(ys[side], xs[side]))
        pts_b = list(zip(ys[~side], xs[~side]))
        if not pts_a or not pts_b:
            return None, None
        a = max(pts_a, key=lambda p: (p[0] - py) ** 2 + (p[1] - px) ** 2)
        b = max(pts_b, key=lambda p: (p[0] - py) ** 2 + (p[1] - px) ** 2)
        return (int(a[1]), int(a[0])), (int(b[1]), int(b[0]))  # (x, y)

    @staticmethod
    def _nearest_sea_province(province_infos: List, point: Tuple[int, int]) -> Optional[int]:
        px, py = point
        best_id, best_dist = None, None
        for p in province_infos:
            if not p.is_sea:
                continue
            d = (p.center_x - px) ** 2 + (p.center_y - py) ** 2
            if best_dist is None or d < best_dist:
                best_dist, best_id = d, p.id
        return best_id
