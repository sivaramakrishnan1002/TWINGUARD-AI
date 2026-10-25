# Track B final report

| Task | Result | Files | Key evidence / numbers | Defaults | Blocked | Top risks |
|---|---|---|---|---|---|---|
| B1 | Done: source coverage audit | AUDIT_AND_BACKTEST.md, BACKTEST_RESULTS.json | Kaggle daily storage/rain: four reservoirs × 6,182 dates, 2004-01-01–2020-12-03; OpenCity monthly series coverage and gaps; 2,164 matched rain-comparison dates in 2015–2020 | Rain depth scale marked INFERRED | Full-year local IMERG not available | Kaggle rain unit not authoritative; published capacities vary |
| B2 | Done: parameterized future-storage target | AUDIT_AND_BACKTEST.md, SENSITIVITY.csv | All 45 entity × horizon × fraction combinations (5 entities × 3 × 3) | DEFAULT, to confirm: N=7, fraction=.80 | None for derived storage target | Target is not flood/release truth; capacity assumptions |
| B3 | Done with caveats: rule + probabilistic comparators | analysis.py, BACKTEST_RESULTS.json | Earlier training 2004–14; calibration 2015–17; test 2018–20; train/calibration boundaries purged by N | Threshold indicators at 70/80/90%; learned rise/rain cutoffs | No flood-outcome model possible from these labels | Target-specific model; only 3 held-out year clusters |
| B4 | Done with caveats: storage-target backtest | BACKTEST_REPORT.md, BACKTEST_RESULTS.json | POD/FAR/CSI per reservoir and combined, event lead times, 300 year-block bootstrap replicates, reliability bins, persistence/rain-only baselines; 2015 case separate | Seed 29 | 2021/2023 daily storage resolution unavailable | Rare targets create undefined or unstable metrics; not flood-warning validation |
| B5 | Done: versioned JSONL and accelerated replay | MESSAGES.md, replay.py, persistence.py, replay_2015_alerts.jsonl | 50 replay-labeled alerts for 2015-11-20–2015-12-04; no DB writes | Rule confidence is evidence fraction, not probability | DB replay requires migration 100 applied | Replay is not live |
| B6 | Done: Compose overlay and runbook authored | docker-compose.trackb.yml, RUNBOOK.md | Track B profile, loopback bindings, quiet validation pass; four expected local tags verified | Exact tags in runbook | None for config/health | Credential value private; never display merged configuration |
| B7 | Done: topics, producer/consumer and Redis processing implemented | pipelines/trackb/streaming.py, tests/trackb/test_streaming.py | 12 focused tests at B7 checkpoint; B9 replay producer/consumer reconciled run-tagged events | — | Database integration separate from streaming | Migration 100 remains unapplied |
| B8 | Done: metrics endpoint and provisioned dashboard authored | pipelines/trackb/metrics.py, pipelines/trackb/streaming.py, services/trackb/, tests/trackb/ | 21 current focused tests; dashboard and endpoint checks; Prometheus target up in B9 run | — | DB write unverified | Unit tests/runtime scrape do not establish DB integration |
| B9 | Blocked: data plane verified; DB persistence unverified | RUNBOOK.md | Run e38099ac743d47ccb69980c9b7cea0ef: producer 120/120 acked; consumer 60 rain + 60 reservoir + 50 alerts; 50 alert outputs (31 Warning, 16 Watch, 3 Critical); errors 0; Redis DB 3 has 120 input markers, 4 states, 4 current-alert keys; committed partition lag 0; Prometheus up | REPLAY 2015-11-20–2015-12-04, unique run ID/group, Redis DB 3 | No authorized isolated DB identified; migration 100 unapplied; no writes attempted | Do not call B9 complete until authorized DB persistence evidence exists |
| B10 | Done: stop and preserve | RUNBOOK.md | Stop-only succeeded after successful data-plane replay; all four services exited; all four volumes present | Never remove volumes | None for stop check | Volumes retained |
| B11 | Done: idempotent twin persistence authored | migration 100, persistence.py | `trackb.alert_events`, `twin.alerts`, `twin.reservoir_state` upsert, recompute markers | — | Migration 100 unapplied; no database write run | Needs valid twin run_id for reservoir states |
| B12 | Done: read-only API and tests | services/trackb/router.py, tests/trackb/test_router.py | 5 GET endpoints; adapter injected; focused route coverage | Source envelope marked replay | Not mounted in host application | No connected read adapter |
| B13 | Done: report and architecture docs | TRACKB.md, DIAGRAM.md, REALTIME_DESIGN.md, this report | Replay/live/simulated separated; no-release and post-2020 limits stated | — | B9 remains blocked pending authorized database persistence evidence | Runtime claims use recorded B9 evidence only |

