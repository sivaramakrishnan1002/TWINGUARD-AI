# Runbook

*Added 10 Nov 2026 (B55). All commands run from the repository root `D:\TIWNGUARD`. No keys or tokens appear in this handbook: the UI's 3D token lives in the git-ignored `frontend/.env.local`, and the API never accepts or returns it.* [repo: `services/ai-service/README.md`]

## Choose one way to run it

Run **exactly one live scheduler at a time**. The local launcher and the packaged stack each keep their own Open-Meteo call counter, and both bind `127.0.0.1:8000`. To run both, set `TWINGUARD_V3_LIVE=0` on one of them and remove its `:8000` host port.

### A. Local service with GPU (recommended for the demo)

```powershell
powershell -ExecutionPolicy Bypass -File services\ai-service\start_live.ps1 -Background
```

- **What it starts:** the AI service on `http://127.0.0.1:8000`, with `TWINGUARD_V3_LIVE=1`, `TWINGUARD_V3_DEVICE=auto` and `TWINGUARD_V3_WORKER=auto` (persistent GPU worker when CUDA is available).
- **Detached:** it survives closing the terminal. A service started from a Claude session instead stops when that session ends.
- **Logs:** `data\features\v3\logs\ai-service-<timestamp>.log`.
- **Stop:** `start_live.ps1 -Stop`. `start_live.bat` takes the same options.
- **Second copies:** it refuses to start one if something already answers on the port.
- **Auto-start:** add a Task Scheduler "At log on" task that runs the same line.
- **UI in development:** run `npm run dev` in `frontend/`. The Vite proxy sends `/api/ai/*` to `127.0.0.1:8000`; set `TWINGUARD_AI_URL` only if the service runs elsewhere.

### B. Packaged stack (B11)

```powershell
docker compose -p twinguard-b11 -f docker-compose.b11.yml up -d --build --wait
```

- **Ports:** UI at `http://127.0.0.1:8081` (nginx proxies `/api/ai/` to the AI container), AI at `:8000`, backend at `:8080`.
- **Mounts:** grids and bundles are read-only; `data/features/v3/runs` is the only writable mount.
- **Stop:** `docker compose -p twinguard-b11 -f docker-compose.b11.yml stop`. Never use `down -v`, and never delete volumes.
- **Always on:** add `-f docker-compose.always-on.yml` (`restart: unless-stopped`, live on).
- **GPU:** add `-f docker-compose.gpu.yml`. This builds the AI image with CUDA PyTorch (`TWINGUARD_GPU=1`, pin `torch==2.14.1` from cu126, kept in step with `requirements-gpu.txt`) and requests `gpus: all`. It needs the NVIDIA Container Toolkit (Docker Desktop with WSL 2 GPU support). CPU stays the default.

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `TWINGUARD_V3_LIVE` | `1` | `0` disables live mode: no scheduler, and `/v3/live/latest` and `/refresh` return 503 |
| `TWINGUARD_V3_DEVICE` | `auto` | `auto`, `cuda` or `cpu` |
| `TWINGUARD_V3_WORKER` | `auto` | `persistent`, `per_run` or `auto` (persistent when CUDA resolves) |
| `TWINGUARD_V3_RUNS` | `data/features/v3/runs` | Run store (runs, live state, weather cache, resources) |
| `TWINGUARD_V3_A25_STATIC` | `data/features/live/a25_static_v1` | A25 bundle; without it the service falls back to the 600 m A06 pilot |
| `TWINGUARD_V3_WEATHER_MIN_INTERVAL_S` | `600` | Minimum seconds between Open-Meteo fetches for the weather panel and forecast runs |

## Open-Meteo budget

- **Free tier:** the published figure is 10,000 calls a day. The scheduler stops before **5,000 counted calls per UTC day** and returns 503 on refresh, while keeping the last good run.
- **Usage:** one live cycle counts about 297 location-calls (99 lattice points × 3 models). Eight scheduled cycles a day use about 2,400, plus any manual refreshes.
- **Where to check:** `GET /v3/live/status` → `sources.open_meteo.calls_today`.
- **CFM-DSS:** read at most once a day (2 requests).
- **Credentials:** none are used for either source.

## Health checks

| Check | Command |
|---|---|
| Service | `curl http://127.0.0.1:8000/health` |
| Engine, device and worker | `curl http://127.0.0.1:8000/v3/status` (`device.resolved`, `worker.state` = warm) |
| Live mode | `curl http://127.0.0.1:8000/v3/live/status` (`state`, `next_scheduled_at`, `last_error`, `sources`) |
| Latest live run | `curl http://127.0.0.1:8000/v3/live/latest` (404 before the first run) |
| Packaged through nginx | Same paths under `http://127.0.0.1:8081/api/ai/` |

## Common situations

| Symptom | Cause and fix |
|---|---|
| The UI shows fixtures or "API unavailable" | Nothing on `:8000`. Start option A or B. |
| A live cycle missed its slot | The machine was asleep. On wake the overdue cycle runs at once as `scheduled`, or as `catch_up` if more than 6 h late. |
| `last_error` with `fetch_forecast` | An Open-Meteo outage or the budget was reached. The last good run is still served, and the next cycle retries. |
| A second Refresh gives 429 | Manual refresh is limited to once per 600 s (`Retry-After` is set). |
| GPU not used | `GET /v3/status` → `device.cuda_available` false, or `worker.mode` per_run. Check the NVIDIA driver and the CUDA PyTorch install (`pip install -r requirements-gpu.txt`). |
| "â€”" instead of "—" in a terminal | The client decoded UTF-8 as cp1252. The server sends `application/json; charset=utf-8`. |

## Tests

```powershell
.venv\Scripts\python.exe -m pytest -q tests\ai_service tests\packaging
.venv\Scripts\python.exe tools\validate_api_contracts.py
.venv\Scripts\python.exe tools\audit_raw_logs.py
```

The end-to-end evidence scripts (`tests/e2e/b13_product_replay.py`, `tests/e2e/b53_live_cycle.py`) need the packaged stack to be running.
