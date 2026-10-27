# A09 — Phase 15 routing decision comparison

## Result and scope

This is a **simulated research comparison**, not live routing, safe evacuation guidance, or validated real-world route performance. A05's `perfect_foresight_imerg` case is a hindsight scenario, not an archived operational forecast. One A06/A05 simulation member (member 20) was hidden as simulated truth; members 1–19 selected the candidate routes and supplied the route-level member-frequency estimates. This is an observing-system simulation experiment (OSSE), not independent observation-based validation.

The run compared static free-flow, current flood-aware, horizon-aware snapshot, and uncertainty-aware routing for six reproducibly sampled directed road-node origin/destination pairs. The pairs are graph probes sampled from the largest static strongly connected component (505,042 of 508,854 nodes, 99.25%); they are not named hospitals, shelters, or evacuation endpoints. It covered the A05/A08 `perfect_foresight_imerg` scenario for 2015-12-02, 2021-11-13, and 2023-12-04 at 6, 24, and 72 hour departure snapshots. Seed: `20261027`.

The “current” candidate uses the 6-hour graph snapshot. The horizon-aware candidate is reoptimized using the graph state at the requested 6-, 24-, or 72-hour valid-time snapshot. These are discrete snapshot routes: no intermediate flood state is invented, and a route does not simulate an edge-by-edge flood-state transition during the trip. Travel time and arrival time are expected values conditional on whole-route success in the 19 forecast members, using A08 assumed speed multipliers. The static route is evaluated against the same snapshot ensemble, but does not choose its path using flood state.

## Main counts

| Measure | Result |
|---|---:|
| Road graph nodes / directed arcs | 508,854 / 1,071,656 |
| Unique directed node pairs after parallel-arc collapse | 1,071,638 |
| Largest static strongly connected component | 505,042 nodes (99.25%) |
| Directed arcs with an A07 depth-cell mapping | 768,688 (71.73%) |
| Directed arcs without a unique depth-cell assessment | 302,968 (28.27%) |
| Sampled node pairs | 6 |
| Route records | 216 (4 methods × 3 events × 3 horizons × 6 pairs) |

Unmapped and structurally unassessed edges remain unknown. The flood-aware searches exclude them; this causes some origin/destination pairs to have no assessed-graph path. Static paths retain the full topology, but every static route in this sample crosses at least one unassessed edge and therefore has null accessibility/failure probabilities and status `INSUFFICIENT_HAZARD_COVERAGE`. A topological path is not evidence of flood accessibility.

## Comparison results

Counts below summarize the 54 route records per method (six pairs × three events × three valid-time snapshots). “Truth failed” is an observed outcome only against the held-out **simulated** member, and is counted only where all route edges have assessed state. Exposure is the mean `sum(edge_length_m × edge_depth_m)` over forecast members, in m²; it is not population exposure.

| Method | Records with a route path | Route probabilities computable | Mean forecast route-failure fraction | Held-out simulated truth failures / assessed paths | Mean expected travel time (s) | Mean expected depth-distance exposure (m²) |
|---|---:|---:|---:|---:|---:|---:|
| Static free-flow | 54 | 0 | Not assessed | 0 / 0 | Not assessed | Not assessed |
| Current flood-aware | 18 | 18 | 0.1316 | 2 / 18 | 1,409.31 | 254.04 |
| Horizon-aware snapshot | 18 | 18 | 0.1316 | 2 / 18 | 1,412.42 | 180.99 |
| Uncertainty-aware | 15 | 15 | 0.0000 | 0 / 15 | 1,355.84 | 62.00 |

The uncertainty-aware search removes edges whose estimated member failure fraction exceeds 20%, then checks the completed route against an 80% accessibility minimum. The 15 successful paths met that constraint in this finite, small OSSE sample; 39 pair/snapshot cases had no route in the filtered assessed graph. This result does not establish a calibrated 80% real-world chance of access. The static route records show graph connectivity, but no assessed route-level hazard probability. Current and horizon-aware paths are the same in several snapshots; the limited route sample and coarse 600 m depths do not support a general claim that one method is superior.

