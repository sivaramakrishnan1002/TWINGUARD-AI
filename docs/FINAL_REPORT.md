# TwinGuard AI — project results report

**Status: INTERNAL DRAFT — for review only.** This report is not peer reviewed or approved for submission. It is not a warning, emergency guidance, or proof that routes are safe.

## What this work currently shows

TwinGuard AI has a research workflow that links rainfall scenarios, a coarse flood simulation, population/road impact summaries, route experiments, and hypothetical shelter allocation for Chennai. The outputs are useful for testing data flow and research questions. A05 hindcast/scenario comparisons are **not operational forecast skill**, and the work does **not** yet demonstrate a validated flood digital twin.

The evidence labels matter:

- Rainfall products, maps, population, land cover, and mapped roads/facilities are source inputs. Some are modelled or incomplete source products (for example, WorldPop population is an estimate).
- Depth, impact, routing, and allocation outputs are **DERIVED/SIMULATED**. They are not observed flood depths, measured impact, or real evacuation outcomes.
- Roughness, infiltration, depth thresholds, speed adjustments, and candidate shelter capacities include **ASSUMPTIONS**.
- A historical pipeline replay is a **REPLAY**, not live sensor operation.
- **NoData/unknown** coverage stays unknown. It does not mean dry, zero population, or a passable road.

## Results at a glance

| Work | What was produced | What the numbers mean | Evidence |
|---|---|---|---|
| A05 rainfall scenarios | Three 72-hour UTC event windows; five rainfall scenarios per window; 20 parameter members; saved 6/12/24/48/72 h outputs on a 600 m EPSG:32644 grid with 2,430 valid cells. | For the 2015-12-02 perfect-foresight IMERG case, the 72-hour rainfall total was 351.54 mm; mean simulated depth was 0.0215 m at 24 h and 0.0418 m at 72 h. These are scenario outputs, not forecast accuracy. | Run `batch2_v1`; [Phase 11 report](PHASE11_FORECAST_BATCH2.md), `data/features/forecast/batch2_v1/forecast_summary.json`. |
| A06 simulation | Two November 2015 cases, 20 parameter members each, 3 km spatial blocks, 600 m grid. | For 24 Nov, spatial-fold map-reproduction IoU was 0.139 ± 0.048; it compares with the same 2015 mapping episode and is not independent hydraulic validation. | Run `batch2_v1`, seed `20261026`; [Phase 12 report](PHASE12_SIMULATION.md), `selected_model_spatialcv.json`. |
| A07 impact | 75 event/scenario/time cases and 4,500 member-threshold rows. | For 2015-12-02 at 24 h and the assumed 0.30 m depth screen, mean population in screened cells was 34,055.4 people and mean screened road length was 96.93 km. These are model outputs; population is a known-data estimate. | `batch2_v4_contract`; [Phase 13 report](PHASE13_IMPACT_BATCH2_V4.md), `impact_results.jsonl`. |
| A08/A09 routing | Time-dependent graph and 216 route-comparison records from six graph-node probes. | 71.73% of directed arcs had mapped depth cells. Only 18 of 54 current and 18 of 54 horizon-aware cases had paths in the assessed graph; missing or structurally unassessed edges were not treated as passable. | A08 snapshot package; A09 `revision_3`, seed `20261027`; [graph report](ROUTING_GRAPH_BATCH2.md), [routing report](ROUTING_BATCH2.md). |
| A10 shelter allocation | 540 simulated cases; final corrected outputs are `batch2_v3`. | At the assumed capacity factor 1, mean served demand was 136,975.33 people and mean unserved demand was 4,699,764.01 across 180 event/time/member cases. Candidate capacities and schools/colleges-as-shelters are assumptions. | [A10 report](SHELTER_ALLOCATION_BATCH2.md), `data/features/decision/shelters/batch2_v3/`. |
| A12 explanation | Grouped feature importance and saved simulation-member sensitivity summaries. | Built-up fraction had the largest reported grouped permutation effect: mean PR-AUC decrease 0.02734 ± 0.00515. This is not a causal effect and comes from a single-event labelled model. | Seed `20261027`; [A12 report](EXPLAINABILITY_BATCH2.md), `experiments/explainability/batch2_v1/`. |
| A14 temporal study | Feasibility check of accepted event labels and modalities. | H1 is **not testable** with current accepted event labels. No model was fitted and metrics were **not computed**. | [A14 report](PHASE19_21_TEMPORAL_EXPERIMENTS.md), `experiments/temporal_models/batch2_v1/`. |
| A15 validation | Read-only review of A05, A06, and A09 outputs. | Independent flood-depth observations and real route outcomes were unavailable. A05 has no archived NWP forecast evidence to score operational forecast skill. | [A15 validation report](VALIDATION_REPORT.md). |
| A20 data readiness | A manifest indexes existing saved-time rasters and preserves their source grid and NoData. | Regional visualization data only; this did not build a 3D UI or service. | [A20 report](FLOOD_3D_SCENARIO_READINESS.md), manifest `data/features/visualization3d/batch2_v1/manifest.json`. |

