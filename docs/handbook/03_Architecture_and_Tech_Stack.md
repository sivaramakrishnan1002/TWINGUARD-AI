# Architecture and technology stack

*Refreshed 10 Nov 2026 (B55) for the final-year product (OD-2026-11-07). The October design notes are kept in the [Decision Log](04_Decision_Log.md) and [Progress and Chronicle](09_Progress_and_Chronicle.md). This chapter describes what runs now.* [repo]

## The pipeline in one line

**Rainfall + reservoirs → flood simulation → 3D digital twin → impact, three-state routing and shelters → what-if comparison**, for Chennai. The owner records this integration as the project's contribution (OD-2026-11-07 §6). Every result is labelled `SIMULATED`, and inputs keep their own source class (`REPLAY`, `MODEL_FORECAST`, `PUBLISHED_SNAPSHOT`, `SCENARIO_INPUT`, `STATIC_REFERENCE`). [repo: `docs/master/FINAL_YEAR_OWNER_DECISIONS.md`, `docs/api/ai-service.yaml`]

```
 Open-Meteo forecast grid ─┐        CFM-DSS reservoir snapshot ─┐ (A28 storage rule, ASSUMPTION)
 IMERG/ERA5 event replay ──┼──► A25 flood engine (120/90 m citywide, 30 m focus; CUDA or NumPy)
 user rainfall / what-if ──┘          │ depth frames, flow (u, v, wse), peak, ward/building/road products
                                      ▼
                AI service  /v3  (FastAPI; run queue, persistent GPU worker, live scheduler)
                                      │  same-origin /api/ai/  (nginx in the package, Vite proxy in development)
                                      ▼
            React UI: 7 tabs, CesiumJS + Google Photorealistic 3D Tiles, badges and live bar
```

## Components

| Component | What it does | Where |
|---|---|---|
| **Flood engine (A25/A26/A27/A28)** | A local-inertial shallow-water solver on the Copernicus GLO-30 surface DEM. Grids: 120 m (or 90 m) citywide, and 30 m nested focus areas (Velachery, Adyar, T. Nagar, Porur). Event, custom, forecast and what-if forcing. 1 or 3 parameter members. | `services/flood_engine/` (Lane A) |
| **CUDA backend (A26)** | Optional PyTorch float32 solver with CUDA-graph time steps. It matches NumPy within tolerance (peak depth < 1 mm, flooded IoU ≥ 0.9995). NumPy stays the default and the fallback. | `services/flood_engine/hires_torch.py` |
| **Flow export (A27)** | Per-frame depth-averaged velocity `u`, `v` and water-surface elevation (EGM2008), cell-centred, int16 × 0.01. | `flow.npz` per run |
| **Reservoir coupling (A28)** | Rule `A28-RES-STORAGE-v1` turns the CFM-DSS storage percentage into an **assumed** outlet inflow: none below 90 % full, a linear ramp to 100 %, then 2 × Q_ctrl. It is never shown as an observed release. | `services/flood_engine/reservoir_coupling.py` |
| **AI service, C4 v3 (B47/B49/B51)** | 31 paths / 33 operations, including status, overview, weather, events, simulations, depth, flow, buildings, wards, roads, routes, shelters, incidents, emergency plan, scenario resources, comparison, static layers and live endpoints. | `services/ai-service/app/v3/`, contract `docs/api/ai-service.yaml` |
| **Run manager** | Runs one simulation at a time with up to 4 queued. Identical requests return `cached`, and results are stored in a run store. | `app/v3/runs.py` |
| **Persistent GPU worker (OD-2026-11-08c)** | One long-lived child process warms CUDA once and frees cached GPU memory between jobs (one GPU job at a time on the 4 GB card). A crash or CUDA error triggers one CPU rerun with `fallback_reason` recorded. | `app/v3/gpu_worker.py` |
| **Live scheduler (CR-021)** | Runs a 72 h citywide forecast every 3 h, plus a start-up catch-up and manual refresh (at most once per 600 s). Keeps the last 16 live runs and the last-good run, records `last_error`, and counts Open-Meteo calls against a 5,000/day budget. | `app/v3/live.py` |
| **Decision products** | Three-state roads (passable / blocked / unknown; A21/A08 rule), scipy Dijkstra routes with a dry baseline, shelter reachability and allocation (assumed capacities), incidents generated from results (`generated: true`), and a greedy plan for owner-set resources (`SCENARIO_INPUT`). | `app/v3/analysis.py` |
| **UI (B48/B52)** | React, Vite and Tailwind. A dark control-room layout with 7 tabs, CesiumJS with Google Photorealistic 3D Tiles (attribution and logo visible), flow-animated water, and a live bar and run badge. | `frontend/` (UI session) |
| **Package (B11)** | Docker Compose: nginx frontend (`:8081`), AI service (`:8000`), backend (`:8080`). Bind-mounted read-only data and one writable run store. Optional GPU and always-on overlays. | `docker-compose.b11.yml`, `docker-compose.gpu.yml`, `docker-compose.always-on.yml` |

## Data flow of a live cycle

1. The scheduler fetches the Open-Meteo multi-model lattice (about 297 counted calls) and saves the snapshot with the run.
2. It reuses the CFM-DSS reservoir snapshot if it is under 24 h old; otherwise it reads it once (2 requests).
3. The engine runs a 72 h forecast at 120 m with the A28 coupling, on the persistent GPU worker (about 31 s engine time on an RTX 3050) or on CPU (about 4.6 min).
4. The result is published as `run_kind: LIVE_FORECAST` (`mode: live`) with a `live` block: issue time, valid window, reservoir `source_date`, coupling rule and the disclaimer "Model forecast — not an official warning".
5. The UI polls `GET /v3/live/status` every 60 s and switches to the new live run unless the user pinned another run.

## Technology

| Layer | Choice |
|---|---|
| Engine | Python 3.12, NumPy, SciPy (road connectivity), optional PyTorch 2.14.1 + CUDA 12.6 (`requirements-gpu.txt`) |
| API | FastAPI 0.162, Uvicorn, Pydantic 2 |
| UI | React, Vite, Tailwind, CesiumJS with Google Photorealistic 3D Tiles |
| Packaging | Docker Desktop 29.x, Compose, nginx 1.27 |
| Data | EPSG:32644 grids, WGS84 GeoJSON, run stores in `data/features/v3/` (git-ignored) |
| Earlier work | The PostgreSQL/PostGIS database, Kafka/Redis replay (Track B) and Spring backend remain from earlier phases. The product UI uses only the AI service. |

## What it is not

It is not an operational warning service. Model skill is not validated against observed depths, there is no storm-drain network, and building heights are mostly estimated. See [Risks and Limitations](13_Risks_and_Limitations.md).
