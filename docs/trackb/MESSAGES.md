# Track B JSON Lines messages

All records are UTF-8 JSON Lines, one JSON object per line. Common fields are `schema` (string version), `event_id` (stable idempotency key), `time_precision` (`date|instant`), `source_date` (`YYYY-MM-DD` source-calendar day), `observed_at` (nullable ISO-8601 instant), `received_at` (ISO-8601 timestamp with timezone), `source` (`replay|live|simulated`), and `provenance` (object with source identifier and optional source file/hash). For `time_precision=date`, `source_date` is required, `observed_at` is JSON `null`, and `observation_timezone` is `unknown`; no instant is inferred. For `time_precision=instant`, `observed_at` is required and its supplied UTC offset is preserved in JSON. `received_at` always records actual ingestion/processing time separately from source observation time. Do not label replay or simulated data as live.

### Timestamp semantics and historical-timezone status

For timestamped events, `observed_at` is the source-supplied instant encoded with an explicit UTC offset; consumers parse it as offset-aware and persist the equivalent instant as `timestamptz` while preserving the original representation in payload JSON. `source_date`, when present on a timestamped record, must match the calendar date in that supplied offset. For date-only events, use `source_date` for grouping, ordering, and idempotency; never convert it to an instant. `received_at` is the actual ingestion/processing instant and is never substituted for observation time. An alert derived from a date-only observation has null `observed_at`, `valid_from`, and `valid_to`; it does not assert an exact validity interval.

The reservoir CSV source has date-only rows and declares neither a measurement instant nor a timezone. Historical timezone remains unconfirmed. Producer events preserve the parsed calendar date as `source_date`, set `observed_at` to null, and carry `timezone_status="unknown; source provides date only"`; they do not use midnight `Asia/Kolkata` or any other sentinel. Consumers preserve this limitation through state and alerts. Timestamped sources retain their actual supplied offsets and instants.

## `rain_update` schema `trackb.rain_update.v1`

Required: `schema`, `event_id`, `time_precision`, `received_at`, `source`, `provenance`, `location_key`, `value`, `unit` (`mm` or `mm/day`), `period_seconds`, `qc_flags` (array), and the temporal fields for the selected precision. `value` is a non-negative number or null when unavailable. Daily reservoir-source rain messages are date precision with `source_date` and null `observed_at`.

## `reservoir_update` schema `trackb.reservoir_update.v1`

Required: `schema`, `event_id`, `time_precision`, `received_at`, `source`, `provenance`, `reservoir_key`, `storage_value`, `storage_unit` (`mcft`), `capacity_value` (number or null), `capacity_unit` (`mcft` or null), `release_value` (number or null), `release_unit` (`cusecs` or null), `qc_flags` and the temporal fields for the selected precision. A storage change is not a release measurement. Date-only historical rows retain `source_date`; time and timezone remain unknown/null.

## `twin_update` schema `trackb.twin_update.v1`

Required: `schema`, `event_id`, `observed_at`, `received_at`, `source`, `provenance`, `run_id`, `state_ref`, `recompute_marker_key`. This twin-run control message identifies an instant and is not a date-only reservoir observation.

## `alert` schema `trackb.alert.v1`

Required: `schema`, `event_id`, `time_precision`, `received_at`, `source`, `provenance`, `reservoir_key`, `level` (`Normal|Watch|Warning|Critical`), `confidence` (0–1), `valid_from`, `valid_to`, `rule_version`, `trigger_inputs` (object), `target` (object) and the temporal fields for the selected precision. Date-only alerts require `source_date` and null `observed_at`, `valid_from`, and `valid_to`; timestamped alerts retain offset-bearing instant fields. Confidence is decision confidence under stated rules, not release probability.

### Persistence compatibility

Migrations 010/100 require non-null instants and timestamp-based keys for the existing twin state, alert, event, and marker tables. B19 adds the unapplied Track B migration `101_trackb_date_only_reservoir_observations.sql`: date-keyed reservoir observations and recompute markers, plus date-only alert events containing `source_date` and distinct `received_at`. Date-only alerts are not inserted into `twin.alerts`, whose exact interval columns cannot represent them. Existing timestamped persistence remains on the original tables. Migration 101 has not been applied to any database.
