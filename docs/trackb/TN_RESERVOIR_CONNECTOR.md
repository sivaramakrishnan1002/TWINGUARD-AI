# Public CFM-DSS reservoir snapshot connector

## Implemented scope

`services.trackb.connectors.tn_reservoir.CfmDashboardClient` performs one bounded read of either the public dashboard's daily (default) or monthly reservoir history. Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m services.trackb.connectors.tn_reservoir --period daily
.\.venv\Scripts\python.exe -m services.trackb.connectors.tn_reservoir --period monthly
```

It loads the public CFM-DSS dashboard in an anonymous HTTP session, reads the page-scoped `RequestVerificationToken`, then requests exactly one history route. It never logs in, uses credentials, stores cookies or tokens, retries automatically, persists data, writes a database, mounts an API, schedules polling, or triggers model recomputation. Errors are reported without returning response headers or token material.

## Verified source evidence

On 2026-11-06, the unauthenticated dashboard page returned HTTP 200. A plain history GET without the page-generated request token returned HTTP 403; loading the same public page in an anonymous cookie-aware session and making the dashboard's normal token-bearing GET returned HTTP 200. No account, officer login, OTP, or private credentials were used.

- Daily route: `/Master/GetLast15daysWaterLevel`; 75 records for five reservoir IDs over 2026-10-23 through 2026-11-06.
- Monthly route: `/Master/GetMonthlyWaterLevelOfReservoir`; 65 records for five reservoir IDs over 2025-11 through 2026-11.
- Observed fields: `tankid`, `date` or `monthly`, `average_waterlevel`, `average_storage`.
- Dashboard chart labels identify water level in metres and storage in MCM. Current card values were consistent with the numeric payload after display rounding. For Poondi the newest daily response was 38.6894239561109 m and 16.5085657652556 MCM.
- The route response is JSON encoded as a string containing a JSON array. The connector validates the documented-by-observation shape and fails closed on malformed/changed values, duplicate identities, unknown reservoir IDs, non-finite or negative values, HTTP failures, and unsupported date serialization.
- Each output row carries a SHA-256 hash of the exact response body, source ID/route, and a separate UTC `received_at`.

Tank IDs are mapped to the dashboard's five visible labels: `Po001` Poondi, `TNCH-07-T0726` Chembarambakkam, `RD001` Red Hills, `Cho001` Cholavaram, and `TK-001` Thervoy Kandigai. Unknown IDs fail closed rather than being silently assigned.

## Time and freshness

The source serializes date/month labels as strings such as `2026-11-06T00:00:00`. The connector preserves only the calendar label in `source_date`; it sets `observed_at=null`, `observation_timezone=unknown`, and `time_precision=date`. The midnight suffix is not treated as an observation instant. `received_at` records when this client fetched the payload.

The source's official update cadence, exact daily aggregation semantics, measurement timezone, revision/backfill rules, terms, rate limits, and freshness SLA remain unverified. For that reason `freshness=unknown`; the product is described as the latest-published dashboard snapshot, not sub-hourly live telemetry. Do not infer releases/inflow/outflow, flood probability, route safety, or operational decisions from these storage/level values. Use only occasional on-demand reads and provide source attribution. Do not redistribute raw responses until the source terms are confirmed.

## Verification

The connector tests use fake transport and clock fixtures only. They cover token extraction without token leakage, nested JSON decoding, daily/monthly schemas, response hashes, date-only semantics, HTTP failures, malformed/duplicate/unknown rows, non-finite values, and schema drift.

Verification on 2026-11-06:

- Focused connector tests: **9 passed**.
- Full Track B suite: **67 passed, 1 skipped**, with one existing Starlette/httpx deprecation warning.
- Python compilation and scoped `git diff --check`: passed.
- Raw audit: **157 files, 30,544,672,450 bytes; 157 hash matches; zero missing comparable hashes; zero mismatches**.
- One on-demand daily CLI fetch returned 75 rows and matched the Poondi dashboard card after display rounding: 38.6894239561109 m, 16.5085657652556 MCM, source date 2026-11-06. One on-demand monthly CLI fetch returned 65 rows; newest Poondi month label was 2026-11-01.

No database, Docker service, or persistent storage was used. The endpoint remains an undocumented dashboard implementation detail; this evidence verifies the current read path only, not long-term endpoint stability or an official real-time service guarantee.
