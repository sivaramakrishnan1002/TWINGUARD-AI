# TwinGuard AI: a research-stage flood digital twin for Chennai

**Status: INTERNAL DRAFT — not peer reviewed, not approved for submission, and not operational guidance.**

## Abstract

TwinGuard AI is a research prototype for organizing flood-related data and testing how rainfall scenarios, coarse inundation simulation, population exposure, road access, and hypothetical shelter allocation can be connected for Chennai. Lane A Batch 2 produced hindcast/scenario depth fields, impact summaries, a time-dependent road graph, route comparisons, shelter-allocation experiments, and model explanations. These are reproducible research artifacts, not a validated flood-warning system.

The model chain has important evidence limits. The A05 rainfall inputs produce perfect-foresight and product-disagreement scenarios; this is not operational forecast skill. A06 is an assumption-based 600 m local-inertial simulation calibrated against two November 2015 map extents; independent hydraulic validation is unavailable. Routing and allocation use simulated ensemble states and simplified graph/capacity assumptions. Flood-depth observations and real route outcomes are unavailable. A14 therefore found H1 not testable with currently accepted event labels. A20 adds a manifest over already-saved coarse rasters; it does not implement a 3D user interface or service.

## 1. Scope and evidence rules

This draft synthesizes completed Lane A Batch 2 evidence through A15, with A20 cited only for visualization-data readiness. It does not repeat processing or make a new scientific analysis. A11 (priority zones) remains blocked because a defensible, sourced vulnerability proxy or authorized acceptance-criteria revision is still needed; A13 (decision lab) consequently remains blocked. A16 remains manually blocked.

Evidence labels used below:

- **SOURCE / OBSERVED INPUT:** a collected source product or record. “Observed” describes the input product only; it does not mean that model output was observed or independently validated.
- **DERIVED:** a transformed product, including raster indexes or SAR-derived label candidates.
- **SIMULATED:** an output from the A06/A05 numerical scenario chain or a downstream experiment using it.
- **ASSUMPTION:** a selected parameter or rule without local measurement/validation, such as roughness, infiltration, closure threshold, or hypothetical facility capacity.
- **REPLAY:** a replay of historical inputs in a software pipeline. Replay is not live operation.
- **UNKNOWN / NoData:** missing or unassessed information. It is never interpreted here as dry, zero, or passable.

For each numeric result the source report or artifact, run/version, units, time basis, coverage, and provenance are included where the source records them. Reported values below are transcribed from those existing records; no new value has been calculated for this paper.

## 2. Project context and data status

The prototype joins rainfall products and model inputs with elevation, land cover, mapped waterways, population estimates, OSM roads/facilities, and historical flood references. The current accepted event-flood vector references are the 12 and 24 November 2015 UNOSAT layers. These are two dates from the same flood episode, not an independent held-out event. The 2021 NRSC and 2023 NDEM references remain map/PDF products without an accepted digitized validation layer; the December 2015 peak has no accepted official vector extent. OpenCity flood points have unclear dates and approximate locations, so they support only cautious spatial cross-checks. Tier D SAR-derived candidates are not accepted labels.

Input and label limitations are detailed in [A14 temporal/modality feasibility](PHASE19_21_TEMPORAL_EXPERIMENTS.md) and the validation summary [through A15](VALIDATION_REPORT.md). In particular, those reports distinguish map-reproduction checks from independent flood validation.

## 3. Methods and reproducible evidence

### 3.1 Rainfall scenarios and depth fields

A05 reused the A06 NumPy solver and 20 parameter members across three 72-hour UTC event windows, five rainfall scenarios per window, and saved horizons of 6, 12, 24, 48, and 72 hours. The event keys refer to windows 2015-11-30 00:00–2015-12-02 23:00 UTC, 2021-11-11 00:00–2021-11-13 23:00 UTC, and 2023-12-02 00:00–2023-12-04 23:00 UTC. Its reproducible package is `data/features/forecast/batch2_v1/`, with `forecast_summary.json` recording the run, input hashes, scenarios, and member outputs. The grid is 600 m, EPSG:32644, with 2,430 valid cells; output GeoTIFFs are float32 with −9999 NoData. The 2015 `perfect_foresight_imerg` case uses observed daily IMERG totals shaped with an ERA5 hourly pattern. The rain-error quantiles are descriptive product differences, not calibrated forecast errors. Archived numerical weather prediction forecasts are unavailable for 2015. See [Phase 11](PHASE11_FORECAST_BATCH2.md) and [A15 validation](VALIDATION_REPORT.md).

