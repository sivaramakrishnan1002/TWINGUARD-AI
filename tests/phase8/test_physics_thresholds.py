import numpy as np
from affine import Affine

from pipelines.phase8.physics_thresholds import align_exact


def test_exact_alignment_preserves_zero_cells_and_integer_offset():
    source = np.array([[0, 1], [1, 0]], dtype=np.uint8)
    src_transform = Affine(30, 0, 390000, 0, -30, 1471620)
    dst_transform = Affine(30, 0, 389970, 0, -30, 1471650)
    aligned = align_exact(source, src_transform, "EPSG:32644", dst_transform, "EPSG:32644", (4, 4))
    assert np.array_equal(aligned[1:3, 1:3], source)
    assert int(np.count_nonzero(aligned)) == 2
    assert aligned[1, 1] == 0


def test_exact_alignment_rejects_fractional_pixel_shift():
    source = np.ones((2, 2), dtype=np.uint8)
    src_transform = Affine(30, 0, 390015, 0, -30, 1471620)
    dst_transform = Affine(30, 0, 389970, 0, -30, 1471650)
    try:
        align_exact(source, src_transform, "EPSG:32644", dst_transform, "EPSG:32644", (4, 4))
    except ValueError as exc:
        assert "pixel-aligned" in str(exc)
    else:
        raise AssertionError("fractional pixel shift must fail")
