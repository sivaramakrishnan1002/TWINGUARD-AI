"""SUPERSEDED, NOT MOUNTED: the CR-018 /live draft, folded into C4 v3 (/v3, app.v3.router) by B47.

Kept only as the unmounted reference exercised by tests/phase12_openmeteo_grid. B47 removed its scheduler:
there is no background polling anywhere; Open-Meteo is fetched only for user-triggered /v3 requests.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import numpy as np
from fastapi import APIRouter, HTTPException, Path as PathParam, Query, Response

log = logging.getLogger("twinguard.live")
router = APIRouter(prefix="/live", tags=["live"])

LAYERS = ("peak_mean", "peak_p05", "peak_p95", "prob_peak_ge_0_30", "hourly_mean")
RUN_ID_PATTERN = r"^live-\d{8}T\d{6}Z-[a-f0-9]{8}$"


def _settings() -> dict:
    return {
        "static": Path(os.environ.get("TWINGUARD_LIVE_STATIC", "/app/data/features/live/a06_live_static_v1")),
        "runs": Path(os.environ.get("TWINGUARD_LIVE_RUNS", "/app/data/live/runs")),
        "min_interval_s": float(os.environ.get("TWINGUARD_LIVE_MIN_INTERVAL_S", "600")),
        "timeout_s": float(os.environ.get("TWINGUARD_LIVE_RUN_TIMEOUT_S", "1500")),
    }


class _Runner:
    """Runs the engine CLI in a child process; at most one at a time."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.running = False
        self.started_at: str | None = None
        self.last: dict = {"outcome": None, "run_id": None, "finished_at": None, "error": None}

    def start(self, force: bool = False) -> bool:
        with self.lock:
            if self.running:
                return False
            self.running = True
            self.started_at = _now()
        threading.Thread(target=self._run, args=(force,), daemon=True, name="live-run").start()
        return True

    def _run(self, force: bool) -> None:
        s = _settings()
        cmd = [sys.executable, "-m", "services.flood_engine.cli", "run", "--static", str(s["static"]), "--runs", str(s["runs"]),
               "--min-interval-s", str(s["min_interval_s"])] + (["--force"] if force else [])
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=s["timeout_s"])  # noqa: S603 - fixed argv
            line = (proc.stdout.strip().splitlines() or ["{}"])[-1]
            doc = json.loads(line) if line.startswith("{") else {"outcome": "failed", "error": "engine produced no result"}
            self.last = {"outcome": doc.get("outcome"), "run_id": doc.get("run_id"), "finished_at": _now(), "error": doc.get("error")}
        except subprocess.TimeoutExpired:
            self.last = {"outcome": "failed", "run_id": None, "finished_at": _now(), "error": "engine run timed out"}
        except Exception as error:  # noqa: BLE001
            self.last = {"outcome": "failed", "run_id": None, "finished_at": _now(), "error": type(error).__name__}
        finally:
            log.info("live run finished: %s", self.last)
            with self.lock:
                self.running = False


RUNNER = _Runner()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _runs_dir() -> Path:
    return _settings()["runs"]


def _run_ids() -> list[str]:
    root = _runs_dir()
    if not root.exists():
        return []
    return sorted((p.name for p in root.iterdir() if p.is_dir() and p.name.startswith("live-") and (p / "result.json").exists()), reverse=True)


def _load(run_id: str) -> dict:
    path = _runs_dir() / run_id / "result.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run not found.")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise HTTPException(status_code=503, detail="Run result is unreadable.") from None


def _summary(doc: dict) -> dict:
    return {
        "run_id": doc.get("run_id"), "computed_at": doc.get("computed_at"), "source_mode": doc.get("source_mode"),
        "status": doc.get("status"), "fetched_at": doc.get("forcing", {}).get("fetched_at"),
        "horizon": doc.get("horizon"), "outlook": doc.get("outlook"),
        "weather_models": doc.get("ensemble", {}).get("weather_models"), "members": doc.get("ensemble", {}).get("members"),
        "forcing_sha256": doc.get("forcing", {}).get("combined_forcing_sha256"),
    }


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.get("/status", operation_id="getLiveStatus")
def live_status(response: Response) -> dict:
    _no_store(response)
    s = _settings()
    ids = _run_ids()
    latest = _summary(_load(ids[0])) if ids else None
    return {
        "engine": "twinguard-live-engine/1.0.0", "static_available": (s["static"] / "static.npz").exists(),
        "schedule_minutes": None, "next_scheduled_at": None,
        "running": RUNNER.running, "running_since": RUNNER.started_at if RUNNER.running else None,
        "last_attempt": RUNNER.last, "run_count": len(ids), "latest": latest,
        "freshness_note": "A run is as current as its Open-Meteo fetch time; model issue times are not supplied by the provider.",
    }


@router.get("/runs", operation_id="listLiveRuns")
def list_runs(response: Response, limit: int = Query(default=12, ge=1, le=48)) -> dict:
    _no_store(response)
    return {"runs": [_summary(_load(i)) for i in _run_ids()[:limit]]}


@router.get("/runs/latest", operation_id="getLatestLiveRun")
def latest_run(response: Response) -> dict:
    _no_store(response)
    ids = _run_ids()
    if not ids:
        raise HTTPException(status_code=404, detail="No live run has completed yet.")
    return _load(ids[0])


@router.post("/runs", status_code=202, operation_id="triggerLiveRun")
def trigger_run(response: Response) -> dict:
    """Request a recomputation now. Rate-limited by the engine; identical forcing creates no new run."""
    _no_store(response)
    if not (_settings()["static"] / "static.npz").exists():
        raise HTTPException(status_code=503, detail="Live engine static grid is not installed.")
    started = RUNNER.start()
    return {"accepted": started, "state": "started" if started else "already_running", "running_since": RUNNER.started_at}


@router.get("/runs/{run_id}", operation_id="getLiveRun")
def get_run(response: Response, run_id: str = PathParam(pattern=RUN_ID_PATTERN)) -> dict:
    _no_store(response)
    return _load(run_id)


@router.get("/runs/{run_id}/grid/{layer}", operation_id="getLiveRunGrid")
def get_grid(response: Response, run_id: str = PathParam(pattern=RUN_ID_PATTERN),
             layer: Literal["peak_mean", "peak_p05", "peak_p95", "prob_peak_ge_0_30", "hourly_mean"] = PathParam(),
             hour: int | None = Query(default=None, ge=0, le=200)) -> dict:
    _no_store(response)
    doc = _load(run_id)
    try:
        with np.load(_runs_dir() / run_id / "grids.npz", allow_pickle=False) as bundle:
            array = bundle[layer]
    except (OSError, KeyError, ValueError):
        raise HTTPException(status_code=503, detail="Run grid is unreadable.") from None
    if layer == "hourly_mean":
        if hour is None or hour >= array.shape[0]:
            raise HTTPException(status_code=422, detail=f"hour must be 0..{array.shape[0] - 1} for hourly_mean")
        array = array[hour]
        valid_time = doc["timeline"][hour]["valid_time_utc"]
    else:
        valid_time = None
    values = [[None if not np.isfinite(v) else round(float(v), 3) for v in row] for row in array]
    return {"run_id": run_id, "layer": layer, "hour": hour, "valid_time_utc": valid_time,
            "unit": "fraction of members" if layer == "prob_peak_ge_0_30" else "m",
            "rows": len(values), "cols": len(values[0]) if values else 0, "grid": doc["grid"], "values": values,
            "nodata": "null = outside assessed CMA cells; not dry"}
