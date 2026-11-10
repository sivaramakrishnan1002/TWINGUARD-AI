# G6 Gate Review — validation, documentation and release v1.0 — 2026-11-10

**Current gate decision: PASS_WITH_CAVEATS**

Reviewer: Integrator (Lane I). Scope per `docs/master/GATES.md`: "Validation, documentation, release tag v1.0". G6 requires A15, A17, I04, A29 and B55. Owner release decisions: **OD-2026-11-10b**. The owner replied "choose best" to the recommended defaults in [G6_OWNER_DECISION_CHECKLIST.md](G6_OWNER_DECISION_CHECKLIST.md).

TwinGuard is a bachelor's final-year project (OD-2026-11-07), not an operational or research-grade service. `PASS_WITH_CAVEATS` means the project's evidence, documentation and release record are complete and honest about their limits. It does not mean validated forecast or depth accuracy.

## Criterion review

| # | Criterion | Decision | Evidence |
|---|---|---|---|
| G6.1 | Validation synthesis | PASS_WITH_CAVEATS | A15 `docs/VALIDATION_REPORT.md`: internal numerical, raster and route checks pass. No independent observed depth or route truth exists, so those metrics are reported as unavailable. Gate evidence: G1–G5 reports. |
| G6.2 | Final report and paper | PASS | A29 (58273af): `docs/FINAL_REPORT.md` (thesis results chapter) and `docs/PAPER_DRAFT.md`. The Integrator verified the novelty wording verbatim, 0 broken links, all cited commits existing, no accuracy or warning claim, and GPU figures matching the benchmark. |
| G6.3 | Handbook and documentation | PASS | B55 (4281576): architecture, user guide, runbook, risks, decision log, references. The Integrator verified scope, links, no tokens and the novelty wording. API: C4 v3 in `docs/api/ai-service.yaml` (34 paths, 36 operations) and `contracts/c4_openapi_v3.md`. |
| G6.4 | Licences and attribution (M7) | PASS_WITH_CAVEATS | The 14-source table was accepted (OD-2026-11-10b). The CFM-DSS dashboard is cited as a source with no published terms. |
| G6.5 | Release record (I04) | PASS | A local annotated tag `v1.0` on this report's commit (hash below). No database dump: no G1–G5 or Round 2 work wrote to the shared `twinguard` database. No push or remote by any session; M4 (private remote, push after a secret scan) is the owner's action. Docker images stay local. |
| G6.6 | Gates G0–G5 | PASS | All `ready`: `GATE_G0`–`GATE_G5_REPORT.md`, plus the Round 2 live-mode review `ROUND2_LIVE_REVIEW.md`. |

## G6 protocol checks (2026-11-10, this session)

| Check | Command | Result |
|---|---|---|
| State integrity | `.venv\Scripts\python.exe tools\master\verify_state.py` | exit 0, no drift |
| Requirements | `.venv\Scripts\python.exe -m pip check` | "No broken requirements found." Pins unchanged since the G0/I13 reconciliation, apart from the optional `requirements-gpu.txt` (torch 2.14.1 cu126, reconciled 2026-11-08). |
| Migration numbering | inspected `database/migrations/` | unique: 001–014, 100, 101. Nothing applied by this review. |
| API contracts | `.venv\Scripts\python.exe tools\validate_api_contracts.py` | PASS. AI service: 34 paths, 36 operations. Backend: 11 paths, 12 operations. |
| Backend suite | `mvn -o -B -ntp -q -f services/backend/pom.xml test` | exit 0; 30 tests, 0 failures, 0 errors |
| Full Python suite | `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib -p no:cacheprovider` | **469 passed, 1 skipped** (env-gated isolated PostgreSQL test), 115 subtests passed, 197.5 s |
| Raw audit | `.venv\Scripts\python.exe tools\audit_raw_logs.py` | `DATA_FILES=157; DATA_BYTES=30544672450; HASH_MATCH=157; NO_COMPARABLE_HASH=0; MISMATCH=0` |
| Packaged end-to-end | not rerun at G6 | The packaged stack was stopped after B54. The latest packaged evidence is G5/B13 (product replay), B50 (packaged UI), B53 (live cycle) and B54 (live UI), all reviewed in their reports. |
| Backup | not required | OD-2026-11-10b §I04. No database write, migration or Docker operation by the Integrator. |

## Limitations carried into the release (thesis-short)

1. **Validation.** The models are calibrated on a single November 2015 SAR-derived event. The out-of-event check uses an unaccepted 2023 map. There is no observed depth or road truth, so accuracy is not validated (G1, G2, A15).
2. **Hydraulics.** The engine is a simplified 120 m citywide / 30 m focus local-inertial model with no storm-drain network. Building heights are mostly estimated (A25).
3. **Assumptions.** Reservoir outflows (A28 rule), shelter capacities, road thresholds and emergency resources are assumptions or scenario inputs, and are labelled as such.
4. **Forecasts.** Live mode is a numerical weather-model forecast pushed through this model. It is not an official warning, and its skill is not measured (CR-021).
5. **Data sources.** No gauge or IMD observations are ingested (B40/B42 parked). The CFM-DSS reservoir data has no published terms.
6. **Packaging.** The packaged checks ran on the CPU image; the GPU image has not been built. The Cesium ion token is compiled into local frontend builds, so do not publish images or bundles as built.

## Decision

G6 is **PASS_WITH_CAVEATS** and is recorded as `ready`. I04 is finished. The release is the local annotated tag `v1.0`. Remaining owner actions, none of which blocks G6:
- **M4:** create the private remote and push after a secret scan.
- **M8:** schedule the draft review and the final demo.

**Closure (2026-11-10):** I04 finished `done`, with its report commit `93704bf`. G6 is set `ready`. `gate_check.py` G0–G6: all READY. `verify_state.py`: exit 0. Master tests: 26 passed. The release tag `v1.0` (annotated, local only, not pushed) points at the commit that adds this line. Its hash is recorded in `CHANGELOG.md` and the release note below.
