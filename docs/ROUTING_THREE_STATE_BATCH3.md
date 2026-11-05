# A21 — three-state flood-routing and decision-stability OSSE

**Status:** completed with caveats. **Evidence:** saved simulated outputs only; this report is not operational route guidance. No independent observed road closures, route outcomes, or date-matched flood-depth truth were available.

## Registered method and provenance

The preregistration was committed before comparative analysis in `docs/ROUTING_THREE_STATE_BATCH3_PREREGISTRATION.md` (SHA-256 `55c272d3420c239b4bc81fc6671ec063c2e1b63ce0bdf46c89aea19f83562b43`; commit `cd35fcd`). The analysis used seed 21031, 120 unique directed primary OD pairs in 12 sector-by-distance strata, and 12 disconnected supplement pairs reported separately. It evaluated the three saved event windows, five A05 scenario labels where A08 snapshots existed, saved 6/24/72 h horizons, and 20 members. No snapshots were interpolated. The main artifacts and hashes are recorded in `data/features/routing/three_state_batch3_v1/manifest.json`; 48 preregistered input hashes were checked before analysis and are rechecked by the analysis code.

Each edge is `ASSESSED_PASSABLE`, `ASSESSED_BLOCKED`, or `UNKNOWN`, with reason codes retained. Fail-closed routes use passable edges only. The conditional search is attempted only when that route is absent; it excludes blocked edges and minimizes unknown-edge distance before assessed travel time. Any path containing unknown edges is `CONDITIONAL / NEEDS VERIFICATION`, never passable or safe.

## Route comparison

The 120 primary OD pairs yield 108,000 matched OD/event/scenario/horizon/member cases. The 12 disconnected supplements add 10,800 cases, for 118,800 total. Primary route coverage classes over those 108,000 cases were full 6,300, partial 99,000, and absent or ambiguous 2,700 (`coverage_cases.parquet`).

| Result | Count | Denominator / interpretation |
|---|---:|---|
| Fail-closed assessed route | 14,148 | 108,000 primary cases (13.10%) |
| Three-state assessed-passable route | 14,148 | 108,000 primary cases; identical when the baseline exists |
| Conditional route requiring verification | 92,750 | 108,000 primary cases (85.88%) |
| No three-state path | 1,102 | 108,000 primary cases (1.02%) |
| Three-state route available, including conditional | 106,898 | 108,000 primary cases (98.98%); conditional does not mean passable |
| Disconnected supplements with no route | 10,800 | 10,800 supplement cases; kept outside the primary denominator |

The aggregate includes 118,800 rows in `route_cases.parquet`: fail-closed 14,148 assessed routes and 104,652 no-assessed-path rows; three-state 14,148 assessed-passable routes, 92,750 conditional routes, and 11,902 no-path rows. The difference between the aggregate no-path count and the primary count is the disconnected supplement.

### Held-out simulated member 20

Among 112,860 route-selection cases from members 1–19, member 20 marked 13,438 selected routes as simulated passable under A08's rule for both methods. The fail-closed method selected no route in the other 99,422 cases. For three-state routes, 88,114 had unknown held-out truth and 11,308 had no selected route. Therefore the fully assessed outcome denominator is 13,438 per method and there were zero simulated blocked outcomes in that denominator. Unknown truth is excluded, not counted as success or failure. This is an OSSE against another simulation member, not observed validation.

### Clustered uncertainty

The registered crossed event-cluster and within-stratum OD-cluster bootstrap used 2,000 replicates, seed 21031, and three event clusters/120 OD clusters (`cluster_bootstrap_intervals.json`). Descriptive 95% intervals were: fail-closed primary route availability 0.081–0.183; three-state availability including conditional routes 0.980–0.997; difference 0.805–0.911; conditional-route share 0.805–0.911. Simulated failure-rate intervals were [0, 0] for both methods on the fully assessed member-20 denominator. Only three event clusters are available, so these intervals are unstable and must not be read as real-world probabilities.

## Verification prioritization and status support

The deterministic greedy coverage queue in `unknown_verification_priority.parquet` ranks 1,470 unknown road arcs. The top arc (ID 156473) occurs in 20,404 of 92,750 conditional cases. The greedy queue covers 20,404/92,750 cases with one edge; 43,603 with five; 54,138 with ten; 77,552 with 25; and 92,750 with 50. This is an evidence-acquisition queue, not evidence that any edge is passable.

