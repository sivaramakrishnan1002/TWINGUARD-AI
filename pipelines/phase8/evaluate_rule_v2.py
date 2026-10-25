"""Evaluate the frozen Flood Rule v2 candidate after preregistration."""
from __future__ import annotations

import json
import argparse
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import rasterize
from scipy.ndimage import label
from shapely import wkb
from sqlalchemy import text

from pipelines.phase8.physics_thresholds import align_exact
from pipelines.stage5.db_common import make_engine

ROOT = Path(__file__).resolve().parents[2]
EVENT = "2015-11-24"
SAR = ROOT / "data/processed/sar_work/rtc_aligned"
TERRAIN = ROOT / "data/processed/terrain_cleaned"


def align(path: Path, ref_profile: dict) -> tuple[np.ndarray, float | int | None]:
    with rasterio.open(path) as ds:
        a = align_exact(ds.read(1), ds.transform, ds.crs,
                        ref_profile["transform"], ref_profile["crs"],
                        (ref_profile["height"], ref_profile["width"]),
                        fill_value=ds.nodata if ds.nodata is not None else 0)
        return a, ds.nodata


def official_mask(ref: rasterio.DatasetReader, role: str, date: str) -> tuple[np.ndarray, dict]:
    engine = make_engine()
    try:
        with engine.connect() as connection:
            row = connection.execute(text("""
                SELECT count(*), ST_Area(ST_Intersection(ST_Union(geom),
                              (SELECT ST_Union(geom) FROM twinguard.study_area))) / 1000000.0,
                       array_agg(ST_AsBinary(geom))
                FROM labels.v_usable_flood_labels
                WHERE reference_role = :role AND event_date = CAST(:date AS date)
            """), {"role": role, "date": date}).one()
    finally:
        engine.dispose()
    geometries = [wkb.loads(bytes(blob)) for blob in (row[2] or [])]
    mask = rasterize(((geom, 1) for geom in geometries),
                     out_shape=(ref.height, ref.width), transform=ref.transform,
                     fill=0, dtype="uint8", all_touched=False).astype(bool)
    return mask, {"feature_count": int(row[0]), "dissolved_area_km2": float(row[1] or 0.0)}


def score(truth: np.ndarray, pred: np.ndarray) -> dict:
    tp = int(np.count_nonzero(truth & pred))
    fp = int(np.count_nonzero(~truth & pred))
    fn = int(np.count_nonzero(truth & ~pred))
    tn = int(np.count_nonzero(~truth & ~pred))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    iou = tp / (tp + fp + fn) if tp + fp + fn else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall, "f1": f1, "iou": iou,
            "predicted_area_km2": (tp + fp) * 0.0009,
            "reference_rasterized_area_km2": (tp + fn) * 0.0009}


def assign_tier(iou: float, area_km2: float) -> str:
    if iou >= 0.40 and 49.08 <= area_km2 <= 147.24:
        return "B"
    if 0.25 <= iou < 0.40:
        return "C"
    return "D"


def sieve(binary: np.ndarray, min_cells: int = 5) -> tuple[np.ndarray, dict[str, int]]:
    components, count = label(binary, structure=np.ones((3, 3), dtype=np.uint8))
    sizes = np.bincount(components.ravel())
    keep = sizes >= min_cells
    keep[0] = False
    return keep[components], {"components_before": int(count), "components_after": int(np.count_nonzero(keep)),
                             "pixels_removed": int(binary.sum() - keep[components].sum())}


