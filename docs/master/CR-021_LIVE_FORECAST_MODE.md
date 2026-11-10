# CR-021 — Live forecast mode (Round 2 "live stage")

**Decision:** OD-2026-11-10. The project owner delegated this decision to the coordinator session ("run by your order"), which relayed it to the Integrator on 2026-11-10. This is a local educational prototype. It is **not** an operational warning service.

## What live mode does

1. **Automatic cycle every 3 h** (with catch-up at start-up):
   - fetch the A23 multi-model Open-Meteo forecast grid;
   - reuse a CFM-DSS reservoir snapshot that is no more than 24 h old, or fetch a new one (at most once a day);
   - apply A28's documented coupling rule;
   - run the engine for 72 h citywide at 120 m (GPU when available, CPU fallback);
   - publish the result as the latest live run.
2. **Manual "Refresh now":** `POST /v3/live/refresh`, at most once per 600 s.
3. **Run handling:**
   - No overlapping runs: a single live lock, and the queue rules of the existing engine still apply.
   - Keep the last 16 live runs (2 days). Older live runs are pruned; event, what-if and custom runs are untouched.
   - If a cycle fails, keep serving the last good run and report the error in `/v3/live/status`.
4. **UI:**
   - A run-dependent badge (LIVE FORECAST with the run time, or REPLAY, or WHAT-IF) replaces the fixed DEMO badge.
   - The permanent note "Model forecast — not an official warning" is always shown.

## What it amends (and only for this purpose)

| Earlier rule | Amendment |
|---|---|
| OD-2026-11-07 §7: on-demand fetches only, no background polling | A scheduled fetch every 3 h plus manual refresh (minimum 600 s) is allowed for live mode. No other background polling is allowed. |
| CR-014 (Overview weather context, at most every 30 min while Overview is active) | Unchanged for the weather panel. Live mode uses its own forecast-grid fetch. |
| CR-015 (one A23 snapshot) | Already superseded by OD-2026-11-07 §7. Live mode reuses the A23 lattice fetcher within the free-tier limits. |
| CR-016: CFM-DSS reads are low-volume and on demand; do not poll; do not retain; no model recomputation; **do not infer inflow, outflow or releases** | Live mode may read the public dashboard **at most once a day** (plus at most one manual read when the snapshot is more than 24 h old). It may keep the snapshot only inside a live run's provenance, for that run's retention period. It may use the snapshot as model forcing **through A28's documented assumption rule**. The resulting outlet inflows are model assumptions, labelled as such. **They are never presented as observed or published releases.** All other CR-016 boundaries remain: no redistribution of raw responses, no credentials, no endorsement claim, and C3 date-only semantics. |
| CR-017 (`/reservoirs/history` makes no cache, schedule or recomputation) | That endpoint is unchanged. The live scheduler uses the B41 client separately, under the daily limit above. |
| CR-018 (GET-only proxy, no polling) | The UI may poll `GET /v3/live/status` every 60 s (a local AI-service endpoint, not an upstream source). `POST /v3/live/refresh` passes through the existing `/api/ai/v3/` block, which already allows POST. |

**Free-tier budget:** one A23 lattice snapshot is about 240 location-calls (0.05° lattice, three models). Eight cycles a day is about 1,900, plus at most 144 manual refreshes, which in practice will be far fewer. The scheduler must count upstream calls per UTC day and stop fetching (returning 503 on refresh, and keeping the last good run) before reaching **5,000 calls a day**, half of Open-Meteo's published 10,000/day free-tier figure. On HTTP 429 it backs off once, as A23's fetcher already does.

## Contract (C4 v3, additive; `planned_paths` until mounted)

| Operation | Purpose |
|---|---|
| `GET /v3/live/status` → `LiveStatus` | Enabled flag, 3 h cycle, state, latest run, last good run, next scheduled time, manual-refresh window, `sources.open_meteo` / `sources.cfm_dss` (`SourceHealth`), last error, retention, disclaimer |
| `GET /v3/live/latest` → `LiveLatest` | Latest live run: run_id, run_kind LIVE_FORECAST, issued and valid times, summary, inputs with their source modes, device, disclaimer. 404 before the first run, 503 when disabled. |
| `POST /v3/live/refresh` → 202 `LiveRefreshAccepted` | Returns `started` or `already_running`. 429 inside 600 s; 503 when disabled or over budget. |

**Changes to existing schemas:**
- `SimulationRun` gains `run_kind` (LIVE_FORECAST / REPLAY / WHAT_IF / CUSTOM / FORECAST), `mode: live`, and a `live` block (cycle, issued and valid times, reservoir `source_date`, coupling rule id, disclaimer).
- `Overview` gains `live`, and `badge` is widened to the run-dependent values.

**Note on "source_mode LIVE_FORECAST":** the coordinator asked for `source_mode` LIVE_FORECAST on runs. The contract carries it as `run_kind` instead. `source_mode` states the provenance class of a value: results stay SIMULATED, and inputs stay MODEL_FORECAST or PUBLISHED_SNAPSHOT. Putting LIVE_FORECAST there would blur the binding rule that no simulated value may look observed. The UI badge reads `run_kind`.

## Tasks (disjoint ownership)

| Task | Lane | Owns | Starts |
|---|---|---|---|
| A28 | A | `services/flood_engine/`, `pipelines/`, `data/features/`, `tests/flood_engine/` | now |
| B51 | B | `services/ai-service/`, `docker-compose*.yml`, `tests/ai_service/`, `tests/packaging/` | now (stubs A28's coupling until it lands) |
| B52 | UI session | `frontend/`, `tests/ui/`, `tools/ui/`, `docs/ui/` | after B51 |
| B53 | B, with UI screenshots | evidence under `docs/trackb/` and `docs/ui/screenshots/` | after A28, B51 and B52 |
| I27 | I | Round 2 review | after B53 |
