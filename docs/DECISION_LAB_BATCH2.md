# A13 — Phase 22 decision lab (Batch 2)

**Status: simulated, descriptive research only.** This is not an operational forecast, real-world route safety assessment, validated hydraulic result, or emergency guidance. H2–H5 are not confirmed by these experiments.

## Inputs and reproducibility

The run used only the task-registered final revisions: A05 `data/features/forecast/batch2_v1/`, A09 `data/features/routing/results/batch2_v1/revision_3/`, A10 `data/features/decision/shelters/batch2_v3/`, A11 `data/features/decision/priority_zones/batch2_v1/revision_2/`, and A12 `experiments/explainability/batch2_v1/`. SHA-256 hashes, file sizes, A09 run identity, A05 member files and A05 validity-mask rasters are recorded in `experiments/decision_lab/batch2_v1/input_provenance.json` and `run_manifest.json`. The A11 hazard, population-exposure and facility-access-loss indicators remain separate. A12 is cited as a diagnostic input only; no feature importance is converted into a decision weight.

The analysis plan was saved before calculating metrics at `experiments/decision_lab/batch2_v1/analysis_plan.json`. Seed: **20261028**. Paired bootstrap: **5,000 replicates**, clustered by event for H2 and by event within paired route cases for H3/H4. Only three event clusters exist, so the intervals are descriptive simulation sensitivity, not independent-event inference. Case/member win fractions are descriptive fractions of these simulated cases, never real-world probabilities or confidence.

## H2 — deterministic and uncertainty-aware depth summaries

For each of 3 event windows × 5 A05 scenarios × 5 saved horizons (**75 cases**), A05 member 12 (nominal parameter multipliers 1.0/1.0) was the deterministic reference. The uncertainty-aware point estimate was the cellwise median of forecast members 1–19, with their p05–p95 interval. Member 20 was held out as a **synthetic simulation member**, not an observation. The valid-data mask came from each matching A05 p50 GeoTIFF: **2,430 valid cells and 3,642 NoData/out-of-model cells per case** on the 88 × 69, 600 m EPSG:32644 grid. NoData was excluded, never interpreted as dry.

| Event key | Cases | Member 12 MAE (m) | Ensemble median MAE (m) | p05–p95 coverage of member 20 | Mean interval width (m) |
|---|---:|---:|---:|---:|---:|
| 2015-12-02 | 25 | 0.005490 | 0.004458 | 79.69% | 0.010191 |
| 2021-11-13 | 25 | 0.002768 | 0.002841 | 85.33% | 0.005909 |
| 2023-12-04 | 25 | 0.004162 | 0.003695 | 82.44% | 0.007809 |
| Macro mean across 75 cases | 75 | 0.004140 | 0.003665 | **82.48%** | 0.007969 |

The ensemble median minus member 12 MAE averaged **−0.000476 m** (event-cluster bootstrap 95% descriptive interval **−0.001032 to +0.000072 m**). It had lower MAE in **24**, tied in **8**, and higher MAE in **43** of the 75 cases; the aggregate mean improvement is small and does not dominate case-by-case. The nominal 90% interval covered the held-out member in 82.48% of valid cells, **7.52 percentage points below nominal**. This is a same-ensemble synthetic-member diagnostic, not empirical calibration, observed flood validation, or evidence that the interval is calibrated for real events.

## H3 — uncertainty-aware versus current-state route alternative

There were **54 exactly paired cases** (same event/scenario, requested horizon, origin and destination; 3 event windows × 3 horizons × 6 OD probes). A09 reported a route for **15/54** uncertainty-aware cases and **18/54** current-state cases; the remaining statuses were `NO_TOPOLOGICAL_PATH` (39 and 36 respectively). These are simulated graph outcomes, not safety outcomes.

| Outcome (A = uncertainty-aware; lower is better unless noted) | A wins / ties / losses / missing | Paired A−current mean | 95% event-cluster interval |
|---|---:|---:|---:|
| A09 modeled route-failure fraction | 0 / 15 / 0 / 39 | 0.000 | [0.000, 0.000] |
| Travel time (seconds) | 3 / 12 / 0 / 39 | −0.010 s | [−0.017, 0.000] s |
| Expected depth-distance exposure (m²) | 1 / 12 / 2 / 39 | −0.025 m² | [−0.076, +0.001] m² |
| Assessed-edge coverage (higher is better) | 0 / 15 / 0 / 39 | 0.000 | [0.000, 0.000] |

The two methods had median travel times of **1,030.42 s** and **1,032.32 s** among their respective found routes, but these unmatched medians are descriptive only. The paired travel-time difference uses only cases where both routes were found. Missing routes remain missing, not zero travel time or safe passage. Route failure, travel time, exposure and coverage are reported separately; no score combines them.

## H4 — horizon-aware versus current-state routes

