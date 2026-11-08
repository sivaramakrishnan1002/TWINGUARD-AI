#!/usr/bin/env python
"""A26 CPU (NumPy) vs CUDA (torch) benchmark on the A25 grids.

Writes data/features/simulation/a26_benchmark_v1/{cpu,cuda}/<run_id>/ and benchmark.json; the report is
docs/FLOOD_ENGINE_GPU_BENCHMARK.md.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import time
from pathlib import Path

import numpy as np

from services.flood_engine import hires, hires_torch
from services.flood_engine.scenario import ENGINE_VERSION, run_scenario

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "data/features/live/a25_static_v1"
OUT = ROOT / "data/features/simulation/a26_benchmark_v1"
CASES = [
    ("citywide 120 m, 24 h", dict(mode="event", event_key="2015-12-01", duration_hours=24)),
    ("citywide 120 m, 48 h", dict(mode="event", event_key="2015-12-01", duration_hours=48)),
    ("citywide 120 m, 24 h, 3 members", dict(mode="event", event_key="2015-12-01", duration_hours=24, members=3)),
    ("citywide 90 m, 24 h", dict(mode="event", event_key="2015-12-01", duration_hours=24, citywide_cell_m=90)),
    ("focus 30 m VELACHERY, 24 h (nested)", dict(mode="event", event_key="2015-12-01", duration_hours=24, resolution="focus", focus_area="VELACHERY")),
]


def _env() -> dict:
    import torch
    info = {"platform": platform.platform(), "cpu": platform.processor(), "cpu_count": os.cpu_count(), "numpy": np.__version__,
            "torch": torch.__version__, "torch_cuda": torch.version.cuda, "engine": ENGINE_VERSION}
    ok, name = hires_torch.available()
    info["gpu"] = name if ok else None
    if ok:
        props = torch.cuda.get_device_properties(0)
        info["gpu_total_mb"] = round(props.total_memory / 2**20)
    try:
        info["nvidia_driver"] = subprocess.run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                                               capture_output=True, text=True, timeout=20).stdout.strip() or None
    except Exception:  # noqa: BLE001
        info["nvidia_driver"] = None
    return info


def _compare(cpu_dir: Path, gpu_dir: Path) -> dict:
    with np.load(cpu_dir / "frames.npz") as a, np.load(gpu_dir / "frames.npz") as b:
        fa, fb = a["depth_cm"], b["depth_cm"]
    with np.load(cpu_dir / "peak.npz") as a, np.load(gpu_dir / "peak.npz") as b:
        pa, pb = a["depth_mean"], b["depth_mean"]
    da = np.where(fa == hires.NODATA_CM, np.nan, fa / 100.0)
    db = np.where(fb == hires.NODATA_CM, np.nan, fb / 100.0)
    diff = np.abs(da - db)
    pdiff = np.abs(pa - pb)
    wet = np.isfinite(pa) & (pa >= 0.10)
    return {"frames_max_abs_m": float(np.nanmax(diff)), "frames_mean_abs_m": float(np.nanmean(diff)),
            "peak_max_abs_m": float(np.nanmax(pdiff)), "peak_mean_abs_m": float(np.nanmean(pdiff)),
            "peak_p99_abs_m": float(np.nanpercentile(pdiff, 99)),
            "flooded_cells_cpu": int(wet.sum()), "flooded_cells_agreeing": int((wet == (np.isfinite(pb) & (pb >= 0.10))).sum())}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"environment": _env(), "cases": []}
    for label, kw in CASES:
        row = {"label": label}
        for device in ("cpu", "cuda"):
            t = time.perf_counter()
            doc = run_scenario(STATIC, OUT / device, **kw, device=device, use_cache=False)
            wall = time.perf_counter() - t
            diag = list(doc["diagnostics"].values())
            row[device] = {"run_id": doc["run_id"], "wall_seconds": round(wall, 1), "steps": sum(d["steps"] for d in diag),
                           "max_mass_balance_relative_error": max(d["mass_balance_relative_error"] for d in diag),
                           "device": doc["provenance"]["device"]}
            row["grid"] = {k: doc["grid"][k] for k in ("cell_size_m", "rows", "cols")}
            row["members"] = len(doc["members"])
            print(json.dumps({"label": label, "device": device, "wall_seconds": row[device]["wall_seconds"]}), flush=True)
        row["speedup"] = round(row["cpu"]["wall_seconds"] / row["cuda"]["wall_seconds"], 2)
        row["agreement"] = _compare(OUT / "cpu" / row["cpu"]["run_id"], OUT / "cuda" / row["cuda"]["run_id"])
        report["cases"].append(row)
        (OUT / "benchmark.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({c["label"]: c["speedup"] for c in report["cases"]}))


if __name__ == "__main__":
    main()
