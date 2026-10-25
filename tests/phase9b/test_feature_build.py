import numpy as np

from pipelines.phase9b.feature_build import (
    compute_hand_and_flow_length,
    relative_elevation,
    terrain_curvature,
)


def test_relative_elevation_uses_valid_window_mean_and_keeps_nodata():
    z = np.arange(25, dtype=np.float32).reshape(5, 5)
    valid = np.ones(z.shape, dtype=bool)
    valid[0, 0] = False
    z[0, 0] = np.nan
    out = relative_elevation(z, valid, 3)
    assert np.isnan(out[0, 0])
    assert np.isfinite(out[2, 2])
    assert abs(float(out[2, 2])) < 1e-6


def test_curvature_is_zero_for_a_plane_and_nodata_at_mask_edge():
    y, x = np.mgrid[:7, :7]
    z = (3 * x + 2 * y).astype(np.float32)
    valid = np.ones(z.shape, dtype=bool)
    valid[:, 0] = False
    plan, profile = terrain_curvature(z, valid)
    assert np.isnan(plan[:, 0]).all()
    assert np.isnan(plan[:, 1]).all()
    assert np.isfinite(plan[3, 3])
    assert abs(float(plan[3, 3])) < 1e-8
    assert abs(float(profile[3, 3])) < 1e-8


def test_hand_and_d8_flow_length_reach_downstream_threshold_stream():
    z = np.tile(np.array([3, 2, 1, 0], dtype=np.float32), (3, 1))
    direction = np.zeros(z.shape, dtype=np.uint8)
    direction[:, :3] = 3  # D8 code 3 points east.
    accumulation = np.tile(np.array([1, 2, 3, 4], dtype=np.float32), (3, 1))
    accumulation[:, 3] = 100
    valid = np.ones(z.shape, dtype=bool)
    hand, lengths, _ = compute_hand_and_flow_length(z, direction, accumulation, valid, thresholds=(100,))
    assert np.allclose(hand[1], [3, 2, 1, 0])
    assert np.allclose(lengths["d8_flow_length_to_stream_100cells_m"][1], [90, 60, 30, 0])


def test_hand_uses_mapped_drainage_seeds_in_addition_to_accumulation_streams():
    z = np.tile(np.array([3, 2, 1, 0], dtype=np.float32), (3, 1))
    direction = np.zeros(z.shape, dtype=np.uint8)
    direction[:, :3] = 3
    accumulation = np.tile(np.array([1, 2, 3, 4], dtype=np.float32), (3, 1))
    valid = np.ones(z.shape, dtype=bool)
    mapped_water = np.zeros(z.shape, dtype=bool)
    mapped_water[:, 3] = True
    hand, _, stats = compute_hand_and_flow_length(
        z, direction, accumulation, valid, thresholds=(100,), drainage_mask=mapped_water)
    assert np.allclose(hand[1], [3, 2, 1, 0])
    assert stats["hand_added_mapped_water_cells"] == 3
