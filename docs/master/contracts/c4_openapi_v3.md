# C4 v3 — product simulation and decision API (proposed)

**Status:** proposed and unfrozen. Contract-first design under CR-019 / OD-2026-11-07. The machine-readable source is `docs/api/ai-service.yaml`, top-level key `x-c4-v3-product-api` (OpenAPI 3.1 path items and component schemas, with an example for every response). All 19 operations are mounted by B47 (commit d5a45e9) and carry `x-current-runtime-status: 200` inside the section.

C4 v0 (frozen), v1 (CR-008) and v2 (CR-012) are unchanged. C7/C8 remain frozen. v3 is additive and lives under `/v3` on the AI service. The UI reaches it through the same-origin `/api/ai/` proxy (CR-018).

## Promotion rule

B47 moves an operation from `x-c4-v3-product-api.paths` into the top-level `paths` (with `x-current-runtime-status: 200`) only when it is mounted and its focused tests pass. `tests/ai_service/test_api.py` requires every top-level path to exist at runtime. Changing a field name, unit or enum needs an Integrator edit of this contract.

## Conventions

| Topic | Rule |
|---|---|
| Time | RFC 3339 UTC (`Z`). Date-only historical sources keep the C3 `source_date` semantics. |
| Units | Depth, height and tide in m; distance in m; duration in s; rainfall in mm per interval; flow in m³/s (1 m³/s = 35.3147 cusecs); area in km²; population in people |
| CRS | Grids use EPSG:32644 with the origin at the upper-left and row 0 at the north. GeoJSON and `LonLat` use WGS84. |
| Grid size | `GridSpec.cell_size_m` ∈ {30, 90, 100, 120, 600}. 600 m is the interim A06/A23 engine grid (88×69) served until A25 bundles exist. This additive change was made on 2026-11-07 at the request of Lane B and the UI session. |
| Nulls | `null` means unknown or outside the domain, never zero. A depth of `0` means modelled dry. |
| Provenance | Every result has `source_mode` ∈ {SIMULATED, MODEL_FORECAST, PUBLISHED_SNAPSHOT, SCENARIO_INPUT, REPLAY, STATIC_REFERENCE}. Incidents have `generated: true`. Resources are `SCENARIO_INPUT`. |
| Errors | `ApiError {detail, code, retry_after_s}` with codes 400, 404, 409 (run in progress or version conflict), 422, 429 (minimum interval not elapsed; `Retry-After` set) and 503 (no partial body) |
| UI | One "DEMO / SIMULATION" badge. `limitations` holds at most 5 short thesis notes. |
| Secrets | No endpoint accepts or returns the Google Map Tiles key. |

## Operations by tab

| Tab | Operation | Purpose |
|---|---|---|
| 1 Situation Overview | `GET /v3/overview`, `GET /v3/weather`, `GET /reservoirs/history` (existing, CR-017) | Aggregate of latest run, weather, reservoir, incident counts and top wards |
| 2 Flood Simulation | `GET /v3/events`, `POST /v3/simulations`, `GET /v3/simulations`, `GET /v3/simulations/{run_id}`, `GET /v3/simulations/{run_id}/depth`, `GET /v3/simulations/{run_id}/wards` | Event, custom-rainfall or forecast runs; timeline frames; depth grids; per-ward summaries |
| 3 Emergency Support | `GET /v3/simulations/{run_id}/incidents`, `GET /v3/simulations/{run_id}/shelters`, `GET`/`PUT /v3/scenario-resources`, `GET /v3/simulations/{run_id}/emergency-plan` | Generated incidents, shelter reachability and allocation, owner-set resources, greedy assignment |
| 4 Road Routing | `GET /v3/simulations/{run_id}/roads`, `POST /v3/routes` | Three-state edges (ASSESSED_PASSABLE / ASSESSED_BLOCKED / UNKNOWN). Route status is ASSESSED_PASSABLE, CONDITIONAL or NO_ROUTE, plus a dry baseline. |
| 5 What-if Simulation | `POST /v3/simulations` (`mode=what_if`), `GET /v3/simulations/{run_id}/comparison` | Rainfall %, reservoir release in m³/s, tide offset in m; deltas against the base run |
| 6 Reservoir Monitoring | `GET /reservoirs/history` (existing) | CFM-DSS public snapshot (`PUBLISHED_SNAPSHOT`) |
| 7 Digital Twin 3D City | `GET /v3/simulations/{run_id}/depth`, `GET /v3/simulations/{run_id}/buildings`, `GET /v3/static/{layer}` | Draped or extruded water surface, per-building max depth (382,294 OSM footprints, paged and bbox-filtered), ward/building/shelter/focus-area GeoJSON |
| All | `GET /v3/status` | Engine, queue and weather-cache state |

