"""Single-event, spatially blocked Nov 2015 flood susceptibility pilot.

Raw files are never read or written. The inputs are existing derived feature and
label rasters. Outputs are refused if any destination already exists.
"""

from __future__ import annotations

import gc
import hashlib
import json
import math
import sys
import argparse
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Compression
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier


ROOT = Path(__file__).resolve().parents[2]
SEED = 20261024
N_SPLITS = 5
BLOCK_BUFFER_RADIUS = 1  # one neighboring 3 km block ring; min train/test gap = 3 km
NEGATIVE_TO_POSITIVE_RATIO = 3
BOOTSTRAP_SIZE = 20
CELL_AREA_KM2 = 0.0009
FEATURES = [
    "elevation_m",
    "slope_deg",
    "twi_d8_proxy",
    "flow_accumulation_cells_d8",
    "built_up_fraction",
    "water_fraction",
    "building_density_per_km2",
    "distance_to_nearest_road_node_m",
    "distance_to_exact_named_waterway_m",
    "worldpop_2021",
    "population_is_nodata",
]
TARGET_CATEGORIES = {
    "logistic_regression": {"C": 1.0, "max_iter": 400, "solver": "lbfgs"},
    "random_forest": {
        "n_estimators": 140,
        "max_depth": 16,
        "min_samples_leaf": 3,
        "max_features": "sqrt",
        "n_jobs": 4,
    },
    "xgboost": {
        "n_estimators": 180,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_lambda": 1.0,
        "tree_method": "hist",
        "n_jobs": 4,
    },
    "lightgbm": {
        "n_estimators": 180,
        "num_leaves": 31,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_lambda": 1.0,
        "n_jobs": 4,
        "verbosity": -1,
    },
}

