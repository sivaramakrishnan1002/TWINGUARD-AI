# Track B JSON Lines messages

All records are UTF-8 JSON Lines, one JSON object per line. Common required fields: `schema` (string version), `event_id` (stable idempotency key), `observed_at` (ISO-8601 timestamp with timezone), `received_at` (ISO-8601 timestamp with timezone), `source` (`replay|live|simulated`), and `provenance` (object with source identifier and optional source file/hash). Replay timestamps remain historical event time; `received_at` records the actual processing time. Do not label replay or simulated data as live.

## `rain_update` schema `trackb.rain_update.v1`

Required: `schema`, `event_id`, `observed_at`, `received_at`, `source`, `provenance`, `location_key`, `value`, `unit` (`mm` or `mm/day`), `period_seconds`, `qc_flags` (array). `value` is a non-negative number or null when unavailable.

## `reservoir_update` schema `trackb.reservoir_update.v1`

Required: `schema`, `event_id`, `observed_at`, `received_at`, `source`, `provenance`, `reservoir_key`, `storage_value`, `storage_unit` (`mcft`), `capacity_value` (number or null), `capacity_unit` (`mcft` or null), `release_value` (number or null), `release_unit` (`cusecs` or null), `qc_flags`. A storage change is not a release measurement.

## `twin_update` schema `trackb.twin_update.v1`

Required: `schema`, `event_id`, `observed_at`, `received_at`, `source`, `provenance`, `run_id`, `state_ref`, `recompute_marker_key`.

## `alert` schema `trackb.alert.v1`

Required: `schema`, `event_id`, `observed_at`, `received_at`, `source`, `provenance`, `reservoir_key`, `level` (`Normal|Watch|Warning|Critical`), `confidence` (0–1), `valid_from`, `valid_to`, `rule_version`, `trigger_inputs` (object), `target` (object). Confidence is decision confidence under stated rules, not release probability.
