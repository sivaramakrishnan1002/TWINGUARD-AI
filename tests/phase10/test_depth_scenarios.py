import numpy as np
import pytest

from pipelines.phase10.depth_scenarios import cancel_common_bias, depth_classes
from pipelines.phase10.risk_map import NODATA_CLASS, classify, downsample_mode, zonal_table
from rasterio.transform import Affine


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


def test_risk_class_fixed_cut_points_and_nodata():
    p = np.array([[0.0, 0.049, 0.05, 0.10, 0.25, -9999.0, np.nan]], dtype=np.float32)
    assert classify(p, -9999.0).tolist() == [[1, 1, 2, 3, 4, NODATA_CLASS, NODATA_CLASS]]


def test_overview_mode_does_not_fill_low_coverage_cells():
    a = np.full((8, 8), NODATA_CLASS, dtype=np.uint8)
    a[:4, :4] = 2
    a[4:, :4] = 3
    small, transform = downsample_mode(a)
    assert small.shape == (2, 2)
    assert small[0, 0] == 2
    assert small[1, 0] == 3
    assert small[0, 1] == NODATA_CLASS
    assert transform == Affine(120, 0, 390000, 0, -120, 1471620)


def test_zonal_summary_keeps_unassessed_and_population_nodata():
    classes = np.array([[1, NODATA_CLASS], [4, NODATA_CLASS]], dtype=np.uint8)
    blocks = np.ones((2, 2), dtype=np.uint32)
    population = np.array([[3.0, -9999.0], [4.0, 5.0]], dtype=np.float32)
    rows = zonal_table("synthetic", classes, blocks, population, -9999.0, [], [], Affine.identity())
    unassessed = next(r for r in rows if r["risk_label"] == "not_assessed")
    assert unassessed["cell_count"] == 2
    assert unassessed["population_nodata_cells"] == 1
    assert unassessed["population_valid_sum_model_estimate"] == 5.0
