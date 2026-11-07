# G2 Gate Review — risk map, fair baselines and out-of-event evaluation — 2026-11-07

**Current gate decision: PASS_WITH_CAVEATS**

Reviewer: Integrator (Lane I) session. Scope per `docs/master/GATES.md`: "Risk map, fair baselines and out-of-event evaluation". Required tasks: A03 (Phase 10 risk map, re-scoped by CR-003 to "without out-of-event validation") and A04 (Phase 9B model upgrade). Both are `done_with_caveats`. Supporting completed tasks reviewed: A03d (2023 out-of-event check), A04b (Phase 9C plus the CR-004 addendum) and A04c (physical layer).

`PASS_WITH_CAVEATS` means every criterion is met for its bounded purpose. **It does not mean the susceptibility model or the risk map is validated out of event.** G2 asks for an out-of-event *evaluation*. That evaluation exists and is reported honestly, but only as a descriptive cross-check against an unaccepted preliminary map. Out-of-event *validation* against an accepted reference remains unavailable. This is a binding caveat for G6 and the report. On that basis `STATE.json` records G2 as `ready`.

## Owner-accepted protocol deviation

Lanes did not stop for this gate. Lane A's **A23** (lock held) and the UI redesign kept running with the project owner's approval, because G2 reviews completed tasks. Their paths were not edited and their locks were not touched. No G2 evidence depends on A23 outputs.

## Criterion review

| # | Criterion | Decision | Evidence | Binding caveats |
|---|---|---|---|---|
| G2.1 | Risk map with stated cut-points, uncertainty, zonal summaries, PNG/GeoTIFF/tiles | PASS_WITH_CAVEATS | `docs/PHASE10_RISK_MAP_CR004.md`; `data/features/predictions/phase10_cr004_v9/`; `docs/PHASE10_RISK_MAP_CR003_V3.md`/`.json`; `docs/figures/phase10_risk_map_cr003_v3.png`; `data/processed/tiles/phase10_cr003_v3/`; `docs/PHASE9C_ADDENDUM_CR004_FINAL_LINEAGE.md` | **Apparent, single-event, non-operational map.** Risk classes 1–4 use display cut-points 0.10/0.25/0.50 and appear only inside the radar-observability mask. Outside it, the map shows a PHYSICAL percentile-rank score (not a probability) with the `unreliable_from_labels` flag. The MVT tiles (45 non-empty, z8–12) come from the CR-003 v3 composite. Road length uses approximate midpoint allocation. No ward boundaries exist, so summaries use 3 km blocks. WorldPop NoData is kept as NoData. |
| G2.2 | Fair baselines under spatial blocking with true prevalence | PASS_WITH_CAVEATS | `docs/PHASE9B_MODEL_UPGRADE_V2.md`; `docs/PHASE9B_V2_METRICS.json`; `docs/PHASE9B_V2_MODEL_REGISTRY.json`; `docs/PHASE9C_ADDENDUM_CR004_FINAL.md`; `docs/PHASE9C_ADDENDUM_CR004_V6.json`; `docs/MODEL_CARD_SUSCEPTIBILITY_CR004.md` | 5-fold GroupKFold on 3 km blocks with a one-block buffer, evaluated at true prevalence. Eight Platt-calibrated baselines were used: elevation, river distance, TWI, slope, relative elevation, HAND, terrain logistic and random prevalence. Phase 9B: the chosen ensemble beats every baseline on PR-AUC in 5/5 folds (e.g. +0.183 ± 0.054 over terrain logistic). Phase 9C/CR-004: the exposure-free model has pooled PR-AUC 0.219, against 0.069 for elevation, 0.074 for waterway distance and 0.063 for random. PR-AUC/ROC-AUC/F1/IoU/Brier/ECE are reported with fixed seeds and registry entries. **Single November 2015 SAR-derived event.** Built-up gains may reflect radar-observability label bias. The Phase 9B conformal band under-covers (85.8% against 90% nominal). The Phase 9C spatial Mondrian bands reach 91.6–91.9% only in the observable built-up ≤0.5 strata. The Phase 9 `test_block_ids` bookkeeping defect is documented, and 9B rebuilt the splits independently. |
| G2.3 | Out-of-event evaluation | PASS_WITH_CAVEATS (evaluation only; validation unavailable) | `docs/PHASE9C_OUT_OF_EVENT_2023.md`; `data/features/labels/map_batch2/nrsc_2023_dec07_diagnostic.json`; `docs/GEO_PDF_LABELS_BATCH2.md`; A03d in `STATE.json`; `docs/PHASE9B_MODEL_UPGRADE_V2.md` (no accepted out-of-event label) | The Nov 2015-trained Phase 9C model was scored against the Dec 2023 NRSC GeoPDF red class on 574,018 radar-observable cells (prevalence 0.0438): **PR-AUC 0.121 (lift 2.76), ROC-AUC 0.778**. The A04c physical score over the full covered CMA gave PR-AUC 0.028 (lift 1.09) and ROC-AUC 0.575. **The reference is `PRELIMINARY_NOT_ACCEPTED`.** The map says it has no ground verification, and its flood class may include standing paddy or rain water. No control-point RMS was measurable, so it was not loaded as a tier B/C label. F1 at a training threshold, Brier and calibration were not computed for this cross-check. The 2021 NRSC map has an unresolved CRS conflict (manual-needed), and the December 2015 maps are absent. `labels.v_usable_flood_labels` has no accepted label for any other event or date. The OpenCity point check (undated, approximate) did **not** beat matched chance. |
| G2.4 | Honest labelling of limits on outputs | PASS | `docs/PHASE10_RISK_MAP_CR004.md`; `docs/MODEL_CARD_SUSCEPTIBILITY_CR004.md`; A03/A04 notes in `STATE.json` | The outputs say "apparent", "single event", "not field truth" and "out-of-event validation pending digitised maps". Prior output versions are kept and marked superseded. |

