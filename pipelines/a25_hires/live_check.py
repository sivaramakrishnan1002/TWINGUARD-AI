#!/usr/bin/env python
"""A28 live-style sanity check: real Open-Meteo forecast + real CFM-DSS snapshot -> 72 h citywide 120 m runs.

One forecast fetch and one dashboard read are reused for: CPU run, CUDA run, and a no-rain/no-inflow control.
Writes data/features/simulation/a28_live_check_v1/ (runs/ + summary.json + the snapshot record kept with the runs).
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from services.flood_engine import forcing, products, scenario

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "data/features/live/a25_static_v1"
OUT = ROOT / "data/features/simulation/a28_live_check_v1"
CONTROL_MAX_FLOODED_KM2 = 1.0   # documented near-dry threshold for the control (cells >= 0.10 m, permanent water excluded)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    runs = OUT / "runs"
    run_time = datetime.now(timezone.utc)
    from services.trackb.connectors.tn_reservoir.client import CfmDashboardClient
    snap_body = CfmDashboardClient(timeout_seconds=20.0).fetch_daily_history().to_dict()
    (OUT / "cfm_snapshot_provenance.json").write_text(json.dumps({"received_at": snap_body.get("received_at"),
        "rows": len(snap_body.get("records", [])), "note": "raw response not retained (CR-016); see run provenance hash"}, indent=1))
    t = time.perf_counter()
    meta = scenario.StaticBundle(STATIC, "citywide_120m").grid
    fc = forcing.fetch_snapshot(meta["bbox_wgs84"])
    fetch_s = time.perf_counter() - t
    fetch = lambda bounds: fc  # noqa: E731 - reuse the single snapshot
    result = {"run_time_utc": run_time.strftime("%Y-%m-%dT%H:%M:%SZ"), "forecast_fetch_seconds": round(fetch_s, 1),
              "forecast_manifest": forcing.manifest(fc), "runs": {}}
    for label, kw in (("live_cpu", dict(device="cpu")), ("live_cuda", dict(device="cuda"))):
        t = time.perf_counter()
        doc = scenario.run_scenario(STATIC, runs, mode="forecast", duration_hours=72, fetch_forecast=fetch, reservoir_snapshot=snap_body,
                                    run_time=run_time, use_cache=False, **kw)
        result["runs"][label] = {"run_id": doc["run_id"], "wall_s": round(time.perf_counter() - t, 1), "timing": doc["timing"],
                                 "device": doc["provenance"]["device"], "steps": doc["diagnostics"]["central"]["steps"],
                                 "mass_balance": doc["diagnostics"]["central"]["mass_balance_relative_error"],
                                 "summary": doc["summary"], "forcing": doc["forcing"], "forecast_check": doc["forecast_check"],
                                 "reservoir_coupling": doc["reservoir_coupling"]}
        print(json.dumps({label: result["runs"][label]["wall_s"]}), flush=True)
    t = time.perf_counter()
    ctrl = scenario.run_scenario(STATIC, runs, mode="custom", duration_hours=72, device="cuda", use_cache=False,
                                 custom_rainfall={"start_time_utc": result["run_time_utc"], "interval_minutes": 60, "values_mm": [0.0] * 72})
    pk = np.array(products.depth_frame(runs, ctrl["run_id"])["values"], dtype=float)
    result["runs"]["control_no_rain_no_inflow"] = {"run_id": ctrl["run_id"], "wall_s": round(time.perf_counter() - t, 1), "summary": ctrl["summary"],
        "mass_balance": ctrl["diagnostics"]["central"]["mass_balance_relative_error"],
        "wet_cells_ge_0_01m": int(np.nansum(pk >= 0.01)), "threshold_flooded_km2": CONTROL_MAX_FLOODED_KM2,
        "near_dry": ctrl["summary"]["flooded_area_km2"] <= CONTROL_MAX_FLOODED_KM2}
    a = np.array(products.depth_frame(runs, result["runs"]["live_cpu"]["run_id"])["values"], dtype=float)
    b = np.array(products.depth_frame(runs, result["runs"]["live_cuda"]["run_id"])["values"], dtype=float)
    result["cpu_vs_cuda_peak"] = {"max_abs_m": float(np.nanmax(np.abs(a - b))), "mean_abs_m": float(np.nanmean(np.abs(a - b)))}
    (OUT / "summary.json").write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v.get("summary", {}).get("flooded_area_km2") for k, v in result["runs"].items()}))


if __name__ == "__main__":
    main()
