# A22 — Open-Meteo rainfall forcing feasibility

**Decision: `INSUFFICIENT_EVIDENCE` for a flood-model experiment under the current approval.** Gate 1 is complete. Stop here: no Open-Meteo response was requested or saved for this assessment, no response was connected to A05/A06, and no flood outputs were generated. Any use or retention as solver forcing requires separate explicit project-owner approval and change control; CR-014 remains unchanged.

## Scope and evidence reviewed

Reviewed the approved weather-context boundary in `docs/master/CR-014_OPEN_METEO_WEATHER_CONTEXT.md`; the B43 request/client and evidence in `docs/ui/OPEN_METEO_WEATHER_FEED.md`, `frontend/src/ui/weather/openMeteoClient.ts`, `tests/ui/weather/open-meteo-weather.test.mjs`, and `docs/trackb/PROGRESS_BOARD.md`; A05/A06 specifications, reports, lineage, source code and saved summaries; and the official Open-Meteo Forecast API and model-update documentation. B43's test responses are local fixtures, not retained provider data. CR-014 records one bounded 2026-11-06 connectivity/schema request, but no response snapshot or provider model-run identity is retained for this feasibility review. No additional HTTP request was made.

Key reviewed artifact identities:

| Evidence | SHA-256 |
|---|---|
| `docs/master/CR-014_OPEN_METEO_WEATHER_CONTEXT.md` | `9c59ca2fd807419bd3c7a3041628511e83ff5d35451e2472402efe0a9bfe49be` |
| `docs/ui/OPEN_METEO_WEATHER_FEED.md` | `d399079d5675826eadb4d813e1dbe3ebbd7e4811cf0232af5988bc991112f89c` |
| `frontend/src/ui/weather/openMeteoClient.ts` | `9440b3fc93520677ce5333a939079d8405822d19dce4b2e60bd3efd39b34a8e4` |
| `docs/PHASE11_FORECAST_BATCH2.md` | `9038cda30b861fb352f79556230cb1909211f1e06cab178dda64d5df4732b126` |
| `docs/PHASE12_SIMULATION.md` | `8ac366288d2aedd59a7631bbbd332ba6ebab6712da905f4a709d16cd9243024c` |
| `pipelines/phase11/run.py` | `a21c44a828f3aebb041bf0a6a5e067142992a92e1364b2297030b40ddc8a929b` |
| `pipelines/phase12/simulate.py` | `16e60c9cc536b38e5e25b4c5535c73d364a7a6f7aacc9ba66959b7637877e5e9` |
| A05 saved summary `data/features/forecast/batch2_v1/forecast_summary.json` | `0bc0e322041c0d264a214d995912fd648fbda3534616f3e4588122e292e94dba` |
| A06 saved summary `data/features/simulation/batch2_v1/simulation_summary.json` | `58f736b54a4b4971fcade55f653cc6d86867c66eec612b16d184d9c93f365697` |

## Source request and time semantics

B43's exact approved request is the public `/v1/forecast` GET for latitude 13.0827, longitude 80.2707, with current `precipitation`, `rain`, `temperature_2m`, and `relative_humidity_2m`; hourly `precipitation`; `forecast_hours=24`; `timezone=Asia/Kolkata`; ISO 8601 time format; millimetres and Celsius. No other point, variable, API, key, or credential is approved by CR-014.

| Field | Documented meaning and possible A06 mapping | Evidence limit |
|---|---|---|
| Current precipitation/rain | B43 records units `mm`; `current.interval=900` seconds means the amount is accumulated over the preceding 15 minutes. `current.time` is provider valid time for that current estimate. | It is not a future hourly amount. A single preceding quarter-hour cannot be multiplied by four to create an hourly total. It can overlap the first hourly forecast window and must not be added to it. |
| Hourly precipitation | Forecast API documentation defines precipitation in `mm` as the sum for the preceding hour at each stated hourly time. This interval amount, rather than a rate, is dimensionally compatible with A06's ordered `hourly_mm` input after explicit timestamp alignment. | B43 requests only 24 future hourly steps. A05/A06 event runs use 72 consecutive UTC hours and save horizons through 72 h. The approved feed therefore cannot provide their complete forcing window. |
| Time | CR-014 requests `Asia/Kolkata`; B43 preserves the provider's local valid-time label and timezone offset (`utc_offset_seconds=19800`). To align an approved hourly amount with A06, timestamps would need to be converted to UTC while retaining the original local label and interval endpoint semantics. | The retained B43 documentation does not preserve a raw provider response from which to verify every literal wire timestamp, interval boundary, duplicate/gap behavior, or the exact last 24 hourly timestamps. It gives no A06 UTC forcing object. |
| Fetch time | B43 records client `fetchedAt` separately after receiving/parsing a response. | It is not model initialization, issue time, or publication time. CR-014's 30-minute refresh is a UI polling rule, not a provider update cadence. Open-Meteo documents model updates separately and warns the forecast API's automatic model selection/update timing is not inferred from `current.time`. |
| Null and zero | B43's schema and tests keep numeric zero distinct from `null`; missing values are displayed as unknown. | A06 expects numeric hourly inputs and has no explicit meteorological gap/quality representation. A future adapter would have to reject or explicitly preserve missing intervals before solver invocation; it must never coerce missing rainfall to zero. |

