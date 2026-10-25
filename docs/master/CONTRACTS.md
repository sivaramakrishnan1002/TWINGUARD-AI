# Contract registry

Contracts evolve additively and increment their version on change. Stubs must be visibly marked STUB and never presented as measured results. Current repository contract maturity is recorded in `STATE.json`; existence of a spec does not mean runtime integration.

| ID | Contract | v0 path | Owner | Consumers |
|---|---|---|---|---|
| C1 | Depth fields: metres, mean/p05/p95, master 30 m grid, NoData, timestamps | `contracts/c1_depth_v0.md` | A/I | routing, impact, simulation |
| C2 | Label registry and `labels.v_usable_flood_labels` | `contracts/c2_labels_v0.md` | A | science and API |
| C3 | Replay/live/simulated message contract | `contracts/c3_messages_v0.md` | B | streaming and twin |
| C4 | AI/backend OpenAPI and Track B router | `contracts/c4_openapi_v0.md` | I/B | UI and gateway |
| C5 | Tile/layer catalogue | `contracts/c5_tiles_v0.md` | I/B | UI |
| C6 | Twin schema | `contracts/c6_twin_v0.md` | I/B | services |
| C7 | Impact result schema | `contracts/c7_impact_v0.md` | A | API/UI |
| C8 | Routing result schema | `contracts/c8_routing_v0.md` | A | API/UI |

