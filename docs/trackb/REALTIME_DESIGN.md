# Track B realtime design notes

## DEFAULT, to confirm

A replay message uses a stable event id and explicit source class. Kafka topic proposals: `trackb.rain.v1` (3 partitions, 30-day retention), `trackb.reservoir.v1` (3, 90 days), `trackb.twin.v1` (1, 30 days), and `trackb.alerts.v1` (1, 365 days). Partition by location/reservoir key to preserve ordering. Retention values are defaults for review and are not deployed.

The intended state path is replay/live adapter → validated versioned JSONL → Kafka → consumer/rule engine → durable `twin.alerts` plus idempotency link and recompute marker → Redis current-state cache → Prometheus/Grafana. PostgreSQL is durable; Redis is disposable. The public API router is read-only. There is no live ingestion configured.

## Deployment status

B6 compose is authored with loopback-only bindings, named volumes, healthchecks, a `trackb` profile and a 512 MiB Kafka heap ceiling. Image tags remain `to-confirm`. The local cache lacks Redis, Kafka, Prometheus and Grafana. B7–B10 are blocked; exact commands are in `RUNBOOK.md`. No end-to-end replay was attempted and no latency values are available.
