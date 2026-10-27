from __future__ import annotations

import numpy as np
import pytest

from pipelines.routing.time_dependent_batch2.graph_overlay import (
    STATE_BLOCKED,
    STATE_OPEN,
    STATE_REDUCED,
    STATE_STRUCTURE_UNASSESSED,
    STATE_UNKNOWN,
    depth_state,
    edge_structure,
    parse_speed_kmh,
    state_transition_count,
    structure_state,
)


def test_ordinary_depth_states_and_assumed_speed_factor():
    depth = np.array([np.nan, 0.0, 0.15, 0.299, 0.30], dtype=np.float32)
    state, speed = depth_state(depth, 0.30)
    assert state.tolist() == [STATE_UNKNOWN, STATE_OPEN, STATE_REDUCED, STATE_REDUCED, STATE_BLOCKED]
    assert np.isnan(speed[0])
    assert speed[1] == pytest.approx(1.0)
    assert speed[2] == pytest.approx(0.6)
    assert speed[3] >= 0.20
    assert speed[4] == 0.0


def test_tunnel_uses_separate_lower_block_threshold():
    state, _ = structure_state(np.array([0.149, 0.15], dtype=np.float32), "tunnel_underpass_proxy")
    assert state.tolist() == [STATE_REDUCED, STATE_BLOCKED]


@pytest.mark.parametrize("structure", ["bridge", "bridge_and_tunnel"])
def test_bridge_depth_is_not_mistaken_for_deck_depth(structure):
    state, speed = structure_state(np.array([0.0, 3.0, np.nan], dtype=np.float32), structure)
    assert np.all(state == STATE_STRUCTURE_UNASSESSED)
    assert np.all(np.isnan(speed))


def test_missing_depth_is_never_treated_as_open_or_dry():
    state, speed = structure_state(np.array([np.nan], dtype=np.float32), "ordinary")
    assert state[0] == STATE_UNKNOWN
    assert np.isnan(speed[0])


def test_transition_count_weights_state_changes_by_directed_arc_count():
    previous = np.array([STATE_OPEN, STATE_UNKNOWN, STATE_BLOCKED, STATE_REDUCED], dtype=np.uint8)
    current = np.array([STATE_REDUCED, STATE_UNKNOWN, STATE_BLOCKED, STATE_OPEN], dtype=np.uint8)
    weights = np.array([2, 100, 4, 3])
    assert state_transition_count(previous, current, weights) == 5
    assert state_transition_count(None, current, weights) == 0


def test_structure_flags_and_speed_tag_defaults_are_explicit():
    assert edge_structure("yes", "") == "bridge"
    assert edge_structure("", "building_passage") == "tunnel_underpass_proxy"
    assert edge_structure("no", None) == "ordinary"
    assert edge_structure("viaduct", "yes") == "bridge_and_tunnel"
    assert parse_speed_kmh("30 mph", "residential")[0] == pytest.approx(48.28032)
    assert parse_speed_kmh(None, "residential") == (30.0, "ASSUMED_HIGHWAY_DEFAULT")
    assert parse_speed_kmh("unknown", "unlisted_class") == (20.0, "ASSUMED_HIGHWAY_DEFAULT")


def test_invalid_zero_threshold_fails_instead_of_creating_infinite_factor():
    with pytest.raises(ValueError, match="must be positive"):
        depth_state(np.array([0.1], dtype=np.float32), 0.0)
