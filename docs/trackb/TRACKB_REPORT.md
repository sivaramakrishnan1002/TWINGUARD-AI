# Track B final report

| Task | Result | Files | Key evidence / numbers | Defaults | Blocked | Top risks |
|---|---|---|---|---|---|---|
| B1 | Done: source coverage audit | AUDIT_AND_BACKTEST.md, BACKTEST_RESULTS.json | Kaggle daily storage/rain: four reservoirs × 6,182 dates, 2004-01-01–2020-12-03; OpenCity monthly series coverage and gaps; 2,164 matched rain-comparison dates in 2015–2020 | Rain depth scale marked INFERRED | Full-year local IMERG not available | Kaggle rain unit not authoritative; published capacities vary |
| B2 | Done: parameterized future-storage target | AUDIT_AND_BACKTEST.md, SENSITIVITY.csv | All 45 entity × horizon × fraction combinations (5 entities × 3 × 3) | DEFAULT, to confirm: N=7, fraction=.80 | None for derived storage target | Target is not flood/release truth; capacity assumptions |
| B3 | Done with caveats: rule + probabilistic comparators | analysis.py, BACKTEST_RESULTS.json | Earlier training 2004–14; calibration 2015–17; test 2018–20; train/calibration boundaries purged by N | Threshold indicators at 70/80/90%; learned rise/rain cutoffs | No flood-outcome model possible from these labels | Target-specific model; only 3 held-out year clusters |
| B4 | Done with caveats: storage-target backtest | BACKTEST_REPORT.md, BACKTEST_RESULTS.json | POD/FAR/CSI per reservoir and combined, event lead times, 300 year-block bootstrap replicates, reliability bins, persistence/rain-only baselines; 2015 case separate | Seed 29 | 2021/2023 daily storage resolution unavailable | Rare targets create undefined or unstable metrics; not flood-warning validation |
| B5 | Done: versioned JSONL and accelerated replay | MESSAGES.md, replay.py, persistence.py, replay_2015_alerts.jsonl | 50 replay-labeled alerts for 2015-11-20–2015-12-04; no DB writes | Rule confidence is evidence fraction, not probability | DB replay requires migration 100 applied | Replay is not live |
| B6 | Done: Compose overlay and runbook authored | docker-compose.trackb.yml, RUNBOOK.md | Track B profile, loopback bindings, quiet validation pass; four expected local tags verified | Exact tags in runbook | None for config/health | Credential value private; never display merged configuration |
| B7 | Done: topics, producer/consumer and Redis processing implemented | pipelines/trackb/streaming.py, tests/trackb/test_streaming.py | B9 replay producer/consumer reconciled 60 rain and 60 reservoir unique input IDs; duplicate inputs suppressed | — | None for replay data plane | Replay is not live |
| B8 | Done: metrics endpoint and provisioned dashboard authored | pipelines/trackb/metrics.py, pipelines/trackb/streaming.py, services/trackb/, tests/trackb/ | B9: 170 unique messages, 50 alerts, zero errors, 170 latency observations; Prometheus target up | — | None for replay scrape | Replay is not live |
| B9 | Done: replay data plane and isolated DB persistence verified | RUNBOOK.md | Run `a68fb84f09bb4d1e80517e8eab42d25f`: 120/120 producer acknowledgements per pass; 170 unique consumed, 50 alerts, zero errors; 60 states, 60 markers, 50 alert events/links/twin alerts; idempotent repeat; zero lag on nonempty partitions; Prometheus up. | REPLAY, isolated database | None for recorded replay acceptance | Historical replay only; not live monitoring validation |
| B10 | Done: stop and preserve | RUNBOOK.md | Stop-only succeeded after successful data-plane replay; all four services exited; all four volumes present | Never remove volumes | None for stop check | Volumes retained |
| B11 | Done: idempotent twin persistence authored and isolated-tested | migration 100, persistence.py | Isolated migration and persistence run verified; key normalization aligns replay identifiers with migration-010 reservoir keys | — | Migration 100 remains unapplied to shared DB | Needs valid twin run_id for reservoir states |
| B12 | Done: read-only API and tests | services/trackb/router.py, tests/trackb/test_router.py | 5 GET endpoints; adapter injected; focused route coverage | Source envelope marked replay | Not mounted in host application | No connected read adapter |
| B13 | Done: report and architecture docs | TRACKB.md, DIAGRAM.md, REALTIME_DESIGN.md, this report | Replay/live/simulated separated; no-release and post-2020 limits stated | — | B9 replay complete; current evidence and limits are recorded below | Runtime claims use recorded evidence only |

## Final status

