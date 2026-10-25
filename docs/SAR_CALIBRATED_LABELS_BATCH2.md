# Calibrated SAR candidate labels — Batch 2

**Result: TIER C candidate.** The held-out comparison only measures reproduction of the UNOSAT 24 Nov 2015 map. It is not independent flood validation, because UNOSAT may have used the same SAR scene.

Training/evaluation used 1,072,291 cells (25,266 positive; prevalence 2.3563%) from 1,196,300 eligible CMA cells. HAND was finite for 24,511 cells (2.29%) and imputed within training folds with a missingness indicator.

## Out-of-fold results

| Candidate/baseline | ROC-AUC | PR-AUC | F1 | IoU | Precision | Recall | Brier | ECE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| sar_full | 0.9921 | 0.8353 | 0.7482 | 0.5977 | 0.7384 | 0.7583 | 0.00837 | 0.00075 |
| vv_only | 0.9921 | 0.8390 | 0.7510 | 0.6013 | 0.7343 | 0.7685 | 0.00828 | 0.00080 |
| elevation_only | 0.4868 | 0.0669 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.02344 | 0.00331 |
| waterway_distance_only | 0.3871 | 0.0242 | 0.0460 | 0.0236 | 0.0236 | 1.0000 | 0.02323 | 0.00312 |
| random | 0.4987 | 0.0236 | 0.0243 | 0.0123 | 0.0243 | 0.0242 | 0.33381 | 0.47692 |

The default model is not treated as an accepted flood label unless pooled held-out IoU reaches 0.25. The candidate and baselines use the same buffered 3 km spatial folds and training-only thresholds. Per-fold counts and metrics are in `data/features/labels/sar_calibrated_batch2/metrics.json`.

## Decision and limits

Gate passed for a Tier C candidate only; proceed with unchanged frozen method on the specified dates, with independent checks.
No SAR output is called ground truth. The training comparison is circular if the official map was interpreted from this 24 Nov scene. Missing HAND is extensive and model behavior may mostly reflect the other SAR and land-cover features. The 2023 and 2021 PDF maps remain weak or manual validation references.

## Reproducibility

Run: `.venv/Scripts/python.exe pipelines/phase9c/calibrated_sar_candidate.py`. Seed 20261025; 5 outer and 3 inner buffered spatial folds; no hyperparameter search.

## Spatial fold results

Fold-specific held-out results for the full model; thresholds were selected using the inner training blocks.

| Fold | buffered train cells | test cells | threshold | IoU | precision | recall |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 856,909 | 114,917 | 0.37 | 0.6560 | 0.8409 | 0.7490 |
| 2 | 552,743 | 333,569 | 0.45 | 0.6198 | 0.8187 | 0.7184 |
| 3 | 464,597 | 364,879 | 0.40 | 0.5437 | 0.6330 | 0.7939 |
| 4 | 693,097 | 210,612 | 0.39 | 0.5458 | 0.6580 | 0.7620 |
| 5 | 946,471 | 48,314 | 0.41 | 0.6070 | 0.7212 | 0.7931 |

Across folds, full-model IoU mean ± SD: 0.5945 ± 0.0437.

The full model did **not** beat VV-only: VV-only pooled PR-AUC (0.8390) and IoU (0.6013) slightly exceed full-model PR-AUC (0.8353) and IoU (0.5977). It does beat the specified elevation-only, waterway-distance-only and random baselines on pooled ROC-AUC/PR-AUC/IoU. The very high map agreement remains vulnerable to same-scene circularity.
