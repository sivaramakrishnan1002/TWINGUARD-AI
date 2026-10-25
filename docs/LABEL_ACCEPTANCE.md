# Flood Rule v2 acceptance preregistration

**Recorded before event-reference evaluation:** 2026-10-25 09:42:35.367 Asia/Kolkata (UTC+05:30).

The fixed T3 Flood Rule v2 parameters are frozen in `T2_PHYSICS_THRESHOLDS.json` and `FLOOD_RULE_V2.md`. No parameter will be changed using the 24 November 2015 UNOSAT event layer. The assessment compares the versioned 24 Nov candidate to the official UNOSAT `S1_20151124_Flood` reference in `labels.v_usable_flood_labels`.

## Tier rule

- **Tier B:** IoU ≥0.40 **and** predicted flood area is within ±50% of the known 98.16 km² UNOSAT source area (49.08–147.24 km² inclusive).
- **Tier C:** 0.25 ≤ IoU <0.40, regardless of the area gate.
- **Tier D:** all other results, including IoU ≥0.40 when the area gate fails.

The ordering removes ambiguity at IoU 0.40: Tier B must satisfy both gates; a candidate at or above 0.40 that misses the area range is Tier D. No manual tier override is permitted. Area from the rasterized 30 m reference will also be reported separately from the supplied source area.

## Evaluation plan frozen before scoring

Use pixel-centre rasterization of the accepted official event geometry onto the same EPSG:32644 30 m grid. The primary confusion matrix and IoU use common-valid SAR cells inside the CMA; cells excluded by the rule's terrain, water, urban or minimum-component masks count as unpredicted for the full-observable-area score, while SAR invalid/layover/shadow cells are excluded and reported. Also report metrics conditional on rule-eligible cells to make the denominator difference visible. No threshold, mask, or morphology change follows this comparison.

Report predicted and reference area; precision, recall, F1, IoU and TP/FP/FN/TN; ablations that remove one mask at a time; error totals by WorldCover class and 3 km spatial block. The 3 km analysis is a descriptive error-concentration check, not independent cross-validation. Any same-scene derivation of UNOSAT weakens independence. Binary rule outputs do not supply calibrated probabilities, so ROC-AUC, PR-AUC, Brier score, ECE, calibration, and uncertainty coverage are not applicable to this label-acceptance test; those gates remain mandatory for learned probabilistic models.
