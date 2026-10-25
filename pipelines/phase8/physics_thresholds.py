"""Estimate SAR thresholds from pre-event water/land samples only.

Run from project root: .venv/Scripts/python.exe -m pipelines.phase8.physics_thresholds
This reads existing aligned RTC and thematic rasters; it does not read event labels.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.features import rasterize
from scipy.ndimage import binary_erosion
from sklearn.metrics import roc_auc_score
from shapely import wkb
from sqlalchemy import text

from pipelines.stage5.db_common import make_engine

ROOT = Path(__file__).resolve().parents[2]
SAR = ROOT / "data/processed/sar_work/rtc_aligned"
OUT_JSON = ROOT / "docs/T2_PHYSICS_THRESHOLDS.json"
OUT_FIG = ROOT / "docs/figures/T2_pre_event_sar_distributions.png"
SEED = 20261025
SAMPLE_PER_GROUP = 20_000
LAND_COVER = {50: "built-up", 40: "cropland", 10: "tree", 60: "bare", 30: "grass"}
SCENES = {"2015-10-19": "2015-10-19", "2021-10-23": "2021-10-23", "2021-11-04": "2021-11-04"}


def align_exact(source_array: np.ndarray, src_transform, src_crs, dst_transform, dst_crs, shape) -> np.ndarray:
    """Copy between congruent 30 m grids with an integer pixel offset; do not resample."""
    if src_crs != dst_crs or abs(src_transform.a - dst_transform.a) > 1e-8 or abs(src_transform.e - dst_transform.e) > 1e-8:
        raise ValueError("Input and master grid must have identical CRS and pixel size")
    col_off_f = (src_transform.c - dst_transform.c) / dst_transform.a
    row_off_f = (src_transform.f - dst_transform.f) / dst_transform.e
    col_off, row_off = round(col_off_f), round(row_off_f)
    if abs(col_off_f - col_off) > 1e-6 or abs(row_off_f - row_off) > 1e-6:
        raise ValueError("Input raster is not pixel-aligned to the master grid")
    result = np.zeros(shape, dtype=source_array.dtype)
    src_r0, src_c0 = max(0, -row_off), max(0, -col_off)
    dst_r0, dst_c0 = max(0, row_off), max(0, col_off)
    height = min(source_array.shape[0] - src_r0, shape[0] - dst_r0)
    width = min(source_array.shape[1] - src_c0, shape[1] - dst_c0)
    if height > 0 and width > 0:
        result[dst_r0:dst_r0 + height, dst_c0:dst_c0 + width] = source_array[src_r0:src_r0 + height, src_c0:src_c0 + width]
    return result


def read_on_grid(path: Path, reference: rasterio.DatasetReader):
    with rasterio.open(path) as source:
        return align_exact(source.read(1), source.transform, source.crs,
                           reference.transform, reference.crs,
                           (reference.height, reference.width))


def values(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1).astype(np.float32)
        return np.where(np.isfinite(a) & (a != ds.nodata) & (a > -100), a, np.nan)


def baseline_masks_from_usable_view(reference: rasterio.DatasetReader) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Rasterize baseline-water geometries from the T1 accepted-label view."""
    engine = make_engine()
    try:
        with engine.connect() as connection:
            rows = connection.execute(text("""
                SELECT event_date, ST_AsBinary(geom)
                FROM labels.v_usable_flood_labels
                WHERE reference_role = 'baseline_water'
                  AND event_date IN (DATE '2015-09-01', DATE '2015-10-14')
                  AND ST_SRID(geom) = 32644
            """)).fetchall()
    finally:
        engine.dispose()
    geoms: dict[str, list] = {"2015-09-01": [], "2015-10-14": []}
    for event_date, geom_wkb in rows:
        key = event_date.isoformat()
        geoms[key].append(wkb.loads(bytes(geom_wkb)))
    masks = {}
    for key, items in geoms.items():
        masks[key] = rasterize(
            ((geom, 1) for geom in items),
            out_shape=(reference.height, reference.width),
            transform=reference.transform,
            fill=0,
            dtype="uint8",
            all_touched=False,
        )
    return masks["2015-09-01"], masks["2015-10-14"], {k: len(v) for k, v in geoms.items()}


