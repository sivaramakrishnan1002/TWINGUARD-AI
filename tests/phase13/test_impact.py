import numpy as np

from pipelines.phase13.impact import (
    grid_indices,
    known_population_exposure,
    member_distribution,
    probability_below,
    validate_impact_result,
)


def test_grid_indices_uses_row_major_and_marks_outside():
    transform = type("Transform", (), {"c": 100.0, "a": 10.0, "f": 200.0, "e": -10.0})()
    result = grid_indices(np.array([105, 115, 95]), np.array([195, 185, 195]), transform, 2, 2)
    assert result.tolist() == [0, 3, -1]


def test_depth_equal_to_threshold_is_blocked_and_nodata_is_unassessed():
    stack = np.array([[[0.1, 0.3, np.nan]], [[0.2, 0.4, np.nan]]], dtype=np.float32)
    probability, count = probability_below(stack, 0.3)
    assert probability[0, 0] == 1.0
    assert probability[0, 1] == 0.0
    assert np.isnan(probability[0, 2])
    assert count.tolist() == [[2, 2, 0]]


def test_population_nodata_remains_unknown_not_zero():
    depth = np.array([[0.3, 0.3, np.nan]], dtype=np.float32)
    population = np.array([[10.0, np.nan, np.nan]])
    valid = np.array([[1, 0, 0]])
    nodata = np.array([[0, 1, 0]])
    known, unknown, flooded_cells = known_population_exposure(depth, population, valid, nodata, 0.3)
    assert known == 10.0
    assert unknown == 1
    assert flooded_cells == 2


def test_distribution_is_descriptive_and_empty_is_null():
    summary = member_distribution([1, 2, 3], "m")
    assert summary["mean"] == 2.0
    assert summary["member_count"] == 3
    unavailable = member_distribution([np.nan], "people")
    assert unavailable["status"] == "UNAVAILABLE"
    assert unavailable["mean"] is None


def test_c7_proposal_validator_checks_time_units_coverage_and_cascade_fields():
    record = {
        "schema_id": "twinguard.impact_result", "schema_version": "0.1-draft",
        "result_id": "test", "run_id": "test", "run_version": "batch2_v2",
        "source_mode": "SIMULATED", "event": {"time_basis": "UTC"},
        "valid_at_utc": "2026-01-01T00:00:00Z", "aggregation_interval": None,
        "generated_at_utc": "2026-01-01T00:00:00Z", "scenario_key": "test",
        "thresholds": {"road_block_depth_m": 0.3},
        "metrics": {"population_exposed_people": {"unit": "people"}},
        "facility_access_by_category": [{"facility_count": 1, "reachable_count": 1,
            "unreachable_count": 0, "unassessed_count": 0, "access_loss_fraction": 0.0,
            "coverage_fraction": 1.0}],
        "coverage": {"population": {"nodata_count": 0}}, "uncertainty": {},
        "provenance": {}, "qc_flags": [],
    }
    validate_impact_result(record)
    record["coverage"]["population"].pop("nodata_count")
    try:
        validate_impact_result(record)
    except ValueError as exc:
        assert "NoData count" in str(exc)
    else:
        raise AssertionError("validator accepted population coverage without a NoData count")
