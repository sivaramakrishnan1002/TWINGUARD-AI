# CR-008 — B08 deterministic artifact selectors

**Status:** Approved by the project owner on 2026-10-29 for the bounded, versioned selector change below. C4 v0 and C7/C8 remain frozen and unchanged; implementation and runtime behavior remain subject to I14 validation and B08 acceptance.

## Project-owner decision

The project owner approved this proposal on 2026-10-29: use the existing A07 `scenario_key` with `run_id` and `valid_at` to select exactly one saved impact result; add a distinct read-only saved-route lookup by `result_id`, explicitly scoped to A09 revision 3; keep `POST /route` unavailable because the saved A09 data has no evidenced integer run mapping. Keep C7/C8 response bodies unchanged, preserve all simulation and provenance limits, and do not enable live/shared-database behavior. Lane A's confirmation is recorded in `docs/CR008_LANEA_SELECTOR_EVIDENCE.md`.

I14 implemented this as a separately versioned C4 v1 request/operation delta in `docs/master/contracts/c4_openapi_v1.md`. The frozen C4 v0 baseline and C7/C8 result bodies remain unchanged. OpenAPI additions remain design-only until B08 runtime conformance passes.

## I14 implementation and verification

The AI and backend OpenAPI projections now document the same required A07 selector and the same saved A09 revision-3 result lookup, with explicit 404 behavior and runtime-unavailable markers. The existing `POST /route` computation operation remains unavailable. The projection test verifies cross-spec selector parity and checks all 75 A07 keys and 216 revision-3 A09 IDs for uniqueness while confirming route `run_id` is null.

Checks: `tools/validate_api_contracts.py` passed (AI 10 paths/10 operations; backend 10 paths/11 operations); `tests/master/test_api_contract_projection.py` passed (6 tests); `git diff --check` passed. The broader AI-service test selection had 30 passes and one expected B08 handoff failure: its generated-runtime-schema equality assertion still compares the intentionally unimplemented v0 `RunTimeRequest` against the approved v1 OpenAPI request. No AI runtime code was changed; B08 must implement and test the v1 request before exposing results. The G0 v0 checklist/report and frozen C4 v0 were not changed; this additive, design-only request/operation delta does not require G0 reassessment. G0 must still be checked after I14 is finished and no task is running.

## Verified blocker

The frozen C4 `RunTimeRequest` requires `run_id` and `valid_at`; its only other field is optional `zone_ids`. It has no A07 scenario selector. The AI `RouteRequest` requires `run_id`, `departure_at`, `origin`, and `destination`, with optional `mode` and minimum accessibility probability; it has no A09 `result_id`, `scenario_key`, or method selector. These shapes are recorded in `docs/master/contracts/c4_openapi_v0.md`, `docs/api/ai-service.yaml`, `services/ai-service/app/main.py`, and the backend projection.

Read-only checks of the owner-produced artifacts confirm:

- A07 V4 has 75 records, all `run_id=7004`, at 15 valid times. Every `(run_id, valid_at_utc)` has five records, one per scenario. `scenario_key` is present and `(run_id, valid_at_utc, scenario_key)` uniquely identifies all 75 records; `result_id` is also unique. The frozen request cannot carry the scenario key, so selecting by its current fields is ambiguous.
- A09 revision 3 has 216 records; every `run_id` is null and every `result_id` is unique. The artifact contains three scenario keys and four methods. Groups matching the current non-run route request fields (`departure_at_utc`, origin, destination, mode) contain four records. The required integer `run_id` has no artifact mapping, and choosing a method or result from the current request would be invented.
- Existing focused tests validate all 75 A07 and 216 A09 rows against the Track B response models and assert the A09 null run IDs. B08 tests keep ambiguous impact and unsupported route behavior unavailable. The projections and result DTOs agree; the failure is selection semantics, not a reason to weaken the frozen result schemas.

Evidence paths:

