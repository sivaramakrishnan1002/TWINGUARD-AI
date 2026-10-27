# A18 — T6 GeoTIFF metadata conformance repair

## Result

The six original T6 TIFFs under `data/features/depth/batch1_v1/` were read-only inspected. They are one-band Float32 rasters, EPSG:32644, 30 m, NoData `-9999.0`, and `AREA_OR_POINT=Area`. Their arrays and masks were copied without resampling into the separate `data/features/depth/c1_metadata_repair_v0/` directory. The originals were not changed.

The new copies add explicit band roles, units, CRS/grid, NoData, source tier and feature count, method, uncertainty rule, DEM caveat, version/status, and time metadata. Event date is a date only. `run_time_utc` preserves the T6 generation time recorded in the original tags and summary. The source contains no acquisition instant; the GeoTIFF says `UNKNOWN; serialize as JSON null`, and the sidecar stores JSON `null`. No acquisition time was inferred.

The `p05` and `p95` filenames remain for compatibility. Their semantic roles are `lower_assumption_bound_m` and `upper_assumption_bound_m`; they encode `max(0, mean - 4 m)` and `mean + 4 m`, respectively. These are assumption bounds, not calibrated statistical percentiles or probability coverage.

## Validation and provenance

`metadata_repair_manifest.json` records per-file source and output SHA-256, valid and NoData pixel counts, the tags, and exact cell/mask equality checks. Tests reopen all six output TIFFs and verify the spatial contract, tags, event/time meanings, and unchanged pixel data and masks. Running the script refuses a non-empty destination directory.

Run with:

```powershell
.\.venv\Scripts\python.exe pipelines\phase8\repair_depth_metadata.py
```

The copies remain **DERIVED, assumption-based and unvalidated depth proxies**, not observed depth and not approved routing inputs. The DEM is the Copernicus GLO-30 surface model, so buildings and vegetation remain in the elevation values. This file-level repair does not freeze the shared C1 contract.
