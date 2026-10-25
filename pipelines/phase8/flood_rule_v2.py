"""Build Batch 1's fixed Flood Rule v2 candidate from existing RTC/terrain rasters."""
from __future__ import annotations

import json
import argparse
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import label
from sqlalchemy import text

from pipelines.phase8.physics_thresholds import align_exact
from pipelines.stage5.db_common import make_engine

ROOT = Path(__file__).resolve().parents[2]
SAR = ROOT / "data/processed/sar_work/rtc_aligned"
TERRAIN = ROOT / "data/processed/terrain_cleaned"
OUT = ROOT / "data/features/labels"
EVENT = "2015-11-24"
EVENT_SCENE = "2015-11-24"
REFERENCE_SCENES = ["2015-10-19"]
STREAM_ACCUMULATION_CELLS = 100
MAX_SLOPE_DEG = 5.0
MAX_HAND_M = 5.0
MAX_BUILT_UP_FRACTION = 0.5
MIN_COMPONENT_CELLS = 5


def compute_hand(dem: np.ndarray, direction: np.ndarray, accumulation: np.ndarray,
                 valid: np.ndarray, stream_threshold: float) -> tuple[np.ndarray, dict[str, int]]:
    """Height above the first downstream D8 cell at/above threshold, in metres."""
    offsets = {1: (-1, 0), 2: (-1, 1), 3: (0, 1), 4: (1, 1),
               5: (1, 0), 6: (1, -1), 7: (0, -1), 8: (-1, -1)}
    h, w = dem.shape
    downstream = np.full(h * w, -1, dtype=np.int64)
    rr, cc = np.indices((h, w))
    for code, (dy, dx) in offsets.items():
        src = valid & (direction == code)
        r = rr[src] + dy
        c = cc[src] + dx
        inside = (r >= 0) & (r < h) & (c >= 0) & (c < w)
        src_flat = np.flatnonzero(src)[inside]
        dst_flat = r[inside] * w + c[inside]
        dst_good = valid.ravel()[dst_flat]
        downstream[src_flat[dst_good]] = dst_flat[dst_good]
    stream = valid & np.isfinite(accumulation) & (accumulation >= stream_threshold)
    z = dem.ravel()
    valid_ids = np.flatnonzero(valid.ravel())
    order = valid_ids[np.argsort(z[valid_ids], kind="stable")]
    stream_elev = np.full(h * w, np.nan, dtype=np.float32)
    stream_elev[stream.ravel()] = z[stream.ravel()]
    for index in order:
        if stream.ravel()[index]:
            continue
        target = downstream[index]
        if target >= 0 and np.isfinite(stream_elev[target]):
            stream_elev[index] = stream_elev[target]
    hand = np.full(h * w, np.nan, dtype=np.float32)
    has_drainage = valid.ravel() & np.isfinite(stream_elev)
    hand[has_drainage] = np.maximum(0.0, z[has_drainage] - stream_elev[has_drainage])
    return hand.reshape(h, w), {
        "valid_cells": int(valid.sum()), "stream_cells": int(stream.sum()),
        "cells_reaching_stream": int(has_drainage.sum()),
        "unassigned_sink_or_outlet_cells": int(valid.sum() - has_drainage.sum()),
    }


def _read(path: Path) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as ds:
        return ds.read(1), ds.profile.copy()


def _align(path: Path, ref_profile: dict) -> np.ndarray:
    with rasterio.open(path) as ds:
        return align_exact(ds.read(1), ds.transform, ds.crs,
                           ref_profile["transform"], ref_profile["crs"],
                           (ref_profile["height"], ref_profile["width"]),
                           fill_value=ds.nodata if ds.nodata is not None else 0)


def _valid_float(a: np.ndarray, nodata: float | int | None) -> np.ndarray:
    # This helper is used for linear-power gamma0 rasters; zero cannot be log10-transformed.
    return np.isfinite(a) & ((a != nodata) if nodata is not None else True) & (a > 0)


