# G3 Gate Review — replay connected to twin and integration evidence — 2026-11-07

**Current gate decision: PASS_WITH_CAVEATS**

Reviewer: Integrator (Lane I) session. Scope per `docs/master/GATES.md`: "Replay connected to twin and integration evidence". Required tasks: B02 (Streaming/monitoring B6–B10) and B03 (Twin link/API). Both are `done_with_caveats`. Supporting completed evidence: B19 (date-only semantics), B20 (isolated PostgreSQL date-only persistence), I11 and the G0 C3/C6 findings.

`PASS_WITH_CAVEATS` means historical **REPLAY** data has been shown to flow through Kafka, Redis, the consumer and Prometheus into twin tables, in an **isolated test database only**. It is not live ingestion, live monitoring or shared-database integration. On that basis `STATE.json` records G3 as `ready`.

## Owner-accepted protocol deviation

Lanes did not stop for this gate. A23 (Lane A, lock held) and the UI redesign kept running with the project owner's approval, because G3 reviews completed tasks. Their paths were not edited and their locks were not touched. No Track B, database or Docker operation was run by this review.

## Criterion review

| # | Criterion | Decision | Evidence | Binding caveats |
|---|---|---|---|---|
| G3.1 | Replay data plane: producer → Kafka → consumer → Redis, with metrics and Prometheus | PASS_WITH_CAVEATS | `docs/trackb/RUNBOOK.md` (runs `a68fb84f09bb4d1e80517e8eab42d25f` and `0985c9e7544449eda8abe120a2f12512`); `docs/trackb/TRACKB_REPORT.md` (B9); `docs/trackb/PROGRESS_BOARD.md`; `docker-compose.trackb.yml` | 120/120 producer acks per pass. 170 unique messages consumed (60 rain, 60 reservoir, 50 alerts) with 0 rule errors. Zero lag on the 5 non-empty partitions; Prometheus target up=1. All records are `source=replay`. **This is historical replay, not live operation.** The runtime runs were not repeated in this review. |
| G3.2 | Replay connected to the twin (persistence) | PASS_WITH_CAVEATS | RUNBOOK § B9 isolated persistence; `database/migrations/100_trackb_twin_link.sql`; `pipelines/trackb/persistence.py`; G0 C6 finding (`docs/master/GATE_G0_REPORT.md`) | The isolated `twinguard_trackb_test` (owner `twinguard_app`) holds 60 `twin.reservoir_state`, 60 recompute markers and 50 each of `trackb.alert_events`, `twin.trackb_alert_links` and `twin.alerts`, all for one replay run. A same-run repeat left the counts unchanged (idempotent). **Migrations 100/101 are applied only to the isolated test DB.** Shared `twinguard` stays at 14 migrations with no Track B tables. |
| G3.3 | Date-only time semantics through replay and persistence (C3) | PASS_WITH_CAVEATS | B19 `docs/trackb/MESSAGES.md`, `tests/trackb/test_date_only_timestamps.py`; B20 `tests/trackb/test_date_only_persistence_db.py`, `docs/master/B20_MIGRATION_100_RECONCILIATION.md`; `docs/master/C3_DATE_ONLY_DECISION.json` | **The B9 Kafka runs predate B19.** Their reservoir rows used the old provisional instant encoding (`Asia/Kolkata` "DEFAULT, to confirm"), which the approved C3 policy has since replaced. Current code keeps `source_date`, sets `observed_at=null` and timezone unknown, and keeps `received_at` separate. This is proven by unit tests and by B20's isolated PostgreSQL persistence/readback (1 passed, gated). **No full Kafka/Redis replay has been rerun under the date-only semantics.** G5/B13 covers the source-backed date-only replay path end to end. Historical measurement time and timezone remain unknown. |
| G3.4 | Twin read API | PASS_WITH_CAVEATS | `services/trackb/router.py`; `tests/trackb/test_router.py`; C4/C5/C6 frozen v0 | A read-only FastAPI router with an injected reader. It returns 503 when no reader is configured, rejects rows without a replay/live/simulated source, and serializes date-only rows without synthetic instants. **It is not mounted** in the AI service or gateway and has no configured database reader, so no twin read API is exposed at runtime. The router is tested with fakes only. |
| G3.5 | Task completion records | PASS_WITH_CAVEATS | `STATE.json` B02 (commit bc80bb4) and B03; `git log` (b0d123e added `services/trackb/router.py` and migration 100; d12c454 added date-only persistence and migration 101) | The B03 record has no `finished_at` or `commit` and no notes. Its completion rests on the cited files and the B9/B20 evidence, not on a recorded closeout. This review adds the commit references to the B03 notes. No behaviour depends on the missing metadata. |

## Required gate checks (run 2026-11-07, this session)

| Check | Command | Result |
|---|---|---|
| Gate prerequisites | `.venv\Scripts\python.exe tools\master\gate_check.py G3` | exit 0: "G3 READY for integrator gate checklist; all listed task prerequisites are complete" |
| State integrity | `.venv\Scripts\python.exe tools\master\verify_state.py` | exit 0, no evidence drift. Shared DB read-only: 14 applied migrations. |
| Focused G3 suites | `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib -p no:cacheprovider tests/trackb tests/stage7` | **71 passed, 1 skipped** (the env-gated isolated PostgreSQL test, not enabled in this review), 1 existing Starlette/httpx deprecation warning |
| API contracts | `.venv\Scripts\python.exe tools\validate_api_contracts.py` | PASS. AI service: OpenAPI 3.1.0, 13 paths/13 operations. Backend: OpenAPI 3.1.0, 11 paths/12 operations. |
| Full Python suite | `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib -p no:cacheprovider` | **369 passed, 1 skipped** (env-gated); backend Maven 30 tests passed. See `GATE_G4_REPORT.md` § Shared checks. |
| Raw audit | `.venv\Scripts\python.exe tools\audit_raw_logs.py` | 157/157 hash matches, 0 mismatches |
| Migration numbering | inspected `database/migrations/` | unique 001–014, 100, 101; nothing applied |
| End-to-end | reviewed, not rerun | The B9 replay and B20 isolated persistence records were reviewed. No Docker services were started and no DB connection beyond `verify_state.py`'s read-only summary was made. |
| Backup | not required | No DB write, migration or Docker operation. No dump made; no volume touched. |

## Decision and carried caveats

G3 passes with caveats. The replay-to-twin connection is demonstrated, idempotent and source-labelled, but only for historical REPLAY into an isolated test database. The full broker replay predates the approved date-only C3 semantics, and the twin read router is not mounted.

None of this may be presented as live ingestion, live monitoring, deployed integration or shared-database state. Applying migrations 100/101 to shared `twinguard` still needs separate authorization. No repair task is registered: every G3 criterion is met within these bounds, and the remaining end-to-end date-only replay belongs to G5/B13.

No lane-owned file, database, Docker volume, tag or push was changed or created.
