# Track B realtime design notes

## Defaults and confirmation state

The reservoir source's historical measurement instant and timezone are **unknown/unconfirmed**: its CSV rows contain calendar dates only. Producer, replay, consumer, alert, API, and persistence paths use `source_date` for date-level identity/order and retain null `observed_at`; they do not encode a midnight default. `received_at` remains a separate processing timestamp. No authoritative source-owner evidence was found. Producer and consumer rules are specified in `MESSAGES.md`.

A replay message uses a stable event id and explicit source class. Kafka topic proposals: `trackb.rain.v1` (3 partitions, 30-day retention), `trackb.reservoir.v1` (3, 90 days), `trackb.twin.v1` (1, 30 days), and `trackb.alerts.v1` (1, 365 days). Partition by location/reservoir key to preserve ordering. Retention values are defaults for review and are not deployed.

The intended state path is replay/live adapter → validated versioned JSONL → Kafka → consumer/rule engine → durable timestamped twin rows or additive date-keyed Track B rows → Redis current-state cache → Prometheus/Grafana. Date-only alerts remain in the date-only Track B event store and do not enter `twin.alerts`, which requires exact validity instants. PostgreSQL is durable; Redis is disposable. The public API router is read-only. There is no live ingestion configured.

## Deployment status

B6 compose uses loopback-only bindings, named volumes, healthchecks, a `trackb` profile and a 512 MiB Kafka heap ceiling. Historical B9 runtime evidence is in `RUNBOOK.md` and remains evidence for that earlier replay only. B19's migration 101 is additive and unapplied; no shared or isolated database was modified. No live ingestion is configured.
