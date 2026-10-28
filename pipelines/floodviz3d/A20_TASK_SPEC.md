# A20 task specification — 3D scenario data readiness

## Scope

Create an offline, versioned index of already-produced A05 forecast/hindcast depth snapshots and A06 simulation summary rasters. Do not rerun either model, alter source rasters, resample, or write values for unsaved times. The new index is intended to let a later renderer locate the existing 600 m values.

## Required audit

- Record scenario/event identity, UTC time semantics, CRS, affine grid, pixel spacing, units, NoData meaning and coverage, ensemble semantics, provenance, and SHA-256 hashes for source summaries, declared inputs, and indexed outputs.
- Use one reproducible A05 subset: the `perfect_foresight_imerg` hindcast for all three event windows, at the five actually saved lead times (6, 12, 24, 48, and 72 hours), with p05/p50/p95 files. These are parameter-member summaries, not calibrated uncertainty bounds.
- Index A06 selected-hour and event-peak products as separate context layers. A selected-hour product has the exact global selected UTC time from its recorded zero-based hour index. Per-cell peak products have no single valid instant and must have `valid_time_utc: null`.
- Keep every source layer on its existing 600 m EPSG:32644 grid. No interpolation, upscaling, street-level rendering data, or fabricated building water levels.

## Files and verification

- `pipelines/floodviz3d/build_manifest.py`: deterministic manifest builder and validator; refuse overwrite.
- `pipelines/floodviz3d/manifest.schema.json`: machine-readable manifest schema.
- `data/features/visualization3d/batch2_v1/manifest.json`: generated index only, referencing existing raster files.
- `tests/visualization3d/`: validation and non-invention tests.
- `docs/FLOOD_3D_SCENARIO_READINESS.md`: audit findings, limitations, runtime/tool check, and reproduction command.

All results remain DERIVED assumption-based research scenarios, not observed water, validated hydraulic truth, operational forecasts, safe evacuation guidance, or emergency advice. Presentation-only animation between snapshots must not change numeric depth values or imply finer model resolution.
