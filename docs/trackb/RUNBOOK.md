# Track B runbook

## Verified local prerequisites

Checked 2026-10-25: all four required image references are present locally; no image pull was performed. Existing `.venv` client pins are redis 8.1.0, confluent-kafka 2.16.0, and prometheus-client 0.26.0. No package installation is needed.

Use these exact local image assignments if overriding the overlay defaults:

```powershell
$env:TRACKB_REDIS_IMAGE = 'redis:8.10.2-alpine'
$env:TRACKB_KAFKA_IMAGE = 'apache/kafka:4.3.2'
$env:TRACKB_PROMETHEUS_IMAGE = 'prom/prometheus:v3.13.2'
$env:TRACKB_GRAFANA_IMAGE = 'grafana/grafana:13.2.2-ubuntu'
```

## Validate and start only Track B

The validation command suppresses all output and prints only its exit result. Never print rendered Compose configuration.

```powershell
docker compose -f docker-compose.yml -f docker-compose.trackb.yml --profile trackb config --quiet
```

Start only the four named Track B services (do not omit the service list, which could start unprofiled services from the base file):

```powershell
docker compose -f docker-compose.yml -f docker-compose.trackb.yml --profile trackb up -d trackb-redis trackb-kafka trackb-prometheus trackb-grafana
docker compose -f docker-compose.yml -f docker-compose.trackb.yml --profile trackb ps
```

Ports published by the overlay are loopback-only: Redis 6380, Kafka 9092, Prometheus 9090, Grafana 3001. Track B consumer metrics bind to `127.0.0.1:8000`; the Prometheus target is `host.docker.internal:8000`. Scrape reachability must be checked at runtime and is not implied by configuration.

## Run the consumer and REPLAY

In a separate terminal, use a fresh replay consumer group and an isolated Redis logical database for the B9 run. `latest` starts this new group at the current topic end, avoiding pre-existing retained records. The consumer still reads generated alerts produced after the replay begins.

```powershell
$runId = [guid]::NewGuid().ToString('N')
$env:TRACKB_KAFKA_BOOTSTRAP_SERVERS = '127.0.0.1:9092'
$env:TRACKB_CONSUMER_GROUP = "trackb-b9-$runId"
$env:TRACKB_AUTO_OFFSET_RESET = 'latest'
$env:TRACKB_REDIS_URL = 'redis://127.0.0.1:6380/3'
.\.venv\Scripts\python.exe -m pipelines.trackb.streaming consume --persist-isolated-db --replay-run-id $runId
```

In another terminal, produce the historical replay window at full speed; records are marked `source: replay`:

```powershell
.\.venv\Scripts\python.exe -m pipelines.trackb.streaming replay --start 2015-11-20 --end 2015-12-04 --run-id $runId
```

Inspect local metrics at `http://127.0.0.1:8000/metrics`, Prometheus at `http://127.0.0.1:9090`, and Grafana at `http://127.0.0.1:3001`. Record actual topic counts, consumed messages, alert counts, errors, latency and Prometheus target health. These are REPLAY results, never live data.

## Database boundary

Do not apply migration 100 or write to the shared project database. The default consumer has no database connection. For an authorized integration run, `--persist-isolated-db --replay-run-id $runId` opts into the fixed `twinguard_trackb_test` target; startup overrides only the database name while taking host/role credentials from the configured environment, then verifies `current_database()`, PostGIS, migration 100, required tables, and reservoir fixtures before creating the run record. The adapter fails closed on any target mismatch. Never target shared `twinguard`.

## Runtime attempt and verified data plane — 2026-10-25

The first B9 run was stopped before draining: the consumer did synchronous per-partition Kafka watermark requests after every poll, and invalid uninitialized offsets inflated the reported lag. The code now uses cached watermarks and skips invalid positions. Use a fresh unique consumer group, Redis DB 3, and a unique replay run ID as shown above.

Verified run `e38099ac743d47ccb69980c9b7cea0ef`: producer sent/acknowledged 120 events (60 rain + 60 reservoir); consumer processed 170 total (60 rain + 60 reservoir + 50 alert events); zero rule errors; 50 alerts (31 Warning, 16 Watch, 3 Critical). Redis DB 3 had 120 input markers, four reservoir states, four current-alert keys and four latest-rain keys. Five non-empty Kafka partitions committed to their log ends with zero lag; three empty partitions had no committed offset. Prometheus target was up during the consumer run. Metrics recorded 170 latency observations, 175.269548 seconds total (mean 1.030997 seconds), and zero active-partition lag. All records are REPLAY.

At the 2026-10-25 checkpoint, B9 database persistence was unverified because no isolated database had been identified; migration 100 was unapplied and no DB writes had been attempted. This historical blocker was resolved by the DBA-provisioned isolated database and the completion evidence below.

B10 stop-only returned success. All four Track B containers are exited and all four named volumes remain present.

