# Contract registry

Contracts evolve additively and increment their version only on a separately authorized change. G0 froze C1-C8 at their existing v0 versions on 2026-10-28. Their evidence and limits are recorded in `G0_CHECKLIST.json` and `GATE_G0_REPORT.md`; freeze does not mean runtime integration or scientific validation. Stubs remain visibly non-operational and must never be presented as measured results.

| ID | Contract | Version/status | Draft path | Owner | Consumers |
|---|---|---|---|---|
| C1 | DERIVED depth proxy: single-band Float32 metres, 30 m EPSG:32644, explicit NoData; legacy p05/p95 are uncalibrated ±4 m assumption bounds | v0 / frozen G0 | `contracts/c1_depth_v0.md` | A/I | routing, impact, simulation |
| C2 | Accepted label view and GeoJSON Feature serialization; A/B/C accepted only, provenance and date/load-time semantics | v0 / frozen G0 | `contracts/c2_labels_v0.md` | A | science and API |
| C3 | Versioned JSONL messages; approved date-only representation, historical source time/timezone unknown; isolated persistence compatibility only | v0 / frozen G0 | `contracts/c3_messages_v0.md` | B | streaming and twin |
| C4 | Model-conformant AI/backend OpenAPI projections with explicit runtime/stub boundaries | v0 / frozen G0 | `contracts/c4_openapi_v0.md` | I/B | UI and gateway |
| C5 | Model-conformant JSON layer catalogue projection and database MVT capability; HTTP tile endpoint unavailable | v0 / frozen G0 | `contracts/c5_tiles_v0.md` | I/B | UI |
| C6 | PostgreSQL twin serialization, JSONB provenance and isolated B9 replay/persistence evidence | v0 / frozen G0 | `contracts/c6_twin_v0.md` | I/B | services |
| C7 | A07 V4 simulated impact result and model-conformant API serialization; not operational or validated | v0 / frozen G0 | `contracts/c7_impact_v0.md` | A | API/UI |
| C8 | A09 revision 3 route-result shape/API serialization in metres/seconds; simulated only, no safety/live claim | v0 / frozen G0 | `contracts/c8_routing_v0.md` | A | API/UI |

`I03` owns these registry and contract-draft paths. `I05` separately owns `docs/api/ai-service.yaml` and `docs/api/backend.yaml`, because those paths are not part of I03's task outputs. G0 is `ready`; all registry versions remain v0 and frozen.

### Approved post-G0 C4 change

CR-008 authorizes a separately versioned C4 v1 request/operation delta in `contracts/c4_openapi_v1.md`: exact A07 impact selection by `(run_id, valid_at, scenario_key)` and saved A09 revision-3 retrieval by its revision-scoped `result_id`. C4 v0 remains the frozen G0 baseline; C7/C8 response schemas are unchanged. `POST /route` computation remains unavailable because no authoritative run mapping exists. The OpenAPI projection is design/conformance evidence only until B08 passes its runtime tests; this change does not alter G0's v0 record.
