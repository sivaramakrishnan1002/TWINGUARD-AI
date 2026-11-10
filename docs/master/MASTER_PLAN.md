# TwinGuard master plan

## Vision and locked stack

Build an auditable flood digital twin for the Chennai Metropolitan Area. Current evidence uses the provisional older CMA boundary (about 1,187 km²). The repository's stack is authoritative: Python pipelines, PostgreSQL 18.6/PostGIS 3.6.2, FastAPI AI-service, Docker Compose; UI uses React/TypeScript/Tailwind/MapLibre and Java 21/Spring Boot. Maven tests and the locked-dependency frontend build have recorded passing evidence; business API/data integration remains gated by task completion and service readiness.

<!-- CURRENT STATE START -->

## Current coordinated state (generated)

- G0: `ready`; C1-C8: frozen at v0.
- Gate status: G0 `ready` ([report](GATE_G0_REPORT.md)); G1 `ready` ([report](GATE_G1_REPORT.md)); G2 `ready` ([report](GATE_G2_REPORT.md)); G3 `ready` ([report](GATE_G3_REPORT.md)); G4 `ready` ([report](GATE_G4_REPORT.md)); G5 `ready` ([report](GATE_G5_REPORT.md)); G6 `not_ready`.
- Running tasks: none.
- Selector-ready tasks: A: none; B: none; I: none.

<!-- CURRENT STATE END -->

## Contributions and hypotheses

| ID | Intended contribution | Hypothesis |
|---|---|---|
| C1 | SAR-aware flood extent and depth uncertainty | H1: SAR features improve flood extent over static terrain/context features. |
| C2 | Rainfall and reservoir forecast | H2: hydrology and reservoir context improve forecast skill. |
| C3 | Impact, routing and shelter decisions | H3: time-varying depth improves safe routing and shelter ranking. |
| C4 | Integrated, uncertainty-aware digital twin | H4: uncertainty propagation improves decision reliability; H5: counterfactual decisions are more robust. |

These are proposed tests, not findings. Track B has no observed release decisions; daily storage data ends Dec 2020 per its report. Claims remain provisional until preregistered evaluation and independent events.

## Lanes

| Lane | Scope | Current evidence |
|---|---|---|
| A | labels, depth, forecasting, simulation, impact, routing, decisions, experiments and CR-006 visualization data | A01-A20 completion evidence is recorded; no Lane A task is currently running. |
| B | reservoir/replay platform, twin integration, AI/API services and product UI | G0 is ready. B08, B11, B17, B18, B21-B26 are complete with their recorded evidence/caveats. C9 remains proposed and unfrozen. B13 remains blocked pending a distinct mounted backend/UI historical REPLAY slice beyond B9 and B18/I08. B27 is blocked pending I21, CR-011 owner approval and verified date-only fixture evidence. No live operation is implied. |
| I | contracts, shared files, gates, API projections and release integration | G0 is formally ready; C1-C8 are frozen at v0. I16/CR-009, I17, I19/CR-010 and I20 completed. I21 is ready to review the proposed B13 C4 v2 API/change control. I08 completed with caveats; C9 remains proposed and unfrozen. I04 is blocked_manual pending the recorded release/tag and backup decisions. |

## Task catalogue

| ID | Task | Lane | Depends on | Status |
|---|---|---|---|---|
| F1–F12 | Foundation phases 1–9 and tools | I | — | See STATE.json; F7–F12 caveats recorded. |
| A01–A20 | Batch 1, Batch 2 and science roadmap | A | As specified in STATE.json and lane spec | See generated task catalogue below. |
| B01–B27 | Track B and product platform | B | As specified in STATE.json and Track B spec | See generated task catalogue below. |
| I01–I21 | Gate checks, requirements, contract versioning, release, CR-006, CR-008, CR-009/010, CR-011 and API projection coordination | I | See STATE.json | See generated task catalogue below. |
| M1–M8 | Human actions | M | External/manual | Listed in NEXT.md. |

## Gate calendar (relative to project day 1)

