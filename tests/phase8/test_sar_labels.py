from pathlib import Path

import numpy as np
import pytest
from affine import Affine

from pipelines.phase8.sar_labels import (
    _assert_grid_alignment,
    _confusion_metrics,
    _crop_grid,
    _crop_valid,
    _otsu,
    _scene_file_index,
)


def test_scene_index_maps_source_scene_timestamp():
    records = [{"source_scene": "S1A_IW_GRDH_1SDV_20151124T003120_20151124T003149_008739_00C723_AB80",
                "source_scene_zip_exists": True}]
    assert "20151124T003120" in _scene_file_index(records)


def test_otsu_separates_two_modes_without_reference_labels():
    values = np.r_[np.full(100, -8.0), np.full(100, 2.0)]
    threshold = _otsu(values)
    assert -8.0 < threshold < 2.0


def test_confusion_metrics_known_counts():
    predicted = np.array([1, 1, 0, 0], dtype=bool)
    observed = np.array([1, 0, 1, 0], dtype=bool)
    metrics = _confusion_metrics(predicted, observed, np.ones(4, dtype=bool))
    assert metrics["confusion_matrix_TP_FP_FN_TN"] == [1, 1, 1, 1]
    assert metrics["iou"] == pytest.approx(1 / 3)
    assert metrics["f1"] == pytest.approx(0.5)


def test_crop_and_validity_use_master_window_offsets():
    grid = np.arange(100).reshape(10, 10)
    info = {"buffer_window_offset": [-2, -3], "height": 10, "width": 10}
    meta = {"height": 4, "width": 3}
    np.testing.assert_array_equal(_crop_grid(grid, info, meta), grid[2:6, 3:6])
    valid = np.ones((10, 10), dtype=np.float32)
    valid[4, 4] = 0
    cropped = _crop_valid(valid, grid_info=info, master_meta=meta)
    assert cropped.shape == (4, 3)
    assert not cropped[2, 1]


def test_alignment_accepts_integral_pixel_offset_and_rejects_fractional():
    master = Affine(30, 0, 390000, 0, -30, 1471620)
    assert _assert_grid_alignment(Affine(30, 0, 390090, 0, -30, 1471560), master) == (3.0, 2.0)
    with pytest.raises(ValueError, match="not pixel-aligned"):
        _assert_grid_alignment(Affine(30, 0, 390015, 0, -30, 1471620), master)
