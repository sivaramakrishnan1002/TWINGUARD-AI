"""Build explicitly assumed depth-scenario probabilities without changing T6 files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_erosion, gaussian_filter, label

ROOT = Path(__file__).resolve().parents[2]
GRID = ROOT / "data/processed/grid/cma_mask.tif"
DEM = ROOT / "data/processed/terrain_cleaned/cleaned_elevation_m.tif"
LABELS = ROOT / "data/processed/labels_inspection"
T6 = ROOT / "data/features/depth/batch1_v1"
OUT = ROOT / "data/features/depth_scenarios/cr003_v1"
SUMMARY = ROOT / "docs/DEPTH_UNCERTAINTY_SCENARIOS.json"
NODATA = -9999.0
CLASSES = ((0.0, 0.15), (0.15, 0.30), (0.30, 0.50), (0.50, None))
DATES = ("2015-11-12", "2015-11-24")


def depth_classes(values: np.ndarray) -> np.ndarray:
    """Class indices: <0.15, [0.15,0.30), [0.30,0.50), >=0.50 m."""
    return np.searchsorted(np.array([0.15, 0.30, 0.50]), values, side="right").astype(np.uint8)


def cancel_common_bias(dem: np.ndarray, flood_valid: np.ndarray, offset_m: float = 4.0) -> float:
    """Return max depth difference after applying one datum offset to DEM and surface."""
    if not np.isfinite(offset_m):
        raise ValueError("offset_m must be finite")
    if dem.shape != flood_valid.shape:
        raise ValueError("dem and flood_valid must have matching shapes")
    if not flood_valid.any():
        raise ValueError("flood_valid must contain at least one cell")
    if not np.isfinite(dem[flood_valid]).all():
        raise ValueError("DEM must be finite on every flooded cell")
    components, count = label(flood_valid, structure=np.ones((3, 3), dtype=np.uint8))
    edge = flood_valid & ~binary_erosion(flood_valid, structure=np.ones((3, 3), dtype=bool), border_value=0)
    edge_idx = np.flatnonzero(edge)
    component_ids = components.ravel()[edge_idx]
    order = np.argsort(component_ids, kind="stable")
    edge_idx = edge_idx[order]
    component_ids = component_ids[order]
    counts = np.bincount(component_ids, minlength=count + 1)
    split_points = np.cumsum(counts[1:-1])
    edge_groups = np.split(edge_idx, split_points)
    surfaces = np.full(count + 1, np.nan, dtype=np.float64)
    flat_dem = dem.ravel()
    for cid, group in enumerate(edge_groups, start=1):
        if group.size:
            surfaces[cid] = np.median(flat_dem[group])
    component_surface = surfaces[components[flood_valid]]
    elevations = dem[flood_valid].astype(np.float64)
    before = np.maximum(0.0, component_surface - elevations)
    after = np.maximum(0.0, (component_surface + offset_m) - (elevations + offset_m))
    return float(np.max(np.abs(before - after)))


def _correlated_error(shape: tuple[int, int], valid: np.ndarray, rng: np.random.Generator,
                      q95_magnitude: float, sigma_cells: float = 10.0) -> np.ndarray:
    white = rng.standard_normal(shape, dtype=np.float32)
    field = gaussian_filter(white, sigma=sigma_cells, mode="reflect")
    scale = float(np.quantile(np.abs(field[valid]), 0.95))
    if not np.isfinite(scale) or scale <= 0:
        raise RuntimeError("spatial error field has zero or invalid spread")
    return np.clip(field * (q95_magnitude / scale), -q95_magnitude, q95_magnitude).astype(np.float32)


def _write(path: Path, array: np.ndarray, profile: dict, description: str, tags: dict[str, str]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite scenario output: {path}")
    profile = profile.copy()
    profile.update(dtype="float32", count=1, nodata=NODATA, compress="deflate", tiled=True)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(array.astype(np.float32), 1)
        dst.set_band_description(1, description)
        dst.update_tags(**tags)


def process_event(event_date: str, draws: int, rng: np.random.Generator, out_dir: Path) -> dict:
    label_path = LABELS / f"{event_date}_EXPLORATORY_NOT_FINAL.tif"
    mean_path = T6 / f"depth_mean_{event_date}_UNOSAT_A_DERIVED.tif"
    with rasterio.open(GRID) as gd, rasterio.open(DEM) as dd, rasterio.open(label_path) as ld, rasterio.open(mean_path) as md:
        profile = gd.profile.copy()
        cma = gd.read(1) == 1
        dem = dd.read(1).astype(np.float32)
        dem_ok = np.isfinite(dem) & (dem != dd.nodata)
        raw_label = ld.read(1)
        label_flood = (raw_label == 1) & cma
        mean = md.read(1).astype(np.float32)
        # This is the actual T6 finite depth coverage; never convert its NoData to dry.
        coverage = (mean != md.nodata) & np.isfinite(mean) & label_flood & dem_ok
        align = all((ds.crs == gd.crs and ds.transform == gd.transform and (ds.width, ds.height) == (gd.width, gd.height))
                    for ds in (dd, ld, md))
        if not align:
            raise ValueError(f"grid/DEM/label/T6 alignment mismatch for {event_date}")
        if not coverage.any():
            raise ValueError(f"no covered event-depth cells for {event_date}")

    if draws < 20 or draws > 65535:
        raise ValueError("Monte Carlo draws must be between 20 and 65535")
    components, n_components = label(coverage, structure=np.ones((3, 3), dtype=np.uint8))
    edge = coverage & ~binary_erosion(coverage, structure=np.ones((3, 3), dtype=bool), border_value=0)
    edge_idx = np.flatnonzero(edge)
    edge_comp = components.ravel()[edge_idx]
    order = np.argsort(edge_comp, kind="stable")
    sorted_edge_idx = edge_idx[order]
    sorted_comp = edge_comp[order]
    counts = np.bincount(sorted_comp, minlength=n_components + 1)
    split_points = np.cumsum(counts[1:-1])
    edge_groups = np.split(sorted_edge_idx, split_points)
    valid_idx = np.flatnonzero(coverage)
    valid_comp = components.ravel()[valid_idx]
    dem_valid = dem.ravel()[valid_idx].astype(np.float64)
    depth_base = mean.ravel()[valid_idx].astype(np.float64)

    # Demonstrate the distinction between a common vertical datum offset and spatial error.
    common_bias_max = cancel_common_bias(dem, coverage, 4.0)
    # Relative-error scenario: an assumed 20% multiplicative depth error field, spatially
    # correlated over sigma=10 cells (300 m); this is a sensitivity scenario, not a sensor claim.
    # Absolute scenario: spatially varying DEM elevation error bounded at +/-4 m at its 95th
    # absolute percentile; water-surface edge medians are recomputed per component/draw.
    class_counts = {"relative_20pct": np.zeros((4, valid_idx.size), dtype=np.uint16),
                    "absolute_dem_pm4m": np.zeros((4, valid_idx.size), dtype=np.uint16)}
    depth_draws = {k: np.empty((draws, valid_idx.size), dtype=np.float32) for k in class_counts}
    field_q95_relative = []
    for i in range(draws):
        rel_field = _correlated_error(dem.shape, coverage, rng, 1.0)
        rel_factor = np.maximum(0.0, 1.0 + 0.20 * rel_field.ravel()[valid_idx])
        relative_depth = np.maximum(0.0, depth_base * rel_factor)
        relative_class = depth_classes(relative_depth)
        for c in range(4):
            class_counts["relative_20pct"][c] += (relative_class == c)
        depth_draws["relative_20pct"][i] = relative_depth

        abs_field = _correlated_error(dem.shape, cma & dem_ok, rng, 4.0)
        abs_flat = abs_field.ravel()
        component_surface = np.full(n_components + 1, np.nan, dtype=np.float64)
        for cid, group_idx in enumerate(edge_groups, start=1):
            if group_idx.size:
                component_surface[cid] = np.median(dem.ravel()[group_idx] + abs_flat[group_idx])
        abs_depth = np.maximum(0.0, component_surface[valid_comp] - (dem_valid + abs_flat[valid_idx]))
        abs_class = depth_classes(abs_depth)
        for c in range(4):
            class_counts["absolute_dem_pm4m"][c] += (abs_class == c)
        depth_draws["absolute_dem_pm4m"][i] = abs_depth.astype(np.float32)

    tags = {"status": "DERIVED_SCENARIO_CALIBRATION_PROXY_NOT_ROUTING_INPUT", "event_date": event_date,
            "source_depth": mean_path.relative_to(ROOT).as_posix(), "grid": "EPSG:32644; master 30m grid",
            "coverage": "valid only where existing T6 mean depth is not NoData; outside coverage remains NoData",
            "random_seed": "20261025", "draws": str(draws), "spatial_error_correlation_sigma_cells": "10",
            "spatial_error_correlation_approx_m": "300"}
    summary = {"event_date": event_date, "source_rasterized_cells": int(label_flood.sum()),
               "covered_depth_cells": int(coverage.sum()), "coverage_fraction": float(coverage.sum()/label_flood.sum()),
               "components_in_covered_extent": int(n_components), "draws": draws,
               "common_absolute_bias_test": {"offset_m": 4.0, "maximum_depth_difference_m": common_bias_max,
                   "interpretation": "a spatially uniform DEM offset cancels exactly because both edge water-surface estimate and cell DEM receive the same offset"},
               "scenario_parameters": {"relative_20pct": {"interpretation": "depth multiplied by max(0,1+spatial_error); assumed q95 fractional magnitude 20%", "correlation_sigma_cells": 10, "correlation_approx_m": 300},
                   "absolute_dem_pm4m": {"interpretation": "spatial DEM error normalized to +/-4m q95 absolute magnitude; water-surface edge median recomputed per component", "correlation_sigma_cells": 10, "correlation_approx_m": 300}},
               "scenarios": {}}
    for scenario, counts_arr in class_counts.items():
        scenario_dir = out_dir / scenario
        scenario_dir.mkdir(parents=True, exist_ok=True)
        probs = counts_arr.astype(np.float32) / float(draws)
        # Summaries per scenario and class cover only cells with depth data.
        class_names = ("lt_0p15m", "0p15_to_0p30m", "0p30_to_0p50m", "gte_0p50m")
        for c, name in enumerate(class_names):
            full = np.full(mean.shape, NODATA, dtype=np.float32)
            full.ravel()[valid_idx] = probs[c]
            _write(scenario_dir / f"prob_{name}_{event_date}.tif", full, profile,
                   f"Probability depth is {name.replace('_',' ')}; scenario proxy, not routing input", tags | {"scenario": scenario, "depth_class_m": str(CLASSES[c])})
        quant = np.quantile(depth_draws[scenario], [0.05, 0.95], axis=0).astype(np.float32)
        for qi, key in enumerate(("depth_p05", "depth_p95")):
            full = np.full(mean.shape, NODATA, dtype=np.float32)
            full.ravel()[valid_idx] = quant[qi]
            _write(scenario_dir / f"{key}_{event_date}.tif", full, profile,
                   f"Scenario ensemble {key} depth in metres; calibration proxy, not routing input", tags | {"scenario": scenario})
        scenario_summary = {"class_cell_mean_probability": {name: float(probs[c].mean()) for c, name in enumerate(class_names)},
                            "class_probability_sum_min": float(probs.sum(axis=0).min()),
                            "class_probability_sum_max": float(probs.sum(axis=0).max()),
                            "ensemble_depth_p05_m": float(quant[0].mean()), "ensemble_depth_p95_m": float(quant[1].mean())}
        summary["scenarios"][scenario] = scenario_summary

    mask = np.full(mean.shape, 255, dtype=np.uint8)
    mask[coverage] = 1
    mask_path = out_dir / f"coverage_{event_date}.tif"
    if mask_path.exists():
        raise FileExistsError(f"refusing to overwrite scenario output: {mask_path}")
    mprofile = profile.copy(); mprofile.update(dtype="uint8", count=1, nodata=255, compress="deflate", tiled=True)
    with rasterio.open(mask_path, "w", **mprofile) as dst:
        dst.write(mask, 1); dst.set_band_description(1, "1=covered by source T6 depth; 255=not assessed"); dst.update_tags(**tags)
    return summary


def run(root: Path = ROOT, draws: int = 100) -> dict:
    global GRID, DEM, LABELS, T6, OUT, SUMMARY
    GRID = root / "data/processed/grid/cma_mask.tif"
    DEM = root / "data/processed/terrain_cleaned/cleaned_elevation_m.tif"
    LABELS = root / "data/processed/labels_inspection"
    T6 = root / "data/features/depth/batch1_v1"
    OUT = root / "data/features/depth_scenarios/cr003_v1"
    SUMMARY = root / "docs/DEPTH_UNCERTAINTY_SCENARIOS.json"
    if OUT.exists() and any(OUT.rglob("*")):
        raise FileExistsError(f"refusing to reuse non-empty scenario output folder: {OUT}")
    if SUMMARY.exists():
        raise FileExistsError(f"refusing to overwrite summary: {SUMMARY}")
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261025)
    results = [process_event(date, draws, rng, OUT) for date in DATES]
    result = {"status": "DERIVED scenario calibration proxies; not measured depth, calibrated prediction or routing input",
              "random_seed": 20261025, "spatial_correlation": {"filter": "Gaussian-smoothed white noise", "sigma_cells": 10, "approximate_range_m": 300},
              "depth_classes_m": ["<0.15", "0.15 to <0.30", "0.30 to <0.50", ">=0.50"], "events": results}
    SUMMARY.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draws", type=int, default=100)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = run(args.root, args.draws)
    print(json.dumps({"events": [{"date": e["event_date"], "covered_cells": e["covered_depth_cells"], "common_bias_test": e["common_absolute_bias_test"], "scenarios": e["scenarios"]} for e in result["events"]]}, indent=2))


if __name__ == "__main__":
    main()