## Isolated database preflight — 2026-10-25

The read-only preflight resolved the configured database name to the shared project database `twinguard`; no connection values or credentials were displayed. PostgreSQL 18 is reachable locally and PostGIS is installed in the shared database and available on the server. The shared migration ledger contains 14 records; migration 100 is absent, and all three Track B target tables are absent. Candidate `twinguard_trackb_test_20261025_29c98e7b46` was confirmed absent but was not created; recheck before any future use.

The configured database role has neither `CREATEDB` nor superuser permission. No database was created, no migration was applied, and no write was attempted. The shared database was only queried in read-only mode. At that historical checkpoint, the required action was DBA provisioning of a fresh isolated database with PostGIS and scoped role ownership. This was later completed; do not change privileges on or write to `twinguard`.

Migration prerequisites identified from the checked-in SQL: migration 001 creates the base PostGIS-backed `twinguard` tables; migration 005 creates `twinguard.observation_records`; migration 010 creates `twin.reservoirs`, `twin.reservoir_state`, and `twin.alerts`; migration 100 adds Track B tables and foreign keys to the twin tables. Migration 010 seeds reservoir identities from observation records. The existing `pipelines.stage5.apply_migrations` runner always targets the `.env` database and applies every SQL migration in order, so it is unsafe for this isolated verification and must not be used. Only a database-specific, selected-migration procedure may be used after the isolated database is provisioned and its source-data/fixture prerequisites are confirmed.

## Stop and preserve volumes

After runtime checks, stop only Track B services. Never run `down`, `down -v`, prune, or a volume deletion command.

```powershell
docker compose -f docker-compose.yml -f docker-compose.trackb.yml --profile trackb stop trackb-redis trackb-kafka trackb-prometheus trackb-grafana
docker compose -f docker-compose.yml -f docker-compose.trackb.yml --profile trackb ps
docker volume ls --filter label=com.docker.compose.volume=trackb-redis-data --format '{{.Name}}'
docker volume ls --filter label=com.docker.compose.volume=trackb-kafka-data --format '{{.Name}}'
docker volume ls --filter label=com.docker.compose.volume=trackb-prometheus-data --format '{{.Name}}'
docker volume ls --filter label=com.docker.compose.volume=trackb-grafana-data --format '{{.Name}}'
```

The previous credential exposure risk is accepted by the user for this run. Do not copy, display, or log any credential; keep Compose output suppressed.

## B9 isolated-database preflight recheck — 2026-10-25

A fresh read-only transaction confirmed the configured connection still targets shared database `twinguard` as role `twinguard_app`. The role has neither `CREATEDB` nor superuser capability. Shared migration count remains 14; PostGIS is installed there; all three Track B migration-100 tables remain absent. Fresh candidate `twinguard_trackb_test_20261025_5e49babb2e` does not exist. No database was created, no migration was applied, and no write was attempted. The shared database was queried read-only.

**Required action:** an authorized DBA must provision a fresh, empty, uniquely named isolated PostgreSQL database, install PostGIS there, and assign `twinguard_app` ownership or equivalent privileges scoped only to that new database. Do not change privileges on or write to `twinguard`. After provisioning, recheck the target name and database identity before migration or replay.


## B9 isolated persistence verification — 2026-10-27

The DBA target was positively verified before writes: explicit target `twinguard_trackb_test`, configured role and database owner `twinguard_app`, PostGIS enabled, and no application schema/migration ledger before setup (other than PostGIS metadata). The general migration runner must not be used because it reads `.env` and applies every migration. Only the required chain `001_core_schema.sql`, `005_stage5_complementary_tables.sql`, `010_create_twin_schema.sql`, `100_trackb_twin_link.sql` was applied to the isolated target; ledger and expected Track B tables were verified. The configured connection values were never displayed.

Persistence run `b9db-749826c9199986d1` used real Track B generated REPLAY events and the Track B processor/persistence adapter, with local fakes replacing Redis and Kafka. It accepted 120 inputs and persisted 60 states, 60 recompute markers and 50 alerts/links (31 Warning, 16 Watch, 3 Critical). Reprocessing the same input left counts unchanged. This procedure validates persistence/idempotency, not Kafka delivery or Prometheus runtime.

A read-only post-check confirmed shared `twinguard` remains at 14 migrations and has no migration-100 tables. Compose quiet validation passed; Docker daemon was unavailable, so no runtime services were started. Re-run the full Kafka/Redis/Prometheus replay once the Docker daemon is available; do not use the existing `.env` migration runner.


## B9/B10 completed replay evidence — 2026-10-27

Replay ID `a68fb84f09bb4d1e80517e8eab42d25f`, window 2015-11-20 through 2015-12-04. Verify the consumer group is stable and assigned the rain, reservoir, twin, and alert topics before starting the producer when using `latest` offset reset. Initial producer sent/acked 120 messages. Same-run repeat sent/acked another 120 to verify idempotency. Kafka held 120 records per rain/reservoir topic (60 distinct event IDs each) and 50 generated alert records (50 distinct IDs).