## Semantics, thresholds, and caveats

- Route-level probability is the fraction of the 19 forecast members in which every edge on that candidate path is assessed and not blocked. If any required edge is unmapped, bridge-unassessed, or otherwise unknown, probabilities are null; missing is never treated as dry or passable.
- `topologically_reachable` reports a graph path only. `status`, `edge_coverage`, and accessibility probability separately express flood-assessment limits.
- Ordinary-road depth blocking at 0.30 m and tunnel/underpass-proxy blocking at 0.15 m come from A08 and are assumptions; sensitivity values are 0.15, 0.30, and 0.50 m. Bridges remain unassessed because deck elevations are unavailable. The A08 depth-speed curve and class-default speeds are also assumptions.
- The 20× free-flow penalty for a blocked member in the expected-time route objective is a fixed computational penalty, not a calibrated delay. The uncertainty-aware edge filter is not a guarantee of whole-route reliability; the route-level constraint is checked separately.
- Expected depth-distance exposure is a line-route diagnostic. No population was assigned to routes, and the reported values are not people affected or exposed.
- Exact UTC departure and valid-time snapshots are included in each record. Expected arrival is departure plus the route's mean travel time conditional on success. Edge entry/exit times are emitted only when all edge travel times are available; otherwise they are null.
- Route JSON follows the Lane A draft in `docs/ROUTE_RESULT_SCHEMA.md`; it is not a frozen C8/API contract. No shared API, UI, or database contract was changed.

## Output and provenance

Final versioned output: `data/features/routing/results/batch2_v1/revision_3/` (generated, ignored data; not committed):

- `route_results.jsonl` — 216 records with geometry, ordered node and edge paths, UTC times, nullable probabilities, edge coverage, assumptions, input provenance, and simulated-truth annotations.
- `comparison_metrics.csv` — one row per route/method/event/horizon.
- `summary.json` — run design, counts, limitations, and SHA-256 for input artifacts.

Output SHA-256:

| File | SHA-256 |
|---|---|
| `route_results.jsonl` | `ee4e33b45268ba869cfc0f3f48eee1c10ac2c5ae83837b1d82165c6ca6c2ea7f` |
| `comparison_metrics.csv` | `b21f007f94c7307b8b0dee5d0500072f30462d66be20ac5a955cc13f42eea6ad` |
| `summary.json` | `3d0784a481aaaf451456e9e9f1bb1291461bb0a3680b6cc7019335d0501adc3b` |

The output summary records the exact source hashes for the A08 graph summary, directed arcs and snapshot index, OSM road graph package, A05 forecast summary, and A07 impact summary. Route records identify code commit `b9b6ea40f13c4af4a411bcafdbc773882c7f6acc`.

An initial A09 output and a corrected intermediate revision were preserved under `data/features/routing/results/batch2_v1/` rather than overwritten. The initial output had an inverted accessibility/failure probability assignment; the corrected intermediate lacked final code-commit provenance. **`revision_3` above is the final verified output and supersedes those earlier run directories.**

## Checks

Commands and results:

```powershell
.venv\Scripts\python.exe -m pytest -q tests\routing\test_phase15_routing.py --import-mode=importlib
# 5 passed
.venv\Scripts\python.exe pipelines\routing\phase15_routing.py --verify-only --output data\features\routing\results\batch2_v1\revision_3
# 216 records; schema and NoData checks PASS
.venv\Scripts\python.exe -m pytest -q tests\routing tests\labels tests\explainability tests\phase8 tests\phase9 tests\phase9b tests\phase9c tests\phase10 tests\phase11 tests\phase12 tests\phase13 --import-mode=importlib
# 110 passed
.venv\Scripts\python.exe tools\audit_raw_logs.py
# DATA_FILES=157; DATA_BYTES=30544672450; HASH_MATCH=157; NO_COMPARABLE_HASH=0; MISMATCH=0
```

CPU only. No GPU workload was necessary for sparse shortest paths; no package was installed and no network or credentials were used. Raw data stayed read-only. No route result is safe, operational, or validated emergency guidance.
