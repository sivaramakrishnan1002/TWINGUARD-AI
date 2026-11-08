"""Build the compact C4 v3 product static bundle from saved, git-ignored project data (developer tool).

Run once with the project virtualenv (needs pandas, pyarrow, shapely, pyproj):

    .venv/Scripts/python.exe services/ai-service/app/v3/build_static.py

Writes ``data/features/v3/product_static_v1/`` (roads.npz, buildings.npz, shelters.json, manifest.json) and
``services/ai-service/app/v3/events.json`` (small saved event forcing). The AI service only needs NumPy at runtime.
Every layer is STATIC_REFERENCE (OSM) or REPLAY (archived IMERG/ERA5); nothing is observed flood data.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "data/features/v3/product_static_v1"
EVENTS_OUT = Path(__file__).with_name("events.json")
ROAD_GPKG = ROOT / "data/features/roads/chennai_road_graph.gpkg"
BUILDING_GPKG = ROOT / "data/features/buildings/chennai_building_footprints.gpkg"
FACILITY_GPKG = ROOT / "data/features/facilities/chennai_facilities.gpkg"
A08 = ROOT / "data/features/routing/time_dependent_batch2"
SHELTERS = ROOT / "data/features/decision/shelters/batch2_v3/candidate_facilities.parquet"
LIVE_STATIC = ROOT / "data/features/live/a06_live_static_v1"
EVENT_DIR = ROOT / "data/features/events"

STRUCTURES = ["ordinary", "tunnel_underpass_proxy", "bridge", "bridge_and_tunnel", "unassessed"]
# Saved rainfall events (peak UTC day). Windows cover the three days before the peak plus the peak day and one after.
EVENTS = [
    ("2015-11-08", "Nov 2015 early-season heavy rain"),
    ("2015-11-15", "Nov 2015 Chennai floods (15 Nov)"),
    ("2015-12-01", "Dec 2015 Chennai floods (1 Dec)"),
    ("2021-11-10", "Nov 2021 Chennai heavy rain"),
    ("2023-12-04", "Dec 2023 Cyclone Michaung"),
]


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _wkb(blob: bytes) -> bytes:
    """Strip the GeoPackage binary header and return standard WKB."""
    flags = blob[3]
    envelope = (flags >> 1) & 0x07
    size = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[envelope]
    return blob[8 + size:]


def _transformer():
    from pyproj import Transformer
    return Transformer.from_crs("EPSG:32644", "EPSG:4326", always_xy=True)


def build_roads(tf) -> dict:
    import pandas as pd
    import shapely

    segments = pd.read_parquet(A08 / "static_segments.parquet")
    arcs = pd.read_parquet(A08 / "directed_arcs.parquet")
    con = sqlite3.connect(ROAD_GPKG)
    node_rows = con.execute("select osmid, geom from road_nodes order by fid").fetchall()
    node_osm = np.array([r[0] for r in node_rows], dtype=np.int64)
    pts = shapely.from_wkb([_wkb(r[1]) for r in node_rows])
    nx, ny = shapely.get_x(pts), shapely.get_y(pts)
    nlon, nlat = tf.transform(nx, ny)
    order = np.argsort(node_osm)
    lookup = lambda ids: order[np.searchsorted(node_osm[order], ids)]  # noqa: E731

    seg_rows = con.execute("select fid, geom from road_segments order by fid").fetchall()
    if len(seg_rows) != len(segments) or seg_rows[0][0] != 1:
        raise RuntimeError("road_segments fid order does not match A08 static_segments")
    lines = shapely.from_wkb([_wkb(r[1]) for r in seg_rows])
    coords, index = shapely.get_coordinates(lines, return_index=True)
    lon, lat = tf.transform(coords[:, 0], coords[:, 1])
    offsets = np.concatenate([[0], np.cumsum(np.bincount(index, minlength=len(seg_rows)))]).astype(np.int64)

    highways = sorted(set(segments.highway.astype(str)) | set(arcs.highway.astype(str)))
    hw = {h: i for i, h in enumerate(highways)}
    seg_mid = shapely.line_interpolate_point(lines, 0.5, normalized=True)
    mlon, mlat = tf.transform(shapely.get_x(seg_mid), shapely.get_y(seg_mid))
    return {
        "node_lon": nlon.astype(np.float64), "node_lat": nlat.astype(np.float64),
        "node_x": nx.astype(np.float64), "node_y": ny.astype(np.float64),
        "seg_cell": segments.grid_cell_id.to_numpy(np.int32),
        "seg_structure": np.array([STRUCTURES.index(s) for s in segments.structure_class], np.uint8),
        "seg_highway": np.array([hw[str(h)] for h in segments.highway], np.uint8),
        "seg_length_m": segments.length_m.to_numpy(np.float32),
        "seg_mid_lon": mlon.astype(np.float32), "seg_mid_lat": mlat.astype(np.float32),
        "seg_coord_offsets": offsets, "seg_coord_lon": lon.astype(np.float32), "seg_coord_lat": lat.astype(np.float32),
        "arc_from": lookup(arcs.from_node.to_numpy(np.int64)).astype(np.int32),
        "arc_to": lookup(arcs.to_node.to_numpy(np.int64)).astype(np.int32),
        "arc_segment": arcs.edge_feature_index.to_numpy(np.int32),
        "arc_length_m": arcs.length_m.to_numpy(np.float32),
        "arc_speed_kmh": arcs.base_speed_kmh.to_numpy(np.float32),
        "highway_names": np.array(highways),
        "structure_names": np.array(STRUCTURES),
    }


def build_buildings(tf, cell_of) -> dict:
    import shapely

    con = sqlite3.connect(BUILDING_GPKG)
    rows = con.execute("select fid, osmid, levels, geom from building_footprints order by fid").fetchall()
    geoms = shapely.from_wkb([_wkb(r[3]) for r in rows])
    rings = shapely.get_exterior_ring(shapely.get_geometry(geoms, 0))
    centroid = shapely.centroid(geoms)
    cx, cy = shapely.get_x(centroid), shapely.get_y(centroid)
    clon, clat = tf.transform(cx, cy)
    coords, index = shapely.get_coordinates(rings, return_index=True)
    lon, lat = tf.transform(coords[:, 0], coords[:, 1])
    offsets = np.concatenate([[0], np.cumsum(np.bincount(index, minlength=len(rows)))]).astype(np.int64)
    levels = np.array([float(r[2]) if r[2] not in (None, "") and str(r[2]).replace(".", "", 1).isdigit() else np.nan for r in rows])
    return {
        "fid": np.array([r[0] for r in rows], np.int64), "osmid": np.array([r[1] or 0 for r in rows], np.int64),
        "lon": clon.astype(np.float64), "lat": clat.astype(np.float64), "cell": cell_of(cx, cy),
        "levels": levels.astype(np.float32),
        "ring_offsets": offsets, "ring_lon": lon.astype(np.float32), "ring_lat": lat.astype(np.float32),
    }


def build_shelters(tf, cell_of) -> list[dict]:
    import pandas as pd
    import shapely

    cand = pd.read_parquet(SHELTERS)
    con = sqlite3.connect(FACILITY_GPKG)
    geo = {}
    for osmid, blob in con.execute("select osmid, geom from facilities"):
        geo.setdefault(int(osmid), blob)
    out = []
    for row in cand.itertuples():
        blob = geo.get(int(row.osmid))
        if blob is None:
            continue
        point = shapely.centroid(shapely.from_wkb(_wkb(blob)))
        x, y = shapely.get_x(point), shapely.get_y(point)
        lon, lat = tf.transform(x, y)
        out.append({"shelter_id": str(row.candidate_id), "name": str(row.name or "") or f"Unnamed {row.category}",
                    "category": str(row.category), "lon": round(float(lon), 6), "lat": round(float(lat), 6),
                    "cell": int(cell_of(np.array([x]), np.array([y]))[0]),
                    "capacity_people": int(row.assumed_capacity_people), "capacity_source": "assumed"})
    return out


def build_events() -> list[dict]:
    import pandas as pd

    events = []
    for key, label in EVENTS:
        year = key[:4]
        frame = pd.read_parquet(EVENT_DIR / f"aligned_{year}.parquet")
        frame = frame.set_index(frame.timestamp_utc.dt.floor("h")).sort_index()
        era5 = frame[[c for c in frame.columns if c.startswith("era5_precipitation_era5_")]].mean(axis=1)
        era5 = era5.dropna().groupby(level=0).mean()
        imerg = frame["imerg_cma_mean_mm_day"].dropna().groupby(level=0).first()
        peak = pd.Timestamp(key, tz="UTC")
        start, end = peak - timedelta(days=3), peak + timedelta(days=2)
        hourly = []
        day = start
        while day < end:
            hours = pd.date_range(day, periods=24, freq="h")
            daily = imerg[(imerg.index >= day) & (imerg.index < day + timedelta(days=1))]
            shape = era5.reindex(hours)
            if daily.empty or shape.isna().any():
                raise RuntimeError(f"event {key}: missing IMERG/ERA5 on {day.date()}")
            total = float(shape.sum())
            amount = float(daily.iloc[0])
            hourly.extend((shape / total * amount).tolist() if total > 0 else [amount / 24] * 24)
            day += timedelta(days=1)
        events.append({"event_key": key, "label": label, "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                       "end_utc": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                       "rainfall_source": "GPM IMERG daily CMA-mean total, distributed by the ERA5 hourly profile (archived)",
                       "source_mode": "REPLAY", "hourly_mm": [round(v, 3) for v in hourly]})
    return events


def main() -> int:
    meta = json.loads((LIVE_STATIC / "static_meta.json").read_text(encoding="utf-8"))
    a, b, c, d, e, f = meta["grid"]["transform"]
    rows, cols = meta["grid"]["rows"], meta["grid"]["cols"]

    def cell_of(x, y):
        col = np.floor((np.asarray(x) - c) / a).astype(np.int64)
        row = np.floor((np.asarray(y) - f) / e).astype(np.int64)
        ok = (row >= 0) & (row < rows) & (col >= 0) & (col < cols)
        return np.where(ok, row * cols + col, -1).astype(np.int32)

    EVENTS_OUT.write_text(json.dumps({"schema": "twinguard.v3_events.v1", "events": build_events()}, indent=1), encoding="utf-8")
    if "--events-only" in sys.argv:
        return 0
    tf = _transformer()
    OUT.mkdir(parents=True, exist_ok=True)
    print("roads...", flush=True)
    np.savez_compressed(OUT / "roads.npz", **build_roads(tf))
    print("buildings...", flush=True)
    np.savez_compressed(OUT / "buildings.npz", **build_buildings(tf, cell_of))
    print("shelters...", flush=True)
    (OUT / "shelters.json").write_text(json.dumps(build_shelters(tf, cell_of)), encoding="utf-8")
    manifest = {
        "schema": "twinguard.v3_product_static.v1",
        "grid": {"rows": rows, "cols": cols, "cell_size_m": meta["grid"]["cell_size_m"], "crs": meta["grid"]["crs"],
                 "transform": meta["grid"]["transform"]},
        "sources": {str(p.relative_to(ROOT)).replace("\\", "/"): _sha(p) for p in
                    (ROAD_GPKG, BUILDING_GPKG, FACILITY_GPKG, A08 / "static_segments.parquet", A08 / "directed_arcs.parquet", SHELTERS)},
        "files": {},
    }
    for name in ("roads.npz", "buildings.npz", "shelters.json"):
        manifest["files"][name] = _sha(OUT / name)
    manifest["version"] = hashlib.sha256(json.dumps(manifest["files"], sort_keys=True).encode()).hexdigest()[:16]
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(json.dumps(manifest["files"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
