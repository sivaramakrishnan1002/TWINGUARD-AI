from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "pipelines/decision/phase22_decision_lab.py"
SPEC = importlib.util.spec_from_file_location("phase22_decision_lab", MODULE_PATH)
phase22 = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(phase22)


def test_case_key_uses_full_registered_pairing_dimensions():
    row = {"scenario_key": "2015-12-02/perfect_foresight_imerg", "requested_horizon_seconds": 21600,
           "origin_id": "osm-road-node:1", "destination_id": "osm-road-node:2"}
    assert phase22.case_key(row) == (row["scenario_key"], 21600, row["origin_id"], row["destination_id"])


def test_route_comparison_joins_only_identical_event_horizon_and_od():
    def row(method, event, horizon):
        return {"scenario_key": f"{event}/scenario", "requested_horizon_seconds": horizon,
                "origin_id": "o", "destination_id": "d", "method": method,
                "status": "ROUTE_FOUND", "route_failure_probability": 0.1,
                "travel_time_seconds": 100.0,
                "provenance": {"parameters": {"expected_exposure_depth_distance_m2": 20.0}},
                "edge_coverage": {"fraction_assessed": 1.0}, "arrival_at_utc": "2015-01-01T01:00:00Z"}
    rows = [row("current_flood_aware", "e1", 21600), row("uncertainty_aware", "e1", 21600),
            row("current_flood_aware", "e1", 86400), row("uncertainty_aware", "e2", 86400)]
    result = phase22.compute_route_comparisons(rows)
    assert result["comparisons"]["H3"]["matched_case_count"] == 1
    assert result["comparisons"]["H4"]["matched_case_count"] == 0


def test_paired_bootstrap_is_reproducible_and_reports_small_cluster_count():
    rows = [("e1", 1.0, 2.0), ("e1", 3.0, 4.0), ("e2", 2.0, 1.0)]
    first = phase22.compare_values(rows, "lower")
    second = phase22.compare_values(rows, "lower")
    assert first == second
    assert first["counts"] == {"wins": 2, "ties": 0, "losses": 1, "missing": 0, "incomparable": 0}
    assert first["paired_A_minus_B"]["cluster_count"] == 2
    assert first["paired_A_minus_B"]["seed"] == phase22.SEED


def test_missing_value_is_not_treated_as_zero_or_a_win():
    result = phase22.compare_values([("event", None, 0.0), ("event", 0.2, 0.3)], "lower")
    assert result["counts"]["missing"] == 1
    assert result["counts"]["wins"] == 1
    assert result["comparable_case_count"] == 1


def test_raster_validity_mask_preserves_nodata(tmp_path):
    path = tmp_path / "mask.tif"
    data = np.array([[0.0, -9999.0], [1.0, 2.0]], dtype="float32")
    with rasterio.open(path, "w", driver="GTiff", height=2, width=2, count=1, dtype="float32",
                       crs="EPSG:32644", transform=from_origin(390000, 1471620, 600, 600), nodata=-9999.0) as ds:
        ds.write(data, 1)
    mask = phase22._read_valid_mask(path, (2, 2))
    assert mask.tolist() == [[True, False], [True, True]]
    assert data[0, 0] == 0.0  # valid dry-depth zero remains a valid value


def _find_prohibited_key(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in phase22.PROHIBITED:
                return key
            found = _find_prohibited_key(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_prohibited_key(child)
            if found:
                return found
    return None


def test_output_contract_prohibits_composite_or_vulnerability_fields():
    safe = {"hazard": {"unit": "fraction"}, "population_exposure": {"unit": "people_model_estimate"},
            "facility_access_loss": {"unit": "count"}, "status": "SIMULATED"}
    forbidden = {"hazard": {}, "vulnerability_score": 0.4}
    assert _find_prohibited_key(safe) is None
    assert _find_prohibited_key(forbidden) == "vulnerability_score"
    h2 = {"case_count": 75, "status": "SIMULATED_SYNTHETIC_HOLDOUT_DIAGNOSTIC_NOT_EMPIRICAL_CALIBRATION"}
    route = {"route_record_count": 216, "comparisons": {"H3": {}, "H4": {}}}
    h5 = {"departure_shift": {"status": "UNAVAILABLE_FROM_REGISTERED_ARTIFACTS"}}
    provenance = {"a11_indicators_kept_separate": {"indicator_categories": ["hazard", "population_exposure", "facility_access_loss"]}}
    phase22.validate_output_contract(h2, route, h5, provenance)
