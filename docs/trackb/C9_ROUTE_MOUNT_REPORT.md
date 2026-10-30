# B21 — Approved C9 route mount evidence

Date: 2026-10-30

## Scope and contract status

B21 mounted only the CR-009 approved read-only operations in the AI service and Spring backend:

- `GET /scenario-visualization-assets`
- `GET /scenario-visualization-assets/{event_id}/{scenario_id}`

Both project from B17's A20 manifest and bounded saved assets. The output remains saved research/simulation evidence. C9 remains proposed and unfrozen; C1–C8 are unchanged. No live feeds, generated results, database access/writes, migrations, operational alerts, or route computation were added. Raster bytes are not served by these routes.

Invalid selectors/unexpected query or body input map to 400; exact misses to 404; duplicate/ambiguous identities to 409; missing, unreadable, changed, or integrity-failing assets to 503 without a partial result. Error bodies do not expose local paths or filesystem diagnostics. Exact saved timestamps, provenance, nulls, grid/CRS, units basis, member spread, NoData-as-unknown, coverage, and stated research limitations are retained from the manifest.

## Verification

- AI focused suite: `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib tests\ai_service` — **20 passed**.
- AI plus API conformance: `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib tests\ai_service tests\master\test_scenario_visualization_contract.py tests\master\test_api_contract_projection.py` — **58 passed**, one existing Starlette/httpx deprecation warning.
- Python compilation: `.venv\Scripts\python.exe -m compileall -q services\ai-service\app tests\ai_service` — passed.
- Focused Spring tests: `mvn -o -B -ntp -f services/backend/pom.xml '-Dtest=ScenarioVisualizationAssetsTest,ScenarioVisualizationControllerTest' test` — **11 passed**.
- Full backend tests: `mvn -o -B -ntp -f services/backend/pom.xml test` — **25 passed**.
- Quiet packaging validation: `docker compose -p twinguard-b11 -f docker-compose.b11.yml config --quiet` — passed.
- Local image builds: `docker compose -p twinguard-b11 -f docker-compose.b11.yml build --pull=false ai-service backend` — passed; no image pull was requested.
- Runtime smoke checks: both loopback services returned catalog and detail **200**, invalid date and unexpected selector **400**, exact miss **404**. AI `POST /route` with a valid request remained **501**; backend `/impact` remained **404**; POST to the catalog returned **405**. Responses were inspected only for status and bounded summary fields.
- Container mount inspection showed the A20 manifest-linked forecast, simulation, and visualization directories mounted `RW=false` in both apps. Existing AI impact/routing binds were also read-only. Backend mount scope is limited to the A20 manifest-linked asset directories.
- Stop-only shutdown completed. The three B11 containers were exited; no volume cleanup or prune ran. No named volumes were added by B21.
- Raw audit: `DATA_FILES=157; DATA_BYTES=30544672450; HASH_MATCH=157; NO_COMPARABLE_HASH=0; MISMATCH=0`.

## Limitation

`tests/packaging/test_b11_packaging.py` was also run: **4 passed, 1 failed**. Its existing `test_ai_mounts_only_registered_artifacts_read_only` asserts the pre-B21 two-mount list. B21 adds the three A20-linked read-only mounts required for both approved routes. The packaging test is outside B21's registered output list and was left unchanged; its owning task must reconcile that expectation. The B21-specific mount assertion and quiet Compose validation pass.

The live smoke used the local B11 app-tier only; it does not establish operational or live-source behavior. C9 is not frozen, and B18/I08 remain outside this task.
