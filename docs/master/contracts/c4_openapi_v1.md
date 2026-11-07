# C4 AI/backend API v1 — bounded saved-artifact selectors

**Status:** project-owner-approved post-G0 change-control contract, 2026-10-29. This is a separately versioned C4 request/operation delta. It does not rewrite the frozen C4 v0 document or change C7/C8 response bodies. The documented operations remain unavailable until their owning implementation and tests pass.

## Scope

C4 v1 adds deterministic access to two already-produced research artifacts. It does not create forecasts, recompute impacts, calculate routes, or establish live service operation.

### Saved A07 impact result

`POST /impact` accepts JSON `run_id` (integer), `valid_at` (offset-aware date-time identifying the UTC valid instant), and `scenario_key` (non-empty string). All three are required. The service must resolve the exact `(run_id, valid_at_utc, scenario_key)` tuple in the registered A07 V4 artifact. It must return exactly one matching C7 result, return 404 when no tuple matches, and fail closed if the artifact contains duplicate matches. It must not choose a default scenario. The existing C7 response body and its simulated/descriptive provenance remain unchanged.

The operation is a read-only projection of saved A07 results. It does not forecast, mutate a database, or claim validated impacts, warnings, safety, or emergency guidance.

### Saved A09 route result

`GET /route-results/{result_id}` retrieves an exact saved A09 revision-3 record. `result_id` is unique only within that immutable revision-3 artifact; it is not a global identity. The service must return that C8 result or 404 when the identifier is absent, and fail closed on duplicates. The response body and C8 semantics remain unchanged, including `run_id: null`, simulated source mode, unknown coverage, and the distinction between topological reachability and flood accessibility.

This operation retrieves a saved simulated result; it does not compute a route. The existing `POST /route` run-based computation request remains unavailable (HTTP 501 at the AI service / unexposed at the backend) because no authoritative integer run mapping exists for A09 revision 3. No run ID may be inferred from file names, scenario keys, or timestamps.

## Runtime and source boundaries

OpenAPI describes the approved request and response projections, not current runtime availability. Until B08 implements and verifies an operation, AI runtime behavior remains HTTP 501; backend routes remain unexposed. `POST /forecast`, `/uncertainty`, `/scenario`, and route computation remain unavailable until their own evidence-backed selector semantics and tasks are complete. I07 C9 visualization operations are separate.

All responses preserve source mode, artifact/run version, provenance, units, time meanings, null/NoData, coverage and QC exactly as C7/C8 require. Do not read or write the shared database or substitute live feeds. Saved outputs remain simulated/derived research evidence and do not establish operational forecast skill, scientific validation, safe routes, or emergency guidance.

## Change-control and compatibility

C4 v0 remains frozen as the G0 baseline. This v1 delta is authorized by CR-008 and must be projected consistently in the AI-service and backend OpenAPI documents. The implementation owner must keep C4 v0 operations and C7/C8 result schemas unchanged except for the explicitly versioned request/operation additions above. The v1 projections are not runtime-ready until B08 conformance tests pass. Gate reassessment is not required for this documentation-only, additive selector contract while runtime remains unavailable; any later runtime activation or change to C7/C8 semantics requires the applicable gate/change-control review.

Evidence: `docs/master/CR-008_B08_ARTIFACT_SELECTORS.md`, `docs/CR008_LANEA_SELECTOR_EVIDENCE.md`, A07 V4 `impact_results.jsonl`, A09 revision-3 `route_results.jsonl`, and the selector/projection conformance tests.
