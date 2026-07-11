/**
 * EU4 World Generator — procedural world generation engine.
 *
 * Orchestrates: heightmap → provinces → terrain → countries → rivers → statistics.
 * All functions are purely deterministic given the same config seed.
 */
import type { MapConfig, GenerationResult } from './eu4-types'
import { generateHeightmap } from './eu4-noise'
import { generateProvinces } from './eu4-provinces'
import { classifyTerrain } from './eu4-terrain'
import { generateCountries } from './eu4-countries'
import { generateRivers } from './eu4-rivers'

// ═══════════════════════════════════════════════════════════════════════════════
// Main entry point
// ═══════════════════════════════════════════════════════════════════════════════

export function generateWorld(config: MapConfig): GenerationResult {
  const startTime = performance.now()

  const cfg: MapConfig = {
    width: config.width ?? 1200,
    height: config.height ?? 512,
    seed: config.seed ?? Date.now(),
    landPercentage: Math.max(10, Math.min(50, config.landPercentage ?? 30)),
    mapStyle: config.mapStyle ?? 'continents',
    octaves: config.octaves ?? 6,
    provinceCount: config.provinceCount ?? 200,
  }

  const { width, height } = cfg

  // 1. Generate heightmap + land mask + continents
  const { heightmap, landMask, continentMap, continentCount } =
    generateHeightmap(cfg)

  // 2. Generate provinces (Voronoi partition)
  const { provinces, provinceMap } = generateProvinces(heightmap, landMask, cfg)

  // 3. Classify terrain
  const { terrainMap, provinceTerrain } = classifyTerrain(
    heightmap,
    landMask,
    provinceMap,
    provinces,
  )

  // 4. Remap land elevations to full 0-1 range for display
  let landMin = Infinity
  let landMax = -Infinity
  for (let i = 0; i < heightmap.length; i++) {
    if (landMask[i] === 1) {
      if (heightmap[i] < landMin) landMin = heightmap[i]
      if (heightmap[i] > landMax) landMax = heightmap[i]
    }
  }
  const displayHeightmap = new Float32Array(heightmap.length)
  const landRange = landMax - landMin || 1
  for (let i = 0; i < heightmap.length; i++) {
    if (landMask[i] === 1) {
      displayHeightmap[i] = (heightmap[i] - landMin) / landRange
    } else {
      displayHeightmap[i] = heightmap[i] * 0.5
    }
  }

  // 5. Generate countries
  const countries = generateCountries(
    provinces,
    provinceTerrain,
    continentMap,
    continentCount,
    cfg,
  )

  // 6. Generate rivers
  const rivers = generateRivers(displayHeightmap, landMask, cfg)

  // 7. Compute statistics
  const landProvinces = provinces.filter((p) => !p.isSea)
  const seaProvinces = provinces.filter((p) => p.isSea)
  const wastelandProvinces = provinces.filter((p) => p.isWasteland)

  const religionDistribution: Record<string, number> = {}
  const techDistribution: Record<string, number> = {}
  for (const c of countries) {
    religionDistribution[c.religion] = (religionDistribution[c.religion] ?? 0) + 1
    techDistribution[c.techGroup] = (techDistribution[c.techGroup] ?? 0) + 1
  }

  const terrainDistribution: Record<string, number> = {}
  for (const p of provinces) {
    terrainDistribution[p.terrainType] = (terrainDistribution[p.terrainType] ?? 0) + 1
  }

  const continentDistribution: Record<
    string,
    { count: number; totalDev: number; avgDev: number }
  > = {}
  for (const c of countries) {
    if (!continentDistribution[c.continent]) {
      continentDistribution[c.continent] = { count: 0, totalDev: 0, avgDev: 0 }
    }
    continentDistribution[c.continent].count++
    continentDistribution[c.continent].totalDev += c.adm + c.dip + c.mil
  }
  for (const cont of Object.keys(continentDistribution)) {
    const d = continentDistribution[cont]
    d.avgDev = Math.round((d.totalDev / d.count) * 10) / 10
  }

  const topCountries = [...countries]
    .sort((a, b) => b.adm + b.dip + b.mil - (a.adm + a.dip + a.mil))
    .slice(0, 8)
    .map((c) => ({
      tag: c.tag,
      name: c.name,
      dev: c.adm + c.dip + c.mil,
      color: `rgb(${c.colorR},${c.colorG},${c.colorB})`,
    }))

  let landPixelCount = 0
  for (let i = 0; i < landMask.length; i++) {
    if (landMask[i] === 1) landPixelCount++
  }
  const actualLandPct =
    Math.round((landPixelCount / (width * height)) * 1000) / 10

  const generationTime = Math.round((performance.now() - startTime) * 10) / 10

  return {
    config: cfg,
    heightmap: displayHeightmap,
    landMask,
    provinces,
    provinceMap,
    countries,
    terrainMap,
    rivers,
    continentMap,
    continentCount,
    generationTime,
    statistics: {
      totalProvinces: provinces.length,
      landProvinces: landProvinces.length,
      seaProvinces: seaProvinces.length,
      wastelandProvinces: wastelandProvinces.length,
      totalCountries: countries.length,
      landPercentage: actualLandPct,
      religionDistribution,
      techDistribution,
      terrainDistribution,
      continentDistribution,
      topCountries,
    },
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// World configuration presets
// ═══════════════════════════════════════════════════════════════════════════════

export const WORLD_PRESETS: Record<string, MapConfig> = {
  pangaea: {
    width: 1200,
    height: 512,
    seed: 42,
    landPercentage: 35,
    mapStyle: 'pangea',
    octaves: 6,
    provinceCount: 200,
  },
  continents: {
    width: 1200,
    height: 512,
    seed: 42,
    landPercentage: 32,
    mapStyle: 'continents',
    octaves: 6,
    provinceCount: 200,
  },
  archipelago: {
    width: 1200,
    height: 512,
    seed: 42,
    landPercentage: 22,
    mapStyle: 'archipelago',
    octaves: 5,
    provinceCount: 160,
  },
  old_world: {
    width: 1200,
    height: 512,
    seed: 42,
    landPercentage: 38,
    mapStyle: 'continents_islands',
    octaves: 7,
    provinceCount: 250,
  },
  random: {
    width: 1200,
    height: 512,
    seed: Math.floor(Math.random() * 1000000),
    landPercentage: 20 + Math.floor(Math.random() * 25),
    mapStyle: (
      ['pangea', 'continents', 'archipelago', 'continents_islands'] as const
    )[Math.floor(Math.random() * 4)],
    octaves: 4 + Math.floor(Math.random() * 5),
    provinceCount: 150 + Math.floor(Math.random() * 150),
  },
}
