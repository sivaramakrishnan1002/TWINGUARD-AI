"""Load approved project GIS layers into the twinguard PostGIS schema.

Raw sources are opened read-only. Existing target rows are never replaced; each
source is checksum-gated and safe to rerun after a completed import.
"""
from __future__ import annotations

import hashlib
import json
import sys
import uuid
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
from geoalchemy2 import Geometry
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from pipelines.stage5.db_common import ROOT, make_engine


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _records(gdf: gpd.GeoDataFrame, table: str, key: str, source: Path,
             source_layer: str, source_crs: str, digest: str,
             caveat: str, licence: str) -> int:
    if gdf.empty:
        raise RuntimeError(f"Refusing to register empty layer: {key}")
    if gdf.crs is None:
        raise RuntimeError(f"Missing source CRS for {key}")
    frame = gdf.to_crs(32644).copy()
    if frame.geometry.name != "geom":
        frame = frame.rename_geometry("geom")
    count = len(frame)
    stage = "load_" + uuid.uuid4().hex[:16]
    engine = make_engine()
    try:
        with engine.connect() as conn:
            existing = conn.execute(text(
                "SELECT source_sha256,loaded_row_count FROM twinguard.dataset_catalog WHERE layer_key=:k"),
                {"k": key},
            ).first()
            if existing:
                if existing[0] == digest:
                    print(f"SKIP {key}: already loaded ({existing[1]} rows; source hash matches)")
                    return int(existing[1])
                raise RuntimeError(f"Refusing to overwrite previously loaded layer: {key}")
            current = conn.execute(text(f"SELECT count(*) FROM twinguard.{table}")).scalar_one()
            catalogued = conn.execute(text(
                "SELECT COALESCE(sum(loaded_row_count),0) FROM twinguard.dataset_catalog WHERE layer_key=:key"
            ), {"key": key}).scalar_one()
            if table == "flood_references":
                catalogued = conn.execute(text(
                    "SELECT COALESCE(sum(loaded_row_count),0) FROM twinguard.dataset_catalog "
                    "WHERE layer_key LIKE 'unosat_%'"
                )).scalar_one()
            if current != catalogued:
                raise RuntimeError(f"Refusing to append to table with uncatalogued rows: {table}")
        geom_type = "MULTIPOLYGON" if table == "study_area" else ("GEOMETRY" if table == "flood_references" else {
            "road_edges": "LINESTRING", "facilities": "POINT", "waterways": "LINESTRING"
        }[table])
        frame.to_postgis(stage, engine, schema="twinguard", if_exists="fail", index=False,
                         chunksize=1000, dtype={"geom": Geometry(geometry_type=geom_type, srid=32644)})
        with engine.begin() as conn:
            stage_cols = [c for c in frame.columns]
            columns = ", ".join(f'"{c}"' for c in stage_cols)
            select_columns = ", ".join(
                f'"{c}"::jsonb AS "{c}"' if c == "source_properties" else f'"{c}"'
                for c in stage_cols
            )
            conn.exec_driver_sql(
                f"INSERT INTO twinguard.{table} ({columns}) SELECT {select_columns} FROM twinguard.{stage}"
            )
            inserted = conn.execute(text(f"SELECT count(*) FROM twinguard.{table}")).scalar_one()
            if inserted - current != count:
                raise RuntimeError(
                    f"Row-count mismatch loading {key}: expected {count}, inserted {inserted - current}"
                )
            conn.execute(text("""INSERT INTO twinguard.dataset_catalog
                (layer_key,source_path,source_layer,source_sha256,source_crs,target_srid,
                 loaded_row_count,caveat,licence_note)
                VALUES (:key,:path,:layer,:hash,:crs,32644,:count,:caveat,:licence)"""), {
                    "key": key, "path": source.relative_to(ROOT).as_posix(), "layer": source_layer,
                    "hash": digest, "crs": source_crs, "count": count,
                    "caveat": caveat, "licence": licence,
                })
            conn.exec_driver_sql(f"DROP TABLE twinguard.{stage}")
        print(f"LOADED {key}: {count} rows")
        return count
    except Exception:
        with engine.begin() as conn:
            conn.exec_driver_sql(f"DROP TABLE IF EXISTS twinguard.{stage}")
        raise
    finally:
        engine.dispose()