## Required gate checks (run 2026-11-07, this session)

| Check | Command | Result |
|---|---|---|
| Gate prerequisites | `.venv\Scripts\python.exe tools\master\gate_check.py G2` | exit 0: "G2 READY for integrator gate checklist; all listed task prerequisites are complete" |
| State integrity | `.venv\Scripts\python.exe tools\master\verify_state.py` | exit 0, no evidence drift |
| Focused G2 suites | `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib -p no:cacheprovider tests/phase9 tests/phase9b tests/phase9c tests/phase10` | **42 passed** |
| Full Python suite | `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib -p no:cacheprovider` | **369 passed, 1 skipped** (env-gated); backend Maven 30 tests passed. See `GATE_G4_REPORT.md` § Shared checks. |
| Raw audit | `.venv\Scripts\python.exe tools\audit_raw_logs.py` | 157 files, 30,544,672,450 bytes; 157 hash matches; 0 non-comparable; 0 mismatches |
| Migration numbering / requirements | as in `GATE_G1_REPORT.md` | unique 001–014, 100, 101; no requirement change since G0 |
| End-to-end | not applicable | static model and map products |
| Backup | not required | No DB write, migration or Docker operation. No dump made; no volume touched. |

## Decision and carried caveats

G2 passes with caveats. Scoring against an accepted reference for another event is **not available**. The only out-of-event evidence is the descriptive 2023 cross-check, which shows moderate ranking skill against a preliminary, unverified map. No report, UI or API may describe the susceptibility model or the Phase 10 map as validated out of event, operational, or field-verified.

The path to real out-of-event validation is the existing owner task **M6** (optional PDF georeferencing, `parked`). It would georeference the 2021/2023 PDFs and supply control-point residuals so the existing `pipelines/labels/manual_map_loader.py` can load tier B/C labels. M6 is an owner choice, not a G2 repair, so no new repair task is registered. A15 (validation synthesis) and A17 (paper) must carry this limitation into G6.

No lane-owned file, database, Docker volume, tag or push was changed or created.
