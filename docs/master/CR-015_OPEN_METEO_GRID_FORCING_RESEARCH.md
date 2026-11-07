# CR-015 — Bounded Open-Meteo spatial rainfall snapshot for A06 feasibility

**Decision:** approved by the project owner in the 2026-11-06 request that registered this change. This is a narrow additive decision; it does not amend or expand CR-014.

## Authorized scope

- **Provider/product:** Open-Meteo Forecast API only, using the non-commercial educational access terms and published API limits already recorded in CR-014. No IMD, reservoir provider, alternate weather provider, paid/commercial endpoint, credentialed endpoint, or access-control workaround is authorized.
- **Purpose:** one bounded data acquisition for Lane A task A23 to determine whether spatially distributed precipitation can cover the existing A06 grid and a complete A05/A06 72-hour run. If A23's documented scientific-feasibility gate passes, the same deterministic snapshot may be used for at most one versioned research-only run. If the gate fails or evidence is insufficient, stop with the feasibility report and generate no flood output.
- **Variables:** precipitation amounts and only the time, interval, model/product, timezone, grid-coordinate, and source metadata required to interpret and reproduce them. Temperature, humidity, reservoirs, warnings, and unrelated fields are outside this change.
- **Spatial/time scope:** the A06 assessed domain/grid and one forecast window sufficient to evaluate 72 consecutive hours, if the documented product supports it. The exact request/model/coverage must be recorded by A23. No assumption that the B43 single-point 24-hour request suffices.
- **Retrieval/retention:** the minimum terms-compliant unauthenticated request set needed for one deterministic snapshot; no periodic refresh, ongoing feed, or repeated forecast ingestion. Retain the exact request and response, provider metadata, retrieval time, and hashes only under `data/features/weather/openmeteo_a06_domain_v1/`. `data/raw/` remains read-only. Do not use credentials; if authentication is required, stop for a separate decision.
- **Use boundary:** solver input is allowed only inside A23 after its feasibility report establishes a defensible spatial/time mapping and A06 internal checks are specified. This permits one research run, not a live or recurring solver connection.

## Required safeguards and exclusions

1. Respect the Open-Meteo published terms, attribution, and rate limits. If the domain/horizon cannot be retrieved within those terms and a bounded request set, stop and request a new decision.
2. Preserve provider valid times, accumulation intervals, units, returned coordinates, model identity when available, and the separate actual fetch time. Do not invent model initialization time, interpolate missing cells/times, or turn NoData into zero.
3. Label the source as numerical-weather-model output, never as a rain-gauge observation or validated flood input. Keep the exact snapshot and every derived output traceable by SHA-256.
4. Do not alter A05/A06 outputs; write any supported experiment only to A23's new versioned paths. No API/UI connection, continuous ingestion, database, migration, alert, impact, route, shelter, emergency decision, public warning, or operational/safety claim is authorized.
5. Do not change CR-014, frozen C1–C8, C9, G0, G5, or G6.

## Decision scope

This CR authorizes only the bounded Open-Meteo data retrieval and retention above and, conditionally, one research-only A23 run after its feasibility gate passes. It does not establish that Open-Meteo's product is spatially or temporally suitable, that A06 is validated, or that the experiment will produce interpretable flood outputs. A23 must stop without flood outputs if any required mapping or physical assumption is unsupported.
