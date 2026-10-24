"""Unit tests for Phase 9 label, block split and metric logic."""

import numpy as np

from pipelines.phase9.pilot import (
    buffered_train_groups,
    construct_targets,
    correct_sampled_prior,
    metric_bundle,
    threshold_max_f1,
)


def test_construct_targets_subtracts_baseline_and_worldcover_water() -> None:
    nov12 = np.array([[1, 1, 0, 0]], dtype=np.uint8)
    nov24 = np.array([[0, 1, 1, 0]], dtype=np.uint8)
    sep = np.array([[0, 0, 2, 0]], dtype=np.uint8)
    oct14 = np.array([[0, 0, 0, 0]], dtype=np.uint8)
    water_fraction = np.array([[0.0, 0.25, 0.0, 0.0]], dtype=np.float32)

    result = construct_targets(nov12, nov24, sep, oct14, water_fraction)

    assert result["target_2015_11_12"].tolist() == [[True, True, False, False]]
    assert result["target_2015_11_24"].tolist() == [[False, True, True, False]]
    assert result["target_union_minus_baseline"].tolist() == [[True, False, False, False]]
    assert result["excluded_water_mask"].tolist() == [[False, True, True, False]]


def test_buffered_train_groups_has_no_overlap_or_adjacent_test_block() -> None:
    positions = {1: (0, 0), 2: (0, 1), 3: (0, 2), 4: (1, 2), 5: (3, 3)}
    train = np.array([1, 2, 3, 4, 5])
    test = np.array([2])

    kept = buffered_train_groups(train, test, positions, radius=1)

    assert 2 not in kept
    assert 1 not in kept  # touching neighbor is inside the 3 km buffer
    assert 3 not in kept
    assert 4 not in kept
    assert 5 in kept
    assert not (set(kept) & set(test))


def test_threshold_is_selected_on_training_values() -> None:
    y = np.array([0, 0, 1, 1], dtype=np.uint8)
    scores = np.array([0.1, 0.2, 0.8, 0.9])
    threshold = threshold_max_f1(y, scores)
    assert 0.2 <= threshold <= 0.8


def test_threshold_weights_restore_true_training_prevalence() -> None:
    # Case-control sample has 50% positives; the full fold has 1 positive
    # against 100 negatives. Weight each sampled negative to represent 25.
    y = np.array([1, 0, 1, 0], dtype=np.uint8)
    scores = np.array([0.55, 0.52, 0.40, 0.10], dtype=np.float64)
    weights = np.array([1.0, 50.0, 1.0, 50.0])

    sampled_cutoff = threshold_max_f1(y, scores)
    population_cutoff = threshold_max_f1(y, scores, weights)

    assert population_cutoff > sampled_cutoff


def test_metrics_include_calibration_and_area() -> None:
    y = np.array([0, 0, 1, 1], dtype=np.uint8)
    p = np.array([0.1, 0.2, 0.8, 0.9])
    metrics = metric_bundle(y, p, 0.5)
    assert metrics["roc_auc"] == 1.0
    assert metrics["pr_auc_average_precision"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["iou"] == 1.0
    assert metrics["actual_flooded_area_km2"] == 2 * 0.0009
    assert metrics["brier_score"] < 0.05
    assert "expected_calibration_error_10_equal_width_bins" in metrics
    assert metrics["reliability_curve"]


def test_case_control_prior_correction_reduces_sampled_prior() -> None:
    corrected = correct_sampled_prior(np.array([0.5]), 0.25, 0.1)
    assert 0 < corrected[0] < 0.5
