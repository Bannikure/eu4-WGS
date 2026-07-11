/**
 * Seeded, deterministic 2D value noise + FBM + heightmap generation.
 * All functions are pure given the same seed.
 */
import type { MapConfig } from './eu4-types'
import { floodFill } from './eu4-utils'

// ═══════════════════════════════════════════════════════════════════════════════
// Core noise
// ═══════════════════════════════════════════════════════════════════════════════

function hash(x: number, y: number, seed: number): number {
  let h = (seed + x * 374761393 + y * 668265263 + 1610612741) | 0
  h = Math.imul(h ^ (h >>> 13), 1274126177)
  h = h ^ (h >>> 16)
  return (h >>> 0) / 4294967296
}

function smoothNoise(x: number, y: number, seed: number): number {
  const ix = Math.floor(x)
  const iy = Math.floor(y)
  const fx = x - ix
  const fy = y - iy
  const sx = fx * fx * (3 - 2 * fx)
  const sy = fy * fy * (3 - 2 * fy)

  const n00 = hash(ix, iy, seed)
  const n10 = hash(ix + 1, iy, seed)
  const n01 = hash(ix, iy + 1, seed)
  const n11 = hash(ix + 1, iy + 1, seed)

  return n00 + (n10 - n00) * sx + (n01 + (n11 - n01) * sx - (n00 + (n10 - n00) * sx)) * sy
}

export function fbmNoise(
  x: number,
  y: number,
  seed: number,
  octaves: number,
): number {
  let value = 0
  let amplitude = 1
  let frequency = 1
  let maxValue = 0

  for (let i = 0; i < octaves; i++) {
    value += smoothNoise(x * frequency, y * frequency, seed + i * 1024) * amplitude
    maxValue += amplitude
    amplitude *= 0.5
    frequency *= 2
  }

  return (value / maxValue) * 2 - 1
}

// ═══════════════════════════════════════════════════════════════════════════════
// Heightmap generation
// ═══════════════════════════════════════════════════════════════════════════════

export function generateHeightmap(config: MapConfig): {
  heightmap: Float32Array
  landMask: Uint8Array
  continentMap: Uint8Array
  continentCount: number
} {
  const { width, height, seed, landPercentage, mapStyle, octaves } = config
  const totalPixels = width * height
  const heightmap = new Float32Array(totalPixels)
  const landMask = new Uint8Array(totalPixels)
  const freqScale = 0.004

  for (let py = 0; py < height; py++) {
    for (let px = 0; px < width; px++) {
      const nx = px * freqScale
      const ny = py * freqScale
      const idx = py * width + px

      switch (mapStyle) {
        case 'pangea': {
          const cx = px / width - 0.5
          const cy = py / height - 0.5
          const dist = Math.sqrt(cx * cx + cy * cy) * 2.2
          const centerBias = Math.max(0, 1 - dist)
          const edgeNoise =
            smoothNoise(nx * 3, ny * 3, seed + 5000) * 0.25 * dist
          heightmap[idx] =
            fbmNoise(nx, ny, seed, octaves) + centerBias * 1.2 + edgeNoise
          break
        }
        case 'continents': {
          const continentSeeds = [seed + 100, seed + 200, seed + 300]
          let continentBias = 0
          for (const cs of continentSeeds) {
            const cx2 = (hash(0, 0, cs) * 0.6 + 0.2) * width
            const cy2 = (hash(1, 0, cs) * 0.6 + 0.2) * height
            const dx = px - cx2
            const dy = py - cy2
            const d = Math.sqrt(dx * dx + dy * dy) / (width * 0.4)
            continentBias += Math.max(0, 1 - d) * 0.8
          }
          heightmap[idx] = fbmNoise(nx, ny, seed, octaves) + continentBias
          break
        }
        case 'archipelago': {
          const cx = px / width - 0.5
          const cy = py / height - 0.5
          const dist = Math.sqrt(cx * cx + cy * cy)
          const islandNoise =
            fbmNoise(nx * 1.5, ny * 1.5, seed + 3000, octaves) * 0.8
          const edgeBias = dist * 0.6
          heightmap[idx] = islandNoise + edgeBias
          break
        }
        case 'continents_islands': {
          const cSeeds = [seed + 100, seed + 200]
          let continentBias = 0
          for (const cs of cSeeds) {
            const cx2 = (hash(0, 0, cs) * 0.5 + 0.25) * width
            const cy2 = (hash(1, 0, cs) * 0.5 + 0.25) * height
            const dx = px - cx2
            const dy = py - cy2
            const d = Math.sqrt(dx * dx + dy * dy) / (width * 0.35)
            continentBias += Math.max(0, 1 - d) * 0.7
          }
          const islandNoise =
            fbmNoise(nx * 2, ny * 2, seed + 4000, 3) * 0.35
          heightmap[idx] =
            fbmNoise(nx, ny, seed, octaves) + continentBias + islandNoise
          break
        }
      }
    }
  }

  // Normalize to [0, 1]
  let hMin = Infinity
  let hMax = -Infinity
  for (let i = 0; i < totalPixels; i++) {
    if (heightmap[i] < hMin) hMin = heightmap[i]
    if (heightmap[i] > hMax) hMax = heightmap[i]
  }
  const hRange = hMax - hMin || 1
  for (let i = 0; i < totalPixels; i++) {
    heightmap[i] = (heightmap[i] - hMin) / hRange
  }

  // Threshold for land mask
  const sorted = new Float32Array(totalPixels)
  sorted.set(heightmap)
  sorted.sort()
  const thresholdIdx = Math.floor(totalPixels * (1 - landPercentage / 100))
  const landThreshold =
    sorted[Math.max(0, Math.min(totalPixels - 1, thresholdIdx))]

  for (let i = 0; i < totalPixels; i++) {
    landMask[i] = heightmap[i] >= landThreshold ? 1 : 0
  }

  // Continent detection via flood fill
  const visited = new Uint8Array(totalPixels)
  const continentMap = new Uint8Array(totalPixels)
  let continentId = 0
  const MIN_CONTINENT = 200

  for (let py = 0; py < height; py++) {
    for (let px = 0; px < width; px++) {
      const idx = py * width + px
      if (landMask[idx] === 1 && !visited[idx]) {
        const region = floodFill(landMask, width, height, px, py, visited)
        if (region.length >= MIN_CONTINENT) {
          continentId++
          for (const ri of region) continentMap[ri] = continentId
        }
      }
    }
  }

  return { heightmap, landMask, continentMap, continentCount: continentId }
}
