# G4 Gate Review — forecast through shelter API — 2026-11-07

**Current gate decision: FAIL**

Reviewer: Integrator (Lane I) session. Scope per `docs/master/GATES.md`: "Forecast through shelter API" (`MASTER_PLAN.md`: "Forecast-to-shelter API"). Required tasks: A05 (Phase 11 forecast/hindcast) and A10 (Phase 16 shelter allocation). Both are `done_with_caveats`, so `gate_check.py G4` reports its prerequisites as complete. The chain between them was also reviewed: A06 simulation, A07 impact, A08 routing graph, A09 routing comparison, and B08 AI endpoints.

The scientific **forecast → simulation → impact → routing → shelter chain exists and passes with caveats**, as simulated research artifacts. The **API criterion fails**: no API serves forecast or shelter results. G4 therefore stays `not_ready`, and repair tasks are registered for the owning lanes below.

## Owner-accepted protocol deviation

Lanes did not stop for this gate. A23 (Lane A, lock held) and the UI redesign kept running with the project owner's approval, because G4 reviews completed tasks. Their paths were not edited and their locks were not touched. A23 reads A05/A06 outputs but writes only to its own registered paths, so it does not affect the reviewed evidence.

## Criterion review

| # | Criterion | Decision | Evidence | Binding caveats |
|---|---|---|---|---|
| G4.1 | Forecast/hindcast depth ensembles at 6/12/24/48/72 h (A05) | PASS_WITH_CAVEATS | `docs/PHASE11_FORECAST_BATCH2.md`; `data/features/forecast/batch2_v1/forecast_summary.json`; `tests/phase11/` | 300 deterministic CPU runs: 3 event windows × 5 rainfall scenarios × 20 A06 members, max mass-balance error 0.591%. **These are hindcasts, not forecasts.** No archived NWP exists for 2015, so "perfect foresight" uses observed IMERG and the error scenarios are IMERG/ERA5 product disagreement. There is no observed lead-time depth validation and no operational forecast skill. 600 m grid. A15 notes that the A05/A06 TIFF bands lack explicit unit tags (metres per the docs). |
| G4.2 | Simulation, impact and routing chain (A06→A07→A08→A09) | PASS_WITH_CAVEATS | `docs/PHASE12_SIMULATION.md`; `docs/PHASE13_IMPACT_BATCH2_V4.md`; `data/features/impact/batch2_v4_contract/run_summary.json`; `docs/ROUTING_GRAPH_BATCH2.md`; `docs/ROUTING_BATCH2.md`; `data/features/routing/results/batch2_v1/revision_3/summary.json`; `docs/VALIDATION_REPORT.md` | A06: 600 m local-inertial NumPy solver, 20 members, mass balance <1%, no drain network, GLO-30 is not a building DSM, no independent depth truth. A07: 75 outputs and 4,500 member-threshold rows; access is a coarse graph proxy. A08: 1,500 snapshots, with unknown/unassessed coverage. A09: 216 route records from a simulated OSSE with member 20 held out as truth. **Simulated research results only; no passability or safe-route claim.** |
| G4.3 | Shelter allocation under flood access (A10) | PASS_WITH_CAVEATS | `docs/SHELTER_ALLOCATION_BATCH2.md`; `data/features/decision/shelters/batch2_v3/`; `tests/decision/test_shelter_allocation.py` | Final corrected run **batch2_v3**: 540 cases, 293,374 detail rows, accounting reconciled. v1 and v2 are kept; v2 mislabelled unserved demand. Candidates are 102 OSM shelters plus 559 schools and 134 colleges, **as an assumption**. Capacities of 100/250/500 people are hypothetical, with sensitivity factors 0.5/1/2. Allocation is greedy by planar distance within weak components; it is not travel-time pathfinding. WorldPop NoData is kept. Not evacuation guidance and not verified shelter capacity or status. The A10 output registry named `batch2_v1/`; this review adds `batch2_v3/` as the final output. |
| G4.4 | **Forecast-through-shelter API** | **FAIL** | `services/ai-service/app/main.py`; `docs/api/ai-service.yaml`; `docs/api/backend.yaml`; `services/backend/src/main/java/org/twinguard/backend/adapter/notconfigured/NotConfiguredTrackBAdapter.java`; `docs/master/LIVE_DATA_INTEGRATION_MAP.md` | **AI `POST /forecast`, `POST /uncertainty` and `POST /route` return HTTP 501.** The only result endpoints are B08's saved-artifact lookups: `POST /impact` (exact A07 selector) and `GET /route-results/{result_id}` (A09 revision 3). **No AI shelter operation exists.** Backend `GET /shelters` is declared in OpenAPI with `x-current-runtime-status: unexposed`, has no controller, and its port is `NotConfiguredTrackBAdapter`. The frozen C4 v0 `Shelter` schema (`facility_id`, `capacity_people`, `accessibility_probability`) does not represent A10's case-level served/unserved/unreachable results. No A05 forecast artifact selector or A10 result schema has passed change control. |

