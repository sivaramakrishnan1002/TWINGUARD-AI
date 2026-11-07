# C1 depth-field v0

**Status:** frozen v0 contract for G0 (2026-10-28). It describes current T6 DERIVED products and required metadata. It does not assert calibrated depth or a validated depth product.

## Grid and file representation

- One single-band GeoTIFF per field; band 1 is Float32 depth in metres, EPSG:32644, 30 m aligned to the master grid, `AREA_OR_POINT=Area`, raster NoData `-9999.0`.
- Current T6 product family is named `batch1-depth-v1`; legacy filenames use `mean`, `p05`, and `p95`. These are per-file products, not three bands in one raster.
- Required metadata for conforming products: `version`, `status`, `band_role`, `units`, `crs`, `grid`, `nodata`, `event_date`, `acquisition_time_utc`, `run_time_utc`, `source`, `source_tier`, `source_geometry_count`, `method`, `uncertainty_rule`, and `dem`. Use ASCII-safe uncertainty text.

## Scientific and temporal meaning

- The T6 products are DERIVED, unvalidated surface-DEM depth proxies conditioned on accepted extent references; the outline is extent information, not observed depth. GLO-30 includes building/vegetation surface returns; urban values are unreliable.
- In legacy T6 `p05`/`p95` files, `p05=max(0, mean_m−4 m)` and `p95=mean_m+4 m`. They are ±4 m assumption bounds, not calibrated percentiles, probabilities, confidence bounds, or coverage intervals. Preserve legacy filenames only for compatibility; `band_role` must state the assumption-bound meaning.
- `event_date` is the source map/reference date as a date, not flood onset or acquisition time. `acquisition_time_utc` is a separately evidenced acquisition instant; it is null/unknown for present T6 products. `run_time_utc` is processing time. Do not fabricate midnight instants.
- Raster NoData `-9999.0` means unavailable/outside valid depth extent and must remain masked, never converted to zero. Current T6 coverage is limited (about 29.91–32.10% of rasterized extents).

## Evidence and conformance boundary

Lane A evidence: `docs/DEPTH_FIELD_CONTRACT.md`, `docs/T6_DEPTH_OUTPUTS.json`, `docs/LANE_A_G0_REPAIR_PROPOSALS.md`, and A18's `docs/DEPTH_METADATA_REPAIR.md` plus `data/features/depth/c1_metadata_repair_v0/metadata_repair_manifest.json`. The six original files under `batch1_v1/` remain untouched legacy sources. The separate A18 copies have the required band roles, units, grid/NoData, date/unknown acquisition/processing times and provenance tags; their manifest records matching source/output hashes and unchanged values/masks, and focused tests reopen every output. Unknown acquisition is represented as JSON null in the sidecar and an explicit unknown marker in TIFF tags. These copies are file-conformant; this does not assert that legacy originals were rewritten or that routing consumes the copies. Shared version remains v0; G0 freeze does not promote the depth proxy or imply downstream consumption.
