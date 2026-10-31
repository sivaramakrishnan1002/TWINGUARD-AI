# B24 — Packaged frontend origin CORS verification

Date: 2026-10-31

## Policy and tests

The AI service allows exactly origin `http://127.0.0.1:8081`, method `GET`, and request header `Accept`; credentials are disabled. A narrow middleware subclass removes Starlette's default safelisted-header expansion so preflight advertises only `Accept`. No proxy or frontend changes were made; calls remain direct to the loopback AI service.

`tests/ai_service/test_scenario_visualization_cors.py` verifies the catalog, exact detail, and raster routes independently. For each route it checks allowed preflight and GET, absent credential allowance, denied CORS exposure for alternate/null/development origins, and rejected preflights for POST, Authorization, and Content-Type. A disallowed-origin GET can still be processed by HTTP; the test confirms the browser is not granted access because `Access-Control-Allow-Origin` is absent.

## Checks

- Docker Linux engine: `docker info --format '{{.OSType}}'` — `linux`.
- Focused CORS/API/C9 suite: `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib tests\ai_service\test_scenario_visualization_cors.py tests\ai_service\test_scenario_visualization_raster.py tests\ai_service\test_scenario_visualization_api.py tests\ai_service\test_scenario_visualization.py tests\master\test_scenario_visualization_contract.py` — **65 passed**, one existing Starlette/httpx deprecation warning.
- Full AI-service suite: `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib tests\ai_service` — **88 passed**, same warning.
- Python compilation: `.venv\Scripts\python.exe -m compileall -q services\ai-service\app tests\ai_service` — passed.
- API structural validation: `python tools\validate_api_contracts.py` — AI **11 paths/11 operations**, backend **10 paths/11 operations**, pass.
- Quiet package configuration: `docker compose -p twinguard-b11 -f docker-compose.b11.yml config --quiet` — passed, no rendered configuration emitted.
- Packaged AI image build: `docker compose -p twinguard-b11 -f docker-compose.b11.yml build --pull=false ai-service` — build passed; image digest `sha256:f6947071eadd5cf34d9b7cb6060cdb5c57240640caeaf9d9fca9f1123a33904a`.
- Raw audit: `DATA_FILES=157; DATA_BYTES=30544672450; HASH_MATCH=157; NO_COMPARABLE_HASH=0; MISMATCH=0`.

## Runtime blocker

Started only `twinguard-b11-ai-service-1` with `docker compose -p twinguard-b11 -f docker-compose.b11.yml up -d --no-build --pull never ai-service`. The packaged container exited during app import before health became available: Rasterio could not load `libexpat.so.1`. Therefore no packaged preflight or catalog/detail/raster GET check could run. The task-started container is stopped/exited. No database, other service, or volume was accessed or modified.

The blocker is in the existing AI image's operating-system runtime dependency set (B23 packaging path), outside B24's registered outputs (`main.py`, CORS tests, and this evidence). Integrator/package owner must register or authorize a narrowly scoped image dependency repair, rebuild, then rerun B24 packaged preflight and GET checks. Until then, B24 is incomplete and B18/I20 must remain blocked; I08 remains downstream of B18. C9 stays unfrozen; C1–C8 and G0 are unchanged.