The persistent consumer processed 170 unique messages: 60 rain, 60 reservoir, 50 alert. Alert levels were 31 Warning, 16 Watch, 3 Critical; rule errors 0. It observed 170 latency samples (207.618582 seconds total, 1.2212858 seconds mean). Redis DB 3 had 170 run-scoped processed markers and four keys each for reservoir state, storage history, current alert, and latest rain. Kafka lag was zero on five nonempty partitions; three empty partitions had no committed offset. Prometheus target `host.docker.internal:8000` was up=1.

The isolated target `twinguard_trackb_test` has migration records 001, 005, 010, and 100. This run persisted 60 reservoir-state rows, 60 recompute markers, and 50 rows each in `trackb.alert_events`, `twin.trackb_alert_links`, and `twin.alerts`. Repeating the run did not increase any of these counts. Shared `twinguard` remained at 14 migrations with migration-100 tables absent.

Stop-only succeeded; all four Track B services exited and all four named volumes remain present. Volumes were not deleted or cleaned. The runtime replay leaves data in those volumes. Focused tests 22 passed; compile passed; default full-suite collection reported the explainability/Track B `test_analysis` module-name collision; `pytest -q --import-mode=importlib` passed 133 tests. Raw audit: 157 files, 30,544,672,450 bytes, 157 matches, 0 unavailable comparable hashes, 0 mismatches.

## Fresh G0 repair replay — 2026-10-27

Fresh run ID: `0985c9e7544449eda8abe120a2f12512` (source `replay`, 2015-11-20 through 2015-12-04). Docker daemon was Linux 29.8.2; four expected image refs were local and `docker compose ... config --quiet` passed. Before writes, a read-only connection reported exact effective DB `twinguard_trackb_test`, PostGIS enabled, and migration 100 present. The configured shared DB `twinguard` was separately read-only checked; no migrations or writes were issued there. No migration was reapplied.

Producer pass 1: 120 sent, 120 acknowledged. Producer pass 2 (same run ID): 120 sent, 120 acknowledged. A scan to partition EOF found this run's 120 rain records (60 unique IDs), 120 reservoir records (60 unique IDs), and 50 alert records (50 unique IDs). The consumer processed 60 rain + 60 reservoir + 50 alert events (170 total); severity counts were 31 Warning, 16 Watch, 3 Critical. No rule-error samples were recorded. Latency: 170 samples, 142.850667 seconds total, 0.840298 seconds mean.

Consumer group `trackb-b9-0985c9e7544449eda8abe120a2f12512` had zero lag at log end for five nonempty partitions; three empty partitions had no committed offsets. Metrics endpoint showed the source/topic message counters, severity counters, zero errors, 170 latency observations, and zero active lag. Prometheus target `host.docker.internal:8000` was healthy during the run.

Persistence in `twinguard_trackb_test` (state run ID 5): 60 `twin.reservoir_state` rows across four reservoir keys; 60 recompute markers; 50 `trackb.alert_events`; 50 `twin.trackb_alert_links`; and 50 corresponding `twin.alerts`. All persisted source labels were replay and severity totals matched consumer metrics. Duplicate producer records were deduplicated; one state per reservoir/day and one alert per event ID were persisted.

Redis DB 3 was checked after the consumer stopped by starting only the named Track B Redis service, reading without mutation, and stopping it again: 170 run-scoped processed markers and all four reservoir state keys contained this replay's run-scoped replay state. No unrelated services were started.

Shared DB post-check was read-only: `twinguard` remains at 14 migration records, migration 100 is absent, and Track B alert/link/marker tables are absent. Stop-only succeeded; Redis, Kafka, Prometheus, and Grafana Track B services are stopped. All four named Track B volumes remain present and retain runtime data; no volume removal/cleanup was performed.

## G0 repair handoff

- Historical reservoir timezone is not established by the date-only source. Continue to preserve `DEFAULT, to confirm`; do not infer timezone from values. Producer/consumer semantics are in `MESSAGES.md`.
- Track B DTO/API proposal, metadata limitations, and twin serialization mapping are in `G0_REPAIR_EVIDENCE.md`. Integrator must review/apply proposed OpenAPI changes; no Integrator-owned contract was edited.
- The `/layers` catalogue is metadata only. Migration 002 has database MVT functions for selected families and zoom 0–22, but no HTTP tile endpoint exists; do not advertise one.
- Post-repair checks: focused Track B + AI-service tests 35 passed; Python compilation passed; backend `mvn -q test` passed; full suite `pytest -q --import-mode=importlib` 137 passed with one existing Starlette/httpx deprecation warning; raw audit 157 files / 30,544,672,450 bytes / 157 matches / 0 no comparable hashes / 0 mismatches.
