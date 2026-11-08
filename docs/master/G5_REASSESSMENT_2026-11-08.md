# G5 reassessment and revised-B13 proposal — 2026-11-08

**Status:** Integrator proposal. **G5 stays `not_ready`.** Changing G5's definition (in `GATES.md` and CR-012) needs a project-owner decision. This document does not execute any lane's work.

## Current G5 definition and evidence

`GATES.md` G5 requires one specific end-to-end replay. B13 must take one uniquely selected, source-backed archived **reservoir observation** with date-only C3 semantics and pass it through approved processing, a mounted read-only backend route, and the **packaged UI**. The UI must keep the REPLAY input separate from any derived output. CR-012 fixes the selector `replay:POONDI:date:2015-12-01`.

| Item | State on 2026-11-08 |
|---|---|
| B28 fixture (archived row, hashes) | done_with_caveats (6cbe448) |
| I22 C4 v2 projection | done_with_caveats (7fec84d) |
| B27 vertical slice: AI `GET /replay-alerts/{event_id}` and backend `B13ReplayController` | done_with_caveats (2d14e13). Mounted in code. The OpenAPI annotations still say `unexposed`. |
| B13 dependencies (B02 … I22, 16 tasks) | **all done or done_with_caveats.** The `blocked_prerequisite` status was stale. |
| Packaged UI | **Gap.** The B48 rebuild (OD-2026-11-07, running) no longer imports `frontend/src/ui/replay/B13ReplayView.tsx`, and `frontend/nginx.conf` has no `/replay-alerts` route. The packaged product therefore does not currently show the G5 replay. |
| Packaged stack | Docker engine 29.8.2 is available again, but no image has been rebuilt since B47/B49 (recorded B47 limitation). |
| /v3 product API | B47 (d5a45e9 … e847149) and B49 (17bf87c) are mounted. All 20 C4 v3 operations are promoted. The UI calls the real `/v3` (0b7173f). |

**G5 cannot close as written.** No packaged end-to-end run of the current stack exists, and the current UI has no replay view.

## Options for the owner

**A. Keep G5 as written (the POONDI date-only observation).**
- B48 restores a replay panel, for example in Tab 6 Reservoir Monitoring, that shows the archived observation (REPLAY, `source_date`, unknown time and timezone) separately from the derived rule output.
- Lane B then runs B13 on the rebuilt package.
- This is the smallest change to the gate. However, it exercises a path the demo barely uses: it produces no flood output, and none is invented.

**B. Revise G5 to the product pipeline (recommended; needs a CR, e.g. CR-020).**
- One archived or forecast input goes through an engine run, then `/v3`, then the packaged UI, keeping G5's key rule that source input stays distinct from derived output.
- This tests what the owner demos. It builds on B47, B49 and A25 evidence that already exists, and is consistent with OD-2026-11-07.
- The POONDI replay route stays as an optional secondary check. It is mounted, but needs no UI under option B.

## Proposed revised B13 acceptance (option B)

Owners:
- **Lane B** executes B13 (packaging and runtime evidence).
- **The UI session** (B48) supplies the run view and labels.
- **The Integrator** reviews and runs `gate_check`.

The task ID stays B13, with its scope revised. Acceptance:

1. **Input:**
   - Use one source-identified input: the saved event `2015-12-01` from `services/ai-service/app/v3/events.json` (archived IMERG daily totals with the ERA5 hourly profile, `source_mode: REPLAY`).
   - Optionally, also use one cached Open-Meteo forecast snapshot (`MODEL_FORECAST`).
   - Record the source file hash and the selected record.
2. **Engine run:**
   - Send `POST /v3/simulations {"mode":"event","event_key":"2015-12-01"}` through the **packaged** stack: B11 compose, with nginx `/api/ai/v3/` and the CPU image. Optionally repeat on the GPU image.
   - Record `run_id`, `forcing_sha256`, engine version (A25 2.1.0, or the A06 fallback if that was used), `Provenance.device`, and wall time.
3. **Outputs through /v3:**
   - Call `/depth`, `/flow`, `/wards`, `/roads`, `POST /v3/routes`, `/shelters` and `/incidents` for that run.
   - Validate each body against C4 v3 and record a SHA-256 for each body.
4. **Packaged UI:**
   - Tabs 2 (Flood Simulation) and 7 (Digital Twin 3D City) show that run_id, including flow animation.
   - The input is labelled REPLAY (or MODEL_FORECAST), and every result SIMULATED. Generated incidents are labelled as generated. The DEMO / SIMULATION badge and Google attribution are visible.
   - Capture screenshots under `docs/ui/` or `docs/figures/`.
5. **Determinism:** repeating the same request returns `state: cached` with the same run_id and identical output hashes.
6. **Fail-closed checks:** an unknown run returns 404, flow on a pre-2.1.0 run returns 503, an invalid frame returns 422, and an over-limit queue returns 409. No partial bodies.
7. **Boundaries:**
   - `data/raw/` is unchanged (raw audit 157/157).
   - No shared-database writes and no Docker volume deletion.
   - The Google key does not appear in any request or response.
8. **Contract tidy-up at closeout:**
   - The Integrator corrects the stale `unexposed` annotation on `/replay-alerts/{event_id}` together with `tests/master/test_api_contract_projection.py`.
   - Lane B drops (or the Integrator adds) the flow operation's undocumented `resolution`/`focus_area` query parameters.

G5 closes when B13 meets these criteria and the Integrator review passes.

## Interim state change

B13 moves from the stale `blocked_prerequisite` to `blocked_manual`. All its dependencies are done; it is waiting only for the owner to choose option A or B. Nothing else changes.
