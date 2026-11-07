# B18 browser and raster integration architecture

Date: 2026-10-30

## Decision basis

B21 and B22 are complete. B21 mounts the CR-009 catalog and exact-detail metadata operations in the AI service and Spring backend, and its report records packaged-runtime smoke checks plus read-only inspection of the A20 manifest, forecast, and simulation mounts. B22 reconciles the stale packaging assertion; it does not add raster delivery. The current C9 projections and both B21 applications return metadata and asset references, not raster bytes or map tiles. The B11 frontend is static Nginx with no proxy, published on `127.0.0.1:8081`; the AI service is published on `127.0.0.1:8000`. The AI app has no CORS middleware. The current B18 output list did not include the shell mount file.

The A20 manifest has three scenario series, each with five exact saved UTC slices and p05/p50/p95 references. These references resolve to original single-band Float32 GeoTIFFs; the manifest records EPSG:32644, a 69 × 88 grid, 600 m pixels, NoData `-9999` (outside assessed CMA, not dry), unit evidence, source mode, size, SHA-256, and provenance. B21 already mounts the manifest, forecast and simulation roots read-only in the local app tier.

## Recommendation

1. **B18 shell ownership:** mount the view from `frontend/src/ui/App.tsx`, which is the current application shell. Keep the implementation and scoped styles under `frontend/src/ui/scenario3d/`, tests under `tests/ui/scenario3d/`, and the guide at `docs/ui/FLOOD_3D_SCENARIO_VIEW.md`. Do not edit `frontend/src/main.tsx` (React bootstrap), redesign the global shell, or change the shared stylesheet as part of the initial mount. Add only a focused shell entry point and preserve the existing sections and 2D fallback.
2. **Browser API path:** keep B11's static Nginx/no-proxy design. The browser should call the AI service directly from the packaged UI origin `http://127.0.0.1:8081` to `http://127.0.0.1:8000`; it should use the B21 catalog/detail GETs for metadata. Do not route UI calls through Spring. Register a separate Lane B CORS task allowing exactly the packaged UI origin, GET, and the safelisted `Accept` header, with credentials disabled. Do not allow wildcard, `null`, or development-server origins; do not widen loopback bindings. A Vite development origin is not part of the accepted package path.
3. **Raster requirement:** metadata alone cannot supply a quantitative map layer. The B21 operations do not return TIFF bytes, and browsers cannot dereference manifest-local paths. A 3D scenario display therefore needs a separate, explicitly approved raster-byte operation. Prefer a bounded AI-service operation that returns the original referenced GeoTIFF bytes as `image/tiff`; a separate tile server is unnecessary for the current small saved assets. Do not create XYZ/PNG tiles, reproject, resample, recolor, interpolate, or regenerate science products in this prerequisite. The browser decoder/rendering must preserve the original per-cell values and mask and may not invent intermediate quantitative times.

## Approved delivery boundary (CR-010)

The project owner approved CR-010 on 2026-10-30. It authorizes a separately versioned additive C9 v1 operation in the AI service only, keyed by exact `event_id`, `scenario_id`, saved `valid_time_utc`, and one of `p05`, `p50`, or `p95`. It returns the original single-band Float32 GeoTIFF for that manifest reference. It accepts no filesystem path, arbitrary asset name, time interpolation, or unregistered layer. The allowed file roots are only the existing read-only A20 manifest references under `data/features/visualization3d/batch2_v1/`, `data/features/forecast/batch2_v1/`, and `data/features/simulation/batch2_v1/`; selection must be manifest-driven and path-resolved beneath those roots.

Before returning any bytes, the service must validate exact identity, file size, SHA-256 and TIFF dtype/grid/CRS/NoData against the manifest. On success it must preserve the bytes and make the manifest SHA-256 available as the response entity tag for comparison with the detail metadata. Missing, unreadable, oversized, changed, or hash/schema-invalid assets return 503 with no partial body; invalid selectors return 400, exact misses 404, and duplicate/ambiguous identities 409. Existing C9 metadata operations keep their current semantics. No database, migrations, live feeds, generated predictions, alerts, routing, or wider path access is permitted.

CR-010 approval and Integrator review are recorded in `docs/master/CR-010_C9_RASTER_DELIVERY_DECISION.md` and I19. CR-009 continues to cover only the catalog and exact-detail metadata GETs. C9 v1 remains proposed and unfrozen; C1-C8 and G0 are unchanged.

## Registered task order

- **I19:** record the approved additive C9 v1 projection; this does not freeze C9.
- **B23:** implement and test only the bounded AI-service raw GeoTIFF operation using the existing read-only mounts.
- **B24:** add and test the exact packaged-origin AI CORS policy. Keep static Nginx, no proxy, and loopback-only ports.
- **B18 (blocked prerequisite):** after I19/B23/B24 evidence, build the UI, mount through `App.tsx`, and verify exact saved raster display and fallback.
- **I08 (blocked prerequisite):** after B18 completes, run the deterministic end-to-end replay acceptance.

The proposed B23 and B18 acceptance also requires a pinned, license-reviewed browser GeoTIFF decoder/CRS transformation dependency in the frontend lockfile. No package is installed or fetched by this review. If the required package is not already available through the authorized local dependency workflow, obtain separate approval before network retrieval.

## Evidence reviewed

- `docs/ui/FLOOD_3D_SCENARIO_VIEW.md`
- `docs/trackb/C9_ROUTE_MOUNT_REPORT.md`
- `docs/trackb/B22_PACKAGING_RECONCILIATION.md`
- `docs/trackb/B11_LOCAL_RUNBOOK.md` and `docker-compose.b11.yml`
- `docs/master/contracts/c9_scenario_visualization_v0.md`
- `docs/api/ai-service.yaml` and `docs/api/backend.yaml`
- `data/features/visualization3d/batch2_v1/manifest.json`
- `docs/FLOOD_3D_SCENARIO_READINESS.md`
- `frontend/src/ui/App.tsx`, `frontend/src/main.tsx`, `frontend/nginx.conf`
