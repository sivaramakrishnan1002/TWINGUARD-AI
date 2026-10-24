"""Stage 5/6 schema, provenance, and vector-tile smoke checks."""
from __future__ import annotations

import sys
import hashlib
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipelines.stage5.db_common import read_env  # noqa: E402
from pipelines.stage6.verify_gis import verify  # noqa: E402
from tools.audit_raw_logs import parse_log_text  # noqa: E402


def test_raw_audit_parser_recognizes_imerg_log_labels():
    sample = (
        "File: one.nc4\nSize bytes: 321\nSHA-256: " + "a" * 64 + "\n"
        "\nFile name: two.tif\nFile size (bytes): 654\nSHA-256: " + "b" * 64 + "\n"
    )
    entries = parse_log_text(sample, Path("DOWNLOAD_LOG.txt"))
    assert [(e["name"], e["size"]) for e in entries] == [("one.nc4", 321), ("two.tif", 654)]


def test_env_reader_has_required_keys_without_exposing_values():
    values = read_env()
    assert {"POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"}.issubset(values)
    assert values["POSTGRES_DB"] == "twinguard"


def test_postgis_schema_and_loaded_row_counts_match_catalog():
    report = verify()
    assert report["postgis_version"].startswith("3.6")
    assert all(check["exists"] and check["matches_catalog"]
               for key, check in report["source_hash_checks"].items()
               if key != "stage5_data_manifest")
    assert report["table_checks"]["study_area"]["rows"] == 1
    assert report["table_checks"]["study_area"]["srid"] == 32644
    assert report["table_checks"]["road_edges"]["rows"] == 455285
    assert report["table_checks"]["facilities"]["rows"] == 15413
    assert report["table_checks"]["waterways"]["rows"] == 759
    expected_totals = {
        "road_edges": 455285, "road_nodes": 508854, "facilities": 15413,
        "waterways": 759, "building_footprints": 382294,
    }
    assert set(report["cma_flags"]) == set(expected_totals)
    for table, total in expected_totals.items():
        assert report["cma_flags"][table]["total"] == total
        assert report["cma_flags"][table]["inside"] + report["cma_flags"][table]["outside"] == total
        assert report["cma_flags"][table]["mismatches"] == 0
    assert report["table_checks"]["flood_references"]["rows"] == sum(
        entry["loaded_row_count"] for entry in report["catalog"]
        if entry["layer_key"].startswith("unosat_")
    )
    assert all(report["table_checks"][table]["invalid_geometries"] == 0
               for table in ("study_area", "road_edges", "facilities", "waterways"))
    assert report["table_checks"]["flood_references"]["invalid_geometries"] == 235


def test_manifest_hash_comes_from_latest_load_record():
    from sqlalchemy import text
    from pipelines.stage5.db_common import make_engine

    manifest = ROOT / "docs" / "DATA_MANIFEST.csv"
    expected_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()
    engine = make_engine()
    try:
        with engine.connect() as conn:
            latest = conn.execute(text(
                "SELECT source_sha256, loader, load_time FROM twinguard.data_manifest "
                "WHERE source_id='stage5_data_manifest' ORDER BY load_time DESC LIMIT 1"
            )).one()
            catalogue = conn.execute(text(
                "SELECT source_sha256, loaded_row_count, loaded_at FROM twinguard.dataset_catalog "
                "WHERE layer_key='stage5_data_manifest'"
            )).one()
            row_count = conn.execute(text(
                "SELECT count(*) FROM twinguard.data_manifest WHERE source_id='stage5_data_manifest'"
            )).scalar_one()
            distinct_hashes = conn.execute(text(
                "SELECT count(DISTINCT source_sha256) FROM twinguard.data_manifest "
                "WHERE source_id='stage5_data_manifest'"
            )).scalar_one()
        assert latest.source_sha256 == expected_hash == catalogue.source_sha256
        assert latest.loader == "tools.refresh_data_manifest"
        assert latest.load_time == catalogue.loaded_at
        expected_count = len(list(csv.DictReader(manifest.open(encoding="utf-8-sig", newline=""))))
        assert row_count == catalogue.loaded_row_count == expected_count
        assert distinct_hashes == 1
    finally:
        engine.dispose()


def test_views_and_vector_tile_functions_are_available():
    report = verify()
    assert report["views"] == {
        "v_study_area": 1,
        "v_roads": report["table_checks"]["road_edges"]["rows"],
        "v_facilities": report["table_checks"]["facilities"]["rows"],
        "v_waterways": report["table_checks"]["waterways"]["rows"],
        "v_flood_references": report["table_checks"]["flood_references"]["rows"],
    }
    assert set(report["mvt_tile"]["bytes"]) == {
        "study_area", "roads", "facilities", "waterways", "flood_references"
    }
    assert report["mvt_tile"]["bytes"]["study_area"] > 0

