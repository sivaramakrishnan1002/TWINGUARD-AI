# Phase 9C — urban observability and independent checks

> PILOT. One November 2015 SAR-derived target; not field validated, not an event forecast.

## Radar observability mask

A cell is assessed only if built-up fraction is ≤0.50, slope is ≤15°, both the 19 Oct reference and 24 Nov event RTC masks are valid, and neither quality flag carries layover bit 4 or shadow bit 16. Missing slope is excluded. Other cells inside the CMA have no radar-model value and are labelled **not assessed from radar labels**.

| Mask count | Cells |
|---|---:|
| cma cells | 1,319,380 |
| assessed cells | 481,244 |
| not assessed cells | 838,136 |
| eligible land after phase9 water and population masks | 1,078,595 |
| dense urban gt 0 50 nonexclusive | 528,512 |
| layover or shadow nonexclusive | 0 |
| steep gt 15deg nonexclusive | 3,328 |
| invalid or unobserved reference or event nonexclusive | 0 |
| slope nodata nonexclusive | 215,387 |
| phase9 eligible before phase9b masks | 1,196,300 |
| population nodata excluded | 117,705 |
| model cells inside mask | 481,244 |
| model positives inside mask | 23,962 |

Nonexclusive exclusions and combined reason codes are in `PHASE9C_METRICS.json`; `urban_confidence.tif` is 1 only for model-assessed cells and 0 where the data-driven output is unreliable/not assessed.

## Spatial evaluation and 9B comparison

Nested spatial validation uses the same five 3 km block folds, one-block buffer, two contiguous inner block-row folds, 3:1 training-only negative sampling, true-prevalence held-out cells, and 30 random configurations per tree family as Phase 9B. Same Phase 9B predictors and single-feature logistic baselines were retained. The 2015 target itself is unchanged.

| Metric | Phase 9C inside mask (outer-fold mean ± SD unless pooled stated) | Phase 9C pooled OOF | PR-AUC block bootstrap 95% CI | Phase 9B v2 comparison |
|---|---:|---:|---:|---:|
| pr_auc | 0.1945 ± 0.0464 | 0.1605 | [0.12118667062309145, 0.20579803611728487] | 0.2599 ± 0.0702 |
| roc_auc | 0.8219 ± 0.0301 | 0.7538 | — | 0.898660473818033 |
| brier | 0.0448 ± 0.0095 | 0.0448 | — | 0.028544262566512546 |
| ECE (10 equal-width bins) | 0.0268 ± 0.0188 | 0.0071 | — | 0.0136 |

### Paired comparisons against baselines

| Baseline | PR-AUC delta mean ± SD (folds won) | ROC-AUC delta mean ± SD (folds won) | Brier improvement mean ± SD (folds won) |
|---|---:|---:|---:|
| elevation_logistic | +0.0742 ± 0.0458 (5/5) | +0.2547 ± 0.1530 (5/5) | +0.0029 ± 0.0022 (5/5) |
| river_distance_logistic | +0.1316 ± 0.0151 (5/5) | +0.3639 ± 0.1008 (5/5) | +0.0037 ± 0.0023 (5/5) |
| twi_logistic | +0.1033 ± 0.0430 (5/5) | +0.1124 ± 0.0351 (5/5) | +0.0025 ± 0.0020 (5/5) |
| slope_logistic | +0.0826 ± 0.0454 (5/5) | +0.0783 ± 0.0415 (5/5) | +0.0023 ± 0.0020 (5/5) |
| relative_elevation_15_logistic | +0.1365 ± 0.0258 (5/5) | +0.3009 ± 0.1197 (5/5) | +0.0042 ± 0.0033 (5/5) |
| hand_logistic | +0.1432 ± 0.0408 (5/5) | +0.3180 ± 0.0509 (5/5) | +0.0031 ± 0.0021 (5/5) |
| terrain_logistic | +0.0725 ± 0.0339 (5/5) | +0.0745 ± 0.0346 (5/5) | +0.0023 ± 0.0023 (5/5) |
| random_prevalence | +0.1447 ± 0.0400 (5/5) | +0.3219 ± 0.0301 (5/5) | +0.0031 ± 0.0021 (5/5) |

