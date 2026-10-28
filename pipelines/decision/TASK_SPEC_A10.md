# A10 task specification — shelter allocation

## Registered scope

Use OSM shelters plus schools/colleges as candidate shelters, make capacity assumptions explicit, allocate population under A08 simulated flood access, assign CMA population cells to nearby road nodes, preserve WorldPop NoData, and report unserved demand plus capacity/access sensitivity.

## Fixed implementation choices

- Target candidates are OSM `shelter`, `school`, and `college` facilities falling inside A06's active 600 m CMA model grid. Schools and colleges are candidate shelters by assumption, not confirmed emergency facilities.
- Candidate capacities default to 100 people per OSM shelter, 250 per school, and 500 per college. Sensitivity multiplies all capacities by 0.5, 1, and 2. These are deliberately hypothetical and must not be interpreted as real capacity.
- CMA-limited 30 m WorldPop estimates are summed into the A06 active 600 m cells. Each known-demand cell centre is snapped to its nearest OSM road node; each candidate facility is separately snapped to its nearest road node. Snap distances are recorded. Unobserved population remains NaN/unknown and is never allocated as zero demand.
- A08 member states at 6, 24, and 72 elapsed hours are used for all 20 members of each event/scenario case. The open/reduced directed-road arcs define weakly connected graph components. Unknown, blocked, bridge-unassessed and unassigned arcs do not connect components.
- Demand and candidates are grouped by those weak components. Within each component, a deterministic greedy algorithm allocates demand in increasing planar distance between snapped network nodes until assumed capacity is exhausted. This is an allocation proxy, not direction-aware route finding or travel-time accessibility.
- Events are the 2015-12-02, 2021-11-13 and 2023-12-04 A05/A08 perfect-foresight IMERG scenarios. All results are simulated research scenarios, not real facility operations, live flood access, safe evacuation, or emergency guidance.

## Outputs and validation

Write new artifacts only under `data/features/decision/shelters/batch2_v3/`; do not overwrite existing outputs. Earlier `batch2_v1/` and `batch2_v2/` outputs are preserved as superseded runs. Produce event/horizon/member/capacity-factor summaries, a row-level allocation table keyed by event/time/member/factor/grid cell/candidate OSM ID, a candidate-facility table with capacity assumptions and snap distances, a run summary with input hashes, and deterministic checks of case count, allocation reconciliation, capacity constraints, output labels, and NoData flags. Raw data remain read-only.

The corrected v3 accounting distinguishes total unserved demand from its two disjoint parts: unserved demand that has an active candidate in the same weak component, and demand in components with no usable candidate. The v2 field labelled `unserved_reachable_people_model_estimate` had represented all unserved demand, so adding the separate unreachable amount double-counted it. v3 corrects that field, adds an explicit total-unserved field, and verifies both accounting identities.
