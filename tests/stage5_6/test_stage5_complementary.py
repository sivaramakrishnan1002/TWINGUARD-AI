"""Contracts for the completed Stage 5 extension tables and safe repairs."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

from sqlalchemy import text  # noqa: E402
from pipelines.stage5.db_common import make_engine  # noqa: E402


def test_stage5_complementary_source_rows_and_catalog_are_complete():
    engine=make_engine()
    try:
        with engine.connect() as conn:
            expected={
                "road_nodes":508854,"grid_cells":1319380,"building_footprints":382294,
                "observation_records":266773,"flood_labels":21927,"sentinel_scenes":13,
                "data_manifest":117,
            }
            for table,count in expected.items():
                actual=conn.execute(text(f"SELECT count(*) FROM twinguard.{table}")).scalar_one()
                assert actual==count,table
            # Migrations 001–009 are Stage 5 (009 adds boundary provenance).
            assert conn.execute(text("SELECT count(*) FROM twinguard.schema_migrations WHERE version LIKE '00%'")).scalar_one()==9
            assert conn.execute(text("SELECT count(*) FROM twinguard.dataset_catalog c WHERE c.layer_key IN (SELECT DISTINCT source_id FROM twinguard.grid_cells UNION SELECT DISTINCT source_id FROM twinguard.observation_records UNION SELECT DISTINCT source_id FROM twinguard.flood_labels UNION SELECT DISTINCT source_id FROM twinguard.sentinel_scenes UNION SELECT DISTINCT source_id FROM twinguard.road_nodes UNION SELECT DISTINCT source_id FROM twinguard.building_footprints UNION SELECT DISTINCT source_id FROM twinguard.data_manifest)")).scalar_one()>=35
    finally:
        engine.dispose()


def test_original_flood_geometries_preserved_and_repaired_views_valid():
    engine=make_engine()
    try:
        with engine.connect() as conn:
            original_invalid=conn.execute(text("SELECT count(*) FROM twinguard.flood_references WHERE NOT ST_IsValid(geom)")).scalar_one()
            repaired_invalid=conn.execute(text("SELECT count(*) FROM twinguard.flood_references WHERE geom_repaired IS NULL OR NOT is_valid OR NOT ST_IsValid(geom_repaired)")).scalar_one()
            assert original_invalid==235
            assert repaired_invalid==0
            label_invalid=conn.execute(text("SELECT count(*) FROM twinguard.flood_labels WHERE geom_repaired IS NOT NULL AND (NOT geometry_valid_after_repair OR NOT ST_IsValid(geom_repaired))")).scalar_one()
            assert label_invalid==0
            assert conn.execute(text("SELECT count(*) FROM twinguard.v_flood_references WHERE geom IS NULL OR NOT ST_IsValid(geom)")).scalar_one()==0
            assert conn.execute(text("SELECT count(*) FROM twinguard.v_flood_labels WHERE geom IS NOT NULL AND NOT ST_IsValid(geom)")).scalar_one()==0
    finally:
        engine.dispose()
