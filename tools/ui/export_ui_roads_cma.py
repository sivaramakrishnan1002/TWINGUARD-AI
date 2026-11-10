"""Export the citywide major-road network for the B48 3D twin (neutral context layer).

Reads the project road graph (data/features/roads/chennai_road_graph.gpkg, read-only) and writes
frontend/src/ui/evidence/generated/roads_cma.json (git-ignored):

    {"classes": ["motorway", ...], "lines": [[class_index, lon0_e5, lat0_e5, dlon1, dlat1, ...], ...]}

Only motorway/trunk/primary/secondary/tertiary (+ links) inside the CMA boundary are kept; segments are
merged per class into polylines, simplified (~8 m) and delta-encoded at 1e-5 degrees (~1 m). Residential
streets and the per-run three-state colours come from GET /v3/simulations/{id}/roads for the current view.

Usage: .venv/Scripts/python.exe tools/ui/export_ui_roads_cma.py
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pyogrio
from shapely.ops import linemerge, unary_union

ROOT = Path(__file__).resolve().parents[2]
ROADS = ROOT / "data/features/roads/chennai_road_graph.gpkg"
BOUNDARY = ROOT / "data/raw/boundary/chennai_cma_boundary.geojson"
OUT = ROOT / "frontend/src/ui/evidence/generated/roads_cma.json"
CLASSES = ["motorway", "trunk", "primary", "secondary", "tertiary"]


def main() -> None:
    seg = pyogrio.read_dataframe(ROADS, layer="road_segments", columns=["highway"])
    seg["cls"] = seg["highway"].astype(str).str.replace("_link", "", regex=False)
    seg = seg[seg["cls"].isin(CLASSES)].to_crs("EPSG:4326")
    cma = gpd.read_file(BOUNDARY).to_crs("EPSG:4326").union_all()
    seg = seg[seg.intersects(cma)]
    lines: list[list[int]] = []
    for ci, cls in enumerate(CLASSES):
        geoms = seg.loc[seg["cls"] == cls, "geometry"]
        if geoms.empty:
            continue
        merged = linemerge(unary_union(list(geoms)))
        parts = getattr(merged, "geoms", [merged])
        for ln in parts:
            ln = ln.simplify(0.00008, preserve_topology=False)
            pts = [(round(x * 1e5), round(y * 1e5)) for x, y in ln.coords]
            if len(pts) < 2:
                continue
            row = [ci, pts[0][0], pts[0][1]]
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                row += [x1 - x0, y1 - y0]
            lines.append(row)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"classes": CLASSES, "source": "OSM road graph (data/features/roads)", "lines": lines}, separators=(",", ":")), encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {len(lines)} polylines, {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
