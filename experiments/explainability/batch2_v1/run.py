"""A12 diagnostic explainability and existing-simulation sensitivity analysis."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from sklearn.metrics import average_precision_score

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from pipelines.phase9b import model_upgrade as p9  # noqa: E402

OUT = ROOT / "experiments/explainability/batch2_v1/results"
REPORT = ROOT / "docs/EXPLAINABILITY_BATCH2.md"
FIG = ROOT / "docs/figures/phase12_parameter_sensitivity_batch2.png"
SEED = 20261027
N_DIAGNOSTIC = 2_000
PERMUTATION_REPEATS = 3
FEATURES = [
    *p9.TERRAIN_FEATURES,
    "tree_fraction", "crop_fraction", "grass_fraction", "bare_fraction", "built_up_fraction",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def grouped_permutation_drop(model, x: np.ndarray, y: np.ndarray, groups: np.ndarray,
                             feature: int, seed: int) -> float:
    """PR-AUC loss after permuting a feature only within held-out spatial blocks."""
    baseline = float(average_precision_score(y, model.predict_proba(x)[:, 1]))
    xp = x.copy()
    rng = np.random.default_rng(seed)
    for group in np.unique(groups):
        ids = np.flatnonzero(groups == group)
        if len(ids) > 1:
            xp[ids, feature] = x[rng.permutation(ids), feature]
    permuted = float(average_precision_score(y, model.predict_proba(xp)[:, 1]))
    return baseline - permuted


def aggregate_member_summaries(depth: np.ndarray, params: list[dict], cell_size_m: float) -> list[dict]:
    """Summarize member arrays; -9999 and non-finite values are NoData."""
    if depth.ndim != 3 or depth.shape[0] != len(params):
        raise ValueError("member array must have shape (members, rows, cols) matching parameters")
    rows = []
    cell_area_km2 = (cell_size_m * cell_size_m) / 1_000_000
    for i, p in enumerate(params):
        a = np.asarray(depth[i], dtype=np.float64)
        valid = np.isfinite(a) & (a >= 0)
        v = a[valid]
        if not v.size:
            raise ValueError(f"member {i + 1} contains no valid cells")
        row = {
            "member_id": int(p["member_id"]),
            "manning_multiplier": float(p["manning_multiplier"]),
            "infiltration_multiplier": float(p["infiltration_multiplier"]),
            "valid_cells": int(valid.sum()),
            "nodata_cells": int(a.size - valid.sum()),
            "mean_peak_depth_m": float(v.mean()),
            "p95_peak_depth_m": float(np.quantile(v, .95)),
            "volume_m3": float(v.sum() * cell_size_m * cell_size_m),
        }
        for threshold in (.01, .05, .10, .30, .50):
            row[f"area_ge_{threshold:.2f}m_km2"] = float((v >= threshold).sum() * cell_area_km2)
        rows.append(row)
    return rows


def factorial_effect(rows: list[dict], parameter: str, metric: str) -> list[dict]:
    """Report level means and difference from grand mean for ensemble diagnostics."""
    values = np.asarray([r[metric] for r in rows], dtype=float)
    grand = float(values.mean())
    levels = sorted({r[parameter] for r in rows})
    out = []
    for level in levels:
        v = np.asarray([r[metric] for r in rows if r[parameter] == level], dtype=float)
        mean = float(v.mean())
        out.append({"parameter": parameter, "level": level, "members": int(len(v)),
                    "mean": mean, "difference_from_grand_mean": mean - grand,
                    "percent_difference_from_grand_mean": (100 * (mean / grand - 1)) if grand else None})
    return out


def main() -> None:
    if OUT.exists() and any(OUT.iterdir()):
        raise FileExistsError(f"refusing to overwrite existing output directory: {OUT.relative_to(ROOT)}")
    if REPORT.exists() or FIG.exists():
        raise FileExistsError("refusing to overwrite an existing A12 report or figure")
    start = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    table, labels, y, pilot_eligible, _, _, groups, positions, rows, cols, _ = p9.load_data()
    mask_path = ROOT / "data/features/predictions/phase9c_addendum_cr004_v6/radar_observability_mask.tif"
    with rasterio.open(mask_path) as src:
        observed_grid = src.read(1)
    observed = observed_grid[rows, cols] == 1
    # Use the original Phase 9 eligibility. The superseded Phase 9B population
    # mask is exposure-only and must not censor hazard evaluation.
    domain_ids = np.flatnonzero(pilot_eligible & observed & (groups > 0))
    if len(domain_ids) < 1 or len(np.unique(groups[domain_ids])) < p9.OUTER_FOLDS:
        raise ValueError("insufficient observable cells or spatial blocks for diagnostic fold")
    splits = p9.outer_folds(domain_ids, y, groups, positions)
    fold = splits[0]
    train, test = fold["train"], fold["test"]
    x = p9.make_matrix(table, FEATURES)
    sampled, sample_info = p9.sample_train(train, y, groups, SEED, p9.MAX_TRAIN_POSITIVES)
    model = p9.fit_estimator("random_forest", p9.MODEL_DEFAULTS["random_forest"], x[sampled], y[sampled], SEED)
    rng = np.random.default_rng(SEED + 1)
    test_sample = p9.stratified_indices(test, groups, min(N_DIAGNOSTIC, len(test)), rng)
    xs = x[test_sample].copy()
    ys = y[test_sample].astype(np.uint8)
    gs = groups[test_sample]
    if len(np.unique(ys)) != 2:
        raise ValueError("held-out diagnostic sample must contain both target classes")
    base_ap = float(average_precision_score(ys, model.predict_proba(xs)[:, 1]))

    importance = []
    for fi, feature in enumerate(FEATURES):
        drops = [grouped_permutation_drop(model, xs, ys, gs, fi, SEED + 10_000 * fi + rep)
                 for rep in range(PERMUTATION_REPEATS)]
        importance.append({"feature": feature, "mean_pr_auc_drop": float(np.mean(drops)),
                           "sd_pr_auc_drop": float(np.std(drops, ddof=1)) if len(drops) > 1 else 0.0,
                           "repeat_drops": drops})
    importance.sort(key=lambda r: r["mean_pr_auc_drop"], reverse=True)

    pd_rows = []
    # All Phase 9C reference predictors receive the same held-out partial-dependence diagnostic.
    for fi, feature in enumerate(FEATURES):
        train_values = x[train, fi]
        train_values = train_values[np.isfinite(train_values)]
        if not len(train_values):
            continue
        grid = np.unique(np.quantile(train_values, [.1, .25, .5, .75, .9]))
        for value in grid:
            changed = xs.copy()
            changed[:, fi] = value
            pred = model.predict_proba(changed)[:, 1]
            pd_rows.append({"feature": feature, "value": float(value),
                            "mean_predicted_score": float(pred.mean()),
                            "p05_predicted_score": float(np.quantile(pred, .05)),
                            "p95_predicted_score": float(np.quantile(pred, .95)),
                            "heldout_sample_n": int(len(pred))})

    sim_summary_path = ROOT / "data/features/simulation/batch2_v1/simulation_summary.json"
    sim = json.loads(sim_summary_path.read_text(encoding="utf-8"))
    cell_size = float(sim["grid_cell_size_m"])
    event_summaries = {}
    for event in ("2015-11-12", "2015-11-24"):
        npz = ROOT / f"data/features/simulation/batch2_v1/member_peak_depth_{event}_DERIVED.npz"
        with np.load(npz) as z:
            depth = z["depth_m"]
            ids = z["member_ids"].astype(int).tolist()
        params = [dict(p) for p in sim["parameters"] if p["member_id"] in ids]
        if [p["member_id"] for p in params] != ids:
            raise ValueError(f"simulation parameter/member order mismatch for {event}")
        member_rows = aggregate_member_summaries(depth, params, cell_size)
        event_summaries[event] = {
            "members": member_rows,
            "manning_effect_on_mean_peak_depth": factorial_effect(member_rows, "manning_multiplier", "mean_peak_depth_m"),
            "infiltration_effect_on_mean_peak_depth": factorial_effect(member_rows, "infiltration_multiplier", "mean_peak_depth_m"),
            "manning_effect_on_area_ge_0.10m": factorial_effect(member_rows, "manning_multiplier", "area_ge_0.10m_km2"),
            "infiltration_effect_on_area_ge_0.10m": factorial_effect(member_rows, "infiltration_multiplier", "area_ge_0.10m_km2"),
            "member_range": {
                "mean_peak_depth_m": [float(min(r["mean_peak_depth_m"] for r in member_rows)), float(max(r["mean_peak_depth_m"] for r in member_rows))],
                "area_ge_0.10m_km2": [float(min(r["area_ge_0.10m_km2"] for r in member_rows)), float(max(r["area_ge_0.10m_km2"] for r in member_rows))],
                "volume_m3": [float(min(r["volume_m3"] for r in member_rows)), float(max(r["volume_m3"] for r in member_rows))],
            },
        }
        pd.DataFrame(member_rows).to_csv(OUT / f"simulation_members_{event}.csv", index=False)

    inputs = [p9.FEATURE_TABLE, p9.LABEL_TABLE, p9.BLOCKS, mask_path, sim_summary_path,
              ROOT / "data/features/simulation/batch2_v1/member_peak_depth_2015-11-12_DERIVED.npz",
              ROOT / "data/features/simulation/batch2_v1/member_peak_depth_2015-11-24_DERIVED.npz"]
    result = {
        "status": "DIAGNOSTIC_ONLY_SINGLE_EVENT_NOT_FIELD_VALIDATED",
        "selected_model_reference": "Phase 9C default random forest, feature set iii_plus_built_fraction",
        "model_claim": "The November 2015 radar-visible label is not independent of the SAR feature source; feature effects are descriptive and do not establish flood physics or out-of-event skill.",
        "seed": SEED,
        "device": "CPU; torch 2.14.1+cu126 installed, torch.cuda.is_available() false; nvidia-smi access denied",
        "model_parameters": p9.MODEL_DEFAULTS["random_forest"],
        "features": FEATURES,
        "fold": {"fold": int(fold["fold"]), "train_n": int(len(train)), "test_n": int(len(test_sample)),
                 "test_prevalence": float(ys.mean()), "domain_n": int(len(domain_ids)),
                 "domain_prevalence": float(y[domain_ids].mean()), "buffered_spatial_cv": "first fold of registered five-fold GroupKFold with one-block buffer"},
        "sampling": sample_info,
        "permutation": {"metric": "average precision (PR-AUC)", "permutation": "within each held-out 3 km block", "repeats": PERMUTATION_REPEATS,
                        "baseline_pr_auc": base_ap, "importance": importance},
        "partial_dependence": {"method": "brute-force marginal PDP on the same held-out diagnostic sample; grid from training-fold 10th/25th/50th/75th/90th percentiles",
                               "rows": pd_rows, "caveat": "Correlated terrain predictors can create unrealistic combinations; PDP is not causal."},
        "simulation_sensitivity": {"source": "existing Phase 12 member peak depth arrays; no simulation rerun", "cell_size_m": cell_size,
                                   "events": event_summaries,
                                   "interpretation": "Parameter-member spread reflects the specified Manning and infiltration scenario grid, not probability-calibrated uncertainty."},
        "input_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in inputs},
        "runtime_seconds": time.perf_counter() - start,
    }
    (OUT / "explainability_sensitivity.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    pd.DataFrame(importance).drop(columns="repeat_drops").to_csv(OUT / "permutation_importance.csv", index=False)
    pd.DataFrame(pd_rows).to_csv(OUT / "partial_dependence.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for event, color in (("2015-11-12", "#2676a5"), ("2015-11-24", "#d07a31")):
        vals = [r["area_ge_0.10m_km2"] for r in event_summaries[event]["members"]]
        axes[0].plot(range(1, len(vals) + 1), vals, marker="o", label=event, color=color)
    axes[0].set(title="Member peak area ≥ 0.10 m", xlabel="Member ID", ylabel="Area (km²)")
    axes[0].legend()
    top = importance[:10][::-1]
    axes[1].barh([r["feature"] for r in top], [r["mean_pr_auc_drop"] for r in top], color="#3f7e64")
    axes[1].set(title="Held-out grouped permutation", xlabel="PR-AUC decrease (within-block shuffle)")
    fig.tight_layout()
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=180)
    plt.close(fig)

    lines = [
        "# A12 — Explainability and simulation parameter sensitivity", "",
        "> **Diagnostic only.** The Phase 9C model describes a single November 2015 radar-visible label and is not independently validated. The Phase 12 outputs are assumption-based simulations, not observed depth or calibrated uncertainty.", "",
        "## Data-driven model diagnostic", "",
        f"Used the Phase 9C default random-forest reference (feature set iii; {len(FEATURES)} features) and the first outer fold from the existing buffered spatial-block design. The model trained on {len(sampled):,} sampled training cells ({sample_info['positive_used']:,} positive and {sample_info['negative_used']:,} negative, {sample_info['negative_to_positive']:.1f}:1) and diagnostics used {len(test_sample):,} held-out cells at {ys.mean():.2%} prevalence. Baseline held-out PR-AUC was {base_ap:.4f}. Importance permuted one predictor within held-out 3 km blocks and reports the mean PR-AUC decrease over {PERMUTATION_REPEATS} fixed-seed repeats. This is one fold, not a replacement for the five-fold model report.", "",
        "| Feature | PR-AUC decrease mean | SD |", "|---|---:|---:|",
    ]
    for row in importance:
        lines.append(f"| {row['feature']} | {row['mean_pr_auc_drop']:.5f} | {row['sd_pr_auc_drop']:.5f} |")
    lines += ["", "Partial-dependence curves are supplied in `experiments/explainability/batch2_v1/partial_dependence.csv` for every model feature at training-fold quantiles. They are marginal, can combine correlated features into unrealistic values, and are not causal. See the PNG for the top ten grouped permutation effects and simulation-member area spread.", "",
              "## Simulation parameter sensitivity", "",
              "All 20 existing members per event were summarized from their saved peak-depth arrays. No solver was rerun. NoData cells remain excluded from cell summaries; dry zero-depth valid cells remain included. Per-member depth, volume, and areas above 0.01, 0.05, 0.10, 0.30 and 0.50 m are in the CSV files. Factorial level means and differences from the grand member mean are in the JSON. These are sensitivity summaries over the chosen parameter grid, not probability statements.", "",
              "| Event | Mean peak depth range (m) | Area ≥0.10 m range (km²) | Volume range (m³) |", "|---|---:|---:|---:|"]
    for event, summary in event_summaries.items():
        r = summary["member_range"]
        lines.append(f"| {event} | {r['mean_peak_depth_m'][0]:.4f}–{r['mean_peak_depth_m'][1]:.4f} | {r['area_ge_0.10m_km2'][0]:.2f}–{r['area_ge_0.10m_km2'][1]:.2f} | {r['volume_m3'][0]:.3g}–{r['volume_m3'][1]:.3g} |")
    lines += ["", "## Interpretation and limitations", "",
              "The data-driven result is only an explanation of a model trained/evaluated against one November 2015 SAR-derived map. UNOSAT may share the feature scene, and there is no independent out-of-event flood reference. Do not interpret importance as physical causality or use it to upgrade the map’s validation tier. The simulations use the assumptions documented in `PHASE12_SIMULATION.md`; member spread is parameter sensitivity only. Neither output is operational guidance.", "",
              "## Reproduction and checks", "",
        "Command: `.venv\\Scripts\\python.exe experiments\\explainability\\batch2_v1\\run.py`.",
              f"Seed: {SEED}. Runtime: {result['runtime_seconds']:.2f} seconds. Device: CPU (CUDA unavailable). Input hashes are recorded in `experiments/explainability/batch2_v1/explainability_sensitivity.json`.", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"output": str(OUT.relative_to(ROOT)), "heldout_n": int(len(test_sample)),
                      "heldout_prevalence": float(ys.mean()), "baseline_pr_auc": base_ap,
                      "top_features": importance[:5], "simulation_ranges": {e:v["member_range"] for e,v in event_summaries.items()},
                      "runtime_seconds": result["runtime_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