def valid_slope_mask(slope: np.ndarray, nodata: float | int | None, maximum_deg: float) -> np.ndarray:
    return np.isfinite(slope) & ((slope != nodata) if nodata is not None else True) & (slope <= maximum_deg)


def baseline_water_from_view(ref_profile: dict) -> tuple[np.ndarray, int]:
    from rasterio.features import rasterize
    from shapely import wkb

    engine = make_engine()
    try:
        with engine.connect() as connection:
            rows = connection.execute(text("""
                SELECT ST_AsBinary(geom)
                FROM labels.v_usable_flood_labels
                WHERE reference_role = 'baseline_water'
                  AND event_date IN (DATE '2015-09-01', DATE '2015-10-14')
                  AND ST_SRID(geom) = 32644
            """)).fetchall()
    finally:
        engine.dispose()
    geoms = [wkb.loads(bytes(row[0])) for row in rows]
    mask = rasterize(((g, 1) for g in geoms), out_shape=(ref_profile["height"], ref_profile["width"]),
                     transform=ref_profile["transform"], fill=0, dtype="uint8", all_touched=False)
    return mask.astype(bool), len(geoms)


def main(run_id: str = "20261025_03") -> None:
    if not run_id.replace("_", "").isalnum():
        raise ValueError("run id may contain only letters, digits and underscores")
    hand_path = ROOT / f"data/processed/sar_work/hand_d8_100cells_{run_id}_DEFAULT.tif"
    label_path = OUT / f"label_{EVENT}_rule_v2_{run_id}_DERIVED.tif"
    confidence_path = OUT / f"label_{EVENT}_rule_v2_confidence_{run_id}_DERIVED.tif"
    summary_path = ROOT / f"docs/T3_FLOOD_RULE_V2_{run_id}.json"
    existing = [p for p in (hand_path, label_path, confidence_path, summary_path) if p.exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite Batch 1 outputs; choose a new --run-id")
    ref_path = SAR / f"{REFERENCE_SCENES[0]}_VV_gamma0_power_lee5.tif"
    with rasterio.open(ref_path) as ref:
        profile = ref.profile.copy()
    shape = (profile["height"], profile["width"])
    # Hydrology uses the cleaned conditioned DSM and the matching D8 direction/accumulation.
    flow = _align(TERRAIN / "flow_direction_d8.tif", profile)
    accumulation = _align(TERRAIN / "flow_accumulation_cells_d8.tif", profile).astype(np.float32)
    dem = _align(TERRAIN / "cleaned_elevation_m.tif", profile).astype(np.float32)
    valid_dem = np.isfinite(dem) & (dem > -100)
    hand, hand_counts = compute_hand(dem, flow, accumulation, valid_dem, STREAM_ACCUMULATION_CELLS)
    hand_profile = profile.copy(); hand_profile.update(dtype="float32", count=1, nodata=-9999.0, compress="deflate", tiled=True)
    hand_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(hand_path, "w", **hand_profile) as ds:
        ds.write(np.where(np.isfinite(hand), hand, -9999.0).astype(np.float32), 1)
        ds.update_tags(derivation="D8 height above first downstream cell with accumulation >= 1000", stream_threshold_cells=str(STREAM_ACCUMULATION_CELLS), status="DEFAULT_TO_CONFIRM")

    # Terrain and land cover layers are aligned exactly by integer grid offsets.
    slope_path = TERRAIN / "slope_deg_edge_safe.tif"
    with rasterio.open(slope_path) as slope_ds:
        slope_nodata = slope_ds.nodata
        slope = _align(slope_path, profile).astype(np.float32)
    cma = _align(ROOT / "data/processed/grid/cma_mask.tif", profile) == 1
    wc_class = _align(ROOT / "data/features/landcover/worldcover_2021_class.tif", profile)
    with rasterio.open(ROOT / "data/features/landcover/worldcover_2021_area_fractions_30m.tif") as wc:
        builtup = align_exact(wc.read(5), wc.transform, wc.crs, profile["transform"], profile["crs"], shape).astype(np.float32)
    baseline_water, baseline_count = baseline_water_from_view(profile)
    permanent_water = (wc_class == 80) | baseline_water
    event_power = {}; ref_power = {}; input_valid = cma.copy()
    for pol in ("VV", "VH"):
        e_path = SAR / f"{EVENT_SCENE}_{pol}_gamma0_power_lee5.tif"
        event_power[pol] = _align(e_path, profile).astype(np.float32)
        with rasterio.open(e_path) as ds:
            input_valid &= _valid_float(event_power[pol], ds.nodata)
        aligned_refs=[]
        for date in REFERENCE_SCENES:
            r_path = SAR / f"{date}_{pol}_gamma0_power_lee5.tif"
            r = _align(r_path, profile).astype(np.float32)
            with rasterio.open(r_path) as ds:
                input_valid &= _valid_float(r, ds.nodata)
            aligned_refs.append(r)
        # Reference scenes are combined in linear power, not by averaging dB.
        ref_power[pol] = np.mean(aligned_refs, axis=0, dtype=np.float64).astype(np.float32)
    for date in [EVENT_SCENE, *REFERENCE_SCENES]:
        input_valid &= _align(SAR / f"{date}_valid_layover_shadow_mask.tif", profile) == 1
    thresholds = json.loads((ROOT / "docs/T2_PHYSICS_THRESHOLDS.json").read_text(encoding="utf-8"))
    valid_hand = np.isfinite(hand)
    slope_valid = np.isfinite(slope) & ((slope != slope_nodata) if slope_nodata is not None else True)
    slope_eligible = valid_slope_mask(slope, slope_nodata, MAX_SLOPE_DEG)
    eligible = (input_valid & ~permanent_water & valid_hand & slope_eligible
                & (hand <= MAX_HAND_M) & np.isfinite(builtup) & (builtup <= MAX_BUILT_UP_FRACTION))
    raw_confidence = np.zeros(shape, dtype=np.uint8)
    passes = {}
    for pol in ("VV", "VH"):
        event_db = 10.0 * np.log10(np.maximum(event_power[pol], 1e-12))
        ref_db = 10.0 * np.log10(np.maximum(ref_power[pol], 1e-12))
        delta = event_db - ref_db
        water_threshold = thresholds["water_land_thresholds"][pol]["midpoint_threshold_db"]
        delta_threshold = thresholds["stable_dry_change_thresholds"][pol]["mean_minus_2sd_db"]
        passes[pol] = (event_db <= water_threshold) & (delta <= delta_threshold)
    both = eligible & passes["VV"] & passes["VH"]
    one = eligible & (passes["VV"] ^ passes["VH"])
    raw_confidence[both] = 2
    raw_confidence[one] = 1
    components, count = label(raw_confidence > 0, structure=np.ones((3, 3), dtype=np.uint8))
    sizes = np.bincount(components.ravel())
    keep = sizes >= MIN_COMPONENT_CELLS
    keep[0] = False
    cleaned = keep[components]
    confidence = np.where(cleaned, raw_confidence, 0).astype(np.uint8)
    label_out = np.where(eligible, cleaned.astype(np.uint8), 255).astype(np.uint8)
    confidence_out = np.where(eligible, confidence, 255).astype(np.uint8)
    profile_out = profile.copy(); profile_out.update(dtype="uint8", count=1, nodata=255, compress="deflate", tiled=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for path, arr, desc in [(label_path, label_out, "Flood Rule v2 candidate; 1=flood, 0=eligible nonflood, 255=excluded/nodata"),
                             (confidence_path, confidence_out, "Flood Rule v2 confidence; 2=both polarisations, 1=one, 0=eligible nonflood, 255=excluded/nodata")]:
        with rasterio.open(path, "w", **profile_out) as ds:
            ds.write(arr, 1); ds.set_band_description(1, desc)
            ds.update_tags(status="DERIVED_NOT_ACCEPTED", event=EVENT, reference=",".join(REFERENCE_SCENES), rule_version="v2", thresholds_json="docs/T2_PHYSICS_THRESHOLDS.json")
    report = {
        "status": "DERIVED_NOT_ACCEPTED; no UNOSAT event labels were read or evaluated",
        "event": EVENT, "event_scene": EVENT_SCENE, "reference_scenes": REFERENCE_SCENES,
        "thresholds_source": "docs/T2_PHYSICS_THRESHOLDS.json",
        "fixed_rule": {
            "vv_water_db": thresholds["water_land_thresholds"]["VV"]["midpoint_threshold_db"],
            "vh_water_db": thresholds["water_land_thresholds"]["VH"]["midpoint_threshold_db"],
            "vv_change_db": thresholds["stable_dry_change_thresholds"]["VV"]["mean_minus_2sd_db"],
            "vh_change_db": thresholds["stable_dry_change_thresholds"]["VH"]["mean_minus_2sd_db"],
            "per_polarisation_pass": "event dB <= water median-midpoint AND event-minus-reference dB <= corresponding stable-dry mean−2SD",
            "flood_confidence": "medium if exactly one polarization passes both tests; high if both pass",
            "permanent_water": "WorldCover class 80 OR baseline-water geometries from labels.v_usable_flood_labels",
            "max_slope_deg": MAX_SLOPE_DEG, "max_HAND_m": MAX_HAND_M,
            "stream_accumulation_cells": STREAM_ACCUMULATION_CELLS,
            "dense_urban_excluded_if_built_up_fraction_gt": MAX_BUILT_UP_FRACTION,
            "minimum_mapping_unit": {"connected_cells": MIN_COMPONENT_CELLS, "connectivity": 8, "area_km2": MIN_COMPONENT_CELLS * 0.0009},
        },
        "hand": {**hand_counts, "units": "m", "valid_cma_cells": int(np.isfinite(hand[cma]).sum()),
                 "valid_cma_percent": float(np.isfinite(hand[cma]).sum() / max(int(cma.sum()), 1) * 100),
                 "median_m": float(np.nanmedian(hand[cma])) if np.isfinite(hand[cma]).any() else None,
                 "p95_m": float(np.nanpercentile(hand[cma], 95)) if np.isfinite(hand[cma]).any() else None,
                 "max_m": float(np.nanmax(hand[cma])) if np.isfinite(hand[cma]).any() else None,
                 "definition": "cleaned DEM minus elevation of first downstream D8 cell whose upstream accumulation is >= threshold"},
        "mask_counts": {
            "cma_cells": int(cma.sum()), "baseline_water_features_from_usable_view": baseline_count,
            "permanent_water_cells": int((cma & permanent_water).sum()),
            "common_sar_and_cma_cells": int(input_valid.sum()), "eligible_after_all_masks": int(eligible.sum()),
            "excluded_nodata_slope_cells": int((input_valid & ~permanent_water & ~slope_valid).sum()),
            "excluded_dense_urban_cells": int((input_valid & ~permanent_water & valid_hand & slope_valid & (slope <= MAX_SLOPE_DEG) & (hand <= MAX_HAND_M) & (builtup > MAX_BUILT_UP_FRACTION)).sum()),
            "raw_components_8_connected": int(count), "retained_components": int(np.count_nonzero(keep)),
        },
        "candidate": {"flood_cells": int(cleaned.sum()), "flood_area_km2": float(cleaned.sum() * 0.0009),
                      "high_confidence_cells": int((confidence == 2).sum()), "medium_confidence_cells": int((confidence == 1).sum()),
                      "eligible_nonflood_cells": int(eligible.sum() - cleaned.sum()),
                      "nodata_or_excluded_cells": int((~eligible).sum())},
        "limitations": ["DERIVED candidate, not accepted or field-validated", "no UNOSAT event layer used for threshold selection", "DEM is a DSM; urban height artifacts remain", "HAND stream threshold and cutoffs are defaults to confirm", "common RTC validity masks constrain area"],
    }
    report["run_id"] = run_id
    report["output_files"] = [str(label_path.relative_to(ROOT)), str(confidence_path.relative_to(ROOT)), str(hand_path.relative_to(ROOT))]
    summary_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"candidate": report["candidate"], "masks": report["mask_counts"], "hand": report["hand"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="20261025_03")
    main(parser.parse_args().run_id)