A06 ran the assumption-based local-inertial solver for two November 2015 UNOSAT map dates, with 20 parameter members per date. The 600 m grid and 3 km spatial-block folds were chosen for runtime. Land-cover roughness/infiltration, simplified open-water and waterway sinks, boundary behavior, and building porosity are assumptions; there is no storm-drain network, external catchment inflow, or surveyed hydraulic calibration. The source outputs and diagnostics are under `data/features/simulation/batch2_v1/`. Depth products are documented in metres, but A15 found that the TIFF band unit metadata is unset. See [Phase 12](PHASE12_SIMULATION.md) and [A15 validation](VALIDATION_REPORT.md).

### 3.2 Impact and graph experiments

A07 translated depth ensembles to screened population, facilities, and road-segment impacts. A08 created time-dependent graph snapshots. A09 compared route-selection methods in an observing-system simulation experiment (OSSE), hiding one simulated member as the comparison truth. A10 allocated modelled population to OSM shelter candidates and to schools/colleges treated as hypothetical candidate shelters. Each downstream product inherits its source model assumptions and coverage limits; it is not observed impact or verified accessibility. See [impact](PHASE13_IMPACT_BATCH2_V4.md), [routing](ROUTING_BATCH2.md), and [shelter allocation](SHELTER_ALLOCATION_BATCH2.md).

### 3.3 Explanation and temporal feasibility

A12 reports grouped permutation importance and marginal partial-dependence diagnostics for the Phase 9C model, plus summaries of already-produced A06 parameter-member spread. These are model explanations and sensitivity summaries, not causal effects or new validation. A14 assessed whether the currently accepted labels support the registered temporal/modality hypothesis; it did not fit a new model because an independent held-out event label was unavailable. See [explainability](EXPLAINABILITY_BATCH2.md) and [temporal experiments](PHASE19_21_TEMPORAL_EXPERIMENTS.md).

## 4. Results

### 4.1 A05: rainfall scenario results

The table gives the source-reported 72-hour rainfall total and selected depth summaries for the perfect-foresight IMERG scenario. These are **SIMULATED**, not measured flood depths. The windows and horizons are UTC; “24 h” and “72 h” are saved lead-time states. The depth mean is over 2,430 eligible 600 m cells; mapped area is based on the report’s ensemble-mean depth cut. The 20-member spread is not calibrated statistical uncertainty.

| Event key | 72 h rainfall (mm) | 24 h mean depth (m) | 24 h area ≥0.10 m (km²) | 72 h mean depth (m) | 72 h area ≥0.10 m (km²) | Run/version and evidence |
|---|---:|---:|---:|---:|---:|---|
| 2015-12-02 | 351.54 | 0.0215 | 50.40 | 0.0418 | 59.76 | A05 `batch2_v1`, 20 A06 parameter members; [Phase 11 report](PHASE11_FORECAST_BATCH2.md), summary `data/features/forecast/batch2_v1/forecast_summary.json`. |
| 2021-11-13 | 22.27 | 0.0035 | 6.48 | 0.0021 | 4.68 | Same run/grid/coverage; [Phase 11 report](PHASE11_FORECAST_BATCH2.md), same summary. |
| 2023-12-04 | 279.07 | 0.0058 | 6.48 | 0.0480 | 86.76 | Same run/grid/coverage; [Phase 11 report](PHASE11_FORECAST_BATCH2.md), same summary. |

The 2015 rainfall scenario includes the 1 December IMERG daily peak, but there is no accepted official vector extent for the 1–8 December flood peak. The 2021 NRSC PDF is not an accepted georeferenced raster and the 2023 NDEM map is preliminary. No A05 value in this table is a forecast-skill score or independent flood validation.

### 4.2 A06: coarse simulation and within-episode map reproduction

All values below are spatial-fold averages ± fold-to-fold standard deviation from the same November 2015 map episode. The model output is **SIMULATED**; the UNOSAT extents are calibration/map references, not field-measured depth. The model used 20 parameter members, five buffered 3 km spatial folds, 600 m EPSG:32644 cells, and 2,430 valid cells. Source report: [Phase 12](PHASE12_SIMULATION.md); run/version `data/features/simulation/batch2_v1/`, seed `20261026`.

