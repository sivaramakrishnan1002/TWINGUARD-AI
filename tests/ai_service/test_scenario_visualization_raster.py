"""CR-010 exact, bounded raster-byte reads for saved A20 slices."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest
import rasterio
from fastapi.testclient import TestClient
from rasterio.io import MemoryFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/ai-service"))

from app.main import app
from app.scenario_visualization.raster_repository import ScenarioRasterRepository
from app.scenario_visualization.repository import (
    InvalidScenarioSelector,
    ScenarioAssetNotFound,
    ScenarioAssetsUnavailable,
    ScenarioIdentityConflict,
)
from app.scenario_visualization.raster_router import get_scenario_raster_repository


MANIFEST_PATH = ROOT / "data/features/visualization3d/batch2_v1/manifest.json"
RASTER_PATH = "/scenario-visualization-assets/{event_id}/{scenario_id}/raster"


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _request(client: TestClient, *, band: str = "p50", event_id: str | None = None, extra=None):
    series = _manifest()["scenario_series"][0]
    saved = series["slices"][0]
    path = RASTER_PATH.format(event_id=event_id or series["event_id"], scenario_id=series["scenario_id"])
    params = {"valid_time_utc": saved["valid_time_utc"], "band": band}
    if extra:
        params.update(extra)
    return client.get(path, params=params)


def test_exact_saved_band_returns_original_float32_geotiff_bytes_and_mask() -> None:
    manifest = _manifest()
    series = manifest["scenario_series"][0]
    saved = series["slices"][0]
    client = TestClient(app)
    try:
        for band in ("p05", "p50", "p95"):
            ref = saved["bands"][band]
            source = ROOT / ref["path"]
            response = client.get(
                RASTER_PATH.format(event_id=series["event_id"], scenario_id=series["scenario_id"]),
                params={"valid_time_utc": saved["valid_time_utc"], "band": band},
                headers={"Accept": "image/tiff"},
            )
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("image/tiff")
            assert response.headers["etag"] == f'"{ref["sha256"]}"'
            assert response.content == source.read_bytes()
            assert len(response.content) == ref["size_bytes"]
            assert hashlib.sha256(response.content).hexdigest() == ref["sha256"]
            with MemoryFile(response.content) as memory, memory.open() as raster, rasterio.open(source) as original:
                assert raster.count == 1 and raster.dtypes == ("float32",)
                assert raster.crs.to_string() == manifest["grid"]["crs"] == "EPSG:32644"
                assert (raster.width, raster.height) == (69, 88)
                affine = manifest["grid"]["affine_transform"]
                assert raster.transform.to_gdal() == (affine[2], affine[0], affine[1], affine[5], affine[3], affine[4])
                assert raster.nodata == manifest["nodata"]["value"] == -9999.0
                assert raster.read(1).tobytes() == original.read(1).tobytes()
                assert raster.read_masks(1).tobytes() == original.read_masks(1).tobytes()
    finally:
        client.close()


@pytest.mark.parametrize(
    ("time_value", "band", "expected"),
    [
        ("2015-11-30T06:00:00", "p50", 400),
        ("2015-11-30T06:00:00+00:00", "p50", 400),
        ("2015-11-30T06:00:00Z", "mean", 400),
        ("2015-11-30T07:00:00Z", "p50", 404),
    ],
)
def test_invalid_or_unsaved_selector_fails_without_raster_body(time_value, band, expected):
    series = _manifest()["scenario_series"][0]
    client = TestClient(app)
    response = client.get(
        RASTER_PATH.format(event_id=series["event_id"], scenario_id=series["scenario_id"]),
        params={"valid_time_utc": time_value, "band": band},
    )
    assert response.status_code == expected
    assert response.headers["content-type"].startswith("application/json")
    assert "image/tiff" not in response.headers["content-type"]


def test_unexpected_duplicate_and_body_inputs_are_400():
    series = _manifest()["scenario_series"][0]
    path = RASTER_PATH.format(event_id=series["event_id"], scenario_id=series["scenario_id"])
    saved = series["slices"][0]
    client = TestClient(app)
    extra = client.get(path, params={"valid_time_utc": saved["valid_time_utc"], "band": "p50", "path": "x"})
    body = client.request("GET", path, params={"valid_time_utc": saved["valid_time_utc"], "band": "p50"}, content=b"x")
    assert extra.status_code == body.status_code == 400
    assert extra.json()["code"] == body.json()["code"] == "INVALID_SCENARIO_SELECTOR"


def test_unavailable_changed_path_and_hash_fail_503_without_partial_body(monkeypatch: pytest.MonkeyPatch):
    repository = ScenarioRasterRepository(ROOT)
    manifest = _manifest()
    series = manifest["scenario_series"][0]
    saved = series["slices"][0]

    def changed_manifest():
        bad = copy.deepcopy(manifest)
        bad["scenario_series"][0]["slices"][0]["bands"]["p50"]["sha256"] = "0" * 64
        return bad

    monkeypatch.setattr(repository.assets, "_validated_manifest", changed_manifest)
    app.dependency_overrides[get_scenario_raster_repository] = lambda: repository
    try:
        path = RASTER_PATH.format(event_id=series["event_id"], scenario_id=series["scenario_id"])
        response = TestClient(app).get(path, params={"valid_time_utc": saved["valid_time_utc"], "band": "p50"})
    finally:
        app.dependency_overrides.pop(get_scenario_raster_repository, None)
    assert response.status_code == 503
    assert response.json()["code"] == "SCENARIO_VISUALIZATION_UNAVAILABLE"
    assert response.headers["content-type"].startswith("application/json")
    assert "private" not in response.text and "data/features" not in response.text


@pytest.mark.parametrize("mutation", ["missing", "outside_root", "duplicate", "metadata"])
def test_invalid_manifest_asset_fails_closed_without_partial_body(monkeypatch: pytest.MonkeyPatch, mutation: str):
    manifest = _manifest()
    series = manifest["scenario_series"][0]
    saved = series["slices"][0]
    reference = saved["bands"]["p50"]
    if mutation == "missing":
        reference["path"] = "data/features/forecast/batch2_v1/does-not-exist.tif"
    elif mutation == "outside_root":
        reference["path"] = "data/features/forecast/../../private.tif"
    elif mutation == "duplicate":
        manifest["scenario_series"].append(copy.deepcopy(series))
    else:
        reference["grid"]["crs"] = "EPSG:4326"

    repository = ScenarioRasterRepository(ROOT)
    monkeypatch.setattr(repository.assets, "_validated_manifest", lambda: manifest)
    app.dependency_overrides[get_scenario_raster_repository] = lambda: repository
    try:
        response = TestClient(app).get(
            RASTER_PATH.format(event_id=series["event_id"], scenario_id=series["scenario_id"]),
            params={"valid_time_utc": saved["valid_time_utc"], "band": "p50"},
        )
    finally:
        app.dependency_overrides.pop(get_scenario_raster_repository, None)
    assert response.status_code == (409 if mutation == "duplicate" else 503)
    assert response.content.startswith(b"{")
    assert "image/tiff" not in response.headers.get("content-type", "")


@pytest.mark.parametrize(
    ("replacement", "exception"),
    [
        ({"scenario_series": []}, ScenarioAssetNotFound),
        ({"scenario_series": [{"event_id": "2015-12-02", "scenario_id": "perfect_foresight_imerg"}] * 2}, ScenarioIdentityConflict),
        ({"scenario_series": []}, ScenarioAssetsUnavailable),
    ],
)
def test_repository_error_types_are_fail_closed(replacement, exception):
    repository = ScenarioRasterRepository(ROOT)
    if exception is ScenarioAssetsUnavailable:
        repository.assets._validated_manifest = lambda: (_ for _ in ()).throw(ScenarioAssetsUnavailable("private"))
    else:
        manifest = _manifest()
        manifest["scenario_series"] = replacement["scenario_series"]
        repository.assets._validated_manifest = lambda: manifest
    if exception is ScenarioAssetNotFound:
        with pytest.raises(ScenarioAssetNotFound):
            repository.read("2015-12-02", "perfect_foresight_imerg", "2015-11-30T06:00:00Z", "p50")
    elif exception is ScenarioIdentityConflict:
        with pytest.raises(ScenarioIdentityConflict):
            repository.read("2015-12-02", "perfect_foresight_imerg", "2015-11-30T06:00:00Z", "p50")
    else:
        with pytest.raises(ScenarioAssetsUnavailable):
            repository.read("2015-12-02", "perfect_foresight_imerg", "2015-11-30T06:00:00Z", "p50")


def test_openapi_projects_exact_raster_operation_and_c9_v1_error_semantics():
    generated_spec = app.openapi()
    if RASTER_PATH not in generated_spec["paths"]:
        app.openapi_schema = None
        generated_spec = app.openapi()
    generated = generated_spec["paths"][RASTER_PATH]["get"]
    assert generated["operationId"] == "getScenarioVisualizationRaster"
    assert {p["name"] for p in generated["parameters"]} == {"event_id", "scenario_id", "valid_time_utc", "band"}
    assert generated["responses"]["200"]["content"]["image/tiff"]["schema"] == {
        "type": "string", "format": "binary"
    }
    assert {"400", "404", "409", "503", "501"} <= set(generated["responses"])
