import numpy as np
import pytest

from pipelines.phase10.depth_scenarios import cancel_common_bias, depth_classes


def test_depth_class_boundaries():
    values = np.array([0.0, 0.149, 0.15, 0.299, 0.30, 0.499, 0.50, 1.0])
    assert depth_classes(values).tolist() == [0, 0, 1, 1, 2, 2, 3, 3]


def test_common_absolute_dem_bias_cancels_in_edge_surface_method():
    dem = np.array([[10, 12, 11, 9], [11, 8, 12, 10], [13, 9, 7, 12]], dtype=np.float32)
    flood = np.array([[1, 1, 0, 0], [1, 1, 1, 0], [0, 1, 1, 0]], dtype=bool)
    assert cancel_common_bias(dem, flood, 4.0) == 0.0


def test_common_bias_rejects_nonfinite_offset():
    dem = np.array([[1, 2], [2, 3]], dtype=np.float32)
    flood = np.ones((2, 2), dtype=bool)
    with pytest.raises((ValueError, AssertionError)):
        cancel_common_bias(dem, flood, float("nan"))


def test_common_bias_requires_nonempty_valid_extent():
    with pytest.raises(ValueError, match="at least one cell"):
        cancel_common_bias(np.ones((2, 2)), np.zeros((2, 2), dtype=bool))


def test_common_bias_requires_matching_shapes():
    with pytest.raises(ValueError, match="matching shapes"):
        cancel_common_bias(np.ones((2, 2)), np.ones((2, 3), dtype=bool))
