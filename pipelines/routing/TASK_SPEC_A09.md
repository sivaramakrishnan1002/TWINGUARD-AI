# A09 task spec — Phase 15 routing decision comparison

## Scope and registered acceptance

Compare static, current flood-aware, horizon-aware time-dependent, and uncertainty-aware routes using A05 scenario ensembles and A08 graph snapshots. Use one member hidden as simulated truth and the remaining members as the forecast ensemble. Preserve unknown edge coverage and emit versioned route-result JSON following the Lane A draft in `docs/ROUTE_RESULT_SCHEMA.md`.

## Fixed design decisions

- Input case: A05/A08 `perfect_foresight_imerg` for event windows `2015-12-02`, `2021-11-13`, and `2023-12-04`; these are hindcast/scenario products, not issued forecasts.
- OSSE split: member 20 is hidden as truth; members 1–19 select/evaluate forecast routes. This is a simulated-member experiment, not independent observed validation.
- Six deterministic road-node origin/destination pairs are sampled from the largest directed strongly connected component, seed `20261027`. These are graph probes, not named facilities or evacuation endpoints.
- Route departure snapshots: 6, 24, and 72 hours after scenario issue time. “Current” route choices use the 6-hour snapshot; horizon-aware choices are reoptimized at each selected valid-time snapshot. States between saved snapshots are not interpolated.
- Static weights use A08 nominal free-flow edge times. Flood-aware weights use the 19 forecast members' expected travel time with a 20× free-flow penalty for blocked members. Unknown/structurally unassessed arcs are excluded from flood-aware path search and remain separately counted.
- Uncertainty-aware search excludes edges whose forecast-member blocked fraction exceeds 20%; after routing, the full-path accessibility probability is checked against the 0.80 minimum. This edge filter does not guarantee a whole-route probability of 0.80; failures are reported as `BELOW_ACCESSIBILITY_CONSTRAINT`.
- Ordinary and tunnel-proxy depth thresholds (0.30 m and 0.15 m) and A08 speed multipliers remain assumptions. Bridges remain unassessed.
- “Expected exposure” means expected depth-distance integral `sum(edge_length_m × edge_depth_m)` in m². It is not exposed population.

## Output and verification

Write only new outputs to `data/features/routing/results/batch2_v1/`: JSONL route records, a per-route comparison CSV, and a summary JSON with input hashes. Output records preserve topology separately from accessibility, UTC snapshot/departure/arrival fields, graph/hazard provenance, edge coverage, nullable probabilities, NoData/QC flags, and simulated-truth outcomes. No route is represented as safe, operational, or validated real-world guidance.

Focused validation checks route-result uniqueness and required fields, graph-path/topology consistency, edge-coverage arithmetic, null semantics for unknown edges, and no invented route measurements on no-path results. Full Lane A tests and the raw audit are run before task finish.
