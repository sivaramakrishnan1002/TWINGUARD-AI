"""B21 HTTP behavior for the CR-009 read-only C9 operations."""

from __future__ import annotations

import copy
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/ai-service"))
sys.path.insert(0, str(ROOT / "tests/master"))

from app.main import app
from app.scenario_visualization import ScenarioAssetRepository, ScenarioAssetsUnavailable
from app.scenario_visualization.router import get_scenario_asset_repository
from test_scenario_visualization_contract import _resolved_schema, _validate_schema


MANIFEST = ROOT / "data/features/visualization3d/batch2_v1/manifest.json"
CATALOG_PATH = "/scenario-visualization-assets"
DETAIL_PATH = "/scenario-visualization-assets/{event_id}/{scenario_id}"


@contextmanager
def _client(repository: ScenarioAssetRepository) -> Iterator[TestClient]:
    app.dependency_overrides[get_scenario_asset_repository] = lambda: repository
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_scenario_asset_repository, None)


def _contract(filename: str = "ai-service.yaml") -> dict:
    return json.loads((ROOT / "docs/api" / filename).read_text(encoding="utf-8"))


def test_catalog_and_exact_detail_return_schema_conformant_saved_research_metadata() -> None:
    repository = ScenarioAssetRepository(ROOT)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    spec = _contract()
    with _client(repository) as client:
        catalog_response = client.get(CATALOG_PATH)
        assert catalog_response.status_code == 200
        catalog = catalog_response.json()
        _validate_schema(_resolved_schema(spec, "ScenarioVisualizationCatalog"), catalog, spec)
        assert catalog["status"] == "DERIVED_ASSUMPTION_BASED_RESEARCH_SCENARIO"
        assert catalog["nodata"]["meaning"].endswith("unknown coverage, not dry")
        assert catalog["scenario_series"][0]["source_mode"] == "PERFECT_FORESIGHT_HINDCAST"

        source = manifest["scenario_series"][0]
        detail_response = client.get(f"{CATALOG_PATH}/{source['event_id']}/{source['scenario_id']}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        _validate_schema(_resolved_schema(spec, "ScenarioVisualizationAsset"), detail, spec)
        assert detail["series"] == source
        assert [item["valid_time_utc"] for item in detail["series"]["slices"]] == [
            item["valid_time_utc"] for item in source["slices"]
        ]
        assert detail["provenance"] == manifest["provenance"]
        assert detail["depth_units"]["value"] == "m"
        assert not any(isinstance(value, str) and value.startswith("data:image/") for value in detail.values())


@pytest.mark.parametrize(
    "path",
    [
        f"{CATALOG_PATH}/2015-02-30/perfect_foresight_imerg",
        f"{CATALOG_PATH}/2015-11-12/bad%20scenario",
    ],
)
def test_invalid_detail_selector_is_400(path: str) -> None:
    with _client(ScenarioAssetRepository(ROOT)) as client:
        response = client.get(path)
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_SCENARIO_SELECTOR"
    assert "scenario_series" not in response.text


def test_unexpected_query_input_is_400() -> None:
    with _client(ScenarioAssetRepository(ROOT)) as client:
        response = client.get(CATALOG_PATH, params={"source": "live"})
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_SCENARIO_SELECTOR"


def test_request_body_input_is_rejected_without_being_parsed() -> None:
    with _client(ScenarioAssetRepository(ROOT)) as client:
        response = client.request("GET", CATALOG_PATH, content=b"untrusted")
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_SCENARIO_SELECTOR"


def test_no_exact_detail_identity_is_404() -> None:
    with _client(ScenarioAssetRepository(ROOT)) as client:
        response = client.get(f"{CATALOG_PATH}/2015-11-12/not-a-saved-scenario")
    assert response.status_code == 404
    assert response.json()["code"] == "SCENARIO_ASSET_NOT_FOUND"
    assert "series" not in response.text


def test_duplicate_catalog_and_detail_identity_map_to_409_without_partial_results(tmp_path: Path) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["scenario_series"][1] = copy.deepcopy(manifest["scenario_series"][0])
    manifest_path = tmp_path / "data/features/visualization3d/batch2_v1/manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    repository = ScenarioAssetRepository(tmp_path)
    with _client(repository) as client:
        catalog = client.get(CATALOG_PATH)
        detail = client.get(f"{CATALOG_PATH}/2015-12-02/perfect_foresight_imerg")
    for response in (catalog, detail):
        assert response.status_code == 409
        assert response.json()["code"] == "SCENARIO_IDENTITY_CONFLICT"
        assert "scenario_series" not in response.text and "series" not in response.text


def test_unavailable_manifest_or_asset_maps_to_503_without_partial_result(monkeypatch: pytest.MonkeyPatch) -> None:
    repository = ScenarioAssetRepository(ROOT)

    def unavailable():
        raise ScenarioAssetsUnavailable("private local path must not be returned")

    monkeypatch.setattr(repository, "_validated_manifest", unavailable)
    with _client(repository) as client:
        catalog = client.get(CATALOG_PATH)
        detail = client.get(f"{CATALOG_PATH}/2015-12-02/perfect_foresight_imerg")
    for response in (catalog, detail):
        assert response.status_code == 503
        assert response.json()["code"] == "SCENARIO_VISUALIZATION_UNAVAILABLE"
        assert "private local path" not in response.text
        assert "scenario_series" not in response.text and "series" not in response.text


def test_openapi_projects_only_the_two_approved_get_operations() -> None:
    spec = _contract()
    generated = app.openapi()
    for path, operation_id in (
        (CATALOG_PATH, "listScenarioVisualizationAssets"),
        (DETAIL_PATH, "getScenarioVisualizationAsset"),
    ):
        documented = spec["paths"][path]["get"]
        runtime = generated["paths"][path]["get"]
        assert runtime["operationId"] == operation_id
        assert set(documented["responses"]).issubset(runtime["responses"])
        assert all(method == "get" for method in generated["paths"][path])


def test_b11_mounts_only_a20_referenced_asset_directories_read_only() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.b11.yml").read_text(encoding="utf-8"))
    expected = {
        "./data/features/visualization3d/batch2_v1": "/app/data/features/visualization3d/batch2_v1",
        "./data/features/forecast/batch2_v1": "/app/data/features/forecast/batch2_v1",
        "./data/features/simulation/batch2_v1": "/app/data/features/simulation/batch2_v1",
    }
    for service in ("ai-service", "backend"):
        mounts = compose["services"][service]["volumes"]
        selected = {mount["source"]: mount["target"] for mount in mounts if mount["source"] in expected}
        assert selected == expected
        assert all(mount["read_only"] is True and mount["type"] == "bind" for mount in mounts if mount["source"] in expected)
        assert "volumes" not in compose
