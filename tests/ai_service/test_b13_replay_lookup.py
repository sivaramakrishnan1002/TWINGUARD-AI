"""CR-012 bounded source observation replay projection tests."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "ai-service"))

from app import main  # noqa: E402

client = TestClient(main.app)


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def test_exact_archive_selector_hashes_and_date_only_semantics() -> None:
    archive = ROOT / "data/raw/reservoirs/kaggle_chennai_water_management/archive.zip"
    raw_archive = archive.read_bytes()
    assert hashlib.sha256(raw_archive).hexdigest() == "7645febde7ccc21871200487139d1c8a84ea90a6dd2eccc93b7d1f06faf69197"
    with zipfile.ZipFile(io.BytesIO(raw_archive)) as source:
        level_bytes = source.read("chennai_reservoir_levels.csv")
        assert hashlib.sha256(level_bytes).hexdigest() == "3b4b6f2f53b5db20513d2829c2dba265c5738a55bf0c8eade51e0e2d5cfeaef7"
        rows = list(csv.DictReader(io.StringIO(level_bytes.decode("utf-8-sig"))))
    candidates = [(line, row) for line, row in enumerate(rows, start=2) if row["Date"] == "01-12-2015" and row["POONDI"] == "2745.00"]
    assert len(candidates) == 1 and candidates[0][0] == 4354
    before = hashlib.sha256(archive.read_bytes()).hexdigest()
    response = client.get(f"/replay-alerts/{main.REPLAY_EVENT_ID}")
    assert response.status_code == 200
    payload = response.json()
    source = payload["source_observation"]
    assert payload["contract_version"] == "C4-v2"
    assert source["event_id"] == main.REPLAY_EVENT_ID
    assert source["source_mode"] == "REPLAY"
    assert source["raw_source_row"] == {"Date": "01-12-2015", "POONDI": "2745.00"}
    assert source["source_date"] == "2015-12-01"
    assert source["observed_at"] is None and source["observation_timezone"] == "unknown"
    assert source["received_at"].endswith("Z")
    assert source["provenance"]["archive_sha256"] == before
    assert payload["replay"]["configuration_sha256"] == main.REPLAY_CONFIG_SHA256
    assert len(payload["replay"]["context_inputs"]) == 3
    assert response.json()["derived_output"]["status"] in {"produced", "not_produced"}
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == before


def test_replay_run_identity_is_stable_and_output_hash_is_real() -> None:
    first = client.get(f"/replay-alerts/{main.REPLAY_EVENT_ID}").json()
    second = client.get(f"/replay-alerts/{main.REPLAY_EVENT_ID}").json()
    assert first["replay"]["replay_run_id"] == second["replay"]["replay_run_id"]
    assert first["replay"]["normalized_input_sha256"] == second["replay"]["normalized_input_sha256"]
    assert first["source_observation"]["received_at"] != second["source_observation"]["received_at"]
    output = first["derived_output"]
    if output["status"] == "produced":
        assert output["alert"]["observed_at"] is None
        assert output["alert"]["valid_from"] is None and output["alert"]["valid_to"] is None
        assert output["alert"]["received_at"] == first["source_observation"]["received_at"]
        assert output["output_sha256"] == canonical_hash(output["alert"])
        assert output["alert"]["level"] == "Warning"
        assert output["alert"]["trigger_inputs"]["rain_3d_mm"] == pytest.approx(86.7)
    else:
        assert output["alert"] is None and output["output_sha256"] is None


def test_invalid_absent_duplicate_and_corrupt_asset_fail_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    assert client.get("/replay-alerts/not-a-selector").status_code == 400
    assert client.get("/replay-alerts/replay:POONDI:date:2015-99-99").status_code == 400
    missing = client.get("/replay-alerts/replay:CHOLAVARAM:date:2015-12-01")
    assert missing.status_code == 404 and missing.json()["code"] == "not_found"

    fixture = main._load_b13_fixture()[0]
    monkeypatch.setattr(main, "_load_b13_fixture", lambda: (fixture, fixture))
    conflict = client.get(f"/replay-alerts/{main.REPLAY_EVENT_ID}")
    assert conflict.status_code == 409 and conflict.json()["code"] == "ambiguous_identity"

    monkeypatch.undo()
    corrupted = tmp_path / "corrupt.json"
    corrupted.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(main, "REPLAY_FIXTURE", corrupted)
    unavailable = client.get(f"/replay-alerts/{main.REPLAY_EVENT_ID}")
    assert unavailable.status_code == 503 and unavailable.json()["code"] == "asset_unavailable"
    assert "{}" not in unavailable.text


def test_no_output_schema_is_explicit_and_cannot_contain_fabricated_alert() -> None:
    output = main.ReplayDerivedOutput.model_validate({"status": "not_produced", "alert": None, "output_sha256": None})
    assert output.status == "not_produced"
    produced_alert = client.get(f"/replay-alerts/{main.REPLAY_EVENT_ID}").json()["derived_output"]["alert"]
    with pytest.raises(ValidationError, match="not_produced output must be null"):
        main.ReplayDerivedOutput.model_validate({"status": "not_produced", "alert": produced_alert, "output_sha256": None})


def test_api_is_read_only_and_openapi_matches_c4_v2(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import database

    def forbidden_database_access():
        raise AssertionError("B13 replay lookup must not access any database")

    monkeypatch.setattr(database, "_connect_read_only", forbidden_database_access)
    response = client.get(f"/replay-alerts/{main.REPLAY_EVENT_ID}")
    assert response.status_code == 200
    contract = json.loads((ROOT / "docs/api/ai-service.yaml").read_text(encoding="utf-8"))
    operation = contract["paths"]["/replay-alerts/{event_id}"]["get"]
    generated = main.app.openapi()["paths"]["/replay-alerts/{event_id}"]["get"]
    assert operation["operationId"] == generated["operationId"] == "getB13ReplayObservation"
    assert {"200", "400", "404", "409", "503"}.issubset(generated["responses"])
    assert operation["x-contract-version"] == "C4-v2"


def test_ai_cors_is_exact_for_b13_get() -> None:
    allowed = client.options(
        f"/replay-alerts/{main.REPLAY_EVENT_ID}",
        headers={"Origin": "http://127.0.0.1:8081", "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "Accept"},
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:8081"
    assert allowed.headers.get("access-control-allow-credentials") is None
    other_origin = client.options(f"/replay-alerts/{main.REPLAY_EVENT_ID}", headers={
        "Origin": "http://localhost:8081", "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "Accept",
    })
    assert "access-control-allow-origin" not in other_origin.headers
    other_method = client.options(f"/replay-alerts/{main.REPLAY_EVENT_ID}", headers={
        "Origin": "http://127.0.0.1:8081", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "Accept",
    })
    assert other_method.status_code == 400 and other_method.headers["access-control-allow-methods"] == "GET"
    other_header = client.options(f"/replay-alerts/{main.REPLAY_EVENT_ID}", headers={
        "Origin": "http://127.0.0.1:8081", "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "X-Other",
    })
    assert other_header.status_code == 400 and other_header.headers["access-control-allow-headers"] == "Accept"

