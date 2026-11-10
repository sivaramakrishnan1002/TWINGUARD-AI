# I27 — Round 2 live-stage review (CR-021 / OD-2026-11-10) — 2026-11-10

**Decision: PASS_WITH_CAVEATS.** One evidence item is still open: the packaged-UI screenshots (follow-up task **B54**). Under OD-2026-11-07, `done_with_caveats` counts as done.

Reviewer: Integrator (Lane I). Scope: A28, B51, B52, B53 against CR-021 and OD-2026-11-10.

## Task review

| Task | Result | Integrator checks |
|---|---|---|
| **A28** reservoir coupling and forecast checks (bf50c38, done) | PASS | Rule `A28-RES-STORAGE-v1` (`pipelines/a25_hires/A28_RESERVOIR_COUPLING.md`): 0 below 90 % storage, a ramp to Q_ctrl at 100 %, then 2 × Q_ctrl. The rule doc states CFM-DSS publishes no release figures, and the inflows are labelled ASSUMPTION / SCENARIO_INPUT, never observed. Missing or stale (> 48 h) snapshots give zero inflow. The forecast forcing was checked on the 120 m grid (alignment, mm/h, 72 h, coverage 1.0). A live-style run had mass balance 1e-6 and the no-rain control was near-dry. 35 engine tests pass. |
| **B51** live scheduler and `/v3/live/*` (d987199, 818c7fc, done) | PASS | The three operations are mounted exactly as planned and promoted to top-level `paths` (Integrator, bad02a5). Validator: 34 paths and 36 operations. Master, AI-service and packaging tests: 200 passed, including runtime parity. Fake-clock tests cover catch-up, the overlap lock, the 600 s refresh window, retention, the 5,000-call budget, last-good fallback and the daily CFM-DSS limit. |
| **B52** live-first UI (b69c371; follow-up 64bd986; done) | PASS (dev-server evidence) | Run-kind badge; the disclaimer on every tab; updated and next times; source-health dots; Refresh handling 202/429/503; 60 s polling with auto-switch that respects a user's pinned replay or what-if run; a `last_error` banner; A28 inflow labelled ASSUMPTION. UI tests 46/46; 0 console errors. Screenshots `docs/ui/screenshots/20_live_*` come from the Vite dev server. |
| **B53** packaged live-cycle verification (bb6e690; fix d672eae; done_with_caveats) | PASS_WITH_CAVEATS | Packaged B11 stack through nginx, CPU image, isolated run store. Catch-up run `sim-20261110T120422Z-1a781dbd` (277 s) and manual run `sim-20261110T121126Z-979f9524` (286 s): LIVE_FORECAST, engine 2.1.0, A28 applied (0 m³/s), 594 Open-Meteo calls in the container. Refresh during a cycle returned `already_running`; a second refresh returned 429 with `Retry-After: 599`; a simulated Open-Meteo failure kept the last good run and set `last_error`; `keep_last` is 16. The disclaimer is exact UTF-8 with `charset=utf-8`. Raw audit 157/157; no Google key. **Integrator parse of `B53_LIVE_CYCLE_EVIDENCE.json`:** 22 calls (200×18, 202×3, 429×1). The only 3 schema errors are in `catchup_initial`, the deliberately kept capture from before the d672eae fix, where the reservoir `fetched_at` was `+00:00` with microseconds instead of RFC 3339 `Z`. Every post-fix call validates. |

## CR-021 compliance

| Rule | Evidence | Status |
|---|---|---|
| 3 h cycle with start-up catch-up | B51 tests; B53 catch-up run | PASS |
| Manual refresh at most once per 600 s; no overlap | B53 429 and `already_running`; B51 tests | PASS |
| Keep the last 16 runs, pruning live runs only | `keep_last` 16 packaged; pruning shown by fake-clock test only | PASS_WITH_CAVEATS |
| Open-Meteo budget < 5,000/day, one back-off on 429 | Counter per UTC day. In-container 594 plus the separate `:8000` service's 1,188 is about 1,800 machine-wide. | PASS |
| CFM-DSS at most daily; snapshot kept only in run provenance; inflows are assumptions | B53 reused the < 24 h snapshot; A28 labels | PASS |
| Disclaimer "Model forecast — not an official warning" | Exact bytes on the packaged stack; on every UI tab | PASS |
| `run_kind` separate from `source_mode` | Results SIMULATED; inputs MODEL_FORECAST, PUBLISHED_SNAPSHOT or SCENARIO_INPUT | PASS |
| No credentials; no Google key | B53 boundary scan; no repository secrets | PASS |

## Caveats (thesis Limitations)

1. **Packaged-UI screenshots** (`18_live_*`) are not yet in the repository. The UI session is capturing them under follow-up **B54**.
2. **CPU only.** The packaged verification ran on the CPU image (about 4.6 min per 72 h cycle). The GPU overlay was not built for B53. Local GPU runs take about 31 s for the engine.
3. **Retention.** Pruning past 16 runs is shown by a fake-clock test, not by 17 real cycles.
4. **Two live services.** The local `:8000` launcher and the packaged stack each run their own live scheduler with their own Open-Meteo counter. Run only one live scheduler at a time (`TWINGUARD_V3_LIVE=0` on the other) to stay comfortably inside the free tier.
5. **Cesium ion token.** It is compiled into the frontend bundle from git-ignored `.env.local`. This is carried to I04 (do not publish images or bundles as built).
6. **Forecast.** The model forecast is a numerical weather-model forecast pushed through a simplified 120 m hydraulic model. It is not an official warning, and its skill is not validated.

## State changes

I27 is finished `done_with_caveats`. B54 (UI session) is registered for the packaged screenshots. Round 4 tasks and the G6 owner checklist are registered separately (`G6_OWNER_DECISION_CHECKLIST.md`).
