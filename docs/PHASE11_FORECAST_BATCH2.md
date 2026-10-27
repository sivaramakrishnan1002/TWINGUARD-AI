# Phase 11 — Batch 2 forecast and hindcast scenarios

> **DERIVED scenario output; not operational forecast skill, observed flood depth, or validated hydraulic truth.** Archived NWP forecast fields were not available for the 2015 event. Perfect-foresight rainfall uses the observed IMERG daily values, so it cannot measure how a real forecast would have performed.

## Method and scope

The A06 NumPy solver was run for three 72-hour UTC event windows and five rainfall scenarios per window. Each scenario used all 20 existing A06 parameter members, without changing their parameters or the Phase 12 outputs. The simulation grid is 600 m, EPSG:32644, with 2,430 eligible cells. Depth snapshots are saved at elapsed hours 6, 12, 24, 48, and 72. New rasters and member arrays are under `data/features/forecast/batch2_v1/`; A06 source layers and prior simulation products were not modified.

| Event window (UTC) | Context and limitation |
|---|---|
| 2015-11-30 to 2015-12-02 | Includes the 1 Dec IMERG peak. There is no accepted official vector extent for the 1–8 Dec peak. November UNOSAT extents do not validate these forecasts or hourly depths. |
| 2021-11-11 to 2021-11-13 | The 13 Nov NRSC reference is a PDF, not an accepted georeferenced raster. |
| 2023-12-02 to 2023-12-04 | The available 7 Dec NDEM map is preliminary and not an accepted raster reference. |

`perfect_foresight_imerg` distributes each observed daily CMA-mean IMERG value across that UTC day using the ERA5 hourly shape, scaled so the 24 hourly values sum to the IMERG value. This is a hindsight forcing, not an hourly IMERG observation or forecast. `rain_error_q10/q50/q90` add the corresponding empirical quantile of matched-day ERA5-minus-IMERG daily differences to each IMERG day, clipping negative rainfall at zero. These are product-disagreement scenarios, not forecast-error distributions calibrated against archived forecasts. The matched-day residual quantiles were q10 **-25.544**, q50 **0.466**, and q90 **12.851 mm/day**. `persistence_previous_day` repeats the previous UTC day's ERA5-shaped/IMERG-scaled hourly pattern for all three days.

## Simulated scenario summaries

Each entry below reports ensemble-mean depth over eligible cells, area whose ensemble-mean depth is at least 0.10 m, and area at least 0.30 m. The raster outputs also retain member depths and cellwise p05/p50/p95. Areas are approximate because they use the 600 m grid and its CMA boundary rule; they are not mapped flood observations.

| Event | Rainfall scenario | Rainfall total (mm/72 h) | 24 h mean depth (m) | 24 h area ≥0.10 m (km²) | 72 h mean depth (m) | 72 h area ≥0.10 m (km²) | 72 h area ≥0.30 m (km²) |
|---|---|---:|---:|---:|---:|---:|---:|
| 2015 | Perfect-foresight IMERG | 351.54 | 0.0215 | 50.40 | 0.0418 | 59.76 | 36.00 |
| 2015 | Rain difference q10 | 274.91 | 0.0086 | 12.24 | 0.0340 | 54.36 | 33.84 |
| 2015 | Rain difference q50 | 352.94 | 0.0216 | 51.12 | 0.0420 | 60.12 | 36.36 |
| 2015 | Rain difference q90 | 390.09 | 0.0274 | 70.20 | 0.0457 | 66.60 | 37.08 |
| 2015 | Previous-day persistence | 31.87 | 0.0010 | 0.36 | 0.0026 | 5.40 | 0.00 |
| 2021 | Perfect-foresight IMERG | 22.27 | 0.0035 | 6.48 | 0.0021 | 4.68 | 0.00 |
| 2021 | Rain difference q10 | 0.00 | 0.0000 | 0.00 | 0.0000 | 0.00 | 0.00 |
| 2021 | Rain difference q50 | 23.67 | 0.0036 | 7.20 | 0.0023 | 6.48 | 0.00 |
| 2021 | Rain difference q90 | 60.82 | 0.0076 | 22.68 | 0.0126 | 29.52 | 8.28 |
| 2021 | Previous-day persistence | 313.95 | 0.0415 | 90.36 | 0.0601 | 108.00 | 43.56 |
| 2023 | Perfect-foresight IMERG | 279.07 | 0.0058 | 6.48 | 0.0480 | 86.76 | 41.04 |
| 2023 | Rain difference q10 | 204.33 | 0.0000 | 0.00 | 0.0424 | 79.56 | 39.24 |
| 2023 | Rain difference q50 | 280.47 | 0.0060 | 7.56 | 0.0481 | 86.76 | 41.04 |
| 2023 | Rain difference q90 | 317.63 | 0.0117 | 20.16 | 0.0507 | 90.72 | 41.76 |
| 2023 | Previous-day persistence | 7.55 | 0.0000 | 0.00 | 0.0000 | 0.00 | 0.00 |

Rainfall sensitivity is visible: for example, 2015 q10–q90 72-hour area at the 0.10 m ensemble-mean cut varies from 54.36 to 66.60 km². The persistence contrast is especially large for 2021 because the preceding day was wet; it is a simple baseline, not a plausible issued forecast. Depth can rise and then recede between horizons under the solver's infiltration, drainage and boundary assumptions.

## Validation and reproducibility

- No archived NWP forecasts are present for 2015; no operational forecast-skill metric can therefore be computed.
- There are no observed depth series at the selected lead times. The Nov 2015 UNOSAT maps show extents on 12 and 24 Nov, not these event windows or hourly depths. The 2021 PDF and preliminary 2023 PDF are not accepted raster references. No comparison is presented as independent validation.
- A06's documented assumptions remain in force: 600 m aggregation, surface-model DEM, land-cover-based roughness/infiltration, simplified mapped-waterway/open-water boundaries, and no storm-drain network, external catchment inflow, or street-scale hydraulics. The member quantiles express parameter spread only; they are not calibrated confidence intervals.
- Reproduce with `.venv\Scripts\python.exe -m pipelines.phase11.run`. Fixed A06 seed: `20261021`; NumPy CPU execution; CUDA was unavailable (`torch.cuda.is_available() == False`; `nvidia-smi` was permission-blocked). Runtime: **687.71 seconds** for 300 solver runs (3 events × 5 scenarios × 20 members), plus raster/summary writing.
- Focused check: `.venv\Scripts\python.exe -m pytest tests\phase11 -q` — **5 passed** (the combined A05/A12/A06 focused run passed **13**). Run integrity checks also required finite, nonnegative depth and mass-balance relative error ≤1% for each member; all 300 completed, with maximum relative mass-balance error **0.591%**. Raster inspection confirmed 225 GeoTIFFs, EPSG:32644, 600 m pixels, float32 values, and `-9999` NoData outside the 2,430 eligible cells.
- Summary, exact input hashes, per-member diagnostics, rainfall arrays and all horizon summaries: `data/features/forecast/batch2_v1/forecast_summary.json` (ignored generated data; do not commit).

This task supplies simulated scenario ensembles for downstream prototype tasks. It does **not** establish an operational warning capability, event-specific flood accuracy, or measured uncertainty coverage.
