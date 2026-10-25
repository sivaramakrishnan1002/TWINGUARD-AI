# TwinGuard master plan

## Vision and locked stack

Build an auditable flood digital twin for the Chennai Metropolitan Area. Current evidence uses the provisional older CMA boundary (about 1,187 km²). The repository's stack is authoritative: Python pipelines, PostgreSQL 18.6/PostGIS 3.6.2, FastAPI AI-service, Docker Compose; planned UI uses React/TypeScript/Tailwind/MapLibre and Java 21/Spring Boot. Maven is unavailable and the UI has not been installed.

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
| A | labels, depth, forecasting, simulation, impact, routing, decisions and experiments | Batch 1 T3 doing; T1/T2 reported complete in the board. |
| B | reservoir/replay platform, twin integration and product UI | Track B board reports B1–B6/B10–B13 complete with caveats; B7–B9 blocked. UI tasks not started. |
| I | contracts, shared files, gates and release integration | Integrator control files being established. |

## Task catalogue

| ID | Task | Lane | Depends on | Status |
|---|---|---|---|---|
| F1–F12 | Foundation phases 1–9 and tools | I | — | See STATE.json; F7–F12 caveats recorded. |
| A01–A17 | Batch 1 and science roadmap | A | As specified in STATE.json and lane spec | A01 running; downstream tasks blocked/not started. |
| B01–B13 | Track B and product platform | B | As specified in STATE.json and Track B spec | Verify board plus disk in RECONCILIATION.md. |
| I01–I04 | Gate checks, requirements merge, contract versioning, release | I | See STATE.json | I01/I03 ready; release gated. |
| M1–M8 | Human actions | M | External/manual | Listed in NEXT.md. |

## Gate calendar (relative to project day 1)

| Gate | Target | Required outcome |
|---|---:|---|
| G0 | day 2 | Contracts frozen and versions/evidence recorded. |
| G1 | day 6–10 | Accepted labels and depth contract. |
| G2 | day 10–12 | Models and risk map. |
| G3 | day 12–15 | Track B replay connected to twin. |
| G4 | day 22–25 | Forecast-to-shelter API. |
| G5 | day 28–32 | End-to-end replay test. |
| G6 | day 34–38 | Validation, docs and v1.0 release. |

Gate days are planning targets, not calendar commitments. No gate is declared passed without evidence and checks in GATES.md.


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
| A01 | Label rework T1-T5 | A | — | running |
| A02 | Depth fields T6 | A | A01 | blocked_prerequisite |
| A03 | Phase 10 risk map T7-T8 | A | A01 | blocked_prerequisite |
| A04 | Phase 9b model upgrade | A | A01 | blocked_prerequisite |
| A05 | Phase 11 forecast | A | A01, A02, A04 | blocked_prerequisite |
| A06 | Phase 12 simulation | A | A02 | blocked_prerequisite |
| A07 | Phase 13 impact | A | A02 | blocked_prerequisite |
| A08 | Time-dependent routing graph | A | A07 | blocked_prerequisite |
| A09 | Phase 15 routing | A | A08, A05 | blocked_prerequisite |
| A10 | Phase 16 shelter ranking | A | A07, A08 | blocked_prerequisite |
| A11 | Phase 17 priority zones | A | A07, A10 | blocked_prerequisite |
| A12 | Phase 18 explainability | A | A04 | blocked_prerequisite |
| A13 | Phase 22 uncertainty/counterfactuals | A | A05, A09, A10 | blocked_prerequisite |
| A14 | Phases 19-21 experiments | A | A05, A01 | blocked_prerequisite |
| A15 | Phase 25 validation | A | A05, A06, A09 | blocked_prerequisite |
| A16 | MLflow | A | — | blocked_manual |
| A17 | Paper/report | A | A15 | blocked_prerequisite |
| B01 | Track B Part 1 | B | — | done_with_caveats |
| B02 | Streaming/monitoring B6-B10 | B | B01, M1 | blocked_prerequisite |
| B03 | Twin link/API | B | B01 | done_with_caveats |
| B04 | UI-1 | B | — | blocked_manual |
| B05 | UI-2 | B | B04 | blocked_prerequisite |
| B06 | UI-3 | B | B04, B03 | blocked_prerequisite |
| B07 | UI-4 | B | B04, A09 | blocked_prerequisite |
| B08 | AI real endpoints | B | A05, A13 | blocked_prerequisite |
| B09 | Spring gateway | B | M2 | blocked_manual |
| B10 | Monitoring and CI | B | B02 | blocked_prerequisite |
| B11 | Full-stack packaging | B | B04, B08, B09 | blocked_prerequisite |
| B12 | Docs | B | — | running |
| B13 | E2E scenario | B | B02, B03, B04 | blocked_prerequisite |
| I01 | Gate checks | I | — | ready |
| I02 | Requirements merge | I | B01 | not_started |
| I03 | Contract versioning | I | — | ready |
| I04 | Release/backups | I | I01 | blocked_prerequisite |
| M1 | Pull Track B Docker images | M | — | blocked_manual |
| M2 | Install Maven | M | — | blocked_manual |
| M3 | Approve UI npm/network | M | — | blocked_manual |
| M4 | Create GitHub repo/push | M | — | blocked_manual |
| M5 | Install MLflow | M | — | blocked_manual |
| M6 | Optional PDF georeferencing | M | — | parked |
| M7 | Census/licence checks | M | — | blocked_manual |
| M8 | Mentor review dates | M | — | blocked_manual |

<!-- TASK TABLE END -->
