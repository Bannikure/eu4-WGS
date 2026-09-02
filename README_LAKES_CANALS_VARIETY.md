# eu4-WGS: Export Pipeline Fix

## What was actually broken

Your repo has one solid, working generator (`eu4_wgs_v8`'s `engine` /
`content` / `analytics` / `export` stack) plus two disconnected side
projects (`eu4gen/` — an old legacy generator nothing imports anymore, and
`src/lib/eu4-*.ts` — a standalone browser reimplementation via the Blink
app builder). Those two aren't touched by this fix.

Inside the real generator, `export/eu4_exporter.py` had been mid-refactor
and left broken: `export/__init__.py` expected five classes
(`MapFileExporter`, `CountryFileExporter`, `ProvinceHistoryExporter`,
`ModDescriptorExporter`, `MasterExportOrchestrator`), but only one existed,
missing most of its methods — so `python main.py --headless` crashed
before writing a single file. The map-generation engine itself
(heightmap/provinces/rivers/terrain — the six `.bmp` files you originally
uploaded) already worked fine; it just never got wired all the way through
to a real, loadable mod folder.

## What changed

- **`export/eu4_exporter.py`** — rebuilt as the five cooperating classes
  the rest of the codebase already expected: map bitmaps + text
  definitions, per-country files, province histories, the `.mod`
  descriptor, and the orchestrator that ties them together.
- **`main.py`, `generate_world.py`, `gui/studio.py`, `engine/map_generation.py`,
  `content/world_content.py`, `analytics/dashboard.py`,
  `engine/tunnel_generation.py`, `export/et_compatibility.py`** — import
  paths simplified from the fragile `eu4_wgs_v8.*` dynamic-module facade to
  direct top-level imports (`from engine.map_generation import ...`),
  matching how the packages are actually laid out on disk.
- **`eu4_wgs.spec`** — a PyInstaller build spec so `main.py` can be built
  into a standalone `eu4-wgs.exe`.

## Verified working

Ran both entry points end-to-end in a clean environment:

- `python main.py --test` — all 14 integration tests pass, including a
  full mod export (35 export categories written).
- `python main.py --headless --seed 7 --provinces 400 --map-width 1024
  --map-height 512` — produced a complete, correctly structured mod: 400
  country files, 400 province histories, 400 flags, and all 7 real EU4 map
  bitmaps (`heightmap.bmp`, `provinces.bmp`, `rivers.bmp`, `terrain.bmp`,
  `trees.bmp`, `watercolor.bmp`, `world_normal.bmp`) at the requested
  resolution — 2,091 files total, ready to drop into EU4's `mod/` folder.

One harmless warning shows up during export: `Skipping invalid emblems
asset 'giraffe.png'`. That's specific to *this* sandbox — it doesn't have
`git-lfs`, so image assets tracked via Git LFS (everything under
`eu4_wgs_v8/assets/`) came down as tiny text pointer files instead of real
images. On your own machine, with `git-lfs` installed (or if you just
download the repo as a ZIP from GitHub, which resolves LFS files
automatically), those will be real PNGs and this warning should disappear.

## How to apply this

In your local clone of `eu4-WGS`:

```bash
git apply eu4_wgs_export_fix.patch
```

Then copy `eu4_wgs.spec` into the repo root. If `git apply` complains about
conflicts, it means you've made local edits since this was generated —
paste the conflict output back and I'll help reconcile it.

## Building the .exe

PyInstaller doesn't cross-compile, so this has to be run **on Windows**:

```bash
pip install -r requirements.txt pyinstaller
pyinstaller eu4_wgs.spec
```

Output lands at `dist/eu4-wgs/eu4-wgs.exe`.

## Still open

- **`EUIV-Map-Generator`** — the GitHub URL you sent asks for
  authentication (private repo, or a typo in the name/owner). Fix the
  sharing settings or the spelling and send it again if you want it folded
  in too.
- **`eu4gen/` and `src/`** — still disconnected, untouched. Say the word
  if you want me to go through them for anything worth pulling into the
  main generator, or to remove them.
