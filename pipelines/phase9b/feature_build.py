"""Build a new, read-only-source physical feature table for Phase 9B.

Writes a new Parquet table and metadata sidecar. Existing feature tables and
everything under data/raw are inputs only and are never modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import osmium
import pandas as pd
import pyogrio
import rasterio
import geopandas as gpd
from pyproj import Transformer
from rasterio.features import rasterize
from scipy.ndimage import distance_transform_edt, uniform_filter
from shapely.geometry import LineString, Polygon, box
from shapely.ops import transform as transform_geometry

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/features/static/cell_table_phase9b_v2.parquet"
META = ROOT / "data/features/static/cell_table_phase9b_v2.json"
BASE = ROOT / "data/features/static/cell_table.parquet"
OSM_PBF = ROOT / "data/raw/roads/southern-zone-latest.osm.pbf"
OSM_GPKG = ROOT / "data/features/osm/chennai_osm_features.gpkg"
OSM_CACHE = ROOT / "data/processed/sar_work/phase9b_osm_water_cache.gpkg"
WC_FRAC = ROOT / "data/features/landcover/worldcover_2021_area_fractions_30m.tif"
TERRAIN = ROOT / "data/processed/terrain_cleaned"
GRID = ROOT / "data/processed/grid/cma_mask.tif"
CELL_M = 30.0
NODATA = -9999.0
ACCUMULATION_THRESHOLDS = (25, 100, 250, 500)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_float(path: Path) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as ds:
        a = ds.read(1).astype(np.float32)
        valid = np.isfinite(a)
        if ds.nodata is not None:
            valid &= a != ds.nodata
        a[~valid] = np.nan
        return a, {"height": ds.height, "width": ds.width, "transform": ds.transform,
                   "crs": ds.crs, "nodata": ds.nodata}


def relative_elevation(z: np.ndarray, valid: np.ndarray, size: int) -> np.ndarray:
    """Cell elevation minus the valid-data mean in a square odd-cell window."""
    if size < 1 or size % 2 == 0:
        raise ValueError("window size must be a positive odd number")
    values = np.where(valid, z, 0).astype(np.float64)
    weights = valid.astype(np.float64)
    mean_sum = uniform_filter(values, size=size, mode="constant", cval=0.0)
    valid_share = uniform_filter(weights, size=size, mode="constant", cval=0.0)
    # uniform_filter returns means over the full window; the ratio cancels its scale.
    with np.errstate(divide="ignore", invalid="ignore"):
        mean = mean_sum / valid_share
    out = z.astype(np.float64) - mean
    out[~valid | ~np.isfinite(out)] = np.nan
    return out.astype(np.float32)


def terrain_curvature(z: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Plan/profile curvature from a local 3x3 finite-difference Hessian."""
    # Fill only for numerical derivatives; exclude all cells whose 3x3 neighborhood
    # touches NoData from the returned derivatives.
    nearest = distance_transform_edt(~valid, return_distances=False, return_indices=True)
    filled = z[tuple(nearest)].astype(np.float64)
    gy, gx = np.gradient(filled, CELL_M, CELL_M)
    gyy, gyx = np.gradient(gy, CELL_M, CELL_M)
    gxy, gxx = np.gradient(gx, CELL_M, CELL_M)
    zxx, zxy, zyy = gxx, (gyx + gxy) / 2.0, gyy
    p, q = gx, gy
    g2 = p * p + q * q
    plan = np.full(z.shape, np.nan, dtype=np.float32)
    profile = np.full(z.shape, np.nan, dtype=np.float32)
    interior = uniform_filter(valid.astype(np.float32), size=3, mode="constant", cval=0.0) >= 1.0
    nonflat = g2 > 1e-12
    ok = interior & nonflat
    plan[ok] = ((q[ok]**2 * zxx[ok] - 2*p[ok]*q[ok]*zxy[ok] + p[ok]**2*zyy[ok]) /
                np.maximum(g2[ok] ** 1.5, 1e-12)).astype(np.float32)
    profile[ok] = ((p[ok]**2*zxx[ok] + 2*p[ok]*q[ok]*zxy[ok] + q[ok]**2*zyy[ok]) /
                   np.maximum(g2[ok] * (1.0 + g2[ok]) ** 1.5, 1e-12)).astype(np.float32)
    return plan, profile