def main(run_id: str = "20261025_03") -> None:
    if not run_id.replace("_", "").isalnum():
        raise ValueError("run id may contain only letters, digits and underscores")
    hand_path = ROOT / f"data/processed/sar_work/hand_d8_100cells_{run_id}_DEFAULT.tif"
    candidate_path = ROOT / f"data/features/labels/label_{EVENT}_rule_v2_{run_id}_DERIVED.tif"
    out_path = ROOT / f"docs/T4_RULE_V2_EVALUATION_{run_id}_fixed.json"
    if out_path.exists():
        raise FileExistsError("Refusing to overwrite evaluation output; choose a new --run-id")
    with rasterio.open(SAR / "2021-10-23_VV_gamma0_power_lee5.tif") as ref:
        profile = ref.profile.copy(); shape = (ref.height, ref.width)
        truth, source_stats = official_mask(ref, "event_flood", EVENT)
    cma, _ = align(ROOT / "data/processed/grid/cma_mask.tif", profile)
    cma = cma == 1
    candidate, _ = align(candidate_path, profile)
    predicted_primary = candidate == 1
    confidence_path = ROOT / f"data/features/labels/label_{EVENT}_rule_v2_confidence_{run_id}_DERIVED.tif"
    confidence, _ = align(confidence_path, profile)
    wc_class, _ = align(ROOT / "data/features/landcover/worldcover_2021_class.tif", profile)
    with rasterio.open(ROOT / "data/features/landcover/worldcover_2021_area_fractions_30m.tif") as wc:
        builtup = align_exact(wc.read(5), wc.transform, wc.crs, profile["transform"], profile["crs"], shape).astype(np.float32)
    slope, slope_nodata = align(TERRAIN / "slope_deg_edge_safe.tif", profile)
    hand, hand_nodata = align(hand_path, profile)
    # Baseline masks used by the rule are sourced exclusively from the T1 view.
    engine = make_engine()
    try:
        with engine.connect() as connection:
            baselines = connection.execute(text("""
                SELECT event_date, ST_AsBinary(geom)
                FROM labels.v_usable_flood_labels
                WHERE reference_role='baseline_water'
                  AND event_date IN (DATE '2015-09-01', DATE '2015-10-14')
            """)).fetchall()
    finally:
        engine.dispose()
    by_date = {"2015-09-01": [], "2015-10-14": []}
    for dt, geom in baselines: by_date[dt.isoformat()].append(wkb.loads(bytes(geom)))
    base_mask = np.zeros(shape, dtype=bool)
    for geometries in by_date.values():
        base_mask |= rasterize(((g, 1) for g in geometries), out_shape=shape,
                               transform=profile["transform"], fill=0, dtype="uint8").astype(bool)
    water = (wc_class == 80) | base_mask
    hand_valid = np.isfinite(hand) & ((hand != hand_nodata) if hand_nodata is not None else True)
    slope_valid = np.isfinite(slope) & ((slope != slope_nodata) if slope_nodata is not None else True)
    hand_mask = hand_valid & (hand <= 5.0)
    slope_mask = slope_valid & (slope <= 5.0)
    urban_mask = np.isfinite(builtup) & (builtup <= 0.5)

    thresholds = json.loads((ROOT / "docs/T2_PHYSICS_THRESHOLDS.json").read_text(encoding="utf-8"))
    event_date = "2015-11-24"; reference_dates = ["2015-10-19"]
    event_power = {}; ref_power = {}; numeric = cma.copy(); flags = cma.copy()
    for pol in ("VV", "VH"):
        e_path = SAR / f"{event_date}_{pol}_gamma0_power_lee5.tif"
        e, nd = align(e_path, profile); event_power[pol] = e.astype(np.float32)
        numeric &= np.isfinite(e) & ((e != nd) if nd is not None else True) & (e > 0)
        r_path = SAR / f"{reference_dates[0]}_{pol}_gamma0_power_lee5.tif"
        r, rnd = align(r_path, profile); ref_power[pol] = r.astype(np.float32)
        numeric &= np.isfinite(r) & ((r != rnd) if rnd is not None else True) & (r > 0)
    for date in [event_date, *reference_dates]:
        mask, _ = align(SAR / f"{date}_valid_layover_shadow_mask.tif", profile)
        flags &= mask == 1
    passes = {}
    for pol in ("VV", "VH"):
        ev_db = 10*np.log10(np.maximum(event_power[pol], 1e-12))
        rf_db = 10*np.log10(np.maximum(ref_power[pol], 1e-12))
        passes[pol] = ((ev_db <= thresholds["water_land_thresholds"][pol]["midpoint_threshold_db"])
                       & ((ev_db-rf_db) <= thresholds["stable_dry_change_thresholds"][pol]["mean_minus_2sd_db"]))
    raw = cma & numeric & (passes["VV"] | passes["VH"])
    masks = {
        "common_valid_data_and_layover_shadow": flags,
        "permanent_water_exclusion": ~water,
        "slope_at_most_5deg": slope_mask,
        "HAND_at_most_5m": hand_mask,
        "dense_urban_exclusion_builtup_at_most_0.5": urban_mask,
    }
    eligibility_mask = cma & numeric
    for condition in masks.values(): eligibility_mask &= condition
    eligible_pre_mmu = raw & eligibility_mask
    primary, mmu_stats = sieve(eligible_pre_mmu, 5)
    # Domain includes every CMA pixel where event/reference linear power is numeric;
    # cells with flags off are scored as unpredicted, while actual nodata is omitted.
    evaluation_domain = cma & numeric
    y = truth[evaluation_domain]
    primary_score = score(y, predicted_primary[evaluation_domain])
    primary_score["eligible_conditional"] = score(truth[evaluation_domain & eligibility_mask],
                                                   predicted_primary[evaluation_domain & eligibility_mask])

    ablation = []
    for name in [*masks.keys(), "minimum_mapping_unit_5_cells"]:
        raw_eligible = raw.copy()
        for key, condition in masks.items():
            if key != name:
                raw_eligible &= condition
        filtered = raw_eligible if name == "minimum_mapping_unit_5_cells" else sieve(raw_eligible, 5)[0]
        metrics = score(truth[evaluation_domain], filtered[evaluation_domain])
        ablation.append({"mask_removed": name, **metrics})

    reproduced, reproduced_mmu = sieve(eligible_pre_mmu, 5)
    mismatch = predicted_primary ^ reproduced
    mismatch_reasons = {
        "candidate_pixels_failing_numeric_or_cma": int((predicted_primary & ~(cma & numeric)).sum()),
        **{name: int((predicted_primary & ~condition).sum()) for name, condition in masks.items()},
        "pixels_reproduced_different_after_sieve": int(mismatch.sum()),
        "candidate_pixels_not_reproduced": int((predicted_primary & ~reproduced).sum()),
        "reproduced_pixels_missing_from_candidate": int((reproduced & ~predicted_primary).sum()),
    }

    # Land-cover and 3 km block error concentration checks on the fixed full comparison domain.
    class_names={10:"tree",20:"shrub",30:"grass",40:"cropland",50:"built-up",60:"bare",70:"snow/ice",80:"water",90:"wetland",95:"mangrove",100:"moss/lichen"}
    lc_errors=[]
    for code,name in class_names.items():
        m=evaluation_domain & (wc_class==code)
        if not m.any(): continue
        lc_errors.append({"class_code":code,"class":name,"cells":int(m.sum()),"reference_flood_cells":int((truth&m).sum()),
                          "false_negatives":int((truth & ~predicted_primary & m).sum()),"false_positives":int((~truth & predicted_primary & m).sum()),
                          "recall":float((truth & predicted_primary & m).sum()/(truth&m).sum()) if (truth&m).sum() else None})
    blocks, block_nodata = align(ROOT / "data/processed/alignment/spatial_blocks.tif", profile)
    block_rows=[]
    for block in np.unique(blocks[evaluation_domain]):
        if block_nodata is not None and block == block_nodata: continue
        if block <= 0: continue
        m=evaluation_domain & (blocks==block)
        if not (truth&m).any(): continue
        sm=score(truth[m],predicted_primary[m])
        block_rows.append({"block_id":int(block),"reference_flood_cells":int((truth&m).sum()),"false_negatives":sm["fn"],"false_positives":sm["fp"],"iou":sm["iou"]})
    block_rows.sort(key=lambda r:r["false_negatives"],reverse=True)
    ref_area_in_domain=float((truth&evaluation_domain).sum()*0.0009)
    report={
      "status":"fixed-rule evaluation; no threshold or mask retuning",
      "preregistration":"docs/LABEL_ACCEPTANCE.md; recorded 2026-10-25T09:42:35.367+05:30 before this run",
      "event":"2015-11-24", "run_id":run_id,"candidate":str(candidate_path.relative_to(ROOT)),
      "reference_source":"labels.v_usable_flood_labels, tier A official UNOSAT event_flood, rasterized at pixel centres",
      "reference_source_stats":source_stats,
      "comparison": {"cma_cells":int(cma.sum()),"numeric_sar_cells":int((cma&numeric).sum()),"valid_flag_cells":int((cma&flags).sum()),
                     "reference_rasterized_area_cma_km2":float((truth&cma).sum()*0.0009),"reference_rasterized_area_comparison_km2":ref_area_in_domain,
                     "known_source_area_km2":98.16,"comparison_area_km2":int(evaluation_domain.sum())*0.0009,
                     "rule_eligible_cells":int(eligibility_mask.sum()),"rule_eligible_reference_area_km2":float((truth&evaluation_domain&eligibility_mask).sum()*0.0009),
                     "rule_positive_before_mmu_cells":int(eligible_pre_mmu.sum()),
                     "excluded_numeric_cells_with_reference_flood":int((truth & evaluation_domain & ~eligibility_mask).sum())},
      "primary_full_observable_comparison":primary_score,
      "mmu":mmu_stats,
      "candidate_reproduction_check":{"metrics_recomputed_from_frozen_rule":reproduced_mmu,"mismatch_reasons":mismatch_reasons},
      "tier": assign_tier(primary_score["iou"], primary_score["predicted_area_km2"]),
      "acceptance":"B requires IoU>=0.40 and predicted area 49.08-147.24 km2; C requires 0.25<=IoU<0.40; otherwise D.",
      "mask_ablations":ablation,
      "reference_pixels_excluded_by_each_single_mask":{
          name:int((truth & evaluation_domain & ~condition).sum()) for name,condition in masks.items()
      },
      "false_errors_by_worldcover":lc_errors,
      "spatial_block_check":{"method":"descriptive per 3 km spatial block; no CV split","blocks_with_reference_flood":len(block_rows),
                             "top_10_by_false_negatives":block_rows[:10],"top_block_fn_share":float(block_rows[0]["false_negatives"]/max(primary_score["fn"],1)) if block_rows else None,
                             "top_5_fn_share":float(sum(r["false_negatives"] for r in block_rows[:5])/max(primary_score["fn"],1))},
      "limitations":["UNOSAT may use the same 24 Nov SAR scene; comparison tests pipeline/map agreement, not independent physics validation","binary threshold rule has no calibrated probability: ROC/PR AUC, Brier, ECE, calibration and uncertainty coverage are not applicable","descriptive block summaries do not constitute held-out cross-validation","the 30 m rasterized reference area is distinct from vector dissolved area"],
    }
    out_path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"tier":report["tier"],"comparison":report["comparison"],"metrics":{k:v for k,v in primary_score.items() if k!="eligible_conditional"},"ablation":ablation,"blocks":report["spatial_block_check"]},indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="20261025_03")
    main(parser.parse_args().run_id)
