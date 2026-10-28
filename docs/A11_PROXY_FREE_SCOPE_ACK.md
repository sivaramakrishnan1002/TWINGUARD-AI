# A11 proxy-free scope acknowledgment

**Status:** Lane A acknowledgment recorded; this is not an implementation, contract freeze, or master-state change.
**Date:** 2026-10-28
**Scope authority:** Project-owner-approved Option B in `docs/master/A11_PRIORITY_ZONES_SCOPE_CHANGE.md`.

## Acknowledgment

Lane A accepts the revised A11 scope: publish separate, scenario-labelled hazard, population-exposure, and facility-access-loss outputs from the existing A07/A10 research evidence. No vulnerability proxy is available or accepted. The outputs will not be combined into a score, weighted, ranked, or called vulnerability or official priority zones.

The scope is scientifically appropriate provided that each indicator retains its own units, coverage, uncertainty, and caveats. It makes no claims of live operation, hydraulic validation, safe routes, or emergency guidance. The registered A11 path remains `data/features/decision/priority_zones/batch2_v1/`; this note does not create or revise task outputs.

## Lane A output/schema acknowledgment

This is the concrete implementation interpretation of the registered “layers/summaries” acceptance. It reuses fields present in the completed upstream artifacts and does not imply that the unfrozen G0/API contracts have changed.

| Separate product | Proposed representation and fields | Unit/meaning | Evidence and limits |
|---|---|---|---|
| Hazard | A 600 m grid product per registered event/scenario/valid time, keyed by `event_key`, `scenario_key`, `horizon_hours`, `valid_at_utc`, `grid_cell_id`; preserve `depth_mean_m`, `passability_probability`, `depth_valid_member_count`, `member_count`, `threshold_m`, and `qc`. Keep unknown cells NoData/unassessed. | `depth_mean_m` in metres; `passability_probability` from 0 to 1 for the stated screening threshold; counts are members. | A07 `data/features/impact/batch2_v4_contract/cell_impact.parquet`. The 600 m model is coarse and assumption-based. The screening threshold is not a validated flood-depth danger threshold. Do not relabel its depth member bounds as calibrated statistical intervals. |
| Population exposure | A separate per-grid-cell known-population exposure product keyed to the same case and grid, with `known_population_exposed_people`, `population_nodata_cells`, `exposure_threshold_m`, `valid_at_utc`, and QC/coverage fields. Preserve exposure NoData independently from zero exposure. | People are WorldPop model estimates aggregated to the analysis cell; NoData count is cells, not people. | A07 `member_impact_metrics.parquet` provides known exposed people and population-NoData counts; A10 `allocation_cases.parquet` distinguishes known demand from unknown demand cells. WorldPop is an exposure estimate, not vulnerability or a census count. |
| Facility-access loss | A separate case/category summary keyed by `event_key`, `scenario_key`, `valid_at_utc`, `member_id`/ensemble summary, and `category`, carrying `facility_count`, `reachable_count`, `unreachable_count`, `unassessed_count`, `access_loss_fraction`, `coverage_fraction`, and any available member-distribution fields. Keep A10 capacity allocations in a separate companion table with `capacity_factor`, `allocated_people_model_estimate`, candidate category/ID, and its QC fields; do not merge allocation into access-loss counts. | Facilities are counts; loss and coverage are fractions from 0 to 1; allocation is model-estimated people. | A07 `impact_results.jsonl` contains `facility_access_by_category`; `member_impact_metrics.parquet` contains facility access fields. A10 `data/features/decision/shelters/batch2_v3/allocation_cases.parquet`, `allocation_detail.parquet`, and `candidate_facilities.parquet` describe simulated allocation. A07 access is a coarse connected-component proxy, not direction-aware OD routing. A10 capacities are hypothetical; schools/colleges are candidate shelters, not confirmed shelters. |

## Shared metadata and deterministic checks

Each product/summary will include or reference: schema ID and version; result and run ID/version; event and scenario key; exact `valid_at_utc` (UTC) and `horizon_hours`; `generated_at_utc`; source artifact paths and SHA-256 hashes; CRS `EPSG:32644`, 600 m grid identity and cell key; units; threshold assumptions; source mode (`SIMULATED`/`DERIVED`); uncertainty method and member count where available; coverage/NoData semantics; and QC flags. Do not invent times between saved model states. Preserve the input's UTC time basis.

Deterministic tests should check case-key uniqueness, grid dimensions/CRS/resolution, product separation (no composite/rank/vulnerability fields), numeric units/ranges, exact upstream case and scenario coverage, and that NoData/unassessed stays distinct from zero. Tests should also verify every output's source run/version and provenance reference. A07 values and A10 allocations remain independently traceable; no synthetic vulnerability or access observations are introduced.

## Evidence reviewed

- Registered A11 task and acceptance in `docs/master/STATE.json` (read-only): separate indicators, native semantics, provenance, uncertainty/coverage, NoData, deterministic schema tests, and raw audit.
- Owner decision in `docs/master/A11_PRIORITY_ZONES_SCOPE_CHANGE.md` (read-only): proxy-free Option B; A11 remains blocked until Lane A acknowledgment.
- `docs/batches/BATCH_2_PROGRESS.md`: A07 `batch2_v4_contract` and A10 corrected `batch2_v3` are complete with caveats.
- Read-only schemas: A07 `cell_impact.parquet` has `event_key`, `scenario_key`, `valid_at_utc`, `horizon_hours`, `grid_cell_id`, `threshold_m`, `passability_probability`, `depth_mean_m`, member-bound/count fields, and QC; A07 `impact_results.jsonl` has metrics, category access summaries, coverage, uncertainty, provenance and QC; A10 outputs include scenario/time/member keys, known versus unknown demand, assumed capacity factors, and simulation QC.

## Limitations retained

- A05/A06 are hindcast/scenario and coarse assumption-based simulation outputs, not operational forecast skill or independently validated hydraulic truth.
- A07 facility access is an aggregate coarse-component proxy, not route reachability or safety. Road/facility coverage may be incomplete.
- A10 is simulated greedy capacity allocation under hypothetical capacities. A facility marked as a candidate shelter is not evidence that it is an operating shelter.
- Population NoData is unknown exposure, never zero. Modelled population is not vulnerability.
- No vulnerability labels, composite score, weights, ranking, rank stability, or official priority designations are accepted by this acknowledgment.
- G0 remains not ready; C1–C8 remain v0 and unfrozen. This acknowledgment does not freeze or replace those shared contracts.
