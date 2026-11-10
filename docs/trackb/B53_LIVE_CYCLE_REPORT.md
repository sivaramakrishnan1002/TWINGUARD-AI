# B53 — Packaged live-cycle verification (CR-021, Round 2)

**Lane B report, 2026-11-10.** This verifies live forecast mode end to end on the packaged B11 stack through nginx `http://127.0.0.1:8081/api/ai/v3/live/*`.

- **Evidence:** every call with its status, bytes, SHA-256, schema result and timing is in [`B53_LIVE_CYCLE_EVIDENCE.json`](B53_LIVE_CYCLE_EVIDENCE.json).
- **Script:** [`tests/e2e/b53_live_cycle.py`](../../tests/e2e/b53_live_cycle.py), run in four phases: `catchup`, `refresh`, `failure` and `final`.

**Result:** acceptance items 1, 2, 4 and 5 pass. Item 3 (packaged screenshots `docs/ui/screenshots/18_live_*`) is the UI session's to supply.

The packaged run uncovered one contract defect: A28 reports the reservoir `fetched_at` as `…+00:00` with microseconds, which fails C4 v3's RFC 3339 UTC `Z` format. It was fixed in commit `d672eae`, and all bodies were re-checked clean. The pre-fix capture is kept as `catchup_initial`.

## Stack

| Item | Value |
|---|---|
| Docker | Docker Desktop 29.9.3 |
| Command | `docker compose -p twinguard-b11 -f docker-compose.b11.yml -f <scratch b53-override.yml> up -d --build --wait` |
| Images | AI `b5403e3d`, rebuilt at `d672eae` for the timestamp fix. Frontend `9a4e3e7a`, built from the current UI (B52). Backend unchanged. |
| Engine | A25/A27/A28 `twinguard-flood-engine/2.1.0` on CPU (`device.used: cpu`, per-run worker) |
| Live mode | `TWINGUARD_V3_LIVE=1` (B11 compose default) |

The scratch override did two things:
- **No host :8000:** it dropped the AI container's host port (`ports: !reset []`). nginx reaches the container over the compose network, which left the separate local `:8000` service untouched.
- **Isolated run store:** it pointed the container's run store at `data/features/v3/runs_b53`, so the packaged live scheduler shares no live state with `:8000`. The empty store also triggered the start-up catch-up cycle.

## 1 Live cycles

| | Catch-up (start-up) | Manual refresh |
|---|---|---|
| run_id | `sim-20261110T120422Z-1a781dbd` | `sim-20261110T121126Z-979f9524` |
| run_kind / mode / `live.cycle` | LIVE_FORECAST / live / catch_up | LIVE_FORECAST / live / manual |
| Open-Meteo `issued_at` (fetch) | 2026-11-10T12:04:16Z | 2026-11-10T12:11:20Z |
| Forecast window (72 h) | 11:00Z → 2026-11-13T11:00Z | 11:00Z → 2026-11-13T11:00Z |
| Open-Meteo calls counted (container, UTC day) | 297 | 594 cumulative |
| CFM-DSS `source_date` / `received_at` | 2026-11-10 / 12:04:22Z (2 requests) | same snapshot reused (under 24 h) |
| Coupling | `A28-RES-STORAGE-v1 (applied)`, every outlet inflow 0 m³/s (storage below 90 %) | same |
| Engine | `twinguard-v3-engine/1.1.0 (A25 …) (twinguard-flood-engine/2.1.0)` | same |
| Device | cpu, no fallback | cpu, no fallback |
| Wall time (created → completed) | 277.0 s (engine 273.7 s) | 286.0 s (engine 282.5 s) |
| Published after container start | 282 s | — |
| Frames / grid | 145 / 120 m | 145 / 120 m |
| `/v3/live/status` SHA-256 | `97a87954bb09bc5a…` | `771e9d60a17562e5…` |
| `/v3/live/latest` SHA-256 | `8ef725999221e45d…` | `f475d3926194cc5c…` |
| `/depth` frame 72 (678,571 B) | `015148b1f92f9790…` | `2a1bcd68aa906386…` |
| `/flow` frame 72 (2,112,368 B) | `6bc788dfdaa94a11…` | `2db9069a0d25acd2…` |
| Summary SHA-256 (canonical JSON) | `8afd3a2fa70a8ae2…` | `8afd3a2fa70a8ae2…` (identical) |

