# C9 — Scenario visualization assets v1 proposal

**Status:** proposed, project-owner approved for bounded AI raster delivery under CR-010 on 2026-10-30; not frozen and not part of the C1–C8 registry. This is additive to the C9 v0 metadata catalog and exact-detail operations. Their selectors and response schemas are unchanged.

## Raster operation

`GET /scenario-visualization-assets/{event_id}/{scenario_id}/raster?valid_time_utc={saved_utc}&band={p05|p50|p95}`

Operation ID: `getScenarioVisualizationRaster`.

The selector must match exactly one `scenario_series` record in `data/features/visualization3d/batch2_v1/manifest.json`, one exact saved `valid_time_utc` in that series' `slices`, and one of its `p05`, `p50`, or `p95` bands. No timestamp rounding, nearest-time lookup, default band, context-layer lookup, asset-path input, or interpolated value is permitted.

## Success representation

- Status `200`; media type `image/tiff`; body is the exact referenced file bytes from the manifest.
- The referenced file remains the original one-band Float32 GeoTIFF. Preserve EPSG:32644, the exact 69 × 88 grid and 600 m pixels, source NoData value/mask, all TIFF tags/metadata, byte size, and SHA-256. Do not rewrite or transform the TIFF.
- The user first reads the existing C9 v0 detail response for source mode, saved time, band semantics, units and their evidence basis, coverage/NoData meaning, provenance, and the expected SHA-256. The browser computes SHA-256 over the returned bytes and compares it with that exact detail reference before rendering. A mismatch fails closed.
- Current A20 source references are under the manifest root `data/features/visualization3d/batch2_v1/` and manifest-selected assets under `data/features/forecast/batch2_v1/` or `data/features/simulation/batch2_v1/`. The operation serves only `scenario_series` slice bands; it does not accept arbitrary paths or serve raster tiles.

## Errors and validation

- `400`: malformed event/scenario selector, noncanonical UTC timestamp, unsupported band, or unexpected query/body input.
- `404`: no exact saved event/scenario/time/band match.
- `409`: duplicate or ambiguous event/scenario/time identity.
- `503`: manifest or asset missing, unreadable, changed, oversized, outside the allowed root, invalid, or failing size/hash/TIFF-metadata validation. Return no partial body.

Before sending bytes, the implementation must fully read the bounded source, validate the manifest selector and path containment, verify exact byte size and SHA-256, and confirm recorded dtype, band count, CRS, grid, and NoData. Response streaming must not begin before all checks pass. Failures must not reveal local paths or filesystem diagnostics.

## Runtime and scientific limits

The operation is AI-service-only and uses the existing B11 read-only mounts. It has no database, migration, write, live-feed, prediction, alert, routing, or service-to-service capability. It serves saved research/simulation evidence only. The 600 m regional grid, irregular saved times, assumption-based solver, and parameter-member spread do not establish physically simulated street-level water flow or validated flood behavior. No new scientific output is created.

The operation remains unavailable until B23 implementation/tests and B24 packaged-origin verification complete. The AI service must retain the existing loopback-only binding. No C1–C8 or C9 v0 response changes are authorized by this proposal.
