#!/usr/bin/env python
"""Create a new conditioned terrain set; never changes raw or existing features."""
from __future__ import annotations

import argparse
import heapq
import json
import math
import os
import shutil
import uuid
from pathlib import Path

import geopandas as gpd
import numpy as np
import osmium
import rasterio
from affine import Affine
from pyproj import Transformer
from rasterio.features import rasterize
from rasterio.transform import xy
from shapely.geometry import LineString, Polygon, box, mapping
from shapely.ops import transform as transform_geom

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data/processed"
TARGET = PROCESSED / "terrain_cleaned"
DEM = ROOT / "data/features/terrain/elevation_m.tif"
GRID_MASK = PROCESSED / "grid/cma_mask.tif"
WC = ROOT / "data/features/landcover/worldcover_2021_class.tif"
OSM = ROOT / "data/raw/roads/southern-zone-latest.osm.pbf"
BOUNDARY = ROOT / "data/raw/boundary/chennai_cma_boundary.geojson"
OLD = ROOT / "data/features/terrain"
REPORT = ROOT / "docs/TERRAIN_CONDITIONING.md"
NODATA = -9999.0
CELL = 30.0
BURN_DEPTH_M = 2.0
OFFSETS = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
TARGET_NAMES = {
    "Adyar River": {"adyar river"},
    "Cooum": {"cooum"},
    "Kosasthalaiyar River": {"kosasthalaiyar river"},
    "Buckingham Canal": {"buckingham canal"},
}