Positive values mean Phase 9C improved the score (for Brier, lower is better). Against the prior Phase 9B v2 model, Phase 9C has lower pooled ROC-AUC/PR-AUC and higher Brier; pooled ECE is lower. The 9B and 9C evaluation domains differ, so these raw differences are descriptive, not a fair paired model comparison. The model is not accepted as a reliable forecast from this single-event exercise.

## Point cross-check (not radar-label validation)

The two raw OpenCity point KMLs contain 945 approximate, undated observed-flood points. They were not used for fitting or threshold selection. 99 points had radar-model output; 12 additional points had physical-only support; 834 were not scored (833 had no radar or physical-support score; 1 had no built-up cell value). Hit-rate denominators include only scored points: 99 radar points plus 12 physical-only points. Point bootstrap resamples 3 km blocks; chance draws match both the point's built-up-fraction bin and dominant class among tree, crop, grass, bare, built-up and water. This preserves the dominant-class mix, not each continuous fractional composition. Because dates are unclear and locations approximate, this is a spatial cross-check, not dated field validation.

| Top share of mapped rank cells | Point hit share [95% CI] | Land-cover-matched random-cell chance [95% CI] | n scored / chance matched |
|---:|---:|---:|---:|
| 1% | 0.00% [0.00%, 0.00%] | 0.29% [0.00%, 1.75%] | 111 / 111 |
| 5% | 0.00% [0.00%, 0.00%] | 1.52% [0.00%, 4.26%] | 111 / 111 |
| 10% | 0.90% [0.00%, 3.03%] | 3.17% [0.00%, 7.14%] | 111 / 111 |
| 20% | 2.70% [0.00%, 6.52%] | 6.67% [2.41%, 11.88%] | 111 / 111 |

### Point hits by built-up fraction

Each row uses only scored points in that built-up bin; the remaining source points have no applicable map score. CIs use the same 3 km point-block bootstrap.

| Top share | Built-up bin | Point hits [95% CI] | Matched chance [95% CI] | n scored / chance matched |
|---:|---|---:|---:|---:|
| 1% | 0 to 0.1 | 0.00% [0.00%, 0.00%] | 0.64% [0.00%, 4.55%] | 31 / 31 |
| 1% | 0.1 to 0.3 | 0.00% [0.00%, 0.00%] | 0.00% [0.00%, 0.00%] | 27 / 27 |
| 1% | 0.3 to 0.5 | 0.00% [0.00%, 0.00%] | 0.01% [0.00%, 0.00%] | 41 / 41 |
| 1% | 0.5 to 0.75 | no points | no matched points | 0 / 0 |
| 1% | 0.75 to 1 | 0.00% [0.00%, 0.00%] | 0.96% [0.00%, 10.00%] | 12 / 12 |
| 5% | 0 to 0.1 | 0.00% [0.00%, 0.00%] | 3.36% [0.00%, 11.11%] | 31 / 31 |
| 5% | 0.1 to 0.3 | 0.00% [0.00%, 0.00%] | 0.11% [0.00%, 3.34%] | 27 / 27 |
| 5% | 0.3 to 0.5 | 0.00% [0.00%, 0.00%] | 0.16% [0.00%, 2.63%] | 41 / 41 |
| 5% | 0.5 to 0.75 | no points | no matched points | 0 / 0 |
| 5% | 0.75 to 1 | 0.00% [0.00%, 0.00%] | 4.58% [0.00%, 20.00%] | 12 / 12 |
| 10% | 0 to 0.1 | 3.23% [0.00%, 11.11%] | 6.79% [0.00%, 17.07%] | 31 / 31 |
| 10% | 0.1 to 0.3 | 0.00% [0.00%, 0.00%] | 0.38% [0.00%, 4.17%] | 27 / 27 |
| 10% | 0.3 to 0.5 | 0.00% [0.00%, 0.00%] | 0.46% [0.00%, 3.33%] | 41 / 41 |
| 10% | 0.5 to 0.75 | no points | no matched points | 0 / 0 |
| 10% | 0.75 to 1 | 0.00% [0.00%, 0.00%] | 9.29% [0.00%, 29.43%] | 12 / 12 |
| 20% | 0 to 0.1 | 9.68% [0.00%, 24.00%] | 13.71% [3.45%, 26.32%] | 31 / 31 |
| 20% | 0.1 to 0.3 | 0.00% [0.00%, 0.00%] | 0.85% [0.00%, 6.25%] | 27 / 27 |
| 20% | 0.3 to 0.5 | 0.00% [0.00%, 0.00%] | 1.29% [0.00%, 5.72%] | 41 / 41 |
| 20% | 0.5 to 0.75 | no points | no matched points | 0 / 0 |
| 20% | 0.75 to 1 | 0.00% [0.00%, 0.00%] | 20.05% [0.00%, 46.67%] | 12 / 12 |

