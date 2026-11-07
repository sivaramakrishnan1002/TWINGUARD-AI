# C7 impact result v0

**Status:** frozen shared v0 contract for G0, reconciled to completed A07 V4 output and current API/DTO projections. Results are `SIMULATED`, not observed/live impacts or emergency guidance.

## Observed Lane A shape

`data/features/impact/batch2_v4_contract/impact_results.jsonl` contains 75 UTF-8 JSON Lines records. Each record uses `schema_id=twinguard.impact_result`, integer `run_id`, `run_version`, event window, `valid_at_utc`, nullable `aggregation_interval`, explanatory `aggregation_basis`, `generated_at_utc`, scenario, assumed thresholds in metres, metrics, facility-access categories, sensitivity results, coverage, uncertainty, provenance, and QC flags. In the observed instantaneous outputs `aggregation_interval` is null; valid and generated times are offset-aware UTC strings normalized to `Z`.

Metric and category distributions carry status, unit, mean and p05/p50/p95, member count and interpretation. `PARTIAL` measurements may contain values alongside coverage and QC. Null means unavailable and is not zero. Coverage reports assessed, eligible and NoData counts; population NoData is not zero, and no temporal aggregate was computed.

The run summary and output provide source hashes/versions/roles, algorithm/version, code commit, parameters, grid CRS/resolution, ensemble details and QC limits. Quantiles describe scenario/member spread and are not calibrated uncertainty. Outputs are SIMULATED and flag coarse road midpoint sampling and component-proxy access; they do not establish real-world route accessibility, facility operations, live integration or safety. The schema output carries a draft/not-approved/not-frozen QC flag; this contract records observed shape without asserting scientific validation.

## API projection evidence and limits

Both OpenAPI documents project the current `ImpactResult` model. I05's conformance test validates all 75 A07 records and B15's impact fixture against the model and both API schemas; backend DTO round-trip tests preserve null instantaneous interval, explicit basis, units, NoData and QC. The AI impact operation remains HTTP 501 and does not emit the result; no live runtime integration is claimed.

Evidence: `docs/IMPACT_RESULT_SCHEMA.md`, `docs/PHASE13_IMPACT_BATCH2_V4.md`, `data/features/impact/batch2_v4_contract/run_summary.json`, `data/features/impact/batch2_v4_contract/impact_results.jsonl`, `docs/api/ai-service.yaml`, `docs/api/backend.yaml`, `tests/master/test_api_contract_projection.py`, B15 fixtures and backend `GatewayContractTest`. C7 is frozen at v0 for G0; result values remain simulated and not scientifically validated or operational.
