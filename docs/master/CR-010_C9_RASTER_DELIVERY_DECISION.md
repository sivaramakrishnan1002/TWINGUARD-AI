# CR-010 — C9 exact A20 raster-byte delivery

**Decision:** Approved by the project owner on 2026-10-30.

## Approved operation

Authorize one additive, read-only AI-service operation returning the exact original GeoTIFF bytes selected from A20's manifest by `event_id`, `scenario_id`, an exact saved `valid_time_utc`, and band `p05`, `p50`, or `p95`. The response is the original single-band Float32 GeoTIFF (`image/tiff`). Preserve its bytes, values, mask, CRS, grid, TIFF metadata, and SHA-256. Do not reproject, resample, recolor, interpolate, rewrite, generate tiles, or create scientific outputs.

The operation may read only manifest-referenced scenario-series slices below the existing A20 roots mounted read-only by B11. It accepts no path or arbitrary asset name. The service must validate selector identity, path containment, file size, SHA-256, and recorded TIFF properties before returning the body. A missing, corrupt, changed, or unavailable file returns 503 with no partial body. Invalid selectors return 400, exact misses 404, and duplicate/ambiguous identities 409.

This is a separate additive proposed C9 v1 operation. It does not change or freeze C1–C8, the existing C9 catalog/detail operations, or G0. Values remain saved research/simulation evidence; no physical-flow validation, operational warning, safe routing, live data, database write, migration, or shared-state permission is granted.

## Browser-origin configuration

Authorize AI-service CORS only for origin `http://127.0.0.1:8081`, method `GET`, and request header `Accept`, with credentials disabled. Keep the static Nginx frontend, no-proxy behavior, and existing loopback-only service ports. The UI calls the AI service directly at `http://127.0.0.1:8000`; it does not call Spring. Do not allow wildcard/null/development origins or widen ports.

## Implementation and verification sequence

1. I19 records the additive C9 v1 projection while the new operation remains unavailable until B23 and packaged verification.
2. B23 implements and tests the bounded read-only AI raster operation using the existing read-only mounts.
3. B24 adds the approved CORS policy and verifies the packaged browser/API path.
4. Integrator runtime-projection reconciliation records the verified packaged availability; then B18 may implement its UI.
5. I08 remains downstream of B18 completion.

Approval evidence: explicit project-owner decision in the 2026-10-30 task handoff. Integrator change-control review is recorded in I19 and this decision file. C9 remains proposed/unfrozen and outside the C1–C8 contract registry.

## Packaged runtime projection review (2026-10-31)

B25 (`0aebc59`) repaired the AI image's missing Debian Bookworm `libexpat1` runtime dependency while retaining `rasterio==1.5.2`. Its evidence report records a successful local B11 image build and healthy AI startup, allowed-origin catalog/detail/raster GETs, exact raster size/hash match, denied origins and methods/headers, and stop-only cleanup of the task-started AI container. I20 records the verified raster operation as HTTP 200 only in the local B11 AI package. Its response body is the exact original manifest-selected GeoTIFF; the quoted `ETag` is the SHA-256 of those bytes. Invalid selectors, exact misses, duplicate identities, and unavailable/invalid assets retain 400/404/409/503 behavior with no partial raster body.

The Spring backend continues to expose no raster operation; its local B11 C9 metadata routes remain separate. This review does not freeze C9 v1, change C1–C8 or G0, or claim deployment-wide/live availability. The A20 rasters remain saved research/simulation evidence with the recorded 600 m and scientific limitations.
