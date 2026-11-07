# A21 — Test three-state flood routing against A09

**Owner:** Lane A routing/science. **Status at registration:** ready/unclaimed. **Classification:** preregistered simulated OSSE and focused literature review; not operational route guidance.

## Question

Does preserving flood-evidence state per road edge and optionally producing clearly conditional routes provide useful coverage/verification-prioritization information beyond A09's current fail-closed behavior, without treating unknown evidence as passable?

**Secondary question — decision stability (bounded, descriptive):** using only registered saved A05/A08 scenarios and A09/A10 decision outputs (plus A21's preregistered routing evaluation over those saved graph states), do route-choice and modeled shelter-allocation choices remain the same across tested members and recorded assumptions; which recorded scenario condition accompanies a choice change; and which already-recorded unknown/missing input is implicated in the most tested choices? Compare with one recorded point-estimate/single-scenario baseline. This is not a separate task, a causal attribution study, or a novelty claim.

Use the three edge states:

- `ASSESSED_PASSABLE`: assessed under A08's existing documented rule and below its applicable assumed threshold.
- `ASSESSED_BLOCKED`: assessed under that rule at or above the applicable assumed threshold.
- `UNKNOWN`: available flood evidence does not assess that road edge. Preserve reason codes for unmapped/ambiguous edge, NoData, bridge/structure unassessed, or other existing source reason.

Any selected route containing one or more `UNKNOWN` edges is `CONDITIONAL / NEEDS VERIFICATION`. It is not a safe route, does not treat the unknown edge as passable, and is not operational guidance. A route made only of assessed-passable edges is still a model-assessed route under assumptions, not a real-world safety claim.

## Inputs and baseline

- A08 `data/features/routing/time_dependent_batch2/` and `docs/ROUTING_GRAPH_BATCH2.md` (including directed arc mapping, snapshot index, states, and recorded hashes).
- A05 saved event/scenario/member/horizon depths and hashes, as referenced by A08.
- A09 final baseline `data/features/routing/results/batch2_v1/revision_3/route_results.jsonl`, comparison metrics, summary, `pipelines/routing/phase15_routing.py`, and `docs/ROUTING_BATCH2.md`.
- A10 final saved shelter outputs under `data/features/decision/shelters/batch2_v3/` (especially `allocation_cases.parquet`, `allocation_detail.parquet`, `candidate_facilities.parquet`, and `run_summary.json`) and `docs/SHELTER_ALLOCATION_BATCH2.md`.
- A15 `docs/VALIDATION_REPORT.md`, A13 `docs/DECISION_LAB_BATCH2.md`, and prior novelty/hypothesis records in `docs/MASTER_PLAN.md` and `docs/batches/BATCH_2.md`.
- Existing Lane A routing state rules and thresholds. Do not change or regenerate A08/A09/A05 inputs.

## Owned outputs (new versions only)

- `pipelines/routing/three_state_batch3/` — analysis implementation and immutable preregistration/config.
- `data/features/routing/three_state_batch3_v1/` — versioned edge states, route comparisons, verification-priority summaries, and run manifest with hashes.
- `tests/routing/test_three_state_batch3.py` — regression and output validation tests.
- `docs/ROUTING_THREE_STATE_BATCH3_PREREGISTRATION.md` — frozen sampling, methods, metrics, exclusions, and decision rules, committed before result generation.
- `docs/ROUTING_THREE_STATE_BATCH3.md` — results, negative/positive findings, limitations, source hashes, commands, checks, and interpretation.
- `docs/literature/ROUTING_UNKNOWN_EVIDENCE_2025_2026.md` — focused literature-review protocol and comparison with the closest prior work.
- `docs/batches/BATCH_2_PROGRESS.md` — Lane A board completion row and evidence summary.

Do not write to or overwrite `data/features/routing/time_dependent_batch2/`, `data/features/routing/results/batch2_v1/`, any A05/A07 output, existing reports, UI/API artifacts, or frozen contracts. If a required input hash differs from the recorded owner evidence, stop and report the mismatch before analysis.

## Preregistered design requirements

1. Record input SHA-256 values, code/config version, fixed random seed, sampling frame, stratification, methods, denominators, exclusions, missing-data handling, metrics, and failure criteria in the preregistration before producing comparative results.
2. Compare A09's fail-closed assessed-passable routing with the three-state alternative on at least **120 unique directed OD pairs**, sampled reproducibly across 12 strata formed by four geographic graph sectors and three network-distance bands (at least 10 pairs per stratum where the graph permits). Include disconnected/no-path cases and strata for full, partial, and absent/ambiguous flood-edge coverage; document any unavailable stratum and do not silently replace it.
3. Evaluate all three A08 event windows, all five saved A05 scenario labels where the corresponding A08 snapshots exist, and saved horizons 6, 24, and 72 h. Use identical OD/event/scenario/horizon cases for the baseline and proposed method. Never interpolate a flood state between snapshots.
4. In the three-state method, first seek a route composed only of `ASSESSED_PASSABLE` edges. If none exists, an explicitly configured conditional-search stage may seek a path over `ASSESSED_PASSABLE` plus `UNKNOWN` edges, using a preregistered lexicographic objective that minimizes unknown-edge distance before assessed travel cost. It must exclude `ASSESSED_BLOCKED`, preserve state/reason for every edge, and label any route using unknown distance as `CONDITIONAL / NEEDS VERIFICATION`. Unknown edges are never described as passable.
5. Compare route availability, no-path rate, conditional-route frequency, unknown-edge distance and share, coverage, and route-selection differences. Where A05/A06 member 20 can be held out consistently, calculate simulated route failure/exposure only for routes whose full path is assessed in that held-out member; report unknown denominators separately and do not count unknown as success or failure. This is OSSE truth, not observed truth.
6. Evaluate verification prioritization using a deterministic greedy coverage rule over unknown edges: rank edges by the number of distinct conditional OD cases whose route includes them, with preregistered distance and edge-ID tie breaks. Report case counts covered under a verification budget and run both passable and blocked status scenarios for newly assessed edges only when those outcomes are already represented by registered saved simulation states. Call this prioritization of verification effort only; it cannot prove any edge safe or passable.
7. **Secondary decision-stability analysis:** preregister it in the same A21 analysis plan before examining comparative outputs. For routes, hold each route method fixed; use member-specific three-state paths computed only over registered saved A05/A08 member states and compare exact directed edge-path identity by paired OD/event/scenario/horizon. There is no cross-method universal “preferred route” or safety ranking. Compare with the same method run on the saved A05 member-12 state (the recorded nominal reference used by A13) and with a matched single-scenario view using only `perfect_foresight_imerg`. For shelter, use only saved A10 allocation detail: within each event/scenario/horizon/member/capacity-factor case, define the descriptive selected allocation candidate as the candidate with greatest `allocated_people_model_estimate`; use lowest numeric OSM ID as the deterministic representative and report equal top allocations as ties. This is not a recommended/safe shelter. Compare member-resolved choices with saved member 12 at recorded nominal `capacity_factor=1.0`, and with a matched `perfect_foresight_imerg` scenario view. If a baseline/case is absent or incompatible, mark the comparison unavailable rather than synthesize it.
8. Report measurable descriptive metrics separately: decision stability = tested member decisions identical to the matched point-estimate choice / member decisions made; decision-change frequency = changed choices / matched comparable decisions; and scenario-count coverage = decisions made / eligible registered case-member combinations. Provide numerator, denominator, ties, missing/no-decision cases, and unmatched cases for every metric and stratum. These are counts/fractions of tested simulations, never calibrated probabilities, confidence, or real-world frequencies. Do not combine into a score.
9. For each choice change, record the observed changed metadata dimensions (member, event, scenario label, saved horizon, and, for A10 only, recorded capacity factor) as **decision-change triggers/correlates**, not causal effects. Use matched one-dimension contrasts where saved cases permit; report multiple changing dimensions as ambiguous attribution. Do not vary, interpolate, or invent an input.
10. Rank decision-relevant unknown roads/missing inputs by the number of distinct tested decisions that are conditional on, traverse, or differ across already-saved states of that unknown. Report road IDs/recorded missing-input keys and case denominators. A verification priority is an evidence-acquisition queue only; the unknown remains unknown until verified. For non-road missing inputs, use only explicitly recorded missingness/NoData in registered artifacts; do not infer missing values from absence.
11. Report route/shelter coverage versus simulated risk/failure trade-offs without a composite safety score. Include uncertainty intervals clustered by event and OD pair where estimable. Report simulation/horizon/member/capacity-factor denominators, graph exclusions, ties, no-decision cases, and zero/NoData distinctly.
12. The comparison may show no benefit, unstable choices, unavailable comparisons, or a worse trade-off. Do not select thresholds, sampling strata, metrics, or tie rules after viewing comparative outcomes.

The preregistration must also state these decision-stability exclusions/failure rules before inspecting comparison results: preserve each source artifact and stop the affected analysis on hash mismatch; stop decision matching if case keys are duplicate or cannot be joined unambiguously; classify absent/unassessed/no-path/no-allocation cases as no decision and retain them in the eligible-case denominator; exclude unmatched cases from paired change denominators but report their count and reason; do not replace absent member-12 or capacity-factor baselines; report ties separately and apply only the specified stable ID tie break for a representative; mark a stability comparison unavailable if the saved fields cannot identify a choice; and make no stability or decision-change claim when the corresponding numerator/denominator cannot be computed. There is no pass threshold that can turn these descriptive counts into a validated recommendation.

## Regression and scientific acceptance

Tests must cover all three edge states; assessment thresholds/structure reasons; NoData and absent mapping as `UNKNOWN`; `ASSESSED_BLOCKED` exclusion; assessed-passable-only route; conditional route status whenever any unknown edge is traversed; unknown distance arithmetic; no-path behavior; zero-length/zero-count distinction; deterministic selectors and tie-breaking; simulated held-out truth with unknown denominators; and no mutation of source inputs or previous outputs. Tests must fail if `UNKNOWN` is converted to passable, dry, zero depth, or successful truth.

The literature review must search publications dated 2025-01-01 through the recorded search date (within 2025–2026), using a recorded search protocol and reproducible query strings across appropriate scholarly indexes plus primary publisher/proceedings sources. Compare at least the closest work on flood-aware routing under incomplete/uncertain inundation or road-closure evidence, three-state/unknown network edges, conditional routing, and verification prioritization. Cite title, authors, venue, publication date, DOI/primary URL, methods, uncertainty/missingness treatment, and overlap. Separate established ideas from any potentially distinct contribution. If close prior art exists or the search is inconclusive, state that novelty is unproven; do not manufacture a gap.

No independent observed road closure, route availability, or date-matched flood depth truth is currently recorded. Unless the Lane A owner finds and verifies suitable licensed observational evidence, conclusions must be limited to a simulated OSSE over A05/A08 artifacts and saved A10 modeled allocations. Do not describe outputs as live, safe, validated, operational, or emergency guidance. Decision stability across simulation members is not calibration or independent validation.

## Completion evidence

Before finish: verify all output hashes and source manifests; run focused routing tests, applicable Lane A suite, the raw-data audit, and `verify_state.py`; preserve exact command/results and any unavailable checks; update the Lane A progress board; finish A21 through the official Lane A protocol. Keep G0 and all frozen contracts unchanged. This task does not close G1–G6 or make a gate-ready claim.

