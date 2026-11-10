# G5 Gate Review — product-pipeline replay (CR-020) — 2026-11-10

**Current gate decision: FAIL (one item open)**

Reviewer: Integrator (Lane I) session. Scope per `docs/master/GATES.md` G5 as revised by CR-020 (owner decision OD-2026-11-08b): one source-identified archived input goes through a flood-engine run, the C4 v3 `/v3` API and the **packaged UI**, with source input distinguished from simulated output. Required task: B13, which is `done_with_caveats` (commit d68aa15; report `docs/trackb/B13_E2E_SCENARIO.md`; evidence `docs/trackb/B13_PRODUCT_REPLAY_EVIDENCE.json`; script `tests/e2e/b13_product_replay.py`).

Every criterion passes except item 4, where the UI evidence was captured on the development server rather than the packaged UI. G5 therefore stays `not_ready`. One small repair task, **B50**, is registered and added to G5's requirements, so `gate_check.py G5` fails closed until it is done.

## Criterion review (B13 acceptance, CR-020)

| # | Criterion | Decision | Evidence and Integrator checks |
|---|---|---|---|
| 1 | Input: one source-identified archived input | PASS | A25 catalogue `data/features/live/a25_static_v1/shared/events.json`. The Integrator recomputed SHA-256 `e402c3f5…37d61`. Bundle `manifest.json` SHA-256 `a4bced11…bf48a`, also recomputed. Record `2015-12-01`: 72 × 60 min from 2015-11-30T00:00Z, 351.54 mm, `source_mode` REPLAY. No Open-Meteo input was used. |
| 2 | Engine run through the packaged stack | PASS_WITH_CAVEATS | B11 compose, CPU image, nginx `/api/ai/v3/`, A25 120 m engine 2.1.0. Runs: primary 48 h `evt-20261108T152128Z-59eba744`; acceptance-body 24 h `…415999af`; fresh 36 h `…49db828b`, computed in the container on CPU in 161.2 s. **Caveat:** the primary and acceptance runs reused cached engine output first computed on CUDA. Their `provenance.device` describes that original computation. The fresh 36 h run is the in-package compute evidence. |
| 3 | Seven `/v3` outputs, schema-valid, hashed | PASS | `/depth`, `/flow`, `/wards`, `/roads`, `POST /v3/routes`, `/shelters` and `/incidents` all returned 200 with a SHA-256 per body. The Integrator parsed the evidence JSON: 74 recorded calls with no schema failures; statuses were 200×55, 202×9, 422×4, 404×2, 503×2 and 409×2. |
| 4 | **Packaged UI** Tabs 2 and 7 show the run, with flow animation and labels; screenshots | **FAIL (evidence gap)** | B48 screenshots `docs/ui/screenshots/16_g5_flood_simulation.webp` and `16_g5_digital_twin.webp` show run `evt-20261108T141229Z-fb36a1cd`. The Integrator reviewed `16_g5_flood_simulation.webp`: it shows the run_id, REPLAY input, SIMULATED results, modelled `/flow`, the DEMO / SIMULATION badge and Google attribution. All seven outputs of `fb36a1cd` are content-identical to the packaged primary run. **However, the screenshots come from the Vite development server.** The packaged UI (`http://127.0.0.1:8081/`) was checked only by fetching its bundle (200; contains `/api/ai/v3` and the badge; no key). The packaged production build (lazy-loaded Cesium, static assets served by nginx, the 3D tiles) has not been seen rendering Tabs 2 and 7. → repair task **B50**. |
| 5 | Determinism | PASS | A repeated identical request returned `state: cached` with the same run_id, and all seven hashes were byte-identical. |
| 6 | Fail-closed | PASS | Unknown run 404; flow on a pre-2.1.0 run 503; bad frame 422 on `/depth` and `/flow`; a queue over its limit returned 409 on the sixth request. Every error body was a valid ApiError with no partial body. |
| 7 | Boundaries | PASS | Lane B's raw audit: 157/157. Integrator rerun: see Checks. No database service in B11 and no shared-database writes; bind mounts only, so no volume was deleted; no Google key in 47 scanned calls, and the evidence JSON contains no `AIza`. |
| 8 | Contract tidy-up (Integrator) | PASS (done in this review) | `/replay-alerts/{event_id}` is now `x-current-runtime-status: 200` with `x-runtime-availability: available_in_local_B11_package` in both `docs/api/ai-service.yaml` and `docs/api/backend.yaml`. `tests/master/test_api_contract_projection.py` and `tests/master/test_b13_replay_projection.py` were updated to match. The flow-parameter drift was already fixed in B49 (9cb4054). |
| — | Optional secondary check: CR-012 POONDI replay | PASS | `GET /api/ai/replay-alerts/replay:POONDI:date:2015-12-01` returned 200. The body is C4-v2, REPLAY. |
| — | B13 finding: stale limitation text | Fixed | Lane B commit 8686f12: run limitations now describe the engine actually used. |

## Repair task registered

**B50 — Packaged-UI G5 screenshots (UI session, lane B), `ready`, depends on B13.**
- Start the B11 package (Docker Desktop must be running; the owner or coordinator starts it).
- Open `http://127.0.0.1:8081/` (nginx, production bundle), not the development server.
- Capture Tabs 2 and 7 for run `evt-20261108T152128Z-59eba744`, or for `fb36a1cd` if both are listed, with the flow animation playing.
- The screenshots must show the run_id, the REPLAY input, SIMULATED results, generated incidents, the badge, and the Google logo and credit.
- Save them under `docs/ui/screenshots/` as `17_g5_packaged_*`, and note the browser console has no errors.
- If the packaged build fails where the development server worked, record and fix it in the UI session's paths.

