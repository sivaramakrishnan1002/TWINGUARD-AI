#!/usr/bin/env python
"""A25: build versioned static bundles for the high-resolution flood engine.

Output: data/features/live/a25_static_v1/
  shared/   buildings.npz, roads.npz, shelters.npz, wards.geojson, focus_areas.geojson, reservoirs.json, events.json
  citywide_120m/ static.npz + meta.json      (plus citywide_90m/ when requested)
  focus_30m_<AREA>/ static.npz + meta.json   (VELACHERY, ADYAR, T_NAGAR, PORUR)
Every grid uses EPSG:32644, origin at the upper-left corner, row 0 north (C4 v3 GridSpec).
Inputs are read-only: cleaned GLO-30 DEM (from data/raw/dem), WorldCover, WorldPop 30 m, OSM (gpkg + raw PBF tags),
GCC wards (data/features/wards/gcc_wards_v1), A06 IMERG/ERA5 event rainfall.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pyogrio
import rasterio
import shapely
from rasterio.features import rasterize
from rasterio.transform import Affine
from rasterio.warp import transform as warp_transform
from scipy import ndimage

from pipelines.phase12 import simulate as a06

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/features/live/a25_static_v1"
DEM = ROOT / "data/processed/terrain_cleaned/cleaned_elevation_m.tif"
WORLDCOVER = ROOT / "data/features/landcover/worldcover_2021_class.tif"
WORLDPOP = ROOT / "data/features/population/worldpop_2021_sum_resampled_30m.tif"
CELLS = ROOT / "data/features/static/cell_table.parquet"
BUILDINGS = ROOT / "data/features/buildings/chennai_building_footprints.gpkg"
OSM = ROOT / "data/features/osm/chennai_osm_features.gpkg"
PBF = ROOT / "data/raw/roads/southern-zone-latest.osm.pbf"
WARDS = ROOT / "data/features/wards/gcc_wards_v1/Wards.geojson"
ARCS = ROOT / "data/features/routing/time_dependent_batch2/directed_arcs.parquet"
CRS = "EPSG:32644"

# Focus areas: 6 km x 6 km boxes centred on each locality (WGS84 centre).
FOCUS_CENTRES = {"VELACHERY": (80.2185, 12.9791), "ADYAR": (80.2550, 13.0012), "T_NAGAR": (80.2341, 13.0418), "PORUR": (80.1580, 13.0358)}
FOCUS_SIZE_M = 6000
# Reservoir surplus -> river entering the domain; release injected at the river cell nearest the reservoir.
RESERVOIRS = {
    "CHEMBARAMBAKKAM": {"lonlat": (80.060, 13.010), "river": "Adyar River"},
    "POONDI": {"lonlat": (79.860, 13.195), "river": "Kosasthalaiyar River"},
    "PUZHAL": {"lonlat": (80.180, 13.165), "river": "Kosasthalaiyar River"},
    "CHOLAVARAM": {"lonlat": (80.150, 13.230), "river": "Kosasthalaiyar River"},
}
RIVER_WAYS = {  # from data/processed/terrain_cleaned/conditioning_metadata.json target_lines
    "Adyar River": [23110069, 178105896, 178105900, 202471872, 383852846],
    "Cooum": [202505379],
    "Kosasthalaiyar River": [25395844, 30777996, 910151265, 910151277],
}
MANNING = {10: .12, 20: .10, 30: .035, 40: .08, 50: .06, 60: .03, 70: .035, 80: .03, 90: .08, 95: .10, 100: .04}
INFIL_MM_H = {10: 1.4, 20: 1.2, 30: 1.0, 40: 1.4, 50: .25, 60: .4, 70: .5, 80: 0., 90: .8, 95: .8, 100: .5}
SHELTER_CAPACITY = {"shelter": 100, "school": 250, "college": 500, "community_hall": 150}  # A10 defaults + halls
SHELTER_CATEGORIES = {"shelter": "shelter", "school": "school", "college": "college", "community_centre": "community_hall",
                      "community_hall": "community_hall", "townhall": "community_hall"}
LEVEL_HEIGHT_M = 3.2
EVENTS = {  # 72 h windows: event day -1 .. +1 (UTC)
    "2015-12-01": "Chennai floods, Dec 2015",
    "2021-11-11": "Chennai heavy rain, Nov 2021",
    "2023-12-03": "Cyclone Michaung, Dec 2023",
}


def sha(path: Path) -> str:
    d = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            d.update(block)
    return d.hexdigest()


def estimate_height(kind: str, area_m2: float) -> float:
    """Documented fallback when OSM gives neither height nor building:levels."""
    k = (kind or "yes").lower()
    if k in {"apartments", "residential", "dormitory", "hotel"}:
        return 12.0
    if k in {"house", "detached", "semidetached_house", "terrace", "hut", "shed", "roof", "garage", "kiosk"}:
        return 3.5 if k in {"hut", "shed", "roof", "garage", "kiosk"} else 6.4
    if k in {"commercial", "office", "retail", "school", "college", "university", "hospital", "public", "civic", "government"}:
        return 9.6
    if k in {"industrial", "warehouse", "factory", "train_station"}:
        return 8.0
    if area_m2 < 60:
        return 3.5
    if area_m2 < 150:
        return 6.4
    if area_m2 < 600:
        return 9.6
    if area_m2 < 2500:
        return 12.8
    return 16.0


# ----------------------------------------------------------------------------------------------- 30 m base
def load_base() -> dict:
    with rasterio.open(DEM) as ds:
        dem = ds.read(1).astype(np.float64)
        transform = ds.transform
        valid = np.isfinite(dem) & (dem != ds.nodata)
    with rasterio.open(WORLDCOVER) as ds:
        wc = ds.read(1)
    with rasterio.open(WORLDPOP) as ds:
        pop = ds.read(1).astype(np.float64)
        pop = np.where((pop == ds.nodata) | ~np.isfinite(pop) | (pop < 0), np.nan, pop)
    ct = pq.read_table(CELLS, columns=["row", "col"])
    cma = np.zeros(dem.shape, bool)
    cma[ct["row"].to_numpy(), ct["col"].to_numpy()] = True
    water = (wc == 80) | ~valid
    lab, _ = ndimage.label(water)
    edge = np.unique(np.r_[lab[:, -1], lab[0, :], lab[-1, :]])
    sea = np.isin(lab, edge[edge > 0]) & ~cma
    return {"dem": np.where(valid, dem, np.nan), "valid": valid, "wc": wc, "pop": pop, "cma": cma, "sea": sea, "transform": transform}


def load_buildings(base) -> pd.DataFrame:
    b = pyogrio.read_dataframe(BUILDINGS, columns=["osmid", "building", "levels", "area_m2"])
    cent = shapely.centroid(b.geometry.array)
    xy = shapely.get_coordinates(cent)
    lon, lat = warp_transform(CRS, "EPSG:4326", xy[:, 0].tolist(), xy[:, 1].tolist())
    tags = _pbf_height_tags()
    height_tag = b.osmid.map(tags["height"]) if len(tags) else pd.Series(np.nan, index=b.index)
    levels = pd.to_numeric(b.levels, errors="coerce")
    levels = levels.where(levels.notna(), b.osmid.map(tags["levels"]) if len(tags) else np.nan)
    h = pd.to_numeric(height_tag, errors="coerce")
    source = np.where(h.notna() & (h > 0), "osm_height", np.where(levels.notna() & (levels > 0), "osm_levels", "estimated"))
    est = np.array([estimate_height(k, a) for k, a in zip(b.building.fillna("yes"), b.area_m2.fillna(0))])
    height = np.where(source == "osm_height", h, np.where(source == "osm_levels", levels * LEVEL_HEIGHT_M, est))
    out = pd.DataFrame({"osmid": b.osmid.astype(np.int64), "kind": b.building.fillna("yes").astype(str), "area_m2": b.area_m2.astype(float),
                        "x": xy[:, 0], "y": xy[:, 1], "lon": lon, "lat": lat, "height_m": height.astype(float), "height_source": source})
    out.attrs["geometry"] = b.geometry
    return out


def _pbf_height_tags() -> pd.DataFrame:
    cache = OUT / "shared" / "_osm_building_height_tags.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    df = pyogrio.read_dataframe(PBF, layer="multipolygons", columns=["osm_id", "osm_way_id", "building", "other_tags"],
                                where="building IS NOT NULL", bbox=(80.0, 12.84, 80.36, 13.30), read_geometry=False)
    tags = df.other_tags.fillna("")
    ident = pd.to_numeric(df.osm_way_id, errors="coerce").fillna(pd.to_numeric(df.osm_id, errors="coerce"))
    res = pd.DataFrame({"osmid": ident.astype("Int64"),
                        "height": pd.to_numeric(tags.str.extract(r'"height"=>"([0-9.]+)')[0], errors="coerce"),
                        "levels": pd.to_numeric(tags.str.extract(r'"building:levels"=>"([0-9.]+)')[0], errors="coerce")})
    res = res.dropna(subset=["osmid"]).drop_duplicates("osmid").set_index("osmid")
    res = res[res.height.notna() | res.levels.notna()]
    cache.parent.mkdir(parents=True, exist_ok=True)
    res.to_parquet(cache)
    return res


def load_wards() -> gpd.GeoDataFrame:
    w = gpd.read_file(WARDS)
    w["ward_id"] = w.Ward_No.astype(int)
    w = w[(w.ward_id >= 1) & (w.ward_id <= 200)]  # the source also holds a ward-0 cantonment polygon (not a GCC ward)
    w = w.dissolve(by="ward_id", aggfunc={"Zone_Name": "first", "Zone_No": "first"}).reset_index()
    w["ward_name"] = "Ward " + w.ward_id.astype(str)
    w["zone"] = w.Zone_No.astype(str) + " " + w.Zone_Name.astype(str).str.title()
    return w[["ward_id", "ward_name", "zone", "geometry"]].sort_values("ward_id").reset_index(drop=True)


# ----------------------------------------------------------------------------------------------- grids
def coarse(a: np.ndarray, f: int, how: str = "mean", valid: np.ndarray | None = None) -> np.ndarray:
    ny, nx = a.shape
    cy, cx = -(-ny // f), -(-nx // f)
    pad = ((0, cy * f - ny), (0, cx * f - nx))
    v = np.isfinite(a) if valid is None else valid
    ap = np.pad(np.where(v, a, 0), pad).reshape(cy, f, cx, f).astype(np.float64)
    vp = np.pad(v, pad).reshape(cy, f, cx, f)
    s = ap.sum(axis=(1, 3))
    c = vp.sum(axis=(1, 3))
    if how == "sum":
        return np.where(c > 0, s, np.nan)
    if how == "min":
        mn = np.where(vp, ap, np.inf).min(axis=(1, 3))
        return np.where(c > 0, mn, np.nan)
    return np.divide(s, c, out=np.full(s.shape, np.nan), where=c > 0)


def build_grid(base, buildings, wards_raster, f: int, window=None, focus: bool = False) -> tuple[dict, dict]:
    r0, r1, c0, c1 = window or (0, base["dem"].shape[0], 0, base["dem"].shape[1])
    sl = (slice(r0, r1), slice(c0, c1))
    dem, valid, wc = base["dem"][sl], base["valid"][sl], base["wc"][sl]
    cma, sea, pop = base["cma"][sl], base["sea"][sl], base["pop"][sl]
    one = np.ones_like(valid)
    z = coarse(dem, f, "mean", valid)
    cmaf = coarse(cma.astype(float), f, "mean", one)
    seaf = coarse(sea.astype(float), f, "mean", one)
    mann30 = np.full(wc.shape, .06)
    inf30 = np.full(wc.shape, .8)
    for code, v in MANNING.items():
        mann30[wc == code] = v
    for code, v in INFIL_MM_H.items():
        inf30[wc == code] = v
    mann = coarse(mann30, f, "mean", one)
    infil = coarse(inf30, f, "mean", one)
    population = coarse(pop, f, "sum")
    t30 = base["transform"]
    origin_x = t30.c + c0 * t30.a
    origin_y = t30.f + r0 * t30.e
    cell = 30.0 * f
    transform = Affine(cell, 0, origin_x, 0, -cell, origin_y)
    shape = z.shape
    # building coverage -> porosity
    col = np.floor((buildings.x.to_numpy() - origin_x) / cell).astype(np.int64)
    row = np.floor((origin_y - buildings.y.to_numpy()) / cell).astype(np.int64)
    inside = (row >= 0) & (row < shape[0]) & (col >= 0) & (col < shape[1])
    bcell = np.where(inside, row * shape[1] + col, -1)
    barea = np.bincount(bcell[inside], weights=buildings.area_m2.to_numpy()[inside], minlength=shape[0] * shape[1]).reshape(shape)
    porosity = np.clip(1.0 - barea / (cell * cell), 0.3, 1.0)
    if focus:
        active = np.isfinite(z) & (seaf < 0.5)
        ring = np.zeros(shape, bool)
        ring[0, :] = ring[-1, :] = ring[:, 0] = ring[:, -1] = True
        boundary = (ring & active) | ((seaf >= 0.5) & ndimage.binary_dilation(active, iterations=2))
        active &= ~boundary
    else:
        active = (cmaf >= 0.5) & np.isfinite(z)
        boundary = (seaf >= 0.5) & ~active & ndimage.binary_dilation(active, iterations=3)
    z = np.where(np.isfinite(z), z, 0.0)
    sea_b = boundary & (seaf >= 0.5)
    z[sea_b] = np.minimum(z[sea_b], -1.0)
    wr = wards_raster[sl]
    rr = np.minimum(np.arange(shape[0]) * f + f // 2, wr.shape[0] - 1)
    cc = np.minimum(np.arange(shape[1]) * f + f // 2, wr.shape[1] - 1)
    ward_id = wr[np.ix_(rr, cc)].astype(np.int16)
    landcover = wc[np.ix_(rr, cc)].astype(np.int16)
    rows, cols = np.indices(shape)
    lon, lat = warp_transform(CRS, "EPSG:4326", (origin_x + (cols.ravel() + .5) * cell).tolist(), (origin_y - (rows.ravel() + .5) * cell).tolist())
    bx = [origin_x, origin_x + shape[1] * cell]
    by = [origin_y - shape[0] * cell, origin_y]
    blon, blat = warp_transform(CRS, "EPSG:4326", [bx[0], bx[1], bx[1], bx[0]], [by[1], by[1], by[0], by[0]])
    arrays = {
        "z": z.astype(np.float32), "active": active, "boundary": boundary, "drain": boundary,
        "mann": mann.astype(np.float32), "porosity": porosity.astype(np.float32), "infiltration_mm_h": infil.astype(np.float32),
        "landcover": landcover, "population": np.where(active, population, np.nan).astype(np.float32),
        "ward_id": np.where(active, ward_id, 0).astype(np.int16),
        "cell_lon": np.asarray(lon, np.float32).reshape(shape), "cell_lat": np.asarray(lat, np.float32).reshape(shape),
        "building_cell": np.where(inside & active.ravel()[np.clip(bcell, 0, None)], bcell, -1).astype(np.int32),
    }
    grid = {"crs": CRS, "origin_x_m": float(origin_x), "origin_y_m": float(origin_y), "cell_size_m": int(cell),
            "rows": int(shape[0]), "cols": int(shape[1]),
            "bbox_wgs84": [float(min(blon)), float(min(blat)), float(max(blon)), float(max(blat))]}
    return arrays, grid


def cell_index(x, y, grid, active) -> np.ndarray:
    col = np.floor((np.asarray(x) - grid["origin_x_m"]) / grid["cell_size_m"]).astype(np.int64)
    row = np.floor((grid["origin_y_m"] - np.asarray(y)) / grid["cell_size_m"]).astype(np.int64)
    ok = (row >= 0) & (row < grid["rows"]) & (col >= 0) & (col < grid["cols"])
    idx = np.where(ok, row * grid["cols"] + col, -1)
    good = idx >= 0
    idx[good] = np.where(active.ravel()[idx[good]], idx[good], -1)
    return idx.astype(np.int32)


def inflow_cells(rivers: dict, grid: dict, active: np.ndarray, z: np.ndarray) -> dict:
    out = {}
    for name, spec in RESERVOIRS.items():
        line = rivers.get(spec["river"])
        if line is None:
            continue
        pts = shapely.get_coordinates(shapely.segmentize(line, grid["cell_size_m"] / 2))
        idx = cell_index(pts[:, 0], pts[:, 1], grid, active)
        keep = idx >= 0
        if not keep.any():
            out[name] = None
            continue
        rx, ry = warp_transform("EPSG:4326", CRS, [spec["lonlat"][0]], [spec["lonlat"][1]])
        d = np.hypot(pts[keep, 0] - rx[0], pts[keep, 1] - ry[0])
        k = int(np.flatnonzero(keep)[np.argmin(d)])
        cid = int(idx[k])
        r, c = divmod(cid, grid["cols"])
        lon, lat = warp_transform(CRS, "EPSG:4326", [pts[k, 0]], [pts[k, 1]])
        out[name] = {"river": spec["river"], "row": r, "col": c, "lon": lon[0], "lat": lat[0], "bed_elevation_m": float(z[r, c]),
                     "rule": "river cell nearest the reservoir, inside the active domain"}
    return out


# ----------------------------------------------------------------------------------------------- shared assets
def shared_assets(base, buildings, wards) -> dict:
    sh = OUT / "shared"
    sh.mkdir(parents=True, exist_ok=True)
    wards_ll = wards.to_crs("EPSG:4326")
    wards_ll.to_file(sh / "wards.geojson", driver="GeoJSON")
    w32 = wards.to_crs(CRS)
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(buildings.x, buildings.y), crs=CRS)
    joined = gpd.sjoin(pts, w32[["ward_id", "geometry"]], how="left", predicate="within")
    joined = joined[~joined.index.duplicated()]
    bward = joined.ward_id.reindex(range(len(buildings))).fillna(0).astype(np.int16).to_numpy()
    geom = buildings.attrs["geometry"].to_crs("EPSG:4326")
    ext = shapely.get_exterior_ring(shapely.get_geometry(geom.array, 0))
    coords, ring_idx = shapely.get_coordinates(ext, return_index=True)
    offsets = np.r_[0, np.cumsum(np.bincount(ring_idx, minlength=len(buildings)))].astype(np.int64)
    src_code = {"osm_height": 0, "osm_levels": 1, "estimated": 2}
    np.savez_compressed(sh / "buildings.npz", osmid=buildings.osmid.to_numpy(np.int64), x=buildings.x.to_numpy(), y=buildings.y.to_numpy(),
                        lon=buildings.lon.to_numpy(), lat=buildings.lat.to_numpy(), height_m=buildings.height_m.to_numpy(np.float32),
                        height_source=buildings.height_source.map(src_code).to_numpy(np.int8), area_m2=buildings.area_m2.to_numpy(np.float32),
                        ward_id=bward, kind=buildings.kind.to_numpy().astype("U24"),
                        ring_offsets=offsets, ring_lonlat=coords.astype(np.float32))
    roads = pyogrio.read_dataframe(OSM, layer="road_segments", columns=["osmid", "highway", "name", "bridge", "tunnel", "length_m"])
    mid = shapely.get_coordinates(shapely.line_interpolate_point(roads.geometry.array, 0.5, normalized=True))
    rll = roads.to_crs("EPSG:4326")
    rc, ridx = shapely.get_coordinates(rll.geometry.array, return_index=True)
    roff = np.r_[0, np.cumsum(np.bincount(ridx, minlength=len(roads)))].astype(np.int64)
    structure = roads.bridge.fillna("").astype(str).str.lower().isin(["yes", "viaduct", "true", "1"]) | roads.tunnel.fillna("").astype(str).str.lower().isin(["yes", "true", "1", "culvert", "building_passage"])
    rward = gpd.sjoin(gpd.GeoDataFrame(geometry=gpd.points_from_xy(mid[:, 0], mid[:, 1]), crs=CRS), w32[["ward_id", "geometry"]], how="left", predicate="within")
    rward = rward[~rward.index.duplicated()].ward_id.reindex(range(len(roads))).fillna(0).astype(np.int16).to_numpy()
    np.savez_compressed(sh / "roads.npz", osmid=pd.to_numeric(roads.osmid, errors="coerce").fillna(-1).to_numpy(np.int64),
                        highway=roads.highway.fillna("unknown").astype(str).to_numpy().astype("U24"),
                        name=roads.name.fillna("").astype(str).to_numpy().astype("U60"),
                        structure=structure.to_numpy(), length_m=pd.to_numeric(roads.length_m, errors="coerce").fillna(0).to_numpy(np.float32),
                        mid_x=mid[:, 0], mid_y=mid[:, 1], ward_id=rward, line_offsets=roff, line_lonlat=rc.astype(np.float32))
    fac = pyogrio.read_dataframe(OSM, layer="facilities", columns=["osmid", "category", "name"])
    fac = fac[fac.category.isin(SHELTER_CATEGORIES)].reset_index(drop=True)
    fxy = shapely.get_coordinates(fac.geometry.array)
    flon, flat = warp_transform(CRS, "EPSG:4326", fxy[:, 0].tolist(), fxy[:, 1].tolist())
    cat = fac.category.map(SHELTER_CATEGORIES)
    sward = gpd.sjoin(gpd.GeoDataFrame(geometry=gpd.points_from_xy(fxy[:, 0], fxy[:, 1]), crs=CRS), w32[["ward_id", "geometry"]], how="left", predicate="within")
    sward = sward[~sward.index.duplicated()].ward_id.reindex(range(len(fac))).fillna(0).astype(np.int16).to_numpy()
    np.savez_compressed(sh / "shelters.npz", shelter_id=np.array([f"osm:{i}" for i in fac.osmid]).astype("U32"),
                        name=fac.name.fillna("").astype(str).to_numpy().astype("U80"), category=cat.to_numpy().astype("U16"),
                        capacity_people=cat.map(SHELTER_CAPACITY).to_numpy(np.int32), x=fxy[:, 0], y=fxy[:, 1],
                        lon=np.asarray(flon), lat=np.asarray(flat), ward_id=sward)
    focus = []
    for name, (lon, lat) in FOCUS_CENTRES.items():
        cx, cy = warp_transform("EPSG:4326", CRS, [lon], [lat])
        half = FOCUS_SIZE_M / 2
        box = shapely.box(cx[0] - half, cy[0] - half, cx[0] + half, cy[0] + half)
        focus.append({"focus_area": name, "geometry": box})
    gpd.GeoDataFrame(focus, crs=CRS).to_crs("EPSG:4326").to_file(sh / "focus_areas.geojson", driver="GeoJSON")
    events = []
    for key, label in EVENTS.items():
        end = (pd.Timestamp(key) + pd.Timedelta(days=1)).date().isoformat()
        rain = a06.rainfall_72h(end)
        start = pd.Timestamp(key) - pd.Timedelta(days=1)
        events.append({"event_key": key, "label": label, "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                       "end_utc": (start + pd.Timedelta(hours=72)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                       "rainfall_source": "GPM IMERG daily CMA mean, ERA5 hourly shape (A06 method)", "source_mode": "REPLAY",
                       "interval_minutes": 60, "values_mm": [round(float(v), 4) for v in rain], "total_mm": float(rain.sum())})
    (sh / "events.json").write_text(json.dumps({"events": events}, indent=1), encoding="utf-8")
    return {"building_ward": bward, "roads_mid": mid, "roads_structure": structure.to_numpy(), "shelters_xy": fxy}


def road_topology() -> None:
    """shared/road_topology.npz: OSM node ids per road segment (shared/roads.npz order) and node coordinates."""
    roads = pyogrio.read_dataframe(OSM, layer="road_segments", columns=["node_a", "node_b"], read_geometry=False)
    na = pd.to_numeric(roads.node_a, errors="coerce").fillna(-1).to_numpy(np.int64)
    nb = pd.to_numeric(roads.node_b, errors="coerce").fillna(-1).to_numpy(np.int64)
    nodes = pyogrio.read_dataframe(OSM, layer="road_nodes", columns=["osmid"])
    nid = pd.to_numeric(nodes.osmid, errors="coerce").fillna(-1).to_numpy(np.int64)
    xy = shapely.get_coordinates(nodes.geometry.array)
    order = np.argsort(nid)
    np.savez_compressed(OUT / "shared/road_topology.npz", node_a=na, node_b=nb, node_id=nid[order], node_x=xy[order, 0], node_y=xy[order, 1])


def river_lines() -> dict:
    ww = pyogrio.read_dataframe(OSM, layer="waterways", columns=["osmid"])
    ww["osmid"] = pd.to_numeric(ww.osmid, errors="coerce")
    out = {}
    for name, ids in RIVER_WAYS.items():
        sel = ww[ww.osmid.isin(ids)]
        if len(sel):
            out[name] = shapely.line_merge(shapely.union_all(sel.geometry.to_crs(CRS).array))
    return out


def write_grid(name: str, arrays: dict, grid: dict, extra_meta: dict, shared: dict, rivers: dict) -> dict:
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    act = arrays["active"]
    arrays["road_cell"] = cell_index(shared["roads_mid"][:, 0], shared["roads_mid"][:, 1], grid, act)
    arrays["shelter_cell"] = cell_index(shared["shelters_xy"][:, 0], shared["shelters_xy"][:, 1], grid, act)
    arc = pq.read_table(ARCS, columns=["arc_index", "edge_feature_index"]).to_pandas().sort_values("arc_index")
    efi = arc.edge_feature_index.to_numpy()
    arrays["arc_cell"] = np.where((efi >= 0) & (efi < len(arrays["road_cell"])), arrays["road_cell"][np.clip(efi, 0, len(arrays["road_cell"]) - 1)], -1).astype(np.int32)
    road_len = np.zeros(act.size)
    rcell = arrays["road_cell"]
    rl = np.load(OUT / "shared/roads.npz")["length_m"]
    ok = rcell >= 0
    np.add.at(road_len, rcell[ok], rl[ok])
    arrays["road_length_m"] = road_len.reshape(act.shape).astype(np.float32)
    np.savez_compressed(d / "static.npz", **arrays)
    meta = {"schema": "twinguard.a25_static.v1", "static_assets_version": "a25_static_v1", "name": name, "grid": grid,
            "active_cells": int(act.sum()), "boundary_cells": int(arrays["boundary"].sum()),
            "inflow_cells": inflow_cells(rivers, grid, act, arrays["z"]), **extra_meta,
            "arrays": {k: [list(v.shape), str(v.dtype)] for k, v in arrays.items()},
            "notes": {"boundary": "fixed-stage cells (sea; focus grids also the outer ring, nested to the citywide run)",
                      "drain": "alias of boundary for A06-layout readers", "building_cell": "row-major cell of each building centroid in shared/buildings.npz; -1 outside",
                      "road_cell": "cell of each road_segments midpoint (shared/roads.npz order)", "arc_cell": "cell per directed_arcs.parquet arc_index (via edge_feature_index)",
                      "ward_id": "GCC ward (1-200) at the cell centre; 0 = outside GCC"},
            "bundle_sha256": None}
    meta["bundle_sha256"] = sha(d / "static.npz")
    (d / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return meta


def build(resolutions=(120,), focus=True) -> dict:
    t0 = time.perf_counter()
    base = load_base()
    buildings = load_buildings(base)
    wards = load_wards()
    w32 = wards.to_crs(CRS)
    wards_raster = rasterize([(g, int(i)) for g, i in zip(w32.geometry, w32.ward_id)], out_shape=base["dem"].shape, transform=base["transform"], fill=0, dtype="int16")
    shared = shared_assets(base, buildings, wards)
    road_topology()
    rivers = river_lines()
    manifest = {"version": "a25_static_v1", "grids": {}, "sources": {
        "dem": {"path": str(DEM.relative_to(ROOT)), "sha256": sha(DEM), "note": "Copernicus GLO-30 (data/raw/dem) reprojected/conditioned"},
        "wards": {"path": str(WARDS.relative_to(ROOT)), "sha256": sha(WARDS), "source": "https://github.com/datameet/Municipal_Spatial_Data/blob/master/Chennai/Wards.geojson",
                  "licence": "CC BY-SA 2.5 India (Transparent Chennai via DataMeet)", "commit": "313d8feb41fbda4a6269a2567b198016db17026f"},
        "worldpop": {"path": str(WORLDPOP.relative_to(ROOT)), "sha256": sha(WORLDPOP)},
        "worldcover": {"path": str(WORLDCOVER.relative_to(ROOT)), "sha256": sha(WORLDCOVER)},
        "buildings": {"path": str(BUILDINGS.relative_to(ROOT)), "count": int(len(buildings)),
                      "height_source_counts": buildings.height_source.value_counts().to_dict(),
                      "height_rule": "osm_height = OSM height tag (m); osm_levels = building:levels x 3.2 m; estimated = type/area rule in build_static.estimate_height"},
        "osm_pbf_tags": str(PBF.relative_to(ROOT))}}
    for res in resolutions:
        f = res // 30
        arrays, grid = build_grid(base, buildings, wards_raster, f)
        manifest["grids"][f"citywide_{res}m"] = write_grid(f"citywide_{res}m", arrays, grid, {"kind": "citywide"}, shared, rivers)
    if focus:
        t = base["transform"]
        for name, (lon, lat) in FOCUS_CENTRES.items():
            cx, cy = warp_transform("EPSG:4326", CRS, [lon], [lat])
            half = FOCUS_SIZE_M / 2
            c0 = int((cx[0] - half - t.c) // 30)
            r0 = int((t.f - (cy[0] + half)) // 30)
            n = FOCUS_SIZE_M // 30
            arrays, grid = build_grid(base, buildings, wards_raster, 1, (r0, r0 + n, c0, c0 + n), focus=True)
            manifest["grids"][f"focus_30m_{name}"] = write_grid(f"focus_30m_{name}", arrays, grid, {"kind": "focus", "focus_area": name}, shared, rivers)
    manifest["build_seconds"] = round(time.perf_counter() - t0, 1)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str), encoding="utf-8")
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--resolutions", type=int, nargs="+", default=[120])
    ap.add_argument("--no-focus", action="store_true")
    a = ap.parse_args()
    m = build(tuple(a.resolutions), not a.no_focus)
    print(json.dumps({k: {"grid": v["grid"], "active": v["active_cells"]} for k, v in m["grids"].items()}, indent=1))
    print("height sources", m["sources"]["buildings"]["height_source_counts"], "seconds", m["build_seconds"])


if __name__ == "__main__":
    main()
