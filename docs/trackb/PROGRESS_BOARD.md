# Track B progress board

| Task | Status | Commit hash | Notes |
|---|---|---|---|
| B1 audit | done | pending | Daily Kaggle coverage, monthly OpenCity gaps, rainfall source coverage, matched rainfall scale comparison, capacity provenance documented in AUDIT_AND_BACKTEST.md. |
| B2 target | done | pending | Future storage target N=7/fraction=.80; all 3×3 sensitivity combinations calculated. Capacities remain current-published assumptions. |
| B3 rule engine and models | done | pending | Train 2004–14, calibrate 2015–17, held-out 2018–20, horizon-purged. Rule + calibrated logistic and histogram gradient boosting where calibration classes permit; CPU. |
| B4 backtest | done | pending | Per-reservoir/combined POD/FAR/CSI, lead times, 300 year-block bootstrap replicates, reliability curves, persistence and rainfall-only baselines; separate 2015 case study. Storage-target metrics only. |
| B5 replay format | done | pending | Offline replay of 2015-11-20–2015-12-04 wrote 50 explicitly replay-labeled JSONL alert candidates; no DB write. |
| B6 compose | done | — | Track B-only overlay uses the four locally verified image tags; ports are loopback-bound. Quiet Compose validation passed during B9. |
| B7 topics and clients | done | — | Topic/client and Redis processing implemented; 12 focused tests passed at the B7 checkpoint. Runtime evidence remains part of B9. |
| B8 metrics | done | — | Bounded-cardinality metrics, loopback endpoint, Prometheus/Grafana provisioning and dashboard implemented; 16 focused Track B tests passed. Runtime scrape remains part of B9. |
| B9 end-to-end | blocked | — | Quiet Compose validation passed and four services reached healthy. REPLAY producer reported 120 events; consumer processed only 31 before stop, zero alerts, Redis DB 1 had no reservoir-state/current-alert keys, and lag remained 4,079 across topics. Prometheus target was up while consumer ran. Incomplete: diagnose consumer assignment/offset throughput, then rerun B9. |
| B10 stop and clean | done | — | Stop-only command returned success; all four Track B containers are exited and all four named volumes remain present. |
| B11 twin link | done | pending | Migration 100 creates idempotency tables; persistence helpers upsert alerts/states/markers. Migration is unapplied. |
| B12 API | done | pending | Five read-only endpoints and focused route tests; adapter injection, host app mount deferred. |
| B13 docs | done | pending | Audit, results, sensitivity CSV, report, lineage/limits, realtime design and diagram authored. |

## Current evidence and limits

- B7 focused checkpoint: 12 tests passed; B8 checkpoint: 16 tests passed; after B9 remediation changes, current focused Track B suite: 17 passed, one existing Starlette/httpx deprecation warning. Changed Python modules compile.
- Full repository suite after B9 remediation changes: 106 passed, 0 failed, one existing Starlette/httpx deprecation warning (2026-10-25).
- Raw audit after runtime work: 157 files, 30,544,672,450 bytes, 157 hash matches, 0 missing comparable hashes, 0 mismatches (2026-10-25). `data/raw/` remains read-only.
- DERIVED storage-target backtest uses 2018–2020 held-out years; outcome labels are future daily storage threshold attainment. This is not a flood or release-decision evaluation.
- Daily storage ends 2020-12-03; 2021/2023 have no daily-storage test coverage. Current published capacity denominators are not verified historically. Kaggle rain unit is INFERRED.
- Verified local image tags: `redis:8.10.2-alpine`, `apache/kafka:4.3.2`, `prom/prometheus:v3.13.2`, `grafana/grafana:13.2.2-ubuntu`. Installed clients: redis 8.1.0, confluent-kafka 2.16.0, prometheus-client 0.26.0. No image pulls or package installs.
- Quiet Compose validation passed. All four Track B services reached healthy after replacing the Grafana healthcheck command with the image-provided curl binary.
- B9 REPLAY producer reported 120 emitted events. The isolated fresh consumer processed only 31 before it was stopped, generated zero alerts, had zero recorded rule errors, and lag remained 4,079 across the four topics. Redis DB 1 contained processed markers but zero reservoir-state and current-alert keys. End-to-end B9 is blocked; these partial counts are not successful completion evidence.
- Prometheus scraped the host metrics target successfully while the consumer was running (`health=up`); after consumer shutdown the target went down, as expected. The partial local histogram sample had 31 observations and mean 65.8237 seconds, which includes delayed/stale message timing and is not accepted as representative replay latency.
- B10 stop returned success. All four Track B services are exited, and `tiwnguard_trackb-{redis,kafka,prometheus,grafana}-data` volumes remain present.
- Migration 100 is authored but unapplied. No shared DB writes; no isolated approved DB was identified for this run.
- The user authorized continuation with the earlier credential unrotated. Its value is not repeated or placed in logs or reports; Compose output remains suppressed.
- GPU compute was not needed for streaming, metrics or dashboard work.
- Track B changes remain uncommitted; unrelated worktree paths are preserved.


## Prerequisite recheck — 2026-10-25

- The four exact Track B Docker images were present locally before runtime; tags are listed in the runbook. No pull was performed.
- Installed clients verified in `.venv`: redis 8.1.0, confluent-kafka 2.16.0, prometheus-client 0.26.0.
- Docker daemon and image availability were checked without printing environment values or rendered Compose configuration.
- Migration 100 remains unapplied. No shared database write is authorized.
