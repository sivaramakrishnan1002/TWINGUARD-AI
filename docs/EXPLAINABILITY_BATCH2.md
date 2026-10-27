# A12 — Explainability and simulation parameter sensitivity

> **Diagnostic only.** The Phase 9C model describes a single November 2015 radar-visible label and is not independently validated. The Phase 12 outputs are assumption-based simulations, not observed depth or calibrated uncertainty.

## Data-driven model diagnostic

Used the Phase 9C default random-forest reference (feature set iii; 27 features) and the first outer fold from the existing buffered spatial-block design. The model trained on 31,212 sampled training cells (7,803 positive and 23,409 negative, 3.0:1) and diagnostics used 2,000 held-out cells at 5.60% prevalence. Baseline held-out PR-AUC was 0.2274. Importance permuted one predictor within held-out 3 km blocks and reports the mean PR-AUC decrease over 3 fixed-seed repeats. This is one fold, not a replacement for the five-fold model report.

| Feature | PR-AUC decrease mean | SD |
|---|---:|---:|
| built_up_fraction | 0.02734 | 0.00515 |
| relative_elevation_33cells_m | 0.01261 | 0.01935 |
| distance_to_all_available_water_m | 0.00627 | 0.00707 |
| relative_elevation_15cells_m | 0.00495 | 0.00721 |
| elevation_m | 0.00467 | 0.00783 |
| upslope_area_km2 | 0.00330 | 0.00175 |
| grass_fraction | 0.00294 | 0.00800 |
| relative_elevation_5cells_m | 0.00216 | 0.00251 |
| local_depression_depth_m | 0.00211 | 0.00064 |
| tree_fraction | 0.00208 | 0.01217 |
| bare_fraction | 0.00123 | 0.00093 |
| flow_accumulation_cells_d8 | 0.00103 | 0.00157 |
| d8_flow_length_to_stream_100cells_m | 0.00029 | 0.00017 |
| distance_to_coast_or_sea_m | 0.00025 | 0.00266 |
| d8_flow_length_to_stream_250cells_m | 0.00000 | 0.00000 |
| d8_flow_length_to_stream_500cells_m | 0.00000 | 0.00000 |
| upslope_area_ge_100cells_km2 | 0.00000 | 0.00000 |
| upslope_area_ge_250cells_km2 | 0.00000 | 0.00000 |
| upslope_area_ge_500cells_km2 | 0.00000 | 0.00000 |
| upslope_area_ge_25cells_km2 | -0.00006 | 0.00017 |
| plan_curvature_per_m | -0.00047 | 0.00404 |
| d8_flow_length_to_stream_25cells_m | -0.00055 | 0.00175 |
| hand_d8_accum100_m | -0.00101 | 0.00041 |
| crop_fraction | -0.00110 | 0.00384 |
| profile_curvature_per_m | -0.00240 | 0.00529 |
| slope_deg | -0.00288 | 0.02475 |
| twi_d8_proxy | -0.00838 | 0.00794 |

Partial-dependence curves are supplied in `experiments/explainability/batch2_v1/partial_dependence.csv` for every model feature at training-fold quantiles. They are marginal, can combine correlated features into unrealistic values, and are not causal. See the PNG for the top ten grouped permutation effects and simulation-member area spread.

## Simulation parameter sensitivity

All 20 existing members per event were summarized from their saved peak-depth arrays. No solver was rerun. NoData cells remain excluded from cell summaries; dry zero-depth valid cells remain included. Per-member depth, volume, and areas above 0.01, 0.05, 0.10, 0.30 and 0.50 m are in the CSV files. Factorial level means and differences from the grand member mean are in the JSON. These are sensitivity summaries over the chosen parameter grid, not probability statements.

| Event | Mean peak depth range (m) | Area ≥0.10 m range (km²) | Volume range (m³) |
|---|---:|---:|---:|
| 2015-11-12 | 0.0091–0.0146 | 42.48–83.88 | 1.98e+07–3.2e+07 |
| 2015-11-24 | 0.0051–0.0111 | 22.32–56.16 | 1.12e+07–2.42e+07 |

## Interpretation and limitations

The data-driven result is only an explanation of a model trained/evaluated against one November 2015 SAR-derived map. UNOSAT may share the feature scene, and there is no independent out-of-event flood reference. Do not interpret importance as physical causality or use it to upgrade the map’s validation tier. The simulations use the assumptions documented in `PHASE12_SIMULATION.md`; member spread is parameter sensitivity only. Neither output is operational guidance.

## Reproduction and checks

Command: `.venv\Scripts\python.exe experiments\explainability\batch2_v1\run.py`.
Seed: 20261027. Runtime: 16.63 seconds. Device: CPU (CUDA unavailable). Input hashes are recorded in `experiments/explainability/batch2_v1/explainability_sensitivity.json`.