G5 requires `B13` and `B50`.

## Gate checks (2026-11-10, this session)

| Check | Command | Result |
|---|---|---|
| Contract validator | `.venv\Scripts\python.exe tools\validate_api_contracts.py` | PASS. AI service: 31 paths, 33 operations. Backend: 11 paths, 12 operations. |
| Master, AI-service and packaging tests | `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib -p no:cacheprovider tests/master tests/ai_service tests/packaging` | **189 passed**, 109 subtests passed |
| Raw audit | `.venv\Scripts\python.exe tools\audit_raw_logs.py` | see the closing line appended below |
| State | `tools/master/verify_state.py`; `tools/master/gate_check.py G5` | recorded after registration below |
| Packaged end-to-end run | not rerun | Docker Desktop is stopped. The review relies on Lane B's recorded run and evidence JSON, which the Integrator parsed and hash-checked against the input files. |
| Backup | not required | No database write, migration or Docker operation by the Integrator. |

## Decision

G5 is **FAIL** with one open item and stays `not_ready`. The pipeline itself is proven end to end on the packaged stack at the API level: archived input → engine → `/v3`. The remaining gap is visual confirmation that the packaged production UI renders Tabs 2 and 7 for that run. Once B50 provides it, re-run `gate_check.py G5` and close G5 as PASS_WITH_CAVEATS, carrying forward these caveats:
- the primary run reused cached CUDA output (the fresh CPU compute is evidenced separately);
- the GPU image has not been built.

**Integrator raw audit (2026-11-10):** `DATA_FILES=157; DATA_BYTES=30544672450; HASH_MATCH=157; NO_COMPARABLE_HASH=0; MISMATCH=0`. `verify_state.py` exit 0. `gate_check.py G5`: "G5 CLOSED: tasks incomplete: B50", as intended.


## G5 re-review after B50 — 2026-11-10

**Current gate decision: PASS_WITH_CAVEATS**

This supersedes the FAIL decision above, which is kept as history. `STATE.json` records G5 as `ready`.

**Criterion 4 (packaged UI) is now PASS.** B50 (done, commit 720264b) supplies evidence from the B11 nginx package at `http://127.0.0.1:8081/`, not the Vite development server.
- **Image:** frontend image `local/twinguard-b11-frontend:0.1.0` (`3c815aa8cc7b`), rebuilt from the current UI.
- **Screenshots:** `docs/ui/screenshots/17_g5_packaged_flood_simulation.webp` and `17_g5_packaged_digital_twin.webp` show run `evt-20261108T152128Z-59eba744`, the packaged primary run from B13, at frame 72 (T+36 h).
- **What they show:** the run_id, the REPLAY rainfall input, SIMULATED results, `MODELLED /flow`, the generated-incidents layer, the DEMO / SIMULATION badge, the Google Maps logo and credit, and the corrected A25 120 m limitation text. The UI session reports 0 console errors. The fix needed for the package (`frontend/.dockerignore`) is recorded.

**Integrator verification against the running package (read-only GETs, 2026-11-10):**

| Check | Result |
|---|---|
| UI `/` | 200 |
| Entry bundle `assets/index-DpsSUc_K.js` | SHA-256 starts `5ce4a2d38fe62924`, matching the UI session's report. 0 Google `AIza` keys. |
| `GET /api/ai/v3/simulations/evt-20261108T152128Z-59eba744` | completed, SIMULATED, engine `twinguard-v3-engine/1.1.0` / `twinguard-flood-engine/2.1.0`, inputs REPLAY + STATIC_REFERENCE |
| `GET …/flow?frame_index=72&stride=4` through nginx | 200 |
| Integrator review of both screenshots | the labels above confirmed |
| Repository secret scan | no Google or Cesium token is tracked. `frontend/dist/` and `frontend/.env.local` are git-ignored. |

All eight CR-020 criteria now pass: 1, 3, 4, 5, 6, 7 and 8 PASS; 2 PASS_WITH_CAVEATS. The optional CR-012 POONDI check also passed.

**Caveats carried forward (thesis Limitations; G6/I04):**
1. **Reused GPU output.** The primary run (and the acceptance-body run) reused engine output computed earlier on CUDA, so its `provenance.device` and the UI's "CUDA" label describe that original computation. In-container CPU compute is evidenced separately by `evt-20261108T152132Z-49db828b` (161 s).
2. **GPU image not built.** The optional GPU image (`docker-compose.gpu.yml`) has not been built.
3. **Cesium ion token in the bundle.** The token is compiled into the packaged frontend bundle at build time from the git-ignored `.env.local`. It is not committed, and the image is local. Any release, publication or image push under I04 must use a URL-restricted token or rebuild without it. Do not push `local/twinguard-b11-frontend` images as built.
4. **Demo build override.** The UI session's package used a local compose override that only removes ai-service's host port `:8000`. Nginx-to-ai-service traffic over the compose network is unchanged.

**Checks:**
- `gate_check.py G5` after the state update: recorded in the line below.
- Master, AI-service and packaging tests: 189 passed (earlier today, with no contract changes since).
- Raw audit: 157/157 (Integrator, earlier today).
- No database write, migration, Docker volume deletion, tag or push by the Integrator.

`gate_check.py G5` after the update: "G5 READY for integrator gate checklist; all listed task prerequisites are complete". `verify_state.py`: exit 0.
