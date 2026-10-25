# Path ownership

| Owner | Paths |
|---|---|
| Lane A | Science pipelines, labels, depth, predictions, forecast, simulation, impact, routing, decision and experiment folders; `tests/science/` and existing Phase 8–10 tests; DB schemas labels/ml/impact/routing/decision; migrations 200–299. |
| Lane B | `pipelines/trackb/`, `services/trackb/`, `services/ai-service/`, `services/backend/`, `frontend/`, `infra/`, `compose.*` except `docker-compose.yml`, `.github/`, `docs/ui/`, `docs/trackb/`, its tests; schemas trackb/ui; migrations 100–199 and 300–399. |
| Integrator | Migrations 013–099, shared `requirements.txt`, `docker-compose.yml`, `README.md`, `docs/PROJECT_STATUS.md`, `DATA_MANIFEST.csv`, `DATA_LINEAGE.md`, and `docs/master/`. This bootstrap may add exactly one README link line. |

Lane status files are `docs/master/LANE_A_STATUS.md` and `LANE_B_STATUS.md`; integrator merges at gates. Existing shared-table changes must be additive nullable columns and logged in CHANGE_REQUESTS.md. Running tasks may not share output paths. `data/raw/` is read-only. Do not stage or commit the other lane's currently dirty paths.

