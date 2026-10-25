# Batch 1 closeout report

**Updated:** 25 October 2026. Data under `data/raw` was treated as read-only. No network, download, or package installation was used. “Done” below means the requested artifact/check exists; it does not imply scientific or field validation.

| Task | Result | Files | Key numbers | Defaults chosen | Blocked |
|---|---|---|---|---|---|
| T1 label hygiene | Done. Stage 8 candidates remain tier D / `REJECTED_PENDING_REWORK`; usable-label view limits analyses to accepted A/B/C references. | `LABEL_DATASET.md`, database migration 014, `DATABASE_SCHEMA.md` | 45,096 existing candidate rows retained; not deleted. | None added in this batch. | No. |
| T2 physical thresholds | Done as a preregistered, label-independent screen. | `PHYSICS_THRESHOLDS.md`, `T2_PHYSICS_THRESHOLDS.json`, `DECISIONS_PENDING.md` | 19,998 stable-water samples; VV/VH midpoint thresholds −12.93/−19.96 dB; change bounds −3.00/−1.80 dB. | B1-D1 midpoint of sample medians; B1-D2 k=2 SD. | Thresholds are not locally field-validated. |
| T3 fixed SAR rule | Done and corrected for NoData and CMA clipping. | `T3_FLOOD_RULE_V2.md`, `T3_FLOOD_RULE_V2.json`, `LABEL_DATASET.md` | 24 Nov candidate 242 cells / 0.2178 km²; HAND valid in 1.91% of CMA. | B1-D3 D8 accumulation ≥100 cells, slope ≤5°, HAND ≤5 m; B1-D4 built-up ≤0.5 and 8-connected MMU ≥5 cells. | Candidate is a screening result only. |
| T4 preregistered acceptance | Done; candidate is tier D on the full observable CMA. | `LABEL_ACCEPTANCE.md`, `LABEL_EVALUATION.md`, `T4_RULE_V2_EVALUATION_20261025_03_fixed.json` | IoU 0.001337; precision 0.6033; recall 0.001339; F1 0.002671; 0.2178 km² predicted vs 98.1576 km² raster reference. Eligible-only IoU 0.5328 covers only 13,533 cells and is not the acceptance score. | Tier B requires IoU ≥0.40 and area within ±50% of 98 km²; C is 0.25–<0.40; otherwise D. | UNOSAT may use the same Sentinel acquisition, so this is not independent physics validation. |
| T5 fixed-rule application | Done without retuning; both new candidates remain tier D and were not added to the database. | `T5_FIXED_RULE_APPLICATION.md`, `T5_APPLY_METRICS_v2.json`, `label_registry.json` (local ignored artifact) | 6 Dec 2015: 0.2322 km²; 16 Nov 2021: 0.0918 km². GFD native-grid cross-check IoU 0.00179 and event ends 4 Dec. OpenCity spatial overlap 0/944 in-CMA points; dates are unclear. | Same frozen B1-D1–D4 rule. | No date-matched numeric official reference for either application. No 2023 label because available SAR scenes predate the peak. |
| T6 depth fields | Done for accepted tier-A 12 and 24 Nov 2015 extents; outputs are DERIVED depth proxies. | `DEPTH_FIELD_CONTRACT.md`, `T6_DEPTH_OUTPUTS.json`, six TIFFs under `data/features/depth/batch1_v1/` | Valid DEM depth: 30,235/94,195 cells (32.10%) on 12 Nov; 32,627/109,067 (29.91%) on 24 Nov. Maximum estimated mean depth 22.817 m and 6.376 m. | B1-D5 component-edge median surface; deterministic ±4 m p05/p95 allowance, lower bound clamped to zero. | No measured event depths to calibrate or test interval coverage; DSM artifacts make urban depths unreliable. |
| T7 Phase 10 risk map | **Blocked: prerequisite.** No out-of-event accepted A/B/C label is available. No risk map or zonal summaries were generated. | `PHASE10_RISK_MAP.md`, `DATABASE_SCHEMA.md` | Accepted event dates are 12 and 24 Nov 2015 only, both within one event. Phase 9 trained on their union. | No additional cut-points or calibration defaults selected because the independent holdout is absent. | 2021 and 2023 references remain PDFs; no accepted independent event/date exists. |
| T8 leakage and sanity review | Done. Updated assumptions, generated lineage, project status and schema documentation; recorded current board status. | `BATCH_1_LEAKAGE_REVIEW.md`, `ASSUMPTIONS.md`, `DATA_LINEAGE.md`, `PROJECT_STATUS.md`, `DATABASE_SCHEMA.md`, `PROGRESS_BOARD.md` | Phase 9 RF spatial-CV: PR-AUC .3415, ROC-AUC .8911, F1 .3499, IoU .2143, Brier .0398, ECE .0093; PR-AUC baselines elevation .0515, river distance .0465, random .0512. Full suite 53 passed/0 failed before final docs-only closeout; raw hashes 157/157 matched. | Phase 9 F1 threshold was selected from in-sample training predictions; bootstrap is 20 full-data resampled fits. | These results do not demonstrate event transfer or held-out uncertainty coverage. |

## Recorded Batch 1 defaults

- **B1-D1:** water/dry threshold is the midpoint of sample medians, by polarization.
- **B1-D2:** stable-dry change threshold is mean minus 2 standard deviations.
- **B1-D3:** D8 contributing-area threshold 100 cells; HAND ≤5 m; slope ≤5°.
- **B1-D4:** exclude built-up fraction >0.5; retain 8-connected components of at least five cells.
- **B1-D5:** component-boundary median DEM elevation for a flat local water surface; deterministic ±4 m bounds. These are defaults to confirm, not validated physical constants.

## Top risks

1. No independent accepted flood event/date exists for Phase 10 evaluation. Do not claim event-transfer performance or calibrated probabilities.
2. The fixed SAR candidate covers only 0.2178 km² against a 98.1576 km² observable 24 Nov reference; its full-domain acceptance score is tier D. HAND/terrain masks leave only 1.03% of CMA cells eligible.
3. Depth estimates are incomplete and weakly constrained: about 30–32% of the event extents have valid DEM values, the DEM is a surface model, the 12 Nov maximum is 22.817 m, and the ±4 m interval has no empirical coverage check.

The full leakage, physical-sanity, and provenance details are in `BATCH_1_LEAKAGE_REVIEW.md`. The tests exercise software contracts; they do not validate flood physics or field accuracy.
