#!/usr/bin/env python
"""Export the A06 600 m grid and A07 exposure layers into one NumPy bundle for the live flood engine.

The bundle lets the AI service recompute floods with NumPy only (no GDAL/pandas at runtime).
Inputs are unchanged A06/A07 sources; nothing in data/raw is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pyogrio
import shapely
from rasterio.warp import transform as warp_transform

from pipelines.phase12 import simulate as a06
from pipelines.phase13 import impact as a07

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "data/features/live/a06_live_static_v1"
FACILITY_GROUPS = {"hospital": "hospital", "clinic": "hospital", "shelter": "shelter", "school": "candidate_shelter", "college": "candidate_shelter"}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def export(output: Path = OUTPUT) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    data = a06.load_static()
    active, drain = data["active"], data["drain"]
    model = active | drain
    transform = data["transform"]
    ny, nx = data["z"].shape

    population, pop_nodata, pop_meta = a07.aggregate_population(transform, active)
    pop_meta.pop("valid_count", None)

    _, edge_cell, edge_len, _, _, road_meta = a07.load_roads(transform, active)
    road_meta.pop("_graph", None)
    road_len = np.bincount(edge_cell[edge_cell >= 0], weights=edge_len[edge_cell >= 0], minlength=ny * nx).reshape(ny, nx)

    facilities = pyogrio.read_dataframe(a07.GPKG, layer="facilities", columns=["osmid", "category", "name"])
    category = facilities.category.fillna("").astype(str).str.lower().to_numpy()
    group = np.array([FACILITY_GROUPS.get(c, "") for c in category], dtype=object)
    xy = shapely.get_coordinates(facilities.geometry.array)
    fcell = a07._xy_to_cell(xy[:, 0], xy[:, 1], transform, active)
    keep = (fcell >= 0) & (group != "")
    flon, flat = warp_transform(data["crs"], "EPSG:4326", xy[keep, 0].tolist(), xy[keep, 1].tolist())
    names = facilities.name.fillna("").astype(str).to_numpy()[keep]

    rows, cols = np.indices((ny, nx))
    cx = transform.c + transform.a * (cols + 0.5)
    cy = transform.f + transform.e * (rows + 0.5)
    lon, lat = warp_transform(data["crs"], "EPSG:4326", cx.ravel().tolist(), cy.ravel().tolist())
    lon = np.asarray(lon).reshape(ny, nx)
    lat = np.asarray(lat).reshape(ny, nx)
    corners_x = [transform.c, transform.c + transform.a * nx, transform.c + transform.a * nx, transform.c]
    corners_y = [transform.f, transform.f, transform.f + transform.e * ny, transform.f + transform.e * ny]
    clon, clat = warp_transform(data["crs"], "EPSG:4326", corners_x, corners_y)

    bundle = output / "static.npz"
    np.savez_compressed(
        bundle,
        z=data["z"].astype(np.float64), active=active, drain=drain, mann=data["mann"].astype(np.float64),
        porosity=data["porosity"].astype(np.float64), landcover=data["landcover"].astype(np.int16),
        population=np.where(np.isfinite(population), population, np.nan).astype(np.float64),
        population_nodata_cells=pop_nodata.astype(np.int32), road_length_m=road_len.astype(np.float64),
        cell_lon=lon, cell_lat=lat,
        facility_cell=fcell[keep].astype(np.int64), facility_group=np.array(group[keep], dtype="U20"),
        facility_category=np.array(category[keep], dtype="U20"), facility_name=np.array(names, dtype="U120"),
        facility_lon=np.asarray(flon), facility_lat=np.asarray(flat),
    )
    meta = {
        "schema": "twinguard.live_static.v1",
        "status": "DERIVED_ASSUMPTION_BASED_PILOT",
        "grid": {"rows": int(ny), "cols": int(nx), "cell_size_m": a06.CELL_M, "crs": str(data["crs"]),
                 "transform": [transform.a, transform.b, transform.c, transform.d, transform.e, transform.f],
                 "corners_lonlat": [[float(a), float(b)] for a, b in zip(clon, clat)],
                 "active_cells": int(active.sum()), "drain_cells": int(drain.sum()),
                 "bounds_lonlat": [float(lon[model].min()), float(lat[model].min()), float(lon[model].max()), float(lat[model].max())]},
        "population": pop_meta,
        "roads": road_meta,
        "facilities": {"mapped": int(keep.sum()), "by_group": {g: int((group[keep] == g).sum()) for g in sorted(set(group[keep]))},
                       "groups": FACILITY_GROUPS},
        "source_sha256": data["hashes"],
        "bundle_sha256": _sha(bundle),
    }
    (output / "static_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    meta = export(args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir)
    print(json.dumps({"bundle_sha256": meta["bundle_sha256"], "grid": meta["grid"]["rows"], "facilities": meta["facilities"]}, indent=2))


if __name__ == "__main__":
    main()
