# CR-014 — Open-Meteo weather-model context for the local prototype

**Decision:** approved by the project owner on 2026-11-06, limited to the educational, non-commercial TwinGuard prototype described here.

## Approved source and use

- Provider/API: Open-Meteo Forecast API, `https://api.open-meteo.com/v1/forecast`.
- Location: fixed Chennai city point, requested at latitude 13.0827, longitude 80.2707; retain the provider-returned grid coordinates in the response display.
- Requested fields: current precipitation, rain, 2 m temperature and 2 m relative humidity; the next 24 hourly precipitation forecast steps; timezone `Asia/Kolkata`; metric units.
- Request method: public HTTPS GET from the browser, no credentials, no API key, no proxy, no persistence, and no other locations or variables.
- Refresh: load when the Overview is entered and refresh at most every 30 minutes while it remains open. The UI must separately display provider valid time and local fetch time. A refresh interval is a client behavior, not the provider's update cadence.
- Terms: educational, non-commercial use under Open-Meteo's free API terms and CC BY 4.0 data license; keep visible attribution and link to provider/source documentation. Respect the published limit of fewer than 10,000 API calls per day. No uptime or accuracy guarantee is implied.

## Interpretation and exclusions

Open-Meteo's `current` values are weather-model output assembled from numerical weather prediction products, not direct Chennai rain-gauge or station observations. `current.time` is the valid time represented by the current model value; it is not a model initialization/publication time. The `interval` field governs the backward-looking precipitation aggregation and must be shown with the precipitation amount. Hourly precipitation is a model forecast amount for its stated hour.

This source is approved only for a clearly labeled external weather-model context panel. It does **not** authorize using these values as flood depth, reservoir state/release, warning, road status, route safety, shelter status, impact result, or as input to the existing Lane A solver. Those outputs remain DEMO/SIMULATED, REPLAY, unknown, or unavailable as already specified. No automatic alert, database write, backend route, source credential, or change to C1–C8/C9 is authorized.

## Evidence

- Open-Meteo's official API documentation says the Forecast API combines model output from national weather services, documents current/hourly variable semantics and timestamps, and says an API key is required only for commercial reserved resources: <https://open-meteo.com/en/docs>.
- Official terms permit educational content under non-commercial use, publish request limits, and specify CC BY 4.0 attribution: <https://open-meteo.com/en/terms>.
- Model timing documentation says updates typically occur every few hours and are subject to processing and eventual-consistency delays: <https://open-meteo.com/en/docs/model-updates>.
- A bounded unauthenticated request for the specified Chennai point returned HTTP 200 on 2026-11-06, with `timezone=Asia/Kolkata`, provider grid coordinates, ISO local valid time, `interval=900` seconds, current precipitation/rain/temperature/humidity fields, and 24 hourly precipitation values. The response is a connectivity/schema check, not an accuracy or gauge-validation result.

## D2/D8 scope clarification

D2 is resolved only for this named Open-Meteo model product and the educational display use above; it does not select IMD or a rainfall gauge. D8 is resolved only for a local prototype that can fetch this public model context. It does not authorize a live flood-model pipeline or operational use. Reservoir source D3, source-owner authorization for other feeds, and observation-triggered recomputation remain unresolved.
