# A20 — 3D scenario data readiness

> **DERIVED, assumption-based research scenario.** This package is not observed water, validated hydraulic truth, a live prediction, safe evacuation guidance, or emergency advice.

## Finding

The existing products can support a regional 3D *presentation* of saved coarse scenarios. They do not support street-scale flow. The created `data/features/visualization3d/batch2_v1/manifest.json` is a deterministic index to the existing rasters; it does not copy, resample, interpolate, or edit them.

The indexed A05 subset is the reproducible `perfect_foresight_imerg` scenario for three windows: 2015-11-30 00:00 through 2015-12-02 23:00 UTC; 2021-11-11 00:00 through 2021-11-13 23:00 UTC; and 2023-12-02 00:00 through 2023-12-04 23:00 UTC. A05 actually saved depth rasters at leads 6, 12, 24, 48 and 72 hours. The exact valid time is the window start plus the saved lead: the 72-hour state is at the exclusive boundary (for example, 2015-12-03 00:00 UTC), after the final hourly model update. It is not an extra observation at the event-window end. Three per-cell parameter-member bands (p05/p50/p95) give 45 referenced rasters across the 15 saved times. The p05/p95 values are parameter spread, not calibrated statistical uncertainty or confidence coverage.

A06 is indexed separately as temporal context, not mixed into the December time series. Its selected-hour layers have these saved global selected times: 2015-11-13 00:00 UTC (zero-based hour index 71) and 2015-11-23 13:00 UTC (index 36). Its per-cell peak layers combine each cell's maximum over the 72-hour run; there is no single valid instant, so the manifest records `valid_time_utc: null` for them. The two event dates each have selected and peak mean/p05/p95 products (12 rasters total).

## Spatial and value audit

| Property | Verified result |
|---|---|
| CRS and grid | EPSG:32644; 69 columns × 88 rows; 600 m square pixels; affine transform `[600, 0, 390000, 0, -600, 1471620]`. |
| Data type and depth units | One float32 band. The Phase 11/12 reports describe values in metres; the inspected TIFF band unit metadata is unset. The manifest records both facts. |
| Coverage | Each indexed A05 raster has 2,430 valid cells and 3,642 NoData cells out of 6,072 grid cells; p05/p50/p95 masks agree. A06 indexed layers also retain the saved grid/coverage. |
| NoData meaning | `-9999`; outside the assessed/modelled coverage or otherwise unmodelled. It means unknown coverage, not dry. The manifest points to the original mask-bearing rasters. |
| A05 output semantics | 20 A06 parameter members per event/scenario. Rainfall uses observed daily IMERG spread with an ERA5 hourly shape: hindsight scenario forcing, not an archived forecast, and not native hourly IMERG. |
| A06 output semantics | Assumption-based NumPy local-inertial pilot; selected and per-cell peak summaries over parameter members. Spread is not calibrated confidence. |

All 7 A05 declared input hashes and all 6 A06 declared input hashes matched the current files. Summary SHA-256: A05 `0bc0e322041c0d264a214d995912fd648fbda3534616f3e4588122e292e94dba`; A06 `58f736b54a4b4971fcade55f653cc6d86867c66eec612b16d184d9c93f365697`. Every referenced output raster is also SHA-256 recorded in the manifest and checked by the validator.

## Visualization limits

- The 600 m source grid and NoData coverage must remain visible as such. Do not upscale the quantitative layer into invented street-level detail or create water levels on buildings.
- A05 horizons are unevenly spaced (6, 12, 24, 48, 72 hours), not a regular six-hour sequence. A06 provides selected-hour and event-peak summaries, not a continuous depth time series.
- Any smooth animation between saved snapshots is presentation-only. It must not change numerical values or imply finer spatial or temporal model resolution.
- GLO-30 is a surface model with building/vegetation returns, not a bare-earth DEM or building DSM. No building inundation elevations are available.
- The rainfall forcing, routing/drainage simplifications, and hydraulic behavior are not independently validated. The outputs are not emergency advice or safe-route evidence.

## Reproduction and checks

```powershell
.venv\Scripts\python.exe -m pipelines.floodviz3d.build_manifest
.venv\Scripts\python.exe -m pipelines.floodviz3d.build_manifest --check data\features\visualization3d\batch2_v1\manifest.json
.venv\Scripts\python.exe -m pytest tests\visualization3d -q
```

The generator refuses to overwrite an existing manifest. The deterministic validator checks scenario IDs, exact UTC valid times, grid/CRS, units, NoData/coverage, band/member semantics, provenance hashes, and explicit null timing for per-cell peaks. It uses project-native validation because `jsonschema` is not installed in the venv; no packages were installed.

GPU check: PyTorch `2.14.1+cu126` was importable, `torch.cuda.is_available()` returned false, and `nvidia-smi` failed with a Windows permissions message. Manifest generation is I/O and metadata work, not a useful GPU workload; it ran on CPU. No numerical solver was changed or rerun.

Final checks on this A20 change:

- `.venv\Scripts\python.exe -m py_compile pipelines\floodviz3d\build_manifest.py` — passed.
- `.venv\Scripts\python.exe -m pipelines.floodviz3d.build_manifest --check data\features\visualization3d\batch2_v1\manifest.json` — passed; 3 event series, 45 saved-time raster references, 4 A06 context groups; source hashes, raster hashes, grid metadata, band type and coverage verified.
- `.venv\Scripts\python.exe -m pytest tests\visualization3d -q` — 5 passed.
- `.venv\Scripts\python.exe -m pytest tests\visualization3d tests\phase8 tests\phase9 tests\phase9b tests\phase9c tests\phase10 tests\phase11 tests\phase12 tests\phase13 tests\routing tests\decision tests\explainability tests\labels tests\temporal_models -q` — 121 passed, 0 failed.
- `.venv\Scripts\python.exe tools\audit_raw_logs.py` — 157 files / 30,544,672,450 bytes; 157 hash matches; zero missing comparable hashes and zero mismatches.