| Map date | ROC-AUC | PR-AUC | Brier score | ECE | F1 | IoU | Source and time/coverage details |
|---|---:|---:|---:|---:|---:|---:|---|
| 2015-11-12 | 0.673 ± 0.045 | 0.143 ± 0.043 | 0.064 ± 0.019 | 0.029 ± 0.019 | 0.214 ± 0.085 | 0.122 ± 0.052 | [Phase 12 report](PHASE12_SIMULATION.md), `selected_model_spatialcv.json`; event-map extent; same-episode 3 km blocked folds. |
| 2015-11-24 | 0.698 ± 0.018 | 0.169 ± 0.057 | 0.078 ± 0.015 | 0.042 ± 0.046 | 0.241 ± 0.077 | 0.139 ± 0.048 | Same source/run/grid/folds; [Phase 12 report](PHASE12_SIMULATION.md), `selected_model_spatialcv.json`. |

These scores describe reproducing spatial patterns of the calibration maps within buffered folds. They do not measure independent hydraulic accuracy or generalization to another event. The member quantiles are parameter spread, not calibrated confidence coverage. The 40 runs were finite and nonnegative; maximum relative mass-balance error was 0.264% (source report, metres/depth grid and 72-hour UTC event windows; `simulation_summary.json`).

### 4.3 A07: impact-screen examples

At a 0.30 m edge-depth screen (an assumption), A07 reported mean modelled population in depth-screened cells and mean road length screened over the parameter members. It used the `perfect_foresight_imerg` scenario and UTC lead times on the 600 m model grid. The output is **SIMULATED**; population is the known-data WorldPop model estimate, not a census count. `NoData` population cells remain unknown. Source/run: [Phase 13 impact report](PHASE13_IMPACT_BATCH2_V4.md), `batch2_v4_contract`, 75 event/scenario/horizon cases and 4,500 member-threshold rows.

| Event key | Lead (h after UTC window start) | Mean population in depth-screened cells (people) | Mean road length screened (km) | Hazard coverage | Provenance |
|---|---:|---:|---:|---:|---|
| 2015-12-02 | 24 | 34,055.4 | 96.93 | 1.000 | [Phase 13 report](PHASE13_IMPACT_BATCH2_V4.md), `impact_results.jsonl`, `batch2_v4_contract`; simulated perfect-foresight scenario; 600 m / 2,430 eligible cells. |
| 2015-12-02 | 48 | 221,131.2 | 734.00 | 1.000 | Same run/scenario/grid and source artifact. |
| 2021-11-13 | 72 | 864.6 | 1.65 | 1.000 | Same run/scenario/grid and source artifact. |

The source inventory reports 405,601 of 566,307 road features midpoint-assessed on the model grid; 160,706 were outside or unassessed. A value of full raster hazard coverage does not mean all source road edges were covered. The impact report describes access cascades as a coarse component proxy, not origin-destination routing or proof that a facility is operating.

### 4.4 A08/A09: graph and route experiment

The routing graph contains 508,854 nodes, 566,307 road segments, and 1,071,656 directed arcs. A08 wrote 1,500 snapshots across 15 event/scenario cases, 20 parameter members, and five saved UTC horizons (6, 12, 24, 48, and 72 hours). Of the directed arcs, 768,688 (71.73%) mapped to A07 depth cells; 302,968 (28.27%) were unassessed or ambiguous. These are counts of the simulated OSM graph snapshot package, not route-safety measures. A08 keeps unknown depth separate from dry/passable. Ordinary road threshold (0.30 m), underpass/tunnel proxy (0.15 m), speed-reduction curves, and class-default speeds are assumptions; bridges remain unassessed because deck elevation is unavailable. Evidence: [A08 routing report](ROUTING_GRAPH_BATCH2.md), `data/features/routing/time_dependent_batch2/`.

A09 compared four methods over six graph-node OD probes, three event windows, and three UTC snapshots, producing 216 **SIMULATED OSSE** route records (`revision_3`, seed `20261027`; [routing report](ROUTING_BATCH2.md), `route_results.jsonl`). One A06/A05 member was held out as simulated truth; this is not observation-based validation.

