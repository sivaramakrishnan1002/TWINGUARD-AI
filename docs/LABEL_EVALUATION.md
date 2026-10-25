# Flood Rule v2 acceptance evaluation

**Result: tier D; rejected for label use.** This is a fixed binary screening rule compared with an official UNOSAT map. It is not a trained model, a probability forecast, or field validation.

## Preregistered comparison

The acceptance thresholds were recorded in `LABEL_ACCEPTANCE.md` at 2026-10-25 09:42:35.367 IST, before the event-reference comparison. Tier B requires IoU ≥0.40 and predicted area 49.08–147.24 km²; tier C requires IoU 0.25–<0.40; all other results are tier D. The reference is the tier A UNOSAT 24 Nov 2015 layer from `labels.v_usable_flood_labels`, rasterized at pixel centres on the EPSG:32644 30 m grid.

The reference vector dissolves to 98.314 km² inside the CMA, consistent with the known source value 98.16 km² (difference 0.16%). The pixel-centre raster occupies 98.1603 km² inside the CMA and 98.1576 km² on the 1,319,255-cell numeric SAR comparison domain. The rule's comparison domain is the full numeric-SAR area, 1,187.3295 km². The 125 CMA cells without valid numeric SAR were excluded. Rule-excluded pixels on the valid comparison domain count as unpredicted.

## Primary full-domain results

| Measure | Result |
|---|---:|
| TP / FP / FN / TN | 146 / 96 / 108,918 / 1,210,095 |
| Precision | 0.6033 |
| Recall | 0.001339 |
| F1 | 0.002671 |
| IoU | 0.001337 |
| Predicted area | 0.2178 km² (242 cells) |
| Reference area in comparison domain | 98.1576 km² |
| Preregistered tier | **D** |

The eligible-only diagnostic is IoU 0.5328, recall 0.8202, and F1 0.6952, but the eligibility masks leave only 13,533 cells (1.03% of CMA) and 0.1602 km² of reference flood in the denominator. It is not the preregistered full-domain acceptance result and cannot justify tier B.

## Mask ablation

Each row removes only the named exclusion while keeping the thresholds fixed; the full numeric-CMA denominator is retained.

| Removed mask | Predicted area (km²) | IoU | Recall |
|---|---:|---:|---:|
| Common valid / layover-shadow | 0.2178 | 0.001337 | 0.001339 |
| Permanent water | 0.2466 | 0.001475 | 0.001476 |
| Slope ≤5° | 0.2637 | 0.001676 | 0.001678 |
| HAND ≤5 m | 34.9074 | 0.165807 | 0.192804 |
| Built-up fraction ≤0.5 | 0.2205 | 0.001337 | 0.001339 |
| Five-cell minimum component | 0.2412 | 0.001447 | 0.001449 |

The HAND mask dominates candidate area and recall. Removing it still does not meet either acceptance tier. The individual reference-flood exclusions overlap and must not be summed: permanent-water exclusion intersects 63,899 reference cells, slope 81,244, HAND 108,825, and dense-urban exclusion 595. The masks exclude 108,886 unique reference pixels in total. WorldCover 2021 water alone accounts for 54,082 false negatives; WorldCover is later than the 2015 event and this is a known temporal limitation.

## Error concentration and implementation review

There are 154 3 km blocks containing reference flood. The five largest false-negative blocks contain 24.99% of all false negatives; the largest contains 7,447. These are descriptive concentrations, not cross-validation folds. Recall is very low across every listed WorldCover class, including cropland, vegetation and built-up cells.

The first candidate implementation accidentally accepted a finite slope NoData sentinel (−9999). It was superseded by run `20261025_03`, which excludes the raster's NoData value explicitly. Reproduction of the corrected run had zero mismatches across grid, valid-data, permanent-water, slope, HAND, urban and sieve checks. Earlier evaluation files also reported an unclipped dissolved reference area; the corrected evaluation intersects the dissolved reference with the CMA before measuring area. Earlier output JSON files are retained as superseded pointers below.

The UNOSAT 24 Nov product may use the same Sentinel-1 acquisition. This tests agreement between our pipeline and the reference map, not independent flood physics. No baselines, spatial CV, learned threshold, calibration or uncertainty interval apply to this deterministic label acceptance check. Therefore PR-AUC, ROC-AUC, Brier score, ECE, calibration curves and uncertainty-band coverage are **not applicable**, not passed. Model quality gates remain mandatory for any later model.

Reproduce the evaluation with `.venv/Scripts/python.exe -m pipelines.phase8.evaluate_rule_v2 --run-id 20261025_03`. The machine-readable result is `T4_RULE_V2_EVALUATION_20261025_03_fixed.json`; the frozen method and candidate are documented in `FLOOD_RULE_V2.md`. Candidate label is DERIVED, tier D, and remains excluded from `labels.v_usable_flood_labels`.
