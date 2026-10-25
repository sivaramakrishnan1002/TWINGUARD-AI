import numpy as np

from pipelines.phase9c.urban_censoring import (
    BUILT_BINS,
    apply_q,
    block_bootstrap_point_hits,
    q_by_bin,
)


def test_mondrian_quantiles_are_builtup_stratified_and_finite():
    idx = np.arange(10)
    built = np.array([.01, .02, .04, .06, .08, .15, .18, .22, .25, .28])
    y = np.array([0, 0, 0, 1, 1, 0, 0, 1, 1, 1], dtype=np.uint8)
    p = np.array([.01, .02, .03, .80, .90, .10, .20, .70, .80, .90])
    q, info = q_by_bin(idx, p, y, built)
    assert q["0_to_0.1"] != q["0.1_to_0.3"]
    assert info["0_to_0.1"]["n"] == 5
    assert info["0.1_to_0.3"]["n"] == 5


def test_apply_mondrian_quantile_clips_interval_to_probability_range():
    p = np.array([.02, .5, .98], dtype=np.float32)
    built = np.array([.03, .2, .9])
    q = {name: .2 for name, _, _ in BUILT_BINS}
    lower, upper = apply_q(p, built, q)
    assert np.allclose(lower, [0, .3, .78])
    assert np.allclose(upper, [.22, .7, 1])


def test_point_hit_bootstrap_compares_to_same_builtup_bin_chance():
    risk = np.arange(400, dtype=np.float32).reshape(20, 20) / 400
    built = np.where(np.indices(risk.shape)[1] < 10, .05, .2).astype(np.float32)
    domain = np.ones(risk.shape, dtype=bool)
    points = [
        {"row": 19, "col": 19, "built": .2, "risk": float(risk[19, 19])},
        {"row": 18, "col": 18, "built": .2, "risk": float(risk[18, 18])},
        {"row": 0, "col": 0, "built": .05, "risk": float(risk[0, 0])},
    ]
    out = block_bootstrap_point_hits(points, risk, built, domain, 20, seed=4, reps=50)
    assert out["n"] == 3
    assert out["observed_share"] == 2 / 3
    assert out["matched_chance_share"] is not None
    assert out["by_built_up_bin"]["0_to_0.1"]["point_n"] == 1
    assert out["by_built_up_bin"]["0_to_0.1"]["observed_share"] == 0.0
    assert out["by_built_up_bin"]["0.1_to_0.3"]["point_n"] == 2
    assert out["by_built_up_bin"]["0.5_to_0.75"]["point_n"] == 0
    assert out["by_built_up_bin"]["0.5_to_0.75"]["observed_share"] is None
    assert out["by_built_up_bin"]["0_to_0.1"]["matched_chance_ci_95"] is not None
    assert len(out["observed_ci_95"]) == 2


def test_unscored_source_points_do_not_enter_map_hit_denominator():
    risk = np.arange(100, dtype=np.float32).reshape(10, 10) / 100
    built = np.full(risk.shape, .2, dtype=np.float32)
    points = [
        {"row": 9, "col": 9, "built": .2, "risk": float(risk[9, 9])},
        {"row": None, "col": None, "built": None, "risk": None},
    ]
    out = block_bootstrap_point_hits(points, risk, built, np.ones(risk.shape, bool), 20, seed=8, reps=30)
    assert out["n"] == 1
    assert out["by_built_up_bin"]["0.1_to_0.3"]["point_n"] == 1


def test_chance_draw_matches_dominant_landcover_class():
    risk = np.tile(np.linspace(0, 1, 20, dtype=np.float32), (20, 1))
    built = np.full(risk.shape, .2, dtype=np.float32)
    landcover = np.where(np.indices(risk.shape)[1] < 10, 0, 1).astype(np.int8)
    point = [{"row": 10, "col": 0, "built": .2, "risk": float(risk[10, 0])}]
    out = block_bootstrap_point_hits(point, risk, built, np.ones(risk.shape, bool), 50,
                                    seed=12, reps=50, landcover_grid=landcover)
    assert out["observed_share"] == 0.0
    assert out["matched_chance_share"] == 0.0
    assert out["matched_chance_n"] == 1
