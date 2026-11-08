# Final-year architecture rebaseline — owner decisions requested

**Status:** awaiting authorized project-owner and domain-owner decisions. This is a request, not an approval. It does not authorize implementation, live feed access, API exposure, data acquisition, credential use, gate changes, release, or deployment. See [architecture rebaseline](FINAL_YEAR_ARCHITECTURE_REBASELINE.md) and CR-013.

Please record a decision and evidence for each item. “Unknown / defer” is valid and keeps dependent work blocked. Do not treat silence as approval.

| ID | Decision needed | Options / evidence requested | Blocks |
|---|---|---|---|
| D1 | Authoritative study boundary and vertical reference | Name/version/hash of boundary; vertical datum; transformation/geoid source and validation. The current older CMA boundary and GLO-30 DSM are provisional and insufficient as a verified hydraulic terrain base. | Final domain, terrain, boundary conditions, city-scale metrics |
| D2 | Rainfall source and access | Approve replay-only source(s), or identify an authorized gauge/IMD source, owner, terms, cadence, timestamp/timezone semantics, credentials custodian, and permitted retention. | Ingestion and forcing |
| D3 | Reservoir source and access | Identify authoritative source owner and provide written license/access, measurement-time/timezone semantics, level/storage/release/gate units and cadence. If not available, approve a clearly bounded replay-only input and prohibit claims about unobserved release. | Reservoir forcing and live-style update |
| D4 | Flood validation references and rights | Identify held-out events with licensed, date-matched observed extent and preferably depth; provide coverage, resolution, units, uncertainty, hashes, and permission. Confirm permissions for UNOSAT/HDX, SAR, and PDF-derived labels. | Scientific validation and any performance claim |
| D5 | Model domain and physical scope | Approve what hydrology/hydraulics are in scope; drainage/culverts and external catchment assumptions; simplified-model disclosure; independent domain reviewer. | Lane A model specification |
| D6 | Resolution, time step, thresholds, and failure criteria | Approve only after benchmark/stability/convergence results; name domain reviewer and preregistration process. Candidate targets in the plan are discussion values, not accepted criteria. | Lane A acceptance and G5/G6 criteria proposals |
| D7 | Hardware and runtime budget | Identify available CPU/GPU/RAM/storage, allowed environment, budget, target scenario area and update latency; reconcile prior conflicting GPU availability records by fresh owner evidence. | Feasibility benchmark and package design |
| D8 | Prototype source mode | Approve replay-only demonstration, or identify which live feed may be used and the explicit authorization, terms, rate limits, secret handling and rollback boundary. Replay is the default until approved. | Lane B ingestion work |
| D9 | UI audience and deployment boundary | Local examiner-only package or another specified audience; network binding, authentication, accessibility standard, data/privacy constraints. Public deployment is not presumed. | Backend/UI packaging and security review |
| D10 | Novelty claim review | Assign literature-review owner, databases/search window/inclusion criteria, and independent reviewer. Approve or reject the provisional uncertainty-aware coupling hypothesis only after review. | Final research novelty statement |
| D11 | Gate/change-control route | Decide whether this remains a planning proposal under existing gates or needs a separately versioned gate proposal. Any change to G5/G6 or frozen contracts requires formal change control; no change is requested here. | Future task registration and gate acceptance |

## Required response record

For each D1–D11, record `approved`, `rejected`, or `deferred`; decision-maker and date; exact source/permission evidence; scope and exclusions; affected owners; and follow-up task IDs. A decision does not itself satisfy implementation acceptance or a gate. After decisions, the Integrator must register narrowly scoped tasks with explicit owners, outputs, dependencies, acceptance criteria, evidence paths, and conflict checks before implementation starts.


## Scoped owner decision recorded 2026-11-06

- **D2 approved in part:** Open-Meteo Forecast API (`/v1/forecast`) for Chennai model-derived current weather context and hourly precipitation in the local educational prototype, under its published non-commercial terms and CC BY 4.0 attribution. This does not authorize an IMD/gauge source or use as a validated rainfall observation.
- **D8 approved in part:** the UI may retrieve this public weather-model context directly by HTTPS GET with no credentials, no persistence, at most every 30 minutes while Overview is active. This does not authorize a continuously recomputed flood model or operational outputs.
- **D3 remains deferred:** no reservoir source selected or authorized.

See [CR-014](CR-014_OPEN_METEO_WEATHER_CONTEXT.md) for endpoint fields, timestamp meanings, terms, evidence, and exclusions. The project owner authorized this limited source/use in the instruction “okay proceed with open metro source.”

## OD-2026-11-07 — Bachelor's final-year product rebaseline (recorded 2026-11-07)

**Decision-maker:** project owner, relayed through the coordinator session. Recorded by the Integrator. Implemented under [CR-019](CR-019_PRODUCT_REBASELINE_UI_API.md).

1. **Project scope:** TwinGuard is a bachelor's final-year project. It is not an operational or research-grade service.
2. **Target product:** the owner's 13 reference UI images, as 7 tabs in a dark control-room style: 1 Situation Overview, 2 Flood Simulation, 3 Emergency Support, 4 Road Routing, 5 What-if Simulation, 6 Reservoir Monitoring, 7 Digital Twin 3D City.
3. **3D:** Google Photorealistic 3D Tiles through CesiumJS.
   - The owner supplies the Map Tiles API key in `frontend/.env.local` as `VITE_GOOGLE_MAPS_API_KEY`. It is never committed (git-ignored via `*.local`), and no API endpoint returns or accepts it.
   - Internet access at demo time is acceptable.
   - Google attribution and the Google logo must stay visible, as Google's terms require.
