# B27 — CR-012 date-only replay vertical slice

**Status: implemented with runtime caveat; G5 remains not ready.** This report records the bounded source-backed REPLAY observation path and its separately derived output. It does not assert live operation, historical outcome, flood-depth result, forecast validation, warning, route safety, or G5 completion.

## Source selection and normalization

The only selected observation is the B28/I22-approved tuple:

- `event_id`: `replay:POONDI:date:2015-12-01`
- Archive: `data/raw/reservoirs/kaggle_chennai_water_management/archive.zip`, SHA-256 `7645febde7ccc21871200487139d1c8a84ea90a6dd2eccc93b7d1f06faf69197`.
- Member: `chennai_reservoir_levels.csv`, SHA-256 `3b4b6f2f53b5db20513d2829c2dba265c5738a55bf0c8eade51e0e2d5cfeaef7`.
- Unique CSV physical line 4354: raw `Date=01-12-2015`, raw `POONDI=2745.00`; normalized `source_date=2015-12-01`.
- Canonical package input: `services/ai-service/app/replay_results/b13_source_observation.json`, SHA-256 `dd5ea17cdf63853ffd1cdc3036b8c8282490daafd3e19715cd82445cb27ff2a8`.

The raw source archive was only read. The canonical fixture preserves the exact selected lexical row, date-only semantics, source/archive/member hashes, the rainfall source row needed by the registered existing rule, and the three prior daily context rows used by the unchanged 1-day/3-day feature calculations. The source observation has `observed_at=null`, `observation_timezone=unknown`; the API supplies actual `received_at` separately. No valid-time or validity interval is synthesized. The legacy alert JSONL is not consumed.

## AI processing and response

`GET /replay-alerts/{event_id}` is mounted in the AI service and the test-scoped B11 package. It accepts only the exact eligible observation, returns 400 for malformed/date-invalid selectors, 404 for a well-formed non-approved selector, 409 for duplicate identity, and 503 for missing/corrupt/unavailable input or context with no partial response. The response is validated against strict C4 v2 runtime models while C4 v0/v1, C7/C8, and C9 status are unchanged.

The existing `trackb-rule-v1` storage-target rule, POONDI thresholds from `docs/trackb/BACKTEST_RESULTS.json`, source capacity assumption, and recorded target defaults are applied without retuning. Replay identity excludes wall-clock time and binds source hashes, selector/line, algorithm/configuration hash, and normalized input hash. Receipt time is separate. The observed rule evaluation produced `Warning` with rule-evidence score 0.75; this is **derived storage-rule output**, not a historical alert. It contains no flood-depth result. Rainfall units remain undocumented/inferred, and the confidence score is not calibrated probability. A valid no-alert envelope uses `not_produced` with null alert/hash.

Current local deterministic identity/evidence:

- Replay run ID: `sha256:9b7d9b8e906ad09b3a0b60b0bbafd0c509c6a925d6bd7be77fc2b217dd788860`.
- Configuration SHA-256: `b2d4f49c2961a5f20d55302786230a3029c6f4863ffa785241d288f4e21f65fb`.
- Normalized input SHA-256: `3797ce61875445e5c3726e0d0fcdee4f3cd8e625cd501d08a4faa7f3a1c4271f`.
- A local evaluation produced output SHA-256 `8727d0e69aa612b90e762b8b35453b4b0d4c057b09304fcd4db86a6b4e2081b7`; this hash covers the generated alert, including its actual processing receipt timestamp, and can therefore differ on another replay. No output hash was hard-coded.

## Backend and packaged UI

The B11 backend exposes the same GET route only when `TWINGUARD_B13_ENABLED=true`; default configuration is disabled. It validates the AI response's selector, REPLAY/date-only identity, source hashes, received time, run/config/input hashes and produced/not-produced envelope, then passes through the body/status unchanged. Upstream failures return a sanitized 503. Backend CORS is limited to `http://127.0.0.1:8081`, GET, and `Accept`, with credentials disabled. B11 Compose enables this route and points only to the local `ai-service` app tier. No database service or writable data mount was added.

The packaged UI adds a separate Historical replay input view. It labels the archived row REPLAY and the rule result derived, shows raw source values, source/context provenance, unknown observation time/timezone, receipt time, hashes, rule limitations, and an explicit no-output state that never implies dry/safe. The UI makes a read-only GET with credentials omitted.

A packaged runtime check passed at the time the rebuilt B11 stack was started: AI/backend/frontend health returned 200; AI and backend exact GET returned 200; date-only/null/raw-row/provenance/run-identity assertions passed; the backend CORS preflight allowed only the specified origin/method/header and rejected a different origin, POST, and `X-Other`; the frontend index and compiled bundle were served. The runtime response was `Warning` derived output (runtime output SHA-256 `9243ac618d60a0e2122476dafdf0f6cdb09f0805eb53810172089879636fbd14`).

After those checks, the Docker Linux daemon became unreachable. `docker info`, browser navigation to the packaged localhost UI, and the stop-only Compose command all failed with a missing Docker engine pipe. The earlier runtime checks remain evidence for the built image, but service shutdown and current container status could not be confirmed, and visual browser rendering was not verified. No volume removal/prune was run. The pre-existing `tiwnguard-db-1` container was not targeted; it was observed running before the daemon became unavailable.

## Checks

- `.venv\Scripts\python.exe -m pytest tests\ai_service\test_b13_replay_lookup.py tests\ai_service\test_api.py tests\packaging\test_b13_replay_vertical_slice.py -q --import-mode=importlib` — **34 passed**, one Starlette/httpx deprecation warning.
- Frontend replay checks using the installed TypeScript/React server-renderer — **passed** for selector encoding, date-only validation, loading, error, provenance, derived/no-output display, and credentials omitted.
- `cd frontend; npm run build` — **passed**; Vite reports the existing large bundle warning.
- `mvn -q -o test` — **passed** (backend suite).
- `python tools/validate_api_contracts.py` — **PASS**, AI 12 paths/12 operations; backend 11 paths/12 operations.
- `docker compose -f docker-compose.b11.yml config --quiet` — **passed** before Docker daemon loss; app-tier-only runtime checks were scoped to frontend/AI/backend.
- `.venv\Scripts\python.exe -m py_compile services\ai-service\app\main.py` and `git diff --check` — **passed**.
- Full Python suite checkpoint: **306 passed, 1 skipped, 1 failed**. The failure is `tests/packaging/test_b11_packaging.py::test_backend_mounts_only_a20_scenario_assets_read_only`, whose pre-B27 exact environment allowlist does not yet include the registered B27 enable/base-URL settings. That test is outside B27's registered output paths and was not changed.
- Raw audit: **157 files, 30,544,672,450 bytes, 157 hash matches, 0 without comparable hashes, 0 mismatches**.
- No database access/write, migration, volume cleanup, or live feed occurred.

## Limitations and follow-up

The B27 runtime path was exercised before Docker became unavailable. Current container stop state is unverified because the daemon pipe disappeared; the stop-only command was attempted and failed at that boundary. The packaged browser itself could not be reopened after the daemon loss. The older B11 packaging assertion still fails and requires a registered B11/integrator ownership update. G5 remains `not_ready`; B13 independent acceptance remains downstream. C3 source-time meaning/timezone remains unknown; no route/flood depth/live/safety claim is made.
