# Track B progress board

| Task | Status | Commit hash | Notes |
|---|---|---|---|
| B1 audit | done | pending | Daily Kaggle coverage, monthly OpenCity gaps, rainfall source coverage, matched rainfall scale comparison, capacity provenance documented in AUDIT_AND_BACKTEST.md. |
| B2 target | done | pending | Future storage target N=7/fraction=.80; all 3×3 sensitivity combinations calculated. Capacities remain current-published assumptions. |
| B3 rule engine and models | done | pending | Train 2004–14, calibrate 2015–17, held-out 2018–20, horizon-purged. Rule + calibrated logistic and histogram gradient boosting where calibration classes permit; CPU. |
| B4 backtest | done | pending | Per-reservoir/combined POD/FAR/CSI, lead times, 300 year-block bootstrap replicates, reliability curves, persistence and rainfall-only baselines; separate 2015 case study. Storage-target metrics only. |
| B5 replay format | done | pending | Offline replay of 2015-11-20–2015-12-04 wrote 50 explicitly replay-labeled JSONL alert candidates; no DB write. |
| B6 compose | done | — | Track B-only overlay uses the four locally verified image tags; ports are loopback-bound. Quiet Compose validation passed during B9. |
| B7 topics and clients | done | — | Topic/client and Redis processing implemented; B9 replay processing reconciled 60 rain + 60 reservoir unique input IDs; producer acknowledged both original and idempotency replay copies. |
| B8 metrics | done | — | Bounded-cardinality metrics and loopback endpoint verified in B9: 170 unique messages, 50 alerts, zero rule errors, 170 latency observations, Prometheus target up. |
| B9 end-to-end | done_with_caveats | — | Fresh REPLAY run `0985c9e7544449eda8abe120a2f12512` verified Kafka, Redis, Prometheus, isolated DB persistence/idempotency and offsets. This is replay evidence only; live ingestion/operation is not verified. Exact evidence in `RUNBOOK.md`. |
| B10 stop and clean | done | — | 2026-10-27 stop-only succeeded; all four Track B containers exited and all four named volumes remain present. No volume cleanup ran. |
| B11 twin link | done | pending | Migration 100 and required base migrations applied only to `twinguard_trackb_test`; isolated persistence/idempotency verified. Migration 100 remains absent from shared `twinguard`. |
| B12 API | done | pending | Five read-only endpoints and focused route tests; adapter injection, host app mount deferred. |
| B13 docs | done | pending | Audit, results, sensitivity CSV, report, lineage/limits, realtime design and diagram authored. |

## Current evidence and limits

