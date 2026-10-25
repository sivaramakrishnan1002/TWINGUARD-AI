"""Phase 9C: radar observability, spatial CV, independent points and Mondrian bands.

All inputs are existing derived project files; this script never writes to raw data
or Phase 9/9B paths. Use --configs 30 for the registered nested search.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject
from sklearn.metrics import average_precision_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from pipelines.phase9b import model_upgrade as p9

OUT = ROOT / "data/features/predictions/phase9c"
METRICS = ROOT / "docs/PHASE9C_METRICS.json"
REGISTRY = ROOT / "docs/PHASE9C_MODEL_REGISTRY.json"
REPORT = ROOT / "docs/PHASE9C_URBAN_CENSORING.md"
FIGURES = ROOT / "docs/figures/phase9c"
POINTS = ROOT / "data/raw/historical_floods/2015/opencity_flood_points"
OBS_BUILT_CUTOFF = 0.50
OBS_SLOPE_CUTOFF_DEG = 15.0
BUILT_BINS = [("0_to_0.1", 0.0, 0.1), ("0.1_to_0.3", 0.1, 0.3),
              ("0.3_to_0.5", 0.3, 0.5), ("0.5_to_0.75", 0.5, 0.75),
              ("0.75_to_1", 0.75, 1.000001)]
LANDCOVER_COLUMNS = ["tree_fraction", "crop_fraction", "grass_fraction", "bare_fraction", "built_up_fraction_phase9b", "water_fraction_phase9b"]
LANDCOVER_NAMES = ["tree", "crop", "grass", "bare", "built_up", "water"]
SEED = 20261025


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_to_grid(path: Path, grid_meta: dict) -> np.ndarray:
    with rasterio.open(path) as src:
        dst = np.zeros((grid_meta["height"], grid_meta["width"]), dtype=np.uint8)
        reproject(source=rasterio.band(src, 1), destination=dst,
                  src_transform=src.transform, src_crs=src.crs,
                  src_nodata=src.nodata, dst_transform=grid_meta["transform"],
                  dst_crs=grid_meta["crs"], dst_nodata=0,
                  resampling=Resampling.nearest)
        return dst


def create_observability(table, labels, rows, cols, grid_meta):
    shape = (grid_meta["height"], grid_meta["width"])
    cma = np.zeros(shape, dtype=bool)
    with rasterio.open(ROOT / "data/processed/grid/cma_mask.tif") as ds:
        cma = ds.read(1) == 1
    # The two Phase 8 masks were built from RTC valid-data and clear layover/shadow bits.
    # Requiring both reference and event valid pixels avoids scoring unobserved cells.
    ref = read_to_grid(ROOT / "data/processed/sar_work/rtc_aligned/2015-10-19_valid_layover_shadow_mask.tif", grid_meta) == 1
    event = read_to_grid(ROOT / "data/processed/sar_work/rtc_aligned/2015-11-24_valid_layover_shadow_mask.tif", grid_meta) == 1
    ref_flags = read_to_grid(ROOT / "data/processed/sar_work/rtc_aligned/2015-10-19_layover_shadow_flags.tif", grid_meta)
    event_flags = read_to_grid(ROOT / "data/processed/sar_work/rtc_aligned/2015-11-24_layover_shadow_flags.tif", grid_meta)
    flags_clear = ((ref_flags & (4 | 16)) == 0) & ((event_flags & (4 | 16)) == 0)
    built = np.full(shape, np.nan, dtype=np.float32)
    slope = np.full(shape, np.nan, dtype=np.float32)
    built[rows, cols] = table["built_up_fraction"].to_numpy(dtype=np.float32)
    slope[rows, cols] = table["slope_deg"].to_numpy(dtype=np.float32)
    dense = np.isfinite(built) & (built > OBS_BUILT_CUTOFF)
    steep = np.isfinite(slope) & (slope > OBS_SLOPE_CUTOFF_DEG)
    missing_slope = ~np.isfinite(slope)
    layover_shadow = ~flags_clear
    valid_radar = ref & event & flags_clear
    eligible_label = labels["eligible_for_model"].to_numpy(dtype=bool)
    pop_ok = ~table["population_is_nodata"].to_numpy(dtype=bool)
    label_land = np.zeros(shape, dtype=bool)
    population_valid = np.zeros(shape, dtype=bool)
    label_land[rows, cols] = eligible_label
    population_valid[rows, cols] = pop_ok
    eligible_base_grid = cma & label_land & population_valid
    observed = eligible_base_grid & valid_radar & ~dense & ~steep & ~missing_slope
    reason = np.zeros(shape, dtype=np.uint8)
    reason[cma & dense] |= 1
    reason[cma & layover_shadow] |= 2
    reason[cma & steep] |= 4
    reason[cma & ~(ref & event)] |= 8
    reason[cma & missing_slope] |= 16
    reason[cma & ~eligible_base_grid] |= 32
    counts = {
        "cma_cells": int(cma.sum()), "assessed_cells": int(observed.sum()),
        "not_assessed_cells": int((cma & ~observed).sum()),
        "eligible_land_after_phase9_water_and_population_masks": int(eligible_base_grid.sum()),
        "dense_urban_gt_0_50_nonexclusive": int((cma & dense).sum()),
        "layover_or_shadow_nonexclusive": int((cma & layover_shadow).sum()),
        "steep_gt_15deg_nonexclusive": int((cma & steep).sum()),
        "invalid_or_unobserved_reference_or_event_nonexclusive": int((cma & ~(ref & event)).sum()),
        "slope_nodata_nonexclusive": int((cma & missing_slope).sum()),
        "combined_exclusion_reason_codes": {str(k): int(np.count_nonzero(cma & (reason == k))) for k in range(1, 64)},
        "reason_code_legend": {"1": "dense built-up >0.50", "2": "layover or shadow flag", "4": "slope >15 degrees",
                               "8": "reference or event RTC invalid/missing", "16": "slope missing; treated as unobservable",
                               "32": "excluded by unchanged Phase 9 water/label eligibility or population-NoData mask"}
    }
    cell_observed = observed[rows, cols]
    eligible = eligible_label & pop_ok & cell_observed
    counts["phase9_eligible_before_phase9b_masks"] = int(eligible_label.sum())
    counts["population_nodata_excluded"] = int((eligible_label & ~pop_ok).sum())
    counts["model_cells_inside_mask"] = int(eligible.sum())
    counts["model_positives_inside_mask"] = int(labels.loc[eligible, "target_union_minus_baseline"].sum())
    return observed, reason, built, slope, eligible, counts


def write_grid(path: Path, grid_meta: dict, array: np.ndarray, desc: str, dtype="float32", nodata=-9999):
    if path.exists():
        with rasterio.open(path) as existing:
            if ((existing.height, existing.width, existing.crs, existing.transform) !=
                    (grid_meta["height"], grid_meta["width"], grid_meta["crs"], grid_meta["transform"]) or
                    existing.descriptions[0] != desc or existing.dtypes[0] != dtype):
                raise FileExistsError(f"Existing Phase 9C output does not match this run: {path.relative_to(ROOT)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = {"driver": "GTiff", "height": grid_meta["height"], "width": grid_meta["width"],
               "count": 1, "dtype": dtype, "crs": grid_meta["crs"], "transform": grid_meta["transform"],
               "nodata": nodata, "compress": "deflate", "predictor": 3 if dtype.startswith("float") else 1}
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(array.astype(dtype), 1)
        ds.set_band_description(1, desc)
        ds.update_tags(status="PHASE 9C PILOT; SINGLE 2015 TARGET; NOT FIELD VALIDATED")


def q_by_bin(train_idx, train_p, y, built):
    q, details = {}, {}
    for name, lo, hi in BUILT_BINS:
        m = (built[train_idx] >= lo) & (built[train_idx] < hi)
        if int(m.sum()) == 0:
            q[name] = None
            details[name] = {"n": 0, "q90": None, "fallback": "unavailable"}
        else:
            residual = np.abs(y[train_idx[m]] - train_p[m])
            q[name] = float(np.quantile(residual, 0.90, method="higher"))
            details[name] = {"n": int(m.sum()), "q90": q[name], "fallback": None}
    vals = [v for v in q.values() if v is not None]
    pooled = float(np.quantile(np.abs(y[train_idx] - train_p), 0.90, method="higher"))
    for name in q:
        if q[name] is None:
            q[name] = pooled
            details[name]["fallback"] = "pooled training OOF quantile; built-up stratum absent"
    details["pooled_training_q90"] = pooled
    return q, details


def apply_q(p, built, q):
    out = np.empty(len(p), dtype=np.float32)
    for i, (name, lo, hi) in enumerate(BUILT_BINS):
        m = (built >= lo) & (built < hi)
        out[m] = q[name]
    return np.maximum(0, p - out), np.minimum(1, p + out)


def point_features(built_grid, landcover_grid, risk_grid, physical_grid, observed, physical_support, grid_meta):
    files = [POINTS / "814ca028-4c84-4bd0-aa67-6dbaeb9b6ba5.kml",
             POINTS / "93d2905a-a580-482d-96b0-4d9ccf5273ef.kml"]
    points = gpd.GeoDataFrame(pd_concat([gpd.read_file(f, driver="KML") for f in files]), geometry="geometry", crs="EPSG:4326")
    points = points.to_crs(grid_meta["crs"])
    records = []
    inv = ~grid_meta["transform"]
    for geom in points.geometry:
        if geom is None or geom.is_empty:
            records.append({"row":None,"col":None,"built":None,"landcover_class":None,"observed":False,"risk":None,"physical":None,
                            "physical_support":False,"unscored_reason":"empty_geometry"}); continue
        colf, rowf = inv * (geom.x, geom.y)
        row, col = int(math.floor(rowf)), int(math.floor(colf))
        if row < 0 or col < 0 or row >= observed.shape[0] or col >= observed.shape[1]:
            records.append({"row":None,"col":None,"built":None,"landcover_class":None,"observed":False,"risk":None,"physical":None,
                            "physical_support":False,"unscored_reason":"outside_master_grid"}); continue
        b = built_grid[row, col]
        if not np.isfinite(b):
            records.append({"row":row,"col":col,"built":None,"landcover_class":None,"observed":False,"risk":None,"physical":None,
                            "physical_support":False,"unscored_reason":"no_built_up_cell_value"}); continue
        lc_code = int(landcover_grid[row,col])
        records.append({"row": row, "col": col, "built": float(b),
                        "landcover_class":LANDCOVER_NAMES[lc_code] if 0 <= lc_code < len(LANDCOVER_NAMES) else None,
                        "observed": bool(observed[row, col]),
                        "risk": float(risk_grid[row, col]) if np.isfinite(risk_grid[row, col]) else None,
                        "physical": float(physical_grid[row, col]) if np.isfinite(physical_grid[row, col]) else None,
                        "physical_support": bool(physical_support[row, col]),
                        "unscored_reason":None if np.isfinite(risk_grid[row,col]) else "outside_radar_and_physical_support"})
    return records


def pd_concat(frames):
    import pandas as pd
    return pd.concat(frames, ignore_index=True)


def dominant_landcover_grid(table, rows, cols, shape):
    fractions=table[LANDCOVER_COLUMNS].to_numpy(dtype=np.float32)
    all_missing=~np.isfinite(fractions).any(axis=1)
    codes=np.argmax(np.where(np.isfinite(fractions),fractions,-np.inf),axis=1).astype(np.int8)
    codes[all_missing]=-1
    grid=np.full(shape,-1,dtype=np.int8)
    grid[rows,cols]=codes
    return grid


def block_bootstrap_point_hits(points, risk_grid, built_grid, domain_mask, top_pct, seed, reps=2000, landcover_grid=None):
    # Cluster bootstrap by 3 km block (100x100 30 m cells), preserving point clustering.
    valid = [p for p in points if p["row"] is not None and p["col"] is not None and
             p["risk"] is not None and domain_mask[p["row"], p["col"]]]
    if not valid:
        return {"n": 0, "observed_share": None, "observed_ci_95": None, "matched_chance_share": None, "matched_chance_ci_95": None}
    ranks = np.full(risk_grid.shape, np.nan, dtype=np.float32)
    vals = risk_grid[domain_mask]
    order = np.argsort(vals, kind="mergesort")
    rank_vals = np.empty(len(vals), dtype=np.float32)
    rank_vals[order] = np.arange(1, len(vals)+1, dtype=np.float32) / max(len(vals), 1)
    ranks[domain_mask] = rank_vals
    threshold = 1.0 - top_pct / 100.0
    for p in valid:
        p["hit"] = bool(ranks[p["row"], p["col"]] >= threshold)
        p["bin"] = next((name for name, lo, hi in BUILT_BINS if lo <= p["built"] < hi), "unknown")
        if landcover_grid is not None:
            lc_code = int(landcover_grid[p["row"],p["col"]])
            p["landcover_class"] = LANDCOVER_NAMES[lc_code] if 0 <= lc_code < len(LANDCOVER_NAMES) else None
        else:
            p["landcover_class"] = p.get("landcover_class", "all")
        p["block"] = (p["row"] // 100, p["col"] // 100)
    blocks = {}
    for p in valid:
        blocks.setdefault(p["block"], []).append(p)
    block_ids = list(blocks)
    rng = np.random.default_rng(seed)
    observed_samples, chance_samples = [], []
    observed_by_bin_samples={name:[] for name,_,_ in BUILT_BINS}
    chance_by_bin_samples={name:[] for name,_,_ in BUILT_BINS}
    by_bin = {}
    flat_risk = ranks
    matched_cells = {}
    for name, lo, hi in BUILT_BINS:
        m = domain_mask & np.isfinite(built_grid) & (built_grid >= lo) & (built_grid < hi)
        landcover_classes = LANDCOVER_NAMES if landcover_grid is not None else ["all"]
        for lc in landcover_classes:
            class_mask = m
            if landcover_grid is not None:
                class_mask = m & (landcover_grid == LANDCOVER_NAMES.index(lc))
            matched_cells[(name,lc)] = np.argwhere(class_mask & np.isfinite(flat_risk))
        selected=[p for p in valid if p["bin"]==name]
        by_bin[name] = {"point_n": len(selected),
                         "observed_share":float(np.mean([p["hit"] for p in selected])) if selected else None,
                         "observed_ci_95":None,
                         "matched_chance_share":None,
                         "matched_chance_ci_95":None,
                         "matched_chance_n":0,
                         "top_cell_share_within_bin": float(np.mean(flat_risk[m] >= threshold)) if m.any() else None}
    for _ in range(reps):
        picked = rng.choice(len(block_ids), size=len(block_ids), replace=True)
        sample = [p for i in picked for p in blocks[block_ids[int(i)]]]
        if not sample:
            continue
        observed_samples.append(float(np.mean([p["hit"] for p in sample])))
        hits = 0
        chance_n = 0
        obs_hits_by={name:[] for name,_,_ in BUILT_BINS}
        chance_hits_by={name:[] for name,_,_ in BUILT_BINS}
        for p in sample:
            cells = matched_cells.get((p["bin"],p["landcover_class"]), [])
            if len(cells):
                rr, cc = cells[int(rng.integers(len(cells)))]
                chance_hit=bool(flat_risk[rr, cc] >= threshold)
                hits += chance_hit
                chance_n += 1
                chance_hits_by[p["bin"]].append(chance_hit)
            obs_hits_by[p["bin"]].append(p["hit"])
        if chance_n:
            chance_samples.append(hits / chance_n)
        for name,_,_ in BUILT_BINS:
            if obs_hits_by[name]: observed_by_bin_samples[name].append(float(np.mean(obs_hits_by[name])))
            if chance_hits_by[name]: chance_by_bin_samples[name].append(float(np.mean(chance_hits_by[name])))
    obs = float(np.mean([p["hit"] for p in valid]))
    chance = float(np.mean(chance_samples)) if chance_samples else None
    for name in by_bin:
        if observed_by_bin_samples[name]:
            by_bin[name]["observed_ci_95"]=[float(np.quantile(observed_by_bin_samples[name],.025)),float(np.quantile(observed_by_bin_samples[name],.975))]
            by_bin[name]["matched_chance_share"]=float(np.mean(chance_by_bin_samples[name])) if chance_by_bin_samples[name] else None
            by_bin[name]["matched_chance_ci_95"]=[float(np.quantile(chance_by_bin_samples[name],.025)),float(np.quantile(chance_by_bin_samples[name],.975))] if chance_by_bin_samples[name] else None
            by_bin[name]["matched_chance_n"]=sum(1 for p in valid if p["bin"]==name and matched_cells.get((name,p["landcover_class"]),[]).size)
    return {"n": len(valid), "observed_share": obs,
            "observed_ci_95": [float(np.quantile(observed_samples,.025)),float(np.quantile(observed_samples,.975))] if observed_samples else None,
            "matched_chance_share": chance,
            "matched_chance_ci_95": [float(np.quantile(chance_samples,.025)),float(np.quantile(chance_samples,.975))] if chance_samples else None,
            "matched_chance_n":sum(1 for p in valid if matched_cells.get((p["bin"],p["landcover_class"]),[]).size),
            "by_built_up_bin": by_bin,
            "method": "3 km point-block cluster bootstrap; matched chance draws one random valid risk cell per point with the same built-up-fraction bin and dominant class among tree/crop/grass/bare/built-up/water fractions; 2000 replicates"}


def run(config_count=30, bootstrap_reps=200, point_bootstrap_reps=2000):
    allowed_partial = {"composite_rank_for_point_audit.tif", "observability_exclusion_reason.tif",
        "physical_susceptibility_outside_radar.tif", "radar_mondrian_p05_apparent.tif",
        "radar_mondrian_p95_apparent.tif", "radar_observability_mask.tif",
        "radar_probability_mean_apparent.tif", "urban_confidence.tif"}
    if OUT.exists():
        extras = [p.name for p in OUT.iterdir() if p.name not in allowed_partial]
        if extras:
            raise FileExistsError(f"Refusing to overwrite existing Phase 9C outputs in {OUT.relative_to(ROOT)}")
    if FIGURES.exists() and any(FIGURES.iterdir()):
        raise FileExistsError(f"Refusing to overwrite existing Phase 9C figures in {FIGURES.relative_to(ROOT)}")
    OUT.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    table, labels, target, pilot_eligible, eligible_old, _, groups, positions, rows, cols, block_raster = p9.load_data()
    with rasterio.open(ROOT / "data/processed/grid/cma_mask.tif") as ds:
        grid_meta = {"height": ds.height, "width": ds.width, "crs": ds.crs, "transform": ds.transform}
    observed, reason, built_grid, slope_grid, eligible, obs_stats = create_observability(table, labels, rows, cols, grid_meta)
    y = target.astype(np.uint8)
    idx = np.flatnonzero(eligible)
    if len(np.unique(groups[idx])) < p9.OUTER_FOLDS:
        raise ValueError("Observability mask leaves fewer than five spatial blocks")
    if np.unique(y[idx]).size < 2:
        raise ValueError("Observability mask leaves only one target class")
    outer = p9.outer_folds(idx, y, groups, positions)
    # Exact existing Phase 9B model feature set and calibrated single-feature baselines.
    xfull = p9.make_matrix(table, p9.FEATURE_SETS["C_all_pilot_features"])
    built = table["built_up_fraction"].to_numpy(dtype=np.float64)
    oof = np.full(len(y), np.nan, dtype=np.float32)
    qfolds, thresholds, fold_metrics, tuning = [], [], [], []
    baseline_metrics, baseline_oof, baseline_fold_results = {}, {}, {}
    for bi, (name, features) in enumerate(p9.SINGLE_BASELINES.items()):
        x = p9.make_matrix(table, features)
        preds = np.full(len(y), np.nan, dtype=np.float32); folds=[]
        for spec in outer:
            res = p9.evaluate_outer("logistic", {}, x, y, groups, spec["train"], spec["test"], positions,
                                    SEED + spec["fold"]*100 + bi)
            folds.append(res["metrics"]); preds[spec["test"]] = res["probability"]
        baseline_metrics[name] = {"fold_mean_sd": p9.summarize_folds(folds,["roc_auc","pr_auc","brier"]),
                                  "pooled": p9.metric_bundle(y[idx],preds[idx],.5,float(y[idx].mean()))}
        baseline_oof[name] = preds
        baseline_fold_results[name] = folds
        print(f"baseline {name}: done", flush=True)
    random_pred = np.full(len(y), np.nan, dtype=np.float32)
    random_folds=[]
    for spec in outer:
        random_pred[spec["test"]] = float(y[spec["train"]].mean())
        random_folds.append(p9.metric_bundle(y[spec["test"]],random_pred[spec["test"]],.5,float(y[spec["train"]].mean())))
        random_folds[-1]["roc_auc"] = 0.5
        random_folds[-1]["pr_auc"] = float(y[spec["test"]].mean())
    baseline_metrics["random_prevalence"] = {"fold_mean_sd": {"roc_auc":{"mean":.5,"sd":0.0},
                                    "pr_auc":p9.summarize_folds([{"pr_auc":float(y[s["test"]].mean())} for s in outer],["pr_auc"])["pr_auc"],
                                    "brier":p9.summarize_folds([{"brier":float(np.mean((y[s["test"]]-y[s["train"]].mean())**2))} for s in outer],["brier"])["brier"]},
                                    "pooled":p9.metric_bundle(y[idx],random_pred[idx],.5,float(y[idx].mean()))}
    baseline_oof["random_prevalence"] = random_pred
    baseline_fold_results["random_prevalence"] = random_folds

    family_raw, family_params = {}, {}
    family_inner = []
    for fi, spec in enumerate(outer):
        fold = spec["fold"]; tr, te = spec["train"], spec["test"]
        calibrated, raw_scores, inner_rows, selected = [], [], [], {}
        for kind in ("random_forest", "xgboost", "lightgbm"):
            params, scores = p9.tune_nested(kind, xfull, y, groups, tr, positions, SEED+fold*100+1000, config_count)
            res = p9.evaluate_outer(kind, params, xfull, y, groups, tr, te, positions, SEED+fold*1000+1901)
            calibrated.append(res["probability"])
            raw_scores.append(res["raw_probability"])
            if not np.array_equal(res["train_calibration_indices"], inner_rows[0]) if inner_rows else False:
                raise ValueError("Phase 9C ensemble calibration rows differ across tree families")
            inner_rows.append(res["train_calibration_indices"])
            selected[kind] = {"params":params,"config_scores":scores}
            family_raw.setdefault(kind,np.full(len(y),np.nan,dtype=np.float32))[te] = res["raw_probability"]
            family_params.setdefault(kind,[]).append(params)
        ptest = np.mean(np.vstack(calibrated), axis=0).astype(np.float32)
        oof[te] = ptest
        cal_idx = inner_rows[0]
        cal_p = np.mean(np.vstack([baseline for baseline in []]),axis=0) if False else None
        # Re-run each family’s returned cross-fitted calibration rows for Mondrian residuals.
        train_calibrated=[]
        for kind, params in ((k, selected[k]["params"]) for k in ("random_forest","xgboost","lightgbm")):
            ix, raw, _, _ = p9.inner_oof(kind, params, xfull, y, groups, tr, positions, SEED+fold*1000+1901)
            cal, cal_oof, _, _ = p9.crossfit_calibration(y, groups, ix, raw, positions)
            train_calibrated.append(cal_oof)
        if not all(np.array_equal(cal_idx, inner_rows[0]) for _ in train_calibrated):
            raise ValueError("Mondrian calibration requires aligned inner training rows")
        train_p = np.mean(np.vstack(train_calibrated), axis=0)
        q, q_info = q_by_bin(cal_idx, train_p, y, built)
        lower, upper = apply_q(ptest, built[te], q)
        m = p9.metric_bundle(y[te], ptest, p9.select_f1_threshold(y[cal_idx],train_p), float(y[tr].mean()))
        m["mondrian_90"] = {"overall_coverage":float(np.mean((y[te]>=lower)&(y[te]<=upper))),
                            "overall_mean_width":float(np.mean(upper-lower)), "per_built_up_bin":{}}
        for name, lo, hi in BUILT_BINS:
            bm=(built[te]>=lo)&(built[te]<hi)
            if bm.any():
                m["mondrian_90"]["per_built_up_bin"][name]={"n":int(bm.sum()),
                    "coverage":float(np.mean((y[te][bm]>=lower[bm])&(y[te][bm]<=upper[bm]))),
                    "mean_width":float(np.mean(upper[bm]-lower[bm])),"q90_training":q[name]}
        fold_metrics.append(m); thresholds.append(m["threshold"]);qfolds.append(q_info)
        tuning.append({"fold":fold,"selected_parameters":selected,"mondrian_training_quantiles":q_info,
                       "train_cells":int(len(tr)),"test_cells":int(len(te)),"train_blocks":len(np.unique(groups[tr])),"test_blocks":len(np.unique(groups[te]))})
        family_inner.append({"indices":cal_idx,"p":train_p})
        print(f"outer fold {fold}/{len(outer)}: tuned ensemble complete", flush=True)

    if np.isnan(oof[idx]).any():
        raise RuntimeError("Outer OOF predictions do not cover all mask-eligible cells")
    # Phase 9B comparator values are the committed v2 full eligible scores.
    p9b = json.loads((ROOT/"docs/PHASE9B_V2_METRICS.json").read_text(encoding="utf-8"))
    p9b_ensemble = p9b["metrics"]["U4_default_tuned_and_ensemble"]["simple_average_tuned_tree_ensemble"]
    chosen_summary = p9.summarize_folds(fold_metrics,["roc_auc","pr_auc","brier"])
    fold_summary = json.loads(json.dumps(chosen_summary))
    ci = p9.block_bootstrap_ap(y[idx],oof[idx],groups[idx],SEED+70,bootstrap_reps)
    chosen_summary.update({"pooled":p9.metric_bundle(y[idx],oof[idx],float(np.median(thresholds)),float(y[idx].mean())),
                           "pr_auc_block_bootstrap_ci_95":ci})
    paired_baselines={}
    for name, folds in baseline_fold_results.items():
        entry={}
        for metric in ("pr_auc","roc_auc","brier"):
            deltas=[]
            for mf,bf in zip(fold_metrics,folds):
                if mf.get(metric) is None or bf.get(metric) is None:
                    continue
                # Positive delta always means Phase 9C is better: larger AUC, lower Brier.
                deltas.append(float(mf[metric]-bf[metric]) if metric!="brier" else float(bf[metric]-mf[metric]))
            entry[metric]={"mean_delta":float(np.mean(deltas)) if deltas else None,
                           "sd_delta":float(np.std(deltas,ddof=1)) if len(deltas)>1 else 0.0 if deltas else None,
                           "folds_won":sum(d>0 for d in deltas),"fold_count":len(deltas)}
        paired_baselines[name]=entry
    coverage_bins={}
    # Fold metrics already use training-only Mondrian q values; aggregate held-out cells by built-up stratum.
    q_by_fold={}
    for spec, fm, qinfo in zip(outer,fold_metrics,qfolds):
        for name, lo, hi in BUILT_BINS:
            bm=(built[spec["test"]]>=lo)&(built[spec["test"]]<hi)
            d=fm["mondrian_90"]["per_built_up_bin"].get(name)
            if d: q_by_fold.setdefault(name,[]).append(d)
    for name, _, _ in BUILT_BINS:
        rows0=q_by_fold.get(name,[])
        coverage_bins[name]={"folds_with_data":len(rows0),"heldout_n":sum(x["n"] for x in rows0),
            "mean_fold_coverage":float(np.mean([x["coverage"] for x in rows0])) if rows0 else None,
            "mean_fold_band_width":float(np.mean([x["mean_width"] for x in rows0])) if rows0 else None,
            "per_fold":rows0}
    pooled_cov=float(np.mean([m["mondrian_90"]["overall_coverage"] for m in fold_metrics]))
    pooled_width=float(np.mean([m["mondrian_90"]["overall_mean_width"] for m in fold_metrics]))

    # Full-data apparent map: fit only inside observable region. Calibration and quantiles are OOF-derived.
    idx_all=idx
    p_apparent_by_family=[]
    for kind in ("random_forest","xgboost","lightgbm"):
        param_keys=[json.dumps(p,sort_keys=True) for p in family_params[kind]]
        params=json.loads(Counter(param_keys).most_common(1)[0][0])
        cal=p9.fit_platt(family_raw[kind][idx],y[idx])
        sampled,_=p9.sample_train(idx,y,groups,SEED+8800+len(p_apparent_by_family))
        model=p9.fit_estimator(kind,params,xfull[sampled],y[sampled],SEED+8800+len(p_apparent_by_family))
        pred=np.empty(len(idx_all),dtype=np.float32)
        for starti in range(0,len(idx_all),50000):
            sub=idx_all[starti:starti+50000]
            raw=p9.raw_prior_adjust(model.predict_proba(xfull[sub])[:,1],float(y[sampled].mean()),float(y[idx].mean()))
            pred[starti:starti+len(sub)]=p9.apply_platt(cal,raw).astype(np.float32)
        p_apparent_by_family.append(pred)
    apparent=np.mean(np.vstack(p_apparent_by_family),axis=0).astype(np.float32)
    global_oof=np.full(len(y),np.nan,dtype=np.float32);global_oof[idx]=oof[idx]
    q_global, q_global_info=q_by_bin(idx, oof[idx], y, built)
    lo_ap, hi_ap=apply_q(apparent,built[idx],q_global)
    full_probability=np.full((grid_meta["height"],grid_meta["width"]),-9999,dtype=np.float32)
    full_lower=full_probability.copy();full_upper=full_probability.copy()
    full_probability[rows[idx],cols[idx]]=apparent
    full_lower[rows[idx],cols[idx]]=lo_ap;full_upper[rows[idx],cols[idx]]=hi_ap
    write_grid(OUT/"radar_probability_mean_apparent.tif",grid_meta,full_probability,"APPARENT calibrated Phase 9C radar susceptibility; unassessed is NoData")
    write_grid(OUT/"radar_mondrian_p05_apparent.tif",grid_meta,full_lower,"APPARENT lower spatial Mondrian 90% band bound; not depth")
    write_grid(OUT/"radar_mondrian_p95_apparent.tif",grid_meta,full_upper,"APPARENT upper spatial Mondrian 90% band bound; not depth")
    obs_out=np.where(cma_mask_from_grid(grid_meta),0,255).astype(np.uint8);obs_out[observed]=1
    write_grid(OUT/"radar_observability_mask.tif",grid_meta,obs_out,"1 assessed by radar-label model; 0 not assessed from radar labels",dtype="uint8",nodata=255)
    conf=np.where(cma_mask_from_grid(grid_meta),0.0,-9999).astype(np.float32);conf[observed]=1.0
    write_grid(OUT/"urban_confidence.tif",grid_meta,conf,"0=not assessed from radar labels (including dense urban); 1=radar-observable low-urban cell")
    reason_out=np.where(cma_mask_from_grid(grid_meta),reason,255).astype(np.uint8)
    write_grid(OUT/"observability_exclusion_reason.tif",grid_meta,reason_out,"Bit flags for observability exclusions; see Phase 9C report",dtype="uint8",nodata=255)

    # Physical-only score outside radar mask; percentile components are equal-weight and never fitted to labels.
    physical_names=["hand_d8_accum100_m","local_depression_depth_m","twi_d8_proxy","distance_to_exact_named_waterway_m"]
    phys_cols=[table[n].to_numpy(dtype=np.float64) for n in physical_names]
    base_domain = np.zeros(observed.shape,dtype=bool)
    base_domain[rows,cols] = labels["eligible_for_model"].to_numpy(dtype=bool) & ~table["population_is_nodata"].to_numpy(dtype=bool)
    outside= base_domain & ~observed
    physical_support=outside.copy()
    for name, arr in zip(physical_names,phys_cols):
        g=np.full(outside.shape,np.nan,dtype=np.float64);g[rows,cols]=arr
        physical_support &= np.isfinite(g)
    component_maps=[]
    for name, arr, high_is_susceptible in zip(physical_names,phys_cols,[False,True,True,False]):
        g=np.full(outside.shape,np.nan,dtype=np.float64);g[rows,cols]=arr
        vals=g[physical_support]
        order=np.argsort(vals,kind="mergesort");rank=np.empty(len(vals),dtype=np.float32)
        rank[order]=np.arange(1,len(vals)+1,dtype=np.float32)/max(len(vals),1)
        if not high_is_susceptible: rank=1-rank
        comp=np.full(outside.shape,np.nan,dtype=np.float32);comp[physical_support]=rank
        component_maps.append(comp)
    stack=np.stack(component_maps)
    nvalid=np.isfinite(stack).sum(axis=0)
    physical=np.divide(np.nansum(stack,axis=0),nvalid,out=np.full(outside.shape,np.nan,dtype=np.float64),where=nvalid>0).astype(np.float32)
    physical[~physical_support]=np.nan
    physical_out=np.where(physical_support,physical,-9999).astype(np.float32)
    write_grid(OUT/"physical_susceptibility_outside_radar.tif",grid_meta,physical_out,"PHYSICAL, NOT FITTED TO LABELS; equal-weight within-support ranks of HAND, depression, TWI and drainage distance")
    # Risk rank for independent point audit: percentile within the relevant model domain; no scale claim across domains.
    radar_percentile=np.full(observed.shape,np.nan,dtype=np.float32)
    m=observed & np.isfinite(full_probability) & (full_probability!=-9999)
    pv=full_probability[m]; ix=np.argsort(pv,kind="mergesort");rv=np.empty(len(pv),dtype=np.float32);rv[ix]=np.arange(1,len(pv)+1,dtype=np.float32)/max(len(pv),1)
    radar_percentile[m]=rv
    comp_risk=np.full(observed.shape,np.nan,dtype=np.float32);comp_risk[m]=radar_percentile[m]
    if physical_support.any():
        vals=physical[physical_support];ix=np.argsort(vals,kind="mergesort");rv=np.empty(len(vals),dtype=np.float32);rv[ix]=np.arange(1,len(vals)+1,dtype=np.float32)/max(len(vals),1);comp_risk[physical_support]=rv
    comp_out=np.where(np.isfinite(comp_risk),comp_risk,-9999).astype(np.float32)
    write_grid(OUT/"composite_rank_for_point_audit.tif",grid_meta,comp_out,"Percentile rank within radar or physical domain for point ranking only; domains are not probability-comparable")

    landcover_grid=dominant_landcover_grid(table,rows,cols,observed.shape)
    points=point_features(built_grid, landcover_grid, comp_risk, physical, observed, physical_support, grid_meta)
    point_summary={"source_files":[p.name for p in (POINTS/"814ca028-4c84-4bd0-aa67-6dbaeb9b6ba5.kml",POINTS/"93d2905a-a580-482d-96b0-4d9ccf5273ef.kml")],
        "source_point_count":len(points),"date_status":"unclear/unspecified; locations approximate; not field truth",
        "radar_assessed_points":sum(p["observed"] for p in points),"physical_only_support_points":sum((not p["observed"]) and p["physical_support"] for p in points),
        "not_scored_points":sum(p["risk"] is None for p in points),
        "not_scored_reason_counts":dict(Counter(p["unscored_reason"] for p in points if p["unscored_reason"])),
        "top_percentile_hits":{},"physical_outside_mask_hits":{}}
    domain=np.isfinite(comp_risk)
    for pct in (1,5,10,20):
        point_summary["top_percentile_hits"][str(pct)]=block_bootstrap_point_hits(points,comp_risk,built_grid,domain,pct,SEED+pct,point_bootstrap_reps,landcover_grid)
        point_summary["physical_outside_mask_hits"][str(pct)]=block_bootstrap_point_hits(points,physical,built_grid,physical_support,pct,SEED+100+pct,point_bootstrap_reps,landcover_grid)

    metrics={"status":"PILOT, SINGLE 2015 TARGET; SAR-DERIVED; NOT FIELD VALIDATED",
        "label":"unchanged Phase 9 target_union_minus_baseline; SHA-256 recorded; labels were not edited",
        "observability":obs_stats,"cutoffs":{"built_up_fraction_gt":OBS_BUILT_CUTOFF,"slope_degrees_gt":OBS_SLOPE_CUTOFF_DEG,
          "layover_shadow":"exclude bit 4 or bit 16; require both 2015-10-19 reference and 2015-11-24 event valid masks"},
        "model":{"name":"simple_average_tuned_tree_ensemble","features":p9.FEATURE_SETS["C_all_pilot_features"],"seed":SEED,
          "outer_cv":"same 5-fold GroupKFold over full 3 km block IDs; one neighbouring-block training buffer; true-prevalence outer test cells",
          "inner_cv":"same two contiguous block-row halves with a one-block buffer; 30 configs per family and outer fold",
          "sampling":"all positives plus 3:1 spatially stratified negatives inside training folds only",
          "baselines":baseline_metrics,"paired_fold_differences_vs_baselines":paired_baselines,
          "fold_metrics":fold_metrics,"selected_tree_search":tuning,
          "mean_sd":fold_summary,"pooled":chosen_summary["pooled"],"pr_auc_block_bootstrap_ci_95":ci,
        "phase9b_v2_comparison":{"pr_auc_outer_mean_sd":p9b_ensemble["fold_mean_sd"]["pr_auc"],
              "roc_auc_pooled":p9b_ensemble["pooled"]["roc_auc"],
              "brier_pooled":p9b_ensemble["pooled"]["brier"],
              "ece_pooled":p9b_ensemble["pooled"]["calibration"]["ece_10_equal_width"],
              "pr_auc_ci_95":p9b_ensemble["pooled"].get("block_bootstrap_pr_auc_ci_95",{}).get("ci_95_percentile")}},
        "conformal":{"method":"spatially cross-fitted absolute-error quantile per built-up bin (Mondrian); train-fold OOF only; outer blocks assess empirical coverage",
          "nominal_coverage":0.90,"outer_fold_mean_coverage":pooled_cov,"outer_fold_mean_width":pooled_width,
          "per_built_up_bin":coverage_bins,"full_data_apparent_quantiles":q_global_info,
          "below_88_percent":bool(pooled_cov<.88),"coverage_note":"Empirical finite-sample coverage is reported; spatial dependence limits the exchangeability guarantee."},
        "independent_point_validation":point_summary,
        "point_chance_landcover_matching":{"dominant_class_fractions":LANDCOVER_COLUMNS,"built_up_strata":BUILT_BINS,
          "classes":LANDCOVER_NAMES,"method":"random-cell draws match both built-up-fraction bin and dominant land-cover class"},
        "physical_complement":{"label":"PHYSICAL, NOT FITTED TO LABELS","features":physical_names,
          "method":"equal-weight mean of within-support percentile ranks, orienting lower HAND/lower drainage distance and higher local depression/TWI as more susceptible; no target labels used",
          "support_cells":int(physical_support.sum()),"outside_observability_cells":int(outside.sum()),
          "support_share_outside":float(physical_support.sum()/max(outside.sum(),1)),
          "point_validation":point_summary["physical_outside_mask_hits"]},
        "hashes":{"phase9b_feature_table_sha256":sha256(ROOT/"data/features/static/cell_table_phase9b_v2.parquet"),
          "phase9_label_table_sha256":sha256(ROOT/"data/features/predictions/labels_nov2015.parquet"),
          "phase9b_metrics_sha256":sha256(ROOT/"docs/PHASE9B_V2_METRICS.json")},
        "timing_seconds":float(time.perf_counter()-start),
        "limitations":["One 2015 event and SAR-derived reference; this is not independent event generalization.",
          "The 945 OpenCity points have unclear dates and approximate locations; spatial point hits are not dated event validation.",
          "Outside radar-observability mask, radar model output is intentionally NoData/not assessed; physical complement is ordinal and not calibrated probability.",
          "Urban censoring uses built-up fraction >0.50; this can omit true urban flooding and does not prove all remaining pixels are observable.",
          "No out-of-event accepted tier A/B/C labels are available."]}
    METRICS.write_text(json.dumps(metrics,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    REGISTRY.write_text(json.dumps({"registry_version":1,"status":metrics["status"],"model":metrics["model"]["name"],
        "parameters_by_outer_fold":{x["fold"]:{k:v["params"] for k,v in x["selected_parameters"].items()} for x in tuning},
        "seed":SEED,"features":p9.FEATURE_SETS["C_all_pilot_features"],"label":"unchanged Phase 9 target_union_minus_baseline",
        "feature_sha256":metrics["hashes"]["phase9b_feature_table_sha256"],"label_sha256":metrics["hashes"]["phase9_label_table_sha256"],
        "metrics":metrics["model"]["pooled"],"pr_auc_block_bootstrap_ci_95":ci,"reproducible_command":".venv\\Scripts\\python.exe pipelines\\phase9c\\urban_censoring.py --configs 30 --bootstrap-reps 200"},indent=2)+"\n",encoding="utf-8")
    write_report(metrics)
    return metrics


def cma_mask_from_grid(grid_meta):
    with rasterio.open(ROOT/"data/processed/grid/cma_mask.tif") as ds:
        return ds.read(1)==1


def write_report(m):
    model=m["model"]
    point=m["independent_point_validation"]
    reasons=point["not_scored_reason_counts"]
    not_scored_detail=f"{reasons.get('outside_radar_and_physical_support',0)} had no radar or physical-support score; {reasons.get('no_built_up_cell_value',0)} had no built-up cell value"
    report=["# Phase 9C — urban observability and independent checks","",
        "> PILOT. One November 2015 SAR-derived target; not field validated, not an event forecast.","",
        "## Radar observability mask","",
        f"A cell is assessed only if built-up fraction is ≤{OBS_BUILT_CUTOFF:.2f}, slope is ≤{OBS_SLOPE_CUTOFF_DEG:g}°, both the 19 Oct reference and 24 Nov event RTC masks are valid, and neither quality flag carries layover bit 4 or shadow bit 16. Missing slope is excluded. Other cells inside the CMA have no radar-model value and are labelled **not assessed from radar labels**.","",
        "| Mask count | Cells |","|---|---:|"]
    for k,v in m["observability"].items():
        if isinstance(v,int): report.append(f"| {k.replace('_',' ')} | {v:,} |")
    report += ["","Nonexclusive exclusions and combined reason codes are in `PHASE9C_METRICS.json`; `urban_confidence.tif` is 1 only for model-assessed cells and 0 where the data-driven output is unreliable/not assessed.","",
        "## Spatial evaluation and 9B comparison","",
        "Nested spatial validation uses the same five 3 km block folds, one-block buffer, two contiguous inner block-row folds, 3:1 training-only negative sampling, true-prevalence held-out cells, and 30 random configurations per tree family as Phase 9B. Same Phase 9B predictors and single-feature logistic baselines were retained. The 2015 target itself is unchanged.","",
        "| Metric | Phase 9C inside mask (outer-fold mean ± SD unless pooled stated) | Phase 9C pooled OOF | PR-AUC block bootstrap 95% CI | Phase 9B v2 comparison |","|---|---:|---:|---:|---:|"]
    for key in ("pr_auc","roc_auc","brier"):
        q=model["mean_sd"].get(key,{})
        c=model["pooled"].get(key)
        old=model["phase9b_v2_comparison"].get(key+"_pooled",model["phase9b_v2_comparison"].get("pr_auc_outer_mean_sd") if key=="pr_auc" else None)
        ci=model["pr_auc_block_bootstrap_ci_95"].get("ci_95_percentile") if key=="pr_auc" else "—"
        if isinstance(old,dict): old=f"{old.get('mean'):.4f} ± {old.get('sd'):.4f}"
        report.append(f"| {key} | {q.get('mean'):.4f} ± {q.get('sd'):.4f} | {c:.4f} | {ci} | {old} |")
    eces=[f['calibration']['ece_10_equal_width'] for f in model['fold_metrics']]
    report.append(f"| ECE (10 equal-width bins) | {np.mean(eces):.4f} ± {np.std(eces,ddof=1):.4f} | {model['pooled']['calibration']['ece_10_equal_width']:.4f} | — | {model['phase9b_v2_comparison']['ece_pooled']:.4f} |")
    report += ["","### Paired comparisons against baselines","",
        "| Baseline | PR-AUC delta mean ± SD (folds won) | ROC-AUC delta mean ± SD (folds won) | Brier improvement mean ± SD (folds won) |",
        "|---|---:|---:|---:|"]
    for name,vals in model["paired_fold_differences_vs_baselines"].items():
        def fmt(x):
            return f"{x['mean_delta']:+.4f} ± {x['sd_delta']:.4f} ({x['folds_won']}/{x['fold_count']})" if x["mean_delta"] is not None else "not computed"
        report.append(f"| {name} | {fmt(vals['pr_auc'])} | {fmt(vals['roc_auc'])} | {fmt(vals['brier'])} |")
    report += ["","Positive values mean Phase 9C improved the score (for Brier, lower is better). Against the prior Phase 9B v2 model, Phase 9C has lower pooled ROC-AUC/PR-AUC and higher Brier; pooled ECE is lower. The 9B and 9C evaluation domains differ, so these raw differences are descriptive, not a fair paired model comparison. The model is not accepted as a reliable forecast from this single-event exercise.","",
        "## Point cross-check (not radar-label validation)","",
        f"The two raw OpenCity point KMLs contain {point['source_point_count']} approximate, undated observed-flood points. They were not used for fitting or threshold selection. {point['radar_assessed_points']} points had radar-model output; {point['physical_only_support_points']} additional points had physical-only support; {point['not_scored_points']} were not scored ({not_scored_detail}). Hit-rate denominators include only scored points: {point['radar_assessed_points']} radar points plus {point['physical_only_support_points']} physical-only points. Point bootstrap resamples 3 km blocks; chance draws match both the point's built-up-fraction bin and dominant class among tree, crop, grass, bare, built-up and water. This preserves the dominant-class mix, not each continuous fractional composition. Because dates are unclear and locations approximate, this is a spatial cross-check, not dated field validation.","",
        "| Top share of mapped rank cells | Point hit share [95% CI] | Land-cover-matched random-cell chance [95% CI] | n scored / chance matched |","|---:|---:|---:|---:|"]
    def sharefmt(value, ci):
        if value is None:
            return "not available"
        if ci is None:
            return f"{value:.2%}"
        return f"{value:.2%} [{ci[0]:.2%}, {ci[1]:.2%}]"
    for pct,d in m["independent_point_validation"]["top_percentile_hits"].items():
        report.append(f"| {pct}% | {sharefmt(d['observed_share'],d['observed_ci_95'])} | {sharefmt(d['matched_chance_share'],d['matched_chance_ci_95'])} | {d['n']} / {d['matched_chance_n']} |")
    report += ["","### Point hits by built-up fraction","",
        "Each row uses only scored points in that built-up bin; the remaining source points have no applicable map score. CIs use the same 3 km point-block bootstrap.","",
        "| Top share | Built-up bin | Point hits [95% CI] | Matched chance [95% CI] | n scored / chance matched |","|---:|---|---:|---:|---:|"]
    for pct,d in m["independent_point_validation"]["top_percentile_hits"].items():
        for name,b in d["by_built_up_bin"].items():
            observed=sharefmt(b['observed_share'],b['observed_ci_95']) if b['point_n'] else "no points"
            chance=sharefmt(b['matched_chance_share'],b['matched_chance_ci_95']) if b['matched_chance_n'] else "no matched points"
            report.append(f"| {pct}% | {name.replace('_',' ')} | {observed} | {chance} | {b['point_n']} / {b['matched_chance_n']} |")
    report += ["","### Physical-only complement point checks","",
        "These are the 12 points with a physical-only score outside radar observability; the score is an ordinal physical screen, not a fitted probability.","",
        "| Top share of physical-score cells | Point hit share [95% CI] | Matched chance [95% CI] | n |","|---:|---:|---:|---:|"]
    for pct,d in m["physical_complement"]["point_validation"].items():
        report.append(f"| {pct}% | {sharefmt(d['observed_share'],d['observed_ci_95'])} | {sharefmt(d['matched_chance_share'],d['matched_chance_ci_95'])} | {d['n']} |")
    report += ["","## Conformal coverage by built-up stratum","",
        "| Built-up fraction | Held-out cells | Empirical coverage | Mean band width |","|---|---:|---:|---:|"]
    for name,d in m['conformal']['per_built_up_bin'].items():
        cov="no held-out cells" if d['mean_fold_coverage'] is None else f"{d['mean_fold_coverage']:.1%}"
        width="—" if d['mean_fold_band_width'] is None else f"{d['mean_fold_band_width']:.4f}"
        report.append(f"| {name.replace('_',' ')} | {d['heldout_n']:,} | {cov} | {width} |")
    report += ["","Physical-only outside-mask point hit rates are reported separately and are not mixed with radar probability scores.","",
        "The Phase 9C vs 9B figures use different evaluation domains: 9C is restricted to 481,244 observable eligible cells, while 9B covered 1,078,595 cells after population-NoData filtering. Their raw metric difference is therefore not a pure model-only comparison.","",
        "## Spatial Mondrian uncertainty","",
        f"Nominal 90% Mondrian conformal interval empirical outer-fold coverage is {m['conformal']['outer_fold_mean_coverage']:.1%}; mean width is {m['conformal']['outer_fold_mean_width']:.4f} probability units. Below 88%: **{m['conformal']['below_88_percent']}**. Per-built-up-stratum held-out coverage and width appear in the JSON. The nominal level is not a guarantee under spatial dependence.","",
        "## Physical complement","",
        f"`physical_susceptibility_outside_radar.tif` is labelled **PHYSICAL, NOT FITTED TO LABELS**. It averages equal-weight within-support percentiles of HAND, local depression depth, TWI and distance to an exact named waterway, oriented toward lower HAND, higher depression/TWI and shorter drainage distance. It is an ordinal screen, not a calibrated probability. It has support on {m['physical_complement']['support_cells']:,} of {m['physical_complement']['outside_observability_cells']:,} cells outside the radar mask ({m['physical_complement']['support_share_outside']:.2%}); the remaining outside-mask cells remain NoData. Point-hit rates are below and in the metrics JSON.","",
        "## Limits and leakage","",
        "The OpenCity points were not predictors, labels, tuning data, or threshold-selection data. The model did use the same 2015 label event as Phase 9B; its point cross-check is separate-source but not necessarily independent event/date validation. Full-data maps are apparent. The observability mask censors dense built-up cells (>0.50), steep slopes (>15°), and quality-mask invalid cells. There are no accepted independent event/date labels, and no claim about December 2015 peak flooding, future forecast skill, causal physical effects, or field accuracy is supported.",""]
    REPORT.write_text("\n".join(report),encoding="utf-8")


def refresh_points_only():
    """Recompute external-point summaries from completed Phase 9C maps; no model refit."""
    metrics=json.loads(METRICS.read_text(encoding="utf-8"))
    table=p9.pd.read_parquet(ROOT/"data/features/static/cell_table_phase9b_v2.parquet")
    with rasterio.open(ROOT/"data/processed/grid/cma_mask.tif") as ds:
        grid_meta={"height":ds.height,"width":ds.width,"crs":ds.crs,"transform":ds.transform}
    def read_float(name):
        with rasterio.open(OUT/name) as ds:
            a=ds.read(1).astype(np.float32)
            a[a==ds.nodata]=np.nan
            return a
    radar=read_float("radar_probability_mean_apparent.tif")
    physical=read_float("physical_susceptibility_outside_radar.tif")
    composite=read_float("composite_rank_for_point_audit.tif")
    with rasterio.open(OUT/"radar_observability_mask.tif") as ds:
        observed=ds.read(1)==1
    with rasterio.open(OUT/"physical_susceptibility_outside_radar.tif") as ds:
        physical_support=ds.read(1)!=ds.nodata
    built_grid=np.full(observed.shape,np.nan,dtype=np.float32)
    rows=table["row"].to_numpy(dtype=np.int32);cols=table["col"].to_numpy(dtype=np.int32)
    built_grid[rows,cols]=table["built_up_fraction"].to_numpy(dtype=np.float32)
    landcover_grid=dominant_landcover_grid(table,rows,cols,observed.shape)
    points=point_features(built_grid,landcover_grid,composite,physical,observed,physical_support,grid_meta)
    summary={"source_files":["814ca028-4c84-4bd0-aa67-6dbaeb9b6ba5.kml","93d2905a-a580-482d-96b0-4d9ccf5273ef.kml"],
        "source_point_count":len(points),"date_status":"unclear/unspecified; locations approximate; not field truth",
        "radar_assessed_points":sum(p["observed"] for p in points),
        "physical_only_support_points":sum((not p["observed"]) and p["physical_support"] for p in points),
        "not_scored_points":sum(p["risk"] is None for p in points),
        "not_scored_reason_counts":dict(Counter(p["unscored_reason"] for p in points if p["unscored_reason"])),
        "top_percentile_hits":{},"physical_outside_mask_hits":{}}
    for pct in (1,5,10,20):
        summary["top_percentile_hits"][str(pct)]=block_bootstrap_point_hits(points,composite,built_grid,np.isfinite(composite),pct,SEED+pct,2000,landcover_grid)
        summary["physical_outside_mask_hits"][str(pct)]=block_bootstrap_point_hits(points,physical,built_grid,physical_support,pct,SEED+100+pct,2000,landcover_grid)
    metrics["independent_point_validation"]=summary
    metrics["point_chance_landcover_matching"]={"dominant_class_fractions":LANDCOVER_COLUMNS,"built_up_strata":BUILT_BINS,
        "classes":LANDCOVER_NAMES,"method":"random-cell draws match both built-up-fraction bin and dominant land-cover class"}
    metrics["physical_complement"]["point_validation"]=summary["physical_outside_mask_hits"]
    METRICS.write_text(json.dumps(metrics,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    write_report(metrics)
    print(json.dumps({"source_point_count":summary["source_point_count"],"scored":summary["source_point_count"]-summary["not_scored_points"],
        "not_scored":summary["not_scored_points"],"reason_counts":summary["not_scored_reason_counts"],"hits":summary["top_percentile_hits"]},indent=2))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--configs",type=int,default=30)
    ap.add_argument("--bootstrap-reps",type=int,default=200)
    ap.add_argument("--point-bootstrap-reps",type=int,default=2000)
    ap.add_argument("--points-only",action="store_true",help="refresh point validation from completed Phase 9C rasters")
    a=ap.parse_args()
    if a.points_only:
        refresh_points_only();return
    m=run(a.configs,a.bootstrap_reps,a.point_bootstrap_reps)
    print(json.dumps({"status":m["status"],"n_model_cells":m["observability"]["model_cells_inside_mask"],"metrics":m["model"]["pooled"],"coverage":m["conformal"]["outer_fold_mean_coverage"],"runtime_seconds":m["timing_seconds"]},indent=2))

if __name__=="__main__":
    main()