| Method | Records with paths (of 54) | Paths with probability (of 54) | Mean expected travel time (s), conditional on whole-route success | Held-out simulated-member failures / assessed paths | Evidence |
|---|---:|---:|---:|---:|---|
| Static free-flow | 54 | 0 | Not assessed | 0 / 0 | [Routing report](ROUTING_BATCH2.md), `comparison_metrics.csv`; every sampled static path crossed at least one unassessed edge. |
| Current flood-aware | 18 | 18 | 1,409.31 | 2 / 18 | Same run and artifact; discrete 6 h state. |
| Horizon-aware snapshot | 18 | 18 | 1,412.42 | 2 / 18 | Same run and artifact; discrete 6/24/72 h states. |
| Uncertainty-aware | 15 | 15 | 1,355.84 | 0 / 15 | Same run and artifact; ensemble member fraction, not calibrated real-world reliability. |

The 39 non-existent uncertainty-aware paths in the 54 route cases show that filtering to assessed/open graph edges can leave no route. The 54 static topological paths have no computed accessibility probability because hazard coverage is incomplete. Results do not establish that any route is safe, usable, or superior in real floods.

### 4.5 A10: hypothetical shelter allocation

A10 version `batch2_v3` evaluates 540 combinations (three events × three saved UTC horizons × 20 members × three capacity factors) over the 600 m EPSG:32644 active grid. Candidate capacities are assumptions: 100 people per mapped shelter, 250 per school, and 500 per college at capacity factor 1.0. Schools and colleges are hypothetical shelter candidates; actual capacity and operational status were not verified. The modelled known WorldPop demand is not a census count, and seven demand cells with unknown population remain flagged as unknown. Source: [A10 allocation report](SHELTER_ALLOCATION_BATCH2.md), `data/features/decision/shelters/batch2_v3/`.

| Capacity factor | Assumed candidate capacity (people) | Mean known modelled demand (people) | Mean served (people) | Mean total unserved (people) | Time basis and evidence |
|---:|---:|---:|---:|---:|---|
| 0.5 | 108,475 | 4,836,739.34 | 68,546.65 | 4,768,192.69 | Mean over 180 event/time/member cases per factor; A10 `batch2_v3`, [allocation report](SHELTER_ALLOCATION_BATCH2.md). |
| 1.0 | 216,950 | 4,836,739.34 | 136,975.33 | 4,699,764.01 | Same coverage and case weighting. |
| 2.0 | 433,900 | 4,836,739.34 | 273,757.83 | 4,562,981.51 | Same coverage and case weighting. |

These are outputs of a hypothetical component/distance allocation, not evacuation capacity or guidance. The method does not verify that sites can operate as shelters or that people can reach them safely.

### 4.6 A12/A14/A15: explanation and validation limits

| Finding | Quantitative result and interpretation | Source, run/version, units, time and coverage |
|---|---|---|
| A12 permutation importance | `built_up_fraction` was the largest listed grouped permutation effect, with mean PR-AUC decrease 0.02734 ± 0.00515 (dimensionless). This is a model diagnostic, not a causal effect. | [Explainability report](EXPLAINABILITY_BATCH2.md), `experiments/explainability/batch2_v1/`; seed `20261027`; one held-out spatial fold for the Phase 9C default RF trained against the single-event SAR-derived label. |
| A12 simulation-member sensitivity | For the 2015-11-12 calibration event, mean peak depth ranged 0.0091–0.0146 m and area ≥0.10 m ranged 42.48–83.88 km² across the saved 20-member parameter set. | Same report and version; 20 existing saved members, not a rerun or probability interval; [explainability report](EXPLAINABILITY_BATCH2.md). |
| A14 H1 feasibility | 10,419 accepted Tier A geometries comprise 4,704 event-flood and 3,710 event-flood geometries on 12/24 Nov 2015 plus 1,360/645 baseline-water geometries on 1 Sep/14 Oct. Metrics: **not computed**; no model was fit. | [Temporal experiment report](PHASE19_21_TEMPORAL_EXPERIMENTS.md), `experiments/temporal_models/batch2_v1/`; four dates in the same 2015 episode. The counts do not create independent event-year validation. |
| A15 validation | No independent flood-depth observations or real route outcomes were available. A05 had no archived NWP forecasts or observed lead-time depths. | [Validation report](VALIDATION_REPORT.md), reviewed A05/A06/A09 artifacts; no independent event/depth sample or observed route sample to score. |

The A14 conclusion is specifically that H1 is **not testable with the current accepted event labels**. It is not a result that a modality performs well or poorly. The validation report also flags unset GeoTIFF band unit metadata: source reports describe depths in metres, but the raster files themselves do not encode the unit.