## How to read these numbers

### Rain and depth

A05 uses hindsight/perfect-foresight and rainfall-source comparison scenarios. For the 2015 event, perfect-foresight IMERG is based on observed daily rainfall totals distributed using an ERA5 hourly pattern. The outputs were saved at specific leads only; there are no observed hourly flood depths to compare with them. A05’s 20-member depth spread is not calibrated uncertainty. The depth rasters use 600 m cells; their source reports describe depth in metres, although the TIFF unit tag is unset. Full source dates, grid details, coverage, scenario statistics, and hashes are recorded in the [Phase 11 report](PHASE11_FORECAST_BATCH2.md) and [validation report](VALIDATION_REPORT.md).

A06 is a coarse, assumption-based local-inertial simulation. Its 2015 November blocked-fold metrics are map-reproduction scores against the same event episode. They do not show that the simulated depths match measured water or transfer to a different flood. The GLO-30 elevation input is a surface model; storm drains, external catchment inflow, and detailed channel stages are unavailable. See [Phase 12](PHASE12_SIMULATION.md).

### People, facilities, roads, and shelters

A07 population values are based on the known part of WorldPop and retain source NoData. Road and facility screening uses a coarse 600 m grid and assumed depth cut-points. A07 midpoint-assessed 405,601 of 566,307 road source features; the remainder were outside the active grid or unassessed. “Hazard coverage 1.000” for an individual raster output does not imply that all source road edges were assessed. See [Phase 13](PHASE13_IMPACT_BATCH2_V4.md).

A09 route comparisons use six synthetic graph-node origin/destination probes. One simulated model member is hidden as the OSSE reference. Of 1,071,656 directed arcs, 768,688 had an A07 depth-cell mapping; 302,968 remained unassessed or ambiguous. Route probabilities are ensemble fractions where coverage is complete, not calibrated chances of real-world access. No real journey outcomes were available. See [routing](ROUTING_BATCH2.md) and [A15 validation](VALIDATION_REPORT.md).

A10’s schools and colleges are candidate shelters only by assumption. Capacities were set hypothetically, and no actual operational status or capacity was verified. The allocation is a component/distance calculation, not direction-aware routing or a tested evacuation plan. See [A10 report](SHELTER_ALLOCATION_BATCH2.md).

## Unanswered questions and blockers

- **Independent flood validation:** accepted, georeferenced labels for an additional event are still needed. The 2021 NRSC and 2023 NDEM references remain PDF/map-only and require QA before use; no accepted vector extent covers the December 2015 peak.
- **Depth validation:** independent flood-depth or water-level observations are unavailable.
- **Forecast skill:** archived forecast fields and observed lead-time depths are unavailable; operational forecast skill is not demonstrated.
- **Route safety:** real road passability, closure, trip-time, bridge-deck, and underpass observations are unavailable; no route is established as safe.
- **Priority zones and decision lab:** A11 waits on a defensible, sourced vulnerability proxy or an authorized revision of its acceptance criteria. A13 depends on A11. These tasks were not treated as complete.
- **MLflow:** A16 remains manually blocked; no setup or tracking work was started as part of this report.
- **Model hypothesis H1:** A14 found the currently accepted labels insufficient for an independent held-out event comparison; its metrics remain not computed.
- **3D and integration:** A20 only indexes saved coarse rasters. G0 remains not ready and C1–C8 remain v0 and unfrozen. No 3D UI/service integration or CR-006 completion is claimed.

## Status and next evidence

The project has a reproducible research pipeline, not a field-validated or live system. The most valuable next evidence is an independently QA-accepted flood map for another event, independent depth/water-level observations, and observed road passability/travel outcomes. A11 also needs the authorized owner to resolve its vulnerability-proxy prerequisite. Until those evidence gaps are addressed and the applicable review gates are passed, results should remain internal research outputs.

## Editorial and reproducibility checks

- Every numeric result in this report points to its source report or artifact, with run/version and units/time basis/coverage stated where recorded.
- Source inputs are distinguished from DERIVED/SIMULATED/ASSUMPTION/REPLAY products. NoData is retained as unknown.
- A20 is described as saved-raster indexing only; no UI/service or CR-006 completion is implied.
- No new analysis was performed for this synthesis. Reproduction commands, seeds, source hashes, spatial coverage, and task checks remain in the cited source reports; [A15 validation](VALIDATION_REPORT.md) consolidates checks for A05/A06/A09.
- This remains an internal draft pending authorized Lane A review and academic/supervisor review.

Current closeout checks: all 19 local report citations and 5 explicit artifact paths in this file resolve. The applicable Lane A suite passed **121 tests** (exact command is recorded in [PAPER_DRAFT.md](PAPER_DRAFT.md)). The raw audit matched 157 of 157 files (30,544,672,450 bytes), with zero missing comparable hashes and zero mismatches. PyTorch `2.14.1+cu126` reported CUDA available on the NVIDIA GeForce RTX 3050 Laptop GPU; no GPU work was applicable or run, and no package was installed.