### Physical-only complement point checks

These are the 12 points with a physical-only score outside radar observability; the score is an ordinal physical screen, not a fitted probability.

| Top share of physical-score cells | Point hit share [95% CI] | Matched chance [95% CI] | n |
|---:|---:|---:|---:|
| 1% | 0.00% [0.00%, 0.00%] | 1.03% [0.00%, 9.09%] | 12 |
| 5% | 0.00% [0.00%, 0.00%] | 4.73% [0.00%, 20.00%] | 12 |
| 10% | 0.00% [0.00%, 0.00%] | 9.21% [0.00%, 27.27%] | 12 |
| 20% | 0.00% [0.00%, 0.00%] | 20.05% [0.00%, 45.45%] | 12 |

## Conformal coverage by built-up stratum

| Built-up fraction | Held-out cells | Empirical coverage | Mean band width |
|---|---:|---:|---:|
| 0 to 0.1 | 386,155 | 92.7% | 0.2780 |
| 0.1 to 0.3 | 49,390 | 96.3% | 0.1239 |
| 0.3 to 0.5 | 45,699 | 96.1% | 0.1134 |
| 0.5 to 0.75 | 0 | no held-out cells | — |
| 0.75 to 1 | 0 | no held-out cells | — |

Physical-only outside-mask point hit rates are reported separately and are not mixed with radar probability scores.

The Phase 9C vs 9B figures use different evaluation domains: 9C is restricted to 481,244 observable eligible cells, while 9B covered 1,078,595 cells after population-NoData filtering. Their raw metric difference is therefore not a pure model-only comparison.

## Spatial Mondrian uncertainty

Nominal 90% Mondrian conformal interval empirical outer-fold coverage is 93.4%; mean width is 0.2464 probability units. Below 88%: **False**. Per-built-up-stratum held-out coverage and width appear in the JSON. The nominal level is not a guarantee under spatial dependence.

## Physical complement

`physical_susceptibility_outside_radar.tif` is labelled **PHYSICAL, NOT FITTED TO LABELS**. It averages equal-weight within-support percentiles of HAND, local depression depth, TWI and distance to an exact named waterway, oriented toward lower HAND, higher depression/TWI and shorter drainage distance. It is an ordinal screen, not a calibrated probability. It has support on 14,440 of 597,351 cells outside the radar mask (2.42%); the remaining outside-mask cells remain NoData. Point-hit rates are below and in the metrics JSON.

## Limits and leakage

The OpenCity points were not predictors, labels, tuning data, or threshold-selection data. The model did use the same 2015 label event as Phase 9B; its point cross-check is separate-source but not necessarily independent event/date validation. Full-data maps are apparent. The observability mask censors dense built-up cells (>0.50), steep slopes (>15°), and quality-mask invalid cells. There are no accepted independent event/date labels, and no claim about December 2015 peak flooding, future forecast skill, causal physical effects, or field accuracy is supported.
