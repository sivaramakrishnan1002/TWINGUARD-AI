# A28 — Live reservoir coupling and forecast-run checks

**Task:** A28 (CR-021 live forecast mode). **Engine:** `twinguard-flood-engine/2.1.0`. **Code:** `services/flood_engine/reservoir_coupling.py`, `services/flood_engine/scenario.py` (`reservoir_snapshot=`, `run_time=`, `forecast_model=`). **Tests:** `tests/flood_engine/test_a28_live.py` (offline fixtures). **Live check:** `pipelines/a25_hires/live_check.py`, writing `data/features/simulation/a28_live_check_v1/`.

## Coupling rule `A28-RES-STORAGE-v1` (ASSUMPTION)

CFM-DSS publishes daily average water level (m) and storage (MCM) per reservoir. **It publishes no release, inflow or outflow figures.** The inflows below are a modelling assumption derived from storage. They are labelled `ASSUMPTION` and `SCENARIO_INPUT`, and must never be presented as observed or published releases (CR-016 as amended by CR-021).

For each reservoir, the outlet inflow is held constant over the run. It is injected at the A25 river inlet cell, the river cell nearest the reservoir in `meta.inflow_cells`.

| Storage | Outlet inflow |
|---|---|
| below 90% of capacity | 0 m³/s (the reservoir absorbs inflow) |
| 90% to under 100% | Q_ctrl × (pct − 90) / 10 (controlled release ramps up) |
| 100% or more | Q_spill = 2 × Q_ctrl (surplus or spill) |

| Reservoir (CFM name) | Nominal capacity | Q_ctrl (assumption) | River in the A25 grid |
|---|---:|---:|---|
| Chembarambakkam | 3.645 TMC = 103.2 MCM | 170 m³/s | Adyar |
| Poondi | 3.231 TMC = 91.5 MCM | 140 m³/s | Kosasthalaiyar |
| Puzhal (CFM "Red Hills") | 3.300 TMC = 93.4 MCM | 60 m³/s | Kosasthalaiyar |
| Cholavaram | 1.081 TMC = 30.6 MCM | 30 m³/s | Kosasthalaiyar |
| Thervoy Kandigai | — | not coupled (no outlet in the A25 grid) | — |

- **Storage percentage:** taken from the snapshot when given, otherwise computed as storage_mcm / capacity × 100. Units are MCM and m, as labelled on the dashboard.
- **Dates:** `source_date` stays date-only (C3), with no time of day invented. The newest row per reservoir is used.
- **Zero inflow** (recorded in `reservoir_coupling.status`) when the snapshot is:
  - missing: `zero_inflow_missing_snapshot`;
  - unparseable: `zero_inflow_unparseable_snapshot`;
  - stale: `zero_inflow_stale_snapshot: …`, when the newest `source_date` is more than 2 calendar days before the run date, or the snapshot was received more than 48 h before `run_time`.
- **Recorded on every forecast run:** forecast-mode runs record the coupling even without a snapshot.
- **Explicit what-if releases** override the rule for that reservoir.
- **Provenance:**
  - `reservoir_coupling` holds the rule id, parameters, per-reservoir rows, `snapshot_sha256`, `snapshot_source_date` and `snapshot_received_at`.
  - Inputs gain `reservoir_snapshot` (PUBLISHED_SNAPSHOT) and `reservoir_outlet_inflow` (SCENARIO_INPUT, "ASSUMPTION; not an observed release").
  - Raw dashboard responses are not retained; only the hash is kept.

## Call for B51

```python
doc = run_scenario(static_root, runs_root, mode="forecast", duration_hours=72, device="cuda",
                   reservoir_snapshot=cfm_body,      # B44 /reservoirs/history body (or list of records); None -> zero inflow
                   run_time=cycle_time_utc,           # reference for staleness
                   forecast_model=None,               # default ECMWF IFS (first usable); or "ensemble_mean"
                   fetch_forecast=None)               # default A23 lattice fetcher; B51 may pass its cached snapshot
```

