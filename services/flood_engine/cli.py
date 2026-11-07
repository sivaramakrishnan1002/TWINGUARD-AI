"""Command-line entry point: ``python -m services.flood_engine.cli run --static DIR --runs DIR [--force]``.

The AI service launches this in a child process so a 3-4 minute ensemble never blocks API requests.
Prints one JSON line: {"outcome": ..., "run_id": ...}.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import LiveEngine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="flood_engine")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--static", type=Path, required=True)
    run.add_argument("--runs", type=Path, required=True)
    run.add_argument("--force", action="store_true")
    run.add_argument("--min-interval-s", type=float, default=600)
    args = parser.parse_args(argv)
    engine = LiveEngine(args.static, args.runs, min_interval_s=args.min_interval_s)
    try:
        outcome = engine.run_once(force=args.force)
    except Exception as error:  # report a single safe line; never a traceback with provider bodies
        print(json.dumps({"outcome": "failed", "error": f"{type(error).__name__}: {str(error)[:200]}"}))
        return 1
    run_doc = outcome.get("run") or {}
    print(json.dumps({"outcome": outcome["outcome"], "run_id": run_doc.get("run_id")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
