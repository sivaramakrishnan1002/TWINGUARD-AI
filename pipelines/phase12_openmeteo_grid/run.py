#!/usr/bin/env python
"""A23: one versioned research run of A06 driven by a gridded Open-Meteo snapshot (CR-015).

Writes the exact snapshot to data/features/weather/openmeteo_a06_domain_v1/ and the flood outputs to
data/features/simulation/openmeteo_grid_72h_v1/ (GeoTIFF + JSON). Never overwrites A05/A06 outputs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

from services.flood_engine import engine, forcing

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "data/features/live/a06_live_static_v1"
SNAPSHOT_DIR = ROOT / "data/features/weather/openmeteo_a06_domain_v1"
OUTPUT = ROOT / "data/features/simulation/openmeteo_grid_72h_v1"


def write_tif(path: Path, array: np.ndarray, meta: dict) -> None:
    t = meta["grid"]["transform"]
    out = np.where(np.isfinite(array), array, -9999).astype("float32")
    profile = {"driver": "GTiff", "height": out.shape[0], "width": out.shape[1], "count": 1, "dtype": "float32",
               "crs": meta["grid"]["crs"], "transform": Affine(*t), "nodata": -9999, "compress": "deflate"}
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(out, 1)
        ds.update_tags(STATUS="DERIVED_RESEARCH_OUTPUT", SOURCE="Open-Meteo gridded model rainfall + A06 ensemble",
                       NODATA="outside assessed CMA; not dry")


def run(output: Path = OUTPUT, snapshot_dir: Path = SNAPSHOT_DIR) -> dict:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite output: {output}")
    static = engine.StaticGrid(STATIC)
    snapshot = forcing.fetch_snapshot(static.bounds)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for model, body in snapshot.raw.items():
        (snapshot_dir / f"{model}.json").write_bytes(body)
    (snapshot_dir / "manifest.json").write_text(json.dumps(forcing.manifest(snapshot), indent=2), encoding="utf-8")
    result, grids = engine.compute_run(static, snapshot)
    output.mkdir(parents=True, exist_ok=True)
    for name in ("peak_mean", "peak_p05", "peak_p95", "prob_peak_ge_0_30"):
        write_tif(output / f"depth_{name}_DERIVED.tif", grids[name], static.meta)
    np.savez_compressed(output / "hourly_mean_depth_DERIVED.npz", depth_m=grids["hourly_mean"])
    result["run_id"] = f"a23-research-{snapshot.fetched_at.replace(':', '').replace('-', '')}"
    (output / "run_summary.json").write_text(json.dumps(result, indent=1, allow_nan=False), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = run(args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir)
    print(json.dumps({k: result[k] for k in ("run_id", "outlook", "horizon", "ensemble")}, indent=2))


if __name__ == "__main__":
    main()
