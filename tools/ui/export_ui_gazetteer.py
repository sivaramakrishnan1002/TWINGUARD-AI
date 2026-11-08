"""Build the B48 locality gazetteer for search, the Areas list and map labels (read-only on project data).

Sources:
  data/raw/roads/southern-zone-latest.osm.pbf     OSM place nodes (suburb/neighbourhood/quarter/locality/town/village/city)
  data/raw/boundary/chennai_cma_boundary.geojson  pre-2022 CMA study boundary (clip)
  data/features/live/a25_static_v1/shared/wards.geojson  GCC 200 wards (Lane A A25), or the project GCC copy

Writes frontend/src/ui/evidence/generated/gazetteer.json (git-ignored):
  { places: [{ name, alt[], type, lon, lat, ward_id, zone, rank }], wards: [{ ward_id, name, zone, lon, lat, bbox }] }
rank orders labels for decluttering: 1 = town/city, 2 = suburb, 3 = quarter/neighbourhood, 4 = locality/village.

Run from the repository root:
    .venv\\Scripts\\python.exe tools\\ui\\export_ui_gazetteer.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import geopandas as gpd
import pyogrio

ROOT = Path(__file__).resolve().parents[2]
PBF = ROOT / "data/raw/roads/southern-zone-latest.osm.pbf"
BOUNDARY = ROOT / "data/raw/boundary/chennai_cma_boundary.geojson"
WARDS = [ROOT / "data/features/live/a25_static_v1/shared/wards.geojson", ROOT / "data/features/wards/gcc_wards_v1/Wards.geojson"]
OUT = ROOT / "frontend/src/ui/evidence/generated/gazetteer.json"
RANK = {"city": 1, "town": 1, "suburb": 2, "quarter": 3, "neighbourhood": 3, "locality": 4, "village": 4, "hamlet": 4}
TAG = re.compile(r'"([^"]+)"=>"([^"]*)"')


def r(v: float) -> float:
    return round(float(v), 5)


def main() -> None:
    boundary = gpd.read_file(BOUNDARY).to_crs("EPSG:4326")
    clip = boundary.geometry.union_all() if hasattr(boundary.geometry, "union_all") else boundary.geometry.unary_union
    minx, miny, maxx, maxy = clip.bounds
    pts = pyogrio.read_dataframe(PBF, layer="points", bbox=(minx, miny, maxx, maxy), columns=["name", "place", "other_tags"])
    pts = pts[pts["place"].isin(list(RANK)) & pts["name"].notna()]
    pts = pts[pts.geometry.within(clip)].set_crs("EPSG:4326", allow_override=True)

    ward_path = next(p for p in WARDS if p.exists())
    wards = gpd.read_file(ward_path).set_crs("EPSG:4326", allow_override=True)
    if "ward_id" not in wards.columns:
        wards = wards.rename(columns={"Ward_No": "ward_id"})
        wards["ward_name"] = "Ward " + wards["ward_id"].astype(str)
        wards["zone"] = wards["Zone_No"].astype(str) + " " + wards["Zone_Name"].astype(str).str.title()
    joined = gpd.sjoin(pts, wards[["ward_id", "zone", "geometry"]], how="left", predicate="within")

    places, seen = [], set()
    for row in joined.itertuples(index=False):
        tags = dict(TAG.findall(row.other_tags if isinstance(row.other_tags, str) else ""))
        alt = [v for k, v in tags.items() if k in ("name:ta", "name:en", "alt_name", "old_name", "official_name") and v and v != row.name]
        key = (row.name.lower(), round(row.geometry.x, 3), round(row.geometry.y, 3))
        if key in seen:
            continue
        seen.add(key)
        places.append({"name": row.name, "alt": alt, "type": row.place, "lon": r(row.geometry.x), "lat": r(row.geometry.y),
                       "ward_id": int(row.ward_id) if row.ward_id == row.ward_id and row.ward_id is not None else None,
                       "zone": row.zone if isinstance(row.zone, str) else None, "rank": RANK[row.place]})
    places.sort(key=lambda p: (p["rank"], p["name"]))

    ward_list = []
    for w in wards.itertuples(index=False):
        c = w.geometry.representative_point()
        b = w.geometry.bounds
        ward_list.append({"ward_id": int(w.ward_id), "name": str(w.ward_name), "zone": str(w.zone) if w.zone else None,
                          "lon": r(c.x), "lat": r(c.y), "bbox": [r(v) for v in b]})
    ward_list.sort(key=lambda w: w["ward_id"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"schema": "twinguard.ui.gazetteer.v1", "source_mode": "STATIC_REFERENCE",
                               "attribution": "© OpenStreetMap contributors (ODbL); GCC ward boundaries",
                               "places": places, "wards": ward_list}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(places)} places, {len(ward_list)} wards ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
