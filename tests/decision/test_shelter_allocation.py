import numpy as np

from pipelines.decision.shelter_allocation import allocate_by_component


def test_allocation_respects_capacity_and_tracks_unserved():
    result = allocate_by_component(
        demand=np.array([80.0, 70.0, 50.0]),
        origin_component=np.array([1, 1, 2]),
        origin_xy=np.array([[0.0, 0.0], [10.0, 0.0], [0.0, 0.0]]),
        candidate_component=np.array([1, 2]),
        candidate_xy=np.array([[0.0, 1.0], [0.0, 1.0]]),
        candidate_capacity=np.array([100.0, 20.0]),
    )
    assert result["served"].sum() == 120.0
    assert result["unserved_demand"] == 80.0
    assert result["unserved_reachable_demand"] == 80.0
    assert result["unreachable_demand"] == 0.0
    assert result["served"].sum() + result["unserved_demand"] == result["known_demand"]
    assert result["capacity_used"].tolist() == [100.0, 20.0]


def test_demand_without_component_is_unreachable_and_nodata_is_not_zero():
    result = allocate_by_component(
        demand=np.array([40.0, np.nan]),
        origin_component=np.array([-1, -1]),
        origin_xy=np.array([[0.0, 0.0], [1.0, 1.0]]),
        candidate_component=np.array([0]),
        candidate_xy=np.array([[0.0, 0.0]]),
        candidate_capacity=np.array([100.0]),
    )
    assert result["known_demand"] == 40.0
    assert result["unserved_demand"] == 40.0
    assert result["unreachable_demand"] == 40.0
    assert result["unserved_reachable_demand"] == 0.0
    assert result["unserved_reachable_demand"] + result["unreachable_demand"] == result["unserved_demand"]
    assert result["unknown_demand_cells"] == 1


def test_no_candidates_leaves_known_demand_unserved():
    result = allocate_by_component(
        demand=np.array([25.0]),
        origin_component=np.array([1]),
        origin_xy=np.array([[0.0, 0.0]]),
        candidate_component=np.array([], dtype=int),
        candidate_xy=np.empty((0, 2)),
        candidate_capacity=np.array([]),
    )
    assert result["unserved_demand"] == 25.0
    assert result["unserved_reachable_demand"] == 0.0
    assert result["unreachable_demand"] == 25.0
    assert result["served"].sum() == 0.0
