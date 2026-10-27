"""Export the accepted flood-label view as RFC 7946 GeoJSON, without DB writes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import psycopg
from pyproj import Transformer
from shapely import from_wkb, transform as shapely_transform
from shapely.geometry import mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_OUTPUT = ROOT / "data/features/labels/usable_flood_labels_geojson_v0.geojson"
PROPERTY_NAMES = (
    "label_key", "event_date", "method", "reference_role", "tier", "is_derived",
    "is_valid", "in_cma", "source_id", "source_sha256", "loader", "load_time",
)
ACCEPTED_TIERS = {"A", "B", "C"}
ACCEPTED_ROLES = {"event_flood", "baseline_water"}
TO_WGS84 = Transformer.from_crs("EPSG:32644", "EPSG:4326", always_xy=True)


def _timestamp_utc(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise TypeError("load_time must be a datetime or null")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("load_time is timezone-naive; refusing to guess its timezone")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _date_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        raise TypeError("event_date must be a date without a time")
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError("event_date must be a date or null")


def serialize_row(row: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Return (Feature, rejection reason); missing provenance remains JSON null."""
    tier = row.get("tier")
    role = row.get("reference_role")
    if tier not in ACCEPTED_TIERS:
        return None, "tier_not_accepted_A_B_C"
    if role not in ACCEPTED_ROLES:
        return None, "reference_role_not_supported"
    if row.get("is_valid") is not True:
        return None, "row_not_marked_valid"
    if row.get("in_cma") is not True:
        return None, "row_not_marked_in_cma"
    raw_geometry = row.get("geom_wkb")
    if raw_geometry is None:
        return None, "geometry_null"
    try:
        geom = from_wkb(bytes(raw_geometry))
    except Exception:
        return None, "geometry_unreadable_wkb"
    if geom.is_empty:
        return None, "geometry_empty"
    if not geom.is_valid:
        return None, "geometry_invalid"
    if geom.geom_type not in {"Polygon", "MultiPolygon"}:
        return None, "geometry_not_polygonal"
    try:
        wgs84 = geom_transform(geom)
    except Exception:
        return None, "geometry_transform_failed"
    if wgs84.is_empty or not wgs84.is_valid or wgs84.geom_type not in {"Polygon", "MultiPolygon"}:
        return None, "transformed_geometry_invalid_or_not_polygonal"

    properties = {
        "label_key": row.get("label_key"),
        "event_date": _date_iso(row.get("event_date")),
        "method": row.get("method"),
        "reference_role": role,
        "tier": tier,
        "is_derived": row.get("is_derived"),
        "is_valid": row.get("is_valid"),
        "in_cma": row.get("in_cma"),
        "source_id": row.get("source_id"),
        "source_sha256": row.get("source_sha256"),
        "loader": row.get("loader"),
        "load_time": _timestamp_utc(row.get("load_time")),
    }
    return {"type": "Feature", "geometry": mapping(wgs84), "properties": properties}, None


def geom_transform(geom):
    return shapely_transform(geom, TO_WGS84.transform, interleaved=False)


def build_collection(rows: Iterable[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    features: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []
    read_count = 0
    for row in rows:
        read_count += 1
        feature, reason = serialize_row(row)
        if feature is None:
            rejects.append({"label_key": row.get("label_key"), "reason": reason})
        else:
            features.append(feature)
    return (
        {"type": "FeatureCollection", "features": features},
        {"read_rows": read_count, "exported_features": len(features), "rejected_rows": len(rejects), "rejections": rejects},
    )


def fetch_rows() -> list[dict[str, Any]]:
    # The project-local parser reads .env without displaying it; the DB transaction is read-only.
    from pipelines.stage5.db_common import read_env

    env = read_env()
    with psycopg.connect(
        host=env.get("POSTGRES_HOST") or "localhost",
        port=int(env.get("POSTGRES_PORT") or "5432"),
        dbname=env["POSTGRES_DB"],
        user=env["POSTGRES_USER"],
        password=env["POSTGRES_PASSWORD"],
        connect_timeout=5,
        options="-c default_transaction_read_only=on",
    ) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        rows = conn.execute(
            """SELECT label_key,event_date,method,reference_role,tier,is_derived,is_valid,
                      in_cma,source_id,source_sha256,loader,load_time,ST_AsBinary(geom) AS geom_wkb
               FROM labels.v_usable_flood_labels
               ORDER BY event_date,reference_role,label_key"""
        ).fetchall()
    # SELECT column names are fixed by the query, independent of credentials or DB configuration.
    names = ["label_key", "event_date", "method", "reference_role", "tier", "is_derived", "is_valid", "in_cma", "source_id", "source_sha256", "loader", "load_time", "geom_wkb"]
    return [dict(zip(names, row, strict=True)) for row in rows]


def _write_new(path: Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".partial")
    if path.exists() or temp.exists():
        raise FileExistsError(f"Refusing to overwrite existing export path: {path}")
    try:
        with temp.open("xb") as stream:
            stream.write(payload)
        # Hard-link creation is exclusive: it cannot replace a path created by another process.
        os.link(temp, path)
        temp.unlink()
    except Exception:
        temp.unlink(missing_ok=True)
        raise
    return hashlib.sha256(payload).hexdigest()


def export(output: Path = DEFAULT_OUTPUT, rows: Iterable[dict[str, Any]] | None = None) -> dict[str, Any]:
    output = output.resolve()
    qa_path = output.with_suffix(".qa.json")
    if output.exists() or qa_path.exists() or output.with_name(output.name + ".partial").exists():
        raise FileExistsError(f"Refusing to overwrite existing export output: {output}")
    collection, qa = build_collection(fetch_rows() if rows is None else rows)
    geojson = (json.dumps(collection, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")
    qa_payload = (json.dumps(qa, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")
    qa["geojson_sha256"] = _write_new(output, geojson)
    qa["geojson_bytes"] = len(geojson)
    # Rewrite the QA file with hash/size included. It is itself created once, exclusively.
    qa_payload = (json.dumps(qa, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")
    qa_hash = _write_new(qa_path, qa_payload)
    qa["qa_sha256"] = qa_hash
    return qa


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = export(args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