Parts 1 and 3 have evidence-backed implementation. The B3/B4 target is **future reservoir storage threshold attainment**, derived from daily observations using current published capacities as assumptions. It does not represent flood occurrence or release decisions. The 2015 event screen is reported separately and remains exploratory. B7/B8 checks pass. B9 completed on 2026-10-27: run `a68fb84f09bb4d1e80517e8eab42d25f` reconciled Kafka, Redis, consumer metrics, Prometheus scrape and isolated DB persistence, including a same-run idempotency pass. B10 stop-only succeeded and all named volumes remain present. Migration 100 is applied only to isolated `twinguard_trackb_test` and remains absent from shared `twinguard`; shared writes remain prohibited. All runtime results are REPLAY, not live operation.

The earlier Compose validation printed a credential from the main compose file. Its value was not repeated. The user confirmed it has not been rotated and plans to change it later; external exposure remains unverified. The config was not revalidated, and no change to the main compose file or `.env` was made by Track B work.

B7 focused tests: 12 passed at the B7 checkpoint; B8 checkpoint: 16 passed. Latest Track B suite: 22 passed and compilation passed. Latest full suite using pytest importlib mode: 133 passed, one existing Starlette/httpx warning; default collection reports the separate explainability/Track B `test_analysis` module-name collision. Latest raw audit: 157 files / 30,544,672,450 bytes, 157 hash matches, 0 mismatches. GPU compute was not needed. No package installs, image pulls, or raw-data writes were performed.

Track B files are committed in scoped commits; unrelated worktree changes remain unstaged. The latest Track B commit contains only Track B-owned paths: `database/migrations/100_trackb_twin_link.sql`, `docker-compose.trackb.yml`, `docs/batches/TRACKB.md`, `docs/trackb/`, `pipelines/trackb/`, `requirements-trackb.txt`, `services/trackb/`, `tests/trackb/`. Exclude `requirements.txt` and all other-session paths.




## Runtime prerequisite recheck — 2026-10-25

The four exact image tags are present locally: `redis:8.10.2-alpine`, `apache/kafka:4.3.2`, `prom/prometheus:v3.13.2`, and `grafana/grafana:13.2.2-ubuntu`. Installed `.venv` clients are redis 8.1.0, confluent-kafka 2.16.0, and prometheus-client 0.26.0. No pull or package install was performed. Migration 100 is still unapplied; DB persistence is not claimed.

## B9/B10 runtime evidence — 2026-10-25

Failure diagnosis: the consumer called synchronous Kafka watermark queries (up to one second per assigned partition) after every poll, starving consumption; it also counted `OFFSET_INVALID` (-1001) as a real offset, inflating lag. The fix uses cached watermarks and skips uninitialized offsets. Delivery failure also clears the Redis dedupe marker before retry, preventing a failed alert publish from being silently suppressed on redelivery. Regression coverage was added.

Run `e38099ac743d47ccb69980c9b7cea0ef` was processed as REPLAY. The producer sent and received broker acknowledgements for 120 events (60 rain and 60 reservoir). Kafka scan verified those 120 run-tagged inputs and 50 generated run-tagged alert records. Consumer metrics processed 170 messages total (60 rain, 60 reservoir, 50 alert), with zero rule errors. Alert metrics counted 31 Warning, 16 Watch and 3 Critical. The consumer group assigned eight partitions; five non-empty partitions committed through their log ends with lag 0, and three empty partitions had no committed offset.

Redis logical DB 3 contained 120 input dedupe markers, four reservoir-state keys, four current-alert keys (current level Warning for each), and four latest-rain keys. Metrics reported 170 processed messages, 50 alerts, 0 errors, 170 latency observations, sum 175.269548 seconds (mean 1.030997 seconds), and zero active-partition lag. Prometheus reported the consumer target up during the run.

At the 2026-10-25 preflight checkpoint, B9 was blocked because no authorized isolated database was available; migration 100 was unapplied then and no database writes had been made. The subsequent isolated persistence and Kafka runtime evidence below supersedes that checkpoint. No shared database was touched.

## Isolated database preflight — 2026-10-25

A read-only connection confirmed the configured database is the shared project database `twinguard`. The shared database has 14 migration records; migration 100 and the three Track B target tables are absent. PostgreSQL 18 is reachable locally; PostGIS is installed in the shared database and available on the server. Candidate `twinguard_trackb_test_20261025_29c98e7b46` was confirmed unused but not created; recheck before use. The configured database role has neither `CREATEDB` nor superuser permission.

