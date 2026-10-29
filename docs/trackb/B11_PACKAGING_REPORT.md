# B11 full-stack packaging report

## Scope delivered

Created a separate app-tier Compose profile at `docker-compose.b11.yml` containing only the static frontend, bounded AI-service artifact projections, and backend health endpoint. Added pinned multi-stage Dockerfiles for the UI, AI service, and backend, loopback-only ports, per-service health checks, focused packaging safety tests, and this runbook. The profile does not edit or replace the main Compose stack or the Track B streaming overlay.

The AI service mounts only A07 V4 and A09 revision-3 registered artifacts read-only. It exposes the tested exact selectors as simulated evidence. Route computation, forecast, uncertainty, and scenario operations return HTTP 501. The distinct C9 operation is absent, and backend business routes remain unexposed. The frontend is a static design artifact with no API proxy.

## Runtime verification (2026-10-29)

- `docker compose -p twinguard-b11 -f docker-compose.b11.yml config --quiet`: passed; stdout/stderr empty.
- `docker compose ... build --pull=false`: all three images built successfully. Build bases were pinned: Node 22.14.0 Alpine 3.21, nginx 1.27.5 Alpine, Python 3.12.8 slim Bookworm, Maven 3.9.9 with Temurin 21, and Temurin 21.0.6_7 JRE Jammy. The initial AI image lacked Psycopg's native binary wrapper; its health check failed. Updated the B11 Dockerfile to install pinned `psycopg[binary]==3.3.6`, rebuilt locally, and all three service health checks passed.
- Startup: frontend, AI service, and backend each reported `running healthy`.
- Smoke checks: frontend `/` 200; backend `/health` 200; exact A07 selector returned 200 and `SIMULATED` result `a07-batch2-v4-2015-12-02-perfect_foresight_imerg-lead06h`; exact A09 revision-3 result returned 200 and `SIMULATED` result `A09-2015-12-02-06h-static-od01`.
- Valid requests to forecast, uncertainty, route computation, and scenario computation returned 501. The C9 visualization path and backend `/impact` returned 404.
- Shutdown used `docker compose -p twinguard-b11 -f docker-compose.b11.yml stop`. The profile declares no named volumes; none were removed. The unrelated PostGIS container was not stopped.
- No database service/credentials were configured or contacted, no database writes or migrations occurred, and no live feeds were connected.

## Automated checks

- `docker compose -p twinguard-b11 -f docker-compose.b11.yml config --quiet`: passed.
- `.venv\\Scripts\\python.exe -m pytest -q --import-mode=importlib tests\\packaging\\test_b11_packaging.py tests\\ai_service tests\\master\\test_api_contract_projection.py`: 38 passed, one existing Starlette/httpx deprecation warning.
- `.venv\\Scripts\\python.exe -m compileall -q services\\ai-service\\app tests\\packaging tests\\ai_service`: passed.
- `frontend`: `npm run build` passed; Vite reported its existing advisory that the main JavaScript chunk exceeds 500 kB (built chunk approximately 1.25 MB).
- `mvn -o -B -ntp -f services/backend/pom.xml test`: 14 tests passed; Maven emitted existing Mockito dynamic-agent warnings.
- `.venv\\Scripts\\python.exe tools\\audit_raw_logs.py`: `DATA_FILES=157; DATA_BYTES=30544672450; HASH_MATCH=157; NO_COMPARABLE_HASH=0; MISMATCH=0` (exit 0).

## Limits

This is local app-tier packaging and a smoke check of saved simulated artifacts. It does not verify live ingestion, operational forecasting, validated flood impacts, safe route computation, shared-database integration, or migration behavior. No GPU work was needed. The frontend has no automated UI or visual browser validation in this task. Changes remain unstaged and uncommitted to preserve other sessions' work.
