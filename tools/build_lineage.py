#!/usr/bin/env python
"""Compatibility entry point for the Phase 4 lineage builder."""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT / "pipelines/phase4/build_lineage.py"), run_name="__main__")
