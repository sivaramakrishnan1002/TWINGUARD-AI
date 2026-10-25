# Batch 1 progress board

| Task | Status | Commit hash | Notes |
|---|---|---|---|
| T1 Label hygiene | done | ea3bc1c | Migration 014 retains all 45,096 rows as tier D / REJECTED_PENDING_REWORK; usable-label view exposes official in-CMA references only. Full pytest 39 passed; raw audit 157/157 hashes matched. |
| T2 Physics-based thresholds | done | pending | 19,998 strict stable-water cells; VV/VH pooled medians -19.13/-25.89 dB; midpoint screens -12.93/-19.96 dB; stable-dry mean−2SD change -3.00/-1.80 dB. Full pytest 41 passed; raw audit 157/157 hashes matched. |
| T3 Flood rule v2 | todo | — | Fixed threshold and mask rule; no UNOSAT tuning. |
| T4 Pre-registered acceptance | todo | — | Register gates before calculating evaluation metrics. |
| T5 Apply fixed rule | todo | — | 6 Dec 2015 and 16 Nov 2021 candidate layers, validation and DB update. |
| T6 Depth fields and contract | todo | — | Extent-derived water surface and uncertainty products; DERIVED. |
| T7 Phase 10 risk map | todo | — | Calibrated classes, zonal summaries and held-out-date evaluation. |
| T8 Review and close | todo | — | Leakage/physical review, docs, tests, audit and final commit. |
