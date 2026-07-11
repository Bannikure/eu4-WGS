import type { TerrainType } from './eu4-types'

// ─── Seeded PRNG (Mulberry32) ────────────────────────────────────────────────

/**
 * Creates a deterministic pseudo-random number generator using the Mulberry32
 * algorithm. Returns a function that produces values in [0, 1) on each call.
 */
export function createRNG(seed: number): () => number {
  let state = seed | 0
  return () => {
    state = (state + 0x6d2b79f5) | 0
    let t = Math.imul(state ^ (state >>> 15), 1 | state)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

// ─── Color utilities ─────────────────────────────────────────────────────────

/**
 * Converts HSL values to a hex color string.
 * h ∈ [0, 360], s ∈ [0, 1], l ∈ [0, 1]
 */
export function hslToHex(h: number, s: number, l: number): string {
  const a = s * Math.min(l, 1 - l)
  const f = (n: number) => {
    const k = (n + h / 30) % 12
    const color = l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1))
    return Math.round(255 * color)
      .toString(16)
      .padStart(2, '0')
  }
  return `#${f(0)}${f(8)}${f(4)}`
}

/**
 * Generates a visually distinct RGB color from a province ID.
 * Uses a golden-angle hue spread for maximum distinction.
 */
export function provinceColor(id: number): { r: number; g: number; b: number } {
  const hue = ((id * 137.508) % 360 + 360) % 360
  const hex = hslToHex(hue, 0.55, 0.5)
  return {
    r: parseInt(hex.slice(1, 3), 16),
    g: parseInt(hex.slice(3, 5), 16),
    b: parseInt(hex.slice(5, 7), 16),
  }
}

/**
 * Generates a deterministic country color from an index and seed.
 * Spreads countries around the color wheel with vibrant saturation.
 */
export function countryColor(
  index: number,
  seed: number,
): { r: number; g: number; b: number } {
  const rng = createRNG(seed + index * 7919)
  const hue = (rng() * 360) | 0
  const sat = 0.45 + rng() * 0.35
  const lit = 0.38 + rng() * 0.24
  const hex = hslToHex(hue, sat, lit)
  return {
    r: parseInt(hex.slice(1, 3), 16),
    g: parseInt(hex.slice(3, 5), 16),
    b: parseInt(hex.slice(5, 7), 16),
  }
}

// ─── Country TAG generation ──────────────────────────────────────────────────

/**
 * Derives a 3-4 uppercase letter TAG from a country name.
 * Examples: "Francia" → "FRA", "Great Ming" → "MNG", "Aztec Empire" → "AZT"
 */
export function nameToTag(name: string): string {
  const words = name.toUpperCase().replace(/[^A-Z\s]/g, '').split(/\s+/).filter(Boolean)
  if (words.length === 0) return 'XXX'

  // Single word: use first 3 letters
  if (words.length === 1) {
    const w = words[0]
    // Skip common prefixes
    const stripped = w.replace(/^(GREAT|KINGDOM OF|EMPIRE OF|REPUBLIC OF|DUCHY OF)\s*/g, '')
    if (stripped.length >= 3) return stripped.slice(0, 3)
    return w.slice(0, 3).padEnd(3, 'X')
  }

  // Multi-word: take first letter of each significant word
  const significant = words.filter(
    (w) => !['OF', 'THE', 'AND', 'GREAT', 'EMPIRE', 'KINGDOM', 'REPUBLIC', 'DUCHY'].includes(w),
  )
  if (significant.length >= 3) {
    return significant.slice(0, 3).map((w) => w[0]).join('')
  }
  if (significant.length === 2) {
    // Two significant words: first letter of first + first two of second
    return significant[0][0] + significant[1].slice(0, 2)
  }
  // Fallback
  return words[0].slice(0, 3).padEnd(3, 'X')
}

// ─── Flood fill ──────────────────────────────────────────────────────────────

/**
 * Performs a flood fill on a grid. Returns an array of pixel indices that are
 * connected to (startX, startY) and share the same value. Uses BFS for stack
 * safety on large regions. The `visited` array is mutated in-place.
 *
 * @param grid   - The grid to fill (values are compared for equality)
 * @param width  - Grid width in pixels
 * @param height - Grid height in pixels
 * @param startX - Starting X coordinate
 * @param startY - Starting Y coordinate
 * @param visited - Uint8Array of visited flags (mutated in place)
 * @param targetValue - Optional: only fill pixels matching this value. Defaults to grid[startX, startY]
 * @returns Array of pixel indices (y * width + x)
 */
export function floodFill(
  grid: Uint8Array,
  width: number,
  height: number,
  startX: number,
  startY: number,
  visited: Uint8Array,
  targetValue?: number,
): number[] {
  const startIdx = startY * width + startX
  const target = targetValue ?? grid[startIdx]
  const result: number[] = []

  // BFS queue (pre-allocated ring buffer)
  const queue = new Int32Array(width * height)
  let head = 0
  let tail = 0

  if (visited[startIdx]) return result

  visited[startIdx] = 1
  queue[tail++] = startX | (startY << 16)

  while (head < tail) {
    const packed = queue[head++]
    const cx = packed & 0xffff
    const cy = (packed >> 16) & 0xffff
    const cIdx = cy * width + cx
    result.push(cIdx)

    // 4-directional neighbors
    const neighbors: [number, number][] = [
      [cx - 1, cy],
      [cx + 1, cy],
      [cx, cy - 1],
      [cx, cy + 1],
    ]

    for (const [nx, ny] of neighbors) {
      if (nx < 0 || nx >= width || ny < 0 || ny >= height) continue
      const nIdx = ny * width + nx
      if (visited[nIdx]) continue
      if (grid[nIdx] !== target) continue

      visited[nIdx] = 1
      queue[tail++] = nx | (ny << 16)
    }
  }

  return result
}

// ─── Terrain classification ──────────────────────────────────────────────────

/** Terrain type index mapping (matches TerrainType order) */
export const TERRAIN_INDICES: Record<TerrainType, number> = {
  ocean: 0,
  coastal: 1,
  plains: 2,
  hills: 3,
  mountains: 4,
  high_mountains: 5,
  wasteland: 6,
}

export const TERRAIN_BY_INDEX: TerrainType[] = [
  'ocean',
  'coastal',
  'plains',
  'hills',
  'mountains',
  'high_mountains',
  'wasteland',
]

/**
 * Classifies a pixel's terrain based on its elevation and land/water status.
 * @param elevation - Normalized 0-1 elevation
 * @param isLand - Whether the pixel is land
 * @param isCoastal - Whether the pixel borders water (for coastal classification)
 */
export function elevationToTerrain(
  elevation: number,
  isLand: boolean,
): TerrainType {
  if (!isLand) return 'ocean'
  if (elevation < 0.08) return 'coastal'
  if (elevation < 0.35) return 'plains'
  if (elevation < 0.60) return 'hills'
  if (elevation < 0.82) return 'mountains'
  return 'high_mountains'
}
