# Phase 12 — local-inertial simulation pilot

> **DERIVED, assumption-based simulation. Not observed flood depth, field-validated, or operational guidance.** The November UNOSAT outlines are map extents used for calibration. Reproducing their spatial pattern does not establish hydraulic accuracy.

## Result

The NumPy local-inertial solver ran two 72-hour November 2015 scenarios with 20 parameter members each. It writes 600 m depth summaries and keeps NoData where the coarse model has no eligible land cell. The uncertainty bands show parameter spread only; they are not calibrated confidence intervals.

| Event map date | 72 h IMERG total with ERA5 hourly shape (mm) | Coarse label prevalence | Training-fold median depth threshold | ROC-AUC mean ± SD | PR-AUC mean ± SD | Brier mean ± SD | ECE mean ± SD | F1 mean ± SD | IoU mean ± SD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2015-11-12 | 86.381 | 6.89% (fold mean) | 0.05 m | 0.673 ± 0.045 | 0.143 ± 0.043 | 0.064 ± 0.019 | 0.029 ± 0.019 | 0.214 ± 0.085 | 0.122 ± 0.052 |
| 2015-11-24 | 66.700 | 8.27% (fold mean) | 0.01 m | 0.698 ± 0.018 | 0.169 ± 0.057 | 0.078 ± 0.015 | 0.042 ± 0.046 | 0.241 ± 0.077 | 0.139 ± 0.048 |

Metrics average the five held-out block folds; the listed SD is the fold-to-fold sample SD. In each fold, one parameter member and a depth threshold were selected by training-block IoU; isotonic calibration was fitted on training-block depths and labels only. PR-AUC and ROC-AUC use those calibrated probabilities. The probability calibration does not turn the physical simulation into a validated flood-probability model. Per-fold member choices, thresholds, metrics, rainfall arrays and mass-balance records are in `data/features/simulation/batch2_v1/selected_model_spatialcv.json` and `simulation_summary.json`. `calibrated_metrics_spatialcv.json` is retained as an all-member diagnostic, not the primary selected-model result.

### Spatial and area checks

The eligible 30 m source table has 1,196,300 cells after the documented permanent-water/label eligibility masks. Aggregation to 600 m leaves 2,430 eligible model cells with cleaned DEM and usable label coverage. Of 3,338 coarse CMA-intersecting cells, 908 are represented as open-water/channel drain boundaries and therefore remain NoData in the depth rasters. A coarse cell is included when at least 10% of its 30 m subcells intersect the CMA. This boundary-cell rule makes area estimates approximate.

To compare coarse output with the source outlines, a coarse label cell is positive when at least 10% of its eligible 30 m subcells are mapped flooded. This produces 174 positive coarse cells (62.64 km²) for 12 November and 209 (75.24 km²) for 24 November. The underlying eligible 30 m UNOSAT-positive areas are 28.74 km² and 37.93 km², respectively. This difference is a consequence of the coarse binary-cell rule; do not cite the coarse areas as replacement UNOSAT areas.

Predicted peak extent is sensitive to the chosen depth cut-point:

| Event | 0.01 m | 0.03 m | 0.05 m | 0.10 m | 0.15 m | 0.30 m | 0.50 m | Training-fold median |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 12 Nov predicted area (km²) | 363.96 | 204.48 | 126.72 | 63.36 | 38.88 | 14.40 | 2.88 | 0.05 m |
| 24 Nov predicted area (km²) | 282.60 | 119.16 | 69.84 | 37.08 | 24.12 | 10.08 | 1.44 | 0.01 m |

The low selected thresholds and area sensitivity show that the simulated depths do not reproduce the mapped extent robustly. The 12 November thresholded area is larger than the eligible 30 m outline area; the 24 November cut-point is only 1 cm. These are calibration results, not evidence that either threshold is physically correct.

## Inputs, resolution, and timing