| Gate | Target | Required outcome |
|---|---:|---|
| G0 | day 2 | Contracts frozen and versions/evidence recorded. |
| G1 | day 6–10 | Accepted labels and depth contract. |
| G2 | day 10–12 | Models and risk map. |
| G3 | day 12–15 | Track B replay connected to twin. |
| G4 | day 22–25 | Forecast-to-shelter API. |
| G5 | day 28–32 | End-to-end replay test: archived input -> engine -> /v3 -> packaged UI (CR-020). |
| G6 | day 34–38 | Validation, docs and v1.0 release. |

Gate days are planning targets, not calendar commitments. No gate is declared passed without evidence and checks in GATES.md.

## Lane reports outside `docs/`

Some lane reports live with their owned code, because their lanes do not own `docs/`:

- **A25** high-resolution flood engine (120/90 m citywide, 30 m focus; commit a4b2cbc): [pipelines/a25_hires/REPORT.md](../../pipelines/a25_hires/REPORT.md)
- **A27** per-frame flow velocity and water-surface export (engine 2.1.0 `flow.npz`; commit b90c0c6): [pipelines/a25_hires/A27_FLOW.md](../../pipelines/a25_hires/A27_FLOW.md)
- **A28** live reservoir coupling rule A28-RES-STORAGE-v1 (ASSUMPTION; commit bf50c38): [pipelines/a25_hires/A28_RESERVOIR_COUPLING.md](../../pipelines/a25_hires/A28_RESERVOIR_COUPLING.md)
- **A26** optional CUDA flood-engine backend (2.25-3.67x on the RTX 3050; commit 887d089): [docs/FLOOD_ENGINE_GPU_BENCHMARK.md](../FLOOD_ENGINE_GPU_BENCHMARK.md)
- **G5** scope revised to the product pipeline: [CR-020](CR-020_G5_PRODUCT_PIPELINE_REPLAY.md), [reassessment](G5_REASSESSMENT_2026-11-08.md)


<!-- TASK TABLE START -->