def compute_hand_and_flow_length(z: np.ndarray, direction: np.ndarray, accumulation: np.ndarray,
                                 valid: np.ndarray, thresholds=ACCUMULATION_THRESHOLDS,
                                 drainage_mask: np.ndarray | None = None):
    """D8 HAND to combined mapped/accumulation drainage and path length to threshold streams."""
    offsets = {1: (-1, 0), 2: (-1, 1), 3: (0, 1), 4: (1, 1),
               5: (1, 0), 6: (1, -1), 7: (0, -1), 8: (-1, -1)}
    h, w = z.shape
    downstream = np.full(h*w, -1, dtype=np.int64)
    rr, cc = np.indices((h, w))
    for code, (dy, dx) in offsets.items():
        src = valid & (direction == code)
        ids = np.flatnonzero(src)
        r, c = rr[src] + dy, cc[src] + dx
        inside = (r >= 0) & (r < h) & (c >= 0) & (c < w)
        ids, r, c = ids[inside], r[inside], c[inside]
        good = valid.ravel()[r*w+c]
        downstream[ids[good]] = r[good]*w+c[good]
    ids = np.flatnonzero(valid.ravel())
    order = ids[np.argsort(z.ravel()[ids], kind="stable")]  # downstream lower cells first
    hand = np.full(h*w, np.nan, dtype=np.float32)
    elev_to_stream = np.full(h*w, np.nan, dtype=np.float32)
    if drainage_mask is None:
        drainage = valid & (accumulation >= 100)
    else:
        if drainage_mask.shape != valid.shape:
            raise ValueError("Drainage mask does not share the DEM grid")
        drainage = valid & ((accumulation >= 100) | drainage_mask)
    stream100 = drainage.ravel()
    elev_to_stream[stream100] = z.ravel()[stream100]
    for i in order:
        if stream100[i]:
            continue
        j = downstream[i]
        if j >= 0 and np.isfinite(elev_to_stream[j]):
            elev_to_stream[i] = elev_to_stream[j]
    got = valid.ravel() & np.isfinite(elev_to_stream)
    hand[got] = np.maximum(0.0, z.ravel()[got] - elev_to_stream[got])
    length_features = {}
    threshold_counts = {}
    for threshold in thresholds:
        stream = valid.ravel() & (accumulation.ravel() >= threshold)
        distance = np.full(h*w, np.nan, dtype=np.float32)
        distance[stream] = 0.0
        for i in order:
            if stream[i]:
                continue
            j = downstream[i]
            if j >= 0 and np.isfinite(distance[j]):
                dy = abs((i // w) - (j // w)); dx = abs((i % w) - (j % w))
                distance[i] = (math.sqrt(2.0) if dy and dx else 1.0)*CELL_M + distance[j]
        length_features[f"d8_flow_length_to_stream_{threshold}cells_m"] = distance.reshape(h, w)
        threshold_counts[str(threshold)] = int(stream.sum())
    hand[~got] = np.nan
    return hand.reshape(h, w), length_features, {
        "hand_stream_threshold_cells": 100,
        "hand_drainage_cells": int(drainage.sum()),
        "hand_added_mapped_water_cells": int((drainage & (accumulation < 100)).sum()),
        "hand_valid_cells": int(got.sum()),
        "d8_stream_cells_by_threshold": threshold_counts,
        "hand_note": "D8 DSM height above downstream drainage seeded by mapped OSM waterways/water bodies/reservoirs, WorldCover water, and accumulation >= 100 cells; sinks/outlets with no downstream drainage remain NoData",
    }


class OSMWater(osmium.SimpleHandler):
    """Read closed water ways, waterway/coastline lines from the local PBF."""
    def __init__(self, bbox, transformer):
        super().__init__()
        self.bbox = bbox
        self.transformer = transformer
        self.water_polygons = []
        self.reservoir_polygons = []
        self.water_lines = []
        self.coastlines = []
        self.counts = {"water_polygon_ways": 0, "reservoir_polygon_ways": 0,
                       "waterway_line_ways": 0, "coastline_line_ways": 0,
                       "natural_water_lines": 0}

    def way(self, way):
        tags = dict(way.tags)
        natural = tags.get("natural")
        water = tags.get("water")
        waterway = tags.get("waterway")
        if natural != "coastline" and natural != "water" and not water and not waterway:
            return
        coords = [(n.location.lon, n.location.lat) for n in way.nodes if n.location.valid()]
        if len(coords) < 2:
            return
        closed = len(coords) >= 4 and coords[0] == coords[-1]
        try:
            if closed and (natural == "water" or water):
                g = transform_geometry(self.transformer, Polygon(coords)).intersection(self.bbox)
                if not g.is_empty and g.is_valid:
                    self.water_polygons.append(g)
                    self.counts["water_polygon_ways"] += 1
                    if water == "reservoir":
                        self.reservoir_polygons.append(g)
                        self.counts["reservoir_polygon_ways"] += 1
            elif natural == "coastline":
                g = transform_geometry(self.transformer, LineString(coords)).intersection(self.bbox)
                if not g.is_empty:
                    self.coastlines.append(g)
                    self.counts["coastline_line_ways"] += 1
            elif waterway or natural == "water" or water:
                g = transform_geometry(self.transformer, LineString(coords)).intersection(self.bbox)
                if not g.is_empty:
                    self.water_lines.append(g)
                    self.counts["waterway_line_ways"] += 1
                    if natural == "water":
                        self.counts["natural_water_lines"] += 1
        except Exception:
            # A malformed local feature is excluded and counted in this explicit field.
            self.counts["unreadable_or_invalid_ways"] = self.counts.get("unreadable_or_invalid_ways", 0) + 1


def distance_from_source(source: np.ndarray, valid: np.ndarray) -> np.ndarray:
    if not source.any():
        return np.full(source.shape, np.nan, dtype=np.float32)
    d = distance_transform_edt(~source, sampling=(CELL_M, CELL_M)).astype(np.float32)
    d[~valid] = np.nan
    return d


def build(output: Path = OUT, metadata_path: Path = META) -> dict:
    if output.exists() or metadata_path.exists():
        raise FileExistsError("Refusing to overwrite Phase 9B feature table or metadata")
    required = [BASE, OSM_PBF, OSM_GPKG, WC_FRAC, GRID,
                TERRAIN/"cleaned_elevation_m.tif", TERRAIN/"slope_deg_edge_safe.tif",
                TERRAIN/"twi_d8_proxy_edge_safe.tif", TERRAIN/"flow_accumulation_cells_d8.tif",
                TERRAIN/"flow_direction_d8.tif", TERRAIN/"depression_fill_depth_m_valid_only.tif"]
    missing = [p.as_posix() for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError("Required existing feature inputs missing: " + ", ".join(missing))
    table = pd.read_parquet(BASE)
    pilot_labels_path = ROOT / "data/features/predictions/labels_nov2015.parquet"
    if not pilot_labels_path.is_file():
        raise FileNotFoundError("Existing Phase 9 pilot label table missing; labels will not be reconstructed or changed")
    pilot_labels = pd.read_parquet(pilot_labels_path, columns=["row", "col", "eligible_for_model"])
    if not np.array_equal(table[["row", "col"]].to_numpy(), pilot_labels[["row", "col"]].to_numpy()):
        raise ValueError("Phase 9 pilot labels do not have the same row/column order as the static cell table")
    grid_mask, grid_meta = read_float(GRID)
    z, zmeta = read_float(TERRAIN/"cleaned_elevation_m.tif")
    slope, _ = read_float(TERRAIN/"slope_deg_edge_safe.tif")
    twi, _ = read_float(TERRAIN/"twi_d8_proxy_edge_safe.tif")
    accumulation, _ = read_float(TERRAIN/"flow_accumulation_cells_d8.tif")
    direction, _ = read_float(TERRAIN/"flow_direction_d8.tif")
    depression, _ = read_float(TERRAIN/"depression_fill_depth_m_valid_only.tif")
    if not (z.shape == grid_mask.shape == slope.shape == twi.shape == accumulation.shape == direction.shape):
        raise ValueError("Terrain inputs do not share the master grid")
    cma = np.isfinite(grid_mask) & (grid_mask == 1)
    valid_dem = np.isfinite(z)
    arrays: dict[str, np.ndarray] = {
        "hand_d8_accum100_m": np.full(z.shape, np.nan, dtype=np.float32),
        "relative_elevation_5cells_m": relative_elevation(z, valid_dem, 5),
        "relative_elevation_15cells_m": relative_elevation(z, valid_dem, 15),
        "relative_elevation_33cells_m": relative_elevation(z, valid_dem, 33),
        "local_depression_depth_m": depression,
    }
    arrays["plan_curvature_per_m"], arrays["profile_curvature_per_m"] = terrain_curvature(z, valid_dem)
    hand, flow_lengths, flow_stats = compute_hand_and_flow_length(
        z, np.nan_to_num(direction, nan=255).astype(np.uint8),
        np.nan_to_num(accumulation, nan=0), valid_dem)
    arrays["hand_d8_accum100_m"] = hand
    arrays.update(flow_lengths)
    arrays["upslope_area_km2"] = accumulation * (CELL_M*CELL_M/1_000_000.0)
    for threshold in ACCUMULATION_THRESHOLDS:
        arrays[f"upslope_area_ge_{threshold}cells_km2"] = np.where(
            np.isfinite(accumulation) & (accumulation >= threshold), arrays["upslope_area_km2"], 0.0).astype(np.float32)

    # Read WorldCover fractions by documented band description; no remapping or resampling.
    with rasterio.open(WC_FRAC) as ds:
        if ds.shape != z.shape:
            raise ValueError("WorldCover area-fraction raster is not on the 30 m master grid")
        descriptions = {d: i+1 for i, d in enumerate(ds.descriptions) if d}
        for class_code, feature_name in ((10,"tree_fraction"),(40,"crop_fraction"),
                                         (30,"grass_fraction"),(60,"bare_fraction"),
                                         (50,"built_up_fraction_phase9b"),(80,"water_fraction_phase9b")):
            band = descriptions.get(f"class_{class_code}_area_fraction")
            if band is None:
                raise ValueError(f"WorldCover class fraction band missing: {class_code}")
            a = ds.read(band).astype(np.float32)
            a[(a == ds.nodata) | ~np.isfinite(a)] = np.nan
            arrays[feature_name] = a

    # Local OSM water features: include existing waterways plus closed tagged water ways
    # (including water=reservoir) and natural=coastline ways when present in the PBF.
    with rasterio.open(GRID) as ds:
        transform, crs, shape = ds.transform, ds.crs, ds.shape
        bounds = ds.bounds
    bbox = box(bounds.left, bounds.bottom, bounds.right, bounds.top)
    if OSM_CACHE.is_file():
        poly = pyogrio.read_dataframe(OSM_CACHE, layer="water_polygons")
        lines = pyogrio.read_dataframe(OSM_CACHE, layer="water_lines")
        coasts = pyogrio.read_dataframe(OSM_CACHE, layer="coastlines")
        osm_water = OSMWater(bbox, None)
        osm_water.water_polygons = [g for g in poly.geometry if g is not None and not g.is_empty]
        osm_water.reservoir_polygons = [g for g, is_res in zip(poly.geometry, poly["is_reservoir"]) if is_res and g is not None]
        osm_water.water_lines = [g for g in lines.geometry if g is not None and not g.is_empty]
        osm_water.coastlines = [g for g in coasts.geometry if g is not None and not g.is_empty]
        osm_water.counts = json.loads((OSM_CACHE.with_suffix(".json")).read_text(encoding="utf-8"))
    else:
        transformer = Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform
        osm_water = OSMWater(bbox, transformer)
        osm_water.apply_file(str(OSM_PBF), locations=True, idx="sparse_mem_map")
        OSM_CACHE.parent.mkdir(parents=True, exist_ok=True)
        reservoir_ids = {id(g) for g in osm_water.reservoir_polygons}
        poly = gpd.GeoDataFrame({"is_reservoir": [id(g) in reservoir_ids for g in osm_water.water_polygons]},
                                geometry=osm_water.water_polygons, crs=crs)
        lines = gpd.GeoDataFrame(geometry=osm_water.water_lines, crs=crs)
        coasts = gpd.GeoDataFrame(geometry=osm_water.coastlines, crs=crs)
        pyogrio.write_dataframe(poly, OSM_CACHE, layer="water_polygons", driver="GPKG")
        pyogrio.write_dataframe(lines, OSM_CACHE, layer="water_lines", driver="GPKG", append=True)
        pyogrio.write_dataframe(coasts, OSM_CACHE, layer="coastlines", driver="GPKG", append=True)
        OSM_CACHE.with_suffix(".json").write_text(json.dumps(osm_water.counts, indent=2)+"\n", encoding="utf-8")
    line_frame = pyogrio.read_dataframe(OSM_GPKG, layer="waterways", columns=["osmid", "waterway"])
    line_geoms = [g for g in line_frame.geometry if g is not None and not g.is_empty]
    all_water_shapes = line_geoms + osm_water.water_lines + osm_water.water_polygons
    osm_source = rasterize(((g,1) for g in all_water_shapes), out_shape=shape, transform=transform,
                          fill=0, all_touched=True, dtype="uint8").astype(bool) if all_water_shapes else np.zeros(shape, bool)
    with rasterio.open(WC_FRAC) as ds:
        wc_water = ds.read(descriptions["class_80_area_fraction"]) > 0
    all_water_source = osm_source | wc_water
    # The final HAND drainage seeds combine mapped waterways and water bodies,
    # reservoirs, WorldCover water, and the >=100-cell D8 accumulation stream.
    # Recompute HAND against those seeds; flow-length products remain tied to
    # their separately documented accumulation thresholds.
    hand, _, hand_stats = compute_hand_and_flow_length(
        z, np.nan_to_num(direction, nan=255).astype(np.uint8),
        np.nan_to_num(accumulation, nan=0), valid_dem,
        drainage_mask=all_water_source)
    arrays["hand_d8_accum100_m"] = hand
    flow_stats.update(hand_stats)
    arrays["distance_to_all_available_water_m"] = distance_from_source(all_water_source, valid_dem)
    coastline_source = rasterize(((g,1) for g in osm_water.coastlines), out_shape=shape,
                                 transform=transform, fill=0, all_touched=True,
                                 dtype="uint8").astype(bool) if osm_water.coastlines else np.zeros(shape,bool)
    if coastline_source.any():
        coast_method = "OSM natural=coastline ways in local PBF; Euclidean distance to rasterized 30 m cells"
        coast_source_name = "OSM coastline"
    else:
        # Conservative fallback explicitly names water as a sea proxy; don't invent coastline.
        labels, n_labels = __import__("scipy.ndimage", fromlist=["label"]).label(wc_water)
        border_ids = np.unique(np.concatenate((labels[0,:], labels[-1,:], labels[:,0], labels[:,-1])))
        sea_ids = border_ids[border_ids > 0]
        coastline_source = np.isin(labels, sea_ids) if sea_ids.size else np.zeros(shape,bool)
        coast_method = "OSM coastline absent; distance to WorldCover water component(s) touching raster edge as sea proxy"
        coast_source_name = "WorldCover edge-connected water proxy"
    arrays["distance_to_coast_or_sea_m"] = distance_from_source(coastline_source, valid_dem)

    rows = table["row"].to_numpy(dtype=np.int32)
    cols = table["col"].to_numpy(dtype=np.int32)
    if np.any(rows < 0) or np.any(cols < 0) or np.any(rows >= shape[0]) or np.any(cols >= shape[1]):
        raise ValueError("Base cell table index outside master grid")
    for name, raster in arrays.items():
        if raster.shape != shape:
            raise ValueError(f"Feature grid mismatch: {name}")
        table[name] = raster[rows, cols].astype(np.float32)
    pilot_eligible = pilot_labels["eligible_for_model"].to_numpy(dtype=bool)
    if "water_fraction" in table and np.nanstd(table.loc[pilot_eligible, "water_fraction"]) == 0:
        table = table.drop(columns=["water_fraction"])
    # NoData indicator is an eligibility mask, never a predictor. Keep values and flag in table.
    table["population_is_nodata"] = table["population_is_nodata"].astype(bool)
    table.to_parquet(output, index=False, compression="zstd")
    feature_columns = [c for c in arrays]
    metadata = {
        "status": "DERIVED PHASE 9B v2 FEATURE TABLE; HAND drainage includes mapped water; not a new label and not field validated",
        "table": output.relative_to(ROOT).as_posix(),
        "rows": int(len(table)), "crs": "EPSG:32644", "grid_resolution_m": 30,
        "input_sha256": {str(p.relative_to(ROOT)).replace("\\","/"): sha256(p) for p in required},
        "pilot_label_table_sha256": sha256(pilot_labels_path),
        "new_feature_columns": feature_columns,
        "hand_drainage_definition": "Rasterized existing OSM waterways, locally extracted OSM water bodies and reservoir ways, WorldCover class 80 water, plus flow accumulation >= 100 cells. HAND is elevation minus the downstream D8 drainage-seed elevation; cells without a reachable downstream seed remain NoData.",
        "population_is_nodata": "eligibility mask only; excluded from predictor columns",
        "zero_variance_water_fraction_dropped": "water_fraction" not in table.columns,
        "water_sources": ["existing OSM waterways lines", "closed natural=water/tagged water ways from local PBF, including water=reservoir when present", "WorldCover class 80"],
        "water_source_counts": {**osm_water.counts, "existing_osm_waterway_lines": len(line_geoms),
                                "rasterized_osm_water_cells": int(osm_source.sum()),
                                "worldcover_water_cells": int(wc_water.sum()),
                                "osm_reservoir_polygons": len(osm_water.reservoir_polygons)},
        "coast_distance_source": coast_source_name,
        "coast_distance_method": coast_method,
        "limitations": ["PBF way extraction does not reconstruct relation multipolygons", "OpenCity reservoir time series has no coordinate geometry in the local table; reservoirs enter only when mapped as local OSM water polygons", "WorldCover is a 2021 categorical water proxy", "distances are Euclidean raster distances, not channel-network distances", "flow length follows existing D8 routing and inherits DEM sink/outlet limitations"],
        "hydrology": flow_stats,
        "upslope_threshold_cells": list(ACCUMULATION_THRESHOLDS),
    }
    metadata["table_sha256"] = sha256(output)
    metadata_path.write_text(json.dumps(metadata, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--metadata", type=Path, default=META)
    args = parser.parse_args()
    result = build(args.output, args.metadata)
    print(json.dumps({k: result[k] for k in ("table", "rows", "new_feature_columns", "water_source_counts", "coast_distance_source", "hydrology")}, indent=2))