## Key request shapes

- `SimulationRequest`:
  - `mode` ∈ {event, custom, forecast, what_if}
  - `event_key`
  - `custom_rainfall {start_time_utc, interval_minutes ∈ {15, 30, 60}, values_mm[]}`
  - `what_if {base_run_id, rainfall_scale_pct 0–300, reservoir_release_m3s {CHEMBARAMBAKKAM|POONDI|PUZHAL|CHOLAVARAM: 0–3000}, tide_offset_m −1…2}`
  - `duration_hours` 6–72
  - `resolution` ∈ {citywide (90–120 m), focus (30 m)}
  - `focus_area` ∈ {VELACHERY, ADYAR, T_NAGAR, PORUR}
  - `frame_interval_minutes` ∈ {15, 30}
- `RouteSearchRequest` (renamed from `RouteRequest` on 2026-11-08, because C4 v1 owns that name):
  - `run_id`, `frame_index`
  - `origin` and `destination` as `LonLat`
  - `policy` ∈ {avoid_blocked, avoid_blocked_and_unknown, shortest_dry}
  - `profile` ∈ {car, emergency_vehicle, walk}
  - `blocked_depth_threshold_m` (default 0.3)

## Runtime rules

- One simulation runs at a time; at most 4 more can queue. An identical request or identical forcing returns `state: cached`.
- `mode=forecast` and `GET /v3/weather?refresh=true` fetch Open-Meteo on demand, subject to the 600 s minimum interval and response caching. There is no background polling, and the draft scheduler stays disabled.
- Depth frames are JSON arrays rounded to 0.01 m. B47 may add a binary Float32 variant only as an additive change to this contract.

## Change log

- **2026-11-07:** `GridSpec.cell_size_m` adds 600 (the interim A06/A23 grid).
- **2026-11-08:** `Comparison.delta` now uses `SummaryDelta`, with nullable fields and no minimums, so what-if decreases can be negative.
- **2026-11-08 promotion status:** all 19 operations are mounted by B47 (commit d5a45e9). Promotion into top-level `paths` waits on two things:
  - the runtime OpenAPI declaring each contract error response;
  - request-body models being named `SimulationRequest`, `RouteRequest` and `ResourceSet`, which `tests/ai_service/test_api.py` requires.
- **2026-11-08 promotion:**
  - The v3 `RouteRequest` schema is renamed `RouteSearchRequest`, because C4 v1's `/route` body already uses `RouteRequest`.
  - All 19 operations are copied into top-level `paths` with `x-current-runtime-status: 200`, after B47 declared the contract error responses and renamed its request models to the contract names (commit baa47f6).
  - The schemas stay under `x-c4-v3-product-api`.
  - The `test_api.py` runtime-parity test passes.
- **2026-11-08 device fields (OD-2026-11-08), additive and optional:**
  - `EngineStatus.device` = {requested auto|cuda|cpu, resolved cuda|cpu, name, cuda_available, gpu_jobs_max = 1}.
  - `Provenance.device` = {used cuda|cpu, name, fallback_reason}.
  - Requested by Lane B (B47).

