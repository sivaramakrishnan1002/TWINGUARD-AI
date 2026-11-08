"""Export static 3D-twin layers for the B48 UI from local project data (read-only).

Writes only to frontend/src/ui/evidence/generated/ (git-ignored):
  terrain_cma.json        GLO-30 cleaned DEM resampled to a WGS84 grid (int16 decimetres)
  wards.json              GCC 200-ward polygons (STATIC_REFERENCE), simplified
  shelters.json           A10 batch2_v3 candidate shelters with snapped-node locations
  waterways.json          OSM rivers and canals (drains omitted), simplified
  boundary.json           pre-2022 CMA study boundary (read-only source), simplified
  focus_<AREA>.json       per focus area: OSM building footprints (levels, height source,
                          UTM centroid for depth sampling) and OSM road segments (class,
                          bridge/tunnel flags, endpoints) for client-side fixture routing

Focus areas are approximate 5 km boxes around the named localities; they are display
extents only, not official boundaries. Nothing here is a model result.

Run from the repository root:
    .venv\\Scripts\\python.exe tools\\ui\\export_ui_twin3d.py
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import rasterio
from rasterio.warp import Resampling, reproject
from shapely.geometry import box, mapping

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "frontend/src/ui/evidence/generated"
DEM = ROOT / "data/processed/terrain_cleaned/cleaned_elevation_m.tif"
WARDS = ROOT / "data/features/wards/gcc_wards_v1/Wards.geojson"
BUILDINGS = ROOT / "data/features/buildings/chennai_building_footprints.gpkg"
ROADS = ROOT / "data/features/roads/chennai_road_graph.gpkg"
SHELTERS = ROOT / "data/features/decision/shelters/batch2_v3/candidate_facilities.parquet"
WATERWAYS = ROOT / "data/features/hydrology/chennai_waterways.gpkg"
BOUNDARY = ROOT / "data/raw/boundary/chennai_cma_boundary.geojson"

# Approximate locality centres (WGS84); boxes are +/- 2.5 km.
FOCUS = {
    "VELACHERY": (80.2209, 12.9815),
    "ADYAR": (80.2570, 13.0012),
    "T_NAGAR": (80.2340, 13.0418),
    "PORUR": (80.1570, 13.0350),
}
HALF_M = 2500
LEVEL_HEIGHT_M = 3.0
DEFAULT_LEVELS = 2  # estimated when OSM has no levels tag


def r(v: float, n: int = 5) -> float:
    return round(float(v), n)


def write(name: str, payload: object) -> None:
    target = OUT / name
    target.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"wrote {target.relative_to(ROOT)} ({target.stat().st_size:,} bytes)")


def export_terrain() -> None:
    west, south, east, north, step = 79.95, 12.78, 80.36, 13.30, 0.0012
    cols = int(round((east - west) / step))
    rows = int(round((north - south) / step))
    dst = np.full((rows, cols), -9999.0, dtype="float32")
    with rasterio.open(DEM) as src:
        reproject(
            source=rasterio.band(src, 1), destination=dst,
            dst_transform=rasterio.transform.from_origin(west, north, step, step), dst_crs="EPSG:4326",
            src_nodata=src.nodata, dst_nodata=-9999.0, resampling=Resampling.average,
        )
    dm = np.where(dst == -9999.0, -32768, np.clip(np.rint(dst * 10), -32000, 32000)).astype("<i2")
    write("terrain_cma.json", {
        "schema": "twinguard.ui.terrain.v1", "source": "GLO-30 cleaned DEM (surface model)", "source_mode": "STATIC_REFERENCE",
        "west": west, "north": north, "step_deg": step, "rows": rows, "cols": cols,
        "encoding": "base64 little-endian int16 decimetres; -32768 = NoData", "heights_dm": base64.b64encode(dm.tobytes()).decode(),
    })


def export_wards() -> gpd.GeoDataFrame:
    wards = gpd.read_file(WARDS).set_crs("EPSG:4326", allow_override=True)
    wards["geometry"] = wards.geometry.simplify(0.0002, preserve_topology=True)
    feats = []
    for _, w in wards.iterrows():
        if w.geometry is None or w.geometry.is_empty:
            continue
        feats.append({"type": "Feature", "geometry": json.loads(json.dumps(mapping(w.geometry), default=float)),
                      "properties": {"ward_id": int(w["Ward_No"]), "ward_name": f"Ward {int(w['Ward_No'])}", "zone": f"{w['Zone_No']} {str(w['Zone_Name']).title()}"}})
    for f in feats:
        f["geometry"]["coordinates"] = _round_coords(f["geometry"]["coordinates"])
    write("wards.json", {"type": "FeatureCollection", "layer": "wards", "source": "GCC 200-ward boundary (open data, project copy)",
                         "source_mode": "STATIC_REFERENCE", "attribution": "Greater Chennai Corporation open data", "next_cursor": None, "features": feats})
    return wards


def _round_coords(c):
    if isinstance(c, (list, tuple)) and c and isinstance(c[0], (int, float)):
        return [r(c[0]), r(c[1])]
    return [_round_coords(x) for x in c]


def export_shelters(wards: gpd.GeoDataFrame) -> None:
    cand = pd.read_parquet(SHELTERS)
    nodes = pyogrio.read_dataframe(ROADS, layer="road_nodes", columns=["osmid"])
    nodes = nodes[nodes["osmid"].isin(cand["snapped_node_osmid"])].to_crs("EPSG:4326")
    loc = {int(o): (g.x, g.y) for o, g in zip(nodes["osmid"], nodes.geometry)}
    pts = gpd.GeoDataFrame(cand, geometry=gpd.points_from_xy([loc.get(int(n), (np.nan, np.nan))[0] for n in cand["snapped_node_osmid"]],
                                                            [loc.get(int(n), (np.nan, np.nan))[1] for n in cand["snapped_node_osmid"]]), crs="EPSG:4326")
    pts = pts[pts.geometry.x.notna()]
    joined = gpd.sjoin(pts, wards[["Ward_No", "geometry"]], how="left", predicate="within")
    out = []
    for _, s in joined.iterrows():
        cat = s["category"] if s["category"] in ("shelter", "school", "college") else "shelter"
        out.append({"shelter_id": s["candidate_id"], "name": s["name"] if isinstance(s["name"], str) and s["name"] else f"Unnamed {cat}",
                    "category": cat, "location": {"lon": r(s.geometry.x), "lat": r(s.geometry.y)},
                    "ward_id": int(s["Ward_No"]) if pd.notna(s.get("Ward_No")) else None,
                    "capacity_people": int(s["assumed_capacity_people"]), "capacity_source": "assumed"})
    write("shelters.json", {"source": "A10 batch2_v3 candidate facilities (OSM); capacities assumed", "source_mode": "STATIC_REFERENCE", "shelters": out})


def export_focus(name: str, lon: float, lat: float) -> None:
    centre = gpd.GeoSeries(gpd.points_from_xy([lon], [lat]), crs="EPSG:4326").to_crs("EPSG:32644").iloc[0]
    bb = (centre.x - HALF_M, centre.y - HALF_M, centre.x + HALF_M, centre.y + HALF_M)
    b = pyogrio.read_dataframe(BUILDINGS, layer="building_footprints", bbox=bb)
    b = b[b.geometry.centroid.within(box(*bb))]
    cent = b.geometry.centroid
    b4 = b.to_crs("EPSG:4326")
    buildings = []
    for (osmid, levels, area), g, c in zip(b4[["osmid", "levels", "area_m2"]].itertuples(index=False), b4.geometry, cent):
        poly = g if g.geom_type == "Polygon" else max(g.geoms, key=lambda p: p.area)
        poly = poly.simplify(0.000008, preserve_topology=True)
        ring = list(poly.exterior.coords)[:-1]
        if len(ring) < 3:
            continue
        try:
            lv = int(float(levels)) if levels not in (None, "") and not pd.isna(levels) else None
        except (TypeError, ValueError):
            lv = None
        lv = lv if lv is not None and 0 < lv < 80 else None
        buildings.append([str(osmid), lv, int(round(c.x)), int(round(c.y)), [r(v, 6) for xy in ring for v in xy]])
    roads = pyogrio.read_dataframe(ROADS, layer="road_segments", bbox=bb,
                                   columns=["osmid", "node_a", "node_b", "highway", "name", "bridge", "tunnel", "length_m"])
    mids = roads.geometry.interpolate(0.5, normalized=True)
    r4 = roads.to_crs("EPSG:4326")
    segs = []
    for row, g, m in zip(r4.itertuples(index=False), r4.geometry, mids):
        g = g.simplify(0.00001)
        flags = (1 if str(row.bridge) not in ("None", "nan", "", "no") else 0) | (2 if str(row.tunnel) not in ("None", "nan", "", "no") else 0)
        segs.append([str(row.osmid), int(row.node_a), int(row.node_b), str(row.highway), float(round(row.length_m, 1)), flags,
                     int(round(m.x)), int(round(m.y)), [r(v) for xy in g.coords for v in xy]])
    write(f"focus_{name}.json", {"schema": "twinguard.ui.focus.v1", "focus_area": name, "centre": {"lon": lon, "lat": lat},
                                 "bbox_utm": [int(v) for v in bb], "source": "OpenStreetMap (ODbL) via project extracts",
                                 "source_mode": "STATIC_REFERENCE", "attribution": "© OpenStreetMap contributors (ODbL)",
                                 "height_rule": f"OSM levels × {LEVEL_HEIGHT_M} m; {DEFAULT_LEVELS} levels estimated when untagged",
                                 "buildings": buildings, "roads": segs})


def export_waterways() -> None:
    w = pyogrio.read_dataframe(WATERWAYS, layer="waterways")
    w = w[w["waterway"].isin(["river", "canal"])].to_crs("EPSG:4326")
    feats = []
    for row, g in zip(w.itertuples(index=False), w.geometry):
        if g is None or g.is_empty:
            continue
        g = g.simplify(0.00005)
        lines = [g] if g.geom_type == "LineString" else list(g.geoms)
        for line in lines:
            feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[r(x), r(y)] for x, y in line.coords]},
                          "properties": {"osmid": str(row.osmid), "waterway": row.waterway, "name": row.name if isinstance(row.name, str) else None}})
    write("waterways.json", {"type": "FeatureCollection", "source": "OpenStreetMap waterways (project extract)", "source_mode": "STATIC_REFERENCE",
                             "attribution": "© OpenStreetMap contributors (ODbL)", "features": feats})


def export_boundary() -> None:
    b = gpd.read_file(BOUNDARY).to_crs("EPSG:4326")
    geom = b.geometry.union_all() if hasattr(b.geometry, "union_all") else b.geometry.unary_union
    geom = geom.simplify(0.0004, preserve_topology=True)
    parts = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
    write("boundary.json", {"type": "FeatureCollection", "source": "Pre-2022 CMA boundary (project copy)", "source_mode": "STATIC_REFERENCE",
                            "features": [{"type": "Feature", "properties": {"part": i}, "geometry": {"type": "Polygon", "coordinates": [[[r(x), r(y)] for x, y in p.exterior.coords]]}} for i, p in enumerate(parts)]})


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    export_terrain()
    wards = export_wards()
    export_shelters(wards)
    export_waterways()
    export_boundary()
    for name, (lon, lat) in FOCUS.items():
        export_focus(name, lon, lat)


if __name__ == "__main__":
    main()
