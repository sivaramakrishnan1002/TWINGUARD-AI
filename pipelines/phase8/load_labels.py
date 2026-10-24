"""Apply Stage 8 label migration and idempotently load derived polygons."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import geopandas as gpd
import pyogrio
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from pipelines.stage5.db_common import make_engine

MIGRATION = ROOT / "database/migrations/013_sar_derived_labels.sql"
CATALOG = ROOT / "docs/HYP3_RTC_PRODUCTS.json"
REGISTRY = ROOT / "data/features/labels/label_registry.json"
LOADER = "pipelines.phase8.load_labels"


def _migration_checksum() -> str:
    return hashlib.sha256(MIGRATION.read_bytes()).hexdigest()


def _apply_migration(conn) -> None:
    checksum = _migration_checksum()
    old = conn.execute(text("SELECT checksum_sha256 FROM twinguard.schema_migrations WHERE version=:v"),
                       {"v": MIGRATION.name}).scalar_one_or_none()
    if old:
        if old != checksum:
            raise RuntimeError("Stage 8 migration checksum differs from applied version")
        return
    conn.exec_driver_sql(MIGRATION.read_text(encoding="utf-8"))
    conn.execute(text("INSERT INTO twinguard.schema_migrations(version,checksum_sha256) VALUES (:v,:h)"),
                 {"v": MIGRATION.name, "h": checksum})


def _source_hashes() -> dict[str, str]:
    records = json.loads(CATALOG.read_text(encoding="utf-8"))
    by_stamp = {}
    for rec in records:
        scene = rec.get("source_scene") or ""
        import re
        match = re.search(r"_(20\d{6}T\d{6})_", scene)
        if match:
            by_stamp[match.group(1)] = rec["sha256"]
    sets = {
        "2015-11-24": ["20151019T003131", "20151124T003120"],
        "2015-12-06": ["20151019T003131", "20151124T003120", "20151206T003120"],
        "2021-11-16": ["20211023T003148", "20211023T003213", "20211104T003147", "20211104T003212", "20211116T003147", "20211116T003212"],
    }
    return {event: hashlib.sha256("\n".join(by_stamp[s] for s in stamps).encode()).hexdigest()
            for event, stamps in sets.items() if all(s in by_stamp for s in stamps)}


def load() -> dict[str, int]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    gpkg_path = ROOT / registry["stage8_outputs"]["vector_geopackage"]
    if not gpkg_path.is_file():
        raise FileNotFoundError("Expected derived polygon GeoPackage was not created")
    layer_names = pyogrio.list_layers(gpkg_path)[:, 0].tolist()
    source_hashes = _source_hashes()
    results: dict[str, int] = {}
    engine = make_engine()
    try:
        with engine.begin() as conn:
            _apply_migration(conn)
            for layer in layer_names:
                gdf = gpd.read_file(gpkg_path, layer=layer)
                inserted = 0
                for _idx, props in gdf.iterrows():
                    geom = props.geometry
                    if geom is None or geom.is_empty:
                        continue
                    event_value = props["event_date"]
                    event = event_value.isoformat() if hasattr(event_value, "isoformat") else str(event_value)
                    digest = source_hashes.get(event)
                    if not digest:
                        raise RuntimeError(f"No verified input SHA-256 set for event {event}")
                    key = props["label_key"]
                    existing = conn.execute(text("SELECT source_sha256 FROM labels.derived_flood_polygons WHERE label_key=:k"),
                                            {"k": key}).scalar_one_or_none()
                    if existing:
                        if existing != digest:
                            raise RuntimeError(f"Existing Stage 8 label key has different provenance: {key}")
                        continue
                    conn.execute(text("""
                        INSERT INTO labels.derived_flood_polygons
                        (label_key,event_date,method,tier,is_derived,is_valid,in_cma,urban_unreliable,
                         flood_area_km2,source_id,source_sha256,loader,geom)
                        SELECT :label_key,:event_date,:method,:tier,true,
                               ST_IsValid(ST_GeomFromWKB(:wkb,32644)),
                               ST_Intersects(sa.geom,ST_GeomFromWKB(:wkb,32644)),
                               :urban_unreliable,:area,:source_id,:sha,:loader,
                               ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_GeomFromWKB(:wkb,32644)),3))::geometry(MultiPolygon,32644)
                        FROM twinguard.study_area sa
                        WHERE ST_Intersects(sa.geom,ST_GeomFromWKB(:wkb,32644))
                        ORDER BY ST_Area(sa.geom) DESC LIMIT 1
                        ON CONFLICT (label_key) DO NOTHING
                    """), {
                        "label_key": key, "event_date": event, "method": props["method"],
                        "tier": props["tier"], "wkb": geom.wkb,
                        "urban_unreliable": bool(props["urban_unreliable"]),
                        "area": float(props["flood_area_km2"]), "source_id": f"hyp3_sar_{event}",
                        "sha": digest, "loader": LOADER,
                    })
                    inserted += 1
                results[layer] = inserted
        return results
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        loaded = load()
        print("Loaded Stage 8 DERIVED polygon rows:", json.dumps(loaded, sort_keys=True))
    except Exception as exc:
        print(f"Stage 8 label load failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
