import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs/api/ai-service.yaml"

def test_cfm_reservoir_projection_is_additive_and_bounded():
    spec=json.loads(SPEC.read_text(encoding="utf-8"))
    operation=spec["paths"]["/reservoirs/history"]["get"]
    assert operation["operationId"] == "getCfmReservoirHistory"
    assert operation["parameters"][0]["schema"]["enum"] == ["daily", "monthly"]
    assert operation["responses"]["200"]["headers"]["Cache-Control"]["schema"]["const"] == "no-store"
    history=spec["components"]["schemas"]["CfmReservoirHistory"]
    assert history["properties"]["source_mode"]["const"] == "LIVE"
    assert history["properties"]["freshness"]["const"] == "unknown"
    assert history["properties"]["records"]["maxItems"] == 75

def test_cfm_record_preserves_date_only_and_source_provenance():
    spec=json.loads(SPEC.read_text(encoding="utf-8"))
    record=spec["components"]["schemas"]["CfmReservoirRecord"]["properties"]
    assert record["source_date"]["format"] == "date"
    assert record["observed_at"]["type"] == "null"
    assert record["observation_timezone"]["const"] == "unknown"
    assert record["average_storage_mcm"]["minimum"] == 0
    assert record["provenance"]["$ref"].endswith("CfmReservoirProvenance")
    assert "/Master/GetLast15daysWaterLevel" in spec["components"]["schemas"]["CfmReservoirProvenance"]["properties"]["endpoint"]["enum"]

def test_cr017_does_not_claim_flood_decision_or_model_recompute():
    text=(ROOT/"docs/master/CR-017_CFM_RESERVOIR_SNAPSHOT_API.md").read_text(encoding="utf-8").lower()
    assert "must not trigger" in text
    assert "freshness=unknown" in text
    assert "operational real-time telemetry" in text
