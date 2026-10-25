"""Phase 9B nested spatial-CV upgrade. Inputs are existing derived files only.

The Phase 9 label is read as-is. This script refuses to overwrite any Phase 9B
report or map. All learned transforms, sampling, calibration and thresholds are
fit from training blocks; outer metrics are evaluated on full-prevalence blocks.
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
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from lightgbm import LGBMClassifier
from rasterio.transform import xy
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipelines.phase9.pilot import buffered_train_groups

SEED = 20261024
OUTER_FOLDS = 5
INNER_FOLDS = 2
BLOCK_BUFFER_RADIUS = 1
NEGATIVE_TO_POSITIVE = 3
# Match the Phase 9 pilot: every flooded training cell plus a 3:1
# block-stratified sample of nonflooded cells. Never cap the positive class.
MAX_TRAIN_POSITIVES = None
TUNING_CONFIGS = 30
BOOTSTRAP_REPS = 200
CELL_AREA_KM2 = 0.0009
FEATURE_TABLE = ROOT / "data/features/static/cell_table_phase9b_v2.parquet"
FEATURE_META = ROOT / "data/features/static/cell_table_phase9b_v2.json"
LABEL_TABLE = ROOT / "data/features/predictions/labels_nov2015.parquet"
BLOCKS = ROOT / "data/processed/alignment/spatial_blocks.tif"
GRID = ROOT / "data/processed/grid/cma_mask.tif"
METRICS_OUT = ROOT / "docs/PHASE9B_V2_METRICS.json"
REGISTRY_OUT = ROOT / "docs/PHASE9B_V2_MODEL_REGISTRY.json"
REPORT_OUT = ROOT / "docs/PHASE9B_MODEL_UPGRADE_V2.md"
OUT_DIR = ROOT / "data/features/predictions/phase9b_v2"
FIG_DIR = ROOT / "docs/figures/phase9b_v2"
ALLOW_EXISTING_GENERATED_RASTERS = False

TERRAIN_FEATURES = [
    "elevation_m", "slope_deg", "twi_d8_proxy", "flow_accumulation_cells_d8",
    "hand_d8_accum100_m", "relative_elevation_5cells_m", "relative_elevation_15cells_m",
    "relative_elevation_33cells_m", "local_depression_depth_m", "plan_curvature_per_m",
    "profile_curvature_per_m", "distance_to_all_available_water_m", "distance_to_coast_or_sea_m",
    "d8_flow_length_to_stream_25cells_m", "d8_flow_length_to_stream_100cells_m",
    "d8_flow_length_to_stream_250cells_m", "d8_flow_length_to_stream_500cells_m",
    "upslope_area_km2", "upslope_area_ge_25cells_km2", "upslope_area_ge_100cells_km2",
    "upslope_area_ge_250cells_km2", "upslope_area_ge_500cells_km2",
]
LANDCOVER_FEATURES = ["built_up_fraction", "tree_fraction", "crop_fraction", "grass_fraction", "bare_fraction"]
EXTRA_FEATURES = ["building_density_per_km2", "distance_to_nearest_road_node_m",
                  "distance_to_exact_named_waterway_m", "worldpop_2021"]
FEATURE_SETS = {
    "A_terrain_hydrology": TERRAIN_FEATURES,
    "B_terrain_plus_landcover": TERRAIN_FEATURES + LANDCOVER_FEATURES,
    "C_all_pilot_features": TERRAIN_FEATURES + LANDCOVER_FEATURES + EXTRA_FEATURES,
}
SINGLE_BASELINES = {
    "elevation_logistic": ["elevation_m"],
    "river_distance_logistic": ["distance_to_exact_named_waterway_m"],
    "twi_logistic": ["twi_d8_proxy"],
    "slope_logistic": ["slope_deg"],
    "relative_elevation_15_logistic": ["relative_elevation_15cells_m"],
    "hand_logistic": ["hand_d8_accum100_m"],
    "terrain_logistic": ["elevation_m", "slope_deg", "twi_d8_proxy", "hand_d8_accum100_m",
                          "relative_elevation_15cells_m", "flow_accumulation_cells_d8"],
}
MODEL_DEFAULTS = {
    "random_forest": {"n_estimators": 140, "max_depth": 16, "min_samples_leaf": 3,
                       "max_features": "sqrt", "n_jobs": 4},
    "xgboost": {"n_estimators": 180, "max_depth": 6, "learning_rate": 0.05,
                "subsample": 0.8, "colsample_bytree": 0.8, "reg_lambda": 1.0,
                "tree_method": "hist", "n_jobs": 4},
    "lightgbm": {"n_estimators": 180, "num_leaves": 31, "learning_rate": 0.05,
                 "subsample": 0.8, "colsample_bytree": 0.8, "reg_lambda": 1.0,
                 "n_jobs": 4, "verbosity": -1},
}


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fit_estimator(kind: str, params: dict, x: np.ndarray, y: np.ndarray, seed: int):
    if kind == "logistic":
        clf = LogisticRegression(C=1.0, max_iter=500, solver="lbfgs", random_state=seed)
    elif kind == "random_forest":
        p = dict(params); p.update(random_state=seed, n_jobs=4, class_weight=None)
        clf = RandomForestClassifier(**p)
    elif kind == "xgboost":
        p = dict(params); p.update(random_state=seed, eval_metric="logloss", n_jobs=4)
        clf = XGBClassifier(**p)
    elif kind == "lightgbm":
        p = dict(params); p.update(random_state=seed, n_jobs=4, verbosity=-1)
        clf = LGBMClassifier(**p)
    else:
        raise ValueError(f"Unknown estimator {kind}")
    model = Pipeline([("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                      ("scaler", StandardScaler()), ("classifier", clf)])
    model.fit(x, y)
    return model


def stratified_indices(indices: np.ndarray, groups: np.ndarray, target: int,
                        rng: np.random.Generator) -> np.ndarray:
    if target >= len(indices):
        return indices.copy()
    if target <= 0:
        return np.empty(0, dtype=np.int64)
    gv, counts = np.unique(groups[indices], return_counts=True)
    exact = target * counts / counts.sum()
    quotas = np.floor(exact).astype(int)
    for k in np.argsort(-(exact - quotas))[: target - int(quotas.sum())]:
        quotas[k] += 1
    selected = []
    for g, quota in zip(gv, quotas):
        cand = indices[groups[indices] == g]
        if quota:
            selected.append(rng.choice(cand, min(int(quota), len(cand)), replace=False))
    return np.concatenate(selected).astype(np.int64) if selected else np.empty(0, dtype=np.int64)


def sample_train(indices: np.ndarray, y: np.ndarray, groups: np.ndarray,
                 seed: int, max_positives: int | None = MAX_TRAIN_POSITIVES) -> tuple[np.ndarray, dict]:
    rng = np.random.default_rng(seed)
    pos = indices[y[indices] == 1]
    neg = indices[y[indices] == 0]
    n_pos = min(len(pos), max_positives) if max_positives else len(pos)
    pos = stratified_indices(pos, groups, n_pos, rng)
    neg = stratified_indices(neg, groups, min(len(neg), len(pos)*NEGATIVE_TO_POSITIVE), rng)
    selected = np.concatenate([pos, neg])
    rng.shuffle(selected)
    return selected, {"positive_total": int(np.sum(y[indices] == 1)), "positive_used": int(len(pos)),
                      "negative_total": int(np.sum(y[indices] == 0)), "negative_used": int(len(neg)),
                      "negative_to_positive": float(len(neg)/max(len(pos),1)), "seed": int(seed)}


def make_split_specs(indices: np.ndarray, groups: np.ndarray, y: np.ndarray,
                     positions: dict[int, tuple[int, int]], n_splits: int) -> list[tuple[np.ndarray,np.ndarray]]:
    if n_splits != 2:
        raise ValueError("Phase 9B inner spatial CV currently requires exactly two folds")
    # Two geographically contiguous north/south block-row folds avoid the
    # fragmented GroupKFold half-splits that can lose every training block
    # when a one-block buffer is removed from this sparse CMA block layout.
    unique=np.unique(groups[indices])
    row_values=sorted({positions[int(g)][0] for g in unique})
    candidates=[]
    for cut in row_values[:-1]:
        va_groups_a=np.array([g for g in unique if positions[int(g)][0]<=cut],dtype=np.int32)
        va_groups_b=np.array([g for g in unique if positions[int(g)][0]>cut],dtype=np.int32)
        if not len(va_groups_a) or not len(va_groups_b):
            continue
        folds=[]
        valid=True
        for va_groups in (va_groups_a,va_groups_b):
            va=indices[np.isin(groups[indices],va_groups)]
            other=np.setdiff1d(unique,va_groups,assume_unique=False)
            kept=buffered_train_groups(other,va_groups,positions,BLOCK_BUFFER_RADIUS)
            tr=indices[np.isin(groups[indices],kept)]
            if not len(tr) or not len(va) or np.unique(y[tr]).size<2:
                valid=False;break
            folds.append((tr,va))
        if valid:
            imbalance=abs(len(folds[0][1])-len(folds[1][1]))/max(len(indices),1)
            candidates.append((imbalance,folds))
    if not candidates:
        raise ValueError("No two-fold contiguous spatial split retains both classes after the one-block buffer")
    specs=min(candidates,key=lambda x:x[0])[1]
    va_all=np.concatenate([va for _,va in specs])
    if len(np.unique(va_all))!=len(indices) or set(va_all.tolist())!=set(indices.tolist()):
        raise ValueError("Inner spatial validation folds do not partition outer training cells exactly once")
    return specs


def raw_prior_adjust(p: np.ndarray, sampled_prev: float, train_prev: float) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=np.float64), 1e-7, 1-1e-7)
    a = np.clip(sampled_prev, 1e-7, 1-1e-7)
    b = np.clip(train_prev, 1e-7, 1-1e-7)
    odds = p/(1-p) * ((b/(1-b))/(a/(1-a)))
    return odds/(1+odds)


def _logit(p: np.ndarray) -> np.ndarray:
    q = np.clip(np.asarray(p, dtype=np.float64), 1e-6, 1-1e-6)
    return np.log(q/(1-q)).reshape(-1,1)


def fit_platt(p: np.ndarray, y: np.ndarray):
    if len(np.unique(y)) < 2:
        raise ValueError("Platt calibration training data must contain both classes")
    model = LogisticRegression(C=1e6, max_iter=1000, solver="lbfgs")
    model.fit(_logit(p), y.astype(np.uint8))
    return model


def apply_platt(model, p: np.ndarray) -> np.ndarray:
    return model.predict_proba(_logit(p))[:, 1]


def select_f1_threshold(y: np.ndarray, p: np.ndarray) -> float:
    order = np.argsort(p)
    candidates = np.unique(np.quantile(p, np.linspace(0, 1, min(401, len(p)))))
    best, threshold = -1.0, 0.5
    for t in candidates:
        score = f1_score(y, p >= t, zero_division=0)
        if score > best:
            best, threshold = float(score), float(t)
    return threshold


def calibration_bins(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> dict:
    edges = np.linspace(0, 1, n_bins+1)
    ix = np.minimum(np.digitize(p, edges[1:-1]), n_bins-1)
    rows, ece = [], 0.0
    for b in range(n_bins):
        m = ix == b
        if not m.any():
            continue
        mp, obs, n = float(np.mean(p[m])), float(np.mean(y[m])), int(m.sum())
        ece += n/len(y)*abs(mp-obs)
        rows.append({"low": float(edges[b]), "high": float(edges[b+1]),
                     "mean_probability": mp, "observed_fraction": obs, "count": n})
    return {"ece_10_equal_width": float(ece), "bins": rows}


def metric_bundle(y: np.ndarray, p: np.ndarray, threshold: float, train_prevalence: float,
                  q90: float | None = None) -> dict:
    y = np.asarray(y, dtype=np.uint8)
    p = np.clip(np.asarray(p, dtype=np.float64), 0, 1)
    pred = p >= threshold
    base = np.full(len(y), float(train_prevalence))
    brier = float(brier_score_loss(y, p))
    baseline_brier = float(brier_score_loss(y, base))
    result = {"n": int(len(y)), "prevalence_true": float(y.mean()),
              "roc_auc": float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else None,
              "pr_auc": float(average_precision_score(y, p)) if y.sum() else None,
              "threshold": float(threshold), "f1": float(f1_score(y, pred, zero_division=0)),
              "iou": float(np.sum(pred & (y == 1))/max(np.sum(pred | (y == 1)),1)),
              "precision": float(precision_score(y, pred, zero_division=0)),
              "recall": float(recall_score(y, pred, zero_division=0)),
              "brier": brier, "brier_skill_vs_train_prevalence": float(1-brier/baseline_brier) if baseline_brier else None,
              "calibration": calibration_bins(y, p)}
    if q90 is not None:
        lo, hi = np.maximum(0,p-q90), np.minimum(1,p+q90)
        covered = (y >= lo) & (y <= hi)
        result["interval_90"] = {"q_abs_residual": float(q90), "coverage": float(covered.mean()),
                                 "mean_width": float(np.mean(hi-lo)),
                                 "positive_coverage": float(covered[y==1].mean()) if np.any(y==1) else None,
                                 "negative_coverage": float(covered[y==0].mean()) if np.any(y==0) else None}
    return result


def inner_oof(kind: str, params: dict, x: np.ndarray, y: np.ndarray, groups: np.ndarray,
              train_idx: np.ndarray, positions: dict[int, tuple[int,int]], seed: int,
              max_positives: int | None = MAX_TRAIN_POSITIVES) -> tuple[np.ndarray,np.ndarray,np.ndarray,dict]:
    specs = make_split_specs(train_idx, groups, y, positions, INNER_FOLDS)
    oof_idx = np.concatenate([va for _,va in specs])
    if len(np.unique(oof_idx)) != len(oof_idx):
        raise ValueError("Inner block validation cells overlap")
    raw = np.full(len(y), np.nan, dtype=np.float32)
    fit_details=[]
    for fold,(tr,va) in enumerate(specs,1):
        sampled, sd = sample_train(tr, y, groups, seed+fold, max_positives)
        model=fit_estimator(kind, params, x[sampled], y[sampled], seed+fold)
        pp=model.predict_proba(x[va])[:,1]
        pp=raw_prior_adjust(pp, float(y[sampled].mean()), float(y[tr].mean()))
        raw[va]=pp.astype(np.float32)
        fit_details.append({"fold":fold,"train_cells":int(len(tr)),"validation_cells":int(len(va)),"sampling":sd})
    if np.isnan(raw[oof_idx]).any():
        raise RuntimeError("Inner OOF calibration predictions are incomplete")
    return oof_idx, raw[oof_idx].astype(np.float64), groups[oof_idx], {"splits":fit_details}


def crossfit_calibration(y: np.ndarray, groups: np.ndarray, indices: np.ndarray,
                         raw: np.ndarray, positions: dict[int,tuple[int,int]]) -> tuple[Any,np.ndarray,float,dict]:
    final=fit_platt(raw,y[indices])
    calibrated=np.full(len(indices),np.nan,dtype=np.float64)
    loc_groups=groups[indices]
    global_to_local={int(g):i for i,g in enumerate(indices)}
    for tr_global,va_global in make_split_specs(indices,groups,y,positions,INNER_FOLDS):
        tr_rel=np.array([global_to_local[int(g)] for g in tr_global],dtype=np.int64)
        va_rel=np.array([global_to_local[int(g)] for g in va_global],dtype=np.int64)
        train=tr_rel
        if len(train)==0 or len(np.unique(y[indices[train]]))<2:
            raise ValueError("Calibration block buffer left insufficient labels")
        cal=fit_platt(raw[train],y[indices[train]])
        calibrated[va_rel]=apply_platt(cal,raw[va_rel])
    if np.isnan(calibrated).any():
        raise RuntimeError("Cross-fitted calibration did not cover all inner OOF rows")
    threshold=select_f1_threshold(y[indices],calibrated)
    q90=float(np.quantile(np.abs(y[indices]-calibrated),0.90,method="higher"))
    return final,calibrated,threshold,{"q90_abs_residual":q90,"calibration_rows":int(len(indices)),
                                      "calibration_block_count":int(len(np.unique(loc_groups)))}


def evaluate_outer(kind: str, params: dict, x: np.ndarray, y: np.ndarray, groups: np.ndarray,
                   train_idx: np.ndarray, test_idx: np.ndarray,
                   positions: dict[int,tuple[int,int]], seed: int,
                   max_positives: int | None=MAX_TRAIN_POSITIVES) -> dict:
    inner_idx, inner_raw, _, inner_info = inner_oof(kind,params,x,y,groups,train_idx,positions,seed,max_positives)
    cal, train_cal, threshold, cal_info = crossfit_calibration(y,groups,inner_idx,inner_raw,positions)
    sampled, sample_info=sample_train(train_idx,y,groups,seed+999,max_positives)
    model=fit_estimator(kind,params,x[sampled],y[sampled],seed+999)
    raw_test=raw_prior_adjust(model.predict_proba(x[test_idx])[:,1],float(y[sampled].mean()),float(y[train_idx].mean()))
    test_p=apply_platt(cal,raw_test)
    q90=cal_info["q90_abs_residual"]
    return {"probability":test_p.astype(np.float32),"raw_probability":raw_test.astype(np.float32),
            "threshold":threshold,"q90":q90,"metrics":metric_bundle(y[test_idx],test_p,threshold,float(y[train_idx].mean()),q90),
            "train_calibration_indices":inner_idx,"train_calibration_probability":train_cal.astype(np.float32),
            "train_calibration_y":y[inner_idx],"train_calibration_groups":groups[inner_idx],
            "train_calibration_q90":q90,"sample":sample_info,"inner":inner_info,
            "calibration":cal_info,"params":params}


def random_configs(kind: str, seed: int, n: int=TUNING_CONFIGS) -> list[dict]:
    rng=np.random.default_rng(seed)
    out=[]
    for _ in range(n):
        if kind=="random_forest":
            depths=[10,16,24,None]; max_features=["sqrt",0.5,0.8]
            depth=depths[int(rng.integers(len(depths)))]
            max_feature=max_features[int(rng.integers(len(max_features)))]
            p={"n_estimators":int(rng.choice([60,90,120])),"max_depth":depth,
               "min_samples_leaf":int(rng.choice([2,4,8])),"max_features":max_feature,
               "max_samples":float(rng.choice([0.6,0.8,1.0])),"bootstrap":True}
        elif kind=="xgboost":
            p={"n_estimators":int(rng.choice([60,90,120])),"max_depth":int(rng.choice([3,4,6,8])),
               "learning_rate":float(rng.choice([0.03,0.05,0.08,0.12])),"subsample":float(rng.choice([0.7,0.85,1.0])),
               "colsample_bytree":float(rng.choice([0.6,0.8,1.0])),"reg_lambda":float(rng.choice([1.0,3.0,8.0])),
               "tree_method":"hist"}
        else:
            leaves=int(rng.choice([15,31,47,63]))
            p={"n_estimators":int(rng.choice([60,90,120])),"num_leaves":leaves,
               "learning_rate":float(rng.choice([0.03,0.05,0.08,0.12])),"subsample":float(rng.choice([0.7,0.85,1.0])),
               "colsample_bytree":float(rng.choice([0.6,0.8,1.0])),"reg_lambda":float(rng.choice([1.0,3.0,8.0])),
               "min_child_samples":int(rng.choice([10,20,40]))}
        out.append(p)
    return out


def tune_nested(kind: str, x: np.ndarray, y: np.ndarray, groups: np.ndarray, outer_train: np.ndarray,
                positions: dict[int,tuple[int,int]], seed: int, config_count: int=TUNING_CONFIGS) -> tuple[dict,list[dict]]:
    inner_specs=make_split_specs(outer_train,groups,y,positions,INNER_FOLDS)
    configs=random_configs(kind,seed,config_count)
    scores=[]
    for ci,params in enumerate(configs,1):
        fold_scores=[]
        for fi,(tr,va) in enumerate(inner_specs,1):
            sampled,_=sample_train(tr,y,groups,seed+ci*100+fi,MAX_TRAIN_POSITIVES)
            model=fit_estimator(kind,params,x[sampled],y[sampled],seed+ci*100+fi)
            pp=raw_prior_adjust(model.predict_proba(x[va])[:,1],float(y[sampled].mean()),float(y[tr].mean()))
            fold_scores.append(float(average_precision_score(y[va],pp)))
        scores.append({"config_index":ci,"parameters":params,"inner_pr_auc_mean":float(np.mean(fold_scores)),
                       "inner_pr_auc_by_fold":fold_scores})
        if ci % 5 == 0:
            print(f"{kind}: evaluated {ci}/{config_count} inner-search configurations",flush=True)
    best=max(scores,key=lambda s:s["inner_pr_auc_mean"])
    return best["parameters"],scores


def outer_folds(orig_indices: np.ndarray, y: np.ndarray, groups: np.ndarray,
                positions: dict[int,tuple[int,int]]) -> list[dict]:
    specs=[]
    for fold,(tr,te) in enumerate(GroupKFold(n_splits=OUTER_FOLDS).split(np.zeros(len(orig_indices)),y[orig_indices],groups[orig_indices]),1):
        train=orig_indices[tr]; test=orig_indices[te]
        keep=buffered_train_groups(np.unique(groups[train]),np.unique(groups[test]),positions,BLOCK_BUFFER_RADIUS)
        train=train[np.isin(groups[train],keep)]
        specs.append({"fold":fold,"train":train,"test":test,"test_groups":np.unique(groups[test]),"train_groups":np.unique(groups[train])})
    return specs


def load_data():
    if not FEATURE_TABLE.is_file() or not LABEL_TABLE.is_file():
        raise FileNotFoundError("Run pipelines/phase9b/feature_build.py first; required new feature table or existing pilot labels are missing")
    table=pd.read_parquet(FEATURE_TABLE)
    labels=pd.read_parquet(LABEL_TABLE)
    if not np.array_equal(table[["row","col"]].to_numpy(),labels[["row","col"]].to_numpy()):
        raise ValueError("Phase 9B feature and Phase 9 label tables differ in cell order")
    target=labels["target_union_minus_baseline"].to_numpy(dtype=np.uint8)
    pilot_eligible=labels["eligible_for_model"].to_numpy(dtype=bool)
    pop_mask=~table["population_is_nodata"].to_numpy(dtype=bool)
    rows=table["row"].to_numpy(dtype=np.int32); cols=table["col"].to_numpy(dtype=np.int32)
    with rasterio.open(BLOCKS) as ds:
        block_raster=ds.read(1)
    groups=block_raster[rows,cols].astype(np.int32)
    group_positions={}
    for g,r,c in zip(groups,rows,cols):
        pos=(int(r//100),int(c//100))
        old=group_positions.setdefault(int(g),pos)
        if old!=pos:
            raise ValueError(f"Pilot spatial block {g} maps to multiple 3 km grid positions")
    orig=np.flatnonzero(pilot_eligible)
    eligible=pilot_eligible & pop_mask
    model_indices=np.flatnonzero(eligible)
    if int(np.sum(target[orig]))!=61166:
        raise ValueError("Phase 9 default union target count changed; refusing to rebuild or alter the label")
    return table,labels,target,pilot_eligible,eligible,model_indices,groups,group_positions,rows,cols,block_raster


def make_matrix(table: pd.DataFrame, features: list[str]) -> np.ndarray:
    missing=[f for f in features if f not in table]
    if missing:
        raise ValueError("Requested Phase 9B predictors missing: "+", ".join(missing))
    a=table[features].to_numpy(dtype=np.float32,na_value=np.nan,copy=True)
    a[~np.isfinite(a)]=np.nan
    return a


def summarize_folds(fold_rows: list[dict], keys: list[str]) -> dict:
    out={}
    for k in keys:
        v=[float(r[k]) for r in fold_rows if r.get(k) is not None and np.isfinite(r[k])]
        out[k]={"mean":float(np.mean(v)) if v else None,"sd":float(np.std(v,ddof=1)) if len(v)>1 else 0.0 if v else None}
    return out


def topk_metrics(y: np.ndarray,p: np.ndarray) -> dict:
    out={}
    order=np.argsort(-p)
    total=max(int(y.sum()),1)
    n=len(y)
    for pct in (1,2,5,10,20,50,100):
        k=max(1,int(math.ceil(n*pct/100)))
        hits=int(y[order[:k]].sum())
        out[str(pct)]={"cells":k,"precision":hits/k,"recall":hits/total,"gain_over_random":(hits/k)/max(float(y.mean()),1e-12)}
    return out


def paired_fold_differences(model_folds: dict[str,list[dict]], reference: str, metrics: list[str]) -> dict:
    result={}
    if reference not in model_folds:
        return result
    for name,folds in model_folds.items():
        if name==reference or len(folds)!=len(model_folds[reference]):
            continue
        result[name]={}
        for metric in metrics:
            d=[float(a[metric])-float(b[metric]) for a,b in zip(folds,model_folds[reference])
               if a.get(metric) is not None and b.get(metric) is not None]
            wins = sum(v < 0 for v in d) if metric in ("brier", "ece") else sum(v > 0 for v in d)
            result[name][metric]={"mean_delta":float(np.mean(d)) if d else None,
                                  "sd_delta":float(np.std(d,ddof=1)) if len(d)>1 else 0.0 if d else None,
                                  "folds_won":int(wins),"folds_compared":len(d),
                                  "win_direction":"lower_is_better" if metric in ("brier", "ece") else "higher_is_better"}
    return result


def block_bootstrap_ap(y: np.ndarray,p: np.ndarray,groups: np.ndarray,seed=SEED,n=BOOTSTRAP_REPS) -> dict:
    unique=np.unique(groups)
    by={int(g):np.flatnonzero(groups==g) for g in unique}
    rng=np.random.default_rng(seed)
    values=[]
    for _ in range(n):
        draw=rng.choice(unique,size=len(unique),replace=True)
        ix=np.concatenate([by[int(g)] for g in draw])
        if y[ix].sum()>0:
            values.append(float(average_precision_score(y[ix],p[ix])))
    return {"method":"resample entire 3 km blocks with replacement", "replicates_requested":n,
            "replicates_valid":len(values), "ci_95_percentile":[float(np.quantile(values,.025)),float(np.quantile(values,.975))] if values else None}


def morans_i_4_neighbor(residual: np.ndarray, valid: np.ndarray, rows: np.ndarray, cols: np.ndarray,
                        grid_shape: tuple[int,int]) -> dict:
    h,w=grid_shape
    loc=np.full(h*w,-1,dtype=np.int32)
    ix=np.flatnonzero(valid)
    loc[rows[ix]*w+cols[ix]]=np.arange(len(ix),dtype=np.int32)
    flat=residual[ix].astype(np.float64)
    mean=float(np.mean(flat)); centered=flat-mean
    # Add each horizontal/vertical edge once. W is 2 per undirected adjacency.
    sums=0.0; edges=0
    for dy,dx in ((0,1),(1,0)):
        r2=rows[ix]+dy; c2=cols[ix]+dx
        inside=(r2<h)&(c2<w)
        a=ix[inside]
        jloc=loc[r2[inside]*w+c2[inside]]
        good=jloc>=0
        if good.any():
            sums+=float(np.sum(centered[inside][good]*centered[jloc[good]]))
            edges+=int(good.sum())
    denom=float(np.sum(centered**2))
    value=float(len(ix)*sums/(edges*denom)) if edges and denom else None
    return {"morans_i_4_neighbor":value,"undirected_neighbor_pairs":edges,
            "interpretation":"descriptive OOF residual spatial autocorrelation; no inferential p-value computed"}


def write_raster(path: Path, values: np.ndarray, rows: np.ndarray, cols: np.ndarray,
                 grid_meta: dict, description: str, dtype="float32"):
    if path.exists() and ALLOW_EXISTING_GENERATED_RASTERS:
        with rasterio.open(path) as existing:
            if (existing.height,existing.width,existing.crs,existing.transform) != (
                    grid_meta["height"],grid_meta["width"],grid_meta["crs"],grid_meta["transform"]):
                raise ValueError(f"Existing Phase 9B raster has a different grid: {path.name}")
            if existing.descriptions[0] != description:
                raise ValueError(f"Existing Phase 9B raster description differs: {path.name}")
        return
    nodata = 255 if dtype == "uint8" else -9999
    grid=np.full((grid_meta["height"],grid_meta["width"]),nodata,dtype=dtype)
    grid[rows,cols]=values.astype(dtype)
    profile={"driver":"GTiff","height":grid_meta["height"],"width":grid_meta["width"],"count":1,
             "dtype":dtype,"crs":grid_meta["crs"],"transform":grid_meta["transform"],
             "nodata":nodata,"compress":"deflate","predictor":3 if dtype.startswith("float") else 1}
    with rasterio.open(path,"w",**profile) as ds:
        ds.write(grid,1); ds.set_band_description(1,description); ds.update_tags(status="APPARENT FULL-DATA MAP; PILOT SINGLE EVENT")


def run(config_count=TUNING_CONFIGS, bootstrap_reps=BOOTSTRAP_REPS,
        resume_generated_rasters: bool = False) -> dict:
    global ALLOW_EXISTING_GENERATED_RASTERS
    ALLOW_EXISTING_GENERATED_RASTERS=resume_generated_rasters
    outputs=[METRICS_OUT,REGISTRY_OUT,REPORT_OUT,OUT_DIR/"probability_mean_apparent.tif",
             OUT_DIR/"interval_lower90_apparent.tif",OUT_DIR/"interval_upper90_apparent.tif",
             OUT_DIR/"oof_residual.tif",OUT_DIR/"oof_error_class.tif",
             FIG_DIR/"phase9b_gain_curve.png",FIG_DIR/"phase9b_error_map.png",
             FIG_DIR/"phase9b_reliability.png",FIG_DIR/"phase9b_importance.png"]
    existing=[p for p in outputs if p.exists()]
    raster_outputs=set(outputs[3:8])
    if existing:
        if (not resume_generated_rasters or any(p not in raster_outputs for p in existing)):
            raise FileExistsError("Refusing to overwrite existing Phase 9B outputs: "+", ".join(str(p.relative_to(ROOT)) for p in existing))
    OUT_DIR.mkdir(parents=True,exist_ok=True); FIG_DIR.mkdir(parents=True,exist_ok=True)
    start=time.perf_counter()
    (table,labels,target,pilot_eligible,eligible,idx,groups,positions,rows_all,cols_all,blocks)=load_data()
    y=target.astype(np.uint8)
    # Same five pilot block assignments are reconstructed from the original eligible label rows.
    outer=outer_folds(np.flatnonzero(pilot_eligible),y,groups,positions)
    pilot=json.loads((ROOT/"docs/PHASE9_METRICS.json").read_text(encoding="utf-8"))
    pilot_folds=pilot["validation"]["folds"]
    if len(pilot_folds)!=OUTER_FOLDS:
        raise ValueError("Phase 9 pilot does not record the expected five outer folds")
    observed_test_groups=[]
    for f,spec in enumerate(outer):
        # The Phase 9 per-fold counts/prevalences are correct, but its saved
        # test_block_ids were accidentally copied from the final fold into
        # all five records. Reconstruct with the exact pilot GroupKFold code.
        ref=pilot_folds[f]
        if int(ref["test_cells_full_true_prevalence"])!=len(spec["test"]):
            raise ValueError(f"Reconstructed outer fold {f+1} test-cell count differs from Phase 9 pilot")
        if not np.isclose(float(ref["test_prevalence"]),float(y[spec["test"]].mean()),rtol=0,atol=1e-12):
            raise ValueError(f"Reconstructed outer fold {f+1} prevalence differs from Phase 9 pilot")
        observed_test_groups.append(set(map(int,spec["test_groups"])))
        spec["train"] = spec["train"][eligible[spec["train"]]]
        spec["test"] = spec["test"][eligible[spec["test"]]]
        if not len(spec["train"]) or not len(spec["test"]):
            raise ValueError(f"Population-NoData mask empties outer fold {f+1}")
    if any(observed_test_groups[i] & observed_test_groups[j]
           for i in range(len(observed_test_groups)) for j in range(i+1,len(observed_test_groups))):
        raise ValueError("Reconstructed Phase 9 test block assignments overlap")
    if set.union(*observed_test_groups)!=set(map(int,np.unique(groups[np.flatnonzero(pilot_eligible)]))):
        raise ValueError("Reconstructed Phase 9 folds do not partition the original pilot block set")
    yprev=float(y[idx].mean())
    xfull=make_matrix(table,FEATURE_SETS["C_all_pilot_features"])
    xsets={name:make_matrix(table,cols) for name,cols in FEATURE_SETS.items()}
    metrics={"status":"PILOT, SINGLE EVENT, OFFICIAL SAR-DERIVED LABEL; NOT FIELD VALIDATED",
             "target":"unchanged Phase 9 target_union_minus_baseline; no relabeling or target re-rasterization",
             "data":{"phase9_cells":int(pilot_eligible.sum()),"phase9_positives":int(y[pilot_eligible].sum()),
                     "phase9_prevalence":float(y[pilot_eligible].mean()),"population_nodata_cells_masked":int((pilot_eligible & ~eligible).sum()),
                     "model_cells":int(len(idx)),"model_positives":int(y[idx].sum()),"model_prevalence":yprev,
                     "feature_table_sha256":file_sha(FEATURE_TABLE),"feature_table_metadata_sha256":file_sha(FEATURE_META),
                     "pilot_label_table_sha256":file_sha(LABEL_TABLE)},
             "validation":{"outer":"reconstructed using the exact deterministic Phase 9 GroupKFold algorithm; 5 folds; full block ID held out",
                           "phase9_split_audit":"Per-fold held-out cell counts and true prevalences match docs/PHASE9_METRICS.json. Its serialized test_block_ids are incorrectly identical across all five folds (bookkeeping defect); Phase 9B does not trust those IDs, and instead reconstructs the assignments from source code and verifies disjoint complete block partitioning.",
                           "inner_split":"Two geographically contiguous block-row halves; choose the cut that best balances cells while retaining both classes after the same one-block buffer. The two inner validation halves partition each outer training set.",
                           "buffer":"same 1 neighboring 3 km block ring removed from training; min block gap 3km",
                           "population_nodata":"excluded as a mask; never used as a feature",
             "sampling":"all positive training cells plus 3:1 block-stratified negatives; only on training indices; evaluation uses all eligible test cells at their true prevalence",
                           "imputation_scaling":"per estimator fit on its sampled training rows only",
                           "calibration":"Platt calibration fit on inner spatial-block OOF predictions only; cross-fitted calibration predictions choose F1 threshold and conformal residual quantile within outer training blocks",
                           "seeds":{"base":SEED,"outer_fold_increment":1,"random_search":SEED+3000},
                           "inner_folds":INNER_FOLDS,"outer_folds":OUTER_FOLDS,"configuration_count_per_tree_family":config_count},
             "metrics":{},"fold_metrics":{},"paired_fold_differences":{},"label_bias":{},"tuning":{},"importance":{},"error_analysis":{},"limitations":[]}

    # U1 calibrated score baselines. Each feature's logistic coefficient learns orientation only in training.
    baseline_fold_results={}
    pred_store={}
    baseline_names=list(SINGLE_BASELINES)
    for name,features in SINGLE_BASELINES.items():
        arr=make_matrix(table,features)
        ofold=[]; oof_p=np.full(len(y),np.nan,dtype=np.float32)
        for spec in outer:
            tr,te=spec["train"],spec["test"]
            result=evaluate_outer("logistic",{},arr,y,groups,tr,te,positions,SEED+spec["fold"]*100+len(ofold))
            ofold.append(result["metrics"]);oof_p[te]=result["probability"]
        print(f"baseline {name}: completed {OUTER_FOLDS} outer folds",flush=True)
        baseline_fold_results[name]=ofold;pred_store[name]=oof_p
    # Prevalence-only random ranking baseline: train-prevalence calibrated, no discrimination.
    random_folds=[];random_oof=np.full(len(y),np.nan,dtype=np.float32)
    for spec in outer:
        tr,te=spec["train"],spec["test"]
        p=np.full(len(te),float(y[tr].mean()),dtype=np.float32)
        # ROC convention for a non-discriminating constant score is 0.5; AP equals true prevalence.
        m=metric_bundle(y[te],p,0.5,float(y[tr].mean()))
        m["roc_auc"]=0.5;m["baseline_definition"]="constant training-fold prevalence; no ranking information"
        random_folds.append(m);random_oof[te]=p
    baseline_fold_results["random_prevalence"] = random_folds;pred_store["random_prevalence"]=random_oof
    metrics["metrics"]["U1_fair_baselines"]={name:{"fold_mean_sd":summarize_folds(folds,["roc_auc","pr_auc","f1","iou","brier","calibration"] if False else ["roc_auc","pr_auc","f1","iou","brier"]),
                                                "pooled":metric_bundle(y[idx],pred_store[name][idx],0.5,yprev)}
                                                 for name,folds in baseline_fold_results.items()}
    metrics["fold_metrics"]["U1_fair_baselines"]=baseline_fold_results

    # U3 feature ablation and dense-urban sensitivity using default RF.
    ablation={};ablation_folds={}
    for set_name,arr in xsets.items():
        ofold=[];oof_p=np.full(len(y),np.nan,dtype=np.float32)
        for spec in outer:
            res=evaluate_outer("random_forest",MODEL_DEFAULTS["random_forest"],arr,y,groups,
                               spec["train"],spec["test"],positions,SEED+spec["fold"]*10+len(ofold)+400)
            ofold.append(res["metrics"]);oof_p[spec["test"]]=res["probability"]
        print(f"ablation {set_name}: completed {OUTER_FOLDS} outer folds",flush=True)
        ablation[set_name]={"fold_mean_sd":summarize_folds(ofold,["roc_auc","pr_auc","f1","iou","brier"]),
                            "pooled":metric_bundle(y[idx],oof_p[idx],float(np.median([m["threshold"] for m in ofold])),yprev)}
        ablation_folds[set_name]=ofold;pred_store["ablation_"+set_name]=oof_p
    dense_cut=0.5
    dense=table["built_up_fraction"].to_numpy(dtype=float)<=dense_cut
    dense_idx=np.flatnonzero(eligible & dense)
    dense_folds=[];dense_oof=np.full(len(y),np.nan,dtype=np.float32)
    for spec in outer:
        tr=spec["train"][dense[spec["train"]]];te=spec["test"][dense[spec["test"]]]
        res=evaluate_outer("random_forest",MODEL_DEFAULTS["random_forest"],xfull,y,groups,tr,te,positions,
                           SEED+spec["fold"]*10+700)
        dense_folds.append(res["metrics"]);dense_oof[te]=res["probability"]
    metrics["label_bias"]={"flood_fraction_by_built_up_bin":{},"feature_set_results":ablation,
                           "dense_urban_exclusion":{"cutoff":"built_up_fraction > 0.50 excluded from both training and evaluation",
                             "cells":int(len(dense_idx)),"positives":int(y[dense_idx].sum()),"prevalence":float(y[dense_idx].mean()),
                             "fold_mean_sd":summarize_folds(dense_folds,["roc_auc","pr_auc","f1","iou","brier"]),
                             "pooled":metric_bundle(y[dense_idx],dense_oof[dense_idx],float(np.median([m["threshold"] for m in dense_folds])),float(y[dense_idx].mean()))}}
    bu=table["built_up_fraction"].to_numpy(dtype=np.float64)
    for label,lo,hi in (("0_to_0.1",0,.1),("0.1_to_0.3",.1,.3),("0.3_to_0.5",.3,.5),("0.5_to_0.75",.5,.75),("0.75_to_1",.75,1.000001)):
        m=eligible & np.isfinite(bu) & (bu>=lo) & (bu<hi)
        metrics["label_bias"]["flood_fraction_by_built_up_bin"][label]={"cells":int(m.sum()),"flooded":int(y[m].sum()),"fraction":float(y[m].mean()) if m.any() else None}
    metrics["fold_metrics"]["U3_feature_ablation"]=ablation_folds
    metrics["fold_metrics"]["U3_dense_urban_excluded"]=dense_folds
    a_pr=ablation["A_terrain_hydrology"]["fold_mean_sd"]["pr_auc"]["mean"]
    b_pr=ablation["B_terrain_plus_landcover"]["fold_mean_sd"]["pr_auc"]["mean"]
    c_pr=ablation["C_all_pilot_features"]["fold_mean_sd"]["pr_auc"]["mean"]
    dense_pr=metrics["label_bias"]["dense_urban_exclusion"]["fold_mean_sd"]["pr_auc"]["mean"]
    metrics["label_bias"]["interpretation"]={
        "A_to_B_pr_auc_change":float(b_pr-a_pr),"B_to_C_pr_auc_change":float(c_pr-b_pr),
        "C_full_to_dense_excluded_pr_auc_change":float(dense_pr-c_pr),
        "plain_language":("Adding land cover increased mean PR-AUC; adding road/building/population proxies increased it further. " if b_pr>a_pr and c_pr>b_pr else
                          "The ablations do not show a monotonic PR-AUC gain from adding land cover and then road/building/population proxies. ")+
                         ("Most full-feature skill remains after dense-urban exclusion." if dense_pr>=c_pr-0.01 else
                          "The dense-urban-excluded score falls by more than 0.01 PR-AUC, so some apparent skill is associated with dense-urban cells."),
        "caution":"Ablation differences are descriptive paired spatial-CV results, not causal attribution; built-up, roads and population can encode exposure or label-mapping bias."}

    # U4 default versus nested random search for the three tree families.
    family_results={}; family_folds={}; family_raw={}; family_thresholds={}; family_intervals={}; family_inner_cal={}
    tuning_details={}
    for kind in ("random_forest","xgboost","lightgbm"):
        print(f"starting default and nested search for {kind}",flush=True)
        default_folds=[];tuned_folds=[];default_oof=np.full(len(y),np.nan,dtype=np.float32);tuned_oof=np.full(len(y),np.nan,dtype=np.float32)
        raw_oof=np.full(len(y),np.nan,dtype=np.float32);thresholds=[];intervals=[];selected_params=[];search_records=[];importance_by_fold=[]
        for spec in outer:
            fold=spec["fold"]; tr,te=spec["train"],spec["test"]
            dres=evaluate_outer(kind,MODEL_DEFAULTS[kind],xfull,y,groups,tr,te,positions,SEED+fold*1000+801)
            default_folds.append(dres["metrics"]);default_oof[te]=dres["probability"]
            params,search=tune_nested(kind,xfull,y,groups,tr,positions,SEED+fold*100+999,config_count)
            selected_params.append(params); search_records.append({"outer_fold":fold,"selected":params,"configs":search})
            tres=evaluate_outer(kind,params,xfull,y,groups,tr,te,positions,SEED+fold*1000+901)
            tuned_folds.append(tres["metrics"]);tuned_oof[te]=tres["probability"];raw_oof[te]=tres["raw_probability"]
            thresholds.append(tres["threshold"]);intervals.append(tres["metrics"]["interval_90"])
            family_inner_cal.setdefault(kind,[]).append({"indices":tres["train_calibration_indices"],
                "probability":tres["train_calibration_probability"],"y":tres["train_calibration_y"],
                "groups":tres["train_calibration_groups"],"q90":tres["train_calibration_q90"]})
            # Held-out permutation importance on a bounded true-prevalence sample.
            rng=np.random.default_rng(SEED+fold*5000)
            sample=rng.choice(te,size=min(3000,len(te)),replace=False)
            sampled,_=sample_train(tr,y,groups,SEED+fold*5000+1)
            mdl=fit_estimator(kind,params,xfull[sampled],y[sampled],SEED+fold*5000+2)
            base_ap=average_precision_score(y[sample],mdl.predict_proba(xfull[sample])[:,1])
            imp=[]
            for j,feat in enumerate(FEATURE_SETS["C_all_pilot_features"]):
                xp=xfull[sample].copy();np.random.default_rng(SEED+fold*300+j).shuffle(xp[:,j])
                drop=float(base_ap-average_precision_score(y[sample],mdl.predict_proba(xp)[:,1]))
                imp.append({"feature":feat,"pr_auc_drop":drop})
            importance_by_fold.append(imp)
            print(f"{kind}: completed outer fold {fold}/{OUTER_FOLDS}",flush=True)
        default_pooled=metric_bundle(y[idx],default_oof[idx],float(np.mean([m["threshold"] for m in default_folds])),yprev)
        tuned_pooled=metric_bundle(y[idx],tuned_oof[idx],float(np.mean(thresholds)),yprev)
        tuned_pooled["block_bootstrap_pr_auc_ci_95"]=block_bootstrap_ap(y[idx],tuned_oof[idx],groups[idx],SEED+77,bootstrap_reps)
        default_summary=summarize_folds(default_folds,["roc_auc","pr_auc","f1","iou","brier"])
        tuned_summary=summarize_folds(tuned_folds,["roc_auc","pr_auc","f1","iou","brier"])
        family_results[kind]={"default":{"parameters":MODEL_DEFAULTS[kind],"fold_mean_sd":default_summary,"pooled":default_pooled,
                                          "fold_metrics":default_folds},
                              "tuned":{"parameters_by_outer_fold":selected_params,"fold_mean_sd":tuned_summary,"pooled":tuned_pooled,
                                       "topk_by_fold":[topk_metrics(y[spec["test"]],tuned_oof[spec["test"]]) for spec in outer],
                                       "gain_curve_pooled":topk_metrics(y[idx],tuned_oof[idx]),
                                       "interval_90_by_fold":intervals}}
        family_folds[kind]=tuned_folds;family_raw[kind]=raw_oof;family_thresholds[kind]=thresholds;family_intervals[kind]=intervals
        tuning_details[kind]={"search_strategy":"30 fixed-seed random configurations per outer fold; 2 inner buffered GroupKFold folds; ranking objective average precision on full-prevalence inner validation blocks",
                              "outer_folds":search_records}
        # Importance summarized as paired held-out AP drops (raw predictions are uncalibrated only for importance scoring).
        imp_summary={}
        for feat in FEATURE_SETS["C_all_pilot_features"]:
            vals=[r[i]["pr_auc_drop"] for r in importance_by_fold for i,f in enumerate(FEATURE_SETS["C_all_pilot_features"]) if f==feat]
            imp_summary[feat]={"mean_pr_auc_drop":float(np.mean(vals)),"sd_across_outer_folds":float(np.std(vals,ddof=1)) if len(vals)>1 else 0.0}
        family_results[kind]["tuned"]["permutation_importance"]=imp_summary
        pred_store["default_"+kind]=default_oof;pred_store["tuned_"+kind]=tuned_oof
    # Simple average of calibrated tuned-tree OOF probabilities.
    ensemble_oof=np.mean(np.vstack([pred_store["tuned_"+k][idx] for k in ("random_forest","xgboost","lightgbm")]),axis=0).astype(np.float32)
    ensemble_fold=[]
    ensemble_inner_cal=[]
    for fold_i,spec in enumerate(outer):
        te=spec["test"]
        model_cal=[family_inner_cal[k][fold_i] for k in ("random_forest","xgboost","lightgbm")]
        cal_idx=model_cal[0]["indices"]
        if any(not np.array_equal(cal_idx,r["indices"]) for r in model_cal[1:]):
            raise ValueError("Tuned tree models produced different inner calibration rows; ensemble threshold would not be paired")
        cal_p=np.mean(np.vstack([r["probability"] for r in model_cal]),axis=0)
        cal_y=model_cal[0]["y"]
        threshold=select_f1_threshold(cal_y,cal_p)
        q=float(np.quantile(np.abs(cal_y-cal_p),.90,method="higher"))
        ensemble_inner_cal.append({"indices":cal_idx,"probability":cal_p,"y":cal_y,"q90":q})
        ensemble_fold.append(metric_bundle(y[te],ensemble_oof[np.isin(idx,te)],threshold,float(y[spec["train"]].mean()),q))
    ensemble_pooled=metric_bundle(y[idx],ensemble_oof,float(np.mean([m["threshold"] for m in ensemble_fold])),yprev)
    ensemble_pooled["block_bootstrap_pr_auc_ci_95"]=block_bootstrap_ap(y[idx],ensemble_oof,groups[idx],SEED+78,bootstrap_reps)
    family_results["simple_average_tuned_tree_ensemble"]={"default":"unweighted average of calibrated tuned RF, XGBoost and LightGBM outer-fold probabilities",
        "fold_mean_sd":summarize_folds(ensemble_fold,["roc_auc","pr_auc","f1","iou","brier"]),"pooled":ensemble_pooled,
        "gain_curve_pooled":topk_metrics(y[idx],ensemble_oof)}
    family_folds["simple_average_tuned_tree_ensemble"]=ensemble_fold;pred_store["simple_average_tuned_tree_ensemble"]=np.full(len(y),np.nan,dtype=np.float32);pred_store["simple_average_tuned_tree_ensemble"][idx]=ensemble_oof
    metrics["metrics"]["U4_default_tuned_and_ensemble"]=family_results
    metrics["fold_metrics"]["U4_tuned_models"]=family_folds
    metrics["tuning"]=tuning_details
    # Paired fold comparisons against every calibrated baseline and against default settings.
    paired={}
    base_refs={**baseline_fold_results,"A_terrain_hydrology_default_RF":ablation_folds["A_terrain_hydrology"],
               "B_terrain_plus_landcover_default_RF":ablation_folds["B_terrain_plus_landcover"],
               "C_all_features_default_RF":ablation_folds["C_all_pilot_features"]}
    for kind in ("random_forest","xgboost","lightgbm","simple_average_tuned_tree_ensemble"):
        model_fold=family_folds[kind]
        for ref,ref_folds in base_refs.items():
            paired[f"{kind}_minus_{ref}"]=paired_fold_differences({kind:model_fold,ref:ref_folds},ref,["pr_auc","roc_auc","f1","iou","brier"])[kind]
        if kind in ("random_forest","xgboost","lightgbm"):
            default_fold=family_results[kind]["default"]["fold_metrics"]
            paired[f"{kind}_tuned_vs_default"]=paired_fold_differences({"tuned":family_folds[kind],"default":default_fold},"default",["pr_auc","roc_auc","f1","iou","brier"])["tuned"]
    metrics["paired_fold_differences"]=paired

    # Choose by mean fold PR-AUC; within one SD of the best, prefer the simple calibrated ensemble.
    candidates={k:(family_results[k]["fold_mean_sd"]["pr_auc"]["mean"] if k=="simple_average_tuned_tree_ensemble"
                   else family_results[k]["tuned"]["fold_mean_sd"]["pr_auc"]["mean"]) for k in
                ("random_forest","xgboost","lightgbm","simple_average_tuned_tree_ensemble")}
    best=max(candidates,key=candidates.get)
    best_mean=candidates[best]
    best_sd=((family_results[best]["fold_mean_sd"]["pr_auc"]["sd"] if best=="simple_average_tuned_tree_ensemble"
              else family_results[best]["tuned"]["fold_mean_sd"]["pr_auc"]["sd"]) or 0)
    chosen="simple_average_tuned_tree_ensemble" if candidates["simple_average_tuned_tree_ensemble"] is not None and candidates["simple_average_tuned_tree_ensemble"] >= best_mean-best_sd else best
    metrics["chosen_model"]={"name":chosen,"selection":"highest mean outer-fold PR-AUC; if the simple ensemble is within one SD of the best, choose the ensemble for stability; no out-of-event evidence supports a deployment claim","fold_mean_pr_auc":candidates}

    # U5 threshold/gain and top-k metrics for chosen OOF model.
    chosen_oof=(ensemble_oof if chosen=="simple_average_tuned_tree_ensemble"
                else pred_store["tuned_"+chosen][idx])
    metrics["decision_metrics"]={"chosen_model_topk_pooled":topk_metrics(y[idx],chosen_oof),
        "thresholds_by_fold":family_thresholds if chosen!="simple_average_tuned_tree_ensemble" else [m["threshold"] for m in ensemble_fold],
        "calibration_note":"Platt calibration and F1 threshold are learned only from inner spatial-block OOF predictions in each outer training set; reported outer metrics use held-out blocks.",
        "gain_curve_definition":"precision, recall and gain over prevalence in the top-ranked fraction of the held-out or pooled OOF cells"}

    # U7 residual/error maps, spatial error summaries and descriptive Moran's I.
    chosen_all=np.full(len(y),np.nan,dtype=np.float32);chosen_all[idx]=chosen_oof
    residual=np.full(len(y),np.nan,dtype=np.float32);residual[idx]=chosen_oof-y[idx]
    median_threshold=float(np.median([m["threshold"] for m in ensemble_fold])) if chosen=="simple_average_tuned_tree_ensemble" else float(np.median(family_thresholds[chosen]))
    errclass=np.full(len(y),255,dtype=np.uint8)
    errclass[idx]=0;errclass[idx[(chosen_oof>=median_threshold)&(y[idx]==0)]]=1;errclass[idx[(chosen_oof<median_threshold)&(y[idx]==1)]]=2
    with rasterio.open(GRID) as ds:
        grid_meta={"height":ds.height,"width":ds.width,"crs":ds.crs,"transform":ds.transform}
    OUT_DIR.mkdir(parents=True,exist_ok=True)
    write_raster(OUT_DIR/"oof_residual.tif",residual[idx],rows_all[idx],cols_all[idx],grid_meta,"OOF probability minus unchanged Phase 9 label")
    write_raster(OUT_DIR/"oof_error_class.tif",errclass[idx],rows_all[idx],cols_all[idx],grid_meta,"0 correct, 1 false positive, 2 false negative",dtype="uint8")
    moran=morans_i_4_neighbor(residual,eligible,rows_all,cols_all,(grid_meta["height"],grid_meta["width"]))
    block_rows=[]
    for g in np.unique(groups[idx]):
        m=idx[groups[idx]==g];p=chosen_all[m];yy=y[m];pred=p>=median_threshold
        block_rows.append({"block_id":int(g),"cells":int(len(m),),"prevalence":float(yy.mean()),
                           "pr_auc":float(average_precision_score(yy,p)) if yy.sum() else None,
                           "false_negative_rate":float(np.sum((yy==1)&~pred)/max(np.sum(yy==1),1)),
                           "false_positive_rate":float(np.sum((yy==0)&pred)/max(np.sum(yy==0),1))})
    block_rows=sorted(block_rows,key=lambda r:(r["false_negative_rate"] or 0),reverse=True)
    built=table["built_up_fraction"].to_numpy(dtype=float)
    distcoast=table["distance_to_coast_or_sea_m"].to_numpy(dtype=float)
    errors_by_urban={}
    for name,lo,hi in (("0_to_0.1",0,.1),("0.1_to_0.3",.1,.3),("0.3_to_0.5",.3,.5),("0.5_to_1",.5,1.00001)):
        m=eligible&(built>=lo)&(built<hi);ii=np.flatnonzero(m);pr=chosen_all[ii]>=median_threshold
        errors_by_urban[name]={"cells":int(len(ii)),"flooded_fraction":float(y[ii].mean()) if len(ii) else None,
            "false_negative_rate":float(np.sum((y[ii]==1)&~pr)/max(np.sum(y[ii]==1),1)),
            "false_positive_rate":float(np.sum((y[ii]==0)&pr)/max(np.sum(y[ii]==0),1))}
    coast_bins={}
    finite_coast=eligible&np.isfinite(distcoast)
    if finite_coast.any():
        qs=np.quantile(distcoast[finite_coast],[0,.2,.4,.6,.8,1])
        for i in range(5):
            m=finite_coast&(distcoast>=qs[i])&(distcoast<=(qs[i+1] if i==4 else np.nextafter(qs[i+1],-np.inf)))
            ii=np.flatnonzero(m);pr=chosen_all[ii]>=median_threshold
            coast_bins[f"q{i+1}"]={"distance_range_m":[float(qs[i]),float(qs[i+1])],"cells":int(len(ii)),
                "false_negative_rate":float(np.sum((y[ii]==1)&~pr)/max(np.sum(y[ii]==1),1)) if y[ii].sum() else None,
                "false_positive_rate":float(np.sum((y[ii]==0)&pr)/max(np.sum(y[ii]==0),1))}
    metrics["error_analysis"]={"moran":moran,"urban_error_rates":errors_by_urban,"coast_distance_error_rates":coast_bins,
        "highest_false_negative_blocks":block_rows[:10],"highest_false_positive_blocks":sorted(block_rows,key=lambda r:r["false_positive_rate"],reverse=True)[:10],
        "error_classes":{"0":"correct at pooled median outer threshold","1":"false positive","2":"false negative","255":"NoData / excluded"}}

    # Permutation importance for chosen estimator (ensemble uses mean of the three model rankings).
    if chosen=="simple_average_tuned_tree_ensemble":
        imp_by_model={k:family_results[k]["tuned"]["permutation_importance"] for k in ("random_forest","xgboost","lightgbm")}
        imp={f:{"mean_pr_auc_drop":float(np.mean([imp_by_model[k][f]["mean_pr_auc_drop"] for k in imp_by_model])),
                "sd_across_models":float(np.std([imp_by_model[k][f]["mean_pr_auc_drop"] for k in imp_by_model]))} for f in FEATURE_SETS["C_all_pilot_features"]}
    else:
        imp=family_results[chosen]["tuned"]["permutation_importance"]
    metrics["importance"]={"method":"Held-out outer-fold permutation, average precision decrease, up to 3,000 true-prevalence cells per fold, one permutation per feature per fold.",
                            "chosen_model":chosen,"features":imp,
                            "physical_review":"Check whether terrain/hydrology features rank ahead of urban, road and population proxies; prominence of exposure/access variables may reflect mapping/source bias, not flood physics."}
    top_importance=sorted(imp.items(),key=lambda kv:kv[1]["mean_pr_auc_drop"],reverse=True)[:10]
    exposure_features=set(LANDCOVER_FEATURES+EXTRA_FEATURES)
    exposure_top=[name for name,_ in top_importance if name in exposure_features]
    metrics["importance"]["top_ten_features"]=[{"feature":name,**value} for name,value in top_importance]
    metrics["importance"]["physical_sanity_result"]={
        "exposure_or_access_features_in_top_ten":exposure_top,
        "flag":"Exposure/access proxy is among the strongest ten features; treat apparent predictive skill cautiously." if exposure_top else
               "No built-up, road, building-density, or population proxy appears in the top ten; this is only a ranking check, not physical validation.",
        "terrain_features_in_top_ten":[name for name,_ in top_importance if name in TERRAIN_FEATURES]}

    # U6 empirical outer-fold interval coverage and apparent full-data map intervals.
    if chosen=="simple_average_tuned_tree_ensemble":
        qvals=[r["q90"] for r in ensemble_inner_cal]
        oof_q=float(np.median(qvals))
        oof_cov=float(np.mean([r["interval_90"]["coverage"] for r in ensemble_fold]))
        oof_width=float(np.mean([r["interval_90"]["mean_width"] for r in ensemble_fold]))
    else:
        oof_q=float(np.median([m["interval_90"]["q_abs_residual"] for m in family_folds[chosen]]))
        oof_cov=float(np.mean([m["interval_90"]["coverage"] for m in family_folds[chosen]]))
        oof_width=float(np.mean([m["interval_90"]["mean_width"] for m in family_folds[chosen]]))
    metrics["uncertainty"]={"method":"90% split-conformalized absolute-error band using cross-fitted Platt probabilities from inner buffered training blocks; outer test blocks assess empirical coverage.",
        "nominal_coverage":0.90,"outer_fold_mean_coverage":oof_cov,"outer_fold_mean_width_probability_units":oof_width,
        "pooled_oof_residual_quantile":oof_q,"under_covers":bool(oof_cov<.90),
        "caveat":"Spatial autocorrelation weakens exchangeability assumptions. The band is for the binary label probability response, not water-depth uncertainty."}

    # U8: query only the approved label view and keep the DB transaction read-only.
    try:
        from sqlalchemy import text
        from pipelines.stage5.db_common import make_engine
        db_engine=make_engine()
        with db_engine.connect() as conn:
            conn.exec_driver_sql("SET TRANSACTION READ ONLY")
            accepted=conn.execute(text("SELECT event_date, reference_role, tier, count(*) AS feature_count "
                "FROM labels.v_usable_flood_labels GROUP BY event_date, reference_role, tier "
                "ORDER BY event_date, reference_role, tier")).all()
        accepted_rows=[{"event_date":str(r.event_date),"role":r.reference_role,"tier":r.tier,
                        "feature_count":int(r.feature_count)} for r in accepted]
        other_events=[r for r in accepted_rows if r["role"]=="event_flood" and r["event_date"] not in ("2015-11-12","2015-11-24")]
        metrics["out_of_event"]={"status":"available" if other_events else "pending",
            "reason":None if other_events else "Only accepted A/B/C event layers are the two November 2015 dates used in the Phase 9 target; baseline-water dates are not event holdouts.",
            "accepted_view_summary":accepted_rows,"independent_event_dates":sorted({r["event_date"] for r in other_events}),
            "evaluation":"not run; no independent accepted event/date label exists" if not other_events else "requires a separate out-of-event evaluation design"}
        db_engine.dispose()
    except Exception as exc:
        metrics["out_of_event"]={"status":"pending","reason":"Could not inspect accepted labels view; " + type(exc).__name__,
                                  "error_detail_omitted":True}
    metrics["runtime_seconds_before_full_map"]=float(time.perf_counter()-start)
    metrics["limitations"]=["Single 2015 event target; no out-of-event performance claim.",
        "Target is official SAR-derived extent, not field-validated and does not represent the Dec 1–8 peak.",
        "Population-NoData cells are excluded as a mask; the model's evaluation denominator is therefore smaller than Phase 9.",
        "New drainage and water distance features inherit DSM, OSM incompleteness, D8 sinks and WorldCover 2021 source limitations.",
        "Nested tuning/calibration and maps are a pilot; full-data maps are apparent, not independent validation."]

    # Apparent maps: refit selected outer-fold parameter medians/modes on all eligible rows.
    # The full-data calibration is fit on outer OOF raw predictions; maps are explicitly apparent.
    chosen_kinds=("random_forest","xgboost","lightgbm") if chosen=="simple_average_tuned_tree_ensemble" else (chosen,)
    full_predictions=[];full_model_params={};global_q=oof_q
    for kind in chosen_kinds:
        if kind=="simple_average_tuned_tree_ensemble":
            continue
        paramslist=[r["selected"] for r in tuning_details[kind]["outer_folds"]]
        keys=[json.dumps(p,sort_keys=True) for p in paramslist]
        params=json.loads(Counter(keys).most_common(1)[0][0])
        full_model_params[kind]=params
        # OOF calibration source is out-of-block and does not alter the label.
        cal=fit_platt(family_raw[kind][idx],y[idx])
        all_sample,sample_info=sample_train(idx,y,groups,SEED+8800,MAX_TRAIN_POSITIVES)
        model=fit_estimator(kind,params,xfull[all_sample],y[all_sample],SEED+8800)
        p=np.empty(len(idx),dtype=np.float32)
        chunk=50000
        for s in range(0,len(idx),chunk):
            ii=idx[s:s+chunk]
            raw=raw_prior_adjust(model.predict_proba(xfull[ii])[:,1],float(y[all_sample].mean()),float(y[idx].mean()))
            p[s:s+len(ii)]=apply_platt(cal,raw).astype(np.float32)
        full_predictions.append(p)
    full_mean=np.mean(np.vstack(full_predictions),axis=0).astype(np.float32)
    write_raster(OUT_DIR/"probability_mean_apparent.tif",full_mean,rows_all[idx],cols_all[idx],grid_meta,"APPARENT full-data calibrated susceptibility probability")
    write_raster(OUT_DIR/"interval_lower90_apparent.tif",np.maximum(0,full_mean-global_q),rows_all[idx],cols_all[idx],grid_meta,"APPARENT conformal lower 90% prediction bound")
    write_raster(OUT_DIR/"interval_upper90_apparent.tif",np.minimum(1,full_mean+global_q),rows_all[idx],cols_all[idx],grid_meta,"APPARENT conformal upper 90% prediction bound")

    # Static figures.
    FIG_DIR.mkdir(parents=True,exist_ok=True)
    fig,ax=plt.subplots(figsize=(7,5),constrained_layout=True)
    for name,top in ((k,topk_metrics(y[idx],pred_store["tuned_"+k][idx] if k!="simple_average_tuned_tree_ensemble" else pred_store[k][idx]))
                     for k in ("random_forest","xgboost","lightgbm","simple_average_tuned_tree_ensemble")):
        points=sorted([(int(k),v["recall"]) for k,v in top.items()])
        ax.plot([x for x,_ in points],[v for _,v in points],marker="o",label=name.replace("_"," "))
    ax.plot([1,2,5,10,20,50,100],[.01,.02,.05,.1,.2,.5,1],"--",label="random gain")
    ax.set(xlabel="Top ranked cells (%)",ylabel="Cumulative recall",title="Phase 9B outer OOF gain curve");ax.grid(alpha=.25);ax.legend(fontsize=7)
    fig.savefig(FIG_DIR/"phase9b_gain_curve.png",dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,6),constrained_layout=True)
    errgrid=np.full((grid_meta["height"],grid_meta["width"]),np.nan,dtype=np.float32);errgrid[rows_all[idx],cols_all[idx]]=errclass[idx]
    ax.imshow(errgrid,vmin=0,vmax=2,cmap=matplotlib.colors.ListedColormap(["#c8e6c9","#ffcc80","#ef9a9a"]),interpolation="nearest")
    ax.set(title="Phase 9B OOF error class (0 correct, 1 FP, 2 FN)",xlabel="Grid column",ylabel="Grid row")
    fig.savefig(FIG_DIR/"phase9b_error_map.png",dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(6,6),constrained_layout=True);ax.plot([0,1],[0,1],"--",color="gray")
    bins=calibration_bins(y[idx],chosen_oof)["bins"]
    ax.plot([b["mean_probability"] for b in bins],[b["observed_fraction"] for b in bins],marker="o")
    ax.set(xlabel="Mean predicted probability",ylabel="Observed fraction",title="Phase 9B OOF reliability");ax.grid(alpha=.25)
    fig.savefig(FIG_DIR/"phase9b_reliability.png",dpi=160);plt.close(fig)
    imp_items=sorted(imp.items(),key=lambda kv:kv[1]["mean_pr_auc_drop"])
    fig,ax=plt.subplots(figsize=(8,8),constrained_layout=True)
    ax.barh([k for k,_ in imp_items],[v["mean_pr_auc_drop"] for _,v in imp_items])
    ax.set(xlabel="Held-out PR-AUC decrease",title="Phase 9B permutation importance");ax.grid(axis="x",alpha=.25)
    fig.savefig(FIG_DIR/"phase9b_importance.png",dpi=160);plt.close(fig)

    # Save comparison summaries and registry/report.
    # Brier skill, F1 thresholds, top-k precision/recall and calibration are present in metrics JSON.
    metrics["report_paths"]={"oof_residual":"data/features/predictions/phase9b_v2/oof_residual.tif",
                             "error_class":"data/features/predictions/phase9b_v2/oof_error_class.tif",
                             "apparent_maps":[p.relative_to(ROOT).as_posix() for p in outputs[3:6]],
                             "figures":[p.relative_to(ROOT).as_posix() for p in outputs[8:12]]}
    registry={"registry_version":1,"status":"PILOT SINGLE EVENT; APPARENT FULL-DATA MAPS",
        "chosen_model":chosen,"seed":SEED,"reproducible_command":".venv\\Scripts\\python.exe pipelines\\phase9b\\model_upgrade.py --configs 30 --bootstrap-reps 200",
        "feature_table_sha256":metrics["data"]["feature_table_sha256"],"pilot_label_table_sha256":metrics["data"]["pilot_label_table_sha256"],
        "target":"unchanged target_union_minus_baseline from Phase 9 label Parquet",
        "outer_folds":OUTER_FOLDS,"buffer_radius_3km_blocks":BLOCK_BUFFER_RADIUS,
        "inner_split_method":"two contiguous block-row halves, balanced by cell count, with the same one-block training buffer",
        "sampling":"all positive cells plus 3:1 sampled negatives, stratified by block, all fitted within training fold",
        "models":{k:{"default_parameters":MODEL_DEFAULTS[k],"tuned_parameters_by_fold":[r["selected"] for r in tuning_details[k]["outer_folds"]],
                     "outer_fold_mean_pr_auc":family_results[k]["tuned"]["fold_mean_sd"]["pr_auc"]["mean"],
                     "outer_fold_sd_pr_auc":family_results[k]["tuned"]["fold_mean_sd"]["pr_auc"]["sd"]} for k in ("random_forest","xgboost","lightgbm")},
        "chosen_oof_metrics":(family_results[chosen]["pooled"] if chosen=="simple_average_tuned_tree_ensemble" else family_results[chosen]["tuned"]["pooled"]),
        "paired_fold_differences":paired,"uncertainty":metrics["uncertainty"],
        "full_data_map_parameters":full_model_params,"metrics_file":METRICS_OUT.relative_to(ROOT).as_posix(),
        "limitations":["single 2015 event", "not forecast or field accuracy", "apparent maps", "out-of-event validation pending"]}
    metrics["runtime_seconds_total"]=float(time.perf_counter()-start)
    METRICS_OUT.write_text(json.dumps(metrics,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    REGISTRY_OUT.write_text(json.dumps(registry,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    report=["# Phase 9B model upgrade", "", "> **PILOT, SINGLE EVENT.** Labels are unchanged from the official SAR-derived November 2015 Phase 9 target. This is not field validation and not a time-varying flood forecast.",
        "", "## Data and split", "", f"Phase 9 eligible cells: {pilot_eligible.sum():,}; positives: {y[pilot_eligible].sum():,}; prevalence: {y[pilot_eligible].mean():.4%}.",
        f"For Phase 9B, population-NoData is used only as an eligibility mask: {metrics['data']['model_cells']:,} cells remain ({metrics['data']['model_positives']:,} flooded; {yprev:.4%}). NoData flag is not a predictor.",
        "The five outer folds were reconstructed using the same deterministic GroupKFold algorithm and spatial buffer as the Phase 9 pilot; test-cell counts and prevalences match its metrics. The saved Phase 9 test_block_ids repeat the final fold across all five records due to a bookkeeping defect, so those IDs were not used; the reconstructed block folds are checked for disjointness and complete partitioning. Inner tuning and calibration use two contiguous block-row halves, balanced by cell count, with the same one-block training buffer. Sampling, imputation, scaling, Platt calibration and F1 threshold selection use training blocks only. Outer test blocks remain at observed prevalence.",
        "", "## Fair baselines and paired fold comparison", "", "Baselines use train-oriented logistic scores with Platt calibration: elevation, river distance, TWI, slope, 15-cell relative elevation, HAND, and a small terrain logistic model. The random baseline is constant training-fold prevalence (no ranking signal).",
        "", "| Baseline | ROC-AUC mean ± SD | PR-AUC mean ± SD | Brier mean ± SD |", "|---|---:|---:|---:|"]
    for name,b in metrics["metrics"]["U1_fair_baselines"].items():
        s=b["fold_mean_sd"];report.append(f"| {name} | {s['roc_auc']['mean']:.4f} ± {s['roc_auc']['sd']:.4f} | {s['pr_auc']['mean']:.4f} ± {s['pr_auc']['sd']:.4f} | {s['brier']['mean']:.4f} ± {s['brier']['sd']:.4f} |")
    report += ["", "## Feature ablation and label-bias check", "", "| Feature set / test | ROC-AUC mean ± SD | PR-AUC mean ± SD | Brier mean ± SD |", "|---|---:|---:|---:|"]
    for name,v in metrics["label_bias"]["feature_set_results"].items():
        s=v["fold_mean_sd"];report.append(f"| {name} | {s['roc_auc']['mean']:.4f} ± {s['roc_auc']['sd']:.4f} | {s['pr_auc']['mean']:.4f} ± {s['pr_auc']['sd']:.4f} | {s['brier']['mean']:.4f} ± {s['brier']['sd']:.4f} |")
    s=metrics["label_bias"]["dense_urban_exclusion"]["fold_mean_sd"]
    report.append(f"| C, built-up >0.50 removed from train and test | {s['roc_auc']['mean']:.4f} ± {s['roc_auc']['sd']:.4f} | {s['pr_auc']['mean']:.4f} ± {s['pr_auc']['sd']:.4f} | {s['brier']['mean']:.4f} ± {s['brier']['sd']:.4f} |")
    report += ["", "Flood fraction by built-up bin:", "", "| Built-up fraction | Cells | Flooded | Flood fraction |", "|---|---:|---:|---:|"]
    for name,v in metrics["label_bias"]["flood_fraction_by_built_up_bin"].items(): report.append(f"| {name} | {v['cells']:,} | {v['flooded']:,} | {v['fraction']:.4%} |")
    report += ["", metrics["label_bias"]["interpretation"]["plain_language"],
               "Paired fold PR-AUC changes and dense-urban sensitivity are in the metrics JSON; these are associations, not causal effects."]
    report += ["", "## Default, tuned and ensemble models", "", "| Model | PR-AUC mean ± SD | ROC-AUC | F1 | IoU | Brier | ECE | PR-AUC 95% block-bootstrap CI |", "|---|---:|---:|---:|---:|---:|---:|---|"]
    for kind in ("random_forest","xgboost","lightgbm"):
        for variant in ("default","tuned"):
            d=family_results[kind][variant];s=d["fold_mean_sd"];p=d["pooled"]
            ci=p.get("block_bootstrap_pr_auc_ci_95",{}).get("ci_95_percentile","—")
            ece=float(p.get("calibration",{}).get("ece_10_equal_width",0))
            report.append(f"| {kind} {variant} | {s['pr_auc']['mean']:.4f} ± {s['pr_auc']['sd']:.4f} | {p['roc_auc']:.4f} | {p['f1']:.4f} | {p['iou']:.4f} | {p['brier']:.4f} | {ece:.4f} | {ci} |")
    e=family_results["simple_average_tuned_tree_ensemble"];s=e["fold_mean_sd"];p=e["pooled"]
    report.append(f"| simple average tuned tree ensemble | {s['pr_auc']['mean']:.4f} ± {s['pr_auc']['sd']:.4f} | {p['roc_auc']:.4f} | {p['f1']:.4f} | {p['iou']:.4f} | {p['brier']:.4f} | {p['calibration']['ece_10_equal_width']:.4f} | {p['block_bootstrap_pr_auc_ci_95']['ci_95_percentile']} |")
    report += ["", f"Chosen: **{chosen}**. {metrics['chosen_model']['selection']}.",
        "", "Paired fold comparison of the chosen model to the main baselines:", "", "| Comparison | PR-AUC delta mean ± SD (folds won) | Brier delta mean ± SD (folds won) |", "|---|---:|---:|"]
    for ref in ["random_prevalence",*SINGLE_BASELINES.keys(),"A_terrain_hydrology_default_RF","B_terrain_plus_landcover_default_RF","C_all_features_default_RF"]:
        key=f"{chosen}_minus_{ref}"; d=metrics["paired_fold_differences"].get(key)
        if d:
            pr,brier=d["pr_auc"],d["brier"]
            report.append(f"| {ref} | {pr['mean_delta']:.4f} ± {pr['sd_delta']:.4f} ({pr['folds_won']}/{pr['folds_compared']}) | {brier['mean_delta']:.4f} ± {brier['sd_delta']:.4f} ({brier['folds_won']}/{brier['folds_compared']}) |")
    report += ["", "Tuned-minus-default PR-AUC paired deltas: " + "; ".join(
        f"{kind} {metrics['paired_fold_differences'][kind+'_tuned_vs_default']['pr_auc']['mean_delta']:+.4f} ± {metrics['paired_fold_differences'][kind+'_tuned_vs_default']['pr_auc']['sd_delta']:.4f} ({metrics['paired_fold_differences'][kind+'_tuned_vs_default']['pr_auc']['folds_won']}/5 folds won)"
        for kind in ("random_forest","xgboost","lightgbm")) + ".",
        "Full paired fold deltas for ROC-AUC, PR-AUC, F1, IoU and Brier are in `PHASE9B_V2_METRICS.json` under `paired_fold_differences`.",
        "", "## Threshold, ranking and uncertainty", "", f"Chosen OOF top-percentile precision/recall/gain: `{json.dumps(metrics['decision_metrics']['chosen_model_topk_pooled'])}`",
        f"Conformal band outer-fold coverage: {metrics['uncertainty']['outer_fold_mean_coverage']:.3f} (nominal 0.90); mean width {metrics['uncertainty']['outer_fold_mean_width_probability_units']:.3f} probability units; under-covers: {metrics['uncertainty']['under_covers']}. Spatial dependence weakens exchangeability.",
        "", "## Physical sanity, errors and maps", "", f"OOF residual Moran's I (4-neighbor) = {moran['morans_i_4_neighbor']}; no inferential p-value was computed. See error summaries by built-up bin, coast-distance quintile and 3 km blocks in the metrics JSON.",
        f"Physical-feature check: {metrics['importance']['physical_sanity_result']['flag']}",
        "Top permutation features: " + ", ".join(f"{v['feature']} ({v['mean_pr_auc_drop']:.5f})" for v in metrics["importance"]["top_ten_features"]),
        "", "![OOF gain curve](figures/phase9b_v2/phase9b_gain_curve.png)", "", "![OOF error map](figures/phase9b_v2/phase9b_error_map.png)", "", "![OOF reliability](figures/phase9b_v2/phase9b_reliability.png)", "", "![Permutation importance](figures/phase9b_v2/phase9b_importance.png)",
        "", "Full-data rasters are explicitly apparent maps: probability mean and conformal lower/upper bounds. They are not OOF maps.",
        "", "## Out-of-event check", "", "Pending: a read-only check of labels.v_usable_flood_labels found only the two November 2015 event dates used in the Phase 9 target; baseline-water layers are not independent flood events. No out-of-event metric is available.",
        "", "## Leakage review and claims", "", "The Phase 9 target Parquet and split algorithm are reused unchanged. The target count is asserted to remain 61,166 before the population-NoData eligibility mask. Per-fold held-out cell counts and prevalence match Phase 9. Its serialized held-out block-ID lists repeat the final fold because of a bookkeeping defect; Phase 9B reconstructs assignments with the original GroupKFold code and checks held-out groups are disjoint and cover the eligible block set. The one-block spatial buffer is reapplied to training. Hyperparameter search, sampling, missing-value imputation, scaling, Platt calibration, threshold selection and conformal quantile estimation use training blocks only. OOF residuals and all outer metrics are evaluated on held-out blocks at their observed prevalence.",
        "The model can describe spatial association with the November 2015 target under this one event and these inputs. It cannot claim future flood prediction, event transfer, field accuracy, calibrated hydraulic depth, or reliable performance for the December 2015 peak. Built-up, road and population associations may encode exposure and mapping biases rather than flood physics.",
        "", f"Reproducible command: `{registry['reproducible_command']}`. Input hashes and complete fold/model details: `PHASE9B_V2_METRICS.json` and `PHASE9B_V2_MODEL_REGISTRY.json`.", ""]
    REPORT_OUT.write_text("\n".join(report),encoding="utf-8")
    metrics["runtime_seconds_total"]=float(time.perf_counter()-start)
    METRICS_OUT.write_text(json.dumps(metrics,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return metrics


if __name__ == "__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--configs",type=int,default=TUNING_CONFIGS)
    ap.add_argument("--bootstrap-reps",type=int,default=BOOTSTRAP_REPS)
    ap.add_argument("--resume-generated-rasters",action="store_true",
                    help="reuse verified Phase 9B rasters created by an interrupted prior run; never overwrite them")
    args=ap.parse_args()
    if args.configs<1 or args.bootstrap_reps<1: ap.error("configs and bootstrap-reps must be positive")
    result=run(args.configs,args.bootstrap_reps,args.resume_generated_rasters)
    print(json.dumps({"chosen_model":result["chosen_model"],"eligible_cells":result["data"]["model_cells"],
                      "runtime_seconds":result["runtime_seconds_total"]},indent=2))
