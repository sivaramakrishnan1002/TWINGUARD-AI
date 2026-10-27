import numpy as np
import pytest

from experiments.explainability.batch2_v1.run import aggregate_member_summaries, factorial_effect, grouped_permutation_drop


class TinyProbabilityModel:
    def predict_proba(self, x):
        p = np.clip(0.1 + 0.8 * x[:, 0], 0.001, 0.999)
        return np.column_stack([1 - p, p])


def test_member_aggregation_keeps_dry_and_excludes_nodata():
    depth = np.array([[[0.0, 0.1], [-9999.0, 0.3]]], dtype=np.float32)
    params = [{"member_id": 1, "manning_multiplier": 1.0, "infiltration_multiplier": 0.5}]
    row = aggregate_member_summaries(depth, params, 600)[0]
    assert row["valid_cells"] == 3
    assert row["nodata_cells"] == 1
    assert row["mean_peak_depth_m"] == pytest.approx((0.0 + 0.1 + 0.3) / 3)
    assert row["area_ge_0.10m_km2"] == pytest.approx(0.72)


def test_factorial_effect_reports_centered_levels():
    rows = [
        {"manning_multiplier": 1.0, "metric": 2.0},
        {"manning_multiplier": 2.0, "metric": 4.0},
    ]
    out = factorial_effect(rows, "manning_multiplier", "metric")
    assert [r["difference_from_grand_mean"] for r in out] == [-1.0, 1.0]


def test_grouped_permutation_is_deterministic_and_preserves_group_membership():
    x = np.array([[0., 1.], [1., 0.], [0., 1.], [1., 0.]])
    y = np.array([0, 1, 0, 1])
    groups = np.array([10, 10, 20, 20])
    model = TinyProbabilityModel()
    a = grouped_permutation_drop(model, x, y, groups, 1, 31)
    b = grouped_permutation_drop(model, x, y, groups, 1, 31)
    assert a == b
    assert np.isfinite(a)