The registered status-support check is reproducible in `pipelines/routing/three_state_batch3/supplemental_checks.py`; its versioned evidence is in `data/features/routing/three_state_batch3_supplement_v1/`. It examined the 1,470 prioritized arcs over 900 saved A08 snapshots (6/24/72 h). All 1,470 remained unknown in all 900 snapshots; zero had a saved passable state and zero had a saved blocked state. Thus no passable/blocked status scenarios were run: imposing either state would invent evidence. A09's 216 saved route rows cover six unique directed OD pairs, with zero exact overlap against the 120 primary sampled pairs; direct row-matched A09 route comparison is unavailable. The tested fail-closed method is a reproduction of A09's passable-only rule on registered A08 states, not a direct rerun of A09's six saved routes.

## Decision stability (secondary descriptive analysis)

Route comparisons use exact directed arc-sequence identity. Counts and denominators below are saved simulation decisions, not probabilities.

| Comparison / method | Decisions / eligible | Paired | Identical / paired | Changed / paired | Unmatched or no decision |
|---|---:|---:|---:|---:|---:|
| Member vs member 12, fail-closed | 12,730 / 106,920 | 12,724 | 12,518 (98.38%) | 206 (1.62%) | 94,196 |
| Member vs member 12, three-state | 96,203 / 106,920 | 96,186 | 84,647 (87.98%) | 11,539 (12.00%) | 10,734 |
| Scenario vs perfect foresight, fail-closed | 10,747 / 90,288 | 10,695 | 10,010 (93.59%) | 685 (6.41%) | 79,593 |
| Scenario vs perfect foresight, three-state | 81,238 / 90,288 | 80,996 | 59,807 (73.84%) | 21,189 (26.16%) | 9,292 |

The 11,745 member-associated and 21,874 scenario-associated changed-route records in `route_choice_changes.parquet` retain event, scenario, horizon, member, recorded conditions, and attribution labels. Scenario-associated changes are correlates of the saved A05 scenario label, not causal effects; member-associated changes occur under A08's assumed ordinary 0.30 m and tunnel-proxy 0.15 m thresholds, with bridges unknown. Multiple dimensions are not assigned causal attribution.

A10 supplies 540 saved shelter-allocation cases and 540 descriptive representative choices; all 540 have tied maximum allocations, with lowest numeric OSM ID used only as the deterministic representative. For nominal capacity factor 1.0, 180 cases were eligible and 171 could be paired to the saved member-12 reference; all 171 were identical, and all were ties. Cross-scenario shelter comparison is unavailable because A10 saved only `perfect_foresight_imerg`. Recorded missing inputs were positive in all 540 cases for both unknown demand (3,780 total repeated case values) and WorldPop NoData cells (51,977,160 total repeated case values); these repeated sums are not counts of unique cells.

## Literature and novelty

The focused, preregistered search and source comparison are documented in `docs/literature/ROUTING_UNKNOWN_EVIDENCE_2025_2026.md`. It covers 2025-01-01 through 2026-10-31, with seven exact queries in OpenAlex and Crossref and primary-source checks for retained works. Close prior work already covers uncertain road accessibility, flood-aware routing, and road verification/value of information, including Li et al. (2026, DOI 10.1007/s44163-026-02033-1) and Pan et al. (2026, DOI 10.1016/j.ress.2026.113592). The review is not exhaustive and does not establish a distinct contribution. **Novelty and real-world benefit remain unproven; no novelty claim is made.**

## Compute, checks, and limitations

The route algorithm uses SciPy sparse graph routines and ran on CPU. A current availability check on 2026-11-05 06:35 UTC found PyTorch 2.14.1+cu126 and one NVIDIA GeForce RTX 3050 Laptop GPU (4 GiB; driver 621.01; CUDA available). GPU was not used because the registered sparse shortest-path implementation is CPU-based; a GPU rewrite would change the implementation and was not needed for this closeout. The recorded analysis run used 12 CPU worker threads; `run_summary.json` records 429.64 s for its recorded analysis/export run. The separate read-only status-support check completed on CPU.

The analysis remains limited by A08's assumed depth/speed/closure rules, unassessed bridges, incomplete route-edge coverage, three event windows, no independent observed routes or closures, and modeled A10 shelter capacities/allocations. Conditional routes require external verification. No output is live, operational, validated for real-world safety, or emergency guidance.

Exact closeout checks and results are recorded in the Lane A progress board and task finish evidence. Generated data under `data/features/` is local/ignored and is not part of the source commit; its manifest provides artifact hashes.