4. **Caveat policy (relaxed):**
   - `done_with_caveats` counts as done.
   - The UI shows one small "DEMO / SIMULATION" badge instead of long limitation text. There are no "unproven/not validated" banners on every card.
   - Reports keep only a short Limitations section for the thesis. Earlier gate reports remain as historical evidence.
5. **Still binding:**
   - No fabricated value may be shown as observed. Every result carries a `source_mode`.
   - Emergency resources (boats, teams, vehicles) are owner-set scenario inputs (`SCENARIO_INPUT`).
   - Incidents and alerts are generated from simulation results and labelled as generated.
6. **Novelty claim (thesis wording):** "an integrated rainfall + reservoir → flood simulation → 3D digital twin → impact, three-state routing and shelter decision pipeline with what-if scenarios for Chennai" is the project's contribution. This supersedes D10's pending literature-review gate for thesis wording.
7. **Open-Meteo retrieval:** this replaces CR-015's "one snapshot, no polling" limit.
   - On-demand Open-Meteo fetches are allowed for user-triggered runs, with response caching and a minimum interval of 600 s (10 min).
   - There is no background polling.
   - Published Open-Meteo terms, CC BY 4.0 attribution and rate limits still apply.

**Follow-up tasks:**
- A25: high-resolution simulation for 3D (Lane A).
- B47: simulation and decision API (Lane B).
- B48: reference-design UI with Google 3D Tiles (ui session).
- The G4 repair chain A24/I26/B46 is superseded.
- Contract: C4 v3 in `docs/api/ai-service.yaml` § `x-c4-v3-product-api`, summarised in `contracts/c4_openapi_v3.md`.

## OD-2026-11-08 — GPU use (recorded 2026-11-08; answers D7 for hardware)

**Decision-maker:** project owner, relayed through the coordinator session. Recorded by the Integrator.

- **Hardware:** NVIDIA GeForce RTX 3050 Laptop GPU, 4 GB VRAM, driver 621.01. This is the owner's evidence, and it supersedes earlier conflicting records. For example, A10 recorded that `nvidia-smi` lacked permissions and that the venv PyTorch build had no CUDA.
- **Policy:** use the GPU whenever it helps. **CPU must remain a supported fallback.** Every GPU path selects the device at runtime and falls back cleanly when CUDA is unavailable, and tests must pass on CPU-only machines.
- **Permitted per lane:**
  - Lane A may add an optional CUDA backend (PyTorch or CuPy) to `services/flood_engine/`.
  - Lane B may add a device option and a GPU job queue in `/v3`. Because of the 4 GB VRAM, keep one GPU job at a time and make no new API contract fields without an Integrator contract edit.
  - The UI may request a high-performance WebGL context.
- **Dependencies:** the Integrator reconciles any new pins (for example, a CUDA PyTorch or CuPy wheel) when lanes report them. GPU wheels go in an optional requirements file or an extra so that the CPU install stays unchanged. Lanes run `pip check` and record the exact wheel and CUDA versions.

## OD-2026-11-08b — G5 scope revised (recorded 2026-11-08)

**Decision-maker:** project owner ("B"), relayed through the coordinator session. Recorded by the Integrator.

- **Revised G5:** G5 becomes the product-pipeline end-to-end check: an archived event input goes through an engine run, `/v3` and the packaged UI.
- **CR-012:** its POONDI date-only replay is kept only as an optional secondary check.
- **Records:** CR-020 and the revised B13 acceptance in `STATE.json`.

**A26 GPU benchmark (OD-2026-11-08 follow-up):** Lane A's A26 (commit 887d089) measures 2.25-3.67x end-to-end speed-up on the RTX 3050 Laptop GPU.
- **Match with NumPy:** mass balance <= 6e-5, peak-depth differences < 1 mm, flooded IoU >= 0.9995.
- **Memory:** peak VRAM 4-30 MB.
- **Fallback:** NumPy remains the default and fallback.
- **Dependencies:** none beyond `requirements-gpu.txt`.
- **Report:** `docs/FLOOD_ENGINE_GPU_BENCHMARK.md`.

## OD-2026-11-08c — Persistent GPU engine worker (recorded 2026-11-08)

**Decision-maker:** the coordinator session, under the owner's delegation, relayed to the Integrator.

- **Decision:** the AI service keeps a persistent engine worker warm, so runs skip CUDA start-up. Lane B implemented it in B47 commits dec0abe and df96bf2.
- **Setting:** `TWINGUARD_V3_WORKER` = `persistent` | `per_run` | `auto`. The default `auto` resolves to persistent when runs resolve to CUDA, otherwise per-run.
- **Fallback:** CPU remains the supported fallback (OD-2026-11-08).
- **Measured:** a warm 48 h citywide run takes 17 s end to end, against 31 s cold. tests/ai_service: 148 passed.
- **Contract:** additive optional `EngineStatus.worker` {mode, state, device, pid, jobs_done, restarts, warmup} in C4 v3.
