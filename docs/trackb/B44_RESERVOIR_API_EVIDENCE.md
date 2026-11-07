# B44 evidence — packaged CFM-DSS reservoir snapshot API

**Date:** 2026-11-07. **Scope:** CR-016 / CR-017, `GET /reservoirs/history?period=daily|monthly` in the B11 AI service. Two on-demand upstream reads were made (one daily, one monthly); no polling, caching, persistence, database write, or model recomputation.

## Implementation

- Router: `services/ai-service/app/reservoir_snapshot/router.py`, mounted in `services/ai-service/app/main.py`.
- Connector: B41 `services/trackb/connectors/tn_reservoir/client.py`, copied into the image; build context narrowed to `./services` with `ai-service/Dockerfile`. No `data/` copy; existing five read-only mounts unchanged.
- Docs: `docs/trackb/CFM_RESERVOIR_API.md`; OpenAPI projection `docs/api/ai-service.yaml` (I25).

## Tests

| Command | Result |
|---|---|
| `.venv/Scripts/python.exe -m pytest --import-mode=importlib tests/ai_service/test_reservoir_snapshot_api.py tests/packaging/test_reservoir_snapshot_package.py` | 6 passed (standalone; test now sets its own `sys.path` like the other AI-service tests) |
| `.venv/Scripts/python.exe -m pytest --import-mode=importlib` (full suite) | 369 passed, 1 skipped, 77 subtests passed |

## Packaged runtime smoke (Docker 29.8.2)

- `docker compose -f docker-compose.b11.yml build ai-service` → image `local/twinguard-b11-ai:0.1.0`, `sha256:63eab9e7ff53b95f5fe1b1106272dda68c67ed6aba68fb036ee5f33b8729b5b1`.
- `docker compose -f docker-compose.b11.yml up -d --no-deps ai-service` → container healthy; `/health` 200.

| Request | Result |
|---|---|
| `period=daily` | 200, 75 records, 5 reservoirs × 15 days, source dates 2026-10-24..2026-11-07; `source_mode=LIVE`, `freshness=unknown`, `observed_at=null`, timezone `unknown`; response SHA-256 prefix `ff03f91b07d4da29`; received 2026-11-07T06:24:59Z |
| `period=monthly` | 200, 65 records, 5 reservoirs × 13 months, labels 2025-11-01..2026-11-01; response SHA-256 prefix `634b6f02c9f740dd`; received 2026-11-07T06:25:01Z |
| `period=hourly` | 422 |
| Headers | `Cache-Control: no-store`; CORS origin limited to `http://127.0.0.1:8081` |
| Leak check | No token/cookie/verification strings in API bodies or container logs |
| Mounts | All five data mounts `rw=false` |

Reservoirs returned: Chembarambakkam, Poondi, Red Hills, Cholavaram, Thervoy Kandigai. Raw upstream responses were not retained or redistributed. The container was stopped afterwards (`docker compose stop`); no volumes removed.

## Caveats

- `LIVE` means fetched from the public dashboard at request time — latest published dashboard snapshot, not operational real-time telemetry. Publication cadence, measurement timing, formal terms, and rate limits remain unknown.
- No inflow/outflow/release, alerts, forecasts, flood depth, routes, or shelter outputs. Reservoir data does not drive A06.
- Backend/frontend were not started for this check; the UI consumer is B45.
