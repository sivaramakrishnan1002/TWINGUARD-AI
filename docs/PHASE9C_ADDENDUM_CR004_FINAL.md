# Phase 9C addendum CR-004 — final results

## What changed

WorldPop NoData no longer limits hazard eligibility. The unchanged Phase 9 eligible set has **1,196,300 cells**, including **117,705** WorldPop-NoData cells; the previous population mask removed **25,551 flooded-label cells**. Those cells remain in the hazard audit. Population stays an impact/exposure layer and is excluded from hazard predictors.

The WorldPop raster has NoData value -99999. Its metadata does not say why each affected cell is missing. Of the 25,551 dropped positive cells, dominant land-cover values were crop 13,482, tree 5,870, grass 5,776, bare 399, built-up 24, water 0. For 25,511, built-up fraction was below 0.10. Distance-to-water was missing for 9,967; among the rest, 15,241 were within 1 km. Distance-to-coast was missing for 9,967; 11,982 were over 5 km away and 9 were within 1 km. They span 120 3 km block IDs. These are spatial descriptions, not evidence of the cause of NoData or settlement status; all block-level counts are in the metrics JSON.

## Observability and comparable evaluation

Radar-visible eligibility requires the unchanged Phase 9 label eligibility, valid reference and event RTC observations, no layover/shadow flag, built-up fraction at most 0.50, and valid slope at most 15 degrees. Population NoData is not a condition. This leaves **574,018** assessed cells, **38,194** positive, prevalence **0.06654**. The earlier Phase 9C run had 481,244 cells and prevalence 0.04979 because it applied the erroneous population mask; those metrics are not an apples-to-apples comparison. The 9B model also used a different population-masked domain and included exposure proxies.

## Hazard feature-set results

Default random forest; same five buffered 3 km spatial folds; all positives and a 3:1 stratified non-flooded training sample; thresholds, imputation, scaling and calibration were learned within training data. No hyperparameter search was run. WorldPop, distance to road nodes and building density were excluded. The third set includes built-up fraction as requested.

| Set | Prevalence | pooled PR-AUC | lift | outer-fold ROC-AUC mean (SD) | PR-AUC mean (SD) | F1 mean (SD) | IoU mean (SD) | Brier mean (SD) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Terrain and hydrology | 0.06654 | 0.21417 | 3.219 | 0.7813 (0.0216) | 0.2169 (0.0467) | 0.1787 (0.0793) | 0.0999 (0.0498) | 0.05805 (0.01522) |
| Plus tree/crop/grass/bare, no built-up | 0.06654 | 0.21100 | 3.171 | 0.7932 (0.0228) | 0.2171 (0.0551) | 0.1853 (0.0954) | 0.1047 (0.0611) | 0.05791 (0.01489) |
| Plus built-up fraction | 0.06654 | 0.21901 | 3.291 | 0.8009 (0.0204) | 0.2284 (0.0511) | 0.1892 (0.0980) | 0.1072 (0.0629) | 0.05773 (0.01492) |

For the third set, the fold-mean PR-AUC 95% t interval across five folds is **0.1650–0.2918**; the fold standard deviation is 0.0511. Fold PR-AUCs, calibration bins/ECE, and the complete metrics are in the JSON.

The third set's pooled PR-AUC (0.21901) exceeded the same-fold pooled elevation-only (0.06897), named-waterway-distance-only (0.07376), and random-prevalence baseline (0.06278). These comparisons are descriptive; the full fold results are in the JSON. Adding non-built land cover barely changed PR-AUC from terrain/hydrology alone; adding built-up raised pooled PR-AUC by about 0.008. This is a modest increase and may reflect radar observability/label bias.

Dense-urban exclusion adds no cells because the observability definition already excludes built-up >0.50. Its evaluation population is therefore the same 574,018 cells, with the same prevalence and lift. No separate skill from urban exposure proxies can be inferred; those predictors were removed.

For the built-up strata 0–0.1, 0.1–0.3 and 0.3–0.5, conformal outer-fold mean coverage was **91.92%, 91.60%, and 91.56%**, with mean band widths **0.591, 0.285, and 0.260**. Each exceeds the requested 88% floor in these observed strata. There are no observable cells above 0.50 by construction, so no coverage claim is made for those strata. Bands are spatially buffered, training-only, Mondrian residual bands; coverage on a single event does not guarantee future coverage.

## Independent OpenCity point check

The points are approximately located and their dates are unclear. Of 945 source points, **99** fell in the radar-visible score domain, **843** were in the physical-only area, and **3** had no score. On radar-visible points, top-risk hits versus land-cover/built-up-matched chance were:

| Top share | Observed hit share (95% block-bootstrap CI) | Matched chance share (95% CI) |
|---:|---:|---:|
| 1% | 0.00% (0–0%) | 0.16% (0–1.16%) |
| 5% | 0.00% (0–0%) | 1.06% (0–3.23%) |
| 10% | 1.01% (0–3.57%) | 2.21% (0–5.80%) |
| 20% | 4.04% (0.90–9.04%) | 4.53% (0.96–9.34%) |

The point ranking did not outperform matched chance. Per built-up stratum and physical-only hit rates are in the JSON. Because event dates are unknown, this is independent spatial checking, not date-specific flood validation.

## Phase 10 display

The data-driven apparent hazard is shown **only inside the radar observability mask**. Outside it, the map shows a separate PHYSICAL susceptibility score plus unreliable_from_labels=1; inside the mask the flag is 0. The composite bands do not merge physical score and probability. The full-CMA physical layer uses available terrain/hydrology rank inputs and is not fitted to flood labels. Output: data/features/predictions/phase10_cr004_v9/radar_visible_plus_physical_composite.tif.

## Limits

This estimates one November 2015 SAR-derived label and describes radar-visible flooding. It is not a forecast, not field truth, and cannot establish performance for 2015 December, 2021 or 2023. Built-up fraction may still encode where radar labels are observable. OpenCity locations/dates, sparse high built-up strata, uncertain NoData causes, and the single-event label remain key risks. Out-of-event validation remains pending independently digitised maps.

## Reproducibility

Script: pipelines/phase9c/addendum_cr004.py; seed 20261025; default RF; no tuning. Outputs are labeled apparent/single-event. Model registry, detailed cell diagnostics, per-fold values, point bootstrap by stratum and source hashes are in PHASE9C_ADDENDUM_CR004_V6.json and PHASE9C_ADDENDUM_CR004_V6_MODEL_REGISTRY.json.
### Comparison with the earlier runs
The earlier Phase 9C report showed pooled PR-AUC 0.1605, ROC-AUC 0.7538 and prevalence 0.04979 on 481,244 cells. This corrected run has pooled PR-AUC 0.2190, fold ROC-AUC mean 0.8009 and prevalence 0.06654 on 574,018 cells. The prior run incorrectly excluded WorldPop-NoData cells and used a different predictor set, so the apparent gain cannot be attributed to this addendum alone. Phase 9B's selected tuned average ensemble had mean fold PR-AUC 0.2599 (SD 0.0702) on a different population-masked domain and used a tuned model; it is not a fair direct comparison. The default average ensemble is retained as an option but was not rerun here.
