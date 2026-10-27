# Depth-field contract — Batch 1 v1

## Meaning and limits

These rasters are **DERIVED, assumption-based depth estimates**, not measured depths. They are made only for the accepted tier A UNOSAT event extents for 12 and 24 November 2015. The input labels describe flood extent, not water depth. Do not describe the depth fields as observed or validated, and do not use them as operational routing thresholds without separate validation.

Within each 8-connected rasterized flood component, the method estimates a local flat water surface as the median cleaned-DEM elevation among boundary pixels of that component. Depth is `max(0, estimated component water surface − cleaned DEM)` for extent pixels with a valid DEM value. A component of one pixel has that same pixel as its edge and therefore gets zero estimated depth. This is a simple geometric proxy; it does not solve hydraulic flow or enforce connected water-surface continuity between components.

The cleaned Copernicus GLO-30 is a digital surface model containing building and vegetation returns, not a bare-earth terrain model. Urban depths and other surface artifacts are unreliable. The DEM contains NoData over much of the mapped extent; those cells remain NoData in all depth bands rather than being treated as dry or as zero depth.

## Uncertainty assumption

The default allowance is **±4 m**, labelled `DEFAULT_TO_CONFIRM`. For each valid mean estimate `d`, the lower layer is `max(0, d − 4 m)` and the upper layer is `d + 4 m`. These `p05` and `p95` names satisfy the downstream field contract but the values are **not calibrated statistical 5th and 95th percentiles**. The ±4 m allowance is not measured in the local study area and has not been tested against held-out depth observations. No event-matched point-depth truth is available, so coverage cannot be measured. Treat the band as a conservative placeholder assumption, not a probabilistic guarantee.

## File contract

| Field | Contract |
|---|---|
| Directory | `data/features/depth/batch1_v1/` |
| File names | `depth_mean_YYYY-MM-DD_UNOSAT_A_DERIVED.tif`, `depth_p05_YYYY-MM-DD_UNOSAT_A_DERIVED.tif`, `depth_p95_YYYY-MM-DD_UNOSAT_A_DERIVED.tif` |
| Dates available | 2015-11-12 and 2015-11-24 |
| Source | `labels.v_usable_flood_labels`, tier A official UNOSAT event extent intersected with the CMA |
| Units / data type | metres / Float32 |
| CRS / grid | EPSG:32644; 30 m CMA master grid, aligned with `data/processed/grid/cma_mask.tif` and the cleaned DEM |
| NoData | −9999 outside extent and wherever cleaned DEM elevation is missing; consumers must preserve it as missing, not zero |
| Valid time | Source event/map date (`event_date` tag) |
| Processing time | `run_time_utc` tag in each TIFF |
| Version/status | `batch1-depth-v1`, `DERIVED_ASSUMPTION_NOT_OBSERVED` |
| Provenance tags | event date, source view/tier, component-edge method, uncertainty assumption, DEM caveat, CRS/grid, run time, version and source feature count |

### Explicit serialization and time semantics (G0 C1 repair proposal)

This section clarifies the existing `batch1-depth-v1` files; it does not change or regenerate them, change their version, or freeze the shared C1 contract.

- **Container and grid:** one single-band GeoTIFF per statistic file; band 1 is Float32 metres, EPSG:32644, aligned cell-for-cell to the 30 m CMA master grid. The band is `AREA_OR_POINT=Area`. Raster NoData is `-9999.0`. `depth_mean_*` stores the component-edge estimate; `depth_p05_*` and `depth_p95_*` are legacy filenames for the lower and upper assumption bounds described below. Existing files have no band description, so consumers must use the filename plus dataset tags; a future regeneration should also set band description/tag `band_role` to `mean_m`, `lower_assumption_bound_m`, or `upper_assumption_bound_m`.
- **Required dataset tags:** `version`, `status`, `band_role`, `units`, `crs`, `grid`, `nodata`, `event_date`, `acquisition_time_utc`, `run_time_utc`, `source`, `source_tier`, `source_geometry_count`, `method`, `uncertainty_rule`, and `dem`. `units=metres`; `crs=EPSG:32644`; `nodata=-9999`; `event_date` is ISO `YYYY-MM-DD`; `run_time_utc` is an ISO-8601 UTC instant. These are metadata requirements for a later product; existing files currently have one-band Float32, CRS/grid, NoData, `event_date`, `run_time_utc`, source/method/status/version and DEM tags, but not `units`, `band_role`, `acquisition_time_utc`, `source_tier`, or `nodata` tags.
- **Time meanings:** `event_date` is the source map/reference date, not a precise flood-onset timestamp. `acquisition_time_utc` means the sensor/source acquisition instant only when the source records one; it is unknown for the current vector-derived T6 products and must be serialized as JSON `null` in any sidecar/API metadata, never imputed to midnight or copied from `event_date`. `run_time_utc` is when the depth-generation process ran (existing T6 tag values are `2026-10-25T04:47:06.612287+00:00` for 12 Nov and `2026-10-25T04:47:42.948183+00:00` for 24 Nov).
- **Bounds, not percentiles:** for each valid mean depth `d`, the lower file is `max(0, d − 4 m)` and the upper file is `d + 4 m`. These are deterministic ±4 m assumption bounds (`DEFAULT_TO_CONFIRM`), **not calibrated statistical p05/p95 percentiles**, confidence limits, or measured uncertainty coverage. Preserve the old filenames for compatibility but expose them as `lower_assumption_bound_m` and `upper_assumption_bound_m`; do not describe them as probabilistic quantiles.
- **NoData and physical meaning:** `-9999` means outside the mapped source extent or missing cleaned-DEM elevation. It is never dry/zero. `status=DERIVED_ASSUMPTION_NOT_OBSERVED` must travel with every file. The input is a GLO-30 surface model with building and vegetation returns; urban values are unreliable and have not been checked against measured depth. The outlines are extent references, not depth truth.
- **Tag encoding observation:** reading the current files confirms a single Float32 band per TIFF and the fields above that are present. The current uncertainty tag appears with a replacement character in place of the ± symbol on this host; future tags should use an ASCII-safe value such as `lower=max(0,mean_m-4);upper=mean_m+4;status=assumption_not_calibrated` rather than relying on a possibly corrupted glyph. Existing TIFFs were not modified.

### Coverage and checks

| Date | Rasterized official extent | Extent with valid DEM / depth cells | Coverage | Mean-depth median / mean / p95 / max |
|---|---:|---:|---:|---:|
| 2015-11-12 | 94,195 cells (84.7755 km²) | 30,235 | 32.10% | 0 / 0.096 / 0.480 / 22.817 m |
| 2015-11-24 | 109,067 cells (98.1603 km²) | 32,627 | 29.91% | 0 / 0.125 / 0.584 / 6.376 m |

The low coverage results from missing cleaned-DEM values within mapped flood extent. The near-zero median results from components whose edge elevation approximates the DEM at their cells, including one-cell components. These findings make the layers unsuitable as validated depth truth. Ordered-band check found zero p05-above-mean or mean-above-p95 violations.

See `T6_DEPTH_OUTPUTS.json` for the machine-readable audit summary. Reproduce using `.venv/Scripts/python.exe -m pipelines.phase8.depth_fields --dem-error-m 4 --output-dir data/features/depth/reproduction_v1 --summary docs/T6_DEPTH_OUTPUTS_REPRODUCTION.json`; this uses a separate output directory and will not overwrite the saved `batch1_v1` files. The read-only audit command is `.venv/Scripts/python.exe -m pipelines.phase8.summarize_depth_fields`.
