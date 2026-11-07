# G1 Gate Review — label acceptance and depth contract — 2026-11-07

**Current gate decision: PASS_WITH_CAVEATS**

Reviewer: Integrator (Lane I) session. Scope per `docs/master/GATES.md`: "Label acceptance and depth contract". Required tasks: A01 (Label rework T1–T5) and A02 (Depth fields T6). Both are `done_with_caveats` in `docs/master/STATE.json`. This review checks completed work only; it does not create new science.

`PASS_WITH_CAVEATS` means every criterion is met for its stated, bounded purpose and the caveats below are binding on every downstream use. It is not a claim of field validation, observed depth, or operational readiness. On that basis `STATE.json` records G1 as `ready` (the status the protocol uses for a passed gate, as for G0).

## Owner-accepted protocol deviation

`GATES.md` says both lanes stop at a gate. The project owner chose to keep Lane A task **A23** (spatial Open-Meteo forcing, running and holding `HEAVY.lock`) and the Lane B/UI product redesign running during the G1–G4 reviews, because those gates assess tasks already completed. This review records that as an **owner-accepted deviation**. A23 and the UI session's files (`pipelines/phase12_openmeteo_grid/`, `tests/phase12_openmeteo_grid/`, `frontend/src/ui/product/*`, `frontend/src/ui/evidence/`, `tools/ui/`, `.gitignore`) were not edited, and A23's lock was not touched. No G1 evidence depends on those paths.

## Criterion review

| # | Criterion | Decision | Evidence | Binding caveats |
|---|---|---|---|---|
| G1.1 | Label hygiene: rejected Stage 8 candidates kept but excluded; single usable-label view | PASS | `docs/PROGRESS_BOARD.md` (T1, commit ea3bc1c); migration `database/migrations/014_stage8_label_hygiene.sql`; contract `docs/master/contracts/c2_labels_v0.md` (frozen v0) | All 45,096 Stage 8 rows are kept as tier D / `REJECTED_PENDING_REWORK`. Consumers must read only `labels.v_usable_flood_labels`. |
| G1.2 | Physics-based thresholds and fixed Flood Rule v2 | PASS_WITH_CAVEATS | `docs/FLOOD_RULE_V2.md`; board T2 (54ebad0) and T3 (70a12cb) | Thresholds came from pre-flood stable water and dry land, with no tuning on UNOSAT. HAND is valid in only 1.91% of the CMA, so the terrain mask removes most cells. T3 had a metadata defect, corrected in run `20261025_03`. |
| G1.3 | Pre-registered acceptance rule recorded before scoring and applied without override | PASS | `docs/LABEL_ACCEPTANCE.md` (recorded 2026-10-25 09:42:35 IST, before evaluation); board T4 (6fb70fe) | Tier rule fixed in advance (Tier B: IoU ≥0.40 and area within ±50%; Tier C: 0.25–0.40; otherwise D). No manual override. |
| G1.4 | Acceptance outcome reported honestly; only accepted tiers enter the usable view | PASS_WITH_CAVEATS | Board T4/T5 (a76c748); A01 notes in `STATE.json` | **The SAR rule failed acceptance.** On the full observable CMA, 24 Nov 2015 has IoU 0.001337 and 0.2178 km² predicted area, so it is tier D. 6 Dec 2015 and 16 Nov 2021 are also tier D. No derived label was accepted or loaded. The usable view holds only the official UNOSAT November 2015 references: per A19, 10,419 records, of which 8,414 are `event_flood` and 2,005 are `baseline_water`. The conditional-eligible IoU of 0.5328 is not the acceptance score. UNOSAT may come from the same scene, which weakens independence. Labels are SAR-derived extents, not field ground truth. |
| G1.5 | Accepted-label serialization (C2) | PASS_WITH_CAVEATS | A19: `docs/LABEL_GEOJSON_EXPORT.md`, `pipelines/labels/export_usable_labels_geojson.py`, `tests/labels/test_usable_labels_geojson.py`; G0 C2 PASS | GeoJSON/RFC 7946 export with exact properties, a date-only `event_date`, UTC `load_time` and null provenance, with zero records rejected. This is serialization evidence, not label truth. |
| G1.6 | Depth fields produced on the master grid and labelled DERIVED | PASS_WITH_CAVEATS | `docs/T6_DEPTH_OUTPUTS.json`; `pipelines/phase8/depth_fields.py`; `tests/phase8/test_depth_fields.py`; board T6 (84368ee) | Depth = water surface from flood-edge DEM elevations minus the cleaned GLO-30 **surface** model. Buildings and vegetation stay in the DEM, so urban depths are unreliable. Only 29.91–32.10% of the mapped extent has valid DEM-derived depth. Labels give extent, not depth. There is no independent observed depth. |
| G1.7 | Depth-field contract (layout, names, units, NoData, CRS, grid, times, version) | PASS_WITH_CAVEATS | `docs/DEPTH_FIELD_CONTRACT.md`; frozen `docs/master/contracts/c1_depth_v0.md`; A18 `docs/DEPTH_METADATA_REPAIR.md` and `data/features/depth/c1_metadata_repair_v0/metadata_repair_manifest.json`; `tests/phase8/test_depth_metadata_contract.py` | Single-band Float32, metres, EPSG:32644 at 30 m, NoData −9999. The event date is date-only, acquisition time is unknown (JSON null), and processing time is in UTC. `p05`/`p95` are **±4 m uncalibrated assumption bounds** (`max(0, mean−4 m)`, `mean+4 m`), not statistical percentiles. Only the A18 copies are tag-conformant; the original `batch1_v1/` files are unchanged legacy sources. The contract does not approve routing use of T6 depth. |

