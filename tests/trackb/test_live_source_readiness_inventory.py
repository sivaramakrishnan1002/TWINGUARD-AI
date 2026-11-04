"""Local completeness checks for the B34 repository-only evidence inventory."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "docs/trackb/live_source_readiness_inventory.json"
REQUIRED_FIELDS = {
    "id",
    "category",
    "name",
    "evidence_paths",
    "owner",
    "access_method_documented",
    "terms",
    "update_cadence",
    "latency",
    "units",
    "timestamp_meaning_timezone",
    "coverage_resolution",
    "provenance_validation",
    "missing_data_behavior",
    "availability_class",
    "live_access_verified",
    "known_limitations",
    "required_before_system_use",
}
ALLOWED_CLASSES = {"LIVE", "REPLAY", "SIMULATED", "PROPOSED", "UNVERIFIED", "UNAVAILABLE"}


def _inventory():
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def test_inventory_has_required_top_level_metadata_and_sources():
    inventory = _inventory()
    assert inventory["inventory_version"]
    assert inventory["created_on"]
    assert inventory["unknown_value"] == "UNKNOWN"
    assert inventory["sources"]
    ids = [source["id"] for source in inventory["sources"]]
    assert len(ids) == len(set(ids))
    categories = {source["category"] for source in inventory["sources"]}
    assert {"rainfall", "reservoir"}.issubset(categories)


def test_each_source_has_complete_explicit_evidence_fields():
    for source in _inventory()["sources"]:
        assert REQUIRED_FIELDS <= source.keys(), source.get("id")
        assert source["evidence_paths"]
        assert all((ROOT / path).exists() for path in source["evidence_paths"]), source["id"]
        assert source["availability_class"] in ALLOWED_CLASSES
        assert isinstance(source["live_access_verified"], bool)
        assert source["known_limitations"]
        assert source["required_before_system_use"]
        for field in REQUIRED_FIELDS - {"evidence_paths", "known_limitations", "required_before_system_use", "live_access_verified"}:
            value = source[field]
            assert value is not None and value != "", (source["id"], field)


def test_no_candidate_is_claimed_live_without_repository_evidence():
    inventory = _inventory()
    assert inventory["live_source_readiness"] == "NO_CANDIDATE_VERIFIED_LIVE"
    assert all(not source["live_access_verified"] for source in inventory["sources"])
    assert all(source["availability_class"] != "LIVE" for source in inventory["sources"])


def test_unknown_source_metadata_stays_explicitly_unknown():
    sources = {source["id"]: source for source in _inventory()["sources"]}
    for source_id in (
        "era5_cds_candidate",
        "imd_rainfall_candidate",
        "tn_wrd_reservoir_operations_candidate",
        "cwc_public_reservoir_monitoring_candidate",
    ):
        source = sources[source_id]
        assert source["availability_class"] == "PROPOSED"
        assert source["live_access_verified"] is False
        assert any("UNKNOWN" in str(source[field]).upper() for field in ("owner", "terms", "update_cadence", "latency", "units", "timestamp_meaning_timezone", "coverage_resolution"))


def test_historical_reservoir_c3_date_only_semantics_are_preserved():
    source = next(source for source in _inventory()["sources"] if source["id"] == "kaggle_chennai_reservoir_archive")
    semantics = source["timestamp_meaning_timezone"]
    assert "date-only" in semantics.lower()
    assert "observed_at=null" in semantics
    assert "observation_timezone=unknown" in semantics
    assert "received_at" in semantics
    assert "never synthesize midnight" in semantics
    assert "UNKNOWN" in semantics