- Cleaned DEM: `data/processed/terrain_cleaned/cleaned_elevation_m.tif`, EPSG:32644. The source is Copernicus GLO-30, a surface model with vegetation/building returns, not bare earth or a building DSM.
- Land cover: `data/features/landcover/worldcover_2021_class.tif`; named waterways: `data/features/hydrology/chennai_waterways.gpkg`.
- Event masks: `data/features/predictions/labels_nov2015.parquet`, using `target_2015_11_12` and `target_2015_11_24` with `eligible_for_model`.
- Rainfall: 72 UTC hours ending on each map date. The existing CMA-mean IMERG daily value is distributed over the corresponding 24 hours according to the nine-point ERA5 mean hourly profile, scaled to preserve that daily IMERG total. ERA5 is in millimetres and its timestamps were converted to UTC; IMERG is a daily UTC product in mm/day. This produces an ERA5-shaped hourly scenario from daily IMERG totals; it is not native hourly IMERG and has no sub-grid spatial variation.
- Runtime: a 72-hour, one-member 600 m pilot took 1.49 s; all 40 event/member runs took **68.03 s**. A 600 m cell aggregates 20 × 20 native cells (400 cells); using 30 m would require roughly 400 times the spatial cells and a smaller stable step. The 600 m grid is selected to keep the 40-run calibration practical. It cannot resolve street, parcel, culvert, or neighborhood-scale flow.

## Model assumptions

The face discharge follows a local-inertial update with gravity-wave stability steps. A face outflow limiter prevents a dry cell from exporting more water than its available storage. No-flow is used at the outer/CMA land boundary. WorldCover open-water cells and rasterized mapped waterway corridors are zero-stage free-draining sinks; interior water classes are not separated into sea, lake, and river stages. This can over-drain water near the simplified boundary and excludes external catchment inflow.

| WorldCover class | Manning n | Infiltration assumption (mm/hour) |
|---|---:|---:|
| Tree cover (10) | 0.12 | 1.4 |
| Shrubland (20) | 0.10 | 1.2 |
| Grassland (30) | 0.035 | 1.0 |
| Cropland (40) | 0.08 | 1.4 |
| Built-up (50) | 0.06 | 0.25 |
| Bare/sparse vegetation (60) | 0.03 | 0.4 |
| Snow/ice (70) | 0.035 | 0.5 |
| Permanent water (80) | 0.03 | 0.0 |
| Herbaceous wetland (90) | 0.08 | 0.8 |
| Mangroves (95) | 0.10 | 0.8 |
| Moss/lichen (100) | 0.04 | 0.5 |

These are explicit scenario defaults, not locally measured parameters. The 20-member ensemble varies Manning n by 0.75, 1, 1.25, 1.5, or 2 times and infiltration by 0.5, 0.75, 1, or 1.5 times. Built-up coarse cells with at least 50% built-up cover use 0.70 plan-area porosity. Buildings are not treated as elevated obstacles. No separate land-cover storm-drain loss rate is imposed: it is set to zero because no storm-drain network or throughput data are available. Flow can drain only through mapped open-water/channel sinks.

The two event maps calibrate parameters/thresholds on training blocks only. Five spatial folds use whole 3 km block IDs; cells within 3 km of each held-out fold are excluded from training. The fold assignments and 20-member parameter list are fixed by seed `20261026`. The CAG reservoir figure was not used; no observed release hydrograph is available.

## Cross-checks

| Cross-check | 12 Nov simulation | 24 Nov simulation | Meaning |
|---|---:|---:|---|
| GFD event 4309 flooded area on comparable model cells | 17.28 km² | 17.28 km² | GFD spans 10 Nov–4 Dec and is a coarse event cross-check, not date-specific truth. |
| Simulated area at training-fold threshold | 126.72 km² | 282.60 km² | Much larger than the GFD mapped overlap area. |
| GFD overlap / IoU | 6.84 km² / 0.050 | 11.52 km² / 0.040 | Poor coarse overlap; grid and date differences limit interpretation. |
| OpenCity points inside assessed grid | 740 of 945 | 740 of 945 | 205 points fell outside model coverage or in NoData. Dates are unclear and locations approximate. |
| OpenCity points in simulated extent | 93/740 (12.6%) | 255/740 (34.5%) | Spatial hit shares only; not event accuracy or independent depth validation. |

No accepted A03d out-of-event map is available for comparison: the 2021 NRSC CRS conflict remains unresolved and the 2023 product is preliminary/unaccepted. The SAR-derived candidates remain Tier D and are not used as labels.

## Numerical checks and outputs

