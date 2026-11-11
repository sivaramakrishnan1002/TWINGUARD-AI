# B56 7-tab end-to-end run (recorded)

`node tests/e2e/ui_7tabs_e2e.mjs http://localhost:5173/ <outDir>` against the dev stack (API :8000, Vite :5173),
2026-11-11 03:12 UTC. Result: **59 passed, 1 failed** (`e2e_results.json`).

- The failed check is "tab switching ≥ 30 fps": 23.3 fps during the 7-tab tour. This run had the laptop on battery
  with Chrome on the Intel Iris Xe integrated GPU; the same tour measures 37.1 fps on that GPU in isolation and
  103.9 fps on the RTX 3050 (`docs/ui/perf/`). Playback 42.1 fps, pan 104.4 fps, idle 51.6 fps in this run.
- Passed: live run badge time and run id equal `/v3/live/status`; replay switch and back to live; Max depth and Wards
  affected equal `/v3` depth and wards (frame 51); Peak extent and Roads screened equal the run summary; scrub,
  playback, 3D / 2D / Satellite, area search (Royapuram), what-if to completion (comparison filled), route request,
  reservoir snapshot, 0 console errors on all 7 tabs, layout passes at 1366x768 and 1920x1080 (no horizontal scroll),
  Google / Cesium attribution, no key in any `/api/ai` request.

| File | View |
| --- | --- |
| `00_overview_live_run.webp` | Overview on the latest LIVE_FORECAST run (live-first default) |
| `01_overview.webp` ... `07_twin.webp` | All 7 tabs, Dec 2015 citywide replay, frame 51 (T+25 h), 1600x1000 |
| `layout_1366x768_*.webp` | All 7 tabs at 1366x768 |
| `layout_1920x1080_*.webp` | All 7 tabs at 1920x1080 |
