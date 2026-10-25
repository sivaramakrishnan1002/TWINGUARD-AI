"""Validate digitized flood-map polygons and optionally load them as pending labels."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely.geometry import MultiPolygon, Polygon
from shapely.validation import explain_validity

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REQUIRED = {"event", "map_date", "source", "digitiser", "confidence", "notes", "georef_rmse_m", "created", "geometry"}
ONE_CELL_RMSE_M = 30.0
LOADER = "pipelines.labels.manual_map_loader"


def classify_tier(rmse_m: float) -> str:
    if not math.isfinite(rmse_m) or rmse_m < 0:
        raise ValueError("georef_rmse_m must be finite and non-negative")
    return "B" if rmse_m <= ONE_CELL_RMSE_M else "C"


def validate_layer(gdf: gpd.GeoDataFrame) -> list[dict[str, Any]]:
    missing = REQUIRED - set(gdf.columns)
    if missing:
        raise ValueError(f"missing required fields: {sorted(missing)}")
    if gdf.crs is None or gdf.crs.to_epsg() != 32644:
        raise ValueError("input GeoPackage must use EPSG:32644")
    records = []
    for index, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            raise ValueError(f"row {index}: empty geometry")
        if not geom.is_valid:
            raise ValueError(f"row {index}: invalid geometry ({explain_validity(geom)})")
        if not isinstance(geom, (Polygon, MultiPolygon)):
            raise ValueError(f"row {index}: geometry must be Polygon or MultiPolygon")
        for field in ("event", "source", "digitiser"):
            if row[field] is None or not str(row[field]).strip():
                raise ValueError(f"row {index}: {field} is required")
        try:
            map_day = date.fromisoformat(str(row["map_date"])[:10])
        except ValueError as exc:
            raise ValueError(f"row {index}: map_date must be YYYY-MM-DD") from exc
        rmse = float(row["georef_rmse_m"])
        tier = classify_tier(rmse)
        confidence = str(row["confidence"] or "").strip()
        created = str(row["created"] or "").strip()
        key_seed = "|".join([str(row["event"]), map_day.isoformat(), str(row["source"]), geom.wkb_hex])
        label_key = "manual-map:" + hashlib.sha256(key_seed.encode("utf-8")).hexdigest()
        records.append({
            "row_index": int(index), "label_key": label_key, "event": str(row["event"]),
            "event_date": map_day, "source_id": str(row["source"]), "tier": tier,
            "confidence": confidence, "digitiser": str(row["digitiser"]),
            "notes": str(row["notes"] or ""), "georef_rmse_m": rmse,
            "created": created, "geometry": geom,
        })
    return records


def create_empty_template(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing template: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    empty = gpd.GeoDataFrame({
        "event": pd.Series(dtype="str"), "map_date": pd.Series(dtype="str"),
        "source": pd.Series(dtype="str"), "digitiser": pd.Series(dtype="str"),
        "confidence": pd.Series(dtype="str"), "notes": pd.Series(dtype="str"),
        "georef_rmse_m": pd.Series(dtype="float64"), "created": pd.Series(dtype="str"),
    }, geometry=gpd.GeoSeries([], crs="EPSG:32644"), crs="EPSG:32644")
    empty.to_file(path, layer="digitised_labels", driver="GPKG", index=False)


def parse_env(path: Path) -> dict[str, str]:
    """Small parser; values are returned only to the DB driver, never displayed."""
    values: dict[str, str] = {}
    if not path.is_file():
        raise FileNotFoundError(".env file is missing")
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def load_records(records: list[dict[str, Any]], source_sha256: str, env_path: Path) -> int:
    import psycopg

    env = parse_env(env_path)
    params = {
        "host": env.get("POSTGRES_HOST", "localhost"), "port": int(env.get("POSTGRES_PORT", "5432")),
        "dbname": env["POSTGRES_DB"], "user": env["POSTGRES_USER"], "password": env["POSTGRES_PASSWORD"],
        "connect_timeout": 5,
    }
    sql = """
    INSERT INTO labels.derived_flood_polygons
      (label_key,event_date,method,tier,is_derived,is_valid,in_cma,urban_unreliable,
       flood_area_km2,source_id,source_sha256,loader,geom,review_status)
    SELECT %(label_key)s,%(event_date)s,'DERIVED-FROM-MAP',%(tier)s,true,true,
       ST_Intersects(ST_SetSRID(ST_GeomFromWKB(%(geom)s),32644),sa.geom),false,
       ST_Area(ST_Intersection(ST_SetSRID(ST_GeomFromWKB(%(geom)s),32644),sa.geom))/1000000.0,
       %(source_id)s,%(source_sha256)s,%(loader)s,
       ST_Multi(ST_SetSRID(ST_GeomFromWKB(%(geom)s),32644)),'PENDING_MANUAL_REVIEW'
    FROM twinguard.study_area sa
    ON CONFLICT (label_key) DO NOTHING
    """
    inserted = 0
    # Do not allow driver exception text to expose connection parameters.
    try:
        with psycopg.connect(**params) as conn:
            with conn.cursor() as cur:
                for rec in records:
                    cur.execute(sql, {"label_key": rec["label_key"], "event_date": rec["event_date"], "tier": rec["tier"], "source_id": rec["source_id"], "source_sha256": source_sha256, "loader": LOADER, "geom": rec["geometry"].wkb})
                    inserted += cur.rowcount
    except Exception as exc:
        # Caller sees the exception type and sanitized summary only.
        raise RuntimeError(f"database load failed ({type(exc).__name__}); credentials and connection details suppressed") from None
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", type=Path, default=PROJECT_ROOT / "data/processed/labels_manual/digitised_labels.gpkg")
    parser.add_argument("--create-template", action="store_true")
    parser.add_argument("--load", action="store_true", help="load validated non-empty rows into labels.derived_flood_polygons")
    args = parser.parse_args()
    if args.create_template:
        create_empty_template(args.input)
        print("Created empty digitised-label template in EPSG:32644.")
        return
    gdf = gpd.read_file(args.input, layer="digitised_labels")
    records = validate_layer(gdf)
    print(json.dumps({"validated_rows": len(records), "tier_b": sum(r["tier"] == "B" for r in records), "tier_c": sum(r["tier"] == "C" for r in records), "loaded": False}))
    if args.load and records:
        source_hash = hashlib.sha256(args.input.read_bytes()).hexdigest()
        inserted = load_records(records, source_hash, PROJECT_ROOT / ".env")
        print(json.dumps({"inserted_rows": inserted, "review_status": "PENDING_MANUAL_REVIEW"}))
    elif args.load:
        print("No rows to load; the template remains empty.")


if __name__ == "__main__":
    main()
