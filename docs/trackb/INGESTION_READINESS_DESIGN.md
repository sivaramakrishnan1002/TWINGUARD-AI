# B35 — Fixture-only ingestion readiness boundary

## Scope and status

This is a typed, in-memory boundary for offline fixture behavior tests. It has no configured URL, credential, source client, route mount, database adapter, queue, migration, or persistence. `FixtureOnlyIngestionAdapter` only uses an explicitly injected `FixtureTransport` and clock. `LIVE` is intentionally rejected by the envelope model; no live transport is implemented or verified.

The checked-in POONDI fixture reuses the B28-recorded source row and provenance hashes as a date-only `REPLAY` example. The timestamped rain fixture is explicitly `SIMULATED` test data, not a source observation. The adapter preserves the supplied strings and provenance; it does not claim either fixture establishes live source behavior.

## Envelope boundary

Each `trackb.observation_envelope.v1` record requires:

- stable `event_id`, `source_id`, `source_mode` and `time_precision`;
- `source_date` or offset-bearing `observed_at` according to precision, plus separate offset-bearing `received_at`;
- unit and spatial coverage fields, both nullable when unavailable;
- provenance source ID, evidence path and lowercase SHA-256;
- quality flags and an explicit `missingness` state (`present`, `missing`, `nodata`, or `unavailable`).

For `date` precision, `source_date` must be a real ISO calendar date, `observed_at` must be null, and `observation_timezone` must equal `unknown`. Extra fields such as validity bounds fail closed. No timestamp is synthesized and `received_at` is never used to rank or age a date-only source observation. A date-only accepted record has `freshness=unknown`.

For `instant` precision, the original ISO-8601 string and UTC offset are preserved. If `source_date` is provided, it must match the calendar date in that supplied offset. The adapter compares instants in UTC only for age calculations; it does not rewrite the stored timestamp string.

Values marked missing, NoData, or unavailable must be null; `present` requires a finite numeric value. Null is not converted to zero or dry. Provenance must identify the same source as the envelope and contain a valid digest-shaped value.

## Freshness, retries and idempotency

Callers supply non-negative `stale_after_seconds`, optional `delayed_after_seconds`, and a positive `max_attempts`. No cadence is inferred from the inventory. For timestamped samples, age strictly greater than the stale threshold yields `stale`; equality remains fresh. A receipt-to-observation delay strictly greater than its optional threshold yields `delayed`. Stale/delayed events are reported but not added to the in-memory accepted-event map. Future-dated samples have unknown freshness; source-specific future-skew policy remains unconfigured.

Only `TransientSourceError` retries, up to the supplied bound. An unavailable source or unexpected injected transport exception returns a sanitized `unavailable` state without retrying. A missing fixture returns `missing`; parse/schema/time/provenance errors return `malformed`. Results do not expose exception text.

The idempotency key is `event_id`; its fingerprint covers source identity/mode, temporal semantics, value/unit, coverage, provenance, quality and missingness, while excluding `received_at`. An identical replay returns `duplicate` without adding another accepted record. Reusing an event ID with different content returns `conflict` and does not replace the accepted content. State is process-local test behavior only; no durable side effect exists in this package.

## Offline test coverage

`tests/trackb/test_ingestion_readiness.py` uses checked-in fixtures, a fake transport, and a fake clock. It covers timestamp-offset/provenance preservation, C3 date-only behavior, strict staleness boundary, delay classification, duplicate and conflicting duplicate behavior, null/missing/NoData/unavailable semantics, malformed timestamp synthesis, unavailable and missing sources, bounded retry, LIVE rejection, and static absence of network/database client imports.

## Source decisions and limitations

The source readiness inventory remains the authority for evidence gaps. In particular:

- **D2 rainfall source/access:** IMERG terms need confirmation; Open-Meteo use is subject to recorded API terms; NASA POWER terms and live access are unresolved; ERA5 CDS and IMD candidates are not collected/authorized.
- **D3 reservoir source/access/time semantics:** no authoritative live reservoir feed, source-owner agreement, or historical timezone/measurement-time evidence is recorded. C3 date-only semantics remain unchanged.
- **D8 replay versus live prototype:** no decision authorizes a live prototype. This B35 boundary is fixture-only and does not connect a source.

Before any production adapter, the project owner must resolve the applicable source/access decisions and source-specific unit, timestamp/timezone, cadence, latency, coverage, terms, freshness, revision and outage policies. A separately registered task must define approved transport/security and durable side-effect behavior. These tests do not establish live ingestion, service readiness, freshness SLAs, or operational warning capability.

## B35 verification record

- Focused: `.venv\Scripts\python.exe -m pytest tests\trackb\test_ingestion_readiness.py -q --import-mode=importlib` — **13 passed**.
- Track B suite: `.venv\Scripts\python.exe -m pytest tests\trackb -q --import-mode=importlib` — **51 passed, 1 skipped**, one existing Starlette/httpx deprecation warning. The skip is the environment-gated B20 isolated-database test; no database was accessed.
- Compilation: `.venv\Scripts\python.exe -m compileall -q services\trackb\ingestion_readiness` — **passed**.
- `git diff --check` for B35 registered outputs — **passed**.
- Raw audit: `.venv\Scripts\python.exe tools\audit_raw_logs.py` — **157 files, 30,544,672,450 bytes; 157 hash matches; 0 without comparable hashes; 0 mismatches**.
- `python tools/master/verify_state.py` — **passed** at startup and will be rerun after protocol finish.
