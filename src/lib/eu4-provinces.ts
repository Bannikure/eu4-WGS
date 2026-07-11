/**
 * Province generation via Poisson-like seed placement + Voronoi partition.
 */
import type { MapConfig, ProvinceInfo } from './eu4-types'
import { createRNG, provinceColor, floodFill } from './eu4-utils'

export function generateProvinces(
  heightmap: Float32Array,
  landMask: Uint8Array,
  config: MapConfig,
): { provinces: ProvinceInfo[]; provinceMap: Uint32Array } {
  const { width, height, seed, provinceCount } = config
  const totalPixels = width * height
  const rng = createRNG(seed + 9999)

  // Collect land pixels
  const landPixels: number[] = []
  for (let i = 0; i < totalPixels; i++) {
    if (landMask[i] === 1) landPixels.push(i)
  }

  if (landPixels.length === 0) {
    return { provinces: [], provinceMap: new Uint32Array(totalPixels) }
  }

  // Poisson-like seed placement
  const targetSeeds = Math.min(provinceCount, landPixels.length)
  const minDist = Math.sqrt(
    (width * height * (config.landPercentage / 100)) / (targetSeeds * Math.PI),
  ) * 1.2

  const seeds: { x: number; y: number }[] = []
  let attempts = 0
  const maxAttempts = targetSeeds * 200

  while (seeds.length < targetSeeds && attempts < maxAttempts) {
    attempts++
    const pi = landPixels[(rng() * landPixels.length) | 0]
    const sx = pi % width
    const sy = (pi / width) | 0

    let tooClose = false
    for (const s of seeds) {
      const dx = s.x - sx
      const dy = s.y - sy
      if (dx * dx + dy * dy < minDist * minDist) {
        tooClose = true
        break
      }
    }
    if (!tooClose) seeds.push({ x: sx, y: sy })
  }

  // Voronoi: assign each land pixel to nearest seed (squared Euclidean)
  const provinceMap = new Uint32Array(totalPixels)
  for (const pi of landPixels) {
    const px = pi % width
    const py = (pi / width) | 0
    let bestDist = Infinity
    let bestSeed = 0

    for (let s = 0; s < seeds.length; s++) {
      const dx = seeds[s].x - px
      const dy = seeds[s].y - py
      const dist = dx * dx + dy * dy
      if (dist < bestDist) {
        bestDist = dist
        bestSeed = s + 1
      }
    }
    provinceMap[pi] = bestSeed
  }

  const numLandProvs = seeds.length

  // Count pixels per province
  const provPixelCounts = new Int32Array(numLandProvs + 1)
  for (const pi of landPixels) {
    const pid = provinceMap[pi]
    if (pid > 0) provPixelCounts[pid]++
  }

  // Build adjacency
  const adjacency = new Map<number, Set<number>>()
  for (let i = 1; i <= numLandProvs; i++) adjacency.set(i, new Set())

  for (let py = 1; py < height - 1; py++) {
    for (let px = 1; px < width - 1; px++) {
      const idx = py * width + px
      const pid = provinceMap[idx]
      if (pid === 0) continue
      const nids = [
        provinceMap[idx - 1],
        provinceMap[idx + 1],
        provinceMap[idx - width],
        provinceMap[idx + width],
      ]
      for (const nid of nids) {
        if (nid > 0 && nid !== pid) adjacency.get(pid)!.add(nid)
      }
    }
  }

  // Merge small provinces (< 30 px)
  const MIN_SIZE = 30
  const mergedInto = new Int32Array(numLandProvs + 1)

  for (let pid = 1; pid <= numLandProvs; pid++) {
    if (provPixelCounts[pid] >= MIN_SIZE) continue
    if (mergedInto[pid] !== 0) continue

    let bestNeighbor = 0
    let bestSize = 0
    for (const nid of adjacency.get(pid) ?? []) {
      if (mergedInto[nid] !== 0) continue
      if (provPixelCounts[nid] > bestSize) {
        bestSize = provPixelCounts[nid]
        bestNeighbor = nid
      }
    }

    if (bestNeighbor > 0) {
      let root = bestNeighbor
      while (mergedInto[root] !== 0) root = mergedInto[root]
      mergedInto[pid] = root
      provPixelCounts[root] += provPixelCounts[pid]
    }
  }

  // Apply merges
  for (const pi of landPixels) {
    let pid = provinceMap[pi]
    if (pid === 0) continue
    while (mergedInto[pid] !== 0) pid = mergedInto[pid]
    provinceMap[pi] = pid
  }

  // Sea provinces via flood fill on water
  const waterVisited = new Uint8Array(totalPixels)
  const seaProvStartId = numLandProvs + 1
  let seaId = seaProvStartId
  const MIN_SEA = 500

  for (let py = 0; py < height; py++) {
    for (let px = 0; px < width; px++) {
      const idx = py * width + px
      if (landMask[idx] === 0 && provinceMap[idx] === 0 && !waterVisited[idx]) {
        const region = floodFill(landMask, width, height, px, py, waterVisited, 0)
        if (region.length >= MIN_SEA) {
          for (const ri of region) provinceMap[ri] = seaId
          seaId++
        }
      }
    }
  }

  // Assign remaining tiny water bodies to first sea province
  const globalOceanId = seaId > seaProvStartId ? seaProvStartId : seaProvStartId
  for (let i = 0; i < totalPixels; i++) {
    if (landMask[i] === 0 && provinceMap[i] === 0) {
      provinceMap[i] = globalOceanId
    }
  }

  // Build province info
  const provinces: ProvinceInfo[] = []
  const processedIds = new Set<number>()
  for (let i = 0; i < totalPixels; i++) {
    const pid = provinceMap[i]
    if (pid > 0) processedIds.add(pid)
  }

  for (const pid of processedIds) {
    let sumX = 0
    let sumY = 0
    let count = 0
    let sumElev = 0

    for (let i = 0; i < totalPixels; i++) {
      if (provinceMap[i] === pid) {
        sumX += i % width
        sumY += (i / width) | 0
        sumElev += heightmap[i]
        count++
      }
    }

    const cx = (sumX / count) | 0
    const cy = (sumY / count) | 0
    const isSea =
      pid >= seaProvStartId ||
      (cx >= 0 && cy >= 0 && cx < width && cy < height && landMask[cy * width + cx] === 0)

    const provColor = provinceColor(pid)
    provinces.push({
      id: pid,
      colorR: provColor.r,
      colorG: provColor.g,
      colorB: provColor.b,
      centerX: cx,
      centerY: cy,
      pixelCount: count,
      isSea,
      isWasteland: false,
      terrainType: 'plains',
      elevation: sumElev / count,
    })
  }

  provinces.sort((a, b) => a.id - b.id)
  return { provinces, provinceMap }
}
