import copy
import json
from pathlib import Path

import pytest

from pipelines.floodviz3d.build_manifest import ROOT, build_manifest, validate_manifest


def test_manifest_indexes_only_saved_times_and_keeps_unknown_coverage():
    manifest = build_manifest(ROOT)
    assert len(manifest["scenario_series"]) == 3
    assert sum(len(s["slices"]) for s in manifest["scenario_series"]) == 15
    assert sum(len(t["bands"]) for s in manifest["scenario_series"] for t in s["slices"]) == 45
    assert manifest["grid"]["pixel_size_m"] == [600.0, 600.0]
    assert manifest["nodata"]["meaning"].endswith("unknown coverage, not dry")
    assert all(t["valid_time_utc"].endswith("Z")
               for s in manifest["scenario_series"] for t in s["slices"])
    assert {t["lead_hours"] for s in manifest["scenario_series"] for t in s["slices"]} == {6, 12, 24, 48, 72}


def test_a06_peak_has_no_single_valid_time_but_selected_hour_does():
    manifest = build_manifest(ROOT)
    peaks = [x for x in manifest["context_layers"] if x["temporal_kind"] == "per_cell_event_peak"]
    selected = [x for x in manifest["context_layers"] if x["temporal_kind"] == "selected_hour"]
    assert len(peaks) == len(selected) == 2
    assert all(x["valid_time_utc"] is None for x in peaks)
    assert all(x["valid_time_utc"].endswith("Z") for x in selected)


def test_manifest_rejects_invented_lead_and_peak_timestamp():
    manifest = build_manifest(ROOT)
    bad_time = copy.deepcopy(manifest)
    bad_time["scenario_series"][0]["slices"][0]["lead_hours"] = 3
    with pytest.raises(ValueError, match="unexpected quantitative lead time"):
        validate_manifest(bad_time, ROOT)
    bad_peak = copy.deepcopy(manifest)
    peak = next(x for x in bad_peak["context_layers"] if x["temporal_kind"] == "per_cell_event_peak")
    peak["valid_time_utc"] = "2015-11-12T00:00:00Z"
    with pytest.raises(ValueError, match="per-cell peak must not claim one valid instant"):
        validate_manifest(bad_peak, ROOT)


def test_output_validation_rechecks_raster_metadata_not_only_manifest_fields():
    manifest = build_manifest(ROOT)
    bad = copy.deepcopy(manifest)
    band = bad["scenario_series"][0]["slices"][0]["bands"]["p50"]
    band["grid"]["width"] = 70
    with pytest.raises(ValueError, match="manifest raster grid/NoData mismatch"):
        validate_manifest(bad, ROOT)


def test_schema_file_is_json_and_declares_the_accepted_manifest_contract():
    schema_path = ROOT / "pipelines/floodviz3d/manifest.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["$schema"].endswith("2020-12/schema")
    assert set(schema["required"]) >= {
        "schema_version", "status", "grid", "depth_units", "nodata", "time_basis",
        "scenario_series", "context_layers", "provenance", "limitations",
    }
    assert schema["properties"]["scenario_series"]["minItems"] == 3
    assert schema["properties"]["context_layers"]["minItems"] == 4
