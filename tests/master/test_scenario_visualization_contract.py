"""C9 OpenAPI projection and A20 manifest conformance; no runtime route is started."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import rasterio

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "data/features/visualization3d/batch2_v1/manifest.json"
AI_SPEC_PATH = ROOT / "docs/api/ai-service.yaml"
BACKEND_SPEC_PATH = ROOT / "docs/api/backend.yaml"
LIST_PATH = "/scenario-visualization-assets"
DETAIL_PATH = "/scenario-visualization-assets/{event_id}/{scenario_id}"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc(value: str) -> None:
    assert value.endswith("Z"), value
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def _resolved_schema(spec, name):
    return spec["components"]["schemas"][name]


def _validate_schema(schema, value, spec):
    """Small JSON Schema subset for the OpenAPI 3.1 shapes used by C9."""
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[1]
        return _validate_schema(_resolved_schema(spec, name), value, spec)
    if "const" in schema:
        assert value == schema["const"], (schema["const"], value)
    if "enum" in schema:
        assert value in schema["enum"], (schema["enum"], value)
    if "anyOf" in schema:
        errors = []
        for branch in schema["anyOf"]:
            try:
                _validate_schema(branch, value, spec)
                break
            except AssertionError as exc:
                errors.append(exc)
        else:
            raise AssertionError(f"value matches no anyOf branch: {errors}")
    if "oneOf" in schema:
        matches = 0
        for branch in schema["oneOf"]:
            try:
                _validate_schema(branch, value, spec)
                matches += 1
            except AssertionError:
                pass
        assert matches == 1, f"expected exactly one oneOf branch, got {matches}"
        return
    schema_type = schema.get("type")
    if schema_type == "null":
        assert value is None
    elif schema_type == "string":
        assert isinstance(value, str)
        if schema.get("format") == "date-time":
            _utc(value)
        if schema.get("format") == "date":
            datetime.strptime(value, "%Y-%m-%d")
        if "pattern" in schema:
            assert re.search(schema["pattern"], value)
    elif schema_type == "integer":
        assert isinstance(value, int) and not isinstance(value, bool)
        if "minimum" in schema:
            assert value >= schema["minimum"]
        if "maximum" in schema:
            assert value <= schema["maximum"]
    elif schema_type == "number":
        assert isinstance(value, (int, float)) and not isinstance(value, bool)
    elif schema_type == "boolean":
        assert isinstance(value, bool)
    elif schema_type == "object":
        assert isinstance(value, dict)
        assert set(schema.get("required", [])) <= set(value)
        if schema.get("additionalProperties") is False:
            assert set(value) <= set(schema["properties"])
        for key, child in schema.get("properties", {}).items():
            if key in value:
                _validate_schema(child, value[key], spec)
    elif schema_type == "array":
        assert isinstance(value, list)
        if "minItems" in schema:
            assert len(value) >= schema["minItems"]
        if "maxItems" in schema:
            assert len(value) <= schema["maxItems"]
        if "prefixItems" in schema:
            assert len(value) >= len(schema["prefixItems"])
            for child, item in zip(schema["prefixItems"], value):
                _validate_schema(child, item, spec)
        elif "items" in schema:
            for item in value:
                _validate_schema(schema["items"], item, spec)


def test_c9_paths_and_operation_ids_are_distinct_with_cr009_status_mappings():
    expected_responses = {
        LIST_PATH: {"200", "409", "501", "503"},
        DETAIL_PATH: {"200", "400", "404", "409", "501", "503"},
    }
    for spec_path in (AI_SPEC_PATH, BACKEND_SPEC_PATH):
        spec = _json(spec_path)
        assert LIST_PATH in spec["paths"]
        assert DETAIL_PATH in spec["paths"]
        assert "/scenario" in spec["paths"] if spec_path == AI_SPEC_PATH else "/scenarios" in spec["paths"]
        operations = []
        for route in (LIST_PATH, DETAIL_PATH):
            op = spec["paths"][route]["get"]
            operations.append(op["operationId"])
            assert op["x-runtime-availability"] == "available_in_local_B11_package"
            assert set(op["responses"]) == expected_responses[route]
            assert "CR-009" in op["description"] and "B21" in op["description"]
            assert "501" in op["responses"]  # reserved fallback; local B11 runtime is verified
            assert "200" in op["responses"]
        assert operations == ["listScenarioVisualizationAssets", "getScenarioVisualizationAsset"]
        all_ids = [op.get("operationId") for path_item in spec["paths"].values()
                   for method, op in path_item.items() if method in {"get", "post", "put", "delete"}]
        assert len(all_ids) == len(set(all_ids))
        assert "ScenarioVisualizationCatalog" in spec["paths"][LIST_PATH]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        assert "ScenarioVisualizationAsset" in spec["paths"][DETAIL_PATH]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        catalog_responses = spec["paths"][LIST_PATH]["get"]["responses"]
        assert "duplicate or ambiguous" in catalog_responses["409"]["description"]
        assert "no catalog result" in catalog_responses["409"]["description"]
        detail_responses = spec["paths"][DETAIL_PATH]["get"]["responses"]
        assert "Invalid" in detail_responses["400"]["description"]
        assert "No exact" in detail_responses["404"]["description"]
        assert "duplicate or ambiguous" in detail_responses["409"]["description"]
        assert "No partial result" in detail_responses["503"]["description"]
        if spec_path == AI_SPEC_PATH:
            assert spec["paths"][LIST_PATH]["get"]["x-current-runtime-status"] == 200
            assert spec["paths"][DETAIL_PATH]["get"]["x-current-runtime-status"] == 200
        else:
            assert spec["paths"][LIST_PATH]["get"]["x-current-runtime-status"] == 200
            assert spec["paths"][DETAIL_PATH]["get"]["x-current-runtime-status"] == 200


def test_cr010_raster_projection_is_additive_owner_approved_and_keeps_c9_unfrozen():
    path = "/scenario-visualization-assets/{event_id}/{scenario_id}/raster"
    ai = _json(AI_SPEC_PATH)
    backend = _json(BACKEND_SPEC_PATH)
    assert path in ai["paths"]
    assert path not in backend["paths"]
    op = ai["paths"][path]["get"]
    assert op["operationId"] == "getScenarioVisualizationRaster"
    assert op["x-contract-version"] == "C9-v1"
    assert op["x-runtime-availability"] == "available_in_local_B11_package"
    assert op["x-current-runtime-status"] == 200
    assert set(op["responses"]) == {"200", "400", "404", "409", "501", "503"}
    success = op["responses"]["200"]
    assert success["content"]["image/tiff"]["schema"] == {
        "type": "string", "format": "binary"
    }
    etag = success["headers"]["ETag"]["schema"]
    assert etag == {"type": "string", "pattern": '^"[0-9a-f]{64}"$'}
    assert "exact original" in success["description"].lower()
    assert "SHA-256" in success["description"] and "ETag" in success["description"]
    assert "invalid" in op["responses"]["400"]["description"].lower()
    assert "exact saved" in op["responses"]["404"]["description"]
    assert "duplicate or ambiguous" in op["responses"]["409"]["description"]
    assert "No partial" in op["responses"]["503"]["description"]
    assert "not observed in the verified local B11 runtime" in op["responses"]["501"]["description"]
    parameters = {p["name"]: p for p in op["parameters"]}
    assert set(parameters) == {"event_id", "scenario_id", "valid_time_utc", "band"}
    assert parameters["valid_time_utc"]["schema"]["pattern"].endswith("Z$")
    assert parameters["band"]["schema"]["enum"] == ["p05", "p50", "p95"]
    assert "CR-010" in op["description"]
    assert "B25 commit 0aebc59" in op["description"]
    assert "local B11 package" in ai["info"]["description"]
    assert "local B11 package" in backend["info"]["description"]
    assert "no backend raster operation" in backend["info"]["description"]
    assert "image/tiff" in (ROOT / "docs/master/contracts/c9_scenario_visualization_v1.md").read_text(encoding="utf-8")
    state = _json(ROOT / "docs/master/STATE.json")
    assert not any(contract["id"] == "C9" for contract in state["contracts"])
    c1_c8 = [c for c in state["contracts"] if c["id"] in {f"C{i}" for i in range(1, 9)}]
    assert len(c1_c8) == 8
    assert all(c["version"] == "v0" and c["status"] == "frozen" for c in c1_c8)


def test_c9_schemas_match_manifest_grid_units_and_null_semantics():
    manifest = _json(MANIFEST_PATH)
    expected_grid = manifest["grid"]
    for path in (AI_SPEC_PATH, BACKEND_SPEC_PATH):
        spec = _json(path)
        grid = _resolved_schema(spec, "ScenarioVisualizationGrid")
        assert grid["properties"]["crs"]["const"] == expected_grid["crs"]
        assert grid["properties"]["width"]["const"] == expected_grid["width"]
        assert grid["properties"]["height"]["const"] == expected_grid["height"]
        assert grid["properties"]["pixel_size_m"]["prefixItems"][0]["const"] == expected_grid["pixel_size_m"][0]
        assert grid["properties"]["affine_transform"]["prefixItems"] == [
            {"type": "number", "const": value} for value in expected_grid["affine_transform"]
        ]
        units = _resolved_schema(spec, "ScenarioVisualizationDepthUnits")
        assert units["properties"]["value"]["const"] == manifest["depth_units"]["value"]
        assert "unset" in units["properties"]["metadata_note"]["const"].lower()
        context = _resolved_schema(spec, "ScenarioVisualizationContextLayer")
        valid_time = context["properties"]["valid_time_utc"]
        assert {"type": "null"} in valid_time["anyOf"]
        assert context["properties"]["temporal_kind"]["enum"] == ["selected_hour", "per_cell_event_peak"]

        raster = _resolved_schema(spec, "ScenarioVisualizationRasterReference")
        assert raster["properties"]["sha256"]["pattern"] == "^[0-9a-f]{64}$"
        assert raster["properties"]["units"]["const"] == manifest["depth_units"]["value"]
        assert raster["properties"]["band_units_metadata"]["anyOf"][-1] == {"type": "null"}


def test_c9_manifest_times_members_masks_hashes_and_provenance_are_exact():
    manifest = _json(MANIFEST_PATH)
    assert manifest["schema_version"] == "1.0.0"
    assert manifest["artifact_version"] == "batch2_v1"
    assert manifest["status"] == "DERIVED_ASSUMPTION_BASED_RESEARCH_SCENARIO"
    assert manifest["provenance"]["source_hash_status"] == "all_declared_A05_A06_input_hashes_match_current_files"
    assert len(manifest["scenario_series"]) == 3
    assert len(manifest["context_layers"]) == 4

    expected_grid = manifest["grid"]
    raster_refs = []
    saved_times = set()
    for series in manifest["scenario_series"]:
        assert series["scenario_id"] == "perfect_foresight_imerg"
        assert series["source_mode"] == "PERFECT_FORESIGHT_HINDCAST"
        assert series["member_count"] == 20
        assert len(series["members"]) == 20
        assert len(series["slices"]) == 5
        assert series["band_semantics"] == manifest["scenario_series"][0]["band_semantics"]
        assert "not archived forecast" in series["rainfall_semantics"]
        for saved in series["slices"]:
            _utc(saved["valid_time_utc"])
            saved_times.add(saved["valid_time_utc"])
            assert saved["lead_hours"] in {6, 12, 24, 48, 72}
            assert set(saved["bands"]) == {"p05", "p50", "p95"}
            raster_refs.extend(saved["bands"].values())

    peak_count = 0
    for context in manifest["context_layers"]:
        assert set(context["bands"]) == {"mean", "p05", "p95"}
        if context["temporal_kind"] == "per_cell_event_peak":
            peak_count += 1
            assert context["valid_time_utc"] is None
            assert context["selected_hour_index_zero_based"] is None
        else:
            _utc(context["valid_time_utc"])
            assert isinstance(context["selected_hour_index_zero_based"], int)
        raster_refs.extend(context["bands"].values())
    assert peak_count == 2
    assert saved_times == {s["valid_time_utc"] for series in manifest["scenario_series"] for s in series["slices"]}
    assert len(raster_refs) == 57

    for ref in raster_refs:
        target = ROOT / ref["path"]
        assert target.is_file()
        assert target.stat().st_size == ref["size_bytes"]
        assert _sha256(target) == ref["sha256"]
        assert ref["grid"] == expected_grid
        assert ref["units"] == manifest["depth_units"]["value"] == "m"
        assert ref["band_units_metadata"] is None
        assert ref["nodata_value"] == manifest["nodata"]["value"] == -9999.0
        assert ref["nodata_meaning"] in {"outside assessed CMA; not dry"}
        assert "not dry" in ref["nodata_meaning"]
        with rasterio.open(target) as raster:
            assert raster.count == 1 and raster.dtypes == ("float32",)
            assert raster.crs.to_string() == expected_grid["crs"]
            assert raster.width == expected_grid["width"] and raster.height == expected_grid["height"]
            assert raster.nodata == -9999.0
            mask = raster.read_masks(1)
            assert int((mask != 0).sum()) == ref["valid_cell_count"]
            assert int((mask == 0).sum()) == ref["nodata_cell_count"]
            assert ref["valid_cell_count"] + ref["nodata_cell_count"] == expected_grid["width"] * expected_grid["height"]

    provenance = manifest["provenance"]
    for row in provenance["declared_input_hashes"]:
        target = ROOT / row["path"]
        assert row["status"] == "match"
        assert row["expected_sha256"] == row["actual_sha256"] == _sha256(target)
    for summary_key in ("forecast_summary", "simulation_summary"):
        row = provenance[summary_key]
        assert _sha256(ROOT / row["path"]) == row["sha256"]

    # Compare both API projections with deterministic views derived only from
    # the checked-in manifest. No new timestamp or scientific value is created.
    catalog_view = {key: manifest[key] for key in (
        "schema_version", "artifact_version", "status", "grid", "depth_units",
        "nodata", "provenance", "context_layers", "limitations",
        "presentation_policy", "time_basis")}
    catalog_view["scenario_series"] = []
    for series in manifest["scenario_series"]:
        summary = {key: series[key] for key in (
            "event_id", "scenario_id", "source_mode", "window_start_utc",
            "window_end_utc_inclusive", "member_count", "rainfall_semantics",
            "band_semantics")}
        summary["saved_times_utc"] = [saved["valid_time_utc"] for saved in series["slices"]]
        catalog_view["scenario_series"].append(summary)
    for api_path in (AI_SPEC_PATH, BACKEND_SPEC_PATH):
        spec = _json(api_path)
        _validate_schema(_resolved_schema(spec, "ScenarioVisualizationCatalog"), catalog_view, spec)
        for series in manifest["scenario_series"]:
            asset_view = {key: manifest[key] for key in (
                "schema_version", "artifact_version", "status", "grid", "depth_units",
                "nodata", "provenance", "limitations", "presentation_policy", "time_basis")}
            asset_view["series"] = series
            _validate_schema(_resolved_schema(spec, "ScenarioVisualizationAsset"), asset_view, spec)

