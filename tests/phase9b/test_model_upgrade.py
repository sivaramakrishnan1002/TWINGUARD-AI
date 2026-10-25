import numpy as np

from pipelines.phase9.pilot import buffered_train_groups
from pipelines.phase9b.model_upgrade import (
    metric_bundle,
    make_split_specs,
    paired_fold_differences,
    random_configs,
    sample_train,
    select_f1_threshold,
    crossfit_calibration,
)


def test_buffered_group_split_has_no_overlap_or_adjacent_training_blocks():
    positions = {0: (0, 0), 1: (0, 1), 2: (0, 2), 3: (1, 0), 4: (1, 1), 5: (1, 2)}
    valid = np.array([2, 5])
    train = np.array([0, 1, 3, 4])
    kept = buffered_train_groups(train, valid, positions, 1)
    assert set(kept).isdisjoint(valid)
    for g in kept:
        gr, gc = positions[int(g)]
        assert all(max(abs(gr - positions[v][0]), abs(gc - positions[v][1])) > 1 for v in valid)


def test_inner_spatial_folds_partition_blocks_and_keep_a_buffer():
    groups = np.repeat(np.arange(12), 40)
    positions = {g: (g // 2, g % 2) for g in range(12)}
    y = np.tile(np.r_[np.ones(10, dtype=np.uint8), np.zeros(30, dtype=np.uint8)], 12)
    indices = np.arange(len(groups))
    folds = make_split_specs(indices, groups, y, positions, 2)
    assert set(np.concatenate([va for _, va in folds])) == set(indices)
    for train, valid in folds:
        assert set(groups[train]).isdisjoint(groups[valid])
        for tg in set(groups[train]):
            for vg in set(groups[valid]):
                assert max(abs(positions[int(tg)][0] - positions[int(vg)][0]),
                           abs(positions[int(tg)][1] - positions[int(vg)][1])) > 1


def test_calibration_threshold_and_band_use_spatial_training_predictions():
    groups = np.repeat(np.arange(12), 40)
    positions = {g: (g // 2, g % 2) for g in range(12)}
    y = np.tile(np.r_[np.ones(10, dtype=np.uint8), np.zeros(30, dtype=np.uint8)], 12)
    indices = np.arange(len(groups))
    raw = np.where(y == 1, 0.75, 0.25).astype(float)
    _, calibrated, threshold, details = crossfit_calibration(y, groups, indices, raw, positions)
    assert np.isfinite(calibrated).all()
    assert 0 <= threshold <= 1
    assert details["q90_abs_residual"] >= 0


def test_random_search_configs_are_reproducible_and_have_requested_size():
    a = random_configs("random_forest", seed=20261024, n=30)
    b = random_configs("random_forest", seed=20261024, n=30)
    assert len(a) == 30
    assert a == b
    assert all(isinstance(p["max_features"], str) or isinstance(p["max_features"], float) for p in a)
    assert all(p["max_features"] in ("sqrt", 0.5, 0.8) for p in a)


def test_training_sample_keeps_all_positives_and_uses_three_to_one_negatives():
    y = np.array([1] * 8 + [0] * 40, dtype=np.uint8)
    groups = np.repeat(np.arange(4), 12)
    selected, details = sample_train(np.arange(len(y)), y, groups, seed=7)
    assert int(y[selected].sum()) == 8
    assert int((y[selected] == 0).sum()) == 24
    assert details["negative_to_positive"] == 3


def test_threshold_and_metrics_use_probability_scores_and_report_true_prevalence():
    y = np.array([0, 0, 1, 0, 1, 1], dtype=np.uint8)
    p = np.array([0.05, 0.1, 0.8, 0.2, 0.7, 0.9])
    threshold = select_f1_threshold(y, p)
    result = metric_bundle(y, p, threshold, train_prevalence=0.25, q90=0.3)
    assert 0 <= threshold <= 1
    assert result["prevalence_true"] == 0.5
    assert result["interval_90"]["coverage"] >= 0
    assert "ece_10_equal_width" in result["calibration"]


def test_paired_fold_win_count_treats_lower_brier_as_better():
    result = paired_fold_differences(
        {"candidate": [{"pr_auc": 0.3, "brier": 0.1}, {"pr_auc": 0.4, "brier": 0.2}],
         "baseline": [{"pr_auc": 0.2, "brier": 0.15}, {"pr_auc": 0.5, "brier": 0.1}]},
        "baseline", ["pr_auc", "brier"]
    )["candidate"]
    assert result["pr_auc"]["folds_won"] == 1
    assert result["brier"]["folds_won"] == 1
    assert result["brier"]["mean_delta"] > 0
    assert result["brier"]["win_direction"] == "lower_is_better"