- **Schema checks:** after the fix, run detail, `/depth` and `/flow` all validate against C4 v3 with zero errors, as do `/live/status` and `/live/latest`.
- **Summary:** max depth 2.07 m and 0.01 km² flooded, from a near-dry 72 h model forecast.
- **Machine-wide Open-Meteo count:** the separate `:8000` service had made 1,188 calls today when last checked, so the machine total stays well under the 5,000/day scheduler budget.

## 2 Behaviour checks

| Check | Result |
|---|---|
| Refresh during a running cycle (the start-up catch-up) | 202 `{"accepted": false, "state": "already_running"}`; no second run started |
| Manual refresh | 202 `started`, published the manual run above |
| Second refresh within 600 s | **429** `rate_limited`, `Retry-After: 599`, ApiError schema-valid |
| Simulated upstream failure | **Pass.** The cycle stopped with `last_error = {stage: fetch_forecast, message: "Open-Meteo fetch failed (ForcingError)"}` and Open-Meteo health `error`. The last good run `…121126Z-979f9524` stayed on `/v3/live/latest` (200, schema-valid). |
| Retention | Packaged `retention.keep_last` = 16 (2 runs stored). Pruning after 16 runs, of live runs only, is proven by `test_retention_prunes_only_live_runs` (fake clock, passed). |

**How the failure was simulated.** The AI container was recreated with `HTTPS_PROXY`/`HTTP_PROXY` set to `http://127.0.0.1:9`, a closed port. This needed no code change. The CFM snapshot was under 24 h old, so only Open-Meteo was attempted. While the proxy was set, the container's health check (urllib to `localhost`) also went through the proxy and reported unhealthy. The container was recreated without the proxy afterwards and came back healthy.

Related fake-clock tests also passed: `test_failure_keeps_last_good_run` and `test_overlap_lock_and_manual_refresh_window`.

## 4 Boundaries

- **Raw audit:** `DATA_FILES=157; HASH_MATCH=157; MISMATCH=0`.
- **Database:** no shared-database writes. The B11 stack has no database service.
- **Docker volumes:** none deleted (7 before and after). The stack uses bind mounts only.
- **Credentials:** none used.
- **Google key:** none in any `/v3` request or response in any phase. The packaged frontend bundle has no `AIza`, `VITE_GOOGLE` or `GOOGLE_MAPS` strings.
- **Cesium token:** the UI's Cesium ion token is built into the bundle from `frontend/.env.local`, by the UI's design (B48/B52). It is not an API credential of this service.

## 5 Disclaimer encoding (packaged)

| Endpoint (via nginx) | Content-Type | Em dash bytes | Mojibake bytes | Decoded string equals the constant |
|---|---|---|---|---|
| `/v3/live/status` | `application/json; charset=utf-8` | `e2 80 94` present | none | yes |
| `/v3/live/latest` | `application/json; charset=utf-8` | `e2 80 94` present | none | yes |

The UTF-8 bytes of `Model forecast — not an official warning` are `4d6f64656c20666f72656361737420e28094206e6f7420616e206f6666696369616c207761726e696e67`. The earlier "â€”" reports came from clients decoding a charset-less response as cp1252. `/v3` now declares `charset=utf-8` (commit `9b413a2`).

## 3 Packaged UI screenshots

Pending from the UI session: `docs/ui/screenshots/18_live_*` at `http://127.0.0.1:8081/`, run `sim-20261110T121126Z-979f9524`.

## Limitations

- **CPU only.** The packaged run used the CPU image (about 4.6 min per 72 h cycle). The GPU overlay (`docker-compose.gpu.yml`) was not built for B53.
- **Retention.** The packaged stack showed `keep_last = 16` with 2 runs. Pruning past 16 runs was verified in the fake-clock test, not by running 17 real cycles.
- **Failure display.** `last_error` stays visible until the next successful cycle (next scheduled at 15:04Z), by design.
