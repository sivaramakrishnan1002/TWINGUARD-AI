# Progress and Chronicle

## Status of the 26-phase roadmap

This is the roadmap supplied in the project brief, reconciled to current repository evidence. “Complete” means planning/collection work is recorded, not that a production system exists. Phases 1–2 are reported closed; Phase 3 feature preparation is complete but the labels and data decisions remain exploratory. Phases 4–26 are not started unless noted. [repo: `docs/PROJECT_STATUS.md`, `docs/PHASE2_CLOSURE.md`, `docs/PHASE3_LOG.md`; user]

| Phase | Scope | Status / evidence |
|---:|---|---|
| 1 | Research foundation | Reported complete; detailed evidence in earlier project work is not fully represented in this repo. [repo: `docs/PROJECT_STATUS.md`] |
| 2 | Study area and data collection | Close-out complete for collected sources, with known gaps and manual tasks. [repo: `docs/PHASE2_CLOSURE.md`] |
| 3 | Data engineering and features | Part B feature preparation complete; outputs exploratory, label limitations remain. [repo: `docs/PHASE3_LOG.md`] |
| 4 | Preprocessing and temporal/spatial alignment | Not started. [repo: `docs/PHASE3_PLAN.md`] |
| 5 | PostgreSQL/PostGIS foundation | Compose configured; containers not started, local database setup status unknown. [repo: `docker-compose.yml`; user] |
| 6 | GIS layers | Not started as an application/database layer. Existing Phase 3 GIS outputs are research artifacts. [repo: `docs/PHASE3_LOG.md`] |
| 7 | Digital Twin foundation | Not started; design only. [user] |
| 8 | Historical flood dataset | Partial; no final, event-consistent label set. [repo: `docs/PHASE3_LOG.md`] |
| 9 | Baseline ML | Not started; no model trained. [repo: `docs/PROJECT_STATUS.md`] |
| 10 | Flood risk mapping | Not started as model output. [user] |
| 11 | Forecast modelling | Not started. [repo: `docs/PROJECT_STATUS.md`] |
| 12 | Flood simulation | Not started. [user] |
| 13 | Impact and cascading risk | Not started beyond exploratory exposure summaries. [repo: `docs/PHASE3_LOG.md`] |
| 14 | Road graph | Extracted, but connectivity/routability is not validated; phase is partial. [repo: `docs/PHASE3_LOG.md`] |
| 15 | Risk-aware evacuation routing | Not started. [user] |
| 16 | Shelter ranking/allocation | Not started. [user] |
| 17 | Emergency priority management | Not started. [user] |
| 18 | Explainable AI | Not started. [user] |
| 19 | Temporal Transformer | Not started. [user] |
| 20 | Satellite vision model | Not started; Sentinel ZIPs remain raw. [repo: `docs/SENTINEL_VERIFICATION.md`] |
| 21 | Multimodal fusion | Not started. [user] |
| 22 | Uncertainty and decision evaluation | Not started. [user] |
| 23 | Dashboard/command centre | Not started. [user] |
| 24 | Full integration | Not started. [user] |
| 25 | Historical validation and experiments | Not started; label preparation is incomplete. [repo: `docs/PHASE3_LOG.md`] |
| 26 | Deployment, documentation and paper | Not started. This handbook is project documentation, not final thesis/paper. [user] |

## Dated repository chronicle

| Date/time recorded | Event | Evidence |
|---|---|---|
| 8 Oct 2026 17:25 +05:30 | Initial project setup and Phase 3 planning commit. | Git commit `19491b1`. |
| 8 Oct 2026 21:36 +05:30 | Phase 2 data close-out commit. | Git commit `eb247de`. |
| 14 Oct 2026 12:02 +05:30 | Phase 2 Sentinel verification commit. | Git commit `80f17a5`. |
| 14 Oct 2026 14:26 +05:30 | Phase 3 feature preparation commit. | Git commit `3bc6e90`. |
| 14 Oct 2026 | Final Part B report records 13 verified Sentinel archives and 18 raster checks. | `docs/PHASE3_LOG.md`. |
| 16 Oct 2026 | Handbook source review date. | System clock for this writing task. |

Planning-chat sequence (project vision, boundary choice, label feasibility review, two-track design, reservoir-data search, manual downloads and ASF switch) is described by the user; exact dates are not present in repository evidence, so those dates are **date not recorded**. [user]

## Known project folder map

`data/raw/` is organized by `boundary`, `buildings`, `dem`, `historical_floods`, `hydrology`, `infrastructure`, `landcover`, `osm`, `population`, `reservoirs`, `roads`, `satellite` and `weather`. Derived results are in `data/processed/` and `data/features/`; they are excluded from Git. Project code is in `pipelines/phase3/` and `tools/`. Planned product folders include `services/backend/`, `services/ai-service/`, `frontend/`, `notebooks/`, `experiments/`, and `docs/research/`. [repo: folder tree, `.gitignore`, `README.md`]
