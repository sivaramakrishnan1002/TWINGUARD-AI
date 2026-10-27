# A12 task spec — explainability and parameter sensitivity

## Scope

Use the unchanged November 2015 target and Phase 9C radar-observability mask. Compute diagnostic, spatially held-out grouped permutation importance and partial dependence for the Phase 9C default random-forest reference (feature set iii, including built-up fraction). The reference is a single-event radar-visible susceptibility model. There is no independent event validation, so these diagnostics do not support deployment or causal claims.

Summarize parameter sensitivity from the existing 20-member Phase 12 ensemble for the 12 and 24 November 2015 scenarios. Do not rerun or alter simulation members.

## Inputs

- `data/features/static/cell_table_phase9b_v2.parquet`
- `data/features/predictions/labels_nov2015.parquet`
- `data/processed/alignment/spatial_blocks.tif`
- `data/features/predictions/phase9c_addendum_cr004_v6/radar_observability_mask.tif`
- `data/features/simulation/batch2_v1/simulation_summary.json`
- `data/features/simulation/batch2_v1/member_peak_depth_2015-11-12_DERIVED.npz`
- `data/features/simulation/batch2_v1/member_peak_depth_2015-11-24_DERIVED.npz`

## Method and defaults

- Use feature set iii and the registered default random forest; fixed seed 20261027.
- Use the first buffered spatial outer fold from the Phase 9B split implementation, training-only 3:1 negative sampling, and one model fit. Diagnostics are calculated on at most 2,000 spatially stratified held-out cells.
- Permutation is repeated within held-out 3 km block IDs (3 repeats); report PR-AUC decrease. This limits broad spatial trend leakage but does not remove correlated-feature attribution ambiguity.
- Partial dependence uses training-fold 10th, 25th, 50th, 75th, and 90th percentiles and the same held-out sample. It is associational and may describe feature combinations that are uncommon in the real data.
- Summarize every existing simulation member without changing outputs. Report valid-cell handling, event-wise depth/area metrics and factorial main effects for Manning and infiltration multipliers.
- CPU only: Torch is installed but CUDA is unavailable in this session. No packages are installed.

## Outputs and checks

- `experiments/explainability/batch2_v1/results/` JSON/CSV outputs and input hashes (scripts/spec remain beside it).
- `docs/EXPLAINABILITY_BATCH2.md` report and figure `docs/figures/phase12_parameter_sensitivity_batch2.png`.
- `tests/explainability/test_analysis.py` tests for grouped permutation and member aggregation helpers.
- Existing raw data, feature tables, model artifacts, and simulation artifacts remain read-only.