INPUTS = {
    "cell_table": ROOT / "data/features/static/cell_table.parquet",
    "blocks": ROOT / "data/processed/alignment/spatial_blocks.tif",
    "grid": ROOT / "data/processed/grid/cma_mask.tif",
    "label_12": ROOT / "data/processed/labels_inspection/2015-11-12_EXPLORATORY_NOT_FINAL.tif",
    "label_24": ROOT / "data/processed/labels_inspection/2015-11-24_EXPLORATORY_NOT_FINAL.tif",
    "baseline_sep": ROOT / "data/processed/labels_inspection/2015-09-01_EXPLORATORY_NOT_FINAL.tif",
    "baseline_oct": ROOT / "data/processed/labels_inspection/2015-10-14_EXPLORATORY_NOT_FINAL.tif",
}
OUTPUTS = [
    ROOT / "data/features/predictions/labels_nov2015.parquet",
    ROOT / "data/features/predictions/susceptibility_mean_pilot_single_event.tif",
    ROOT / "data/features/predictions/susceptibility_p05_pilot_single_event.tif",
    ROOT / "data/features/predictions/susceptibility_p95_pilot_single_event.tif",
    ROOT / "docs/PHASE9_METRICS.json",
    ROOT / "docs/PHASE9_MODEL_REGISTRY.json",
    ROOT / "docs/PHASE9_PILOT.md",
    ROOT / "docs/figures/phase9_reliability_pilot.png",
    ROOT / "docs/figures/phase9_feature_importance_pilot.png",
    ROOT / "docs/figures/phase9_labels_pilot.png",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def construct_targets(
    flood_12: np.ndarray,
    flood_24: np.ndarray,
    baseline_sep: np.ndarray,
    baseline_oct: np.ndarray,
    water_fraction: np.ndarray,
) -> dict[str, np.ndarray]:
    """Build raw date labels and the baseline/WorldCover-adjusted union."""
    arrays = (flood_12, flood_24, baseline_sep, baseline_oct, water_fraction)
    if len({np.asarray(a).shape for a in arrays}) != 1:
        raise ValueError("All target and water arrays must have the same shape")
    date_12 = np.asarray(flood_12) == 1
    date_24 = np.asarray(flood_24) == 1
    baseline = (np.asarray(baseline_sep) > 0) | (np.asarray(baseline_oct) > 0)
    worldcover_water = np.isfinite(water_fraction) & (np.asarray(water_fraction) > 0)
    excluded = baseline | worldcover_water
    adjusted_union = (date_12 | date_24) & ~excluded
    return {
        "target_2015_11_12": date_12,
        "target_2015_11_24": date_24,
        "target_union_minus_baseline": adjusted_union,
        "baseline_water_mask": baseline,
        "worldcover_water_mask": worldcover_water,
        "excluded_water_mask": excluded,
    }


def buffered_train_groups(
    train_groups: np.ndarray,
    test_groups: np.ndarray,
    group_positions: dict[int, tuple[int, int]],
    radius: int = BLOCK_BUFFER_RADIUS,
) -> np.ndarray:
    """Drop training groups within `radius` block rings of any test group."""
    test_positions = [group_positions[int(g)] for g in np.unique(test_groups)]
    keep: list[int] = []
    for group in np.unique(train_groups):
        r, c = group_positions[int(group)]
        close = any(max(abs(r - tr), abs(c - tc)) <= radius for tr, tc in test_positions)
        if not close:
            keep.append(int(group))
    return np.asarray(keep, dtype=np.int64)


def threshold_max_f1(y: np.ndarray, scores: np.ndarray,
                     sample_weight: np.ndarray | None = None) -> float:
    """Select a score threshold using training-fold labels only."""
    precision, recall, thresholds = precision_recall_curve(
        y.astype(np.uint8), scores, sample_weight=sample_weight
    )
    if thresholds.size == 0:
        return 0.5
    f1 = 2 * precision[:-1] * recall[:-1] / np.maximum(precision[:-1] + recall[:-1], 1e-12)
    return float(thresholds[int(np.nanargmax(f1))])


def correct_sampled_prior(probabilities: np.ndarray, sample_prevalence: float, population_prevalence: float) -> np.ndarray:
    """Correct case-control probabilities to the training-fold class prevalence."""
    p = np.clip(np.asarray(probabilities, dtype=np.float64), 1e-7, 1 - 1e-7)
    sample_prevalence = float(np.clip(sample_prevalence, 1e-7, 1 - 1e-7))
    population_prevalence = float(np.clip(population_prevalence, 1e-7, 1 - 1e-7))
    ratio = (population_prevalence / (1 - population_prevalence)) / (
        sample_prevalence / (1 - sample_prevalence)
    )
    odds = p / (1 - p) * ratio
    return odds / (1 + odds)


def metric_bundle(y: np.ndarray, probabilities: np.ndarray, threshold: float,
                 binary_predictions: np.ndarray | None = None) -> dict[str, Any]:
    y = np.asarray(y, dtype=np.uint8)
    p = np.clip(np.asarray(probabilities, dtype=np.float64), 0, 1)
    pred = p >= threshold if binary_predictions is None else np.asarray(binary_predictions, dtype=bool)
    tp = int(np.count_nonzero(pred & (y == 1)))
    fp = int(np.count_nonzero(pred & (y == 0)))
    fn = int(np.count_nonzero(~pred & (y == 1)))
    bins = np.linspace(0, 1, 11)
    index = np.minimum(np.digitize(p, bins[1:-1], right=False), 9)
    reliability = []
    ece = 0.0
    for b in range(10):
        m = index == b
        if not np.any(m):
            continue
        mean_p = float(np.mean(p[m]))
        observed = float(np.mean(y[m]))
        count = int(m.sum())
        ece += count / len(y) * abs(mean_p - observed)
        reliability.append({"bin_low": float(bins[b]), "bin_high": float(bins[b + 1]),
                            "mean_probability": mean_p, "observed_fraction": observed, "count": count})
    try:
        roc = float(roc_auc_score(y, p))
    except ValueError:
        roc = None
    try:
        ap = float(average_precision_score(y, p))
    except ValueError:
        ap = None
    return {
        "n": int(len(y)),
        "prevalence": float(np.mean(y)),
        "roc_auc": roc,
        "pr_auc_average_precision": ap,
        "f1": float(f1_score(y, pred, zero_division=0)),
        "iou": float(tp / max(tp + fp + fn, 1)),
        "brier_score": float(brier_score_loss(y, p)),
        "expected_calibration_error_10_equal_width_bins": float(ece),
        "threshold": float(threshold),
        "actual_flooded_area_km2": float(np.sum(y) * CELL_AREA_KM2),
        "predicted_binary_area_km2": float(np.sum(pred) * CELL_AREA_KM2),
        "predicted_probability_area_km2": float(np.sum(p) * CELL_AREA_KM2),
        "reliability_curve": reliability,
    }


def _read_raster(path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    with rasterio.open(path) as ds:
        if ds.count != 1:
            raise ValueError(f"Expected a single-band raster: {path.name}")
        arr = ds.read(1, masked=True).filled(0)
        meta = {
            "width": ds.width,
            "height": ds.height,
            "crs": ds.crs,
            "transform": ds.transform,
            "nodata": ds.nodata,
        }
    return arr, meta


def _validate_inputs(allow_existing_outputs: bool = False) -> dict[str, Any]:
    absent = [str(p.relative_to(ROOT)) for p in INPUTS.values() if not p.is_file()]
    if absent:
        raise FileNotFoundError("Required existing inputs not found: " + ", ".join(absent))
    existing = [str(p.relative_to(ROOT)) for p in OUTPUTS if p.exists()]
    if existing and not allow_existing_outputs:
        raise FileExistsError("Refusing to overwrite existing Phase 9 outputs: " + ", ".join(existing))
    arrays: dict[str, np.ndarray] = {}
    metadata = None
    for key, path in INPUTS.items():
        if key == "cell_table":
            continue
        arrays[key], current = _read_raster(path)
        if metadata is None:
            metadata = current
        elif (current["width"], current["height"], current["crs"], current["transform"]) != (
            metadata["width"], metadata["height"], metadata["crs"], metadata["transform"]
        ):
            raise ValueError(f"Raster grid mismatch for {path.name}")
    if str(metadata["crs"]) != "EPSG:32644":
        raise ValueError(f"Expected EPSG:32644, found {metadata['crs']}")
    return {"arrays": arrays, "metadata": metadata}


def _sample_nonflood_stratified(
    negative_indices: np.ndarray,
    groups: np.ndarray,
    positive_count: int,
    ratio: int,
    rng: np.random.Generator,
) -> np.ndarray:
    target = min(len(negative_indices), positive_count * ratio)
    if target <= 0:
        return np.empty(0, dtype=np.int64)
    group_values, group_counts = np.unique(groups[negative_indices], return_counts=True)
    exact = target * group_counts / group_counts.sum()
    quotas = np.floor(exact).astype(int)
    for idx in np.argsort(-(exact - quotas))[: target - int(quotas.sum())]:
        quotas[idx] += 1
    selected = []
    for group, quota in zip(group_values, quotas):
        if quota:
            candidates = negative_indices[groups[negative_indices] == group]
            selected.append(rng.choice(candidates, size=int(quota), replace=False))
    return np.concatenate(selected).astype(np.int64) if selected else np.empty(0, dtype=np.int64)


def _make_classifier(name: str, seed: int):
    params = dict(TARGET_CATEGORIES[name])
    if name == "logistic_regression":
        estimator = LogisticRegression(C=params["C"], max_iter=params["max_iter"], solver=params["solver"], random_state=seed)
    elif name == "random_forest":
        estimator = RandomForestClassifier(**params, random_state=seed, class_weight=None)
    elif name == "xgboost":
        estimator = XGBClassifier(**params, random_state=seed, eval_metric="logloss")
    elif name == "lightgbm":
        estimator = LGBMClassifier(**params, random_state=seed)
    else:
        raise ValueError(f"Unknown model: {name}")
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
        ("scaler", StandardScaler()),
        ("classifier", estimator),
    ])


def _write_prediction_raster(path: Path, probabilities: np.ndarray, rows: np.ndarray, cols: np.ndarray,
                             meta: dict[str, Any]) -> None:
    nodata = -9999.0
    grid = np.full((meta["height"], meta["width"]), nodata, dtype=np.float32)
    grid[rows, cols] = np.asarray(probabilities, dtype=np.float32)
    profile = {
        "driver": "GTiff", "height": meta["height"], "width": meta["width"], "count": 1,
        "dtype": "float32", "crs": meta["crs"], "transform": meta["transform"],
        "nodata": nodata, "compress": "deflate", "predictor": 3,
    }
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(grid, 1)
        ds.set_band_description(1, "PILOT single-event susceptibility probability")