At that 2026-10-25 preflight checkpoint, no database was created, no migration was applied, and no database write was attempted. The shared database was queried read-only only. At that historical checkpoint, the next action was for an authorized DBA to provision a fresh isolated database with PostGIS and scoped role ownership. No privilege change on shared `twinguard` is needed or requested. This was the blocker at the 2026-10-25 checkpoint; it was cleared after the DBA provisioned the test database as recorded below.

The minimum schema dependency chain identified is migrations 001 (base PostGIS-backed tables), 005 (`twinguard.observation_records`), 010 (twin state, reservoirs and alerts), then 100 (Track B persistence tables). Migration 010 seeds reservoir identities from source observation records, so the isolated target's seed/fixture requirements must be confirmed before replay. The existing migration runner is not safe for this task: it reads the shared `.env` target and applies all SQL migrations without a target or selection option.

B10 stop-only returned success after this rerun. All four Track B services are exited and the four named volumes remain present. No volumes were deleted. All values above are REPLAY, never live. The credential remains unrotated by the user's choice; its value is not included here.

## B9 isolated-database preflight recheck — 2026-10-25

A fresh read-only transaction confirmed the configured connection still targets shared database `twinguard` as role `twinguard_app`. The role has neither `CREATEDB` nor superuser capability. Shared migration count remains 14; PostGIS is installed there; all three Track B migration-100 tables remain absent. Fresh candidate `twinguard_trackb_test_20261025_5e49babb2e` does not exist. No database was created, no migration was applied, and no write was attempted. The shared database was queried read-only.

**Required action:** an authorized DBA must provision a fresh, empty, uniquely named isolated PostgreSQL database, install PostGIS there, and assign `twinguard_app` ownership or equivalent privileges scoped only to that new database. Do not change privileges on or write to `twinguard`. After provisioning, recheck the target name and database identity before migration or replay.


## B9 isolated persistence recheck — 2026-10-27

The database target was explicitly overridden from configured credentials and verified read-only as `twinguard_trackb_test`; role/owner were `twinguard_app`, PostGIS was enabled, and the database was fresh except for PostGIS metadata. Only migrations `001_core_schema.sql`, `005_stage5_complementary_tables.sql`, `010_create_twin_schema.sql`, and `100_trackb_twin_link.sql` were applied. The `.env` migration runner was not used.

For replay run `b9db-749826c9199986d1`, the real Track B generator and processor accepted 120 events. Persistence evidence: 60 `twin.reservoir_state`, 60 recompute markers, 50 `trackb.alert_events`, 50 idempotency links, and 50 `twin.alerts`; levels were 31 Warning, 16 Watch, and 3 Critical. A second processing pass left counts unchanged. Local fakes stood in for Kafka and Redis, so this proves database persistence and processor behavior only, not runtime broker delivery.

Afterward, shared `twinguard` was checked read-only: migration count remained 14, and the migration-100 alert/link/marker tables remained absent. Quiet Compose validation passed, but Docker daemon was unavailable; no service start, Kafka offsets/lag, or Prometheus scrape was obtained in this turn. This 2026-10-27 persistence-only checkpoint was incomplete until the later Kafka/Redis/Prometheus replay below. It has since been completed. B10 stop/volume evidence is recorded below; no volume was deleted.

At this preceding persistence-only checkpoint: focused tests 21 passed, compilation passed, full suite 124 passed, and raw audit had 157 matching hashes. See the later end-to-end completion section for final checks.


## B9 end-to-end replay and B10 stop — 2026-10-27

Docker Desktop server 29.8.2 was reachable. All four exact images were local, quiet Compose validation passed, and only the named Track B services were started; all four reached healthy. Before starting the persistent consumer, the database override was rechecked as exactly `twinguard_trackb_test`, owned by `twinguard_app`, with PostGIS and migration 100 present. The consumer's opt-in database adapter refuses any other current database and requires the isolated schema prerequisites before writing.

Replay `a68fb84f09bb4d1e80517e8eab42d25f` processed the documented 2015-11-20–2015-12-04 window. The producer sent and received acknowledgements for 120 messages, then another 120 on an intentional same-run idempotency pass. Kafka scan found 120 rain records / 60 distinct IDs, 120 reservoir records / 60 distinct IDs, and 50 generated alert records / 50 distinct IDs. The consumer processed 60 rain + 60 reservoir + 50 alert messages (170 unique total); duplicate replay inputs were suppressed. Alerts: 31 Warning, 16 Watch, 3 Critical. Rule errors: 0. Latency: 170 observations, sum 207.618582 s, mean 1.2212858 s.

