import numpy as np

from pipelines.phase12.simulate import (
    folds,
    metrics,
    parameter_members,
    stable_dt,
    step,
)


def test_parameter_ensemble_has_twenty_fixed_members():
    members = parameter_members()
    assert len(members) == 20
    assert members == parameter_members()
    assert len({(m.manning_multiplier, m.infiltration_multiplier) for m in members}) == 20


def test_local_inertial_step_conserves_volume_and_respects_drain_boundary():
    z = np.zeros((5, 5), dtype=float)
    h = np.zeros_like(z)
    active = np.ones_like(z, dtype=bool)
    drain = np.zeros_like(active)
    drain[2, 3] = True
    active[2, 3] = False
    h[2, 2] = 0.2
    qx = np.zeros((5, 4), dtype=float)
    qy = np.zeros((4, 5), dtype=float)
    mann = np.full_like(z, 0.05)
    porosity = np.ones_like(z)
    infiltration = np.full_like(z, 2e-6)
    dx, dt = 30.0, 2.0
    new_h, new_qx, new_qy, diag = step(
        z, h, qx, qy, active, drain, mann, porosity, infiltration,
        rain_m_s=1e-5, dx=dx, dt=dt,
    )
    before = float(h[active].sum() * dx * dx)
    after = float(new_h[active].sum() * dx * dx)
    assert np.all(new_h >= 0)
    assert np.isfinite(new_qx).all() and np.isfinite(new_qy).all()
    assert abs(before + diag["rain_m3"] - diag["infiltration_m3"] - diag["outflow_m3"] - after) < 1e-6
    assert diag["outflow_m3"] >= 0


def test_stable_step_is_positive_and_shrinks_with_depth():
    active = np.ones((3, 3), dtype=bool)
    qx = np.zeros((3, 2))
    qy = np.zeros((2, 3))
    dry = np.zeros((3, 3))
    wet = np.full((3, 3), 2.0)
    assert stable_dt(dry, qx, qy, active, 600) > stable_dt(wet, qx, qy, active, 600) > 0


def test_buffered_spatial_folds_do_not_overlap_train_and_test():
    blocks = np.repeat(np.repeat(np.arange(1, 17).reshape(4, 4), 5, axis=0), 5, axis=1)
    eligible = np.ones_like(blocks, dtype=bool)
    split = folds(blocks, eligible, nfold=4, buffer_cells=1)
    assert len(split) == 4
    for train, test in split:
        assert not np.any(train & test)
        assert train.any() and test.any()


def test_metrics_include_calibration_and_true_prevalence():
    y = np.array([0, 0, 0, 1, 1], dtype=np.uint8)
    p = np.array([0.1, 0.2, 0.3, 0.7, 0.9])
    result = metrics(y, p)
    assert result["roc_auc"] == 1.0
    assert result["pr_auc"] == 1.0
    assert result["prevalence"] == 0.4
    assert 0 <= result["brier"] <= 1
    assert 0 <= result["ece"] <= 1
