# A23 — Spatial Open-Meteo rainfall forcing over the A06 domain

**Task:** A23 (Lane A). **Authority:** CR-015 (one bounded Open-Meteo snapshot, one research-only run). **Date:** 2026-11-07.
**Decision: Gate 1 `FEASIBLE_WITH_LIMITS`; Gate 2 research run completed.** All outputs are `DERIVED_RESEARCH_OUTPUT` from numerical-weather-model rainfall. No forecast skill, hydraulic accuracy, warning, or safety claim is made.

## Gate 1 — feasibility

| Criterion | Finding |
|---|---|
| Product/model identity | Open-Meteo Forecast API with explicit `models=` (not `auto`): **ECMWF IFS HRES** (`ecmwf_ifs`, nominal ~9 km), **UK Met Office Global 10 km** (`ukmo_global_deterministic_10km`), **DWD ICON Global** (`icon_global`, ~13 km). Model run/initialisation time is not supplied by the API and is recorded as unknown. |
| Spatial coverage of A06 domain | A06 domain (2,430 active + 908 drain cells, 600 m, EPSG:32644) spans lon 80.005–80.342, lat 12.852–13.292. A 0.05° sampling lattice (+0.03° margin; 80 locations per model) returned **38 distinct ECMWF native cells, 18 UKMO, 16 ICON** over the domain — a genuine spatial field, not one point. A pre-run probe at 0.03° found 46 ECMWF cells, so the 0.05° lattice under-samples ECMWF slightly (see caveats). |
| 72-hour horizon | `forecast_hours=72` returned 72 consecutive hourly UTC values for all three models, plus `past_hours=24` used only as model spin-up. No gaps, nulls or duplicate times in the snapshot. |
| Time/unit semantics | Hourly `precipitation` in mm is the sum over the **preceding hour**, labelled by interval end time (UTC, `utc_offset_seconds=0` verified). Mapped directly to A06 `hourly_mm`; no rates are inferred and the 15-minute `current` field is not used. Fetch time (2026-11-07T06:45:10Z) is recorded separately from valid times. |
| Spatial mapping | Each A06 cell takes the value of the nearest sampled native cell (equirectangular distance). Piecewise-constant, no smoothing, no invented sub-grid variability. Edge error ≤ half the lattice spacing (~2.8 km). NoData/missing is never zero-filled: a model with any missing point-hour is excluded. |
| Physics/assumptions | Unchanged A06: dry start (spun up with 24 past model hours), WorldCover Manning/porosity/infiltration defaults with the 20 A06 multipliers, open water/waterways as free-drain sinks, no-flow land edges, no storm drains, tides, river stage or reservoir releases. |
| Compute | ~2.1 s per 96-hour member on this machine; 60 members in 124 s. |

**Why "with limits":** model rainfall at 9–13 km is far coarser than the 600 m solver grid, and A06 itself is an unvalidated coarse pilot. The forcing is reproducible and correctly mapped, but it supports research experiments only.

## Gate 2 — research run results

Run `a23-research-20261107T064510Z`; combined forcing SHA-256 `ed5c55ac7615b986df0b822d78ea04df3dd1dd61ffa82e616bb25d3807cc12de`.

| Check | Result |
|---|---|
| Solver equivalence | `services/flood_engine/solver.py` reproduces `pipelines/phase12/simulate.py` bit-for-bit for uniform rain on both the real A06 grid and a synthetic grid (max depth difference 0.0; same step count). Spatial rain only changes the per-cell rain term. |
| Mass balance | All 60 members ≤ 1% (A06 criterion): median 0.67%, max 0.91%. Steps per member 1,156–1,768. |
| Numerical validity | All depths finite and non-negative; cells outside the assessed CMA are NoData, never dry. |
| Rainfall (domain mean, next 72 h) | ECMWF 12.96 mm (max cell 17.6), UKMO 10.99 mm (15.8), ICON 12.81 mm (34.9). Past 24 h: 3.6 / 4.8 / 9.4 mm. |
| Flood response | Peak area ≥ 0.15 m: median 0.36 km² (p95 3.24 km²); nothing reaches 0.30 m in any member. Exposure at ≥ 0.15 m: median ~2,900 people (p95 ~25,900), median ~5.5 road-km. Derived outlook level **MINIMAL**. No mapped hospital/shelter cell reaches the 0.30 m access threshold. |

