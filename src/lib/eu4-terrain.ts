/**
 * Terrain classification for the world map.
 */
import type { ProvinceInfo, TerrainType } from './eu4-types'
import { elevationToTerrain, TERRAIN_INDICES, TERRAIN_BY_INDEX } from './eu4-utils'

export function classifyTerrain(
  heightmap: Float32Array,
  landMask: Uint8Array,
  provinceMap: Uint32Array,
  provinces: ProvinceInfo[],
): { terrainMap: Uint8Array; provinceTerrain: Map<number, TerrainType> } {
  const totalPixels = heightmap.length
  const terrainMap = new Uint8Array(totalPixels)

  // Per-pixel terrain classification
  for (let i = 0; i < totalPixels; i++) {
    const isLand = landMask[i] === 1
    const terrain = elevationToTerrain(heightmap[i], isLand)
    terrainMap[i] = TERRAIN_INDICES[terrain]
  }

  // Dominant terrain per province (sampled every other pixel for speed)
  const provTerrains = new Map<number, Map<TerrainType, number>>()
  for (const prov of provinces) {
    provTerrains.set(prov.id, new Map())
  }

  for (let i = 0; i < totalPixels; i += 2) {
    const pid = provinceMap[i]
    if (pid === 0) continue
    const terrain = TERRAIN_BY_INDEX[terrainMap[i]]
    const counts = provTerrains.get(pid)
    if (counts) counts.set(terrain, (counts.get(terrain) ?? 0) + 1)
  }

  const provinceTerrain = new Map<number, TerrainType>()
  for (const prov of provinces) {
    const counts = provTerrains.get(prov.id)
    if (!counts || counts.size === 0) {
      prov.terrainType = prov.isSea ? 'ocean' : 'plains'
    } else {
      let dominant: TerrainType = 'plains'
      let maxCount = 0
      for (const [t, c] of counts) {
        if (c > maxCount) { maxCount = c; dominant = t }
      }
      prov.terrainType = dominant
    }

    // High mountains become wasteland
    if (prov.terrainType === 'high_mountains' && !prov.isSea) {
      prov.isWasteland = true
      prov.terrainType = 'wasteland'
    }

    provinceTerrain.set(prov.id, prov.terrainType)
  }

  return { terrainMap, provinceTerrain }
}