Redis DB 3 contained 170 run-specific processed markers and four each of reservoir state, storage history, current alert, and latest rain keys. The isolated database contains one run row, 60 reservoir-state rows, 60 recompute markers, and 50 each of alert-event, idempotency-link, and twin-alert rows, all linked to this replay run and source-labeled replay. Repeating the same run did not change these row counts. Kafka committed offsets reached log ends with zero lag on five nonempty partitions; three empty partitions had invalid/uncommitted offsets. Prometheus reported `host.docker.internal:8000` up=1 during the run.

Post-run read-only confirmation: shared `twinguard` remains at 14 migration records and has none of the migration-100 Track B tables. The four Track B services were stopped with `docker compose ... stop`; all show exited. The four named volumes remain present. No volume cleanup or deletion was run; the volumes retain runtime data from this replay.

Focused Track B suite: 22 passed, one existing deprecation warning. Compilation passed. Default full-suite collection failed on a pre-existing cross-directory `test_analysis` module-name collision involving `tests/explainability/`; no other-lane files were changed. Full suite with `--import-mode=importlib`: 133 passed, one existing deprecation warning. Raw audit: 157 files, 30,544,672,450 bytes, 157 matches, 0 without comparable hashes, 0 mismatches.
# G0 repair and fresh B9 verification — 2026-10-27

Track B-owned repairs and the requested fresh runtime verification were performed without changing `docs/master/`, master API contracts, Lane A paths, shared `requirements.txt`, or the main Compose file. Repository index was empty before the work; unrelated dirty paths were preserved.

- **C3:** raw source archive contains date-only CSV headers and no timezone metadata. Historical timezone remains unconfirmed. Producer/consumer timestamp semantics agree as documented in `MESSAGES.md`; no timezone was inferred from observations.
- **C4:** Java route request/response DTOs now include the AI threshold and optional route accessibility probability with `[0,1]` bounds. The exact requested changes to Integrator-owned OpenAPI contracts, plus null/NoData, provenance, source, severity mapping, and HTTP semantics, are proposed in `G0_REPAIR_EVIDENCE.md`; master API specs were not edited.
- **C5:** Track B-owned AI layer catalogue exposes evidence-backed metadata and explicitly marks unavailable metadata and the absent HTTP tile endpoint. No tile URL was invented.
- **C6:** JSON Lines / PostgreSQL JSONB and twin column mapping, timestamps, units, source, idempotency, and null semantics are documented. Live isolated writes passed; shared DB remained unchanged.
- **Fresh B9 replay:** Docker Linux daemon 29.8.2; four expected images local; quiet Compose validation passed. Read-only preflight positively verified exact target `twinguard_trackb_test`, PostGIS, migration 100; shared `twinguard` was separately read-only checked. No migrations were applied.
- Producer pass 1 and idempotency pass 2 each sent and received Kafka acknowledgements for 120 events. Run-specific Kafka scan found 120 rain rows / 60 unique event IDs, 120 reservoir rows / 60 unique IDs, and 50 generated alert rows / 50 unique IDs. Consumer processed 60 rain + 60 reservoir + 50 alert messages = 170 unique events; 31 Warning, 16 Watch, 3 Critical; no rule-error series was emitted (zero recorded errors); 170 latency samples totaled 142.850667 seconds (mean 0.840298 seconds).
- Kafka consumer group `trackb-b9-0985c9e7544449eda8abe120a2f12512` reached log end: zero lag for all five nonempty partitions; three empty partitions had no committed offsets. Prometheus scraped `host.docker.internal:8000` successfully (`up`) during the replay.
- Isolated database `twinguard_trackb_test`, state run ID 5: 60 reservoir-state rows across four reservoir keys, 60 replay recompute markers, 50 replay alert events, 50 idempotency links, and 50 corresponding `twin.alerts` rows; severities match consumer metrics. Repeated input records resulted in one persisted row per event/day and one state per key/day, confirming idempotency. No non-replay rows were observed for this run.
- Shared `twinguard` read-only check: 14 migration records; migration 100 absent; Track B alert/link/marker tables absent. B10 stop-only succeeded; four Track B services stopped and all four named volumes remain present. No volume deletion or cleanup command ran. Retained volumes contain replay data.
- C3 remains blocked pending authoritative timezone confirmation; C4 and C6 require Integrator contract/freeze review. B9 live E2E acceptance passed for this replay. C5 does not expose a serving HTTP tile endpoint.
- Verification after these repairs: focused Track B + AI-service tests **35 passed**; Python compilation passed; backend `mvn -q test` passed; full Python suite `pytest -q --import-mode=importlib` **137 passed**, one existing Starlette/httpx deprecation warning. Raw audit **157 files / 30,544,672,450 bytes / 157 hash matches / 0 missing comparable hashes / 0 mismatches**.
