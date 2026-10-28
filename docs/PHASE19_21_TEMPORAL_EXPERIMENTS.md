# A14 — H1 temporal and modality experiment feasibility

## Decision

**H1 is not testable with the accepted flood labels currently available.** No model was trained and no performance metrics were computed. This is a missing-validation-data conclusion, not evidence that a modality succeeds or fails.

The read-only accepted-label export contains 10,419 Tier A geometries: 4,704 event_flood features dated 2015-11-12 and 3,710 dated 2015-11-24, plus 1,360 and 645 baseline_water features dated 2015-09-01 and 2015-10-14. The two flood dates are in the same 2015 Chennai episode, so they do not provide an independent held-out event year. Baseline water is not a positive flood target.

2021-11-13 NRSC and 2023-12-07 NDEM maps remain map-only/preliminary and have no accepted digitized event label for scoring. The December 2015 peak still lacks an accepted official vector layer. OpenCity points have unclear dates and approximate locations, so they cannot supply date-matched event truth. SAR-derived candidates remain Tier D and are excluded; the 24 November scene may be the same scene used to prepare the UNOSAT map, making same-scene comparison potentially circular.

## Registered experiment and available inputs

The pre-registered configuration is experiments/temporal_models/batch2_v1/experiment_config.json; the feasibility result is experiments/temporal_models/batch2_v1/feasibility_results.json. The planned comparison uses one identical Tier A event target and coverage mask for weather-only, terrain-only, SAR-only where independent/eligible, and combined features. It requires grouped whole-event holdout, followed by spatial blocks, with preprocessing fitted only on training rows. The spatial plan uses the project 3 km blocks (100 × 100 master-grid cells); a one-block validation buffer is recorded as a provisional conservative design choice that must be checked before a future scored run.

| Modality | Current artifact evidence | Scoring decision |
|---|---|---|
| Weather/rainfall only | A05 event/scenario rainfall artifacts exist. | Feasibility only; no independent accepted held-out event labels. |
| Terrain/hydrology only | Phase 9B v2 feature table exists. | Feasibility only; a single accepted event year cannot test event generalization. |
| SAR only | Sentinel-1 feature and candidate artifacts exist. | Excluded from scoring: derived labels are Tier D, and 24 November may share the mapping scene. |
| Combined | Weather, terrain/hydrology and land-cover artifacts exist; SAR would only be included if independent and eligible. | Feasibility only; no scored comparison. |

The scored metrics—precision, recall, F1, IoU/CSI and PR-AUC where valid—are all **not computed**. No thresholds were selected, no model fit or split was run, and there is no model hash. The two November dates could support a clearly separate within-episode date-transfer study, but that would not establish H1's held-out-event claim; it was not run here.

## Reproducibility and validation

Input SHA-256 values, the seed reserved for a future run, target/date rules, modality inclusion rules, split plan and the no-fit decision are recorded in the experiment configuration. The recorded hashes include the accepted-label GeoJSON, SAR candidate metrics and registry, Phase 9B v2 cell table, A05 forecast summary, and label-strategy/SAR-diagnostic reports. No data were changed.

Focused validation command: .venv\Scripts\python.exe -m pytest -q tests\temporal_models\test_h1_feasibility.py --import-mode=importlib
Raw audit command: .venv\Scripts\python.exe tools\audit_raw_logs.py

Focused tests: 3 passed. All 7 registered input SHA-256 hashes matched the current files. Raw audit: DATA_FILES=157; DATA_BYTES=30544672450; HASH_MATCH=157; NO_COMPARABLE_HASH=0; MISMATCH=0. The focused tests validate the not-testable state, null metrics, Tier A-only event target, same-year event limitation and exclusion of SAR Tier D candidates. Do not interpret the result as a model benchmark.

## What would unblock H1

Obtain a QA-accepted, date-matched event extent for another independent event (for example, an approved digitization of the 2021 or 2023 official map, with georeferencing and interpretation QA), or an accepted official December 2015 extent. Before scoring, verify target/feature timestamps and coverage, confirm the spatial buffer, then run the preregistered grouped event and spatial-block evaluation. Keep undated OpenCity points as a separate spatial cross-check, not an event label.
