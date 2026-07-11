export interface MapConfig {
  width: number       // map width in pixels (default 1200)
  height: number      // map height (default 512)
  seed: number        // random seed
  landPercentage: number  // 10-50
  mapStyle: 'pangea' | 'continents' | 'archipelago' | 'continents_islands'
  octaves: number     // noise octaves (default 6)
  provinceCount: number  // target land provinces (default 200)
}

export interface ProvinceInfo {
  id: number
  colorR: number
  colorG: number
  colorB: number
  centerX: number
  centerY: number
  pixelCount: number
  isSea: boolean
  isWasteland: boolean
  terrainType: TerrainType
  elevation: number
}

export type TerrainType = 'ocean' | 'coastal' | 'plains' | 'hills' | 'mountains' | 'high_mountains' | 'wasteland'

export interface CountryData {
  tag: string
  name: string
  adjective: string
  capitalProvinceId: number
  colorR: number
  colorG: number
  colorB: number
  adm: number
  dip: number
  mil: number
  religion: string
  religionGroup: string
  techGroup: string
  culture: string
  cultureGroup: string
  isAdvanced: boolean
  continent: string
  government: string
}

export interface GenerationResult {
  config: MapConfig
  heightmap: Float32Array       // 0-1 normalized height values
  landMask: Uint8Array          // 0=water, 1=land
  provinces: ProvinceInfo[]
  provinceMap: Uint32Array      // province ID at each pixel index
  countries: CountryData[]
  terrainMap: Uint8Array        // terrain type index at each pixel
  rivers: { x: number; y: number }[][]
  continentMap: Uint8Array      // continent ID at each pixel
  continentCount: number
  generationTime: number
  statistics: {
    totalProvinces: number
    landProvinces: number
    seaProvinces: number
    wastelandProvinces: number
    totalCountries: number
    landPercentage: number
    religionDistribution: Record<string, number>
    techDistribution: Record<string, number>
    terrainDistribution: Record<string, number>
    continentDistribution: Record<string, { count: number; totalDev: number; avgDev: number }>
    topCountries: { tag: string; name: string; dev: number; color: string }[]
  }
}