| ID | Task | Lane | Depends on | Status |
|---|---|---|---|---|
| F1 | Phase 1 research | I | — | done |
| F2 | Phase 2 collection | I | — | done |
| F3 | Phase 3 features/fix-up | I | — | done |
| F4 | Phase 4 alignment/cell table | I | — | done |
| F5 | Phase 5 DB/migrations 001-012 | I | — | done |
| F6 | Phase 6 views/vector tiles | I | — | done |
| F7 | Phase 7 twin/API/AI/design | I | — | done_with_caveats |
| F8 | Docker clone | I | — | done_with_caveats |
| F9 | Handbook v1 | I | — | done_with_caveats |
| F10 | Tools setup | I | — | done_with_caveats |
| F11 | Phase 8 SAR pilot | I | — | done_with_caveats |
| F12 | Phase 9 pilot | I | — | done_with_caveats |
| A01 | Label rework T1-T5 | A | — | done_with_caveats |
| A02 | Depth fields T6 | A | A01 | done_with_caveats |
| A03 | Phase 10 without out-of-event validation | A | A03b, A03c, A04b | done_with_caveats |
| A03b | SAR diagnostic, Label Strategy V2, PDF georeferencing prep and digitised-label loader | A | A01, A02, A04b | done_with_caveats |
| A03c | Depth uncertainty scenarios and probabilistic depth classes | A | A02, A04b | done_with_caveats |
| A04 | Phase 9b model upgrade | A | A01 | done_with_caveats |
| A04b | Phase 9C: urban label censoring, independent point validation, spatial conformal fix | A | A04 | done_with_caveats |
| A04c | Phase 9C urban physical susceptibility layer | A | A04b | done_with_caveats |
| A03d | GeoPDF map labels and 2023 out-of-event check | A | A03b, A04b | done_with_caveats |
| A04d | Calibrated SAR candidate labels (diagnostic acceptance gate) | A | A03b, A04b | done_with_caveats |
| A05 | Phase 11 forecast and hindcast wrapper | A | A06 | done_with_caveats |
| A06 | Phase 12 local-inertial shallow-water simulation | A | A02, A04c, A03d | done_with_caveats |
| A07 | Phase 13 ensemble impact analysis | A | A05, A06, A02 | done_with_caveats |
| A08 | Time-dependent flood-aware routing graph | A | A07 | done_with_caveats |
| A09 | Phase 15 routing decision comparison | A | A05, A08 | done_with_caveats |
| A10 | Phase 16 shelter allocation | A | A07, A08, A09 | done_with_caveats |
| A11 | Phase 17 descriptive hazard, exposure, and access-loss layers (no vulnerability ranking) | A | A07, A10 | done_with_caveats |
| A12 | Phase 18 explainability and parameter sensitivity | A | A04, A04d, A06 | done_with_caveats |
| A13 | Phase 22 decision lab and H2–H5 experiments | A | A05, A09, A10, A11, A12 | done_with_caveats |
| A14 | Phases 19-21 experiments | A | A01, A03d, A04, A04d, A05 | done_with_caveats |
| A15 | Phase 25 validation | A | A05, A06, A09 | done_with_caveats |
| A16 | MLflow | A | — | done_with_caveats |
| A17 | Paper/report | A | A15 | done_with_caveats |
| B01 | Track B Part 1 | B | — | done_with_caveats |
| B02 | Streaming/monitoring B6-B10 | B | B01, M1 | done_with_caveats |
| B03 | Twin link/API | B | B01 | done_with_caveats |
| B04 | UI-1 | B | M3 | done_with_caveats |
| B05 | UI-2 | B | B04 | done_with_caveats |
| B06 | UI-3 | B | B05, B03 | done_with_caveats |
| B07 | UI-4 | B | B06, A07, A09, B15, I05 | done_with_caveats |
| B08 | AI real endpoints | B | A05, A07, A09, A13, B15, B16, I05, I13, I14 | done_with_caveats |
| B09 | Spring gateway | B | M2 | done_with_caveats |
| B10 | Monitoring and CI | B | B02 | done_with_caveats |
| B11 | Full-stack packaging | B | B04, B08, B09 | done_with_caveats |
| B12 | Docs | B | — | done |
| B13 | E2E scenario: packaged replay -> engine -> /v3 -> UI (G5, CR-020) | B | B02, B03, B04, B05, B06, B07, B08, B09, B11, B15, I05, B18, I21, B27, B28, I22, A25, A27, B47, B49 | done_with_caveats |
| B14 | Professional live-ready UI redesign (design-only) | B | — | done_with_caveats |
| I01 | Gate checks | I | — | done_with_caveats |
| I02 | Requirements merge | I | B01 | done_with_caveats |
| I03 | Contract versioning | I | — | done_with_caveats |
| I04 | Release/backups | I | I01 | blocked_manual |
| M1 | Pull Track B Docker images | M | — | done |
| M2 | Install Maven | M | — | done |
| M3 | Approve UI npm/network | M | — | done_with_caveats |
| M4 | Create GitHub repo/push | M | — | blocked_manual |
| M5 | Install MLflow | M | — | done_with_caveats |
| M6 | Optional PDF georeferencing | M | — | parked |
| M7 | Census/licence checks | M | — | blocked_manual |
| M8 | Mentor review dates | M | — | blocked_manual |
| I05 | Reconcile OpenAPI projections with C4-C8 evidence | I | A07, A09, B02, B15, I06, B16 | done_with_caveats |
| A18 | C1 T6 GeoTIFF metadata conformance repair | A | A02 | done_with_caveats |
| A19 | C2 accepted-label GeoJSON export and serialization tests | A | A01 | done_with_caveats |
| B15 | Align route and impact DTOs to completed C7/C8 outputs | B | A07, A09, B02, B16 | done_with_caveats |
| I06 | Publish C5 Layer catalogue OpenAPI projection | I | B02 | done_with_caveats |
| B16 | Repair and verify C4/C5 service DTO and catalogue serialization | B | B02, I06 | done_with_caveats |
| A20 | 3D flood scenario time-series and visualization readiness | A | A15 | done_with_caveats |
| I07 | Define post-G0 3D scenario display contract | I | A20, I05 | done_with_caveats |
| B17 | Serve versioned flood scenario visualization assets | B | A20, I07, B08, B09, B15 | done_with_caveats |
| B18 | 3D flood scenario timeline and map visualization | B | B17, B05, B06, B07, B14, B21, I19, B23, B24, I20 | done_with_caveats |
| I08 | End-to-end acceptance for 3D flood scenario replay | I | A20, I07, B17, B18 | done_with_caveats |
| B19 | Preserve date-only reservoir time semantics through replay and persistence | B | B02, B03 | done_with_caveats |
| I09 | Reconcile C3 date-only timestamp contract and gate evidence | I | B19, I01 | done_with_caveats |
| I10 | Apply approved C3 date-only contract policy and gate evidence | I | B19, I09 | done_with_caveats |
| B20 | Verify isolated PostgreSQL persistence compatibility for C3 date-only records | B | B03, B19 | done_with_caveats |
| I11 | Reconcile C3 persistence compatibility evidence after B20 | I | B20, I10 | done_with_caveats |
| I12 | Final G0 evidence reassessment and gate closure | I | A07, A09, A13, A16, A18, A19, B02, B09, B15, B16, B20, I01, I05, I06, I11, M5 | done_with_caveats |
| I13 | Reconcile root and Lane A dependency pins for the G0 gate | I | I02, A16, M5 | done_with_caveats |
| I14 | CR-008: reconcile B08 artifact selectors under change control | I | A07, A09, B15, I05 | done_with_caveats |
| I15 | Reconcile OpenAPI runtime annotations after B08 | I | B08, I14, I05 | done_with_caveats |
| I16 | CR-009 C9 read-only route activation change-control review | I | I07, B17 | done_with_caveats |
| B21 | Mount approved C9 read-only catalog and detail routes | B | B08, B09, B11, B17, I07, I16, I17 | done_with_caveats |
| I17 | Complete CR-009 catalog duplicate-identity response mapping | I | I16, B17 | done_with_caveats |
| B22 | Reconcile B11 packaging checks after C9 route mounts | B | B11, B21 | done |
| I18 | Define browser and raster delivery prerequisites for B18 | I | A20, I07, B17, B21, B22 | done_with_caveats |
| I19 | Project approved C9 raster delivery projection | I | I18 | done_with_caveats |
| B23 | Serve exact A20 scenario GeoTIFF assets read-only | B | A20, I18, I19, B17, B21, B22 | done_with_caveats |
| B24 | Allow the packaged B18 UI origin to read approved AI scenario assets | B | B21, B22, B23 | done_with_caveats |
| I20 | Reconcile C9 raster runtime projection after package verification | I | I19, B24 | done_with_caveats |
| B25 | Repair AI image Rasterio libexpat runtime dependency | B | B11, B23 | done |
| B26 | Display authoritative gate state in the packaged UI | B | B18, I08 | done_with_caveats |
| I21 | CR-011 B13 replay API and change-control review | I | B08, B09, B11, B15, B18, B19, B26, I05, I08, I20 | done_with_caveats |
| B27 | B13 source-backed date-only observation replay vertical slice | B | B08, B09, B11, B15, B18, B19, B26, I05, I08, I20, I21, B28, I22 | done_with_caveats |
| B28 | B13 source-backed date-only replay fixture evidence | B | B09, B19 | done_with_caveats |
| I22 | CR-012 API projection for date-only observation replay | I | B28, I21 | done_with_caveats |
| B29 | Frontend product experience - centralized DEMO/SIMULATED mode | B | B14, B18, B27 | done_with_caveats |
| B30 | Refine B29 frontend visual design from user reference | B | B29 | done_with_caveats |
| A21 | Evaluate three-state evidence-aware flood routing and novelty | A | A08, A09, A13, A15, A10 | done_with_caveats |
| B31 | Flood operations control-room UI refinement | B | B29, B30 | done_with_caveats |
| B32 | High-fidelity TwinGuard product UI | B | B29, B30, B31 | done_with_caveats |
| B33 | Reference-inspired flood control-room UI | B | B29, B30, B31, B32 | done_with_caveats |
| I23 | Map live-data integration flow against frozen contracts | I | — | done_with_caveats |
| B34 | Inventory live-source readiness and evidence gaps | B | — | done |
| B35 | Define fixture-only ingestion adapter and offline behavior tests | B | I23, B34 | done |
| B36 | Add explicit source and freshness states to the UI adapter boundary | B | B33, I23, B34, B35 | done_with_caveats |
| I24 | Prepare rainfall and reservoir source authorization decision package | I | I23, B34, B35, B36 | done_with_caveats |
| B37 | Professor-facing TwinGuard demo UI refinement | B | B33, B36, B18, I08, I24 | done_with_caveats |
| B38 | Verify IMD rainfall and weather source readiness | B | B34, I24 | done_with_caveats |
| B39 | Verify official Tamil Nadu reservoir source readiness | B | B34, I24 | done_with_caveats |
| B40 | Implement authorized IMD rainfall/weather connector | B | B38 | blocked_prerequisite |
| B41 | Implement bounded public CFM-DSS reservoir snapshot connector | B | B39 | done_with_caveats |
| B42 | Prove observation-triggered recomputation through API and UI | B | B37, B40, B41 | blocked_prerequisite |
| B43 | Connect Open-Meteo Chennai weather-model context to the product UI | B | B34, B35, B36, B37, I23, I24 | done_with_caveats |
| A22 | Assess Open-Meteo Chennai weather-model rainfall for a versioned flood run | A | A05, A06, B43 | done_with_caveats |
| A23 | Assess spatial Open-Meteo rainfall forcing over A06 domain | A | A22, A05, A06, B43 | done_with_caveats |
| I25 | Define additive CFM-DSS reservoir snapshot API projection | I | B41, I23, I24 | done_with_caveats |
| B44 | Mount read-only CFM-DSS reservoir snapshot API | B | I25, B41 | done_with_caveats |
| B45 | Connect CFM reservoir snapshots to the product UI | B | B44, B36, B37 | done_with_caveats |
| A24 | G4 repair: versioned shelter-allocation result schema and A05 forecast artifact selector evidence | A | A05, A10 | parked |
| I26 | G4 repair: CR-019 additive read-only forecast and shelter API projection | I | A24 | parked |
| B46 | G4 repair: mount read-only saved forecast and shelter-allocation endpoints | B | I26, A24, B08 | parked |
| A25 | High-resolution flood simulation for 3D (citywide 90-120 m, 30 m focus areas, buildings, wards) | A | A23, A10, A21 | done_with_caveats |
| B47 | Simulation and decision API (C4 v3) | B | B08, B44, B45 | done_with_caveats |
| B48 | Reference-design UI with Google Photorealistic 3D Tiles (7 tabs) — ui session | B | B45, B37 | done_with_caveats |
| A27 | Per-frame flow velocity and water-surface export for UI flow animation | A | A25 | done |
| A26 | Optional CUDA backend for services/flood_engine (OD-2026-11-08) | A | A25 | done |
| B49 | Serve per-frame flow (GET /v3/simulations/{run_id}/flow) | B | A27, B47 | done |
| B50 | Packaged-UI G5 screenshots (Tabs 2 and 7 on the B11 nginx package) — ui session | B | B13 | done |
| A28 | Live reservoir coupling and forecast-run checks (CR-021) | A | A25, A26, A27 | done |
| B51 | Live forecast scheduler and /v3/live endpoints (CR-021) | B | B47, B49, B44, A26 | done |
| B52 | Live-first UI: smart badge, live status, refresh and auto-switch (CR-021) - ui session | B | B51 | done |
| B53 | Round 2 verification: one full live cycle on the packaged stack (CR-021) | B | A28, B51, B52 | done_with_caveats |
| I27 | Round 2 live-stage review (CR-021) | I | B53 | done_with_caveats |
| B54 | Packaged live-UI screenshots (18_live_*) - ui session | B | B52, B53 | done |
| A29 | Round 4: final report and paper refresh (G6) | A | A17, A28, B53, I27 | done |
| B55 | Round 4: handbook refresh (architecture, user guide, runbook, attribution) | B | B53, I27 | done |

<!-- TASK TABLE END -->