def sample(a: np.ndarray, mask: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    v = a[mask & np.isfinite(a)]
    if v.size > SAMPLE_PER_GROUP:
        v = v[rng.choice(v.size, SAMPLE_PER_GROUP, replace=False)]
    return v


def stat(a: np.ndarray) -> dict[str, float | int | None]:
    if not a.size:
        return {"n": 0, "mean_db": None, "sd_db": None, "p05_db": None, "median_db": None, "p95_db": None}
    return {
        "n": int(a.size), "mean_db": float(np.mean(a)), "sd_db": float(np.std(a, ddof=1)) if a.size > 1 else 0.0,
        "p05_db": float(np.percentile(a, 5)), "median_db": float(np.median(a)), "p95_db": float(np.percentile(a, 95)),
    }


def main() -> None:
    reference_path = SAR / "2021-10-23_VV_dB_lee5.tif"
    def on_master(path: Path) -> np.ndarray:
        with rasterio.open(reference_path) as ref:
            return read_on_grid(path, ref)

    with rasterio.open(reference_path) as ref:
        profile = ref.profile.copy()
        shape = (ref.height, ref.width)
        cma_native = read_on_grid(ROOT / "data/processed/grid/cma_mask.tif", ref) == 1
        wc_class = read_on_grid(ROOT / "data/features/landcover/worldcover_2021_class.tif", ref)
        sep, octo, baseline_feature_counts = baseline_masks_from_usable_view(ref)
        # Erode the native WorldCover 2021 water class by one 30 m cell before reprojection.
        with rasterio.open(ROOT / "data/features/landcover/worldcover_2021_class.tif") as wc:
            wc_water = wc.read(1) == 80
            eroded_native = binary_erosion(wc_water, structure=np.ones((3, 3), dtype=bool), border_value=0)
            eroded = align_exact(eroded_native.astype(np.uint8), wc.transform, wc.crs,
                                 ref.transform, ref.crs, shape)
    # Baseline agreement is intentionally strict: both historical UNOSAT layers and the
    # one-cell-eroded WorldCover water core must agree. UNOSAT value 1 or 2 means mapped water.
    stable_water = cma_native & (eroded == 1) & (sep > 0) & (octo > 0)
    stable_dry = cma_native & ~stable_water & ~((eroded == 1) | (sep > 0) | (octo > 0))
    dry_masks = {name: stable_dry & (wc_class == code) for code, name in LAND_COVER.items()}
    rng = np.random.default_rng(SEED)
    result: dict = {
        "status": "PRE_EVENT_PHYSICS_SAMPLES; thresholds are defaults to confirm, not event-label tuned",
        "seed": SEED,
        "grid": {"crs": "EPSG:32644", "pixel_m": 30, "shape": list(shape), "cma_cells": int(cma_native.sum())},
        "water_sample_definition": "CMA ∩ one-cell-eroded WorldCover class 80 ∩ nonzero UNOSAT 2015-09-01 ∩ nonzero UNOSAT 2015-10-14",
        "dry_sample_definition": "CMA cells outside all mapped baseline-water cells, stratified by WorldCover class 50/40/10/60/30; stability is an unverified assumption because no field dry/wet labels exist",
        "stable_water_cells": int(stable_water.sum()),
        "baseline_features_from_usable_view": baseline_feature_counts,
        "stable_dry_cells_by_landcover": {name: int(mask.sum()) for name, mask in dry_masks.items()},
        "sampling": f"Up to {SAMPLE_PER_GROUP:,} pixels per water and land-cover stratum per date, fixed seed; observations are spatially autocorrelated.",
        "scenes": {},
        "threshold_method": "For each polarization, compute ROC-AUC for lower dB as water; choose midpoint of sampled water and balanced-land medians as a descriptive screening threshold (not fitted to event flood labels).",
        "change_threshold_method": "Per-polarization 2021 Nov 04 minus Oct 23 dB change on stable dry samples; mean − 2 sample standard deviations (k=2, DEFAULT to confirm).",
    }
    figure_data: dict[str, dict[str, list[np.ndarray]]] = {p: {"water": [], "dry": []} for p in ("VV", "VH")}
    pooled_dry: dict[str, list[np.ndarray]] = {p: [] for p in ("VV", "VH")}
    pooled_water: dict[str, list[np.ndarray]] = {p: [] for p in ("VV", "VH")}
    for date in SCENES:
        result["scenes"][date] = {}
        valid = on_master(SAR / f"{date}_valid_layover_shadow_mask.tif") == 1
        scene_water_mask = stable_water & valid
        scene_land_masks = {n: m & valid for n, m in dry_masks.items()}
        for pol in ("VV", "VH"):
            a = values(SAR / f"{date}_{pol}_dB_lee5.tif")
            w = sample(a, scene_water_mask, rng)
            by_class = {n: sample(a, m, rng) for n, m in scene_land_masks.items()}
            # Equal weighting of land-cover strata prevents the largest class dominating.
            nonempty = [v for v in by_class.values() if v.size]
            land = np.concatenate(nonempty) if nonempty else np.array([], dtype=np.float32)
            if w.size and land.size:
                auc = float(roc_auc_score(np.r_[np.ones(w.size), np.zeros(land.size)], np.r_[-w, -land]))
                midpoint = (float(np.median(w)) + float(np.median(land))) / 2.0
            else:
                auc = None
                midpoint = None
            result["scenes"][date][pol] = {
                "water": stat(w), "dry_by_landcover": {n: stat(v) for n, v in by_class.items()},
                "balanced_dry": stat(land), "roc_auc_lower_db_as_water": auc,
                "median_midpoint_threshold_db": midpoint,
            }
            figure_data[pol]["water"].append(w)
            figure_data[pol]["dry"].append(land)
            pooled_dry[pol].append(land)
            pooled_water[pol].append(w)
    thresholds = {}
    for pol in ("VV", "VH"):
        w = np.concatenate([x for x in pooled_water[pol] if x.size])
        d = np.concatenate([x for x in pooled_dry[pol] if x.size])
        auc = float(roc_auc_score(np.r_[np.ones(w.size), np.zeros(d.size)], np.r_[-w, -d]))
        wm, dm = float(np.median(w)), float(np.median(d))
        thresholds[pol] = {
            "water_median_db": wm, "balanced_dry_median_db": dm,
            "midpoint_threshold_db": (wm + dm) / 2.0,
            "roc_auc_lower_db_as_water": auc,
            "water_sample_n": int(w.size), "balanced_dry_sample_n": int(d.size),
            "interpretation": "AUC near 0.5 indicates weak separation; thresholds are only screening defaults.",
        }
    result["water_land_thresholds"] = thresholds
    change = {}
    valid23 = on_master(SAR / "2021-10-23_valid_layover_shadow_mask.tif") == 1
    valid04 = on_master(SAR / "2021-11-04_valid_layover_shadow_mask.tif") == 1
    stable_dry_sample_mask = np.logical_or.reduce(list(dry_masks.values()))
    pair_mask = stable_dry_sample_mask & valid23 & valid04
    for pol in ("VV", "VH"):
        a23 = values(SAR / f"2021-10-23_{pol}_dB_lee5.tif")
        a04 = values(SAR / f"2021-11-04_{pol}_dB_lee5.tif")
        delta = (a04 - a23)[pair_mask & np.isfinite(a23) & np.isfinite(a04)]
        mu = float(np.mean(delta)); sd = float(np.std(delta, ddof=1))
        change[pol] = {"n": int(delta.size), "mean_db": mu, "sd_db": sd, "mean_minus_2sd_db": mu - 2 * sd, "p05_db": float(np.percentile(delta, 5)), "p95_db": float(np.percentile(delta, 95))}
    result["stable_dry_change_thresholds"] = change
    result["note"] = "Pre-event classifier distributions use existing Lee 5x5 dB RTC aligned products; duplicate adjacent slices are already mosaicked by the prior Stage 8 workflow. WorldCover is 2021 and the 2015 baseline labels are exploratory. No event flood label or UNOSAT event extent is used to choose these thresholds."
    OUT_JSON.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    OUT_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    for ax, pol in zip(axes, ("VV", "VH")):
        water = np.concatenate([x for x in figure_data[pol]["water"] if x.size])
        dry = np.concatenate([x for x in figure_data[pol]["dry"] if x.size])
        bins = np.linspace(min(np.percentile(water, 1), np.percentile(dry, 1)), max(np.percentile(water, 99), np.percentile(dry, 99)), 70)
        ax.hist(water, bins=bins, density=True, alpha=.60, label="stable water sample")
        ax.hist(dry, bins=bins, density=True, alpha=.60, label="balanced dry land")
        ax.axvline(thresholds[pol]["midpoint_threshold_db"], color="black", linestyle="--", label="median midpoint")
        ax.set(title=f"{pol}: pre-event backscatter", xlabel="Lee-filtered gamma0 dB", ylabel="Density")
        ax.legend(fontsize=8)
    fig.suptitle("DERIVED training-free distributions — not event-label validation")
    fig.savefig(OUT_FIG, dpi=160)
    plt.close(fig)
    print(json.dumps({"cma_cells": int(cma_native.sum()), "stable_water_cells": int(stable_water.sum()), "dry_strata": result["stable_dry_cells_by_landcover"], "thresholds": thresholds, "change": change}, indent=2))


if __name__ == "__main__":
    main()