## Forecast forcing checks (`doc["forecast_check"]`)

- **Valid times:** Open-Meteo hourly values are labelled by interval end, so the simulation starts one hour before the first forecast label. Frame k is at start + k × frame interval.
- **Units:** mm per 1-hour interval (mm/h). Forecast horizon 72 h, after discarding 24 spin-up past hours. A request longer than the horizon is refused.
- **Model coverage:** every usable model is mapped to the 120 m grid by nearest native cell, reporting distinct native cells, `active_cell_coverage` (must be 1.0), the domain-mean 72 h total and the response hash. Models with missing hours are excluded and listed, never zero-filled.
- **Fetch time:** `fetched_at` is recorded, separate from valid times.
- **Memory:** `forcing.map_to_grid` is now chunked, giving bounded memory on 30–120 m grids with identical output.

## Live-style sanity check

Run time 2026-11-10T04:33Z. One Open-Meteo lattice fetch (3 models, `fetched_at` 2026-11-10T04:33:48Z) and one on-demand CFM-DSS read (snapshot `source_date` 2026-11-10) are reused for every run. Results: `data/features/simulation/a28_live_check_v1/summary.json`.

| Check | Result |
|---|---|
| Forecast forcing | Valid 2026-11-10T04:00Z → 2026-11-13T03:00Z (72 h), simulation start 03:00Z, mm/h. Domain-mean 72 h total: ECMWF IFS 0.5 mm (used), UKMO 0.95 mm, ICON 0.0 mm. All three models have active-cell coverage 1.0. |
| Reservoir coupling | Status `applied`. Storage: Chembarambakkam 38.7%, Poondi 18.1%, Puzhal 73.5%, Cholavaram 15.1%, all below 90%, so every assumed outlet inflow is 0 m³/s. |
| Live run, CPU (`sim-20261110T043354Z-f8940308`) | 72 h, 145 frames, 13,824 steps, mass balance 1e-6, depths finite and non-negative. Flooded area (≥ 0.10 m) 0.014 km², 0 buildings, 0 wards affected: plausible for 0.5 mm of rain. |
| Live run, CUDA (`sim-20261110T043629Z-f8940308`) | Same steps and summary; peak grid identical to CPU at 0.01 m rounding; `kernel_mode` cuda_graph |
| No-rain, no-inflow control (`sim-20261110T043751Z-965abe99`) | **Near-dry: flooded area 0.014 km², below the documented threshold of 1 km²** (cells ≥ 0.10 m, permanent water excluded). 15 cells ≥ 0.01 m, all coastal cells below MSL filled from the sea boundary (net 2.36 × 10⁵ m³ in). Mass balance 5e-6. The live run's single flooded cell is this same coastal cell. |

**72 h timing** (citywide 120 m, 440 × 343 grid, 145 frames):

| Device | Setup | Device init | Solve | Post-processing | Total |
|---|---:|---:|---:|---:|---:|
| CPU (NumPy, 8 threads) | 0.9 s | — | 148.8 s | 4.8 s | 154.6 s |
| CUDA (RTX 3050, CUDA graph) | 0.9 s | 4.2 s | 9.4 s | 3.8 s | 18.3 s |

**Mass-balance definition fix:** the relative error now divides by rain + inflow + net water entering from the sea boundary, so the error stays finite when rain and inflow are zero. Previously the zero-input control reported 1.1e9. Values for runs with rain are unchanged in practice.

## Limitations

- Release magnitudes (Q_ctrl, the 90% threshold and the spill factor) are assumptions, not operating rules. Real gate operations are not public.
- A single constant inflow is applied per run, with no routing through the reservoir and no inflow forecast for the reservoir catchment.
- Puzhal, Poondi and Cholavaram all enter the Kosasthalaiyar at nearby inlet cells.
