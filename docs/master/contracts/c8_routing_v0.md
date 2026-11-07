# C8 routing result v0

**Status:** frozen shared v0 contract for G0, reconciled to completed A09 revision 3 outputs and current API/DTO projections. The recorded routes are simulated model outputs, not safe real-world routes.

## Observed Lane A shape

`data/features/routing/results/batch2_v1/revision_3/route_results.jsonl` contains 216 UTF-8 JSON Lines route records. Results encode candidate identity and explicit status; departure/arrival and hazard issue/validity instants in UTC; requested horizon seconds; distance in metres; travel time in seconds; topological reachability separately from flood accessibility/failure probabilities; minimum probability constraint; ordered edges; nullable depth/geometry; edge coverage; depth-threshold assumptions; graph/hazard provenance; uncertainty and QC. Null means unavailable/unassessed, not zero or passable. Topological path existence is not flood accessibility. Thresholds and sensitivity values are assumptions; no safety claim follows.

## API projection evidence and limits

Both OpenAPI documents project the current `RouteResponse` model. I05's conformance test validates all 216 A09 records and B15 fixtures (route found, no topological path, insufficient hazard coverage) against the model and API schemas. Backend DTO round-trip tests preserve status, topology/accessibility distinction, metre/second units, UTC timestamps, nullable probabilities, coverage and provenance. The AI route endpoint remains HTTP 501 and the backend route endpoint is unexposed; this is schema/serialization agreement, not live integration or safe-route validation.

Evidence: `docs/ROUTE_RESULT_SCHEMA.md`, `docs/PHASE14_ROUTING_BATCH2.md`, `data/features/routing/results/batch2_v1/revision_3/summary.json`, `data/features/routing/results/batch2_v1/revision_3/route_results.jsonl`, `docs/api/ai-service.yaml`, `docs/api/backend.yaml`, `tests/master/test_api_contract_projection.py`, B15 route fixtures, and backend `GatewayContractTest`. C8 is frozen at v0 for G0; route outputs remain simulated and do not establish passability or safety.