There were also **54 paired cases**. Each method found **18/54** routes and had 36 `NO_TOPOLOGICAL_PATH` results. Travel-time pairs were available in 16 cases; arrival-time pairs in 16 cases; two route-found cases did not overlap between methods. Horizon-aware minus current-state travel/arrival time averaged **+3.314 s** (95% descriptive event-cluster interval **−0.017 to +9.970 s**): 3 better, 12 tied, 1 worse, 38 missing for travel time. For arrival time, 3 were earlier, 12 tied, 1 later, and 2 missing. Expected depth-distance exposure was available for 18 paired found routes: 4 lower, 12 tied, 2 higher; mean difference **−73.048 m²** (interval **−129.327 to +0.001 m²**). Assessed-edge coverage was tied for the 18 paired found routes; 36 were missing. These are saved A09 simulation results, not live or observed travel outcomes.

## H5 — counterfactual checks

- **Departure one hour earlier/later: unavailable.** A08 saved snapshots at 6, 12, 24, 48 and 72 hours; the A09 route file has no exact ±1-hour reroute. No interpolation or new route search was done.
- **Bridge closure: saved-path invalidation only.** Applying the predeclared selection rule (most-used bridge in saved static paths; tie-break by lowest edge ID) identified directed edge **64052**, present in **9 saved static route records**. A08 labels bridges `UNASSESSED_STRUCTURE`; closure is hypothetical. The artifacts do not contain reroutes with this bridge removed, so alternative paths and their travel times are unavailable.
- **Shelter candidate unavailable: allocation withdrawal only.** The registered A10 candidate set and allocation detail selected OSM shelter **28275720** (candidate `osm:28275720`, assumed capacity **100 people**, snap distance **20.31 m**) by highest cumulative saved allocation, with numeric OSM ID as the tie-break. Its saved allocation sums to **63,000 people-model-estimate** across 180 grouped records. Allocation detail does not identify capacity factor per row. The sensitivity withdraws those recorded allocations without redistributing them; this is not evidence of real occupancy or availability, and the A10 candidate capacities and weak-component allocation method remain assumptions.

## Caveats, tools, and checks

All A05/A06 depths, A08/A09 route outcomes, and A10 allocations are simulations or model estimates. A05 is at 600 m resolution and its held-out member is from the same parameter ensemble. A09 has six OD probes per event and incomplete assessed-network coverage; topological non-paths are not evidence of flooding. A10 uses assumed shelter/school/college capacities and a coarse weak-component screen. The three event clusters are too few for broad statistical inference. A11’s indicators are not merged into vulnerability, a weighted score, rankings, or official priority zones. A12 remains a single-event radar-label diagnostic, not independent validation.

GPU check: PyTorch **2.14.1+cu126**, CUDA available, NVIDIA **GeForce RTX 3050 Laptop GPU**, driver **566.07** (CUDA runtime reported **12.7**). A representative quantile benchmark over 19 × 455,400 values took **0.140 s** with NumPy CPU versus **0.453 s** including CUDA transfer and calculation; maximum absolute difference was **1.19×10⁻⁷**. This task’s arrays and route comparisons are small, so the reproducible CPU/NumPy path was faster and was used for the outputs. No packages were installed.

Commands run:

```text
.venv\Scripts\python.exe tools\master\verify_state.py
.venv\Scripts\python.exe tools\master\next_task.py --lane A
.venv\Scripts\python.exe -m pytest tests\decision_lab\test_phase22_decision_lab.py -q
.venv\Scripts\python.exe pipelines\decision\phase22_decision_lab.py
```

The focused tests cover exact route joins, fixed-seed paired bootstrap, missing values, raster NoData versus valid zero, and prohibited composite/vulnerability fields. Results:

- Focused A13 tests: `6 passed`.
- Applicable Lane A suite: `133 passed` across `tests/decision`, `tests/decision_lab`, `tests/explainability`, `tests/labels`, `tests/phase8`, `tests/phase9`, `tests/phase9b`, `tests/phase9c`, `tests/phase10`, `tests/phase11`, `tests/phase12`, `tests/phase13`, `tests/routing`, and `tests/visualization3d`.
- Raw audit: `157` data files / `30,544,672,450` bytes; `157` hash matches, `0` without comparable hashes, `0` mismatches.
- Output generation: `2.13 s` in the final run; 75 H2 cases, 216 route records, and 293,374 A10 allocation-detail rows read.
- GPU benchmark (NumPy CPU vs CUDA transfer + quantile): 0.140 s vs 0.453 s; outputs differed by at most `1.1920929e-07`. CPU used for the final computation.
- No data under `data/raw/` was changed. No package was installed. The task commit is recorded in the Lane A progress board and official task state after closeout.

### Output files

- `experiments/decision_lab/batch2_v1/analysis_plan.json`
- `experiments/decision_lab/batch2_v1/h2_synthetic_holdout_metrics.json`
- `experiments/decision_lab/batch2_v1/h3_h4_route_comparisons.json`
- `experiments/decision_lab/batch2_v1/h5_counterfactuals.json`
- `experiments/decision_lab/batch2_v1/input_provenance.json`
- `experiments/decision_lab/batch2_v1/run_manifest.json`
- `pipelines/decision/phase22_decision_lab.py`
- `tests/decision_lab/test_phase22_decision_lab.py`
