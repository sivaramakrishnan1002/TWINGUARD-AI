# CFM-DSS reservoir snapshot API

The local AI service exposes `GET /reservoirs/history?period=daily|monthly` for an explicit, on-demand fetch from the public Chennai Flood Monitoring dashboard. `period` defaults to `daily`. Each request obtains a fresh anonymous dashboard session and page token, then fetches one history payload. The service does not cache or schedule calls.

The response is labeled `source_mode=LIVE` because it is fetched from the source during the request; freshness remains `unknown`, and the product must label it **Latest published dashboard snapshot**. `source_date` is a daily/monthly calendar bucket, `observed_at` is null, timezone is unknown, and `received_at` is the separate service fetch time. Values are dashboard-labeled metres and MCM. Provenance includes the endpoint and SHA-256 of the response body.

Upstream failures, malformed/changed payloads, duplicate identities, or invalid values return a generic 503 without source tokens, cookies, raw body, or exception details. Invalid `period` values return 422. Responses use `Cache-Control: no-store`.

This is not sub-hourly telemetry. Publication cadence, exact measurement timing, formal terms, and rate limits remain unknown. It does not provide rainfall, releases, inflow/outflow, alerts, forecasts, model recomputation, flood depth, route safety, or shelter recommendations. Keep requests manual and low-volume; do not use the values for operational decisions.
