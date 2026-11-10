"""Integrator-owned conformance checks for the C5/C7/C8 API projections.

These checks compare published OpenAPI schemas with the current service model
schemas, validate owner-produced result fixtures/output records, and keep
runtime-status annotations aligned with verified service availability.
"""
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AI_SPEC = ROOT / "docs/api/ai-service.yaml"
BACKEND_SPEC = ROOT / "docs/api/backend.yaml"


def _models():
    service_dir = ROOT / "services/ai-service"
    if str(service_dir) not in sys.path:
        sys.path.insert(0, str(service_dir))
    return importlib.import_module("app.main")


def _load_spec(path):
    # The repository's API documents use JSON, which is valid YAML 1.2.
    return json.loads(path.read_text(encoding="utf-8"))


_SEMANTIC_KEYS = {
    "type", "enum", "const", "format", "minimum", "maximum", "exclusiveMinimum",
    "exclusiveMaximum", "minLength", "maxLength", "pattern", "minItems", "maxItems",
    "uniqueItems", "required", "properties", "items", "anyOf", "oneOf", "allOf",
    "additionalProperties",
}


def _semantic(schema, root, local_defs=None):
    """Resolve local refs, then compare constraints while ignoring prose/defaults."""
    local_defs = local_defs or {}
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref.startswith("#/components/schemas/"):
            target = root["components"]["schemas"][ref.rsplit("/", 1)[1]]
            return _semantic(target, root, local_defs)
        if ref.startswith("#/$defs/"):
            return _semantic(local_defs[ref.rsplit("/", 1)[1]], root, local_defs)
        raise AssertionError(f"unsupported schema ref: {ref}")
    result = {}
    for key, value in schema.items():
        if key not in _SEMANTIC_KEYS:
            continue
        if key == "properties":
            result[key] = {name: _semantic(child, root, local_defs) for name, child in value.items()}
        elif key in ("items", "additionalProperties") and isinstance(value, dict):
            result[key] = _semantic(value, root, local_defs)
        elif key in ("anyOf", "oneOf", "allOf"):
            # Branch order is not semantically significant for these unions.
            branches = [_semantic(child, root, local_defs) for child in value]
            result[key] = sorted(branches, key=lambda item: json.dumps(item, sort_keys=True))
        else:
            result[key] = value
    return result


def _assert_model_projection(model, spec, component_name):
    expected = model.model_json_schema()
    actual = spec["components"]["schemas"][component_name]
    assert _semantic(actual, spec) == _semantic(expected, {}, expected.get("$defs", {})), component_name


def test_ai_and_backend_openapi_models_match_trackb_dto_schemas():
    main = _models()
    ai = _load_spec(AI_SPEC)
    backend = _load_spec(BACKEND_SPEC)
    for model, name in (
        (main.Layer, "Layer"),
        (main.ImpactResult, "ImpactResult"),
        (main.RouteRequest, "RouteRequest"),
        (main.RouteResponse, "RouteResponse"),
    ):
        _assert_model_projection(model, ai, name)
    for model, name in (
        (main.ImpactResult, "ImpactResult"),
        (main.RouteRequest, "RouteRequest"),
        (main.RouteResponse, "RouteResult"),
    ):
        _assert_model_projection(model, backend, name)


def test_c5_layer_projection_states_typed_provenance_and_unavailable_tiles():
    spec = _load_spec(AI_SPEC)
    layer = spec["components"]["schemas"]["Layer"]
    provenance = layer["properties"]["provenance"]["$ref"]
    provenance_schema = spec["components"]["schemas"][provenance.rsplit("/", 1)[1]]
    assert set(provenance_schema["properties"]) == {"source_sha256", "source_url"}
    assert layer["properties"]["tile_endpoint_available"]["const"] is False
    assert "do not expose http tiles" in layer["description"].lower()


