# CR-012 — G5/B13 source-backed date-only observation replay

> **Superseded as the G5 scope by CR-020 (2026-11-08).** The `GET /replay-alerts/{event_id}` route and its C3 date-only rules remain in force as an optional secondary check with no UI requirement. See `CR-020_G5_PRODUCT_PIPELINE_REPLAY.md`.

**Status: project-owner approved for the bounded G5/B13 scope revision.** Recorded 2026-10-31. This changes G5/B13 acceptance from retrieval of an existing saved historical alert outcome to replaying one actual archived source observation through processing, a mounted read-only backend route, and the packaged UI. It does not change G0, frozen C1-C8, C3 semantics, or C9 status.

## Owner decision recorded

The project owner approved this revision with these binding constraints:

- Use an actual archived source row with source identity and hash; do not invent or alter the input.
- Preserve C3 date-only behavior: source date only, observation time/timezone unknown, ingestion time separate, and no synthetic midnight or validity interval.
- Select the source row uniquely and deterministically; record the selector, source provenance/hash, replay run identity, and output hashes.
- Pass it through approved replay processing, a mounted read-only backend route, and the packaged UI. Display source date, unknown observation time, provenance, REPLAY status, derived-output status, and limitations.
- Distinguish the archived input from generated system output. Any generated alert or flood result is a derived replay result, never an observed historical event, live warning, validated forecast, or safety guidance.
- Processing/routes remain read-only with respect to source data and databases unless separately authorized. Do not change frozen C1-C8 or claim C9 frozen.
- G5 remains not ready until packaged end-to-end evidence passes.

## Existing evidence and scope decision

B28's owner report, `docs/trackb/B13_REPLAY_FIXTURE_EVIDENCE.md`, remains valid for its original question: no existing saved date-only POONDI alert fixture was found. The archived source row itself is verified and is now the approved **input**, not a pre-existing alert result:

- Archive: `data/raw/reservoirs/kaggle_chennai_water_management/archive.zip`, SHA-256 `7645febde7ccc21871200487139d1c8a84ea90a6dd2eccc93b7d1f06faf69197`.
- Member: `chennai_reservoir_levels.csv`, SHA-256 `3b4b6f2f53b5db20513d2829c2dba265c5738a55bf0c8eade51e0e2d5cfeaef7`.
- Unique source row reported by B28: physical CSV line 4354, `Date='01-12-2015'`, `POONDI='2745.00'`. This is a date-only source value and contains no observation time or timezone.
- B28 found zero occurrences of `replay:POONDI:date:2015-12-01` in the saved alert JSONL. Its legacy POONDI row has fabricated midnight/validity values and unconfirmed timezone metadata; it remains untouched and is prohibited as a substitute.

**G5 scope recommendation/decision:** retain B13 as a full-stack historical replay acceptance, now using the verified archived observation as input and treating any result as derived replay output. Do not require a pre-existing alert record. Do not generate or assert an alert merely to populate the UI. If the approved replay processing produces no derived alert/result, the UI must state that no derived output was produced. B28 evidence supports this input choice; the actual processing output and route behavior still require Lane B implementation and runtime tests. This is not G5 completion or scientific validation.

## Revised B13 acceptance

1. Consume only the uniquely identified B28 source row. Preserve the exact raw source values and add traceable source/member hashes; normalization to `source_date=2015-12-01` must be documented without implying a time or timezone.
2. Use the existing approved Track B replay processing and its registered rules/configuration without retuning. Bind a deterministic selector to the archive hash, member, reservoir, and source date. Record a stable replay run identity and hashes for the normalized input and every output. Identify any historical context rows required by existing processing and retain their provenance; do not treat them as the selected event.
3. Preserve `source_date`, `time_precision=date`, `observed_at=null`, unknown timezone, and separate actual `received_at`. Never synthesize a timestamp, validity interval, or sub-day ordering.
4. Carry source observation and processing result through an approved versioned API projection, a mounted read-only backend route, and the packaged UI. The route must fail closed on invalid, absent, duplicate, hash-mismatched, or unavailable source/result data and return no partial result.
5. Keep source and derived output distinct in API and UI. Show REPLAY for the historical input and an explicit derived-output state. Label any generated alert/flood output as derived replay output; null/no output remains unknown or absent, never an observed historical alert.
6. Show source date, unknown observation time/timezone, actual receipt/processing time separately, exact selector and run identity, source/output provenance and hashes, units/nulls, and research limitations. State that output is not live, historically observed, validated forecast, warning, or safety guidance.
7. Verify packaged AI/backend/UI behavior and deterministic tests for unique selection, provenance/hash validation, date-only semantics, source/output separation, no-output behavior, nulls, fail-closed errors, read-only boundaries, and packaged runtime. Keep G5 not ready until the complete path and required checks pass.

## Task order and implementation boundary

- B28 is complete with caveats and supplies the source-row identity/hash. Its no-existing-alert-fixture finding is preserved.
- I22 reviews and publishes the additive API projection for the revised observation-plus-derived-output semantics. It must preserve C4 v0/v1 and C7/C8; it does not mount runtime routes.
- B27 is revised as the Lane B implementation task and remains blocked until I22 completes. It owns the source fixture copy/normalization tests, bounded replay operation, backend route, packaged UI, runtime tests, and report at its registered paths.
- B13 performs independent G5 end-to-end acceptance only after B27 completes.

No database write, migration, Docker operation, service start, raw-source modification, or active OpenAPI/runtime change was performed as part of this change-control registration. B27 remains blocked, G5 remains `not_ready`, G0 remains unchanged, C1-C8 remain frozen v0, C3's historical measurement-time meaning/timezone remain unknown, and C9 remains proposed/unfrozen.

## I22 C4 v2 projection record

I22 publishes the additive, still-unfrozen C4 v2 `GET /replay-alerts/{event_id}` projection in both API documents. It retains the CR-011-approved route and status mapping while returning an observation/replay envelope: the archived source observation is separate from an optional derived B19 rule alert, and a valid no-alert outcome is `not_produced` with null alert/hash. The operation is documented as unexposed until B27 verifies and mounts it.

The fixed eligible selector is `replay:POONDI:date:2015-12-01`; archive/member hashes and CSV physical line 4354 are included as provenance. The projection retains the source's raw lexical row values, C3 date-only nulls, unknown timezone, and separate actual `received_at`. A stable `sha256:` replay identity excludes wall-clock receipt time and binds the source hashes/selector, algorithm/configuration hash, and normalized-input hash. Output hash remains a runtime evidence value; no hash is invented here. Context rows required by B19 rolling features must be listed and included in the normalized input identity.

The approved errors are 400 invalid selector/input, 404 exact match absent, 409 duplicate/ambiguous identity, and 503 unavailable/unreadable/hash-invalid inputs or assets with no partial result. The current Track B code supports a storage-rule alert only; the projection does not claim a flood-depth result. Its threshold inputs preserve the rainfall-unit caveat (`INFERRED; original unit unspecified`), and rule confidence is not calibrated probability. The complete schema and exact identity canonicalization are in `docs/master/contracts/c4_openapi_v2.md`; conformance checks are in `tests/master/test_b13_replay_projection.py`.