## Repair tasks registered (owning lanes)

Each task is registered in `docs/master/STATE.json`. **B46 has been added to G4's `requires`**, so `gate_check.py G4` now fails closed until the repair is complete.

| Task | Lane | Status at registration | Purpose |
|---|---|---|---|
| **A24** | A | `ready` | Publish the versioned A10 batch2_v3 shelter-allocation result schema and the A05 forecast-artifact selector evidence (unique keys, units, UTC times, provenance, NoData, SIMULATED/hindcast labels), with serialization tests. No new computation; existing outputs stay unchanged. |
| **I26** | I | `blocked_prerequisite` (A24) | Change control (proposed CR-019). Draft an additive, read-only C4 projection for saved A05 forecast and A10 shelter results without altering frozen C4 v0/v1/v2 or C7/C8. Project-owner approval is required before B46. |
| **B46** | B | `blocked_prerequisite` (I26, A24, B08) | Mount the approved read-only saved-forecast and shelter-allocation endpoints in the AI service (and gateway if approved), fail-closed, with focused tests. No live, shared-DB or safety claims. |

The C4 v0 operations `POST /forecast` and `POST /route` (new computation) stay 501 unless separately approved. G4 asks for results served through an API, not live recomputation. Re-review G4 after B46 completes.

## Shared checks for G1–G4 (run 2026-11-07, this session)

| Check | Command | Result |
|---|---|---|
| Gate prerequisites | `.venv\Scripts\python.exe tools\master\gate_check.py G1` … `G4` | All four exited 0 with "READY for integrator gate checklist; all listed task prerequisites are complete". This happened before B46 was added to G4. |
| State integrity | `.venv\Scripts\python.exe tools\master\verify_state.py` | exit 0, no evidence drift. 16 migrations on disk. Shared DB read-only: 14 applied migrations, 1,319,380 grid cells. |
| Focused G4 suites | `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib -p no:cacheprovider tests/phase11 tests/phase12 tests/phase13 tests/routing tests/decision tests/ai_service` | **150 passed**, 1 existing Starlette/httpx deprecation warning |
| Master/control tests | `... pytest ... tests/master` | **26 passed** |
| API contract validator | `.venv\Scripts\python.exe tools\validate_api_contracts.py` | PASS. AI: OpenAPI 3.1.0, 13 paths/13 operations. Backend: OpenAPI 3.1.0, 11 paths/12 operations. |
| Full Python suite | `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib -p no:cacheprovider` | **369 passed, 1 skipped** (env-gated isolated PostgreSQL test), 115 subtests passed, 1 existing deprecation warning, 157.8 s. This ran while A23 and the UI session were active, so it reflects the working tree at that moment, including their uncommitted files. |
| Backend suite | `mvn -o -B -ntp -q -f services/backend/pom.xml test` | exit 0; surefire: 30 tests, 0 failures, 0 errors, 0 skipped |
| Raw audit | `.venv\Scripts\python.exe tools\audit_raw_logs.py` | `DATA_FILES=157; DATA_BYTES=30544672450; HASH_MATCH=157; NO_COMPARABLE_HASH=0; MISMATCH=0` |
| Migration numbering | inspected `database/migrations/` | unique 001–014, 100, 101; none applied |
| Requirements merge | `git log --since=2026-10-28 -- requirements*.txt`; `.venv\Scripts\python.exe -m pip check` | The only changes are 6bb49c4 (A16 MLflow) and e6f201c, which commits the G0/I13 pins `pyarrow==25.0.1` and `certifi==2026.10.23` recorded in `docs/master/REQUIREMENTS_GATE_RECONCILIATION.md`. The installed versions match. `pip check`: "No broken requirements found." |
| End-to-end | not run | The API path fails at G4.4, so there is no forecast-to-shelter route to exercise. No Docker service was started. |
| Backup | not required | No DB write, migration or Docker operation. No dump, tag or push. No volume touched. |

