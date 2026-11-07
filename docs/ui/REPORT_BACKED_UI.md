# Report-backed product UI

The product UI (`frontend/src/ui/product/`) now shows saved project results instead of synthetic demo fixtures. Every panel names its source file. Nothing on these pages is a live observation, official warning, safe route or shelter instruction.

## Sections and sources

| Section | What it shows | Source |
|---|---|---|
| Situation Overview | Saved depth map, A07 impact KPIs, Open-Meteo weather card, A21/A10/Track B summaries | A05 rasters, `PHASE13_IMPACT_BATCH2_V4.md`, CR-014 client |
| Flood Simulation | 3 events × 5 rainfall scenarios × 5 leads × p05/p50/p95 on the 600 m grid, 2D and 3D | `data/features/forecast/batch2_v1/`, `PHASE11_FORECAST_BATCH2.md`, `PHASE12_SIMULATION.md` |
| Impacts & Shelters | A07 screened people/roads/facilities by lead, 72 h access cascade, A10 capacity sensitivity, A11 layers | `PHASE13_IMPACT_BATCH2_V4.md`, `SHELTER_ALLOCATION_BATCH2.md`, `PRIORITY_ZONES_BATCH2.md` |
| Road Routing | A21 three-state outcomes, bootstrap intervals, verification queue, decision stability; A09 methods | `ROUTING_THREE_STATE_BATCH3.md`, `ROUTING_BATCH2.md` |
| What-if Comparison | Two saved scenarios side by side or as a difference map; A13 H2–H5 | A05 rasters, `DECISION_LAB_BATCH2.md` |
| Reservoirs (Track B) | B45 CFM-DSS snapshot on request, 2015 REPLAY alert grid, held-out storage backtest | `reservoir-live/`, `trackb/replay_2015_alerts.jsonl`, `trackb/BACKTEST_REPORT.md` |
| Data & Evidence | Task status, sources and connections, gate snapshot, grid provenance, coverage states, limits | `master/STATE.json`, `VALIDATION_REPORT.md` |

Report figures are transcribed in `frontend/src/ui/evidence/reports.ts`. Update the matching block when a report changes.

## Saved depth grids

`data/features/` is git-ignored, so the grids are exported into a git-ignored folder:

```powershell
.venv\Scripts\python.exe tools\ui\export_ui_depth_grids.py
```

This reads the 225 saved A05 GeoTIFFs read-only and writes `frontend/src/ui/evidence/generated/a05_<event>.json`. Depths are stored as millimetres, with 65535 for NoData (outside the assessed CMA, not dry). Nothing is interpolated or re-modelled. Each event loads lazily (about 140–190 KB gzipped). Without the export, the build still works: the map says the grid is not loaded and report figures stay available.

## Presentation rules kept

- NoData is drawn as a faint dot texture and labelled "unknown, not dry"; a valid zero is a separate class.
- The 3D view extrudes the same saved values with a stated vertical exaggeration; north points top-right there.
- Only five saved lead times exist; nothing is interpolated between them.
- Unknown road edges are "Unknown · verify", never passable. Unassessed metrics show "Not assessed", never 0.
- No composite risk score, ranking, live claim or operational wording was added.
