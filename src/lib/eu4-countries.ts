/**
 * Country generation — each land province becomes a country with
 * culture, religion, tech group, and development. Implements the
 * "inverted dynamics" concept: southern/eastern continents are more developed.
 */
import type { MapConfig, ProvinceInfo, CountryData, TerrainType } from './eu4-types'
import { createRNG, countryColor, nameToTag } from './eu4-utils'
import {
  CULTURE_GROUPS,
  RELIGIONS,
  TECH_GROUPS,
  GOVERNMENTS,
  getRandomCountryName,
} from './eu4-name-lists'

export function generateCountries(
  provinces: ProvinceInfo[],
  _provinceTerrain: Map<number, TerrainType>,
  continentMap: Uint8Array,
  continentCount: number,
  config: MapConfig,
): CountryData[] {
  const { width, height, seed } = config
  const rng = createRNG(seed + 77777)

  const landProvinces = provinces.filter((p) => !p.isSea && !p.isWasteland)
  if (landProvinces.length === 0) return []

  // ── Continent centroids ────────────────────────────────────────────────

  const continentInfo = new Map<
    number,
    { cx: number; cy: number; count: number }
  >()

  for (const prov of landProvinces) {
    const ci = continentMap[prov.centerY * width + prov.centerX] || 0
    if (!continentInfo.has(ci)) {
      continentInfo.set(ci, { cx: 0, cy: 0, count: 0 })
    }
    const info = continentInfo.get(ci)!
    info.cx += prov.centerX
    info.cy += prov.centerY
    info.count++
  }

  for (const [, info] of continentInfo) {
    info.cx /= info.count
    info.cy /= info.count
  }

  // Rank continents: south + east = higher rank = more dev
  const continentEntries = Array.from(continentInfo.entries())
  continentEntries.sort((a, b) => {
    const sa = a[1].cy / height + (a[1].cx / width) * 0.5
    const sb = b[1].cy / height + (b[1].cx / width) * 0.5
    return sb - sa
  })

  const continentRank = new Map<number, number>()
  continentEntries.forEach(([cid], idx) => continentRank.set(cid, idx))

  // ── Assign religion/tech/culture to continents ─────────────────────────

  const continentReligion = new Map<number, string>()
  const continentTech = new Map<number, string>()
  const continentCulture = new Map<number, string>()

  const religionGroups = [
    'christian', 'muslim', 'dharmic', 'eastern', 'pagan', 'zoroastrian',
  ]
  const cultureGroupKeys = Object.keys(CULTURE_GROUPS)

  for (const [cid] of continentEntries) {
    continentReligion.set(cid, religionGroups[(rng() * religionGroups.length) | 0])
    continentTech.set(cid, TECH_GROUPS[(rng() * TECH_GROUPS.length) | 0])
    continentCulture.set(cid, cultureGroupKeys[(rng() * cultureGroupKeys.length) | 0])
  }

  // ── Create countries ───────────────────────────────────────────────────

  const countries: CountryData[] = []
  const usedNames = new Set<string>()
  const totalContinents = continentEntries.length

  for (const prov of landProvinces) {
    const ci = continentMap[prov.centerY * width + prov.centerX] || 0
    const rank = continentRank.get(ci) ?? 0

    // Inverted dynamics: lower rank = more dev
    const devBonus =
      totalContinents > 1 ? (1 - rank / (totalContinents - 1)) * 15 : 5
    const baseDev = 3 + (rng() * 5) | 0

    const cultureGroup =
      rng() < 0.7
        ? continentCulture.get(ci) ?? 'germanic'
        : cultureGroupKeys[(rng() * cultureGroupKeys.length) | 0]

    // Unique name
    let nameInfo: { name: string; adjective: string }
    let attemptCount = 0
    do {
      const nameSeed = seed + prov.id * 31337 + attemptCount * 7919
      nameInfo = getRandomCountryName(nameSeed, cultureGroup)
      attemptCount++
    } while (usedNames.has(nameInfo.name) && attemptCount < 50)

    usedNames.add(nameInfo.name)
    const tag = nameToTag(nameInfo.name)

    // Religion
    const relGroup = continentReligion.get(ci) ?? 'christian'
    const groupReligions = RELIGIONS.filter((r) => r.group === relGroup)
    const religion =
      groupReligions.length > 0
        ? groupReligions[(rng() * groupReligions.length) | 0]
        : RELIGIONS[(rng() * RELIGIONS.length) | 0]

    const techGroup = continentTech.get(ci) ?? 'western'
    const government = GOVERNMENTS[(rng() * GOVERNMENTS.length) | 0]
    const color = countryColor(countries.length, seed)
    const continentName = ci === 0 ? 'Uncharted Isles' : `Continent ${ci}`

    const adm = baseDev + (rng() * (devBonus * 0.5)) | 0
    const dip = baseDev + (rng() * (devBonus * 0.5)) | 0
    const mil = baseDev + (rng() * (devBonus * 0.5)) | 0
    const isAdvanced = adm + dip + mil >= 18

    countries.push({
      tag,
      name: nameInfo.name,
      adjective: nameInfo.adjective,
      capitalProvinceId: prov.id,
      colorR: color.r,
      colorG: color.g,
      colorB: color.b,
      adm,
      dip,
      mil,
      religion: religion.name,
      religionGroup: religion.group,
      techGroup,
      culture: nameInfo.adjective,
      cultureGroup,
      isAdvanced,
      continent: continentName,
      government,
    })
  }

  return countries
}
