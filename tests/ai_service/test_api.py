"""Contract and behavior tests for the AI-service scaffold."""

import json
import sys
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
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
            "source_crs": "EPSG:4326",
            "target_srid": 32644,
            "loaded_row_count": 42,
            "units": {"length_m": "m"},
            "zoom": {"min": 0, "max": 22},
            "attribution": "OpenStreetMap attribution",
            "vintage": None,
            "provenance": {"source_sha256": "a" * 64, "source_url": None},
            "nodata": "not_declared_in_catalogue",
            "tile_endpoint_available": False,
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


def test_route_request_requires_timezone_and_serializes_as_utc() -> None:
    request = main.RouteRequest.model_validate({
        "run_id": 7,
        "departure_at": "2026-10-25T08:00:00+05:30",
        "origin": "A",
        "destination": "B",
        "mode": "walking",
        "minimum_accessibility_probability": 0.7,
    })
    assert request.model_dump(mode="json")["departure_at"] == "2026-10-25T02:30:00Z"
    assert request.minimum_accessibility_probability == 0.7

    with pytest.raises(ValidationError, match="explicit UTC offset"):
        main.RouteRequest.model_validate({
            "run_id": 7,
            "departure_at": "2026-10-25T08:00:00",
            "origin": "A",
            "destination": "B",
        })


def test_route_response_rejects_unbounded_probability_in_owner_output_shape() -> None:
    route = _owner_fixture("a09_route_found.json")
    route["route_accessibility_probability"] = 1.1
    with pytest.raises(ValidationError):
        main.RouteResponse.model_validate(route)


def test_route_endpoint_stays_501_until_implemented() -> None:
    response = client.post("/route", json={
        "run_id": 7,
        "departure_at": "2026-10-25T08:00:00+05:30",
        "origin": "A",
        "destination": "B",
    })
    assert response.status_code == 501


OWNER_FIXTURES = ROOT / "services" / "backend" / "src" / "test" / "resources" / "owner-fixtures"


def _owner_fixture(name: str) -> dict[str, object]:
    return json.loads((OWNER_FIXTURES / name).read_text(encoding="utf-8"))


def test_a07_owner_impact_fixture_round_trips_instantaneous_simulated_result() -> None:
    impact = main.ImpactResult.model_validate(_owner_fixture("a07_impact_v4.json"))
    payload = impact.model_dump(mode="json")

    assert payload["schema_id"] == "twinguard.impact_result"
    assert payload["source_mode"] == "SIMULATED"
    assert payload["aggregation_interval"] is None
    assert "INSTANTANEOUS" in payload["aggregation_basis"]
    assert payload["metrics"]["population_exposed_people"]["unit"] == "people"
    assert payload["coverage"]["population"]["nodata_count"] > 0
    assert "WORLDPOP_NOData_NOT_ZERO" in payload["qc_flags"]
    assert payload["provenance"]["sources"]


@pytest.mark.parametrize(
    ("fixture", "status", "topological", "probability", "distance"),
    [
        ("a09_route_found.json", "ROUTE_FOUND", True, 1.0, True),
        ("a09_no_topological_path.json", "NO_TOPOLOGICAL_PATH", False, None, False),
        ("a09_insufficient_coverage.json", "INSUFFICIENT_HAZARD_COVERAGE", True, None, True),
    ],
)
def test_a09_owner_route_fixtures_preserve_route_status_and_missingness(
    fixture: str, status: str, topological: bool, probability: float | None, distance: bool
) -> None:
    route = main.RouteResponse.model_validate(_owner_fixture(fixture))
    payload = route.model_dump(mode="json")

    assert payload["status"] == status
    assert payload["source_mode"] == "SIMULATED"
    assert payload["topologically_reachable"] is topological
    assert payload["route_accessibility_probability"] == probability
    assert (payload["distance_m"] is not None) is distance
    assert payload["edge_coverage"]["unassessed_edge_count"] >= 0
    assert isinstance(payload["qc_flags"], list)