- B7 focused checkpoint: 12 tests passed; B8 checkpoint: 16 tests passed; after B9 runtime/persistence fixes, current focused Track B suite: 22 passed, one existing Starlette/httpx deprecation warning. Changed Python modules compile.
- Latest full suite (2026-10-27, pytest importlib mode): 133 passed, 0 failed, one existing Starlette/httpx deprecation warning. Default collection reports the separate explainability/Track B test module-name collision.
- Latest raw audit after replay (2026-10-27): 157 files, 30,544,672,450 bytes, 157 hash matches, 0 missing comparable hashes, 0 mismatches. `data/raw/` remains read-only.
- DERIVED storage-target backtest uses 2018–2020 held-out years; outcome labels are future daily storage threshold attainment. This is not a flood or release-decision evaluation.
- Daily storage ends 2020-12-03; 2021/2023 have no daily-storage test coverage. Current published capacity denominators are not verified historically. Kaggle rain unit is INFERRED.
- Verified local image tags: `redis:8.10.2-alpine`, `apache/kafka:4.3.2`, `prom/prometheus:v3.13.2`, `grafana/grafana:13.2.2-ubuntu`. Installed clients: redis 8.1.0, confluent-kafka 2.16.0, prometheus-client 0.26.0. No image pulls or package installs.
- Quiet Compose validation passed. All four Track B services reached healthy after replacing the Grafana healthcheck command with the image-provided curl binary.
- B9 root cause: after every poll, `update_consumer_lag` queried Kafka watermarks synchronously (up to one second per assigned partition), starving the consumer; it also treated `OFFSET_INVALID` (-1001) as a real position and inflated lag. The fix uses cached watermarks and skips invalid/uninitialized positions. Regression tests cover these cases and delivery retry behavior.
- Successful data-plane REPLAY run `e38099ac743d47ccb69980c9b7cea0ef`: producer 120 sent / 120 acknowledged. Kafka scan found this run's 60 rain updates, 60 reservoir updates, and 50 generated alert events. Consumer metrics processed 60 rain + 60 reservoir + 50 alert records = 170; rule errors 0. Alert metrics: Warning 31, Watch 16, Critical 3. Kafka group had 8 assigned partitions, 5 with committed offsets at log end and lag 0; 3 partitions were empty and had no committed offset.
- Isolated Redis DB 3 contained 120 run-specific input dedupe markers, four reservoir state keys, four current-alert keys (all current levels Warning), and four latest-rain keys. Metrics: 170 processed, 50 alerts, 0 errors, 170 latency observations, sum 175.269548 s (mean 1.030997 s), active-partition lag 0. Prometheus target was `up` during the consumer run.
- Historical 2026-10-25 status: B9 was blocked because isolated DB persistence was unavailable. See the 2026-10-27 recheck below; migration 100 is now applied only to `twinguard_trackb_test`.
- 2026-10-25 DB preflight: configured connection resolves to shared `twinguard`; PostgreSQL 18 and PostGIS are available; shared ledger has 14 migrations; migration 100 and Track B target tables are absent. Candidate `twinguard_trackb_test_20261025_29c98e7b46` was unused but not created; recheck before use. The configured role has neither `CREATEDB` nor superuser. Required action: an authorized DBA must provision a fresh empty isolated database with PostGIS and assign the configured role ownership (or equivalent database-scoped privileges); do not grant/change privileges on shared `twinguard`.
- B10 stop after the successful rerun returned success. All four Track B services are exited, and all four named volumes remain present.
- Migration 100 is applied only to isolated `twinguard_trackb_test`; it remains absent from shared `twinguard`. No shared DB writes occurred.
- The user authorized continuation with the earlier credential unrotated. Its value is not repeated or placed in logs or reports; Compose output remains suppressed.
- GPU compute was not needed for streaming, metrics or dashboard work.
- Track B changes remain uncommitted; unrelated worktree paths are preserved.
- G0 repair checkpoint verification (2026-10-27): focused Track B + AI-service tests **35 passed**; Python compilation passed; backend `mvn -q test` passed; latest full suite `pytest -q --import-mode=importlib` **137 passed**, one existing Starlette/httpx deprecation warning. Raw audit: **157 files, 30,544,672,450 bytes, 157 hash matches, 0 without comparable hashes, 0 mismatches**.
- Fresh B9 run `0985c9e7544449eda8abe120a2f12512` also verified Redis DB 3 had 170 run-scoped dedupe markers and all four reservoir state keys contained this replay's state. All four Track B containers were stopped afterward; named volumes remain.

## G0 repair checkpoint — 2026-10-27

- Master task B02 (B6–B10) was claimable after B01/M1 dependencies and output-conflict checks; formal closeout is recorded with `done_with_caveats` because B9 verifies historical replay, not live operation. The B6–B10 acceptance evidence is recorded below and in the runbook.

- C3: **blocked / source confirmation required**. Source archive headers contain date-only values and no timezone. Replay producer uses Asia/Kolkata only as a provisional timestamp encoding and labels it `DEFAULT, to confirm`; consumer preserves that offset and derives source-calendar date keys from the encoded timestamp. See `MESSAGES.md` and `G0_REPAIR_EVIDENCE.md`.
- C4: Track B route DTOs now match AI route threshold/probability fields and numeric bounds. Integrator-owned OpenAPI files were not edited; proposed exact changes and severity/null/provenance mappings are in `G0_REPAIR_EVIDENCE.md`. Integrator review remains outstanding.
- C5: AI `/layers` now returns catalogued CRS, target SRID, loaded count, source hash/URL provenance, licence note, vintage, known units, zoom only for evidenced MVT function families, explicit NoData status, and `tile_endpoint_available=false`. No HTTP tile route is claimed. Fields absent from catalog evidence remain null/empty/explicitly unavailable.
- C6: JSONL-to-PostgreSQL serialization mapping is documented in `G0_REPAIR_EVIDENCE.md` and compatible with the Track B/twin SQL types and null behavior. The isolated live run verified actual writes; shared database unchanged. Integrator freeze review remains outstanding.


## Prerequisite recheck — 2026-10-25

- The four exact Track B Docker images were present locally before runtime; tags are listed in the runbook. No pull was performed.
- Installed clients verified in `.venv`: redis 8.1.0, confluent-kafka 2.16.0, prometheus-client 0.26.0.
- Docker daemon and image availability were checked without printing environment values or rendered Compose configuration.
- At the 2026-10-25 prerequisite checkpoint, migration 100 was unapplied. It is now applied only to `twinguard_trackb_test`; no shared database write was authorized or performed.

- 2026-10-25 fresh read-only B9 preflight recheck: shared DB twinguard, role twinguard_app, still no CREATEDB/superuser; 14 migrations, PostGIS installed, zero migration-100 tables. Fresh isolated candidate twinguard_trackb_test_20261025_5e49babb2e is absent. No create/migration/write attempted. Await DBA provisioning of a new empty PostGIS database with role ownership scoped to that DB; B9 stays blocked.


## B9 isolated persistence recheck — 2026-10-27