Outputs (not overwriting A05/A06):

- `data/features/weather/openmeteo_a06_domain_v1/` — exact responses per model + `manifest.json` (requests, hashes, valid-time range, fetch time).
- `data/features/simulation/openmeteo_grid_72h_v1/` — `depth_peak_{mean,p05,p95}_DERIVED.tif`, `depth_prob_peak_ge_0_30_DERIVED.tif`, `hourly_mean_depth_DERIVED.npz`, `run_summary.json` (timeline, exposure, facilities, member diagnostics, provenance).
- `data/features/live/a06_live_static_v1/` — NumPy bundle of the A06 grid, A07 population/roads and OSM hospitals/shelters (`static_meta.json` records source hashes; bundle SHA-256 `424c0cea…a8f`).

## Caveats

1. Weather-model rainfall, not gauge observation; not validated against IMD or gauges for this window.
2. A06 is a coarse, assumption-based pilot with no independent depth truth; this run is not a flood forecast.
3. Ensemble spread (3 weather models × 20 parameter members) is descriptive, not a calibrated confidence interval.
4. The 0.05° lattice sampled 38 of the ~46 ECMWF cells seen at 0.03°; a few native cells are represented by a neighbour (≤ ~2.8 km shift). 0.03° × 4 models exceeded Open-Meteo's per-minute free limit (HTTP 429), so the final snapshot uses 0.05° and three models; the fetcher retries once after 65 s on 429.
5. **Request disclosure:** besides the final 3-model snapshot, preparation used one 2-point probe per candidate model (11 requests) and one 0.03° trial across four models (GFS returned 429). These trial responses were not retained or used for the run.
6. No reservoir boundary: A06 cannot ingest reservoir releases; CFM-DSS reservoir data remains display-only.

## Handover — live engine and drafted API (for change control)

**Engine (`services/flood_engine/`, NumPy only):**

- `forcing.py` — builds the sampling lattice from the static bounds, fetches `past_hours=24`, `forecast_hours=72` for the three models, validates units/time/coordinates, excludes incomplete models, maps to the grid, and writes a manifest with per-model and combined hashes.
- `solver.py` — A06 step with per-cell rain (equivalence-tested).
- `engine.py` — `compute_run` (ensemble, peak/p05/p95/probability grids, hourly mean depth, timeline, exposure at 0.15/0.30/0.50 m, facility access flags, outlook level), `RunStore` (atomic versioned `live-<fetch time>-<sha8>` directories, keeps 48), `LiveEngine.run_once` (rate limit, and identical forcing → `unchanged`, no new run).
- CLI: `python -m services.flood_engine.cli run --static data/features/live/a06_live_static_v1 --runs <dir> [--force]` → one JSON line `{"outcome","run_id"}`.
- Runtime: ~30 s per 20-member single-model ensemble; ~2 min for the 3-model, 60-member ensemble.
- Static bundle: regenerate with `python -m pipelines.phase12_openmeteo_grid.static_export`.

**Drafted API (`services/ai-service/app/live/router.py`, NOT mounted, not committed):** `GET /live/status`, `GET /live/runs`, `GET /live/runs/latest`, `GET /live/runs/{run_id}`, `GET /live/runs/{run_id}/grid/{layer}?hour=` (layers `peak_mean|peak_p05|peak_p95|prob_peak_ge_0_30|hourly_mean`; JSON grid with nulls for NoData), `POST /live/runs` (202; runs the CLI in a child process, one at a time). Optional scheduler via `TWINGUARD_LIVE_SCHEDULE_MIN`. It is exercised by `tests/phase12_openmeteo_grid/test_flood_engine.py` on a standalone app.

**Still needed before any live use (not done here):** an Integrator change request authorising recurring Open-Meteo retrieval (CR-015 permits one snapshot) and the API projection; Lane B packaging (copy `services/flood_engine` into the AI image, mount the static bundle read-only and a writable run store, proxy route); UI wiring by the ui session; and B42 evidence that new observations trigger recomputation. At 0.05° × 3 models a run uses ~240 Open-Meteo location-calls, so a 2-hour cycle stays well within the free 10,000/day limit.

## Reproduce

```
python -m pipelines.phase12_openmeteo_grid.static_export
python -m pipelines.phase12_openmeteo_grid.run          # refuses to overwrite an existing output
python -m pytest tests/phase12_openmeteo_grid
```
