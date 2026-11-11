# B56: UI performance, reference layout and 7-tab end-to-end test

Owner request (2026-11-10, 21:30 IST): the simulation map was slow and lagging, the centre map felt too small; follow
the reference design (`docs/ui/reference_images/owner_feedback_20261110_target_all_tabs.webp`, current state in
`owner_feedback_20261110_current.webp`), map everything properly, and add an end-to-end test.

## 1. Performance

Measured with `tools/ui/perf_probe.mjs` (headless Chrome on the real GPU, 1600x1000, Overview tab, Dec 2015 citywide
120 m replay `evt-20261108T152128Z-59eba744`, 97 frames). "Before" is the UI at `d672eae` served from a
`git archive` copy; "after" is this change. FPS is browser frames per second (requestAnimationFrame), long tasks are
main-thread tasks over 50 ms. JSON: `docs/ui/perf/`.

**RTX 3050 Laptop GPU (mains power)**: `before_overview.json` / `after_overview.json`

| | before | after |
| --- | --- | --- |
| Map canvas | 859 x 618 | 1238 x 561 (+31 % area) |
| Playback, 12 s | 22.6 fps, 10.1 s long tasks, 6 frames advanced | 121.7 fps, 0.38 s long tasks, 9 frames (one per 1.3 s, as designed) |
| Frame step (scrub to a new frame) | 3,172 ms median | 340 ms median (network included) |
| Tab switching, 7 tabs | 73.5 fps, 12.7 s long tasks, ~1.9 s per switch | 103.9 fps, 2.9 s long tasks, ~0.37 s per switch |
| Pan | 255.7 fps | 142.2 fps (both far above 30; p95 7.1 ms) |
| Idle | 143.8 fps | 143.8 fps |

**Intel Iris Xe integrated GPU (laptop on battery, "Silent" plan; Windows gave Chrome the iGPU)**: `*_igpu.json`

| | before | after |
| --- | --- | --- |
| Playback | 4.6 fps (p95 1.5 s) | 44.2 fps |
| Frame step | 3,994 ms | 287 ms |
| Tab switching | 18.4 fps, 18.5 s long tasks | 37.1 fps, 3.3 s long tasks |
| Pan / idle | 62.9 / 24.2 fps | 97.4 / 50.5 fps |

What changed:

- **Water texture**: `depthFieldCanvas` re-projected every texture pixel to UTM on every frame (~2.7 s per frame on
  the main thread). The per-pixel projection, bilinear taps and terrain heights are now cached once per grid
  (`fieldSampler`), the texture is 3 texels per model cell (max 1024 px), and finished textures are reused across tab
  switches (`cachedField`).
- **Frames**: depth and flow for a frame load together (one texture build, not two); playback advances only when the
  next frame is loaded (minimum 1.3 s per frame, matching the cross-fade) and prefetches the next frame; depth/flow
  caches are bounded (48 frames).
- **Tab switches**: static layers (6,705 citywide road polylines, rivers, CMA outline, locality labels, callouts) stay
  on the shared viewer and are re-shown, not rebuilt; the fallback extruded focus-area buildings are no longer built
  or recoloured per frame when the Cesium ion token is configured (they were never shown in that case).
- **Emergency queue** renders the 150 most severe of up to ~3,000 generated incidents (count shown).
- "Loading map tiles · 1" no longer sticks: a count that does not move for 5 s is hidden.
- Remaining tab-switch cost is Cesium shader/glyph work for the per-run water and road primitives.

## 2. Layout (reference design)

- Compact header: logo, title, Chennai, run badge (LIVE FORECAST · HH:MM IST / REPLAY / WHAT-IF / CUSTOM), data
  source, IST date/time, live temperature / humidity / wind (Open-Meteo model).
- The first layout row is sized to the window (measured `--tg-fill`): side columns scroll on their own and the map
  column fills the height. Side columns are 250-306 px. Below 860 px tall the Overview map keeps the full window height
  and its mini panels follow below.
- Map share of the window (e2e layout pass): 1366x768 - Overview 54 %, other tabs 38-43 %; 1920x1080 - Overview 47 %,
  other tabs 53-58 %; no horizontal scroll at either size.
- Map toolbar on one row: 3D / 2D / Satellite, Layers, area search (no longer hidden), Areas, and a run picker
  (citywide / focus groups). The legend is a compact card bottom-left with the depth ramp; "More" opens rivers, road
  states and building classes.
- Overview follows the reference: left column City Risk Snapshot (rain next 24 h, max depth now / peak, inundation,
  wards affected), Active Alerts (top 3 groups), Rainfall & Forecast chart, Confidence & Data Freshness; under the map
  the Reservoir Status, Emergency Support and Road Routing (Safe Routes) mini panels.
- Alerts are grouped by type and named by the nearest gazetteer locality, e.g. "Urban flood risk - Adambakkam,
  Madhavaram, Ambattur · 33 critical · 30,259 buildings in 2,763 cells · max 2.32 m", instead of a raw count of ~3,000
  rows; per-incident titles read "2 buildings flooded to 2.30 m · Adambakkam" (the API's "Shelter unreachable: nan"
  becomes "Shelter cut off: unnamed site").
- Flood Simulation: Simulation Setup and Saved Simulations left, map centre, Simulation Result plus Inundation Growth
  chart right. Other tabs keep their panels with the same narrower columns and full-height map.
- Values no longer wrap ("199/200" was "199/20 0"). Locality labels are decluttered on screen against the place
  callouts and each other (no more "Velachery/Jagannathapuram" overprint).
- The default camera no longer jumps to Velachery in the dev build (React StrictMode re-ran the focus-area effect).

## 3. Data binding

Every number shown comes from the C4 v3 API or the project's own files: run summary and frames, depth/flow per frame,
wards, incidents (generated: true), shelters (capacities "assumed"), scenario resources (SCENARIO_INPUT), roads
(3-state), live status, Open-Meteo weather (MODEL_FORECAST), the CFM-DSS snapshot (PUBLISHED_SNAPSHOT, fetched only
on request). The e2e test asserts on-screen values against `/v3` (below). Run-kind badges, the disclaimer, ASSUMPTION
labels and the Google / Cesium / OpenStreetMap attribution are unchanged.

## 4. End-to-end test

`tests/e2e/ui_7tabs_e2e.mjs` drives headless Chrome over the DevTools protocol (`tools/ui/cdp.mjs`, no new
dependencies) against the running stack (`start_twinguard.ps1`: API :8000, Vite :5173):

```
node tests/e2e/ui_7tabs_e2e.mjs http://localhost:5173/ docs/ui/screenshots/e2e_b56
```

It checks the live run (badge time = `/v3/live/status` issued_at, run picker = latest live run, source health), the
switch to the Dec 2015 replay and back to live, Max depth and Wards affected against `/v3 .../depth` and `/wards`,
Peak extent and Roads screened against the run summary, timeline scrub and playback, 3D / 2D / Satellite
(scene mode), area search (Royapuram, camera position), a what-if run to completion with its comparison table, a
route request, the reservoir snapshot, 0 console errors on each tab, the layout passes at 1366x768 and 1920x1080, and
that no Cesium/Google key appears in any `/api/ai` request. Results: `docs/ui/screenshots/e2e_b56/e2e_results.json`
and the screenshots in the same folder.

The recorded run is listed in `docs/ui/screenshots/e2e_b56/README.md`.
