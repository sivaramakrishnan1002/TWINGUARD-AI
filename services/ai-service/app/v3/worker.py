"""Simulation worker: ``python -m app.v3.worker RUN_DIR`` (launched by the run manager in a child process).

Reads RUN_DIR/job.json, writes progress.json while running, then frames.npz, forcing.npz and result.json.
Prints one JSON line {"ok": bool, "error": str|None}. Never prints provider bodies or tracebacks.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np

from . import analysis, config, simulate, static, weather


def _write(path: Path, doc: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, allow_nan=False), encoding="utf-8")
    os.replace(tmp, path)


def execute(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    job = json.loads((run_dir / "job.json").read_text(encoding="utf-8"))
    req = job["request"]
    last = [0.0]

    def progress(pct: float) -> None:
        if pct - last[0] >= 1.0 or pct >= 100:
            last[0] = pct
            _write(run_dir / "progress.json", {"progress_pct": round(min(pct, 99.0), 1)})

    progress(0.0)
    if job.get("engine") == "a25":
        return _execute_a25(run_dir, job, progress)
    grid = static.grid(req["resolution"], req.get("focus_area"))
    mode = req["mode"]
    extra, tide, reservoir_detail = None, 0.0, {}
    if mode == "event":
        event = next(e for e in static.events() if e["event_key"] == req["event_key"])
        forcing = simulate.event_forcing(event, req["duration_hours"])
    elif mode == "custom":
        forcing = simulate.custom_forcing(req["custom_rainfall"])
    elif mode == "forecast":
        snapshot = weather.forecast_snapshot(bool(job.get("fetch_forecast")), static.grid("citywide").bounds_lonlat)
        forcing = simulate.forecast_forcing(grid, snapshot)
    elif mode == "what_if":
        mods = req["what_if"]
        base = simulate.Forcing.load(Path(job["base_run_dir"]) / "forcing.npz")
        forcing = simulate.whatif_forcing(base, mods.get("rainfall_scale_pct", 100.0))
        releases = mods.get("reservoir_release_m3s") or {}
        if releases:
            extra, reservoir_detail = simulate.reservoir_inflow(grid, releases)
            forcing.inputs.append({"name": "reservoir release", "source": "what-if release above assumed bank-full capacity",
                                   "source_mode": "SCENARIO_INPUT", "fetched_at": None, "sha256": None})
        tide = float(mods.get("tide_offset_m", 0.0))
        if tide:
            forcing.inputs.append({"name": "tide offset", "source": f"what-if outfall level +{tide:g} m",
                                   "source_mode": "SCENARIO_INPUT", "fetched_at": None, "sha256": None})
    else:
        raise ValueError(f"unsupported mode {mode}")

    out = simulate.run(grid, forcing, req["duration_hours"], req["frame_interval_minutes"], extra, tide, progress)
    n_frames = out["depth_mean"].shape[0]
    times = analysis.frame_times(out["frame_start"], n_frames, req["frame_interval_minutes"])
    np.savez_compressed(run_dir / "frames.npz", **{k: out[k] for k in ("depth_mean", "depth_p05", "depth_p95", "velocity_mps")})
    forcing.save(run_dir / "forcing.npz")
    try:
        product = static.product()
    except static.StaticUnavailable:
        product = None
    frames = {k: out[k] for k in ("depth_mean",)}
    summary = analysis.summary(grid, product, frames, times)
    inputs = list(forcing.inputs) + [
        {"name": "model grid", "source": f"A06/A23 static grid {grid.directory.name}", "source_mode": "STATIC_REFERENCE",
         "fetched_at": None, "sha256": grid.bundle_sha256},
    ]
    if product:
        inputs.append({"name": "roads, buildings and shelters", "source": "OpenStreetMap via A08 graph and OSM footprints",
                       "source_mode": "STATIC_REFERENCE", "fetched_at": None, "sha256": None})
    result = {
        "grid": grid.grid_spec(),
        "frames": [{"index": k, "valid_time_utc": t, "elapsed_minutes": (k + 1) * req["frame_interval_minutes"]}
                   for k, t in enumerate(times)],
        "summary": summary,
        "provenance": {"engine_version": config.ENGINE_VERSION, "run_id": job["run_id"], "forcing_sha256": forcing.sha256(),
                       "static_assets_version": product.version if product else None, "inputs": inputs},
        "diagnostics": {"members": out["members"], "runtime_seconds": out["runtime_seconds"], "reservoir": reservoir_detail},
    }
    _write(run_dir / "result.json", result)
    _write(run_dir / "progress.json", {"progress_pct": 100.0})
    return result


def _execute_a25(run_dir: Path, job: dict, progress) -> dict:
    """Lane A's A25 engine (services.flood_engine.scenario, read-only): run it, then keep frames in the v3 layout."""
    from services.flood_engine import scenario

    req = job["request"]
    engine_runs = config.runs_dir() / "_a25"
    what_if = None
    if req["mode"] == "what_if":
        what_if = {**req["what_if"], "base_run_id": job["base_engine_run_id"]}
    fetch = None
    if req["mode"] == "forecast":
        fetch_now = bool(job.get("fetch_forecast"))
        bounds = static.grid("citywide").bounds_lonlat
        fetch = lambda _bounds: weather.forecast_snapshot(fetch_now, bounds)  # noqa: E731 - cached, >= 600 s apart
    doc = scenario.run_scenario(
        config.a25_root(), engine_runs, mode=req["mode"], event_key=req.get("event_key"), custom_rainfall=req.get("custom_rainfall"),
        what_if=what_if, duration_hours=req["duration_hours"], resolution=req["resolution"], focus_area=req.get("focus_area"),
        frame_interval_minutes=req["frame_interval_minutes"], members=config.a25_members(),
        citywide_cell_m=config.a25_citywide_cell_m(), fetch_forecast=fetch, progress=progress)
    engine_dir = engine_runs / doc["run_id"]
    grid = static.grid(req["resolution"], req.get("focus_area"))
    with np.load(engine_dir / "frames.npz", allow_pickle=False) as z:
        cm = z["depth_cm"]
    depth = np.where(cm == 65535, np.nan, cm.astype(np.float32) / 100.0)
    depth = np.where(grid.active[None], depth, np.nan).astype(np.float32)
    frames = {"depth_mean": depth}
    with np.load(engine_dir / "peak.npz", allow_pickle=False) as z:
        for key in ("depth_p05", "depth_p95", "velocity_mps"):  # peak-only layers in A25
            if key in z.files:
                frames[key] = np.where(grid.active, z[key], np.nan).astype(np.float32)[None]
    np.savez_compressed(run_dir / "frames.npz", **frames)
    times = [f["valid_time_utc"] for f in doc["frames"]]
    try:
        product = static.product()
    except static.StaticUnavailable:
        product = None
    summary = analysis.summary(grid, product, {"depth_mean": depth}, times)
    provenance = doc.get("provenance") or {}
    inputs = list(provenance.get("inputs") or []) + [
        {"name": "model grid", "source": f"A25 static bundle {grid.directory.name}", "source_mode": "STATIC_REFERENCE",
         "fetched_at": None, "sha256": None}]
    result = {
        "grid": dict(doc["grid"]),
        "frames": doc["frames"],
        "summary": summary,
        "provenance": {"engine_version": f"{config.ENGINE_VERSION_A25} ({provenance.get('engine_version', 'A25')})",
                       "run_id": job["run_id"], "forcing_sha256": provenance.get("forcing_sha256"),
                       "static_assets_version": grid.version, "inputs": inputs},
        "diagnostics": {"engine_run_id": doc["run_id"], "engine_cached": bool(doc.get("cached")), "layers": sorted(frames)},
    }
    _write(run_dir / "result.json", result)
    _write(run_dir / "progress.json", {"progress_pct": 100.0})
    return result


def main(argv: list[str]) -> int:
    started = time.time()
    try:
        execute(Path(argv[0]))
    except Exception as error:  # noqa: BLE001 - report a single safe line
        print(json.dumps({"ok": False, "error": f"{type(error).__name__}: {str(error)[:200]}"}))
        return 1
    print(json.dumps({"ok": True, "error": None, "seconds": round(time.time() - started, 1)}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