## Required gate checks (run 2026-11-07, this session)

| Check | Command | Result |
|---|---|---|
| Gate prerequisites | `.venv\Scripts\python.exe tools\master\gate_check.py G1` | exit 0: "G1 READY for integrator gate checklist; all listed task prerequisites are complete" |
| State integrity | `.venv\Scripts\python.exe tools\master\verify_state.py` | exit 0. No evidence drift. 16 migrations on disk; shared DB (read-only) reports 14 applied migrations and 1,319,380 grid cells. |
| Focused G1 suites | `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib -p no:cacheprovider tests/labels tests/phase8` | **37 passed** |
| Full Python suite | `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib -p no:cacheprovider` | **369 passed, 1 skipped** (env-gated), 115 subtests passed. One run covers G1–G4; details in `GATE_G4_REPORT.md` § Shared checks. |
| Backend suite | `mvn -o -B -ntp -q -f services/backend/pom.xml test` | exit 0; 30 tests, 0 failures/errors |
| Raw audit | `.venv\Scripts\python.exe tools\audit_raw_logs.py` | `DATA_FILES=157; DATA_BYTES=30544672450; HASH_MATCH=157; NO_COMPARABLE_HASH=0; MISMATCH=0` |
| Migration numbering | inspected `database/migrations/` | Unique: 001–014, 100, 101. Nothing applied during this review. |
| Requirements merge | `git log --since=2026-10-28 -- requirements*.txt`; `pip check` | Only the G0/I13 pins (`pyarrow==25.0.1`, `certifi==2026.10.23`, commit e6f201c) and A16 MLflow (6bb49c4) have changed, matching `docs/master/REQUIREMENTS_GATE_RECONCILIATION.md`. `pip check`: no broken requirements. |
| End-to-end | not applicable to G1 | G1 covers static label and depth products. There is no runtime path to exercise. |
| Backup | not required | No database write, migration or Docker operation was performed. No dump was made and no Docker volume was touched. |

## Decision and carried caveats

G1 passes with caveats. The label-acceptance *process* is sound, pre-registered and honestly applied. Its *outcome* is that no SAR-derived label was accepted. The only accepted event labels are the official UNOSAT November 2015 references. The depth contract is frozen and file-conformant through the A18 copies, but depth is an assumption-based surface-DEM proxy with partial coverage and uncalibrated ±4 m bounds.

These caveats carry forward to G2 (single training event, no accepted out-of-event label) and to every consumer of depth.

No repair task is registered for G1. No lane-owned file, database, Docker volume, tag or push was changed or created.
