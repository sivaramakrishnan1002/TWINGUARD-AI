# Batch 1 progress board

| Task | Status | Commit hash | Notes |
|---|---|---|---|
| T1 Label hygiene | done | ea3bc1c | Migration 014 retains all 45,096 rows as tier D / REJECTED_PENDING_REWORK; usable-label view exposes official in-CMA references only. Full pytest 39 passed; raw audit 157/157 hashes matched. |
| T2 Physics-based thresholds | done | 54ebad0 | 19,998 strict stable-water cells; VV/VH pooled medians -19.13/-25.89 dB; midpoint screens -12.93/-19.96 dB; stable-dry mean−2SD change -3.00/-1.80 dB. Baselines rasterized from T1 view; checks 41 passed and raw audit 157/157. |
| T3 Flood rule v2 | done (corrected) | 70a12cb | Fixed thresholds/masks; corrected run `20261025_03` candidate is 0.2178 km² (242 cells), with finite slope NoData excluded; HAND valid in 1.91% of CMA. T4 evaluates it as tier D. Full pytest 49 passed; raw audit 157/157 hashes matched. |
| T4 Pre-registered acceptance | done | 6fb70fe | Preregistered before scoring. Corrected run `20261025_03` is tier D on the full observable CMA (IoU 0.001337; predicted area 0.2178 km²); conditional-eligible IoU 0.5328 is not the acceptance score. No probability-model gates apply to this binary rule. |
| T5 Apply fixed rule | done | pending commit | Fixed rule applied with no retuning: 6 Dec 2015 = 0.2322 km², 16 Nov 2021 = 0.0918 km²; both tier D. GFD coarse IoU 0.00179 (dates differ); OpenCity spatial point overlap 0/944 (dates unspecified). HAND valid in 1.91% CMA; flooded median elevation ~25 m flags a plausibility concern. Existing database records remain D/rejected; no accepted new labels to load. |
| T6 Depth fields and contract | todo | — | Extent-derived water surface and uncertainty products; DERIVED. |
| T7 Phase 10 risk map | todo | — | Calibrated classes, zonal summaries and held-out-date evaluation. |
| T8 Review and close | todo | — | Leakage/physical review, docs, tests, audit and final commit. |
