/**
 * River generation — traces paths from high-elevation land pixels
 * following steepest gradient descent until reaching water.
 */
import type { MapConfig } from './eu4-types'
import { createRNG } from './eu4-utils'

export function generateRivers(
  heightmap: Float32Array,
  landMask: Uint8Array,
  config: MapConfig,
): { x: number; y: number }[][] {
  const { width, height, seed } = config
  const rng = createRNG(seed + 55555)
  const totalPixels = width * height

  const rivers: { x: number; y: number }[][] = []
  const riverTargets = Math.floor(config.provinceCount * 0.35)

  // Collect high-elevation land pixels as candidates
  const candidates: { idx: number; elevation: number }[] = []
  for (let i = 0; i < totalPixels; i++) {
    if (landMask[i] === 1 && heightmap[i] > 0.6) {
      candidates.push({ idx: i, elevation: heightmap[i] })
    }
  }

  candidates.sort((a, b) => b.elevation - a.elevation)
  const pool = candidates.slice(0, Math.min(riverTargets * 3, candidates.length))

  // Shuffle
  for (let i = pool.length - 1; i > 0; i--) {
    const j = (rng() * (i + 1)) | 0
    ;[pool[i], pool[j]] = [pool[j], pool[i]]
  }

  const sources = pool.slice(0, riverTargets)

  for (const { idx: startIdx } of sources) {
    const path: { x: number; y: number }[] = []
    const visited = new Set<number>()
    let currentIdx = startIdx
    let steps = 0
    const maxSteps = 500

    while (steps < maxSteps) {
      if (visited.has(currentIdx)) break
      visited.add(currentIdx)

      const cx = currentIdx % width
      const cy = (currentIdx / width) | 0
      path.push({ x: cx, y: cy })

      if (landMask[currentIdx] === 0) break

      // Find steepest descent (8-dir)
      let bestNeighbor = -1
      let bestElevation = heightmap[currentIdx]
      const dirs = [-1, 0, 1]

      for (const dy of dirs) {
        for (const dx of dirs) {
          if (dx === 0 && dy === 0) continue
          const nx = cx + dx
          const ny = cy + dy
          if (nx < 0 || nx >= width || ny < 0 || ny >= height) continue
          const nIdx = ny * width + nx
          if (visited.has(nIdx)) continue
          if (heightmap[nIdx] < bestElevation) {
            bestElevation = heightmap[nIdx]
            bestNeighbor = nIdx
          }
        }
      }

      if (bestNeighbor === -1) break
      currentIdx = bestNeighbor
      steps++
    }

    if (path.length >= 8) rivers.push(path)
  }

  return rivers
}
