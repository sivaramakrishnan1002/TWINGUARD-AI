"""B17 read-only checks against the owner-produced A20 scenario manifest."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/ai-service"))
sys.path.insert(0, str(ROOT / "tests/master"))
MANIFEST_PATH = ROOT / "data/features/visualization3d/batch2_v1/manifest.json"

from app.main import app
from app.scenario_visualization import (
    InvalidScenarioSelector,
    ScenarioAssetNotFound,
    ScenarioAssetRepository,
    ScenarioAssetsUnavailable,
    ScenarioIdentityConflict,
)
from test_scenario_visualization_contract import _resolved_schema, _validate_schema


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _raster_refs(manifest: dict):
    for series in manifest["scenario_series"]:
        for saved in series["slices"]:
            yield from saved["bands"].values()
    for context in manifest["context_layers"]:
        yield from context["bands"].values()


def test_catalog_is_a_bounded_exact_manifest_projection_and_all_asset_hashes_match() -> None:
    manifest = _manifest()
    catalog = ScenarioAssetRepository(ROOT).catalog()
    assert set(catalog) == {
        "schema_version", "artifact_version", "status", "grid", "depth_units", "nodata",
        "provenance", "scenario_series", "context_layers", "limitations", "presentation_policy", "time_basis",
    }
    assert catalog["schema_version"] == manifest["schema_version"] == "1.0.0"
    assert catalog["artifact_version"] == manifest["artifact_version"] == "batch2_v1"
    assert catalog["status"] == "DERIVED_ASSUMPTION_BASED_RESEARCH_SCENARIO"
    assert catalog["grid"] == manifest["grid"]
    assert catalog["depth_units"] == manifest["depth_units"]
    assert catalog["nodata"] == manifest["nodata"]
    assert catalog["provenance"] == manifest["provenance"]
    assert catalog["context_layers"] == manifest["context_layers"]
    assert len(catalog["scenario_series"]) == 3
    for projected, source in zip(catalog["scenario_series"], manifest["scenario_series"], strict=True):
        assert projected == {
            **{key: source[key] for key in (
                "event_id", "scenario_id", "source_mode", "window_start_utc", "window_end_utc_inclusive",
                "member_count", "rainfall_semantics", "band_semantics",
            )},
            "saved_times_utc": [saved["valid_time_utc"] for saved in source["slices"]],
        }

    refs = list(_raster_refs(manifest))
    assert len(refs) == 57
    assert sum(ref["size_bytes"] for ref in refs) < 1024 * 1024
    for ref in refs:
        path = ROOT / ref["path"]
        assert path.stat().st_size == ref["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == ref["sha256"]
        with rasterio.open(path) as raster:
            assert raster.crs.to_string() == manifest["grid"]["crs"]
            assert (raster.width, raster.height) == (manifest["grid"]["width"], manifest["grid"]["height"])
            assert raster.nodata == manifest["nodata"]["value"]
            mask = raster.read_masks(1)
            assert int((mask != 0).sum()) == ref["valid_cell_count"]
            assert int((mask == 0).sum()) == ref["nodata_cell_count"]
        assert "not dry" in ref["nodata_meaning"].lower()
        assert ref["band_units_metadata"] is None


def test_exact_detail_preserves_source_times_parameter_spread_and_unknown_coverage() -> None:
    manifest = _manifest()
    saved = manifest["scenario_series"][0]
    asset = ScenarioAssetRepository(ROOT).asset(saved["event_id"], saved["scenario_id"])
    assert set(asset) == {
        "schema_version", "artifact_version", "status", "grid", "depth_units", "nodata", "provenance",
        "limitations", "presentation_policy", "time_basis", "series",
    }
    assert asset["series"] == saved
    assert asset["series"]["source_mode"] == "PERFECT_FORESIGHT_HINDCAST"
    assert [item["valid_time_utc"] for item in asset["series"]["slices"]] == [
        item["valid_time_utc"] for item in saved["slices"]
    ]
    assert asset["series"]["member_count"] == 20
    assert "not calibrated statistical uncertainty" in asset["series"]["band_semantics"]
    assert asset["nodata"]["meaning"].endswith("unknown coverage, not dry")
    peak = next(row for row in manifest["context_layers"] if row["temporal_kind"] == "per_cell_event_peak")
    assert peak["valid_time_utc"] is None
    assert peak["selected_hour_index_zero_based"] is None


def test_runtime_metadata_projections_conform_to_both_c9_schema_projections() -> None:
    repository = ScenarioAssetRepository(ROOT)
    catalog = repository.catalog()
    for filename in ("ai-service.yaml", "backend.yaml"):
        spec = json.loads((ROOT / "docs/api" / filename).read_text(encoding="utf-8"))
        _validate_schema(_resolved_schema(spec, "ScenarioVisualizationCatalog"), catalog, spec)
        for summary in catalog["scenario_series"]:
            detail = repository.asset(summary["event_id"], summary["scenario_id"])
            _validate_schema(_resolved_schema(spec, "ScenarioVisualizationAsset"), detail, spec)


@pytest.mark.parametrize(
    ("event_id", "scenario_id"),
    [("2015-2-1", "perfect_foresight_imerg"), ("../2015-11-12", "perfect_foresight_imerg"),
     ("2015-11-12", "../manifest")],
)
def test_invalid_selectors_are_rejected_without_path_interpretation(event_id: str, scenario_id: str) -> None:
    with pytest.raises(InvalidScenarioSelector):
        ScenarioAssetRepository(ROOT).asset(event_id, scenario_id)


def test_unknown_exact_selector_is_not_substituted() -> None:
    with pytest.raises(ScenarioAssetNotFound):
        ScenarioAssetRepository(ROOT).asset("2015-11-12", "not-a20-scenario")


def test_oversized_or_unavailable_manifest_fails_closed(tmp_path: Path) -> None:
    data = tmp_path / "data/features/visualization3d/batch2_v1"
    data.mkdir(parents=True)
    (data / "manifest.json").write_bytes(b"{" + b" " * (256 * 1024))
    with pytest.raises(ScenarioAssetsUnavailable):
        ScenarioAssetRepository(tmp_path).catalog()


def test_manifest_asset_path_cannot_escape_project_root(tmp_path: Path) -> None:
    data = tmp_path / "data/features/visualization3d/batch2_v1"
    data.mkdir(parents=True)
    malicious = {
        "schema_version": "1.0.0",
        "artifact_version": "batch2_v1",
        "status": "DERIVED_ASSUMPTION_BASED_RESEARCH_SCENARIO",
        "scenario_series": [{"slices": [{"bands": {"mean": {
            "path": "../outside.tif", "size_bytes": 10, "sha256": "0" * 64,
        }}}]}],
        "context_layers": [],
    }
    (data / "manifest.json").write_text(json.dumps(malicious), encoding="utf-8")
    with pytest.raises(ScenarioAssetsUnavailable):
        ScenarioAssetRepository(tmp_path).catalog()


def test_manifest_timestamps_must_be_explicit_utc_and_saved_as_recorded(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest["scenario_series"][0]["slices"][0]["valid_time_utc"] = "2015-11-30T06:00:00"
    path = tmp_path / "data/features/visualization3d/batch2_v1/manifest.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ScenarioAssetsUnavailable):
        ScenarioAssetRepository(tmp_path).catalog()


def test_duplicate_manifest_identity_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    repository = ScenarioAssetRepository(ROOT)
    duplicate = {"event_id": "2015-11-12", "scenario_id": "perfect_foresight_imerg"}
    manifest = {"scenario_series": [duplicate, duplicate]}
    monkeypatch.setattr(repository, "_validated_manifest", lambda: manifest)
    with pytest.raises(ScenarioIdentityConflict):
        repository.asset("2015-11-12", "perfect_foresight_imerg")


def test_approved_c9_http_operations_are_mounted_as_get_routes_only() -> None:
    paths = set(app.openapi()["paths"])
    assert "/scenario-visualization-assets" in paths
    assert "/scenario-visualization-assets/{event_id}/{scenario_id}" in paths
    assert set(app.openapi()["paths"]["/scenario-visualization-assets"]) == {"get"}
    assert set(app.openapi()["paths"]["/scenario-visualization-assets/{event_id}/{scenario_id}"]) == {"get"}

