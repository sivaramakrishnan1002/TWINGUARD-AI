# Track B progress board

| Task | Status | Commit hash | Notes |
|---|---|---|---|
| B1 audit | done | pending | Daily Kaggle coverage, monthly OpenCity gaps, rainfall source coverage, matched rainfall scale comparison, capacity provenance documented in AUDIT_AND_BACKTEST.md. |
| B2 target | done | pending | Future storage target N=7/fraction=.80; all 3×3 sensitivity combinations calculated. Capacities remain current-published assumptions. |
| B3 rule engine and models | done | pending | Train 2004–14, calibrate 2015–17, held-out 2018–20, horizon-purged. Rule + calibrated logistic and histogram gradient boosting where calibration classes permit; CPU. |
| B4 backtest | done | pending | Per-reservoir/combined POD/FAR/CSI, lead times, 300 year-block bootstrap replicates, reliability curves, persistence and rainfall-only baselines; separate 2015 case study. Storage-target metrics only. |
| B5 replay format | done | pending | Offline replay of 2015-11-20–2015-12-04 wrote 50 explicitly replay-labeled JSONL alert candidates; no DB write. |
| B6 compose | done | — | Track B-only overlay uses the four locally verified image tags; ports are loopback-bound. Quiet Compose validation passed during B9. |
| B7 topics and clients | done | — | Topic/client and Redis processing implemented; 12 focused tests passed at B7 checkpoint. The B9 rerun acknowledged and processed all 120 run-tagged replay inputs. |
| B8 metrics | done | — | Bounded-cardinality metrics, loopback endpoint, Prometheus/Grafana provisioning/dashboard implemented; current focused Track B tests: 21 passed. Runtime scrape verified during B9. |
| B9 end-to-end | blocked | — | Fixed per-poll blocking Kafka watermark queries and invalid-position lag inflation. Run `e38099ac743d47ccb69980c9b7cea0ef`: producer sent/acknowledged 120/120; consumer processed 60 rain + 60 reservoir + 50 generated alert records; 50 alerts (31 Warning, 16 Watch, 3 Critical), zero errors. Redis DB 3 has 120 run markers, four reservoir states, four current alerts; Kafka committed-partition lag 0; Prometheus target up. DB persistence remains unverified: migration 100 unapplied and no authorized isolated test DB identified. |
| B10 stop and clean | done | — | Stop-only returned success after replay; all four Track B containers are exited and all four named volumes remain present. |
| B11 twin link | done | pending | Migration 100 creates idempotency tables; persistence helpers upsert alerts/states/markers. Migration is unapplied. |
| B12 API | done | pending | Five read-only endpoints and focused route tests; adapter injection, host app mount deferred. |
| B13 docs | done | pending | Audit, results, sensitivity CSV, report, lineage/limits, realtime design and diagram authored. |

## Current evidence and limits

- B7 focused checkpoint: 12 tests passed; B8 checkpoint: 16 tests passed; after B9 remediation changes, current focused Track B suite: 21 passed, one existing Starlette/httpx deprecation warning. Changed Python modules compile.
- Full repository suite after B9 diagnosis/fix: 113 passed, 0 failed, one existing Starlette/httpx deprecation warning (2026-10-25).
- Raw audit after diagnosis/fix and before replay: 157 files, 30,544,672,450 bytes, 157 hash matches, 0 missing comparable hashes, 0 mismatches (2026-10-25). `data/raw/` remains read-only.
- DERIVED storage-target backtest uses 2018–2020 held-out years; outcome labels are future daily storage threshold attainment. This is not a flood or release-decision evaluation.
- Daily storage ends 2020-12-03; 2021/2023 have no daily-storage test coverage. Current published capacity denominators are not verified historically. Kaggle rain unit is INFERRED.
- Verified local image tags: `redis:8.10.2-alpine`, `apache/kafka:4.3.2`, `prom/prometheus:v3.13.2`, `grafana/grafana:13.2.2-ubuntu`. Installed clients: redis 8.1.0, confluent-kafka 2.16.0, prometheus-client 0.26.0. No image pulls or package installs.
- Quiet Compose validation passed. All four Track B services reached healthy after replacing the Grafana healthcheck command with the image-provided curl binary.
- B9 root cause: after every poll, `update_consumer_lag` queried Kafka watermarks synchronously (up to one second per assigned partition), starving the consumer; it also treated `OFFSET_INVALID` (-1001) as a real position and inflated lag. The fix uses cached watermarks and skips invalid/uninitialized positions. Regression tests cover these cases and delivery retry behavior.
- Successful data-plane REPLAY run `e38099ac743d47ccb69980c9b7cea0ef`: producer 120 sent / 120 acknowledged. Kafka scan found this run's 60 rain updates, 60 reservoir updates, and 50 generated alert events. Consumer metrics processed 60 rain + 60 reservoir + 50 alert records = 170; rule errors 0. Alert metrics: Warning 31, Watch 16, Critical 3. Kafka group had 8 assigned partitions, 5 with committed offsets at log end and lag 0; 3 partitions were empty and had no committed offset.
- Isolated Redis DB 3 contained 120 run-specific input dedupe markers, four reservoir state keys, four current-alert keys (all current levels Warning), and four latest-rain keys. Metrics: 170 processed, 50 alerts, 0 errors, 170 latency observations, sum 175.269548 s (mean 1.030997 s), active-partition lag 0. Prometheus target was `up` during the consumer run.
- B9 remains blocked on database persistence evidence: no authorized isolated test database was identified. Migration 100 remains unapplied and no DB writes were attempted. Do not treat this limitation as a runtime alert-flow failure or claim full DB integration.
- B10 stop after the successful rerun returned success. All four Track B services are exited, and all four named volumes remain present.
- Migration 100 is authored but unapplied. No shared DB writes; no isolated approved DB was identified for this run.
- The user authorized continuation with the earlier credential unrotated. Its value is not repeated or placed in logs or reports; Compose output remains suppressed.
- GPU compute was not needed for streaming, metrics or dashboard work.
- Track B changes remain uncommitted; unrelated worktree paths are preserved.


## Prerequisite recheck — 2026-10-25

- The four exact Track B Docker images were present locally before runtime; tags are listed in the runbook. No pull was performed.
- Installed clients verified in `.venv`: redis 8.1.0, confluent-kafka 2.16.0, prometheus-client 0.26.0.
- Docker daemon and image availability were checked without printing environment values or rendered Compose configuration.
- Migration 100 remains unapplied. No shared database write is authorized.