### 4.7 A20 visualization-readiness boundary

A20 created a deterministic manifest indexing 45 saved A05 raster references and four A06 context groups, retaining the existing 600 m EPSG:32644 grid and NoData masks. It records exact saved UTC times; a per-cell A06 peak map has no single valid instant. The index does not resample or create intermediate quantitative values. Evidence: [A20 readiness report](FLOOD_3D_SCENARIO_READINESS.md), manifest `data/features/visualization3d/batch2_v1/manifest.json`.

This is visualization-ready data indexing only. No 3D UI or service integration, building water level, fine-scale flow, live operation, or hydraulic validation is completed. G0 remains not ready; C1–C8 remain v0/unfrozen; CR-006 is not complete.

## 5. Discussion

The current project evidence demonstrates a connected research workflow: saved rainfall scenarios feed a coarse model, model depth screens feed impact and graph experiments, and those feeds support controlled allocation and route comparisons. Reproducibility is improved by versioned output folders, source hashes, explicit event/time semantics, fixed seeds, and explicit unknown coverage.

The workflow is not yet a validated digital twin in the operational sense. A05 is a hindsight/scenario wrapper, not evidence of advance forecast skill. A06 reproduces some of the same 2015 map patterns under spatial blocking, but has no independent hydraulic observations, and its physical assumptions and 600 m grid limit interpretation. A07–A10/A09 transform those assumptions into downstream results; those results inherit rather than remove the upstream uncertainty. Incomplete edge-to-cell mapping limits flood-aware routing, while assumed speeds, thresholds, and shelter capacities add further uncertainty. Model-explanation effects cannot be interpreted causally, and the available accepted labels cannot test H1 across events.

## 6. Limitations and evidence needed next

1. **Independent event labels:** QA-accepted, date-matched flood extents for another event are needed for out-of-event model validation. The 2021 NRSC and 2023 NDEM PDFs require georeferencing/digitization and QA; December 2015 official vector extent remains absent.
2. **Hydraulic observations:** gauge or surveyed flood-depth/water-level observations with time, datum, and location are needed to evaluate depth magnitude and timing independently.
3. **Forecast evidence:** archived weather forecasts or forecast-time rainfall products are needed to measure actual lead-time forecast skill; perfect-foresight hindsight cannot do so.
4. **Routing evidence:** verified road closure/passability observations, bridge/underpass elevations, and trip outcomes are needed before assessing real-world route performance.
5. **Exposure and facilities:** population remains a model estimate with NoData; shelter capacities and operations are hypothetical/unverified. A defensible, sourced vulnerability proxy is required for A11; its acceptance/status must be resolved by the authorized owner before A13.
6. **Integration and contracts:** A20 does not implement a 3D service/UI. G0 and frozen contracts are prerequisites for the downstream integration tasks, and remain unresolved.

## 7. Reproducibility and editorial checks

This document is a synthesis only; no model was run and no data or owner output was changed. Quantitative statements above are paired with a source report/artifact and the available run/version, units, UTC basis, spatial coverage, and provenance. Unknown and NoData values are not converted to zero. Forecast, simulation, impact, routing, allocation, explanation, and replay products retain their source labels and caveats.

Reproducibility records remain in the cited source reports and JSON/CSV/GeoTIFF artifacts. A15 summarizes the relevant source hashes, commands, runs, and checks; see [A15 validation](VALIDATION_REPORT.md). This draft has not passed academic peer review, supervisor review, or any authorized publication review.

Documentation closeout for A17: 30 local report citations and 9 explicit artifact paths checked in this file; the companion final report checked 19 local citations and 5 artifact paths. The applicable Lane A suite (`.venv\Scripts\python.exe -m pytest tests\visualization3d tests\phase8 tests\phase9 tests\phase9b tests\phase9c tests\phase10 tests\phase11 tests\phase12 tests\phase13 tests\routing tests\decision tests\explainability tests\labels tests\temporal_models -q`) passed **121 tests**. The read-only raw audit (`.venv\Scripts\python.exe tools\audit_raw_logs.py`) reported 157 files / 30,544,672,450 bytes, 157 hash matches, zero missing comparable hashes, and zero mismatches. PyTorch `2.14.1+cu126` reported CUDA available on the NVIDIA GeForce RTX 3050 Laptop GPU; no GPU computation was applicable or run for this writing task, and no package was installed.
