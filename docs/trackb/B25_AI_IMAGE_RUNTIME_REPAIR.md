# B25 — AI image Rasterio runtime repair

Date: 2026-10-31

## Image change

The prior B24 packaged startup failed while importing Rasterio because `libexpat.so.1` was missing. The AI image now installs Debian Bookworm's `libexpat1` with `apt-get update`, `apt-get install --no-install-recommends`, and apt index cleanup in one Docker layer. The existing `rasterio==1.5.2` pin is retained. No application routes, CORS policy, or Compose service configuration were changed.

## Packaged build and runtime

- Build: `docker compose -p twinguard-b11 -f docker-compose.b11.yml build --pull=false ai-service` — passed. Image digest: `sha256:0987a6d5368f70b2c0e4e4f891eeaf67cd3360117bcc5020c437581182559e11`.
- Started only `ai-service` via `docker compose -p twinguard-b11 -f docker-compose.b11.yml up -d --no-build --pull never ai-service`. Container health reached **healthy**; image ID was `sha256:0987a6d5368f70b2c0e4e4f891eeaf67cd3360117bcc5020c437581182559e11`.
- At origin `http://127.0.0.1:8081`, preflight returned 200 with `Access-Control-Allow-Origin` exactly that origin, methods `GET`, allowed headers `Accept`, and no `Access-Control-Allow-Credentials`. GET returned 200 for catalog, detail, and raster.
- Raster selector was taken from the first saved slice in `data/features/visualization3d/batch2_v1/manifest.json`, band `p50`. Response content type was `image/tiff`, size **13,763 bytes**, SHA-256 `d563c3780e5c7b611f2a8f13ada4945f1f692160e6b16beeff7b0e455917a1cd`; it matched the selected manifest reference. JSON catalog/detail returned artifact version `batch2_v1`.
- `http://localhost:8081`, `null`, `http://127.0.0.1:3000`, and `http://127.0.0.1:8082` received no `Access-Control-Allow-Origin` on all three GET paths. Preflights for POST, `Accept, Authorization`, and `Content-Type` returned 400 on all three routes. Credentials were not allowed.
- Stopped only the AI container started for this task with `docker compose -p twinguard-b11 -f docker-compose.b11.yml stop ai-service`; it is exited. No database, migration, other app service, volume, or cleanup command was used.

## Checks

- B25 packaging plus B24 CORS/API tests: `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib tests\packaging\test_b25_ai_image_runtime.py tests\ai_service\test_scenario_visualization_cors.py tests\ai_service\test_scenario_visualization_raster.py tests\ai_service\test_scenario_visualization_api.py tests\ai_service\test_scenario_visualization.py tests\master\test_scenario_visualization_contract.py` — **67 passed**, one existing Starlette/httpx deprecation warning.
- Full AI-service tests: `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib tests\ai_service` — **88 passed**, same warning.
- Compilation: `.venv\Scripts\python.exe -m compileall -q services\ai-service\app tests\ai_service tests\packaging` — passed.
- API validation: `python tools\validate_api_contracts.py` — AI OpenAPI 3.1.0, 11 paths/11 operations; backend OpenAPI 3.1.0, 10 paths/11 operations; passed.
- Compose validation: `docker compose -p twinguard-b11 -f docker-compose.b11.yml config --quiet` — passed with no rendered configuration output.
- Raw audit: `DATA_FILES=157; DATA_BYTES=30544672450; HASH_MATCH=157; NO_COMPARABLE_HASH=0; MISMATCH=0`.

Results are limited to saved A20 research/simulation assets and the local loopback B11 app tier. They do not establish live operation or a C9 contract freeze. C1–C8 and G0 are unchanged. B24 remains blocked until the Integrator accepts this packaged runtime evidence; B18 and I08 were not started.
