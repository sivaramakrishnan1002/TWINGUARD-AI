# Open-Meteo weather-model context feed

## What the UI now fetches

When the Situation Overview is open, the browser makes one HTTPS GET to Open-Meteo's public Forecast API for a fixed Chennai point (requested at 13.0827, 80.2707). It requests current precipitation, rain, 2 m temperature, relative humidity, and the next 24 hourly precipitation steps in `Asia/Kolkata`. It sends `Accept: application/json`, omits credentials, and uses no API key, proxy, database, or local persistence. A bounded refresh runs no more often than every 30 minutes while that panel is mounted; leaving Overview stops the timer and aborts any request.

This is a narrow **external weather-model context** connection. Open-Meteo describes its current conditions as weather-model data assembled from national weather-service forecast products, not direct station observations. `current.time` is the valid time of that estimate, and `current.interval` specifies the preceding accumulation window for precipitation. The code retains the provider's local timestamp and returned timezone explicitly; fetch receipt time is recorded separately. The request date/time shown in the UI does not assert the model run initialization/publication time.

The UI shows the current precipitation amount with its provider interval, rain, temperature, humidity, the provider-returned grid coordinate, and the next 24 hourly precipitation values. Zero remains a displayed numeric zero; null/missing values remain Unknown. Invalid units, timezone, coordinates, array shapes, HTTP errors, JSON errors, and timeouts fail closed. If a later refresh fails, the last successful response is marked as a previous response and is explicitly not presented as current.

## Interpretation boundary

The feed does not drive any flood solver or alter the central demo adapter. It is not converted into gauge rainfall or flood depth. Reservoir levels/releases, flood extent/depth, alerts, impacts, route/shelter status, what-if results, and 3D water remain demo, replay, unknown, or unavailable. A successful weather request does not mean a new provider model run occurred, and it does not establish a flood warning, flood forecast, or operational decision.

## Terms and source attribution

Open-Meteo's published free API terms allow educational, non-commercial use, limit the free API to fewer than 10,000 calls per day, and require acceptance of CC BY 4.0 attribution. The package displays “Weather data from Open-Meteo · CC BY 4.0” with a documentation link. Open-Meteo states it does not guarantee data accuracy, completeness, uninterrupted availability, or suitability. Its model update page says model updates typically occur every few hours and can be delayed/eventually consistent. The 30-minute timer is only the client polling interval and does not claim provider cadence.

Sources: [Forecast API documentation](https://open-meteo.com/en/docs), [terms](https://open-meteo.com/en/terms), [model update timing](https://open-meteo.com/en/docs/model-updates), and the project decision [CR-014](../master/CR-014_OPEN_METEO_WEATHER_CONTEXT.md).

## Verification evidence

A bounded request to the exact endpoint returned HTTP 200 from this environment on 2026-11-06. The response was checked for HTTP status, JSON shape, Asia/Kolkata timezone, returned grid coordinates, metric units, current valid time and interval, and hourly time/value arrays. Its values are not saved as project data and this connectivity check is not a gauge comparison, forecast-skill assessment, or flood validation.

Automated UI tests inject local fake responses and do not call Open-Meteo. The build/package guard permits only the exact registered Forecast API client and attribution URL; other network clients and service endpoints remain prohibited in the product UI.
