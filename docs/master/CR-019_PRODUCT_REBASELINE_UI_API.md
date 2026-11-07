# CR-019 — Product rebaseline: reference-design UI, Google 3D Tiles and the C4 v3 simulation/decision API

**Decision:** approved by the project owner as OD-2026-11-07 (see `FINAL_YEAR_OWNER_DECISIONS.md`). Registered by the Integrator on 2026-11-07.

## Scope and disjoint ownership

| Task | Lane / session | Owns (disjoint) | Purpose |
|---|---|---|---|
| A25 | Lane A | `pipelines/`, `services/flood_engine/`, `data/features/`, Lane A tests (`tests/flood_engine/`, `tests/phase*/`, `tests/routing/`, `tests/decision/`, `tests/labels/`), and Lane A docs under `docs/` (not `docs/master/`, `docs/api/` or `docs/ui/`) | Run citywide simulation at 90–120 m plus 30 m focus areas, with per-building depth, per-ward summaries, building heights and a 15–30 min time series |
| B47 | Lane B | `services/ai-service/`, `services/backend/`, `services/trackb/`, `docker-compose*.yml`, `docker/`, `tests/ai_service/`, `tests/packaging/`, `tests/trackb/` | C4 v3 simulation and decision API, built from the draft `services/ai-service/app/live/router.py` |
| B48 | UI session (lane B id) | `frontend/`, `tests/ui/`, `tools/ui/`, `docs/ui/`, `.gitignore` | Rebuild the 7 tabs to the reference images with CesiumJS and Google Photorealistic 3D Tiles |
| Integrator | Lane I | `docs/master/`, `docs/api/`, `tools/master/` | Contract, registry and board |

**Contract first:** C4 v3 is in `docs/api/ai-service.yaml` § `x-c4-v3-product-api` (17 paths, 19 operations, with examples for every response). It is summarised in `contracts/c4_openapi_v3.md`. B47 and B48 work in parallel against it. B47 moves each operation into the top-level `paths` only when that operation is mounted and tested. Any change to field names or units goes through the Integrator.

## Superseded

- **CR-015's one-snapshot limit:** replaced by on-demand, cached fetches with a 600 s minimum interval and no background polling (OD-2026-11-07 §7). The draft router's `TWINGUARD_LIVE_SCHEDULE_MIN` background scheduler must stay disabled (0).
- **G4 repair chain A24/I26/B46:** superseded. A forecast and shelter API is now covered by B47's `POST /v3/simulations` (mode `forecast`/`event`) and `GET /v3/simulations/{run_id}/shelters`. G4 now requires B47 in place of B46.
- **Draft `/live/*` routes (CR-018):** to be folded into `/v3` by B47.

## Binding rules kept

- No fabricated value may be shown as observed. Every result carries a `source_mode`.
- Generated incidents are labelled `generated: true`. Resources are `SCENARIO_INPUT`.
- The Google key is never committed or served by any API, and Google attribution stays visible. `frontend/.env.local` is git-ignored (`.gitignore` `*.local`, added by the ui session on 2026-11-07).
- `data/raw/` stays read-only, and raw-audit hashes must keep matching.
- C1–C8 v0 stay frozen; C4 v3 is additive.