- Fail-closed target verification used an explicit database override from the configured role: effective database exactly `twinguard_trackb_test`, role `twinguard_app`, database owner `twinguard_app`, PostGIS enabled, and no application tables/migration ledger before setup (apart from PostGIS `public.spatial_ref_sys`).
- Applied only `001_core_schema.sql`, `005_stage5_complementary_tables.sql`, `010_create_twin_schema.sql`, and `100_trackb_twin_link.sql` to the isolated target. The normal migration runner was not used because it reads `.env` and applies every migration. Verified all four ledger entries and Track B alert, link, marker, reservoir-state, alert, and reservoir relations.
- Database persistence replay run `b9db-749826c9199986d1` used the real Track B event generator, processor, and persistence adapter with local Redis/Kafka fakes because Docker was unavailable. All 120 generated input events were accepted; 60 reservoir-state rows, 60 recompute markers, 50 alert event rows, 50 alert links, and 50 `twin.alerts` rows were observed. Alert levels: 31 Warning, 16 Watch, 3 Critical. Reprocessing the same run produced the same row counts (idempotent). This is database persistence/processor evidence, not a Kafka runtime replay.
- Shared DB read-only check after persistence: `twinguard` still has 14 migrations; migration-100 alert, link, and marker tables remain absent. No shared writes were performed.
- Quiet Compose configuration validation passed. Docker daemon was unavailable, so no services, Kafka replay, consumer offsets/lag, or current Prometheus scrape were verified. Previously documented data-plane run `e38099ac743d47ccb69980c9b7cea0ef` remains historical evidence, not this persistence run.
- At the persistence-only checkpoint before the Kafka runtime replay, focused tests had 21 passes and full suite 124 passes. The later 2026-10-27 completion results are recorded below.
- The prior 2026-10-27 persistence-only checkpoint was incomplete pending actual Kafka/Redis/Prometheus runtime replay; that blocker was cleared by the end-to-end evidence below.


## B9/B10 Kafka and isolated database completion — 2026-10-27

- Docker daemon `29.8.2`; four required local images verified; quiet Compose validation passed. Only the four named Track B services were started and reached healthy.
- Isolated DB guard immediately before consumer setup confirmed exact database `twinguard_trackb_test`, role/owner `twinguard_app`, PostGIS enabled, and migration 100 recorded. The consumer's opt-in persistence path rechecks the fixed database name, extension, migration record and required table before creating a run row. No shared DB connection was used for writes.
- Replay run `a68fb84f09bb4d1e80517e8eab42d25f`, source `replay`, window 2015-11-20 through 2015-12-04. Initial producer: 120 sent and 120 acknowledged. A same-run idempotency pass also sent/acknowledged 120. Kafka scan found 120 records each on rain and reservoir topics (60 distinct IDs per topic due to deliberate duplicate pass) and 50 alert records (50 distinct IDs).
- Consumer metrics counted 60 rain + 60 reservoir + 50 alerts = 170 unique processed messages, 31 Warning / 16 Watch / 3 Critical alerts, zero rule-engine errors, 170 latency observations, sum 207.618582 seconds (mean 1.2212858 seconds). Duplicate inputs were deduplicated. Redis DB 3 had 170 run-scoped processed markers, four reservoir states, four storage-history keys, four current-alert keys and four latest-rain keys.
- Kafka consumer group `trackb-b9-a68fb84f09bb4d1e80517e8eab42d25f` reached log end with lag 0 on five nonempty partitions; three empty partitions had no committed offset. Prometheus target `host.docker.internal:8000` reported up=1 during the run.
- Isolated DB for this run: one state-run record, 60 `twin.reservoir_state`, 60 recompute markers, 50 `trackb.alert_events`, 50 idempotency links and 50 `twin.alerts`; all source labels are replay. Alert levels match consumer metrics. DB counts remained unchanged after the duplicate replay. Prior persistence-only attempt records are retained and were not deleted.
- Read-only shared DB post-check: `twinguard` has 14 migrations; `trackb.alert_events`, `twin.trackb_alert_links`, and `twin.trackb_recompute_markers` remain absent. No shared DB write or migration occurred.
- B10 stop-only succeeded. All four Track B containers are exited and all four volumes (`tiwnguard_trackb-{redis,kafka,prometheus,grafana}-data`) are present. Volumes were not deleted or cleaned; they retain this runtime's replay/broker/metrics data.
- Verification: focused Track B tests 22 passed (one existing Starlette/httpx warning); Python compilation passed. Default `pytest -q` collection hit the unrelated module-name collision between `tests/explainability/test_analysis.py` and `tests/trackb/test_analysis.py`; `pytest -q --import-mode=importlib` passed 133 tests with one existing deprecation warning. Raw audit: 157 files, 30,544,672,450 bytes, all 157 hash matches, zero no-hash files, zero mismatches.
