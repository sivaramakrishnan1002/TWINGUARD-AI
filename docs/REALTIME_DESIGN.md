# Realtime and replay design

## Current status

Kafka, Redis, live sensors, alert services and realtime dashboards are **not implemented**. The existing Track B reservoir screen is illustrative historical analysis, not a validated warning rule. Storage observations are not releases, complete release values are unavailable, and current capacity history is not verified. Until real feeds and a validated model exist, the three event windows are replay-only; any future mock stream must be labelled simulated.

## Intended flow

`source adapter → validation/QC → Kafka event → state updater → versioned twin run → impact/route evaluation → alert candidate → human review`

Kafka is the durable event log for replayable updates. Redis is a short-lived cache for latest accepted values and read models, not the historical source of truth. PostgreSQL/PostGIS remains the durable project state/catalogue; source observations retain file and hash provenance.

## Kafka topic proposals

| Topic | Carries | Required event fields |
|---|---|---|
| `rainfall.observed.v1` | Rainfall updates from a named source/station/grid. | event id, observation time and timezone, received time, source/version, variable, value, unit, QC flags, geometry or station/grid key, source file/hash. |
| `reservoir.observed.v1` | Storage, level, inflow or release only when the source explicitly supplies that quantity. | reservoir key, observed time, field name, value/unit, source, QC, source id/hash. Missing release stays missing. |
| `twin.state.updated.v1` | State-run completion and references to grid-state artifacts plus edge/facility/reservoir state partitions. | run id, valid time, version/code/config ids, artifact URI/hash, QC summary and provenance. |
| `alerts.candidate.v1` | A model-generated candidate requiring review. | alert id, severity, issued/valid interval, affected assets/area, triggering inputs, uncertainty, model/run version, review status. |

Partition by station/grid/reservoir or entity key to preserve per-entity ordering. Use stable event IDs for idempotency. Keep source event time distinct from ingestion time; reject or quarantine malformed units, stale timestamps and impossible values. Replay must use historical event-time order and preserve original source/QC flags.

## Redis proposal

- Cache the latest accepted observation by source and entity key with an explicit TTL and `observed_at`.
- Cache the latest completed twin-run manifest and compact alert/shelter/route read models.
- Treat cache loss as recoverable from PostgreSQL and Kafka; never store the only copy of an observation, model output or alert in Redis.
- Do not use a cache entry after its freshness threshold. Report stale/unavailable explicitly.

## Track B interface

The rapid-alert interface should show rainfall accumulation and freshness, reservoir storage with capacity provenance, missing release data, alert candidate and confidence, lead time, affected roads/facilities, and a human acknowledgement/action record. Each alert displays source times and uncertainty. A storage trend must never be labelled a release.

Initially replay Track B over the available historical rainfall/reservoir series only, showing that it is an **illustrative rule replay**. No operational alert should be emitted. Live mode remains disabled until authoritative feeds, update frequency, units, thresholds, false-alarm/lead-time evaluation, failover and human escalation are approved and tested.