- `data/features/impact/batch2_v4_contract/impact_results.jsonl`
- `data/features/routing/results/batch2_v1/revision_3/route_results.jsonl`
- `docs/master/contracts/c4_openapi_v0.md`, `docs/master/contracts/c7_impact_v0.md`, `docs/master/contracts/c8_routing_v0.md`
- `docs/api/ai-service.yaml`, `docs/api/backend.yaml`
- `services/ai-service/app/main.py`, `services/backend/src/main/java/org/twinguard/backend/dto/ImpactResponse.java`, `services/backend/src/main/java/org/twinguard/backend/dto/RouteResponse.java`
- `tests/ai_service/test_api.py`, `tests/master/test_api_contract_projection.py`, `services/backend/src/test/java/org/twinguard/backend/GatewayContractTest.java`
- `docs/trackb/TRACKB_REPORT.md` (B08 2026-10-29 review)

## Proposed bounded resolution

1. Give `/impact` a dedicated request schema with required `run_id`, `valid_at`, and `scenario_key`. Resolve only the exact registered A07 tuple; return the documented not-found response when there is no exact result. Keep the C7 result body unchanged.
2. Add a distinct read-only saved-result operation, proposed as `GET /route-results/{result_id}`, resolving only an exact A09 result ID from the registered revision 3 artifact. This is retrieval of an existing simulated record, not route computation. Keep `POST /route` unavailable because its current run-based request has no evidence-backed mapping to A09's null `run_id` records. Keep the C8 response body unchanged.
3. Keep forecast, uncertainty, and C4 `/scenario` unavailable until their registered A05/A13 artifacts have explicit compatible request/result identities and response semantics. Keep I07's C9 visualization operations separate.
4. Do not select a default scenario, infer a route run ID, or imply that the simulated results are operational, scientifically validated, or safe.

The proposed selectors use fields already present in the frozen C7/C8 result artifacts. The request/operation changes still change C4 semantics and therefore require explicit approval and a versioned change under the contract protocol. If the project owner rejects this approach, the alternative is an owner-scoped Lane A task to produce and test a versioned route identity/request mapping; no such mapping may be inferred by B08.

### Lane A confirmation

Lane A recorded read-only confirmation in `docs/CR008_LANEA_SELECTOR_EVIDENCE.md`, commit `e3161b59632ae2a50b5c582ae0ce278af81d25be`. It confirms all A07 scenario keys and unique `(run_id, valid_at_utc, scenario_key)` tuples; all A09 result IDs are unique within the saved revision 3 file; and no integer route run mapping exists. The A09 `result_id` is revision-3 scoped, not a global content identifier, and does not supply the run ID required by the frozen route-computation request. The confirmation expressly does not approve API behavior or revise contracts. It satisfies the Lane A evidence prerequisite only.

## Owners and affected artifacts

- **Project owner:** decide whether to approve the proposed selectors or require another owner-supported mapping. Until recorded approval, no frozen contract or API projection changes.
- **Lane A:** selector evidence is confirmed for the saved outputs as bounded above. No Lane A implementation change is requested by this proposal; no global identity or run mapping is claimed.
- **Integrator:** if approved, version the C4 request/operation semantics through change control and reconcile both `docs/api/ai-service.yaml` and `docs/api/backend.yaml`. C7/C8 response schemas remain unchanged unless evidence demonstrates a separate response change is needed and that change is separately approved.
- **Track B:** only after the approved C4 projection and selectors are available, resume B08 to implement bounded read-only artifact lookup and focused tests. Maintain 501/unavailable behavior until each operation passes its acceptance.
- **Tests:** update OpenAPI structural/model-projection tests, AI endpoint selector tests (exact match, missing/unknown selector, duplicate match fail-closed, 501 while unavailable, no database access), and backend DTO/projection tests if the backend exposes the retrieval projection. Validate all owner-produced A07/A09 records and preserve null/NoData, provenance, source mode, units, and timestamp semantics.
- **Downstream:** B11 packaging, B13 full-stack replay, B17 scenario asset serving, and I08 acceptance remain gated on their registered dependencies and must consume only the approved operation semantics. No downstream task becomes ready from this proposal alone.

## Gate and runtime boundary

G0 remains recorded `ready`; C1-C8 remain frozen at v0. This proposal does not itself invalidate G0's evidence that the current OpenAPI projections match the current frozen DTO/result schemas. Before any approved C4 revision is published or implemented, I14 must determine from `GATES.md` whether the formal change requires gate reassessment and complete that process if required. No live feed, shared database access/write, deployment, or API enablement is authorized here.
