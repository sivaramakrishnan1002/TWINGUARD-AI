# B23 — Exact A20 GeoTIFF delivery

Date: 2026-10-31  
Status: implementation and focused verification complete with packaged-runtime caveat

## Scope and implementation

B23 adds the approved AI-service-only `GET /scenario-visualization-assets/{event_id}/{scenario_id}/raster` operation. It accepts only an exact saved UTC slice and one of `p05`, `p50`, or `p95`; it resolves only manifest-listed scenario bands under the existing forecast bind mount. The request cannot supply a path or arbitrary layer. The service fully reads the bounded file, validates manifest identity, path containment, size, SHA-256, and the TIFF's band count, Float32 dtype, CRS, dimensions, affine grid, NoData value and mask counts, source-status/NoData tags, and absence of embedded unit metadata before constructing the response. The exact original bytes are returned as `image/tiff`, with the manifest SHA-256 in `ETag`; no TIFF is rewritten.

`rasterio==1.5.2` is pinned in the AI image so the same metadata validation is available at runtime. Failures map to 400 for invalid selectors, 404 for exact misses, 409 for duplicate identity, and 503 for unavailable or invalid assets. Error responses contain no TIFF bytes or local paths.

## Verification

- `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib tests/ai_service/test_scenario_visualization_raster.py tests/ai_service/test_scenario_visualization.py tests/ai_service/test_scenario_visualization_api.py tests/master/test_scenario_visualization_contract.py` — **41 passed**, one Starlette/httpx deprecation warning.
- `python tools/validate_api_contracts.py` — **PASS**, AI and backend OpenAPI structural validation. The proposed raster operation remains documented unavailable pending B24 and I20.
- `docker compose -p twinguard-b11 -f docker-compose.b11.yml config --quiet` — **PASS**, no rendered configuration emitted.
- `docker compose -p twinguard-b11 -f docker-compose.b11.yml build ai-service` — **NOT RUN TO COMPLETION**: Docker could not connect to `npipe:////./pipe/dockerDesktopLinuxEngine`; Docker Desktop's Linux engine was unavailable. No container was started.

The package build/runtime smoke is therefore unverified. B24 must not claim packaged CORS or raster availability until the engine is available and the AI image has been built and smoke-tested using the B11 app-tier only. No database was contacted, no migration was run, no volume was modified or deleted, and no A20 asset or scientific output changed.

## Limits

The operation serves only saved research/simulation bytes from the existing read-only A20 mount. It does not create tiles, interpolate time, transform the raster, enable live feeds, make warnings/routing available, or validate physical flood behavior. C9 remains proposed and unfrozen; C1–C8 and G0 are unchanged.
