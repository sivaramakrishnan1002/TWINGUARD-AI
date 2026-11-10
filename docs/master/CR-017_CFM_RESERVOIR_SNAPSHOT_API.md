# CR-017 — On-demand CFM-DSS reservoir snapshot API

**Decision:** Additive local academic prototype operation, approved by the project owner in this session under CR-016. C1–C8 frozen baselines are unchanged; this operation is a separately versioned C4 addendum (v3 projection) and is not a G0 contract refreeze.

## Operation

`GET /reservoirs/history?period=daily|monthly` calls the B41 anonymous, cookie-aware CFM-DSS dashboard client once per explicit request. `period` defaults to `daily`. The daily response is bounded to the observed 75 rows and the monthly response to 65 rows. The service does not cache, schedule, retry, persist, write a database, or run any flood model. `Cache-Control: no-store` is required.

## Semantics

- `source_mode=LIVE` means the service fetched the public dashboard response during this request; it does not mean operational real-time telemetry. The UI label must say **Latest published dashboard snapshot**.
- `freshness=unknown`; the source update cadence and freshness SLA are not established.
- `source_date` is the daily calendar bucket or monthly label. `observed_at=null` and `observation_timezone=unknown`; never reinterpret the serialized midnight as an observation instant. `received_at` is the independent fetch time.
- Level is metres and average storage is MCM, per the dashboard labels. Inflow, outflow, release, warnings, flood depth, forecast, safe routing, and shelter recommendations are not supplied by this operation.
- Each record includes endpoint identity and SHA-256 of the exact response body. No raw response, cookie, request token, or upstream error is returned.
- Invalid query values receive framework 422; unavailable source, malformed data, unknown IDs, or schema drift fail closed with a generic 503.

## Boundaries

This is a low-volume, manual/on-demand read for the local college project. No recurring polling or public deployment is authorized. Source formal terms, rate limits, update cadence, and owner endorsement remain unknown. The operation must not trigger B42-style observation recomputation.

Implementation task: B44. UI consumer: B45.

## Amendment 2026-11-10 (CR-021 / OD-2026-11-10, live mode only)

The live forecast cycle may read the public CFM-DSS dashboard **at most once a day** (plus at most one manual read when the snapshot is more than 24 h old). It may keep the snapshot only inside a live run's provenance, for that run's retention period. It may use the snapshot as model forcing through A28's documented **assumption** rule. Derived outlet inflows are model assumptions and are never presented as observed or published releases.

All other boundaries in this CR remain. `GET /reservoirs/history` itself is unchanged.