## Decision

G4 is **FAIL** and stays `not_ready`. The science chain is complete as simulated, assumption-labelled research output. The gate's API requirement is not met: forecast operations are 501, and there is no shelter API. Repairs A24 → I26 → B46 are registered. No lane-owned file, database, Docker volume, tag or push was changed or created by this review.


## G4 re-review after B47 — 2026-11-08

**Current gate decision: PASS_WITH_CAVEATS**

On 2026-11-07, OD-2026-11-07 / CR-019 replaced the G4 repair chain A24/I26/B46 with B47, the C4 v3 simulation and decision API. G4 now requires A05, A10 and B47. Under the owner's relaxed caveat policy, `done_with_caveats` counts as done. B47 was finished as `done_with_caveats` at 2026-11-08 09:49 IST with commit `d5a45e9`. This supersedes the 2026-11-07 FAIL above, which stays as history. `STATE.json` records G4 as `ready`.

| # | Criterion | Decision | Evidence |
|---|---|---|---|
| G4.1–G4.3 | Forecast, chain and shelter science | PASS_WITH_CAVEATS (unchanged) | See the criterion table above |
| G4.4 | Forecast-through-shelter API | PASS_WITH_CAVEATS | **Mounted operations:** B47 (`services/ai-service/app/v3/`, mounted in `app/main.py`, commit d5a45e9) exposes all 19 C4 v3 operations; runtime and contract operation sets match exactly (Lane B's "21 operations" count is a miscount). **Integrator probe:** on B47's synthetic fixture (no network, temp run store), `POST /v3/simulations {"mode":"forecast"}` completed run `sim-20261108T042702Z-0a74b15b` with 12 frames and an Open-Meteo input labelled `MODEL_FORECAST`. On that run, `/depth`, `/roads` (three states only), `/shelters` (3 shelters, 2 reachable, capacities `assumed`) and `/incidents` (22, all `generated: true`) each returned 200, and each body validated against `x-c4-v3-product-api`. **Tests:** `pytest tests/ai_service tests/master` gives 164 passed. Lane B reports 39 focused v3 tests, a full suite of 420 passed and 1 skipped, the validator passing and the raw audit at 157/157. |

**Caveats (short, thesis-style):**
- The Integrator probe used the synthetic fixture. Runs on project data use the interim 600 m A06/A23 grid until A25's 120 m/30 m bundle is installed.
- Shelter capacities are assumptions and incidents are generated, both labelled as such.
- The 5 failing subtests in `tests/packaging/test_frontend_demo_only.py` that Lane B reports are UI labels tied to B48, not the API.

**Contract follow-up (not a gate blocker):** the v3 operations stay in `x-c4-v3-product-api`, now marked `x-current-runtime-status: 200`. A trial promotion into top-level `paths` (reverted) failed `tests/ai_service/test_api.py::test_generated_openapi_matches_contract_routes_and_operation_ids` (line 111), for two reasons:
- 17 of the 19 runtime operations do not declare the contract's error responses in FastAPI's `responses=`.
- The request bodies are named `V3SimulationRequest`, `V3RouteRequest` and `V3ResourceSet` instead of `SimulationRequest`, `RouteRequest` and `ResourceSet`.

Both are Lane B code fixes. The Integrator promotes the operations once they are fixed.

**Contract change made in this re-review:** `Comparison.delta` now uses a new `SummaryDelta` schema. It has the same fields, all nullable, without non-negative minimums, and `peak_time_utc` is a nullable date-time, so what-if decreases can be negative. The validator passes.
