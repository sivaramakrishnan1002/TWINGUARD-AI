import numpy as np

from pipelines.phase8.flood_rule_v2 import compute_hand, valid_slope_mask


def test_hand_follows_d8_to_first_threshold_stream_cell():
    dem = np.array([[10.0, 8.0, 5.0]], dtype=np.float32)
    direction = np.array([[3, 3, 0]], dtype=np.uint8)  # code 3 points east
    accumulation = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)
    valid = np.ones((1, 3), dtype=bool)
    hand, counts = compute_hand(dem, direction, accumulation, valid, 3)
    assert np.allclose(hand, [[5.0, 3.0, 0.0]])
    assert counts["stream_cells"] == 1
    assert counts["cells_reaching_stream"] == 3


def test_hand_leaves_sink_without_drainage_as_nodata():
    dem = np.array([[7.0, 4.0]], dtype=np.float32)
    direction = np.array([[0, 0]], dtype=np.uint8)
    accumulation = np.array([[1.0, 1.0]], dtype=np.float32)
    valid = np.ones((1, 2), dtype=bool)
    hand, counts = compute_hand(dem, direction, accumulation, valid, 2)
    assert np.isnan(hand).all()
    assert counts["cells_reaching_stream"] == 0


def test_slope_nodata_sentinel_is_not_eligible():
    slope = np.array([[2.0, -9999.0, 5.0]], dtype=np.float32)
    mask = valid_slope_mask(slope, -9999.0, 5.0)
    assert mask.tolist() == [[True, False, True]]
