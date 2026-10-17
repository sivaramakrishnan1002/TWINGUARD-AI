#!/usr/bin/env python
"""Inventory raster/vector layers and test raster registration and nodata."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pyogrio
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import transform as window_transform

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
TARGET = DATA / "processed/alignment/layer_registry_complete.json"
GRID = DATA / "processed/grid/grid_definition.json"
RASTER_EXT = {".tif", ".tiff", ".vrt"}
VECTOR_EXT = {".gpkg", ".geojson", ".kml", ".pbf"}


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _grid_match(transform, crs, width, height, grid) -> tuple[bool, dict]:
    gt = grid["transform"]
    cell = float(grid["resolution_m"])
    col_offset = (float(transform.c) - float(gt[2])) / cell
    row_offset = (float(gt[5]) - float(transform.f)) / cell
    integral_offsets = math.isclose(col_offset, round(col_offset), abs_tol=1e-8) and math.isclose(row_offset, round(row_offset), abs_tol=1e-8)
    exact = (integral_offsets and crs and str(crs).upper() == grid["crs"].upper()
             and math.isclose(transform.a, gt[0], abs_tol=1e-9)
             and math.isclose(transform.e, gt[4], abs_tol=1e-9)
             and math.isclose(transform.b, 0.0, abs_tol=1e-9)
             and math.isclose(transform.d, 0.0, abs_tol=1e-9)
             and width == grid["width"] and height == grid["height"])
    return bool(exact), {"column_offset_cells": col_offset, "row_offset_cells": row_offset,
                         "origin_offsets_whole_cells": bool(integral_offsets)}


def _raster(path: Path, grid: dict, assess_grid: bool) -> dict:
    with rasterio.open(path) as ds:
        if assess_grid:
            aligned, offset_test = _grid_match(ds.transform, ds.crs, ds.width, ds.height, grid)
        else:
            aligned, offset_test = None, {"not_applicable": "native raw raster; source grid is not expected to match the analysis grid"}
        nodata_count = 0
        nonfinite_count = 0
        valid_count = 0
        for _, window in ds.block_windows(1):
            block = ds.read(1, window=window, masked=False)
            mask = ds.read_masks(1, window=window) == 0
            nodata_count += int(mask.sum())
            if np.issubdtype(block.dtype, np.floating):
                nonfinite_count += int((~np.isfinite(block) & ~mask).sum())
            valid_count += int((~mask).sum())
        return {
            "path": _relative(path), "kind": "raster", "crs": str(ds.crs) if ds.crs else None,
            "cell_size": [float(ds.transform.a), float(abs(ds.transform.e))],
            "origin": [float(ds.transform.c), float(ds.transform.f)],
            "dtype": list(ds.dtypes), "nodata": ds.nodata,
            "extent": [float(ds.bounds.left), float(ds.bounds.bottom), float(ds.bounds.right), float(ds.bounds.top)],
            "width": ds.width, "height": ds.height, "band_count": ds.count,
            "grid_aligned": aligned, "valid_cells_band1": valid_count,
            "nodata_cells_band1": nodata_count, "nonfinite_valid_band1": nonfinite_count,
            "registration_test": offset_test,
            "test_used": "Compare CRS, dimensions, pixel size and origin offsets to master grid; scan band 1 masks for nodata/nonfinite values",
        }


def _vector(path: str | Path, layer: str | None = None, display_path: Path | None = None) -> dict:
    info = pyogrio.read_info(path, layer=layer)
    crs = info.get("crs")
    bounds = info.get("total_bounds")
    return {
        "path": _relative(display_path or Path(path)), "layer": layer or info.get("layer_name"), "kind": "vector",
        "crs": crs, "cell_size": None, "origin": None,
        "dtype": dict(zip(info.get("fields", []), info.get("dtypes", []))),
        "nodata": None,
        "extent": [float(v) for v in bounds] if bounds is not None else None,
        "feature_count": int(info.get("features", 0)),
        "grid_aligned": False,
        "registration_test": {"not_applicable": "vector geometry; no raster cell origin"},
        "test_used": "Read layer metadata; vectors remain in native geometry and are not expected to match raster cells",
    }


def _population_sums() -> dict:
    import geopandas as gpd
    boundary_file = DATA / "raw/boundary/chennai_cma_boundary.geojson"
    boundary = gpd.read_file(boundary_file).geometry.union_all()
    native_file = DATA / "raw/population/ind_pop_2021_CN_100m_R2025A_v1.tif"
    derived_file = DATA / "features/population/worldpop_2021_sum_resampled_30m.tif"
    mask_file = DATA / "processed/grid/cma_mask.tif"
    sums = {}
    with rasterio.open(native_file) as ds:
        geom = gpd.GeoSeries([boundary], crs="EPSG:4326").to_crs(ds.crs).iloc[0]
        total, cells = 0.0, 0
        for _, win in ds.block_windows(1):
            arr = ds.read(1, window=win, masked=False)
            inside = geometry_mask([geom], out_shape=arr.shape,
                                   transform=window_transform(win, ds.transform),
                                   invert=True, all_touched=False)
            nodata = ds.nodata
            valid = inside & np.isfinite(arr)
            if nodata is not None:
                valid &= arr != nodata
            total += float(arr[valid].astype("float64").sum())
            cells += int(valid.sum())
        sums["native_100m"] = {"sum": total, "valid_cells": cells, "crs": str(ds.crs)}
    with rasterio.open(derived_file) as pop, rasterio.open(mask_file) as mask:
        if (pop.width, pop.height, pop.transform, pop.crs) != (mask.width, mask.height, mask.transform, mask.crs):
            raise ValueError("Derived population and CMA mask grids are not aligned")
        total, cells = 0.0, 0
        for _, win in pop.block_windows(1):
            arr = pop.read(1, window=win, masked=False)
            inside = mask.read(1, window=win) == 1
            valid = inside & np.isfinite(arr)
            if pop.nodata is not None:
                valid &= arr != pop.nodata
            total += float(arr[valid].astype("float64").sum())
            cells += int(valid.sum())
        sums["derived_30m"] = {"sum": total, "valid_cells": cells, "crs": str(pop.crs)}
    rel = abs(sums["native_100m"]["sum"] - sums["derived_30m"]["sum"]) / abs(sums["native_100m"]["sum"])
    sums["relative_difference"] = rel
    sums["tolerance"] = 0.001
    sums["within_tolerance"] = rel <= sums["tolerance"]
    return sums


def main() -> int:
    if TARGET.exists():
        raise FileExistsError(f"Refusing to overwrite existing registry: {TARGET}")
    grid = json.loads(GRID.read_text(encoding="utf-8"))
    records, failures = [], []
    roots = [DATA / "raw", DATA / "features", DATA / "processed"]
    for root in roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            suffix = path.suffix.casefold()
            try:
                if suffix in RASTER_EXT:
                    assess = not path.is_relative_to(DATA / "raw")
                    records.append(_raster(path, grid, assess))
                elif suffix in VECTOR_EXT:
                    for layer_info in pyogrio.list_layers(path):
                        layer = str(layer_info[0])
                        records.append(_vector(path, layer))
                elif suffix == ".zip":
                    import zipfile
                    with zipfile.ZipFile(path) as archive:
                        members = [n for n in archive.namelist() if n.casefold().endswith(".shp")]
                    for member in members:
                        vsi = f"/vsizip/{path.as_posix()}/{member}"
                        records.append(_vector(vsi, display_path=path))
            except Exception as exc:
                failures.append({"path": _relative(path), "error": f"{type(exc).__name__}: {exc}"})
    try:
        population_check = _population_sums()
    except Exception as exc:
        failures.append({"path": "population-sum-check", "error": f"{type(exc).__name__}: {exc}"})
        population_check = {"error": f"{type(exc).__name__}: {exc}"}
    payload = {
        "status": "DERIVED", "master_grid": grid,
        "raster_count": sum(r["kind"] == "raster" for r in records),
        "vector_layer_count": sum(r["kind"] == "vector" for r in records),
        "grid_aligned_rasters": sum(r["kind"] == "raster" and r["grid_aligned"] is True for r in records),
        "not_aligned_analysis_rasters": [r["path"] for r in records if r["kind"] == "raster" and r["grid_aligned"] is False],
        "metadata_errors": failures,
        "checks": {
            "origin_offset_rule": "cell offsets must be integers within 1e-8 cells",
            "nodata_rule": "read GDAL mask and independently flag non-finite unmasked float values",
            "population_sum_check": population_check,
            "area_validation": "Rasterized label area and vector dissolved area use different support; report the difference, do not force equality",
        },
        "layers": records,
    }
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"REGISTRY={_relative(TARGET)}; RASTERS={payload['raster_count']}; "
          f"VECTORS={payload['vector_layer_count']}; ALIGNED={payload['grid_aligned_rasters']}; "
          f"ERRORS={len(failures)}; MISALIGNED={len(payload['not_aligned_analysis_rasters'])}")
    return 1 if failures or payload["not_aligned_analysis_rasters"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
