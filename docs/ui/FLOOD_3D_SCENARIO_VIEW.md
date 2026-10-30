# B18 — 3D scenario display readiness review

Date: 2026-10-30

## Readiness outcome: blocked prerequisite

B18 was offered by the Lane B selector and claimed through the official task protocol. No frontend implementation was started because the registered output paths and current package boundary do not provide a safe, working route from the UI to the approved evidence.

### Verified blockers

1. **No authorized shell mount path.** B18 registers `frontend/src/ui/scenario3d/`, `tests/ui/scenario3d/`, and this report. The existing application shell and map page are outside those paths. A component left unmounted would not deliver a usable scenario display; editing `frontend/src/ui/App.tsx` or `MapView.tsx` would exceed the registered B18 outputs.
2. **No browser-accessible API path.** The static frontend is served on the B11 frontend origin; B21 binds the Spring routes on the separate backend origin. B11's packaging contract requires a static frontend without a proxy, and the backend has no CORS configuration. A browser request from the frontend origin therefore has no approved cross-origin path under current B18 ownership. Direct service runtime checks in the B21 report do not establish browser access.
3. **No raster/tile serving operation.** B21 returns the B17 manifest-backed catalog/detail projections, including bounded metadata and saved asset references. It does not serve raster bytes or HTTP tiles. The frontend does not receive the mounted A20 files. Rendering a quantitative map from a visual approximation or inferred asset access would fabricate support that the routes do not provide.

The A20 metadata specifies a 600 m EPSG:32644 grid, selected saved UTC slices, parameter-member spread (not calibrated confidence), and NoData outside the assessed CMA as unknown/not dry. Those facts are suitable for labels and provenance once a real browser path and approved rendering source exist; they do not supply a browser-readable map layer by themselves.

## Required Integrator action

Register or authorize a scoped integration prerequisite that:

- adds the application shell mount path to B18 ownership (or provides another approved mount mechanism);
- defines a browser-safe path to the existing B21 catalog/detail routes while preserving the B22 static/no-proxy packaging constraints, including any required backend CORS ownership; and
- explicitly states whether the B18 experience is metadata-only with a visibly unavailable map, or registers an approved raster/tile delivery operation and its ownership. Do not infer a tile endpoint from manifest references.

Until that action is complete, B18 cannot meet its registered requirement for a working scenario MapLibre timeline. C9 remains proposed/unfrozen. No C1–C8 contracts, assets, frontend code, backend service, database, or Docker volume were changed.

## Checks

- Startup `verify_state.py` passed; the Lane B selector offered B18. B18 had no active output-path conflict and was claimed using `tools/master/claim.py`.
- No frontend build, UI test, visual check, or runtime check was run: no B18 code was changed, and the cross-origin/raster boundary prevents an honest end-to-end UI check.
- Prior B21 route and read-only mount verification remains documented in `docs/trackb/C9_ROUTE_MOUNT_REPORT.md`; it is service-level evidence, not UI browser evidence.
