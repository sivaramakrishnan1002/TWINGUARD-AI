# C4 v2 — date-only source-observation replay projection

**Status:** additive, project-owner-approved change-control projection under CR-012; proposed/unfrozen and not runtime-mounted. It does not replace frozen C4 v0 or approved C4 v1, and it does not change C7/C8. The AI and Spring projections are `GET /replay-alerts/{event_id}`. The path retains the CR-011-approved route; its response is a replay evaluation envelope and does not promise an alert. B27 alone may implement it after I22 finishes.

## Exact source selection and provenance

The sole eligible source selector is `event_id=replay:POONDI:date:2015-12-01`, bound to archive SHA-256 `7645febde7ccc21871200487139d1c8a84ea90a6dd2eccc93b7d1f06faf69197`, member `chennai_reservoir_levels.csv` SHA-256 `3b4b6f2f53b5db20513d2829c2dba265c5738a55bf0c8eade51e0e2d5cfeaef7`, physical CSV line 4354, raw `Date=01-12-2015`, raw `POONDI=2745.00`, normalized `source_date=2015-12-01`. The archive and member hashes are source hashes; no independent hash of the CSV row was established. Keep the raw lexical value and line mapping in response provenance. Do not select the incompatible legacy JSONL alert.

## Response and identity

The response contains separate `source_observation`, `replay`, and `derived_output` objects. The source observation preserves `trackb.reservoir_update.v1`, `source=replay`, `source_mode=REPLAY`, `time_precision=date`, exact `source_date`, `observed_at=null`, `observation_timezone=unknown`, and a distinct offset-aware actual `received_at`. It preserves raw source fields and `storage_value=2745 mcft`; no rainfall unit is asserted.

`replay_run_id` is `sha256:` plus a lowercase SHA-256 digest of UTF-8 canonical JSON (sorted keys, compact separators) over identity version `b13-replay-identity-v1`, source archive/member hashes, exact event selector and source line, `algorithm_id=trackb-rule-v1`, effective configuration SHA-256, and normalized-input SHA-256. The normalized input hash covers the exact source row and every contextual row/feature actually used by B19 processing; context rows must be listed with provenance and never represented as the selected event. `received_at` and other wall-clock values are excluded, making the identity stable across replays. B27 must calculate these hashes and tests before returning the response; this projection does not claim an output hash already exists.

`derived_output.status` is `produced` only with an alert body and canonical output SHA-256; `not_produced` requires null alert and null output hash. A missing alert is a valid no-output result, not a missing source. Existing B19 evidence supports only the storage-target rule alert, not a flood-depth result. Its confidence is a transparent rule-evidence score, not calibrated probability. Capacity fraction/horizon remain defaults requiring confirmation. The legacy rainfall field is unit-uncertain (`INFERRED; original unit unspecified`); no caller may present it as verified mm. No generated result is an observed historical alert.

## Errors and boundaries

- 400: malformed/invalid event selector or input.
- 404: no exact source/replay identity.
- 409: duplicate or ambiguous identity.
- 503: unavailable/unreadable source, context, configuration or result, or any hash mismatch; return no partial body.

The GET is read-only, bounded to the allowlisted fixture, and test-scoped. It does not write source data or a database, apply migrations, access live feeds, or compute flood depth. The current AI/backend runtime remains unexposed; this document and OpenAPI do not claim route availability. G5 remains not ready until the packaged path is independently accepted. Historical measurement-time meaning and timezone remain unknown. No live warning, validated forecast, flood-safety, or emergency-guidance claim is permitted.

C4 v0/v1 and frozen C7/C8 are unchanged. C9 remains a separate proposed/unfrozen contract.
