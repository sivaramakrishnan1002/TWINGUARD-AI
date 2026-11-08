# TwinGuard AI service

Small FastAPI scaffold for the AI-service contract. `/health` reports that the process is up. `/layers` reads registered layers and their recorded row counts from `twinguard.dataset_catalog` using a read-only, short-timeout database connection. The service reads database credentials from the project-root `.env` file and never returns connection details. Forecast, uncertainty, impact, route and scenario are placeholders and return HTTP 501 until implemented.

From `D:\TIWNGUARD`, run this single command to serve locally only:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir services\ai-service --host 127.0.0.1 --port 8000
```

The interactive API description is at `http://127.0.0.1:8000/docs`; the generated OpenAPI document is at `http://127.0.0.1:8000/openapi.json`. The design contract is `docs\api\ai-service.yaml`.

## C4 v3 product API (`/v3`, B47)

`/v3` implements the C4 v3 contract (`docs/api/ai-service.yaml` § `x-c4-v3-product-api`, OD-2026-11-07 / CR-019): status, overview, weather, events, simulations (event, custom rainfall, forecast, what-if), depth frames, buildings, wards, three-state roads, route search, shelters, generated incidents, scenario resources, emergency plan, comparison and static layers. Code lives in `app/v3/`.

- **Engine.** When Lane A's A25 bundle is installed (`data/features/live/a25_static_v1`, override with `TWINGUARD_V3_A25_STATIC`), runs use `services.flood_engine.scenario.run_scenario` on the 120 m citywide grid or the 30 m focus grids. Otherwise they use the A06/A23 600 m grid through `services.flood_engine.solver`. Set `TWINGUARD_V3_ENGINE=a06` to pin the pilot. Lane A's engine is called, never edited.
- **Runs.** One run executes at a time, in a child process (`python -m app.v3.worker`), with at most 4 queued. Identical requests return `state: cached`. Runs, the weather cache and scenario resources are stored under `TWINGUARD_V3_RUNS`.
- **Open-Meteo.** Fetched only for a user-triggered `GET /v3/weather` or `mode=forecast` run. Responses are cached with at least 600 s between fetches; the API answers 429 with `Retry-After` otherwise. There is no background polling, and the unmounted `/live` draft's scheduler was removed.
- **Static bundle.** Roads, buildings and shelters come from `data/features/v3/product_static_v1`, rebuilt with `.\.venv\Scripts\python.exe services\ai-service\app\v3\build_static.py`.

Serve locally with the project data:

```powershell
$env:TWINGUARD_V3_RUNS="data\features\v3\runs"; $env:TWINGUARD_V3_PRODUCT_STATIC="data\features\v3\product_static_v1"; $env:TWINGUARD_LIVE_STATIC="data\features\live\a06_live_static_v1"; $env:TWINGUARD_V3_A25_STATIC="data\features\live\a25_static_v1"; $env:PYTHONPATH="."; .\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir services\ai-service --host 127.0.0.1 --port 8000
```

In the packaged stack (`docker compose -f docker-compose.b11.yml up --build`), the UI reaches `/v3` same-origin at `http://127.0.0.1:8081/api/ai/v3/`. GET, POST and PUT are allowed only on that prefix.

**Limitations.** These are simplified local-inertial models with no storm-drain network and no hydraulic validation. Reservoir and tide what-ifs are forcing proxies. Road states, shelter capacities, incidents and resource plans are derived demo indicators, and incidents are labelled `generated`.

### GPU (optional, OD-2026-11-08)

`TWINGUARD_V3_DEVICE` can be `auto` (the default), `cuda` or `cpu`. `auto` uses CUDA only when it is available and the A25 engine's `run_scenario` accepts a `device` argument; otherwise runs use the CPU, and the A06 pilot is always CPU.
- **One GPU job at a time.** /v3 runs one simulation at a time, which fits the 4 GB card.
- **CPU fallback.** A CUDA error retries the run once on the CPU and is recorded in the run's `provenance.device.fallback_reason`.
- **Reporting.** `GET /v3/status` reports the requested and resolved device in `device`.
- **Docker.** The stack is CPU-only by default. To enable the GPU, install the NVIDIA Container Toolkit (or use Docker Desktop with WSL 2 GPU support), then run:

```powershell
docker compose -f docker-compose.b11.yml -f docker-compose.gpu.yml up --build
```

This builds the AI image with CUDA PyTorch (`--build-arg TWINGUARD_GPU=1`) and adds `gpus: all`.
