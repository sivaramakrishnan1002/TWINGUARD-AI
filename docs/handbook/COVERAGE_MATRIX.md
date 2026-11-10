# Handbook coverage matrix

This matrix maps the current project documentation, code, data folders and raw dataset folders to handbook chapters. The scope is content-bearing project folders; `.git`, `.venv`, Python `__pycache__` and installed-package subfolders are implementation internals and are not described as datasets or product modules. No project folder was changed for this matrix. [repo: current folder listing]

## Existing files under `docs/`

| Source file | Covered in |
|---|---|
| `docs/COVERAGE_2015.md` | 06 Flood Events and Labels; 17 Document Control |
| `docs/DATA_MANIFEST.csv` | 05 Data Inventory; 16 References and Attribution; 17 Document Control |
| `docs/DATA_QUALITY_REPORT.md` | 05 Data Inventory; 13 Risks and Limitations; 17 Document Control |
| `docs/FEATURE_DICTIONARY.md` | 08 Engineering; 14 Glossary; 17 Document Control |
| `docs/GRID_DECISION.md` | 04 Decision Log; 08 Engineering; 09 Progress; 17 Document Control |
| `docs/ISSUES.md` | 13 Risks and Limitations; 17 Document Control |
| `docs/MANUAL_TODO.md` | 10 Roadmap; 12 Team Guide; 17 Document Control |
| `docs/OSM_COUNTS.md` | 05 Data Inventory; 08 Engineering; 13 Risks; 17 Document Control |
| `docs/OSM_WATERWAYS.md` | 05 Data Inventory; 08 Engineering; 13 Risks; 17 Document Control |
| `docs/PHASE2_CLOSURE.md` | 09 Progress; 17 Document Control |
| `docs/PHASE3_LOG.md` | 00, 05–13, 17 Document Control |
| `docs/PHASE3_PLAN.md` | 06 Flood Events; 07 Reservoirs; 10 Roadmap; 11 Evaluation; 17 Document Control |
| `docs/PHASE3_VALIDATION.json` | 08 Engineering; 13 Risks; 17 Document Control |
| `docs/PROJECT_STATUS.md` | 00 Project on a Page; 09 Progress; 17 Document Control |
| `docs/SENTINEL_PLAN.md` | 05 Data Inventory; 06 Flood Events; 10 Roadmap; 17 Document Control |
| `docs/SENTINEL_PREPROCESSING_PLAN.md` | 06 Flood Events; 10 Roadmap; 13 Risks; 17 Document Control |
| `docs/SENTINEL_SHORTLIST.csv` | 06 Flood Events; 17 Document Control |
| `docs/SENTINEL_VERIFICATION.md` | 05 Data Inventory; 06 Flood Events; 09 Progress; 13 Risks; 17 Document Control |
| `docs/STORAGE_ESTIMATE.md` | 05 Data Inventory; 17 Document Control |
| `docs/research/README.md` | 02 Research Foundation; 16 References |
| `docs/LABEL_STRATEGY.md` | **Absent**; documented as an open source conflict in 06 and 17. Existing replacement guidance is summarized from `PHASE3_PLAN.md`. |

## Handbook deliverables

| Handbook file | Coverage purpose |
|---|---|
| `docs/handbook/00_Project_on_a_Page.md` | Starting summary and project state. |
| `docs/handbook/01_Overview_and_Vision.md` | Problem framing, intended use and limits. |
| `docs/handbook/02_Research_Foundation.md` | Research gap, contributions, hypotheses and supplied literature. |
| `docs/handbook/03_Architecture_and_Tech_Stack.md` | Proposed system architecture and implementation status. |
| `docs/handbook/04_Decision_Log.md` | Recorded project decisions and impacts. |
| `docs/handbook/05_Data_Inventory.md` | Collected and missing source inventory. |
| `docs/handbook/06_Flood_Events_and_Labels.md` | Event evidence, label issue and Sentinel table. |
| `docs/handbook/07_Reservoirs_and_Track_B.md` | Reservoir data and Track B status. |
| `docs/handbook/08_Engineering_Phase2_and_Phase3.md` | Existing engineering work, outputs, checks and scripts. |
| `docs/handbook/09_Progress_and_Chronicle.md` | Phase status, dated history and folder map. |
| `docs/handbook/10_Roadmap_and_Next_Steps.md` | Next steps and remaining phase acceptance plan. |
| `docs/handbook/11_Evaluation_Plan.md` | Proposed hypothesis tests, metrics and validation limits. |
| `docs/handbook/12_Team_Guide.md` | Setup, safe work habits and manual tasks. |
| `docs/handbook/13_Risks_and_Limitations.md` | Risks and mitigations. |
| `docs/handbook/14_Glossary.md` | Plain-language term definitions. |
| `docs/handbook/15_FAQ.md` | Teammate/examiner questions and answers. |
| `docs/handbook/16_References_and_Attribution.md` | Supplied literature leads and data attribution reminders. |
| `docs/handbook/17_Document_Control.md` | Source, conflicts, open questions and spot checks. |
| `docs/handbook/TwinGuard_Project_Handbook.md` | Complete ordered master Markdown. |
| `docs/handbook/TwinGuard_Project_Handbook.docx` | Rendered Word version of the master. |
| `docs/handbook/COVERAGE_MATRIX.md` | This evidence/file/folder mapping. |

