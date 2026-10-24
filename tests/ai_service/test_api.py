"""Contract and behavior tests for the AI-service scaffold."""

import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = ROOT / "services" / "ai-service"
sys.path.insert(0, str(SERVICE_DIR))

from app import main  # noqa: E402


client = TestClient(main.app)


def test_health_reports_process_available() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "twinguard-ai-service",
        "database": "not_checked",
    }


def test_layers_returns_mocked_read_only_catalogue(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        {
            "layer_key": "roads",
            "source_layer": "road_edges",
            "target_srid": 32644,
            "loaded_row_count": 42,
        }
    ]
    monkeypatch.setattr(main, "get_layer_records", lambda: rows)
    response = client.get("/layers")
    assert response.status_code == 200
    assert response.json() == rows


def test_layers_hides_database_exception_details(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail() -> list[dict[str, object]]:
        raise RuntimeError("sensitive connection details")

    monkeypatch.setattr(main, "get_layer_records", fail)
    response = client.get("/layers")
    assert response.status_code == 503
    assert "sensitive connection details" not in response.text


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        (
            "/forecast",
            {"event_key": "test", "issued_at": "2026-10-24T00:00:00Z", "horizon_hours": 3, "step_minutes": 15},
        ),
        ("/uncertainty", {"run_id": 1, "valid_at": "2026-10-24T00:00:00Z"}),
        ("/impact", {"run_id": 1, "valid_at": "2026-10-24T00:00:00Z"}),
        (
            "/route",
            {
                "run_id": 1,
                "departure_at": "2026-10-24T00:00:00Z",
                "origin": "a",
                "destination": "b",
            },
        ),
        ("/scenario", {"scenario_key": "test", "base_run_id": 1, "parameters": {}}),
    ],
)
def test_unimplemented_operations_return_501(path: str, payload: dict[str, object]) -> None:
    response = client.post(path, json=payload)
    assert response.status_code == 501
    assert "not implemented yet" in response.json()["detail"].lower()


def test_generated_openapi_matches_contract_routes_and_operation_ids() -> None:
    contract = json.loads((ROOT / "docs" / "api" / "ai-service.yaml").read_text(encoding="utf-8"))
    generated = main.app.openapi()
    assert generated["openapi"].startswith("3.1")
    for path, contract_item in contract["paths"].items():
        for method, contract_operation in contract_item.items():
            generated_operation = generated["paths"][path][method]
            assert generated_operation["operationId"] == contract_operation["operationId"]
            assert set(contract_operation["responses"]).issubset(generated_operation["responses"])
            if "requestBody" in contract_operation:
                contract_ref = contract_operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].split("/")[-1]
                generated_ref = generated_operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].split("/")[-1]
                assert generated_ref == contract_ref


def test_test_client_uses_httpx() -> None:
    assert isinstance(client, TestClient)
    assert httpx.__version__ == "0.28.1"
