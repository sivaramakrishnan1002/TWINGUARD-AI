# Phase 9C lineage

This Lane A output uses the existing Phase 9 target and Phase 9B feature table without modifying either. The OpenCity point observations are read only and are used solely for the separate cross-check.

## Inputs

| Input | Role | Recorded SHA-256 |
|---|---|---|
| `data/features/static/cell_table_phase9b_v2.parquet` | Static predictors and 30 m cell index | `c54c21d8145adde7600d817169b80ebe2d936ce7edae59e2248e40a8280dbf86` |
| Existing Phase 9 target table | Unchanged November 2015 SAR-derived label | `f580f02a7626c2dbad329420d08176d8d19cd126e231846d2fa2c1b690b78052` |
| `docs/PHASE9B_METRICS.json` | Prior model comparison | `2bcd1ca955ae344d1846d34e73f0d4b8645c2bbaa97e9d1807cbfad8b695684a` |
| `data/raw/historical_floods/2015/opencity_flood_points/814ca028-4c84-4bd0-aa67-6dbaeb9b6ba5.kml` | OpenCity approximate observed-flood points | Source file name retained; raw audit verifies current bytes |
| `data/raw/historical_floods/2015/opencity_flood_points/93d2905a-a580-482d-96b0-4d9ccf5273ef.kml` | OpenCity approximate observed-flood points | Source file name retained; raw audit verifies current bytes |
| Existing Phase 9B v2 raster features and SAR quality masks | Observability criteria and feature grid | Paths and checksums are recorded in the metrics JSON where available |

## Transformations and outputs

`pipelines/phase9c/urban_censoring.py` constructs the observability mask, fits the same nested spatial CV model on observable cells, calibrates built-up-stratified spatial Mondrian bands, creates apparent full-data raster layers, and independently summarizes OpenCity points against the apparent rank surfaces. All raster output files live under `data/features/predictions/phase9c/`, a new output directory. JSON metrics and model settings are in `docs/PHASE9C_METRICS.json` and `docs/PHASE9C_MODEL_REGISTRY.json`; the interpretation is in `docs/PHASE9C_URBAN_CENSORING.md` and `docs/MODEL_CARD_SUSCEPTIBILITY.md`.

Reproduce the model and outputs with:

```powershell
.venv\Scripts\python.exe pipelines\phase9c\urban_censoring.py --configs 30 --bootstrap-reps 200
```

Refresh only the point cross-check, without fitting or rewriting the rasters, with:

```powershell
.venv\Scripts\python.exe pipelines\phase9c\urban_censoring.py --points-only
```

The metrics JSON includes the runtime, random seed, source hashes, masks, fold metrics, baseline comparisons, point counts and confidence intervals. The raw-data audit is separate evidence; no files under `data/raw/` were modified.