All 40 runs remained finite and non-negative. The largest recorded relative mass-balance error was **0.264%** for 12 November and **0.203%** for 24 November, both below the 1% criterion. Each member used 1,359–1,569 steps for 12 November and 1,982–2,262 for 24 November. The complete ensemble run took 68.03 seconds on CPU.

New outputs are in `data/features/simulation/batch2_v1/`:

- `depth_{selected,peak}_{mean,p05,p95}_YYYY-MM-DD_DERIVED.tif` — 12 GeoTIFFs, 600 m, EPSG:32644, metres, −9999 NoData. “Selected” is the hour of maximum ensemble-mean stored water; “peak” is each member’s per-cell maximum during 72 hours. p05/p95 are parameter-member percentiles, not calibrated probability coverage.
- `member_peak_depth_YYYY-MM-DD_DERIVED.npz` — 20 member peak arrays per event.
- `simulation_summary.json` — assumptions, source hashes, rainfall sequences, member records and fold results.
- `selected_model_spatialcv.json` — training-only member, depth-threshold and isotonic calibration selection, followed by held-out fold metrics.
- `calibrated_metrics_spatialcv.json` — retained diagnostic that scores each member separately rather than selecting one on training folds.
- `validation_summary_selected_model.json` — GFD and OpenCity cross-checks for the apparent ensemble maps. `validation_summary.json` preserves the earlier cross-check run; the thresholds are the same, but use the selected-model file for provenance.

The output is DERIVED and coarse. It does not have surveyed channel geometry/stages, storm drains, external catchment inflow, depth observations, a validated rainfall field, or enough independent events to claim hydraulic accuracy. Do not use these rasters for routing or public safety decisions.

## Reproduction and checks

Commands run:

```powershell
.venv\Scripts\python.exe -m pipelines.phase12.simulate
.venv\Scripts\python.exe -m pipelines.phase12.recalibrate_outputs
.venv\Scripts\python.exe -m pipelines.phase12.select_fold_models
.venv\Scripts\python.exe -m pipelines.phase12.validate
.venv\Scripts\python.exe -m pytest tests\phase12 -q
```

The required NumPy solver ran on CPU. CUDA 12.6 and PyTorch 2.14.1+cu126 were available on the RTX 3050 Laptop GPU, but the solver is specified as NumPy; changing it to Torch would be a different numerical implementation and was not necessary for the measured 68-second run. No package was installed.

### Closeout checks

| Command | Result |
|---|---|
| `.venv\Scripts\python.exe -m py_compile pipelines\phase12\simulate.py pipelines\phase12\validate.py pipelines\phase12\recalibrate_outputs.py pipelines\phase12\select_fold_models.py` | Passed. |
| `.venv\Scripts\python.exe -m pytest tests\phase12 -q` | 5 passed. |
| `.venv\Scripts\python.exe -m pytest tests\labels tests\phase8 tests\phase9 tests\phase9b tests\phase9c tests\phase10 tests\phase12 -q` | 74 passed. |
| `.venv\Scripts\python.exe tools\audit_raw_logs.py` | `DATA_FILES=157; DATA_BYTES=30544672450; HASH_MATCH=157; NO_COMPARABLE_HASH=0; MISMATCH=0`. Raw data hashes match the logs. |

The `simulate.py` command and separate calibrated/validation commands listed above produced the versioned outputs. Nothing was written under `data/raw/`. Lane A progress and commit status are recorded in `docs/batches/BATCH_2_PROGRESS.md` after commit.

## Implementation fixes during this task

- The first full-run attempt stopped with `RuntimeError: local-inertial stability step below one second: 0.6524809268870229`. The value was the final fractional-second remainder of a 1-hour forcing interval, not the computed stable step. The loop now checks the stable limit separately and accepts a smaller final remainder; the full run then completed.
- The first focused test run had one test-construction failure: `TypeError: step() got an unexpected keyword argument 'rainfall_m_s'`. The test now uses the solver argument `rain_m_s`; the solver code did not need a change for that failure.
- The initial held-out diagnostic averaged metrics across all 20 members and mapped normalized depth directly to a score. That was not the calibrated model-selection protocol. `selected_model_spatialcv.json` now selects the member and threshold on training blocks, fits isotonic calibration on training blocks, and evaluates that choice on held-out blocks. The table above uses the corrected results. The all-member diagnostic JSON remains separately identified.
