# CR-016 — Use the public Chennai Flood Monitoring dashboard reservoir feed

**Decision:** Approved by the project owner in the current project session on 2026-11-06 for a bounded, non-operational college-project prototype. This decision selects the publicly viewable CFM-DSS dashboard data; it does not assert source-owner endorsement, a data license, or operational suitability.

## Selected source and scope

- Source: Tamil Nadu CFM-DSS public dashboard, `https://chennaifloodmonitor.tn.gov.in/HomePage/Dashboard`, Lakes view.
- Public read-only routes observed from the dashboard: `/Master/GetLast15daysWaterLevel` and `/Master/GetMonthlyWaterLevelOfReservoir`.
- The dashboard page returns HTTP 200 without an account login. Its browser obtains a page-scoped request-verification token and sends it with the GET requests. A fresh anonymous page session plus that token returned HTTP 200 for both history routes; direct calls without it returned HTTP 403. No officer login, OTP, credential, private API, or login bypass was used.
- Daily route evidence on 2026-11-06: 75 rows, five reservoir IDs, dates 2026-10-23 through 2026-11-06; fields `tankid`, `date`, `average_waterlevel`, `average_storage`.
- Monthly route evidence on 2026-11-06: 65 rows, five reservoir IDs, month labels 2025-11-01 through 2026-11-01; fields `tankid`, `monthly`, `average_waterlevel`, `average_storage`.
- Dashboard labels show water level in metres and storage in MCM. The endpoint's `date`/`monthly` strings serialize calendar labels with `T00:00:00`; this is not evidence of a measurement at midnight. Store the calendar label as `source_date`, with `observed_at=null` and timezone `unknown`. Record local `received_at` independently.
- Latest Poondi daily row fetched during review: water level 38.6894239561109 m and average storage 16.5085657652556 MCM. This matched the dashboard's rounded display. The exact source-published update cadence and source measurement-time semantics remain unknown; classify the response as latest-published daily dashboard data, not sub-hourly telemetry.

## Boundaries

The project owner authorizes only low-volume, on-demand GET reads for this local academic prototype, source attribution, and non-operational display. Do not poll frequently, redistribute the raw response, make flood/safety decisions from it, infer inflow/outflow or releases, or describe it as operational real-time telemetry. The source's formal terms, rate limits, custodial authority, revision/backfill policy, and freshness SLA were not located and remain unknown. Keep these caveats visible in the connector report. Do not store the page token or cookies; obtain a fresh page-scoped token per invocation and never print it.

CR-016 selects the prototype source and narrows D3/D8 for this prototype only. It does not change C3, C1-C8, G0, or any historical measurement-time claim. It does not authorize database writes, persistent retention, a public API, high-frequency polling, model recomputation, flood prediction, or operational use.
