# C4 AI/backend API v0

**Status:** frozen v0 contract for G0 (2026-10-28). The OpenAPI documents are design projections, not proof that all operations are implemented.

Requests and responses are JSON. Timestamp fields identify their instant/validity meaning and use offset-aware date-time encodings. Quantities carry explicit units; null/unavailable is not zero. Responses preserve typed, bounded provenance and exact source class `replay|live|simulated`; replay is never relabeled live. Unknown source metadata remains null. HTTP semantics distinguish stub/unimplemented 501, unavailable dependency 503, unknown run/time 404, and domain success only when a result exists.

`docs/api/ai-service.yaml` and `docs/api/backend.yaml` project the current Track B Pydantic model schemas. I05's conformance tests compare these schemas with model-generated schemas, validate all A07 impact and A09 route JSONL outputs and B15 owner fixtures, and the backend Maven tests round-trip DTO fixtures. C7/C8 use unit-bearing, nullable result fields and typed provenance. `/forecast`, `/uncertainty`, `/impact`, `/route`, and `/scenario` remain 501 stubs; the backend route endpoint is unexposed. These tests prove schema/serialization agreement only, not runtime integration or live operation.

C5 `/layers` describes the read-only catalogue. It explicitly reports `tile_endpoint_available=false`; database MVT functions are not HTTP tile serving. C8 preserves topological reachability separately from flood accessibility and keeps unavailable coverage/probabilities null. C4 is frozen at v0 for G0; projections remain specifications, while AI business operations remain HTTP 501 and the backend route remains unexposed.

Evidence: `docs/api/ai-service.yaml`, `docs/api/backend.yaml`, `tests/master/test_api_contract_projection.py`, `services/ai-service/app/main.py`, `tests/ai_service/test_api.py`, backend DTOs and `GatewayContractTest`, A07 V4 and A09 revision 3 outputs, and B15 owner fixtures.