## Pipeline and tool scripts

| Source | Covered in |
|---|---|
| `pipelines/phase3/README.md` | 08 Engineering; 12 Team Guide |
| `pipelines/phase3/phase3_core.py` | 08 Engineering; 12 Team Guide |
| `pipelines/phase3/weather_reservoirs.py` | 07 Reservoirs; 08 Engineering; 12 Team Guide |
| `pipelines/phase3/summarize_event_peak_rainfall.py` | 08 Engineering; 12 Team Guide |
| `pipelines/phase3/osm_extract_graph.py` | 08 Engineering; 12 Team Guide |
| `pipelines/phase3/split_osm_layers.py` | 08 Engineering; 12 Team Guide |
| `pipelines/phase3/summarize_osm_gpkg.py` | 08 Engineering; 12 Team Guide |
| `pipelines/phase3/population_exposure.py` | 08 Engineering; 12 Team Guide |
| `pipelines/phase3/flood_labels_inspection.py` | 06 Flood Events; 08 Engineering; 12 Team Guide |
| `pipelines/phase3/validate_outputs.py` | 08 Engineering; 12 Team Guide |
| `tools/add_verified_sentinel_manifest_rows.py` | 08 Engineering; 12 Team Guide |
| `tools/audit_raw_logs.py` | 08 Engineering; 12 Team Guide |
| `tools/osm_waterways_inventory.py` | 05 Data Inventory; 08 Engineering; 12 Team Guide |
| `tools/update_phase3_manifest.py` | 08 Engineering; 12 Team Guide |
| `tools/verify_asf_sentinel.py` | 06 Flood Events; 08 Engineering; 12 Team Guide |
| `tools/verify_sentinel.py` | 08 Engineering; 12 Team Guide |
| `tools/build_handbook_docx.py` | This handbook; 12 Team Guide; 17 Document Control |

## Project folders

| Folder | Handbook coverage |
|---|---|
| `.git/` | Version history summarized in 09; internal Git metadata not reproduced. |
| `.venv/` | Environment notes in 03 and 12; package internals intentionally not catalogued. |
| `data/raw/` | All source families below; immutable rule in 04 and 12. |
| `data/processed/` | Grid, exposure and label-inspection products in 06 and 08. |
| `data/processed/grid/` | 08 Engineering; 14 Glossary. |
| `data/processed/exposure/` | 07 Reservoirs; 08 Engineering. |
| `data/processed/labels_inspection/` | 06 Flood Events; 08 Engineering. |
| `data/features/` | Feature families below; 08 Engineering. |
| `data/features/buildings/` | 05 Data Inventory; 08 Engineering. |
| `data/features/facilities/` | 05 Data Inventory; 08 Engineering. |
| `data/features/hydrology/` | 05 Data Inventory; 08 Engineering. |
| `data/features/landcover/` | 05 Data Inventory; 08 Engineering. |
| `data/features/osm/` | 05 Data Inventory; 08 Engineering. |
| `data/features/population/` | 05 Data Inventory; 08 Engineering. |
| `data/features/reservoirs/` | 07 Reservoirs; 08 Engineering. |
| `data/features/roads/` | 08 Engineering; 10 Roadmap. |
| `data/features/terrain/` | 08 Engineering; 13 Risks. |
| `data/features/weather/` | 05 Data Inventory; 08 Engineering. |
| `docs/` and `docs/research/` | This matrix; source-document table above. |
| `docs/handbook/` | All handbook outputs. |
| `experiments/` | Planned experiment space in 03 and 10. |
| `frontend/` | Planned interface in 03 and 10. |
| `notebooks/` | Planned analysis space in 09 and 12. |
| `pipelines/` and `pipelines/phase3/` | Existing scripts mapped above; 08/12. |
| `services/`, `services/backend/` | Planned backend in 03 and 10. |
| `services/ai-service/` | Planned science service in 03 and 10. |
| `tools/` | Existing tools mapped above; 08/12. |
| Python `__pycache__/` folders | Generated bytecode; not project data or user-authored source. Not separately described. |

