# B48 UI screenshots

Captured 2026-11-08 with headless Chrome (RTX 3050 via ANGLE) against the live C4 v3 API
(`/api/ai/v3`), run `evt-20261108T141229Z-fb36a1cd` (Dec 2015 event, 48 h, citywide 120 m, CUDA),
frame 72 (T+36 h) unless noted. Tools: `tools/ui/capture_screens.mjs`, `tools/ui/capture_photoreal.mjs`.

| File | Shows |
|---|---|
| 01–07 | The seven tabs (Situation Overview … Digital Twin 3D City) |
| 08, 09 | Citywide oblique and Velachery close-up (earlier capture, saved results) |
| 11–13 | End-to-end check: Run Simulation, What-if and Find Routes calling the API |
| 14 | Water animated by modelled `/flow` velocities (legend: "modelled velocity") |
| 15 | Experimental "Photoreal roofs" toggle, before/after, Velachery and T. Nagar |
| 16 | G5 evidence: tabs 2 and 7 with run_id, REPLAY input, SIMULATED, CUDA, `/flow`, DEMO badge, Google attribution |

## Load size (production build)

| | Main JS chunk | gzip | 3D engine |
|---|---|---|---|
| Before (704faa8) | 4,525 kB | 1,233 kB | bundled in main chunk |
| After | 270 kB | 87 kB | lazy `Twin3D` chunk, 4,268 kB / 1,151 kB gzip |

First contentful paint measured with `tools/ui/measure_load.mjs` (SwiftShader, 2 cold runs) is about
the same (2.6–3.0 s before, 2.8 s after); the UI shell no longer waits for the 3D engine. The "after" build
reaches the viewer in 0.5–0.65 s, and globe and citywide buildings in about 20 s under software rendering.