## Final status

Parts 1 and 3 have evidence-backed implementation. The B3/B4 target is **future reservoir storage threshold attainment**, derived from daily observations using current published capacities as assumptions. It does not represent flood occurrence or release decisions. The 2015 event screen is reported separately and remains exploratory. B7/B8 checks pass. The B9 data plane passed for the run-tagged replay and metrics/Redis/Kafka evidence reconciled, but B9 remains blocked because database persistence could not be checked in an authorized isolated database. B10 stopped Track B services and preserved volumes. Migration 100 remains unapplied and shared database writes remain prohibited.

The earlier Compose validation printed a credential from the main compose file. Its value was not repeated. The user confirmed it has not been rotated and plans to change it later; external exposure remains unverified. The config was not revalidated, and no change to the main compose file or `.env` was made by Track B work.

B7 focused tests: 12 passed at the B7 checkpoint; B8 checkpoint: 16 passed. After B9 diagnosis/fix, current Track B suite: 21 passed; changed Python modules compile. Full repository suite: 113 passed, 0 failed, one Starlette/httpx deprecation warning. Raw audit: 157 files / 30,544,672,450 bytes, 157 hash matches, 0 mismatches. GPU compute was not needed. No package installs, image pulls, or raw-data writes were performed.

Track B files are committed in scoped commits; unrelated worktree changes remain unstaged. The latest Track B commit contains only Track B-owned paths: `database/migrations/100_trackb_twin_link.sql`, `docker-compose.trackb.yml`, `docs/batches/TRACKB.md`, `docs/trackb/`, `pipelines/trackb/`, `requirements-trackb.txt`, `services/trackb/`, `tests/trackb/`. Exclude `requirements.txt` and all other-session paths.




## Runtime prerequisite recheck — 2026-10-25

The four exact image tags are present locally: `redis:8.10.2-alpine`, `apache/kafka:4.3.2`, `prom/prometheus:v3.13.2`, and `grafana/grafana:13.2.2-ubuntu`. Installed `.venv` clients are redis 8.1.0, confluent-kafka 2.16.0, and prometheus-client 0.26.0. No pull or package install was performed. Migration 100 is still unapplied; DB persistence is not claimed.

## B9/B10 runtime evidence — 2026-10-25

Failure diagnosis: the consumer called synchronous Kafka watermark queries (up to one second per assigned partition) after every poll, starving consumption; it also counted `OFFSET_INVALID` (-1001) as a real offset, inflating lag. The fix uses cached watermarks and skips uninitialized offsets. Delivery failure also clears the Redis dedupe marker before retry, preventing a failed alert publish from being silently suppressed on redelivery. Regression coverage was added.

Run `e38099ac743d47ccb69980c9b7cea0ef` was processed as REPLAY. The producer sent and received broker acknowledgements for 120 events (60 rain and 60 reservoir). Kafka scan verified those 120 run-tagged inputs and 50 generated run-tagged alert records. Consumer metrics processed 170 messages total (60 rain, 60 reservoir, 50 alert), with zero rule errors. Alert metrics counted 31 Warning, 16 Watch and 3 Critical. The consumer group assigned eight partitions; five non-empty partitions committed through their log ends with lag 0, and three empty partitions had no committed offset.

Redis logical DB 3 contained 120 input dedupe markers, four reservoir-state keys, four current-alert keys (current level Warning for each), and four latest-rain keys. Metrics reported 170 processed messages, 50 alerts, 0 errors, 170 latency observations, sum 175.269548 seconds (mean 1.030997 seconds), and zero active-partition lag. Prometheus reported the consumer target up during the run.

B9 remains blocked for database persistence: no authorized isolated database was available, migration 100 remains unapplied, and no database writes were made. No shared database was touched.

B10 stop-only returned success after this rerun. All four Track B services are exited and the four named volumes remain present. No volumes were deleted. All values above are REPLAY, never live. The credential remains unrotated by the user's choice; its value is not included here.