Open-Meteo documents current precipitation as a backward-looking accumulation interval and hourly precipitation as a preceding-hour sum in mm. ISO/timezone metadata is part of the API response, while model initialization and data-availability times are separate metadata concepts. The normal forecast endpoint returns a continuously stitched “best match” series; it is not a guarantee of one fixed model run. See the [Forecast API documentation](https://open-meteo.com/en/docs) and [model update documentation](https://open-meteo.com/en/docs/model-updates).

## Provider model and spatial representativeness

The approved request leaves model selection at its default (`auto`/Best Match). Open-Meteo says the highest-resolution applicable source is selected automatically, and that regions outside its listed regional-model areas use global models. Its API documentation says returned latitude/longitude identify the weather-grid-cell center used, which may differ from the requested coordinate; returned elevation is based on a 90 m DEM used for grid-cell selection/statistical downscaling, not the weather model's native grid spacing. The source docs list global models with differing resolutions (for example GFS at about 0.11°/~13 km), but the retained B43 evidence does not identify which model supplied each variable/lead or establish the actual grid resolution for its Chennai response. Therefore the B43 value “grid coordinate” is not evidence of a 600 m spatial field.

A06 has 2,430 active simulation cells at 600 m resolution in EPSG:32644 over the CMA domain; the project boundary is about 1,187 km². B43 requests a single fixed city point. No approved request covers the A06 domain as a field, and no evidence-backed interpolation/disaggregation method maps one point to the 2,430 cells. Spreading that value uniformly across the city, or fabricating subgrid variability, is unsupported. Even the approximately 13 km example global grid in the provider docs would be far coarser than 600 m; because the actual model identity is unrecorded, that example must not be presented as the B43 product's verified resolution.

This is the decisive blocker: spatial representativeness and provider grid/model identity are not established for the solver domain. Under the task criteria, a point weather-context estimate cannot be used as domain-wide rainfall forcing without an approved and scientifically supported spatial method.

## A05/A06 model mapping and physical limits

A06 `simulate()` takes hourly rainfall amounts in mm, converts each amount to a constant rate over that hour, and applies the rainfall source directly to every active cell. It uses a variable stable integration step (maximum 300 seconds; further constrained by the gravity-wave bound), 600 m cells, a dry start (`h=0`, zero face discharges), land-cover parameter defaults, and 20 Manning/infiltration members. In A06, WorldCover open-water cells and mapped waterways are zero-stage draining sinks; outer land boundaries are no-flow. The model has no explicit storm-drain network, external catchment inflow, initial soil-moisture state, calibrated antecedent storage, or distinct observed sea/river stage boundary. A05 wraps the same solver in five rainfall scenarios over three 72-hour UTC event windows; its `perfect_foresight_imerg` scenario distributes daily observed totals using ERA5 hourly shape and is explicitly a hindcast, not an operational forecast.

The arithmetic conversion of a complete preceding-hour amount in mm to A06's hourly input is possible in principle, but it does not solve these limitations: only 24 future hourly amounts are authorized, current 15-minute and forecast-hour windows are different intervals, and a single point does not provide spatial rainfall. The 24-hour cap cannot support the existing 72-hour scenario and horizon set. Restarting a simulation after each UI refresh would also change the forecast source, initialization, and forcing history; using the same saved response for deterministic replay would require the separate data-retention approval that CR-014 explicitly withholds.

A06/A05 checks establish only internal numerical integrity and scenario behavior. A06's two-event 40-run pilot took 68.03 seconds; A05's 300 runs took 687.71 seconds on its recorded CPU NumPy path. This suggests the existing coarse solver workload is computationally tractable for research runs, but it says nothing about the quality of Open-Meteo rainfall or flood predictions. A06 reported maximum mass-balance error of 0.264% and A05 0.591% (both below the internal 1% criterion); the A06 report also records weak, threshold-sensitive mapped-label fit and no independent depth validation. Neither check is flood-accuracy validation. No GPU workload was needed for this documentation-only assessment.

## Gate decision and prerequisites for any later proposal

**Gate 1 outcome: `INSUFFICIENT_EVIDENCE`.** Current Open-Meteo inputs are unsupported as A06 domain forcing because the retained request is a single point, actual model/grid identity and spatial field are not evidenced, and the permitted forecast covers 24 rather than the existing 72-hour A05 windows. Temporal units can be interpreted, but no solver adapter or run is authorized. Weather values remain model-derived, not gauge observations.

Any later Gate 2 proposal would first need a separate explicit owner approval/change-control record authorizing solver-input use and deterministic response retention; a versioned request/product and source/model metadata sufficient to identify a reproducible run; a defensible spatial method with coverage/resolution compatible with the A06 domain (or a separately approved change to model domain/grid); the complete forecast period or an explicitly narrowed experiment; a UTC/interval mapping specification; and fail-closed handling for gaps/nulls and provenance. These are prerequisites for a new decision, not implementation instructions or current approval. Do not alter CR-014, B43, A05/A06, APIs, contracts, gates, or prior outputs under this A22 assessment.

## Checks and output boundary

This A22 result is report-only. No files were written below `data/features/forecast/openmeteo_chennai_v1/`, `data/features/simulation/openmeteo_chennai_v1/`, or `pipelines/phase12_openmeteo/`; no solver or new external request was run. The A05/A06 source files and existing outputs were read only. Protocol verification, A05/A06 focused tests, raw audit, and final selector checks are recorded in the task closeout/progress board.