def priority_flood(z: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Fill closed depressions using the standard Priority-Flood surface algorithm."""
    h, w = z.shape
    filled = z.astype(np.float32, copy=True)
    seen = np.zeros((h, w), dtype=np.uint8)
    heap: list[tuple[float, int]] = []
    # Seed valid raster perimeter and every valid cell adjacent to a masked/nodata cell.
    for r in range(h):
        for c in (0, w - 1):
            if valid[r, c] and not seen[r, c]:
                seen[r, c] = 1
                heapq.heappush(heap, (float(filled[r, c]), r * w + c))
    for c in range(w):
        for r in (0, h - 1):
            if valid[r, c] and not seen[r, c]:
                seen[r, c] = 1
                heapq.heappush(heap, (float(filled[r, c]), r * w + c))
    for r in range(h):
        for c in range(w):
            if not valid[r, c] or seen[r, c]:
                continue
            for dy, dx in OFFSETS:
                rr, cc = r + dy, c + dx
                if 0 <= rr < h and 0 <= cc < w and not valid[rr, cc]:
                    seen[r, c] = 1
                    heapq.heappush(heap, (float(filled[r, c]), r * w + c))
                    break
    while heap:
        level, index = heapq.heappop(heap)
        r, c = divmod(index, w)
        for dy, dx in OFFSETS:
            rr, cc = r + dy, c + dx
            if rr < 0 or rr >= h or cc < 0 or cc >= w or not valid[rr, cc] or seen[rr, cc]:
                continue
            seen[rr, cc] = 1
            if filled[rr, cc] < level:
                filled[rr, cc] = level
            heapq.heappush(heap, (float(filled[rr, cc]), rr * w + cc))
    return filled


class WaterAndRivers(osmium.SimpleHandler):
    """Extract only water-tagged ways from the local read-only PBF."""
    def __init__(self, to_grid, grid_bounds, geographic_bounds):
        super().__init__()
        self.to_grid, self.grid_bounds, self.geographic_bounds = to_grid, grid_bounds, geographic_bounds
        self.water_polygons, self.water_lines = [], []
        self.rivers = {k: [] for k in TARGET_NAMES}
        self.river_way_ids = {k: [] for k in TARGET_NAMES}

    def way(self, way):
        tags = dict(way.tags)
        names = {str(tags.get(k, "")).strip().casefold() for k in ("name", "name:en", "alt_name")}
        target = next((k for k, accepted in TARGET_NAMES.items() if names & accepted), None)
        polygon_tag = tags.get("natural") == "water" or bool(tags.get("water"))
        relevant_line = bool(tags.get("waterway")) or tags.get("natural") in {"coastline", "water"} or bool(tags.get("water")) or target
        if not polygon_tag and not relevant_line:
            return
        coords = [(n.location.lon, n.location.lat) for n in way.nodes if n.location.valid()]
        if len(coords) < 2:
            return
        way_box = box(min(x for x, _ in coords), min(y for _, y in coords),
                      max(x for x, _ in coords), max(y for _, y in coords))
        if not box(*self.geographic_bounds).intersects(way_box):
            return
        is_closed = len(coords) >= 4 and coords[0] == coords[-1]
        try:
            if is_closed and polygon_tag:
                geom = transform_geom(self.to_grid, Polygon(coords)).intersection(self.grid_bounds)
                if not geom.is_empty:
                    self.water_polygons.append(geom)
            else:
                geom = transform_geom(self.to_grid, LineString(coords)).intersection(self.grid_bounds)
                if geom.is_empty:
                    return
                if target:
                    self.rivers[target].append(geom)
                    self.river_way_ids[target].append(int(way.id))
                if relevant_line and not target:
                    self.water_lines.append(geom)
        except Exception:
            return


def d8(z: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    h, w = z.shape
    best = np.zeros((h, w), dtype=np.float32)
    direction = np.zeros((h, w), dtype=np.uint8)
    downstream = np.full((h, w), -1, dtype=np.int64)
    for code, (dy, dx) in enumerate(OFFSETS, 1):
        ys = slice(max(0, -dy), min(h, h - dy)); xs = slice(max(0, -dx), min(w, w - dx))
        yn = slice(max(0, dy), min(h, h + dy)); xn = slice(max(0, dx), min(w, w + dx))
        dz = (z[ys, xs] - z[yn, xn]) / (CELL * (math.sqrt(2) if dy and dx else 1))
        good = valid[ys, xs] & valid[yn, xn] & (dz > best[ys, xs])
        best[ys, xs][good] = dz[good]
        direction[ys, xs][good] = code
        sy, sx = np.mgrid[ys, xs]
        downstream[ys, xs][good] = (sy[good] + dy) * w + sx[good] + dx
    accum = np.zeros(h * w, dtype=np.float32)
    flat_valid = valid.ravel()
    accum[flat_valid] = 1
    order = np.flatnonzero(flat_valid)
    order = order[np.argsort(-z.ravel()[order], kind="stable")]
    down = downstream.ravel()
    for i in order:
        j = down[i]
        if j >= 0:
            accum[j] += accum[i]
    return direction, accum.reshape(h, w), downstream


def derivatives(z: np.ndarray, valid: np.ndarray, accum: np.ndarray):
    # Central differences on valid 3x3 neighborhoods; nodata-adjacent slope is nodata.
    gy, gx = np.gradient(z.astype(np.float64), CELL, CELL)
    slope = np.degrees(np.arctan(np.hypot(gx, gy))).astype(np.float32)
    slope[~valid] = NODATA
    slope[valid & ~np.isfinite(slope)] = NODATA
    slope_rad = np.maximum(np.radians(np.maximum(slope, 0)), np.radians(0.1))
    twi = np.log(np.maximum(accum, 1) * CELL / np.maximum(np.tan(slope_rad), 1e-6)).astype(np.float64).astype(np.float32)
    twi[~valid] = NODATA
    return slope, twi


def write_tif(path: Path, arr, transform, crs, dtype, nodata):
    h, w = arr.shape
    with rasterio.open(path, "w", driver="GTiff", width=w, height=h, count=1, dtype=dtype,
                       crs=crs, transform=transform, nodata=nodata, tiled=True,
                       blockxsize=256, blockysize=256, compress="DEFLATE",
                       predictor=2 if dtype.startswith("float") else 1, BIGTIFF="IF_SAFER") as dst:
        dst.write(arr.astype(dtype, copy=False), 1)


def compare(new, old_path: Path, valid_mask, transform, categorical=False):
    with rasterio.open(old_path) as src:
        old = src.read(1).astype(np.float64)
        old_valid = np.isfinite(old) & (old != src.nodata)
    both = valid_mask & old_valid
    if not both.any():
        return {"common_cells": 0, "note": "no overlapping valid cells"}
    n = new.astype(np.float64)
    delta = n[both] - old[both]
    r, c = np.where(both)
    if categorical:
        changed = n[both] != old[both]
        k = int(np.argmax(np.abs(delta))) if len(delta) else 0
        return {"common_cells": int(both.sum()), "changed_cells": int(changed.sum()),
                "changed_percent": float(changed.mean() * 100),
                "largest_code_difference_cell_lonlat": [float(x) for x in rasterio.transform.xy(transform, int(r[k]), int(c[k]), offset="center")]}
    k = int(np.argmax(np.abs(delta)))
    lonx, laty = rasterio.transform.xy(transform, int(r[k]), int(c[k]), offset="center")
    return {"common_cells": int(both.sum()), "mean_difference_new_minus_old": float(delta.mean()),
            "median_difference": float(np.median(delta)), "mae": float(np.mean(np.abs(delta))),
            "rmse": float(np.sqrt(np.mean(delta ** 2))), "p95_absolute_difference": float(np.percentile(np.abs(delta), 95)),
            "max_absolute_difference": float(abs(delta[k])), "largest_difference_cell_xy": [float(x) for x in (lonx, laty)]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repair-generated-derivatives", action="store_true", help="Add edge-safe slope/TWI and valid-only fill-depth rasters under new names; preserves existing files.")
    args = parser.parse_args()
    if args.repair_generated_derivatives:
        if not TARGET.exists():
            raise FileNotFoundError(f"Cannot add edge-safe derivatives before terrain output exists: {TARGET}")
        additions = [TARGET / "depression_fill_depth_m_valid_only.tif", TARGET / "slope_deg_edge_safe.tif", TARGET / "twi_d8_proxy_edge_safe.tif"]
        if any(p.exists() for p in additions):
            raise FileExistsError(f"Refusing to overwrite repair outputs: {[str(p) for p in additions if p.exists()]}")
        with rasterio.open(TARGET / "cleaned_elevation_m.tif") as src:
            z=src.read(1).astype(np.float32); valid=src.read_masks(1)>0; transform,crs=src.transform,src.crs
        with rasterio.open(TARGET / "depression_fill_depth_m.tif") as src:
            fill=src.read(1).astype(np.float32); fill[~valid]=NODATA
        neighbor_count=np.zeros(valid.shape,dtype=np.uint8)
        h,w=valid.shape
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                ys=slice(max(0,-dy),min(h,h-dy)); xs=slice(max(0,-dx),min(w,w-dx))
                yn=slice(max(0,dy),min(h,h+dy)); xn=slice(max(0,dx),min(w,w+dx))
                neighbor_count[ys,xs] += valid[yn,xn]
        inner=valid & (neighbor_count==9)
        with rasterio.open(TARGET / "flow_accumulation_cells_d8.tif") as src: accumulation=src.read(1)
        slope,twi=derivatives(z,inner,accumulation)
        for p,a,dtype,nd in [(additions[0],fill,"float32",NODATA),(additions[1],slope,"float32",NODATA),(additions[2],twi,"float32",NODATA)]:
            write_tif(p,a,transform,crs,dtype,nd)
        print(json.dumps({"new_files":[str(p.relative_to(ROOT)) for p in additions],"edge_cells_set_nodata":int(valid.sum()-inner.sum()),"valid_inner_cells":int(inner.sum())},indent=2))
        return
    if TARGET.exists() or REPORT.exists():
        raise FileExistsError(f"Refusing to overwrite existing target(s): {[str(p) for p in (TARGET, REPORT) if p.exists()]}")

    with rasterio.open(DEM) as src:
        elevation = src.read(1).astype(np.float32)
        transform, crs, profile = src.transform, src.crs, src.profile.copy()
        dem_nodata = src.nodata
    valid = np.isfinite(elevation) & (elevation != dem_nodata)
    with rasterio.open(GRID_MASK) as src:
        cma = src.read(1) == 1
    with rasterio.open(WC) as src:
        wc = src.read(1)
        if wc.shape != elevation.shape or src.transform != transform:
            raise ValueError("WorldCover class raster does not exactly align with the master grid")
    xmin, ymin, xmax, ymax = profile["width"] * transform.a + transform.c, transform.f + profile["height"] * transform.e, transform.c, transform.f
    grid_box = box(min(xmin, xmax), min(ymin, ymax), max(xmin, xmax), max(ymin, ymax))
    to_utm = Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(crs, "EPSG:4326", always_xy=True).transform
    projected_corners = [to_wgs84(xmin, ymin), to_wgs84(xmax, ymax)]
    geographic_bounds = (min(x for x, _ in projected_corners), min(y for _, y in projected_corners),
                         max(x for x, _ in projected_corners), max(y for _, y in projected_corners))
    handler = WaterAndRivers(to_utm, grid_box, geographic_bounds)
    handler.apply_file(str(OSM), locations=True, idx="sparse_mem_map")
    river_geoms = [g for entries in handler.rivers.values() for g in entries]
    if not all(handler.rivers.values()):
        missing = [name for name, geoms in handler.rivers.items() if not geoms]
        raise RuntimeError(f"Exact-match target river/canal geometries missing from local OSM PBF: {missing}")
    water_shapes = [mapping(g) for g in handler.water_polygons + handler.water_lines]
    osm_water = rasterize(((g, 1) for g in water_shapes), out_shape=elevation.shape, transform=transform,
                          fill=0, all_touched=True, dtype="uint8") if water_shapes else np.zeros(elevation.shape, dtype="uint8")
    target_river_cells = rasterize(((mapping(g), 1) for g in river_geoms), out_shape=elevation.shape, transform=transform,
                                   fill=0, all_touched=True, dtype="uint8")
    world_water = (wc == 80)
    combined_water = world_water | (osm_water == 1)
    # Preserve target channels from water masking so their stated burn can be applied.
    water_mask = combined_water & (target_river_cells == 0)
    low_elevation_mask = cma & valid & (elevation < -5.0)
    valid &= ~low_elevation_mask & ~water_mask
    base = elevation.copy()
    base[~valid] = NODATA
    print(f"Priority-Flood on {int(valid.sum()):,} valid cells...", flush=True)
    filled = priority_flood(base, valid)
    fill_depth = np.zeros(elevation.shape, dtype=np.float32)
    fill_depth[valid] = np.maximum(0.0, filled[valid] - base[valid])
    fill_depth[~valid] = NODATA
    burned = filled.copy()
    burn_mask = (target_river_cells == 1) & valid
    burned[burn_mask] = np.maximum(NODATA + 1, filled[burn_mask] - BURN_DEPTH_M)
    direction, accumulation, _ = d8(burned, valid)
    slope, twi = derivatives(burned, valid, accumulation)
    direction[~valid] = 255
    accumulation[~valid] = NODATA
    twi[~valid] = NODATA

    # Stage as a new unique sibling folder; promote atomically only after every file succeeds.
    stage = PROCESSED / f".terrain_cleaned_build_{uuid.uuid4().hex}"
    stage.mkdir(parents=True)
    outputs = {
        "cleaned_elevation_m.tif": (burned, "float32", NODATA),
        "depression_fill_depth_m.tif": (fill_depth, "float32", NODATA),
        "slope_deg.tif": (slope, "float32", NODATA),
        "flow_direction_d8.tif": (direction, "uint8", 255),
        "flow_accumulation_cells_d8.tif": (accumulation, "float32", NODATA),
        "twi_d8_proxy.tif": (twi, "float32", NODATA),
    }
    for filename, (arr, dtype, nd) in outputs.items():
        write_tif(stage / filename, arr, transform, crs, dtype, nd)
    water_area_raw = float((combined_water & cma).sum() * CELL * CELL / 1e6)
    water_area_masked = float((water_mask & cma).sum() * CELL * CELL / 1e6)
    stats = {"cma_cells_below_minus5_masked": int(low_elevation_mask.sum()),
             "low_elevation_area_km2": float(low_elevation_mask.sum() * CELL * CELL / 1e6),
             "worldcover_water_cells": int((world_water & cma).sum()), "osm_water_raster_cells": int((osm_water.astype(bool) & cma).sum()),
             "combined_water_area_km2_before_target_channel_reinstatement": water_area_raw,
             "water_area_masked_km2_after_target_channel_reinstatement": water_area_masked,
             "target_channel_cells_preserved_for_burn": int(burn_mask.sum()), "target_burn_depth_m": BURN_DEPTH_M,
             "target_lines": {name: {"way_ids": handler.river_way_ids[name], "segments": len(handler.rivers[name]),
                                      "length_km": float(sum(g.length for g in handler.rivers[name]) / 1000)} for name in TARGET_NAMES},
             "depression_fill_cells": int((fill_depth > 0).sum()), "max_fill_depth_m": float(fill_depth.max()),
             "mean_positive_fill_depth_m": float(fill_depth[fill_depth > 0].mean()) if (fill_depth > 0).any() else 0,
             "output_comparisons": {"slope_deg": compare(slope, OLD / "slope_deg.tif", valid, transform),
                                    "flow_direction_d8": compare(direction, OLD / "flow_direction_d8.tif", valid, transform, True),
                                    "flow_accumulation_cells_d8": compare(accumulation, OLD / "flow_accumulation_cells_d8.tif", valid, transform),
                                    "twi_d8_proxy": compare(twi, OLD / "twi_d8_proxy.tif", valid, transform)}}
    (stage / "conditioning_metadata.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    stage.rename(TARGET)
    report = ["# Terrain conditioning — Phase 4 Part 1", "", "New outputs are under `data/processed/terrain_cleaned/`. Existing terrain layers and raw inputs were not altered.", "",
              "## Masks and conditioning", "", f"Masked CMA elevation cells below −5 m: **{stats['cma_cells_below_minus5_masked']:,}** ({stats['low_elevation_area_km2']:.4f} km²).",
              f"WorldCover class-80 cells: {stats['worldcover_water_cells']:,}. Rasterized OSM water polygons/lines: {stats['osm_water_raster_cells']:,} cells. The combined rasterized water footprint is {water_area_raw:.3f} km²; after preserving named target channels for burn-in, {water_area_masked:.3f} km² is masked.",
              "Water area is a 30 m cell-footprint estimate. This local OSM extract provides waterways and closed water-tagged ways; incomplete relation multipolygons or unnamed/unmapped water are not guaranteed represented. Target channel centerlines are explicitly restored from the water mask so they can be burned.",
              f"Priority-Flood depression filling modified {stats['depression_fill_cells']:,} cells; maximum fill depth {stats['max_fill_depth_m']:.3f} m; mean positive fill depth {stats['mean_positive_fill_depth_m']:.3f} m.",
              f"The exact-match channel lines were burned by **{BURN_DEPTH_M:.1f} m** below the filled surface. This is a modeling assumption, not a locally calibrated channel depth. Named channels: " + "; ".join(f"{k}: {v['segments']} segments, {v['length_km']:.3f} km" for k, v in stats["target_lines"].items()) + ".", "",
              "GLO-30 is a digital surface model (DSM): it includes returns from buildings and trees, not just bare earth. The fill and burn assumptions cannot remove those surface artifacts.", "",
              "## Differences from existing terrain layers", "", "Comparisons use cells valid in both old and new rasters; the largest-difference coordinates are in EPSG:32644 metres.", "",
              "| Layer | Difference summary | Largest difference location (E, N) m |", "|---|---|---|"]
    for key, val in stats["output_comparisons"].items():
        if "rmse" in val:
            summary = f"n={val['common_cells']:,}; mean Δ={val['mean_difference_new_minus_old']:.4g}; MAE={val['mae']:.4g}; RMSE={val['rmse']:.4g}; P95 |Δ|={val['p95_absolute_difference']:.4g}; max |Δ|={val['max_absolute_difference']:.4g}"
            loc = val["largest_difference_cell_xy"]
        else:
            summary = f"n={val['common_cells']:,}; changed={val['changed_cells']:,} ({val['changed_percent']:.2f}%)"
            loc = val["largest_code_difference_cell_lonlat"]
        report.append(f"| {key} | {summary} | {loc[0]:.1f}, {loc[1]:.1f} |")
    report += ["", "Slope is in degrees, D8 direction codes use the same eight-neighbor ordering as the Phase 3 implementation, accumulation is upstream-cell count, and TWI uses the existing project proxy equation. D8 ties remain sinks; masked water creates hydrologic outlets. The TWI is a proxy, not a calibrated wetness product.", "",
               "## Assumptions and validation notes", "", "The less-than −5 m mask applies only within the CMA; the DSM outside the CMA remains available for context and routing. WorldCover class 80 is used as the 30 m permanent-water proxy. OSM water polygons and lines are rasterized by all-touched 30 m cells, which can over/understate true water width. The four exact-match target channels are restored from the combined water mask and burned by 2 m. This explicit exception is needed to meet both water masking and stream burning objectives.",
               "No terrain values were corrected manually. The previously found source minimum (about −64.51 m) was masked inside the CMA by the requested cutoff. Depressions were filled from the perimeter and valid-mask boundaries with Priority-Flood; this treats mask boundaries as outlets. No existing terrain file was overwritten.", ""]
    REPORT.write_text("\n".join(report), encoding="utf-8")
    print(f"Wrote {TARGET.relative_to(ROOT)} and {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
