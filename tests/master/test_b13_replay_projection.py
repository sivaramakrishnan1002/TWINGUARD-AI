"""Conformance checks for the approved, not-yet-mounted CR-012 projection."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AI_SPEC = ROOT / "docs/api/ai-service.yaml"
BACKEND_SPEC = ROOT / "docs/api/backend.yaml"
CONTRACT = ROOT / "docs/master/contracts/c4_openapi_v2.md"
EVENT_ID = "replay:POONDI:date:2015-12-01"
ARCHIVE_SHA256 = "7645febde7ccc21871200487139d1c8a84ea90a6dd2eccc93b7d1f06faf69197"
MEMBER_SHA256 = "3b4b6f2f53b5db20513d2829c2dba265c5738a55bf0c8eade51e0e2d5cfeaef7"


def _spec(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_ai_and_backend_publish_same_unexposed_c4_v2_projection():
    ai = _spec(AI_SPEC)
    backend = _spec(BACKEND_SPEC)
    path = "/replay-alerts/{event_id}"
    ai_operation = ai["paths"][path]["get"]
    backend_operation = backend["paths"][path]["get"]

    assert ai_operation == backend_operation
    assert ai_operation["operationId"] == "getB13ReplayObservation"
    assert ai_operation["x-contract-version"] == "C4-v2"
    assert ai_operation["x-change-request"] == "CR-012"
    assert ai_operation["x-current-runtime-status"] == "unexposed"
    assert ai_operation["parameters"][0]["schema"]["pattern"] == (
        r"^replay:[A-Z]+:date:[0-9]{4}-[0-9]{2}-[0-9]{2}$"
    )
    assert set(ai_operation["responses"]) == {"200", "400", "404", "409", "503"}
    assert ai_operation["responses"]["400"]["description"].startswith("Malformed")
    assert "No exact" in ai_operation["responses"]["404"]["description"]
    assert "More than one" in ai_operation["responses"]["409"]["description"]
    assert "no partial" in ai_operation["responses"]["503"]["description"]
    assert ai_operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/ReplayObservationResult"
    )


def test_cr012_source_selector_and_c3_date_only_semantics_are_exact():
    ai = _spec(AI_SPEC)
    schemas = ai["components"]["schemas"]
    provenance = schemas["ReplaySourceProvenance"]
    source = schemas["ReplaySourceObservation"]
    props = source["properties"]

    assert props["event_id"]["const"] == EVENT_ID
    assert props["source_date"]["const"] == "2015-12-01"
    assert props["observed_at"]["type"] == "null"
    assert props["observation_timezone"]["const"] == "unknown"
    assert props["received_at"]["format"] == "date-time"
    assert "Actual ingestion time" in props["received_at"]["description"]
    assert props["raw_source_row"]["properties"]["Date"]["const"] == "01-12-2015"
    assert props["raw_source_row"]["properties"]["POONDI"]["const"] == "2745.00"
    assert provenance["properties"]["archive_sha256"]["const"] == ARCHIVE_SHA256
    assert provenance["properties"]["member_sha256"]["const"] == MEMBER_SHA256
    assert provenance["properties"]["csv_physical_line"]["const"] == 4354
    assert provenance["properties"]["raw_storage_value"]["const"] == "2745.00"
    assert "no independent hash" in CONTRACT.read_text(encoding="utf-8")


def test_replay_identity_is_stable_and_derived_output_is_never_historical():
    ai = _spec(AI_SPEC)
    schemas = ai["components"]["schemas"]
    identity = schemas["ReplayRunIdentity"]
    assert identity["properties"]["replay_run_id"]["pattern"] == r"^sha256:[a-f0-9]{64}$"
    identity_description = identity["properties"]["replay_run_id"]["description"]
    assert "normalized_input_sha256" in identity_description
    assert "Excludes received_at/wall-clock time" in identity_description
    assert identity["properties"]["algorithm_id"]["const"] == "trackb-rule-v1"

    output = schemas["ReplayDerivedOutput"]
    assert {branch["properties"]["status"]["const"] for branch in output["oneOf"]} == {
        "produced",
        "not_produced",
    }
    no_output = next(branch for branch in output["oneOf"] if branch["properties"]["status"]["const"] == "not_produced")
    assert no_output["properties"]["alert"]["type"] == "null"
    assert no_output["properties"]["output_sha256"]["type"] == "null"

    alert = schemas["ReplayDerivedAlert"]["properties"]
    assert alert["source"]["const"] == "replay"
    assert alert["observed_at"]["type"] == "null"
    assert alert["valid_from"]["type"] == "null"
    assert alert["valid_to"]["type"] == "null"
    assert "not a calibrated probability" in alert["confidence"]["description"]
    assert schemas["ReplaySourceProvenance"]["properties"]["rainfall_unit_status"]["const"] == (
        "INFERRED; original unit unspecified"
    )
    assert "not historically observed" in ai["paths"]["/replay-alerts/{event_id}"]["get"]["description"]


def test_frozen_contracts_and_unavailable_legacy_operations_are_unchanged():
    ai = _spec(AI_SPEC)
    backend = _spec(BACKEND_SPEC)
    state = json.loads((ROOT / "docs/master/STATE.json").read_text(encoding="utf-8"))
    c4 = next(contract for contract in state["contracts"] if contract["id"] == "C4")
    assert c4["version"] == "v0" and c4["status"] == "frozen"
    assert ai["paths"]["/route"]["post"]["x-current-runtime-status"] == 501
    assert backend["paths"]["/routes"]["post"]["x-current-runtime-status"] == "unexposed"
    assert ai["paths"]["/route-results/{result_id}"]["get"]["x-contract-version"] == "C4-v1"
    assert "/replay-alerts/{event_id}" in ai["paths"]
    assert "/replay-alerts/{event_id}" in backend["paths"]
