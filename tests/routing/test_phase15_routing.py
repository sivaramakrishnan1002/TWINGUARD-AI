import numpy as np

from pipelines.routing.phase15_routing import (
    STATE_BLOCKED,
    STATE_OPEN,
    STATE_UNASSESSED,
    STATE_UNKNOWN,
    classify_route_states,
    dijkstra_path,
    make_route_weights,
    validate_route_record,
)


def test_path_reconstruction_and_unreachable():
    assert dijkstra_path(np.array([-9999, 0, 1]), 0, 2) == [0, 1, 2]
    assert dijkstra_path(np.array([-9999, -9999, -9999]), 0, 2) is None


def test_route_state_keeps_unknown_unassessed_as_null():
    assert classify_route_states(np.array([STATE_OPEN, STATE_BLOCKED])) == (True, 0.0)
    assert classify_route_states(np.array([STATE_OPEN, STATE_UNKNOWN])) == (None, None)
    assert classify_route_states(np.array([STATE_UNASSESSED])) == (None, None)


def test_expected_cost_penalizes_blocked_and_excludes_unknown():
    states = np.array([[STATE_OPEN, STATE_BLOCKED, STATE_UNKNOWN],
                       [STATE_BLOCKED, STATE_OPEN, STATE_OPEN]])
    speed = np.ones_like(states, dtype=float)
    base = np.array([10.0, 20.0, 30.0])
    weights = make_route_weights(states, speed, base)
    assert weights[0] == (10.0 + 200.0) / 2
    assert weights[1] == (400.0 + 20.0) / 2
    assert np.isinf(weights[2])


def test_uncertainty_edge_constraint_is_applied():
    states = np.array([[STATE_OPEN, STATE_BLOCKED],
                       [STATE_OPEN, STATE_BLOCKED],
                       [STATE_OPEN, STATE_OPEN],
                       [STATE_OPEN, STATE_OPEN]])
    weights = make_route_weights(states, np.ones_like(states, dtype=float),
                                 np.array([10.0, 10.0]), failure_limit=0.25)
    assert np.isfinite(weights[0])
    assert np.isinf(weights[1])


def test_route_record_rejects_probability_inversion_and_keeps_simulated_flag():
    record = {
        "schema_id": "twinguard.route_result", "schema_version": "0.1-draft",
        "result_id": "test", "status": "ROUTE_FOUND", "source_mode": "SIMULATED",
        "departure_at_utc": "2026-10-27T00:00:00Z", "arrival_at_utc": None,
        "distance_m": 1.0, "travel_time_seconds": 1.0, "topologically_reachable": True,
        "node_path": [1, 2], "route_accessibility_probability": 0.75,
        "route_failure_probability": 0.25,
        "edge_coverage": {"route_edge_count": 1, "assessed_edge_count": 1,
                          "unassessed_edge_count": 0, "fraction_assessed": 1.0},
        "depth_thresholds": {}, "graph": {}, "hazard_run": {}, "uncertainty": {},
        "provenance": {}, "qc_flags": ["SIMULATED_TRUTH"], "edges": []
    }
    validate_route_record(record)
    record["route_failure_probability"] = 0.75
    try:
        validate_route_record(record)
    except ValueError as exc:
        assert "complement" in str(exc)
    else:
        raise AssertionError("probability inversion was accepted")
