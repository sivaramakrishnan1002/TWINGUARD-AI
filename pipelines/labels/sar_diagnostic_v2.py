"""Reproducible SAR-versus-UNOSAT diagnostic; does not create flood labels."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import rowcol
from sklearn.metrics import roc_auc_score
from sklearn.tree import DecisionTreeClassifier


def _read(path: Path) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as ds:
        return ds.read(1), ds.profile.copy()


def run(root: Path) -> dict:
    base = root / "data"
    label_path = base / "processed/labels_inspection/2015-11-24_EXPLORATORY_NOT_FINAL.tif"
    baseline_paths = [base / f"processed/labels_inspection/{d}_EXPLORATORY_NOT_FINAL.tif" for d in ("2015-09-01", "2015-10-14")]
    feature_path = base / "features/static/cell_table_phase9b_v2.parquet"
    sar = base / "processed/sar_work/rtc_aligned"
    label, lp = _read(label_path)
    baselines = [_read(p)[0] for p in baseline_paths]
    df = pd.read_parquet(feature_path, columns=["x", "y", "built_up_fraction_phase9b", "tree_fraction", "crop_fraction", "grass_fraction", "bare_fraction", "water_fraction_phase9b", "hand_d8_accum100_m"])
    # Sample the source rasters by cell centre, respecting their independent transforms.
    with rasterio.open(label_path) as ld:
        lr, lc = rowcol(ld.transform, df.x.to_numpy(), df.y.to_numpy())
    lr, lc = np.asarray(lr), np.asarray(lc)
    inside = (lr >= 0) & (lc >= 0) & (lr < label.shape[0]) & (lc < label.shape[1])
    keep = inside.copy()
    y = np.zeros(len(df), dtype=np.uint8)
    y[inside] = label[lr[inside], lc[inside]]
    # Preserve only observed 0/1 labels and subtract the two reference-water layers and WorldCover water.
    keep &= np.isin(y, [0, 1])
    permanent = np.zeros(len(df), dtype=bool)
    for arr in baselines:
        permanent[inside] |= arr[lr[inside], lc[inside]] > 0
    permanent |= df.water_fraction_phase9b.fillna(0).to_numpy() > 0
    keep &= ~permanent
    cover_cols = ["tree_fraction", "crop_fraction", "grass_fraction", "bare_fraction", "built_up_fraction_phase9b"]
    cover = np.column_stack([df[c].fillna(-1).to_numpy() for c in cover_cols])
    dominant = np.argmax(cover, axis=1).astype(np.int8)
    hand = df.hand_d8_accum100_m.to_numpy()
    hand_bin = np.digitize(np.nan_to_num(hand, nan=-1.0), [2, 5, 10]).astype(np.int8)
    finite_hand = np.isfinite(hand)
    eligible_before_hand = keep & (cover.max(axis=1) >= 0)
    keep = eligible_before_hand & finite_hand
    pos = np.flatnonzero(keep & (y == 1))
    neg = np.flatnonzero(keep & (y == 0))
    # Exact matching strata: dominant land-cover category and HAND interval.
    strata_pos: dict[tuple[int, int], list[int]] = {}
    strata_neg: dict[tuple[int, int], list[int]] = {}
    for idx, dest in ((pos, strata_pos), (neg, strata_neg)):
        for i in idx:
            dest.setdefault((int(dominant[i]), int(hand_bin[i])), []).append(int(i))
    rng = np.random.default_rng(20261025)
    matched_pos, matched_neg = [], []
    unmatched_pos = 0
    for k, vals in strata_pos.items():
        controls = strata_neg.get(k, [])
        if not controls:
            unmatched_pos += len(vals)
            continue
        # Sample both classes without replacement so no pixel can cross folds twice.
        n_match = min(len(vals), len(controls))
        matched_pos.extend(rng.choice(vals, size=n_match, replace=False).tolist())
        matched_neg.extend(rng.choice(controls, size=n_match, replace=False).tolist())
    matched_pos = np.asarray(matched_pos, dtype=int)
    matched_neg = np.asarray(matched_neg, dtype=int)
    if not len(matched_pos):
        raise RuntimeError("No matched positive/non-flooded cells after eligibility and stratification")

    # Crop raster coordinates from label to the larger RTC working grid using world coordinates.
    values: dict[str, np.ndarray] = {}
    raster_profiles: dict[str, dict] = {}
    for name, path in (("vv", sar / "2015-11-24_VV_dB_lee5.tif"), ("vh", sar / "2015-11-24_VH_dB_lee5.tif"), ("vv_ref", sar / "2015-10-19_VV_dB_lee5.tif")):
        with rasterio.open(path) as ds:
            rr, cc = rowcol(ds.transform, df.x.to_numpy(), df.y.to_numpy())
            rr, cc = np.asarray(rr), np.asarray(cc)
            a = ds.read(1)
            valid = (rr >= 0) & (cc >= 0) & (rr < a.shape[0]) & (cc < a.shape[1])
            out = np.full(len(df), np.nan, dtype=np.float32)
            out[valid] = a[rr[valid], cc[valid]]
            out[out == ds.nodata] = np.nan
            values[name] = out
            raster_profiles[name] = {"crs": str(ds.crs), "transform": tuple(ds.transform), "shape": ds.shape, "nodata": ds.nodata}
    # Enforce the event scene's valid-data and layover/shadow masks; no fallback to map-derived labels.
    with rasterio.open(sar / "2015-11-24_valid_layover_shadow_mask.tif") as ds:
        rr, cc = rowcol(ds.transform, df.x.to_numpy(), df.y.to_numpy()); rr, cc = np.asarray(rr), np.asarray(cc); a = ds.read(1)
        valid_geom = (rr >= 0) & (cc >= 0) & (rr < a.shape[0]) & (cc < a.shape[1])
        valid_product = np.zeros(len(df), dtype=bool); valid_product[valid_geom] = a[rr[valid_geom], cc[valid_geom]] != 0
    with rasterio.open(sar / "2015-11-24_layover_shadow_flags.tif") as ds:
        rr, cc = rowcol(ds.transform, df.x.to_numpy(), df.y.to_numpy()); rr, cc = np.asarray(rr), np.asarray(cc); a = ds.read(1)
        valid_flags = (rr >= 0) & (cc >= 0) & (rr < a.shape[0]) & (cc < a.shape[1])
        flags = np.full(len(df), 255, dtype=np.uint8); flags[valid_flags] = a[rr[valid_flags], cc[valid_flags]]
    valid = keep & valid_product & ((flags & (4 | 16)) == 0)
    # Require complete observations for VV, VH and VV dB change.
    valid &= np.isfinite(values["vv"]) & np.isfinite(values["vh"]) & np.isfinite(values["vv_ref"])
    change = values["vv"] - values["vv_ref"]
    feature_arrays = {"VV event dB": values["vv"], "VH event dB": values["vh"], "VV dB change (24 Nov - 19 Oct)": change}
    # rebuild matched sample after scene-validity filtering
    pos = np.flatnonzero(valid & (y == 1)); neg = np.flatnonzero(valid & (y == 0))
    sp, sn = {}, {}
    for idx, dest in ((pos, sp), (neg, sn)):
        for i in idx: dest.setdefault((int(dominant[i]), int(hand_bin[i])), []).append(int(i))
    matched_pos, matched_neg, unmatched_pos = [], [], 0
    for k, vals in sp.items():
        controls = sn.get(k, [])
        if not controls: unmatched_pos += len(vals); continue
        n_match = min(len(vals), len(controls))
        matched_pos.extend(rng.choice(vals, size=n_match, replace=False).tolist())
        matched_neg.extend(rng.choice(controls, size=n_match, replace=False).tolist())
    mp, mn = np.asarray(matched_pos, dtype=int), np.asarray(matched_neg, dtype=int)
    if not len(mp): raise RuntimeError("No valid matched samples after RTC quality masks")
    if len(np.unique(np.r_[mp, mn])) != len(mp) + len(mn):
        raise AssertionError("matched sample contains duplicate cells")
    samples = np.r_[mp, mn]; target = np.r_[np.ones(len(mp), dtype=np.uint8), np.zeros(len(mn), dtype=np.uint8)]
    aucs = {}
    for name, arr in feature_arrays.items():
        raw_auc = float(roc_auc_score(target, arr[samples]))
        aucs[name] = {"raw_auc_flood_higher": raw_auc, "direction_aware_auc": max(raw_auc, 1.0 - raw_auc), "flood_direction": "lower" if raw_auc < 0.5 else "higher"}
    # 3 km block folds using actual projected coordinates, a depth-1 decision stump per variable.
    xy = np.column_stack([df.x.to_numpy()[samples], df.y.to_numpy()[samples]])
    blocks = np.floor(xy / 3000).astype(np.int64)
    keys = blocks[:, 0] * 100000 + blocks[:, 1]
    unique = np.unique(keys)
    fold_ids = np.array_split(unique, min(5, len(unique)))
    stump = {}
    for name, arr in feature_arrays.items():
        fold_aucs = []
        fold_thresholds = []
        z = arr[samples].reshape(-1, 1)
        for fid in fold_ids:
            test = np.isin(keys, fid); train = ~test
            if len(np.unique(target[train])) < 2 or len(np.unique(target[test])) < 2: continue
            model = DecisionTreeClassifier(max_depth=1, random_state=20261025)
            model.fit(z[train], target[train])
            fold_thresholds.append(float(model.tree_.threshold[0]))
            score = model.predict_proba(z[test])[:, 1]
            fold_aucs.append(float(roc_auc_score(target[test], score)))
        stump[name] = {"fold_auc": fold_aucs, "fold_threshold": fold_thresholds, "mean": float(np.mean(fold_aucs)) if fold_aucs else None, "sd": float(np.std(fold_aucs, ddof=1)) if len(fold_aucs)>1 else None}
    # Shift source label by 1–3 cells in all cardinal directions. Metrics are overlap with original extent.
    source_flood = (label == 1)
    shifts = {}
    for dist in (1, 2, 3):
        scores=[]
        for dy, dx in ((dist,0),(-dist,0),(0,dist),(0,-dist)):
            shifted=np.zeros_like(source_flood); y0=max(0,dy); y1=label.shape[0]+min(0,dy); x0=max(0,dx); x1=label.shape[1]+min(0,dx)
            shifted[y0:y1,x0:x1]=source_flood[y0-dy:y1-dy,x0-dx:x1-dx]
            inter=np.count_nonzero(source_flood & shifted); union=np.count_nonzero(source_flood | shifted)
            scores.append(inter/union if union else float("nan"))
        shifts[str(dist)]={"iou_cardinal_mean":float(np.mean(scores)),"iou_cardinal":scores}
    base_counts={}
    for i, arr in enumerate(baselines): base_counts[baseline_paths[i].name] = {str(int(v)):int(c) for v,c in zip(*np.unique(arr, return_counts=True))}
    water_diagnostic = {}
    water = permanent & np.isfinite(values["vv"]) & np.isfinite(values["vh"])
    land = keep & ~permanent & np.isfinite(values["vv"]) & np.isfinite(values["vh"])
    for name, arr in (("VV event dB", values["vv"]), ("VH event dB", values["vh"])):
        water_diagnostic[name] = {"permanent_water_n": int(water.sum()), "eligible_land_n": int(land.sum()), "permanent_water_median_db": float(np.median(arr[water])) if water.any() else None, "eligible_land_median_db": float(np.median(arr[land])) if land.any() else None, "permanent_water_lower_backscatter_fraction": float(np.mean(arr[water] < np.median(arr[land]))) if water.any() and land.any() else None}
    return {
        "input_files": {"label": str(label_path), "baselines": [str(p) for p in baseline_paths], "features": str(feature_path), "sar": {k: str(sar / f) for k,f in (("VV_event","2015-11-24_VV_dB_lee5.tif"),("VH_event","2015-11-24_VH_dB_lee5.tif"),("VV_reference","2015-10-19_VV_dB_lee5.tif"))}},
        "grid_alignment": {"label": {"crs": str(lp["crs"]), "transform": tuple(lp["transform"]), "shape": label.shape}, "rtc": raster_profiles, "sampling_by_cell_center": True, "label_raster_uses": "official UNOSAT November product inspected exploratory; 1=flood, 0=not mapped flood; 255 nodata", "eligible_exclusions": "either Sep/Oct reference value >0 or WorldCover water fraction >0; RTC invalid and layover/shadow bit 4/16 excluded"},
        "counts": {"feature_table_rows":len(df),"label_cells_mapped":int(inside.sum()),"eligible_positive_before_hand":int(np.count_nonzero(eligible_before_hand & (y==1))),"eligible_negative_before_hand":int(np.count_nonzero(eligible_before_hand & (y==0))),"hand_missing_positive_excluded":int(np.count_nonzero(eligible_before_hand & (y==1) & ~finite_hand)),"eligible_positive_before_rtc":int(np.count_nonzero(keep & (y==1))),"eligible_negative_before_rtc":int(np.count_nonzero(keep & (y==0))),"valid_positive_after_rtc":int(np.count_nonzero(valid & (y==1))),"valid_negative_after_rtc":int(np.count_nonzero(valid & (y==0))),"matched_positive":len(mp),"matched_negative":len(mn),"unmatched_positive_strata":int(unmatched_pos),"hand_bins_m":["<2","2-5","5-10",">=10"],"hand_finite_in_cell_table":int(finite_hand.sum()),"landcover_categories":cover_cols},
        "auc":aucs,"spatial_block_decision_stump":stump,"label_shift_overlap_iou":shifts,"baseline_value_counts":base_counts,"permanent_water_alignment_check":water_diagnostic,
        "interpretation":"Matched, one-dimensional separability diagnostic only; does not establish causal inundation or accepted label status. Spatial folds are grouped by 3 km blocks but not buffered, so stump CV is a small diagnostic rather than a model-quality gate."
    }


def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[2]); args=ap.parse_args()
    result=run(args.root)
    out=args.root/"docs"/"PHASE9B_SAR_DIAGNOSTIC.json"; out.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({"counts":result["counts"],"auc":result["auc"],"stump":result["spatial_block_decision_stump"],"shift_iou":result["label_shift_overlap_iou"],"water_check":result["permanent_water_alignment_check"]},indent=2))

if __name__=="__main__": main()
