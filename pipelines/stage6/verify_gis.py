"""Read-only verification of the Stage 5/6 PostGIS installation and GIS layers."""
from __future__ import annotations

import json
import hashlib
import math
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT))
from pipelines.stage5.db_common import make_engine

TABLES = ("study_area", "road_edges", "facilities", "waterways", "flood_references")
FUNCTIONS = ("study_area", "roads", "facilities", "waterways", "flood_references")


def chennai_tile(z: int = 12) -> tuple[int, int, int]:
    lon, lat = 80.24, 13.05
    n = 2**z
    x = math.floor((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = math.floor((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return z, x, y


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify() -> dict:
    engine = make_engine()
    report: dict = {}
    try:
        with engine.connect() as conn:
            report["postgres_version"] = conn.execute(text("SELECT version()")).scalar_one()
            report["postgis_version"] = conn.execute(text("SELECT postgis_version()")).scalar_one()
            report["migrations"] = conn.execute(text(
                "SELECT version, checksum_sha256 FROM twinguard.schema_migrations ORDER BY version"
            )).all()
            report["catalog"] = [dict(r._mapping) for r in conn.execute(text(
                "SELECT layer_key,source_path,source_layer,source_sha256,source_crs,target_srid,loaded_row_count,licence_note "
                "FROM twinguard.dataset_catalog ORDER BY layer_key"
            )).all()]
            report["source_hash_checks"] = {}
            for item in report["catalog"]:
                source = ROOT / Path(item["source_path"])
                report["source_hash_checks"][item["layer_key"]] = {
                    "exists": source.is_file(),
                    "matches_catalog": source.is_file() and file_sha256(source) == item["source_sha256"],
                }
            report["table_checks"] = {}
            for table in TABLES:
                count, invalid, srid = conn.execute(text(
                    f"SELECT count(*), count(*) FILTER (WHERE NOT ST_IsValid(geom)), "
                    f"min(ST_SRID(geom)) FROM twinguard.{table}"
                )).one()
                report["table_checks"][table] = {"rows": count, "invalid_geometries": invalid, "srid": srid}
            report["views"] = {}
            for view, table in (("v_study_area", "study_area"), ("v_roads", "road_edges"),
                                ("v_facilities", "facilities"), ("v_waterways", "waterways"),
                                ("v_flood_references", "flood_references")):
                report["views"][view] = conn.execute(text(f"SELECT count(*) FROM twinguard.{view}")).scalar_one()
            report["cma_containment"] = conn.execute(text("""
                SELECT
                  (SELECT count(*) FROM twinguard.facilities f,twinguard.study_area a
                   WHERE ST_Covers(a.geom,f.geom)),
                  (SELECT count(*) FROM twinguard.road_edges r,twinguard.study_area a
                   WHERE ST_Intersects(a.geom,r.geom)),
                  (SELECT count(*) FROM twinguard.waterways w,twinguard.study_area a
                   WHERE ST_Intersects(a.geom,w.geom))
            """)).one()
            z, x, y = chennai_tile()
            report["mvt_tile"] = {"z": z, "x": x, "y": y, "bytes": {}}
            for name in FUNCTIONS:
                length = conn.execute(text(
                    f"SELECT octet_length(twinguard.mvt_{name}(:z,:x,:y))"
                ), {"z": z, "x": x, "y": y}).scalar_one_or_none()
                report["mvt_tile"]["bytes"][name] = length or 0
    finally:
        engine.dispose()
    return report


if __name__ == "__main__":
    print(json.dumps(verify(), default=str, indent=2))
