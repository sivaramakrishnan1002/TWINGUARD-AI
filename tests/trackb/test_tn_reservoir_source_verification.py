import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "docs/trackb/tn_reservoir_source_verification.json"


def test_b39_record_has_fields_evidence_and_explicit_unknowns():
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    assert record["task"] == "B39"
    assert record["source"]["page_url"].startswith("https://www.tnagrisnet.tn.gov.in/")
    assert record["source"]["unauthenticated_check"]["http_status"] == 200
    assert "no table rows" in record["source"]["unauthenticated_check"]["response"]
    assert {field["name"] for field in record["fields"]} >= {
        "current_year_level", "current_year_storage", "current_year_inflow",
        "current_year_outflow", "last_year_level", "last_year_storage",
    }
    assert record["cadence_freshness"]["documented_publication_cadence"] == "UNKNOWN"
    assert record["cadence_freshness"]["update_cadence_observed"].startswith("UNKNOWN")
    assert record["cadence_freshness"]["latest_published_or_realtime"] == "UNKNOWN; cannot label LIVE or REAL-TIME because no observation source timestamp/freshness evidence"
    assert record["live_access_verified"] is False
    assert record["authorized_for_live"] is False
    assert record["time"]["preserve_c3"].startswith("Historical source_date date-only")
    assert record["human_follow_up"]


def test_report_preserves_unknowns_and_does_not_claim_live():
    report = (ROOT / "docs/trackb/TN_RESERVOIR_SOURCE_VERIFICATION.md").read_text(encoding="utf-8")
    assert "UNKNOWN" in report
    assert "must not be labeled `LIVE`" in report
    assert "observed_at=null" in report
    assert "No page API/XHR endpoint was inferred or called" in report
