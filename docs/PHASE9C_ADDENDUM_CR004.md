# Phase 9C addendum CR-004

## Scope

The unchanged Phase 9 target is a single November 2015 SAR-derived event. The model describes radar-visible flooding. It is not field truth, a forecast, or cross-event evidence.

## WorldPop eligibility audit

Phase 9 eligible cells: 1,196,300; retained despite WorldPop NoData: 117,705; radar-visible evaluation cells: 574,018, prevalence 0.066538. The previous WorldPop mask had removed 25,551 positive cells. WorldPop is exposure only. The source NoData is -99999; metadata does not identify why each cell is missing. Descriptive distributions are in the JSON; they do not prove a specific cause.

## Models and baselines

All three feature sets use the same buffered 3 km spatial folds, default random forest, training-only sampling/calibration, and true-prevalence outer evaluation. Population, road-node distance and building density are excluded. No search was run. Feature set C includes built-up fraction as requested.

| Set | Prevalence | PR-AUC | Lift | ROC-AUC mean (SD) | Brier mean (SD) |
|---|---:|---:|---:|---:|---:|
| i_terrain_hydrology | 0.066538 | 0.214173 | 3.219 | 0.7813 (0.0216) | 0.05805 (0.01522) |
| ii_plus_landcover_no_built | 0.066538 | 0.211003 | 3.171 | 0.7932 (0.0228) | 0.05791 (0.01489) |
| iii_plus_built_fraction | 0.066538 | 0.219007 | 3.291 | 0.8009 (0.0204) | 0.05773 (0.01492) |

Same-fold baselines and all fold metrics are in the JSON. Dense-urban exclusion results include prevalence, PR-AUC and lift. Top 1/2/5/10 percent precision and recall are reported by built-up stratum in the JSON.

## OpenCity points and uncertainty

OpenCity point dates are unclear and locations approximate. The JSON reports top 1/5/10/20 percent hit rates and a chance comparison matched by built-up stratum and dominant land cover, with 3 km block bootstrap intervals.

Conformal coverage: not computed for this corrected eligibility domain. Earlier Phase 9C bands cannot be carried over as if recalibrated. Do not use them as a 90% guarantee.

## Physical complement and Phase 10 display

Outside the radar observability mask, a separate rank-based PHYSICAL layer is shown with an unreliable-from-labels flag. It is not fitted to flood labels and is not a flood probability. The Phase 10 composite keeps the physical score and apparent radar class in separate bands.

## Reproducibility

Command: .venv/Scripts/python.exe pipelines/phase9c/addendum_cr004.py. Seed: 20261025. Hyperparameter search: none.
