"""Offline integrity checks for the B38 IMD source evidence inventory."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "docs" / "trackb" / "imd_source_verification.json"
REPORT_PATH = ROOT / "docs" / "trackb" / "IMD_SOURCE_VERIFICATION.md"
ALLOWED_HOSTS = {"api.imd.gov.in", "mausam.imd.gov.in"}


def _inventory():
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def test_inventory_has_required_decision_and_evidence_fields():
    inventory = _inventory()
    assert inventory["task_id"] == "B38"
    assert inventory["decision"]["status"] == "PROPOSED_NOT_AUTHORIZED"
    assert inventory["decision"]["live_access_verified"] is False
    assert inventory["decision"]["connector_implemented"] is False
    assert inventory["repository_evidence"]
    assert inventory["official_sources"]
    assert inventory["decision"]["human_follow_up"]
    for source in inventory["sources"]:
        for key in (
            "id",
            "product",
            "product_class",
            "api_version",
            "endpoints",
            "chennai",
            "documented_fields",
            "documented_units_and_time",
            "documented_cadence",
            "observed_update_cadence",
            "spatial_coverage_resolution",
            "provenance_revision_missing_latency",
            "access_terms_status",
            "evidence",
        ):
            assert source.get(key), (source.get("id"), key)


def test_unverified_access_and_observed_freshness_remain_unknown():
    inventory = _inventory()
    decision = inventory["decision"]
    assert decision["unauthenticated_product_checks"] == "NOT_PERFORMED"
    assert decision["observed_endpoint_response"] == "UNKNOWN"
    assert decision["observed_update_cadence"] == "UNKNOWN"
    assert "UNKNOWN" in decision["registration"]
    assert decision["terms_permission"].startswith("UNKNOWN")
    assert decision["retention_redistribution_fees_rate_limits"] == "UNKNOWN"
    for source in inventory["sources"]:
        assert source["observed_update_cadence"].startswith("UNKNOWN")
        assert source["access_terms_status"].startswith("UNKNOWN")


def test_endpoints_are_documented_https_urls_on_official_hosts():
    from urllib.parse import urlparse

    inventory = _inventory()
    for source in inventory["sources"]:
        for endpoint in source["endpoints"]:
            parsed = urlparse(endpoint)
            assert parsed.scheme == "https"
            assert parsed.hostname in ALLOWED_HOSTS
            assert "/api/v1/" in parsed.path


def test_no_source_is_claimed_verified_live_or_observed():
    inventory = _inventory()
    assert all(source.get("status") != "LIVE" for source in inventory["sources"])
    text = REPORT_PATH.read_text(encoding="utf-8")
    assert "**PROPOSED / NOT AUTHORIZED" in text
    assert "**observed API update cadence is UNKNOWN**" in text
    assert "did **not** request any product/data API URL" in text


def test_chennai_mapping_and_undocumented_units_are_explicit():
    inventory = _inventory()
    by_id = {source["id"]: source for source in inventory["sources"]}
    assert "UNVERIFIED" in by_id["cityforecast_7day"]["chennai"]["coverage_status"]
    assert "UNVERIFIED" in by_id["aws_arg"]["chennai"]["coverage_status"]
    assert "unit is not specified" in by_id["cityforecast_7day"]["documented_units_and_time"]
    aws_schema_note = by_id["aws_arg"]["documented_units_and_time"].lower()
    assert "unknown" in aws_schema_note
    assert by_id["districtrainfall"]["chennai"]["coverage_status"].endswith("UNVERIFIED")
