"""CLI for A25 scenario runs (Lane B can call this in a child process).

Examples:
  python -m services.flood_engine.scenario_cli --mode event --event-key 2015-12-01 --hours 24
  python -m services.flood_engine.scenario_cli --mode event --event-key 2015-12-01 --resolution focus --focus-area VELACHERY
  python -m services.flood_engine.scenario_cli --mode what_if --base-run-id evt-... --rain-pct 130 \
      --release CHEMBARAMBAKKAM=850 --tide 0.5
  python -m services.flood_engine.scenario_cli --mode custom --custom '{"start_time_utc":"2026-11-07T00:00:00Z","interval_minutes":60,"values_mm":[5,20,40,10]}'
Prints one JSON line: {"run_id", "state", "cached", "runtime_seconds", "summary"} (or {"state": "failed", "error"}).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .scenario import ScenarioError, run_scenario

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATIC = ROOT / "data/features/live/a25_static_v1"
DEFAULT_RUNS = ROOT / "data/features/simulation/a25_runs_v1"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="flood_engine.scenario_cli")
    ap.add_argument("--static", type=Path, default=DEFAULT_STATIC)
    ap.add_argument("--runs", type=Path, default=DEFAULT_RUNS)
    ap.add_argument("--mode", required=True, choices=["event", "custom", "forecast", "what_if"])
    ap.add_argument("--event-key")
    ap.add_argument("--custom", help="CustomRainfall JSON")
    ap.add_argument("--base-run-id")
    ap.add_argument("--rain-pct", type=float, default=100.0)
    ap.add_argument("--release", action="append", default=[], help="RESERVOIR=m3/s (repeatable)")
    ap.add_argument("--tide", type=float, default=0.0)
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--resolution", choices=["citywide", "focus"], default="citywide")
    ap.add_argument("--focus-area", choices=["VELACHERY", "ADYAR", "T_NAGAR", "PORUR"])
    ap.add_argument("--frame-minutes", type=int, choices=[15, 30], default=30)
    ap.add_argument("--members", type=int, choices=[1, 3], default=1)
    ap.add_argument("--cell-m", type=int, choices=[90, 120], default=120)
    ap.add_argument("--threads", type=int)
    a = ap.parse_args(argv)
    what_if = None
    if a.mode == "what_if":
        rel = {}
        for item in a.release:
            k, v = item.split("=", 1)
            rel[k.strip().upper()] = float(v)
        what_if = {"base_run_id": a.base_run_id, "rainfall_scale_pct": a.rain_pct, "reservoir_release_m3s": rel, "tide_offset_m": a.tide}
    try:
        doc = run_scenario(a.static, a.runs, mode=a.mode, event_key=a.event_key, custom_rainfall=json.loads(a.custom) if a.custom else None,
                           what_if=what_if, duration_hours=a.hours, resolution=a.resolution, focus_area=a.focus_area,
                           frame_interval_minutes=a.frame_minutes, members=a.members, citywide_cell_m=a.cell_m, threads=a.threads)
    except (ScenarioError, RuntimeError, ValueError, OSError) as error:
        print(json.dumps({"state": "failed", "error": f"{type(error).__name__}: {str(error)[:300]}"}))
        return 1
    print(json.dumps({"run_id": doc["run_id"], "state": doc["state"], "cached": doc.get("cached", False),
                      "runtime_seconds": doc.get("runtime_seconds"), "summary": doc["summary"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