def run(recompute_metrics: bool = False) -> dict[str, Any]:
    checked = _validate_inputs(allow_existing_outputs=recompute_metrics)
    rasters = checked["arrays"]
    grid_meta = checked["metadata"]
    source = pd.read_parquet(INPUTS["cell_table"], columns=["row", "col", "cell_id", *FEATURES])
    rows = source["row"].to_numpy(dtype=np.int32)
    cols = source["col"].to_numpy(dtype=np.int32)
    if len(source) != 1_319_380:
        raise ValueError(f"Unexpected static cell table row count: {len(source)}")
    if rows.min() < 0 or cols.min() < 0 or rows.max() >= grid_meta["height"] or cols.max() >= grid_meta["width"]:
        raise ValueError("Static cell table row/column lies outside master grid")
    blocks = rasters["blocks"][rows, cols].astype(np.int32)
    if np.any(blocks == 0):
        raise ValueError("Some static CMA cells have block ID zero")
    features = source[FEATURES].to_numpy(dtype=np.float32, na_value=np.nan)
    if np.any(np.isinf(features)):
        features[np.isinf(features)] = np.nan
    targets = construct_targets(
        rasters["label_12"][rows, cols], rasters["label_24"][rows, cols],
        rasters["baseline_sep"][rows, cols], rasters["baseline_oct"][rows, cols],
        source["water_fraction"].to_numpy(dtype=np.float32),
    )
    y_all = targets["target_union_minus_baseline"].astype(np.uint8)
    eligible = ~targets["excluded_water_mask"]
    eligible_indices = np.flatnonzero(eligible)
    if np.unique(y_all[eligible]).size < 2:
        raise ValueError("The eligible label grid must contain both flooded and non-flooded cells")
    y = y_all[eligible_indices]
    groups = blocks[eligible_indices]
    x = features[eligible_indices]
    eligible_rows, eligible_cols = rows[eligible_indices], cols[eligible_indices]
    group_positions: dict[int, tuple[int, int]] = {}
    for group, row, col in zip(blocks, rows, cols):
        pos = (int(row // 100), int(col // 100))
        old = group_positions.setdefault(int(group), pos)
        if old != pos:
            raise ValueError(f"Spatial block ID {group} maps to multiple 3 km cells")
    if len(group_positions) < N_SPLITS:
        raise ValueError("Not enough spatial blocks for five-fold validation")

    group_kfold = GroupKFold(n_splits=N_SPLITS)
    fold_specs = []
    for fold_number, (train_local, test_local) in enumerate(group_kfold.split(x, y, groups), start=1):
        train_group_set = np.unique(groups[train_local])
        test_group_set = np.unique(groups[test_local])
        kept_groups = buffered_train_groups(train_group_set, test_group_set, group_positions)
        train_local = train_local[np.isin(groups[train_local], kept_groups)]
        if not len(train_local) or not len(test_local) or len(np.unique(y[train_local])) < 2:
            raise ValueError(f"Spatial fold {fold_number} has insufficient train/test labels after buffering")
        fold_specs.append((fold_number, train_local, test_local, len(kept_groups), len(test_group_set)))

    model_names = list(TARGET_CATEGORIES)
    score_names = model_names + ["elevation_only_threshold", "river_distance_only", "random"]
    predictions = {name: np.full(len(eligible_indices), np.nan, dtype=np.float32) for name in score_names}
    decision_predictions = {name: np.zeros(len(eligible_indices), dtype=np.uint8) for name in score_names}
    fold_metrics: dict[str, list[dict[str, Any]]] = {name: [] for name in score_names}
    fold_info: list[dict[str, Any]] = []
    importances: dict[str, list[dict[str, float]]] = {name: [] for name in model_names}
    thresholds_by_fold: dict[str, list[float]] = {name: [] for name in score_names}

    for fold_number, train_local, test_local, retained_blocks, test_blocks in fold_specs:
        fold_seed = SEED + fold_number
        rng = np.random.default_rng(fold_seed)
        train_pos_local = train_local[y[train_local] == 1]
        train_neg_local = train_local[y[train_local] == 0]
        sampled_neg = _sample_nonflood_stratified(
            train_neg_local, groups, len(train_pos_local), NEGATIVE_TO_POSITIVE_RATIO, rng
        )
        sampled_local = np.concatenate([train_pos_local, sampled_neg])
        rng.shuffle(sampled_local)
        y_sample = y[sampled_local]
        if len(np.unique(y_sample)) < 2:
            raise ValueError(f"Fold {fold_number} training sample has a single class")
        test_truth = y[test_local]
        threshold_weights = np.ones(len(sampled_local), dtype=np.float64)
        if len(sampled_neg):
            threshold_weights[y_sample == 0] = len(train_neg_local) / len(sampled_neg)
        fold_record = {
            "fold": fold_number,
            "buffered_train_blocks": retained_blocks,
            "test_blocks": test_blocks,
            "train_cells_after_buffer": int(len(train_local)),
            "train_flood_cells_used": int(len(train_pos_local)),
            "train_nonflood_sampled": int(len(sampled_neg)),
            "train_nonflood_to_flood_ratio": float(len(sampled_neg) / max(len(train_pos_local), 1)),
            "test_cells_full_true_prevalence": int(len(test_local)),
            "test_prevalence": float(np.mean(test_truth)),
        }

        for model_name in model_names:
            estimator = _make_classifier(model_name, fold_seed)
            estimator.fit(x[sampled_local], y_sample)
            train_sample_p = estimator.predict_proba(x[sampled_local])[:, 1]
            train_p = correct_sampled_prior(train_sample_p, float(np.mean(y_sample)), float(np.mean(y[train_local])))
            threshold = threshold_max_f1(y_sample, train_p, threshold_weights)
            test_p_raw = estimator.predict_proba(x[test_local])[:, 1]
            test_p = correct_sampled_prior(test_p_raw, float(np.mean(y_sample)), float(np.mean(y[train_local])))
            predictions[model_name][test_local] = test_p.astype(np.float32)
            decision_predictions[model_name][test_local] = (test_p >= threshold).astype(np.uint8)
            metrics = metric_bundle(test_truth, test_p, threshold)
            fold_metrics[model_name].append(metrics)
            thresholds_by_fold[model_name].append(threshold)

            imp_rng = np.random.default_rng(fold_seed + 100)
            importance_sample = imp_rng.choice(test_local, size=min(2000, len(test_local)), replace=False)
            if np.unique(y[importance_sample]).size == 2:
                imp = permutation_importance(
                    estimator, x[importance_sample], y[importance_sample],
                    scoring="average_precision", n_repeats=2, random_state=fold_seed, n_jobs=1,
                )
                importances[model_name].append({
                    feature: float(value) for feature, value in zip(FEATURES, imp.importances_mean)
                })
            del estimator
            gc.collect()

        # Threshold-only physical baselines, calibrated from training rows only.
        elevation_column = FEATURES.index("elevation_m")
        river_column = FEATURES.index("distance_to_exact_named_waterway_m")
        medians = np.nanmedian(x[sampled_local], axis=0)
        train_x = np.where(np.isfinite(x[sampled_local]), x[sampled_local], medians)
        test_x = np.where(np.isfinite(x[test_local]), x[test_local], medians)
        baseline_defs = {
            "elevation_only_threshold": (elevation_column, -1.0),
            "river_distance_only": (river_column, -1.0),
        }
        for base_name, (column, sign) in baseline_defs.items():
            train_score = sign * train_x[:, column]
            base_threshold = threshold_max_f1(y_sample, train_score, threshold_weights)
            test_score = sign * test_x[:, column]
            test_p = (test_score >= base_threshold).astype(np.float32)
            predictions[base_name][test_local] = test_p
            decision_predictions[base_name][test_local] = test_p.astype(np.uint8)
            metrics = metric_bundle(test_truth, test_p, 0.5)
            metrics["training_score_threshold"] = float(base_threshold)
            fold_metrics[base_name].append(metrics)
            thresholds_by_fold[base_name].append(float(base_threshold))
        random_train = np.random.default_rng(fold_seed + 200).random(len(sampled_local))
        random_threshold = threshold_max_f1(y_sample, random_train, threshold_weights)
        random_test = np.random.default_rng(fold_seed + 300).random(len(test_local)).astype(np.float32)
        predictions["random"][test_local] = random_test
        decision_predictions["random"][test_local] = (random_test >= random_threshold).astype(np.uint8)
        random_metrics = metric_bundle(test_truth, random_test, random_threshold)
        fold_metrics["random"].append(random_metrics)
        thresholds_by_fold["random"].append(random_threshold)
        fold_record["test_block_ids"] = [int(v) for v in test_group_set]
        fold_record["buffered_training_block_ids"] = [int(v) for v in kept_groups]
        fold_info.append(fold_record)
        print(f"Completed spatial fold {fold_number}/{N_SPLITS}", flush=True)

    if any(np.isnan(predictions[name]).any() for name in score_names):
        raise RuntimeError("Out-of-fold predictions do not cover every eligible cell exactly once")

    overall: dict[str, Any] = {}
    fold_spread: dict[str, Any] = {}
    baseline_comparisons = {}
    for name in score_names:
        overall[name] = metric_bundle(
            y, predictions[name], float(np.mean(thresholds_by_fold[name])),
            binary_predictions=decision_predictions[name],
        )
        overall[name]["fold_specific_threshold_f1_iou_applied"] = True
        overall[name]["threshold_mean"] = float(np.mean(thresholds_by_fold[name]))
        overall[name]["threshold_std"] = float(np.std(thresholds_by_fold[name], ddof=1))
        numeric_metrics = [
            "roc_auc", "pr_auc_average_precision", "f1", "iou", "brier_score",
            "expected_calibration_error_10_equal_width_bins", "actual_flooded_area_km2",
            "predicted_binary_area_km2", "predicted_probability_area_km2",
        ]
        fold_spread[name] = {}
        for metric in numeric_metrics:
            values = [entry[metric] for entry in fold_metrics[name] if entry.get(metric) is not None]
            fold_spread[name][metric] = {
                "mean": float(np.mean(values)) if values else None,
                "std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0 if values else None,
            }
    baseline_names = ["elevation_only_threshold", "river_distance_only", "random"]
    best_model = max(model_names, key=lambda name: overall[name]["pr_auc_average_precision"] or -1)
    for name in model_names:
        baseline_comparisons[name] = {
            baseline: {
                "beats_baseline_on_overall_pr_auc": bool(
                    overall[name]["pr_auc_average_precision"] > overall[baseline]["pr_auc_average_precision"]
                ),
                "model_pr_auc": overall[name]["pr_auc_average_precision"],
                "baseline_pr_auc": overall[baseline]["pr_auc_average_precision"],
            }
            for baseline in baseline_names
        }

    # Permutation importances were computed on full-prevalence held-out fold subsets.
    importance_summary = {}
    for name, entries in importances.items():
        for feature in FEATURES:
            vals = [entry[feature] for entry in entries]
            importance_summary.setdefault(name, {})[feature] = {
                "mean_average_precision_drop": float(np.mean(vals)) if vals else None,
                "std_across_folds": float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0 if vals else None,
            }

    source_hashes = {key: sha256(path) for key, path in INPUTS.items()}
    data_hash = hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest()
    eligible_prevalence = float(np.mean(y))
    label_counts = {
        "cma_cell_count": int(len(source)),
        "excluded_baseline_cells": int(np.count_nonzero(targets["baseline_water_mask"])),
        "excluded_worldcover_water_cells": int(np.count_nonzero(targets["worldcover_water_mask"])),
        "excluded_water_union_cells": int(np.count_nonzero(targets["excluded_water_mask"])),
        "eligible_land_cells": int(len(eligible_indices)),
        "target_2015_11_12_flooded_eligible": int(np.count_nonzero(targets["target_2015_11_12"][eligible])),
        "target_2015_11_24_flooded_eligible": int(np.count_nonzero(targets["target_2015_11_24"][eligible])),
        "target_union_minus_baseline_flooded_eligible": int(np.sum(y)),
        "target_union_minus_baseline_prevalence": eligible_prevalence,
        "target_union_minus_baseline_area_km2": float(np.sum(y) * CELL_AREA_KM2),
        "raw_12_nov_prevalence_eligible": float(np.mean(targets["target_2015_11_12"][eligible])),
        "raw_24_nov_prevalence_eligible": float(np.mean(targets["target_2015_11_24"][eligible])),
    }

    # Bootstrap ensemble for the CV-selected model. During a metrics-only
    # correction pass, retain the already generated ensemble if the best model
    # is unchanged; do not rewrite any raster or label outputs.
    best_params = dict(TARGET_CATEGORIES[best_model])
    all_indices = np.flatnonzero(eligible)
    if recompute_metrics:
        old_registry = json.loads(OUTPUTS[5].read_text(encoding="utf-8"))
        if old_registry.get("selected_bootstrap_model") != best_model:
            raise RuntimeError("Corrected CV selected a different best model; existing ensemble rasters cannot be reused")
        bootstrap_size = int(old_registry["bootstrap_size"])
        existing_probability_rasters = []
        for path in OUTPUTS[1:4]:
            with rasterio.open(path) as ds:
                existing_probability_rasters.append(ds.read(1)[rows[all_indices], cols[all_indices]])
        pred_mean, pred_p05, pred_p95 = existing_probability_rasters
    else:
        positive_all = all_indices[y_all[all_indices] == 1]
        negative_all = all_indices[y_all[all_indices] == 0]
        boot_rng = np.random.default_rng(SEED + 9000)
        negative_sample = _sample_nonflood_stratified(
            negative_all, blocks, len(positive_all), NEGATIVE_TO_POSITIVE_RATIO, boot_rng
        )
        ensemble_base = np.concatenate([positive_all, negative_sample])
        population_prior = float(np.mean(y_all[all_indices]))
        ensemble_predictions = np.empty((BOOTSTRAP_SIZE, len(all_indices)), dtype=np.float32)
        for member in range(BOOTSTRAP_SIZE):
            rng = np.random.default_rng(SEED + 10000 + member)
            bootstrap_rows = rng.choice(ensemble_base, size=len(ensemble_base), replace=True)
            bootstrap_labels = y_all[bootstrap_rows]
            model = _make_classifier(best_model, SEED + 10000 + member)
            model.fit(features[bootstrap_rows], bootstrap_labels)
            raw_p = model.predict_proba(features[all_indices])[:, 1]
            ensemble_predictions[member] = correct_sampled_prior(
                raw_p, float(np.mean(bootstrap_labels)), population_prior
            ).astype(np.float32)
            del model
            gc.collect()
            print(f"Completed bootstrap member {member + 1}/{BOOTSTRAP_SIZE}", flush=True)
        pred_mean = np.mean(ensemble_predictions, axis=0)
        pred_p05 = np.quantile(ensemble_predictions, 0.05, axis=0).astype(np.float32)
        pred_p95 = np.quantile(ensemble_predictions, 0.95, axis=0).astype(np.float32)
        del ensemble_predictions
        bootstrap_size = BOOTSTRAP_SIZE

    metrics_doc = {
        "pilot_status": "PILOT, SINGLE EVENT",
        "label_status": "OFFICIAL SAR-DERIVED, NOT FIELD-VALIDATED",
        "default_target": "target_union_minus_baseline",
        "target_counts_and_prevalence": label_counts,
        "grid": {"crs": "EPSG:32644", "pixel_size_m": 30, "cell_area_km2": CELL_AREA_KM2,
                 "width": grid_meta["width"], "height": grid_meta["height"]},
        "features": FEATURES,
        "excluded_feature": {"distance_to_coast_m": "all cells are NoData in cell_table.parquet"},
        "validation": {
            "method": "5-fold GroupKFold by 3 km spatial block; full eligible test blocks evaluated at true prevalence",
            "buffer": "Exclude training blocks in the eight-neighbor ring around test blocks; one 3 km block buffer from test-block edge",
            "folds": fold_info,
            "train_negative_to_positive_ratio": NEGATIVE_TO_POSITIVE_RATIO,
            "negative_sampling": "stratified without replacement by spatial block",
            "seed": SEED,
            "threshold_selection": "maximum weighted F1 using in-sample predictions on the sampled training fold; test blocks never used to choose thresholds",
            "threshold_selection_weights": "Apply inverse negative-sampling weights when selecting thresholds so the training-fold objective reflects its true prevalence; raw model fitting still uses the specified 3:1 sampled set.",
            "threshold_caveat": "Tree models can overfit their in-sample threshold calibration; fold metrics remain out-of-block but threshold choice may be optimistic.",
        },
        "per_fold_metrics": fold_metrics,
        "fold_metric_mean_and_std": fold_spread,
        "overall_out_of_fold_metrics": overall,
        "beats_baselines_by_pr_auc": baseline_comparisons,
        "permutation_feature_importance": {
            "method": "mean decrease in average precision, 2 repeats per fold on up to 2,000 held-out full-prevalence cells",
            "by_model": importance_summary,
        },
        "bootstrap_uncertainty": {
            "model": best_model,
            "ensemble_size": bootstrap_size,
            "seed_base": SEED + 10000,
            "negative_to_positive_ratio": NEGATIVE_TO_POSITIVE_RATIO,
            "outputs": [str(p.relative_to(ROOT)) for p in OUTPUTS[1:4]],
        },
        "input_sha256": source_hashes,
        "data_hash_sha256": data_hash,
    }
    registry = {
        "registry_version": 1,
        "pilot_status": "PILOT, SINGLE EVENT",
        "default_target": "target_union_minus_baseline",
        "data_hash_sha256": data_hash,
        "input_sha256": source_hashes,
        "models": [
            {"model": name, "parameters": dict(TARGET_CATEGORIES[name]), "seed": SEED,
             "metrics": overall[name], "fold_mean_std": fold_spread[name],
             "beats_baselines_by_pr_auc": baseline_comparisons[name]}
            for name in model_names
        ],
        "selected_bootstrap_model": best_model,
        "bootstrap_parameters": best_params,
        "bootstrap_seed_base": SEED + 10000,
        "bootstrap_size": bootstrap_size,
    }

    _publish_outputs(source, targets, eligible, eligible_indices, eligible_rows, eligible_cols,
                     pred_mean, pred_p05, pred_p95, metrics_doc, registry, overall,
                     importance_summary, rasters["grid"], grid_meta,
                     refresh_docs=recompute_metrics)
    return metrics_doc


def _publish_outputs(source: pd.DataFrame, targets: dict[str, np.ndarray], eligible: np.ndarray,
                     eligible_indices: np.ndarray, rows: np.ndarray, cols: np.ndarray,
                     pred_mean: np.ndarray, pred_p05: np.ndarray, pred_p95: np.ndarray,
                     metrics_doc: dict[str, Any], registry: dict[str, Any], overall: dict[str, Any],
                     importance_summary: dict[str, Any], cma_mask: np.ndarray,
                     grid_meta: dict[str, Any], refresh_docs: bool = False) -> None:
    # Existing destinations are always preserved. The normal run preflights all
    # names before computation; this per-file guard also supports recovery after
    # a report-generation failure.
    pred_dir = OUTPUTS[0].parent
    fig_dir = ROOT / "docs/figures"
    pred_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    score_names = list(metrics_doc["per_fold_metrics"])
    model_names = list(TARGET_CATEGORIES)
    baseline_names = ["elevation_only_threshold", "river_distance_only", "random"]
    baseline_comparisons = metrics_doc["beats_baselines_by_pr_auc"]
    best_model = max(model_names, key=lambda n: overall[n]["pr_auc_average_precision"] or -1)

    target_table = pd.DataFrame({
        "row": source["row"].to_numpy(dtype=np.int32),
        "col": source["col"].to_numpy(dtype=np.int32),
        "cell_id": source["cell_id"].astype(str),
        "target_2015_11_12": targets["target_2015_11_12"].astype(np.uint8),
        "target_2015_11_24": targets["target_2015_11_24"].astype(np.uint8),
        "target_union_minus_baseline": targets["target_union_minus_baseline"].astype(np.uint8),
        "baseline_water_mask": targets["baseline_water_mask"].astype(bool),
        "worldcover_water_mask": targets["worldcover_water_mask"].astype(bool),
        "eligible_for_model": eligible.astype(bool),
    })
    if not OUTPUTS[0].exists():
        target_table.to_parquet(OUTPUTS[0], index=False, compression="zstd")
    if not OUTPUTS[1].exists():
        _write_prediction_raster(OUTPUTS[1], pred_mean, rows, cols, grid_meta)
    if not OUTPUTS[2].exists():
        _write_prediction_raster(OUTPUTS[2], pred_p05, rows, cols, grid_meta)
    if not OUTPUTS[3].exists():
        _write_prediction_raster(OUTPUTS[3], pred_p95, rows, cols, grid_meta)
    if refresh_docs or not OUTPUTS[4].exists():
        OUTPUTS[4].write_text(json.dumps(metrics_doc, indent=2, allow_nan=False), encoding="utf-8")
    if refresh_docs or not OUTPUTS[5].exists():
        OUTPUTS[5].write_text(json.dumps(registry, indent=2, allow_nan=False), encoding="utf-8")

    # Reliability plot from overall out-of-fold bins.
    if not OUTPUTS[7].exists():
        fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)
        ax.plot([0, 1], [0, 1], linestyle="--", color="0.4", label="Perfect calibration")
        for name, item in overall.items():
            curve = item["reliability_curve"]
            ax.plot([r["mean_probability"] for r in curve], [r["observed_fraction"] for r in curve],
                    marker="o", linewidth=1.2, label=name.replace("_", " "))
        ax.set(xlabel="Mean predicted probability", ylabel="Observed flooded fraction",
               title="Nov 2015 blocked out-of-fold reliability")
        ax.legend(fontsize=7)
        ax.grid(alpha=0.25)
        fig.savefig(OUTPUTS[7], dpi=160)
        plt.close(fig)

    best_name = max(TARGET_CATEGORIES, key=lambda n: overall[n]["pr_auc_average_precision"] or -1)
    importance = importance_summary.get(best_name, {})
    order = sorted(importance, key=lambda f: importance[f]["mean_average_precision_drop"] or -math.inf)
    if not OUTPUTS[8].exists():
        fig, ax = plt.subplots(figsize=(8, 6), constrained_layout=True)
        values = [importance[f]["mean_average_precision_drop"] or 0 for f in order]
        errors = [importance[f]["std_across_folds"] or 0 for f in order]
        ax.barh(order, values, xerr=errors, color="#3572A5", alpha=0.9)
        ax.set(xlabel="Held-out average-precision drop after permutation",
               title=f"Permutation importance: {best_name.replace('_', ' ')}")
        ax.grid(axis="x", alpha=0.25)
        fig.savefig(OUTPUTS[8], dpi=160)
        plt.close(fig)

    if not OUTPUTS[9].exists():
        fig, ax = plt.subplots(figsize=(8, 8), constrained_layout=True)
        label_grid = np.full((grid_meta["height"], grid_meta["width"]), np.nan, dtype=np.float32)
        # Requested display uses the default target; cma_mask ensures outside-CMA cells are blank.
        label_grid[rows, cols] = targets["target_union_minus_baseline"][eligible].astype(np.float32)
        label_grid[~(cma_mask == 1)] = np.nan
        ax.imshow(label_grid, cmap="Blues", vmin=0, vmax=1, interpolation="nearest")
        ax.set(title="Nov 2015 UNOSAT union minus baseline and WorldCover water", xlabel="Master-grid column", ylabel="Master-grid row")
        fig.savefig(OUTPUTS[9], dpi=160)
        plt.close(fig)

    # Build a concise report from real computed values.
    target_stats = metrics_doc["target_counts_and_prevalence"]
    lines = [
        "# Phase 9 pilot — November 2015 flood susceptibility baseline",
        "",
        "> **PILOT, SINGLE EVENT — OFFICIAL SAR-DERIVED, NOT FIELD-VALIDATED.** This is a susceptibility model for spatial pattern, not a time-varying forecast.",
        "",
        "## Label and eligible cells",
        "",
        "| Quantity | Result |",
        "|---|---:|",
        f"| CMA grid cells in static table | {target_stats['cma_cell_count']:,} |",
        f"| Baseline-water cells excluded | {target_stats['excluded_baseline_cells']:,} |",
        f"| WorldCover water cells excluded | {target_stats['excluded_worldcover_water_cells']:,} |",
        f"| Unique cells excluded by the combined water mask | {target_stats['excluded_water_union_cells']:,} |",
        f"| Eligible cells | {target_stats['eligible_land_cells']:,} |",
        f"| 12 Nov positives among eligible cells | {target_stats['target_2015_11_12_flooded_eligible']:,} ({target_stats['raw_12_nov_prevalence_eligible']:.4%}) |",
        f"| 24 Nov positives among eligible cells | {target_stats['target_2015_11_24_flooded_eligible']:,} ({target_stats['raw_24_nov_prevalence_eligible']:.4%}) |",
        f"| Default union-minus-baseline positives | {target_stats['target_union_minus_baseline_flooded_eligible']:,} ({target_stats['target_union_minus_baseline_prevalence']:.4%}) |",
        f"| Default target area at 30 m cell area | {target_stats['target_union_minus_baseline_area_km2']:.2f} km² |",
        "",
        "The default target is the union of the 12 and 24 November UNOSAT rasters after subtracting every non-zero cell in the 1 September and 14 October baseline layers and any WorldCover water fraction above zero. The baseline layers include uncertain wet-soil class 2, so the subtraction is an unverified label choice. Sea is excluded where represented by WorldCover water; there is no separate sea mask in the cell table.",
        "",
        "## Inputs and model design",
        "",
        "Predictors came only from `data/features/static/cell_table.parquet`: cleaned elevation, slope, TWI proxy, D8 flow accumulation, built-up/water fractions, OSM building density, road and named-waterway distances, WorldPop 2021 and its NoData flag. Coast distance was omitted because it is NoData for every cell. The water fraction is retained as specified but becomes zero for eligible cells because all positive water fractions were masked.",
        "",
        f"Validation used five folds of whole 3 km blocks, a one-block neighbor buffer between training and test blocks, and complete eligible test blocks at their true prevalence. Each model used every flooded training-fold cell plus a spatial-block-stratified sample of nonflooded cells at {NEGATIVE_TO_POSITIVE_RATIO}:1, seed {SEED}. Imputation and scaling were fitted within each training fold. Probability prior correction uses only training-fold prevalence. Threshold selection weights sampled negatives by the inverse sampling fraction, restoring true training-fold prevalence for the F1 objective; thresholds are still selected on in-sample predictions and can be optimistic.",
        "",
        "Fixed model settings were used; no hyperparameter search was run. The bootstrap uncertainty ensemble has 20 resampled fits of the CV-selected model. Its full-grid probability rasters are fitted on the complete eligible single-event dataset (apparent pilot maps), not out-of-fold predictions. They capture model/resampling spread, not all label or source uncertainty; use the blocked CV metrics to judge performance.",
        "",
        "## Out-of-fold model results",
        "",
        "PR-AUC is average precision. Fold spread is mean ± sample standard deviation. The overall columns aggregate the out-of-fold predictions; F1/IoU use the threshold selected separately on each training fold.",
        "",
        "| Model | ROC-AUC pooled (fold mean ± SD) | PR-AUC pooled (fold mean ± SD) | F1 mean ± SD | IoU mean ± SD | Brier pooled (fold mean ± SD) | ECE pooled (fold mean ± SD) | Predicted area vs actual (km²) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model_name in list(TARGET_CATEGORIES) + ["elevation_only_threshold", "river_distance_only", "random"]:
        allm = overall[model_name]
        spread = metrics_doc["fold_metric_mean_and_std"][model_name]
        lines.append(
            f"| {model_name.replace('_',' ')} | {allm['roc_auc']:.4f} ({spread['roc_auc']['mean']:.4f} ± {spread['roc_auc']['std']:.4f}) | {allm['pr_auc_average_precision']:.4f} ({spread['pr_auc_average_precision']['mean']:.4f} ± {spread['pr_auc_average_precision']['std']:.4f}) | "
            f"{spread['f1']['mean']:.4f} ± {spread['f1']['std']:.4f} | {spread['iou']['mean']:.4f} ± {spread['iou']['std']:.4f} | "
            f"{allm['brier_score']:.4f} ({spread['brier_score']['mean']:.4f} ± {spread['brier_score']['std']:.4f}) | {allm['expected_calibration_error_10_equal_width_bins']:.4f} ({spread['expected_calibration_error_10_equal_width_bins']['mean']:.4f} ± {spread['expected_calibration_error_10_equal_width_bins']['std']:.4f}) | "
            f"{allm['predicted_binary_area_km2']:.2f} vs {allm['actual_flooded_area_km2']:.2f} |"
        )
    lines += ["", "### Per-fold performance and uncertainty", "", "| Model | Fold | ROC-AUC | PR-AUC | F1 | IoU | Brier | ECE | Threshold | Actual / predicted area km² |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for model_name in score_names:
        for i, item in enumerate(metrics_doc["per_fold_metrics"][model_name], start=1):
            lines.append(
                f"| {model_name.replace('_',' ')} | {i} | {item['roc_auc']:.4f} | {item['pr_auc_average_precision']:.4f} | "
                f"{item['f1']:.4f} | {item['iou']:.4f} | {item['brier_score']:.4f} | "
                f"{item['expected_calibration_error_10_equal_width_bins']:.4f} | {item.get('training_score_threshold', item.get('threshold', 0.5)):.4f} | "
                f"{item['actual_flooded_area_km2']:.2f} / {item['predicted_binary_area_km2']:.2f} |"
            )
    lines += ["", "## Baseline comparison", "", f"The CV-selected model by overall PR-AUC was **{best_model.replace('_',' ')}**. Each model's PR-AUC comparison with each simple baseline is:", "", "| Model | Elevation-only baseline | River-distance-only baseline | Random baseline |", "|---|---|---|---|"]
    for model_name in model_names:
        vals = baseline_comparisons[model_name]
        lines.append("| " + model_name.replace("_", " ") + " | " + " | ".join(
            f"{'beats' if vals[b]['beats_baseline_on_overall_pr_auc'] else 'does not beat'} ({vals[b]['model_pr_auc']:.4f} vs {vals[b]['baseline_pr_auc']:.4f})"
            for b in baseline_names
        ) + " |")
    lines += ["", "## Permutation importance", "", f"Mean average-precision decrease on held-out fold samples for {best_model.replace('_',' ')} (2 permutations, up to 2,000 cells per fold):", "", "| Feature | Mean PR-AUC drop | Across-fold SD |", "|---|---:|---:|"]
    for feature, values in sorted(importance_summary.get(best_model, {}).items(), key=lambda x: x[1]["mean_average_precision_drop"] or -math.inf, reverse=True):
        lines.append(f"| {feature} | {values['mean_average_precision_drop'] if values['mean_average_precision_drop'] is not None else float('nan'):.6f} | {values['std_across_folds'] if values['std_across_folds'] is not None else float('nan'):.6f} |")
    lines += [
        "",
        "## Figures and prediction rasters",
        "",
        "![Blocked out-of-fold reliability](figures/phase9_reliability_pilot.png)",
        "",
        "![Selected-model permutation importance](figures/phase9_feature_importance_pilot.png)",
        "",
        "![Default label](figures/phase9_labels_pilot.png)",
        "",
        "PILOT single-event ensemble GeoTIFFs on the master grid: mean probability, 5th percentile and 95th percentile are under `data/features/predictions/`. Outside-CMA cells, masked water/sea and cells not in the cell table remain NoData (-9999). The cell-level three-target table is `data/features/predictions/labels_nov2015.parquet`.",
        "",
        "## Leakage review, interpretation and remaining labels",
        "",
        "- No input feature is derived from the November target rasters. The September/October and WorldCover masks are used only to construct/exclude labels; rows masked by them are not evaluated.",
        "- Thresholds are selected on training-fold predictions with inverse negative-sampling weights to restore true fold prevalence; tree thresholds can still be optimistic because predictions are in-sample.",
        "- Entire block IDs stay on one side of each fold. Training blocks within one block ring of the held-out blocks are removed. Feature imputation/scaling and negative sampling happen after each split and use training-fold cells only.",
        "- The models use static inputs and one November 2015 label. They estimate relative spatial susceptibility for this one event; they do not predict when or how deep future flooding will be.",
        "- The mean and percentile map rasters are full-data bootstrap predictions for visualization, not held-out maps; only the reported fold metrics are out-of-block evaluation.",
        "- The November UNOSAT layers do not cover the 1–8 Dec 2015 peak. WorldCover is 2021, and WorldPop is an alpha model product; temporal and source limitations remain.",
        "- A single event cannot test cross-event generalisation or support hypotheses H1 to H5. Do not claim these results establish forecast skill or field accuracy.",
        "- Needed next: digitised and checked December 2015 extent, manually digitised/georeferenced 2021 and 2023 NRSC PDFs, and independent field/gauge or authoritative flood observations. Labels need dates, uncertainty and provenance.",
        "",
        f"Input data hash: `{metrics_doc['data_hash_sha256']}`. Detailed fold data and model settings are in `PHASE9_METRICS.json` and `PHASE9_MODEL_REGISTRY.json`.",
        "",
    ]
    if refresh_docs or not OUTPUTS[6].exists():
        OUTPUTS[6].write_text("\n".join(lines), encoding="utf-8")


def complete_existing_outputs() -> None:
    """Fill missing report artifacts from a completed, existing model run."""
    required = [OUTPUTS[0], OUTPUTS[1], OUTPUTS[2], OUTPUTS[3], OUTPUTS[4], OUTPUTS[5]]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError("Cannot finish report; completed run outputs missing: " + ", ".join(missing))
    if OUTPUTS[6].exists() and OUTPUTS[9].exists():
        raise FileExistsError("Report and label figure already exist; refusing to replace them")
    metrics_doc = json.loads(OUTPUTS[4].read_text(encoding="utf-8"))
    registry = json.loads(OUTPUTS[5].read_text(encoding="utf-8"))
    table = pd.read_parquet(OUTPUTS[0])
    source = table[["row", "col", "cell_id"]]
    targets = {
        name: table[name].to_numpy(dtype=bool)
        for name in ("target_2015_11_12", "target_2015_11_24", "target_union_minus_baseline",
                     "baseline_water_mask", "worldcover_water_mask")
    }
    targets["target_2015_11_12"] = targets.pop("target_2015_11_12")
    targets["target_2015_11_24"] = targets.pop("target_2015_11_24")
    targets["target_union_minus_baseline"] = targets.pop("target_union_minus_baseline")
    targets["excluded_water_mask"] = targets["baseline_water_mask"] | targets["worldcover_water_mask"]
    eligible = table["eligible_for_model"].to_numpy(dtype=bool)
    eligible_rows = source["row"].to_numpy(dtype=np.int32)[eligible]
    eligible_cols = source["col"].to_numpy(dtype=np.int32)[eligible]
    arrays, grid_meta = _read_raster(INPUTS["grid"])
    pred_vals = []
    for path in OUTPUTS[1:4]:
        with rasterio.open(path) as ds:
            pred_vals.append(ds.read(1)[eligible_rows, eligible_cols])
    _publish_outputs(
        source, targets, eligible, np.flatnonzero(eligible), eligible_rows, eligible_cols,
        pred_vals[0], pred_vals[1], pred_vals[2], metrics_doc, registry,
        metrics_doc["overall_out_of_fold_metrics"],
        metrics_doc["permutation_feature_importance"]["by_model"], arrays, grid_meta,
    )


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--complete-existing", action="store_true",
                            help="create only missing report artifacts from an already written Phase 9 run")
        parser.add_argument("--recompute-metrics", action="store_true",
                            help="rerun blocked CV and refresh metrics/docs while preserving existing labels and prediction rasters")
        options = parser.parse_args()
        if options.complete_existing and options.recompute_metrics:
            parser.error("choose only one recovery option")
        if options.complete_existing:
            complete_existing_outputs()
            print("Completed missing Phase 9 report artifacts; existing data outputs were preserved.")
            raise SystemExit(0)
        result = run(recompute_metrics=options.recompute_metrics)
    except Exception as exc:
        print(f"Phase 9 pilot failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
    print("Phase 9 single-event susceptibility pilot completed.")
    print("Eligible cells:", result["target_counts_and_prevalence"]["eligible_land_cells"])
    print("Default-target prevalence:", f"{result['target_counts_and_prevalence']['target_union_minus_baseline_prevalence']:.6%}")
    print("Selected bootstrap model:", result["bootstrap_uncertainty"]["model"])