def test_a07_and_a09_owner_outputs_validate_against_projected_models():
    main = _models()
    impact_path = ROOT / "data/features/impact/batch2_v4_contract/impact_results.jsonl"
    route_path = ROOT / "data/features/routing/results/batch2_v1/revision_3/route_results.jsonl"
    impacts = [json.loads(line) for line in impact_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    routes = [json.loads(line) for line in route_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert impacts and routes
    for record in impacts:
        parsed = main.ImpactResult.model_validate(record)
        assert parsed.source_mode in {"OBSERVED", "DERIVED", "SIMULATED", "ASSUMPTION", "REPLAY"}
    for record in routes:
        parsed = main.RouteResponse.model_validate(record)
        assert parsed.status.value in {
            "ROUTE_FOUND", "NO_TOPOLOGICAL_PATH", "INSUFFICIENT_HAZARD_COVERAGE",
            "BELOW_ACCESSIBILITY_CONSTRAINT", "INPUT_UNAVAILABLE",
        }
        assert not ({"reachable", "edge_ids", "travel_time_minutes"} & record.keys())
        assert "distance_m" in record and "travel_time_seconds" in record


def test_b15_owner_fixtures_preserve_nulls_and_topology_accessibility_distinction():
    main = _models()
    fixture_dir = ROOT / "services/backend/src/test/resources/owner-fixtures"
    impact = json.loads((fixture_dir / "a07_impact_v4.json").read_text(encoding="utf-8"))
    assert main.ImpactResult.model_validate(impact).aggregation_interval is None
    assert "INSTANTANEOUS" in impact["aggregation_basis"]
    assert impact["coverage"]["population"]["nodata_count"] >= 0
    for filename in ("a09_route_found.json", "a09_no_topological_path.json", "a09_insufficient_coverage.json"):
        record = json.loads((fixture_dir / filename).read_text(encoding="utf-8"))
        parsed = main.RouteResponse.model_validate(record)
        assert parsed.distance_m == record["distance_m"]
        assert parsed.travel_time_seconds == record["travel_time_seconds"]
        assert "reachable" not in record and "travel_time_minutes" not in record
    no_path = json.loads((fixture_dir / "a09_no_topological_path.json").read_text(encoding="utf-8"))
    parsed_no_path = main.RouteResponse.model_validate(no_path)
    assert parsed_no_path.topologically_reachable is False
    assert parsed_no_path.route_accessibility_probability is None
    insufficient = json.loads((fixture_dir / "a09_insufficient_coverage.json").read_text(encoding="utf-8"))
    parsed_insufficient = main.RouteResponse.model_validate(insufficient)
    assert parsed_insufficient.topologically_reachable is True
    assert parsed_insufficient.route_accessibility_probability is None


def test_cr008_c4_v1_selectors_match_verified_ai_runtime_and_backend_unexposed():
    from fastapi.testclient import TestClient

    main = _models()
    ai = _load_spec(AI_SPEC)
    backend = _load_spec(BACKEND_SPEC)
    ai_selector = ai["components"]["schemas"]["ImpactArtifactRequest"]
    backend_selector = backend["components"]["schemas"]["ImpactArtifactRequest"]
    assert _semantic(ai_selector, ai) == _semantic(backend_selector, backend)
    assert ai_selector["required"] == ["run_id", "valid_at", "scenario_key"]

    for spec, impact_path in ((ai, "/impact"), (backend, "/impact")):
        operation = spec["paths"][impact_path]["post"]
        assert operation["x-contract-version"] == "C4-v1"
        assert operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith("/ImpactArtifactRequest")
        assert "404" in operation["responses"]
    assert ai["paths"]["/impact"]["post"]["x-current-runtime-status"] == 200
    assert "501" not in ai["paths"]["/impact"]["post"]["responses"]
    assert "503" in ai["paths"]["/impact"]["post"]["responses"]
    assert backend["paths"]["/impact"]["post"]["x-current-runtime-status"] == "unexposed"

    for spec, response_name in ((ai, "RouteResponse"), (backend, "RouteResult")):
        operation = spec["paths"]["/route-results/{result_id}"]["get"]
        assert operation["operationId"] == "getSavedRouteResult"
        assert operation["x-contract-version"] == "C4-v1"
        assert operation["parameters"][0]["name"] == "result_id"
        assert "revision-3" in operation["description"].lower()
        assert "404" in operation["responses"]
        response_ref = operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        assert response_ref.endswith(f"/{response_name}")
    assert ai["paths"]["/route-results/{result_id}"]["get"]["x-current-runtime-status"] == 200
    assert "501" not in ai["paths"]["/route-results/{result_id}"]["get"]["responses"]
    assert "503" in ai["paths"]["/route-results/{result_id}"]["get"]["responses"]
    assert backend["paths"]["/route-results/{result_id}"]["get"]["x-current-runtime-status"] == "unexposed"

    # These successful lookups exercise B08's read-only saved-artifact paths.
    import json
    impact_file = ROOT / "data/features/impact/batch2_v4_contract/impact_results.jsonl"
    route_file = ROOT / "data/features/routing/results/batch2_v1/revision_3/route_results.jsonl"
    impact_record = json.loads(impact_file.read_text(encoding="utf-8").splitlines()[0])
    route_record = json.loads(route_file.read_text(encoding="utf-8").splitlines()[0])
    client = TestClient(main.app)
    impact_response = client.post("/impact", json={
        "run_id": impact_record["run_id"],
        "valid_at": impact_record["valid_at_utc"],
        "scenario_key": impact_record["scenario_key"],
    })
    assert impact_response.status_code == 200
    assert impact_response.json()["result_id"] == impact_record["result_id"]
    assert impact_response.json()["source_mode"] == "SIMULATED"
    route_response = client.get(f"/route-results/{route_record['result_id']}")
    assert route_response.status_code == 200
    assert route_response.json()["result_id"] == route_record["result_id"]
    assert route_response.json()["source_mode"] == "SIMULATED"

    for path, method in (
        ("/forecast", "post"),
        ("/uncertainty", "post"),
        ("/route", "post"),
        ("/scenario", "post"),
    ):
        operation = ai["paths"][path][method]
        assert operation["x-current-runtime-status"] == 501
        assert "501" in operation["responses"]

    # B21 mounted these two saved-A20 metadata operations in the B11 local package.
    for path in (
        "/scenario-visualization-assets",
        "/scenario-visualization-assets/{event_id}/{scenario_id}",
    ):
        operation = ai["paths"][path]["get"]
        assert operation["x-current-runtime-status"] == 200
        assert operation["x-runtime-availability"] == "available_in_local_B11_package"
    assert client.get("/scenario-visualization-assets").status_code == 200
    detail = client.get("/scenario-visualization-assets/2015-12-02/perfect_foresight_imerg")
    assert detail.status_code == 200
    assert detail.json()["series"]["event_id"] == "2015-12-02"

    # C9's approved metadata routes are mounted; unrelated backend business routes remain unexposed.
    assert "CR-009 C9 metadata catalog and detail GETs" in backend["info"]["description"]
    for path, path_item in backend["paths"].items():
        for operation in path_item.values():
            if isinstance(operation, dict) and "operationId" in operation:
                if path in {
                    "/scenario-visualization-assets",
                    "/scenario-visualization-assets/{event_id}/{scenario_id}",
                    "/replay-alerts/{event_id}",  # B27 route, mounted in B11; G5/CR-020 secondary check
                }:
                    assert operation["x-current-runtime-status"] == 200
                else:
                    assert operation["x-current-runtime-status"] == "unexposed"


def test_cr008_selector_keys_are_unique_only_within_registered_artifacts():
    impact_path = ROOT / "data/features/impact/batch2_v4_contract/impact_results.jsonl"
    route_path = ROOT / "data/features/routing/results/batch2_v1/revision_3/route_results.jsonl"
    impacts = [json.loads(line) for line in impact_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    routes = [json.loads(line) for line in route_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    impact_keys = [(row["run_id"], row["valid_at_utc"], row["scenario_key"]) for row in impacts]
    assert len(impacts) == 75
    assert len(set(impact_keys)) == len(impacts)
    assert all(row["result_id"] is not None for row in impacts)

    route_ids = [row["result_id"] for row in routes]
    assert len(routes) == 216
    assert all(value is not None for value in route_ids)
    assert len(set(route_ids)) == len(routes)
    assert all(row["run_id"] is None for row in routes)
    assert "revision_3" in str(route_path).lower()
