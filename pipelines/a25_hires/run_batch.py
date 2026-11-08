#!/usr/bin/env python
"""A25 acceptance batch: saved events citywide, 30 m focus areas, what-if, custom rainfall and a 90 m check.

Writes runs to data/features/simulation/a25_runs_v1/ and a summary to data/features/simulation/a25_runs_v1/batch_summary.json.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from services.flood_engine.scenario import run_scenario

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "data/features/live/a25_static_v1"
RUNS = ROOT / "data/features/simulation/a25_runs_v1"
EVENTS = ("2015-12-01", "2021-11-11", "2023-12-03")
FOCUS = ("VELACHERY", "ADYAR", "T_NAGAR", "PORUR")


def _row(label, doc, seconds):
    return {"label": label, "run_id": doc["run_id"], "cached": doc.get("cached", False), "grid_cell_m": doc["grid"]["cell_size_m"],
            "rows": doc["grid"]["rows"], "cols": doc["grid"]["cols"], "frames": len(doc["frames"]),
            "frame_interval_minutes": doc["frame_interval_minutes"], "members": doc.get("members"),
            "engine_runtime_seconds": doc.get("runtime_seconds"), "wall_seconds": round(seconds, 1),
            "max_mass_balance_relative_error": max(m["mass_balance_relative_error"] for m in doc["diagnostics"].values()),
            "min_dt_s": min(m["min_dt_s"] for m in doc["diagnostics"].values()), "summary": doc["summary"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=48)
    ap.add_argument("--skip-90m", action="store_true")
    a = ap.parse_args()
    rows = []

    def go(label, **kw):
        t = time.perf_counter()
        doc = run_scenario(STATIC, RUNS, **kw)
        rows.append(_row(label, doc, time.perf_counter() - t))
        print(json.dumps({k: rows[-1][k] for k in ("label", "run_id", "wall_seconds", "max_mass_balance_relative_error")}), flush=True)
        (RUNS / "batch_summary.json").write_text(json.dumps({"hours": a.hours, "runs": rows}, indent=1), encoding="utf-8")
        return doc

    base = None
    for ev in EVENTS:
        doc = go(f"event {ev} citywide 120 m", mode="event", event_key=ev, duration_hours=a.hours)
        base = base or doc
    go("event 2015-12-01 citywide 120 m, 3 members", mode="event", event_key="2015-12-01", duration_hours=24, members=3)
    for area in FOCUS:
        go(f"event 2015-12-01 focus 30 m {area}", mode="event", event_key="2015-12-01", duration_hours=a.hours, resolution="focus", focus_area=area)
    go("what-if: 2015 base, rain 130%, Chembarambakkam 850 m3/s, tide +0.5 m", mode="what_if", duration_hours=a.hours,
       what_if={"base_run_id": base["run_id"], "rainfall_scale_pct": 130, "reservoir_release_m3s": {"CHEMBARAMBAKKAM": 850}, "tide_offset_m": 0.5})
    go("custom: 6 h burst 5/20/45/60/30/10 mm, 15-min frames", mode="custom", duration_hours=24, frame_interval_minutes=15,
       custom_rainfall={"start_time_utc": "2026-11-07T00:00:00Z", "interval_minutes": 60, "values_mm": [5, 20, 45, 60, 30, 10]})
    if not a.skip_90m:
        go("event 2015-12-01 citywide 90 m", mode="event", event_key="2015-12-01", duration_hours=24, citywide_cell_m=90)


if __name__ == "__main__":
    main()