## Raw dataset folders

| Raw folder | Datasets covered in |
|---|---|
| `data/raw/boundary/` | 05 Data Inventory |
| `data/raw/buildings/` | 05 Data Inventory; building-data absence noted in 17 |
| `data/raw/dem/` | 05 Data Inventory; 08 Engineering |
| `data/raw/historical_floods/` | 05 Data Inventory; 06 Flood Events |
| `data/raw/historical_floods/2015/` | 05 Data Inventory; 06 Flood Events |
| `data/raw/historical_floods/2015/2015-12-04/` | 05 Data Inventory; 06 Flood Events |
| `data/raw/historical_floods/2015/global_flood_database/` | 05 Data Inventory; 06 Flood Events |
| `data/raw/historical_floods/2015/opencity_flood_points/` | 05 Data Inventory; 06 Flood Events |
| `data/raw/historical_floods/2021/` | 05 Data Inventory; 06 Flood Events |
| `data/raw/historical_floods/2023/` | 05 Data Inventory; 06 Flood Events |
| `data/raw/hydrology/` | 05 Data Inventory; source status in manifest |
| `data/raw/infrastructure/` | 05 Data Inventory; source status in manifest |
| `data/raw/landcover/` | 05 Data Inventory; 08 Engineering |
| `data/raw/osm/` | 05 Data Inventory; source status in manifest |
| `data/raw/population/` | 05 Data Inventory; 08 Engineering; 13 Risks |
| `data/raw/reservoirs/` | 05 Data Inventory; 07 Reservoirs |
| `data/raw/reservoirs/kaggle_chennai_water_management/` | 05 Data Inventory; 07 Reservoirs |
| `data/raw/reservoirs/opencity_lake_levels/` | 05 Data Inventory; 07 Reservoirs |
| `data/raw/reservoirs/reference_docs/` | 05 Data Inventory; 07 Reservoirs; 16 References |
| `data/raw/roads/` | 05 Data Inventory; 08 Engineering |
| `data/raw/satellite/` | 05 Data Inventory; 06 Flood Events |
| `data/raw/satellite/sentinel1/` | 05 Data Inventory; 06 Flood Events; folder-name conflict in 17 |
| `data/raw/satellite/sentinel1/2015/` | 06 Flood Events |
| `data/raw/satellite/sentinel1/2021/` | 06 Flood Events |
| `data/raw/satellite/sentinel1/2023/` | 06 Flood Events |
| `data/raw/weather/` | 05 Data Inventory; 08 Engineering |

## Gaps and exclusions

- No content-bearing project folder or documented dataset family was intentionally omitted. Git and virtual-environment internals and generated Python bytecode are excluded as implementation machinery, not project sources.
- `docs/LABEL_STRATEGY.md` is absent, not silently skipped. The repo’s current label guidance is covered from `docs/PHASE3_PLAN.md`.
- This matrix maps whole dataset families, not every individual file in every folder. File-level names, sizes, periods, sources, licenses and status are in `docs/DATA_MANIFEST.csv` and `05_Data_Inventory.md`; all 13 Sentinel files are separately listed in `06_Flood_Events_and_Labels.md`.


## B55 refresh (10 Nov 2026) — final-year sources

| Source | Covered in |
|---|---|
| `docs/master/FINAL_YEAR_OWNER_DECISIONS.md` (OD-2026-11-07/08/08b/08c/10) | 00 Project on a Page; 04 Decision Log |
| `docs/master/CR-019_PRODUCT_REBASELINE_UI_API.md`, `CR-020_G5_PRODUCT_PIPELINE_REPLAY.md`, `CR-021_LIVE_FORECAST_MODE.md` | 03 Architecture; 04 Decision Log; 19 Runbook |
| `docs/master/GATE_G1_REPORT.md` … `GATE_G5_REPORT.md`, `ROUND2_LIVE_REVIEW.md` | 13 Risks and Limitations |
| `docs/master/G6_OWNER_DECISION_CHECKLIST.md` §3 | 16 References and Attribution |
| `docs/api/ai-service.yaml` (C4 v3), `services/ai-service/README.md` | 03 Architecture; 19 Runbook |
| `docs/trackb/B13_E2E_SCENARIO.md`, `docs/trackb/B53_LIVE_CYCLE_REPORT.md` | 03 Architecture; 13 Risks; 19 Runbook |
| `docs/ui/screenshots/README.md` and screenshots (linked, not copied) | 18 User Guide |