def load_all() -> dict[str, int]:
    results: dict[str, int] = {}
    boundary_path = ROOT / "data/raw/boundary/chennai_cma_boundary.geojson"
    boundary = gpd.read_file(boundary_path)
    boundary["name"] = boundary.get("NAME", "Chennai Metropolitan Area").astype(str)
    boundary["boundary_vintage"] = "Collected older CMA boundary; vintage not confirmed"
    boundary = boundary[["name", "boundary_vintage", boundary.geometry.name]].rename_geometry("geom")
    results["study_area"] = _records(
        boundary, "study_area", "study_area_older_cma", boundary_path, "chennai_cma_boundary",
        "EPSG:4326", sha256(boundary_path),
        "Older CMA boundary used by the existing project grid; boundary vintage remains unconfirmed.",
        "See source entry in docs/DATA_MANIFEST.csv; source terms were not inferred.")

    road_path = ROOT / "data/processed/routing/vehicle_edges.gpkg"
    roads = gpd.read_file(road_path, layer="vehicle_edges")
    roads = roads.rename(columns={"osmid": "source_osmid"})
    results["road_edges"] = _records(
        roads, "road_edges", "vehicle_road_edges", road_path, "vehicle_edges", "EPSG:32644",
        sha256(road_path),
        "Filtered directed vehicle-routing edge set; default speeds and route assumptions are documented in docs/ROUTING_PROFILE.md.",
        "Derived from OpenStreetMap; preserve ODbL attribution and share-alike obligations documented in project records.")

    facility_path = ROOT / "data/features/facilities/chennai_facilities.gpkg"
    facilities = gpd.read_file(facility_path, layer="facilities").rename(columns={"osmid": "source_osmid"})
    results["facilities"] = _records(
        facilities, "facilities", "osm_facilities", facility_path, "facilities", "EPSG:32644",
        sha256(facility_path), "OSM-derived facilities; source completeness and capacity are not guaranteed.",
        "Derived from OpenStreetMap; preserve ODbL attribution and share-alike obligations documented in project records.")

    water_path = ROOT / "data/features/hydrology/chennai_waterways.gpkg"
    waterways = gpd.read_file(water_path, layer="waterways").rename(columns={"osmid": "source_osmid"})
    results["waterways"] = _records(
        waterways, "waterways", "osm_waterways", water_path, "waterways", "EPSG:32644",
        sha256(water_path), "Mapped OSM waterways; missing names/features do not establish real-world absence.",
        "Derived from OpenStreetMap; preserve ODbL attribution and share-alike obligations documented in project records.")

    archive = ROOT / "data/raw/historical_floods/2015/2015-12-04/FL20151123IND_shp.zip"
    boundary_geom = gpd.read_file(boundary_path).to_crs(4326).geometry.iloc[0]
    bbox = tuple(boundary_geom.bounds)
    layers = [
        ("S1_20150901_PreFlood", "2015-09-01", "baseline_water"),
        ("LS8_20151014_PreFlood", "2015-10-14", "baseline_water"),
        ("S1_20151112_Flood", "2015-11-12", "event_flood"),
        ("S1_20151124_Flood", "2015-11-24", "event_flood"),
    ]
    digest = sha256(archive)
    for source_layer, date, role in layers:
        uri = f"/vsizip/{archive.as_posix()}/{source_layer}.shp"
        gdf = gpd.read_file(uri, bbox=bbox)
        if gdf.crs is None:
            raise RuntimeError(f"Missing CRS in flood source layer {source_layer}")
        keep = gdf.geometry.intersects(boundary_geom)
        gdf = gdf.loc[keep].copy()
        if gdf.empty:
            raise RuntimeError(f"No CMA-intersecting flood features found in {source_layer}")
        props = gdf.drop(columns=gdf.geometry.name).to_dict(orient="records")
        def clean_json_value(value):
            if value is None or pd.isna(value):
                return None
            if hasattr(value, "item"):
                value = value.item()
            return value
        gdf["source_properties"] = [
            json.dumps({k: clean_json_value(v) for k, v in row.items()}, default=str, ensure_ascii=False)
            for row in props
        ]
        gdf["source_layer"] = source_layer
        gdf["event_date"] = pd.to_datetime(date).date()
        gdf["reference_role"] = role
        gdf = gdf[["source_layer", "event_date", "reference_role", "source_properties", gdf.geometry.name]].rename_geometry("geom")
        results[f"flood_{source_layer}"] = _records(
            gdf, "flood_references", f"unosat_{source_layer}", archive, source_layer, "EPSG:4326", digest,
            "UNOSAT source features intersecting the provisional CMA bounding area; baseline layers are reference water, not flood labels. Event layers do not cover the Dec 1-8 2015 peak.",
            "Terms/licence not independently confirmed; retain source attribution and consult the source metadata.")
    return results


if __name__ == "__main__":
    summary = load_all()
    print("GIS layer load complete:", json.dumps(summary, sort_keys=True))
