"""Run versioned, explicitly hindcast rainfall scenarios through the A06 solver."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from pipelines.phase12 import simulate as a06

ROOT = a06.ROOT
OUTPUT = ROOT / "data/features/forecast/batch2_v1"
REPORT = ROOT / "docs/PHASE11_FORECAST_BATCH2.md"
HORIZONS = (6, 12, 24, 48, 72)
EVENTS = {
    "2015-12-02": {"end": date(2015, 12, 2), "note": "IMERG peak 2015-12-01; no accepted December flood extent"},
    "2021-11-13": {"end": date(2021, 11, 13), "note": "NRSC PDF map is not an accepted raster reference"},
    "2023-12-04": {"end": date(2023, 12, 4), "note": "NDEM PDF map is preliminary; no accepted raster reference"},
}


def distribute_daily_total(shape: np.ndarray, total_mm: float) -> np.ndarray:
    """Scale a 24-value nonnegative hourly shape to one daily IMERG total."""
    shape = np.maximum(np.asarray(shape, dtype=np.float64), 0)
    if shape.shape != (24,):
        raise ValueError("daily ERA5 profile must contain exactly 24 hourly values")
    if not np.isfinite(shape).all() or not np.isfinite(total_mm) or total_mm < 0:
        raise ValueError("rainfall inputs must be finite and daily total nonnegative")
    mass = float(shape.sum())
    if mass == 0:
        if total_mm > 0:
            raise ValueError("cannot scale a zero ERA5 hourly profile to positive IMERG rainfall")
        return np.zeros(24, dtype=np.float64)
    return shape * (float(total_mm) / mass)


def make_persistence_profile(previous_day: np.ndarray) -> np.ndarray:
    """Repeat the last observed UTC-day rainfall profile over a 72 h baseline."""
    prev = np.asarray(previous_day, dtype=np.float64)
    if prev.shape != (24,) or not np.isfinite(prev).all() or (prev < 0).any():
        raise ValueError("persistence input must be 24 finite nonnegative hourly values")
    return np.tile(prev, 3)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_rainfall_sources():
    imerg = a06.rainfall_daily()
    era = pd.read_csv(ROOT / "data/features/weather/era5_event_hourly_features.csv",
                      usecols=["timestamp_utc", "precipitation"])
    era["timestamp_utc"] = pd.to_datetime(era.timestamp_utc, utc=True)
    era["precipitation"] = pd.to_numeric(era.precipitation, errors="coerce")
    era = era.groupby("timestamp_utc", as_index=False).precipitation.mean()
    era["utc_day"] = era.timestamp_utc.dt.strftime("%Y-%m-%d")
    days = {}
    for day, frame in era.groupby("utc_day"):
        frame = frame.sort_values("timestamp_utc")
        if len(frame) == 24 and frame.precipitation.notna().all():
            days[day] = np.maximum(frame.precipitation.to_numpy(float), 0)
    return imerg, days


def rainfall_error_quantiles(imerg: dict[str, float], era_profiles: dict[str, np.ndarray]) -> dict[str, float]:
    """Empirical matched-day daily total residuals, ERA5 minus IMERG, in mm/day."""
    residuals = [float(profile.sum() - imerg[d]) for d, profile in era_profiles.items() if d in imerg]
    if len(residuals) < 10:
        raise ValueError(f"only {len(residuals)} matched daily rainfall pairs; need at least 10")
    q = np.quantile(np.asarray(residuals), [0.10, 0.50, 0.90])
    return {"q10": float(q[0]), "q50": float(q[1]), "q90": float(q[2])}


def event_forcing(end: date, imerg: dict[str, float], era_profiles: dict[str, np.ndarray],
                  error_mm: float = 0.0) -> tuple[np.ndarray, list[dict]]:
    start = end - timedelta(days=2)
    hourly, daily_rows = [], []
    for offset in range(3):
        day = (start + timedelta(days=offset)).isoformat()
        if day not in imerg:
            raise ValueError(f"IMERG daily CMA mean missing on {day}")
        if day not in era_profiles:
            raise ValueError(f"ERA5 UTC hourly pattern missing on {day}")
        adjusted = max(0.0, float(imerg[day]) + float(error_mm))
        vals = distribute_daily_total(era_profiles[day], adjusted)
        hourly.extend(vals.tolist())
        daily_rows.append({"utc_date": day, "imerg_mm_day": float(imerg[day]),
                           "error_addition_mm_day": float(error_mm), "scenario_mm_day": adjusted,
                           "scenario_hourly_sum_mm": float(vals.sum())})
    result = np.asarray(hourly, dtype=np.float64)
    if result.shape != (72,):
        raise AssertionError("event rainfall forcing must have 72 hourly samples")
    return result, daily_rows


def scenario_forcings(end: date, imerg: dict[str, float], era_profiles: dict[str, np.ndarray],
                      error_q: dict[str, float]):
    scenarios = {}
    base, base_daily = event_forcing(end, imerg, era_profiles)
    scenarios["perfect_foresight_imerg"] = (base, {"type": "PERFECT_FORESIGHT_HINDCAST", "daily": base_daily})
    for qname, delta in error_q.items():
        forcing, daily = event_forcing(end, imerg, era_profiles, delta)
        scenarios[f"rain_error_{qname}"] = (forcing, {"type": "EMPIRICAL_SOURCE_DIFFERENCE_SCENARIO", "residual_quantile": qname,
                                                       "daily_residual_addition_mm": delta, "daily": daily})
    start = end - timedelta(days=2)
    prev_day = (start - timedelta(days=1)).isoformat()
    if prev_day not in imerg or prev_day not in era_profiles:
        raise ValueError(f"persistence antecedent day unavailable: {prev_day}")
    prev = distribute_daily_total(era_profiles[prev_day], float(imerg[prev_day]))
    scenarios["persistence_previous_day"] = (make_persistence_profile(prev), {
        "type": "PERSISTENCE_BASELINE", "repeated_observed_utc_day": prev_day,
        "daily_total_mm": float(prev.sum()), "daily_profile_mm": prev.tolist()})
    return scenarios


def run() -> dict:
    if OUTPUT.exists() and any(OUTPUT.iterdir()):
        raise FileExistsError(f"refusing to overwrite nonempty output: {OUTPUT.relative_to(ROOT)}")
    if REPORT.exists():
        raise FileExistsError(f"refusing to overwrite report: {REPORT.relative_to(ROOT)}")
    tic = time.perf_counter()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    imerg, era_profiles = read_rainfall_sources()
    error_q = rainfall_error_quantiles(imerg, era_profiles)
    data = a06.load_static()
    members = a06.parameter_members()
    # Existing A06 assumptions and deterministic parameter members are reused.
    input_paths = [ROOT / "docs/RAIN_SOURCES_COMPARISON.md",
                   ROOT / "data/features/weather/era5_event_hourly_features.csv",
                   ROOT / "data/processed/terrain_cleaned/cleaned_elevation_m.tif",
                   ROOT / "data/features/landcover/worldcover_2021_class.tif",
                   ROOT / "data/features/hydrology/chennai_waterways.gpkg",
                   ROOT / "data/features/static/cell_table.parquet",
                   ROOT / "data/features/predictions/labels_nov2015.parquet"]
    event_results = {}
    for event_name, meta in EVENTS.items():
        scenarios = scenario_forcings(meta["end"], imerg, era_profiles, error_q)
        event_results[event_name] = {"window_start_utc": (meta["end"] - timedelta(days=2)).isoformat() + "T00:00:00Z",
                                     "window_end_utc": meta["end"].isoformat() + "T23:00:00Z",
                                     "reference_note": meta["note"], "scenarios": {}}
        for scenario_name, (rain, provenance) in scenarios.items():
            print(f"{event_name} {scenario_name}: starting {len(members)} members", flush=True)
            ensemble = np.full((len(members), len(HORIZONS), *data["z"].shape), np.nan, dtype=np.float32)
            run_records = []
            for member_ix, member in enumerate(members):
                t0 = time.perf_counter()
                states, diag, steps = a06.simulate(data["z"], data["active"], data["drain"],
                    data["mann"] * member.manning_multiplier, data["porosity"],
                    a06.infiltration_rate(data["landcover"], member.infiltration_multiplier), rain,
                    a06.CELL_M)
                if not np.isfinite(states).all() or states.min() < -1e-6:
                    raise RuntimeError(f"nonfinite or negative depth for {event_name}/{scenario_name}/member {member.member_id}")
                if diag["mass_balance_relative_error"] > .01:
                    raise RuntimeError(f"mass balance >1% for {event_name}/{scenario_name}/member {member.member_id}: {diag['mass_balance_relative_error']:.6g}")
                for hi, hours in enumerate(HORIZONS):
                    ensemble[member_ix, hi] = states[hours - 1]
                run_records.append({"member_id": member.member_id, "manning_multiplier": member.manning_multiplier,
                                    "infiltration_multiplier": member.infiltration_multiplier, "steps": steps,
                                    **diag, "runtime_seconds": time.perf_counter() - t0})
                if member_ix in (4, 9, 14, 19):
                    print(f"  member {member.member_id}/{len(members)} done", flush=True)
            case_dir = OUTPUT / event_name / scenario_name
            case_dir.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(case_dir / "depth_members_by_horizon_DERIVED.npz",
                depth_m=ensemble, horizons_hours=np.asarray(HORIZONS, dtype=np.int16),
                member_ids=np.asarray([m.member_id for m in members]), seed=np.int64(a06.SEED))
            horizon_stats = []
            for hi, hours in enumerate(HORIZONS):
                sample = ensemble[:, hi]
                for qname, qval in (("p05", 5), ("p50", 50), ("p95", 95)):
                    values = np.percentile(sample, qval, axis=0)
                    values = np.where(data["eligible"], values, np.nan)
                    a06.write_tif(case_dir / f"depth_lead{hours:02d}h_{qname}_DERIVED.tif", values,
                                  data["transform"], data["crs"])
                mean_depth = np.mean(sample, axis=0)
                mean_valid = mean_depth[data["eligible"]]
                horizon_stats.append({"lead_hours": hours, "eligible_cells": int(len(mean_valid)),
                    "mean_depth_m": float(mean_valid.mean()), "p95_cell_depth_m": float(np.quantile(mean_valid, .95)),
                    "area_ge_0.10m_km2": float(np.sum((mean_depth >= .10) & data["eligible"]) * (a06.CELL_M**2) / 1e6),
                    "area_ge_0.30m_km2": float(np.sum((mean_depth >= .30) & data["eligible"]) * (a06.CELL_M**2) / 1e6)})
            event_results[event_name]["scenarios"][scenario_name] = {
                "rainfall_provenance": provenance, "hourly_rainfall_mm": rain.tolist(),
                "total_rainfall_mm": float(rain.sum()), "member_count": len(members),
                "member_runs": run_records, "horizons": horizon_stats,
                "output_directory": str(case_dir.relative_to(ROOT)),
            }
            print(f"{event_name} {scenario_name}: complete", flush=True)
    summary = {
        "name": "A05 historical forecast/hindcast scenarios through A06",
        "status": "DERIVED_HINDCAST_SCENARIOS_NOT_FORECAST_SKILL",
        "seed": a06.SEED, "device": "CPU NumPy; A06 solver is NumPy and CUDA unavailable",
        "grid_cell_size_m": a06.CELL_M, "crs": str(data["crs"]), "model_cells": int(data["eligible"].sum()),
        "horizons_hours": list(HORIZONS), "parameter_members": [m.__dict__ for m in members],
        "rainfall_error_empirical_era5_minus_imerg_mm_day_quantiles": error_q,
        "rainfall_error_source": "Matched UTC daily ERA5 point-mean totals minus IMERG daily CMA means in the local Phase 3 rainfall comparison; descriptive product disagreement, not calibrated forecast errors.",
        "events": event_results,
        "validation": {"archived_nwp_forecasts": "not available", "observed_depth_at_lead_times": "not available",
                       "2015_unosat": "Nov 12 and Nov 24 map extents do not validate the Dec 1-2 peak nor each hourly lead",
                       "2021_nrsc": "PDF only; not a georeferenced accepted raster reference",
                       "2023_ndem": "PDF map preliminary; not an accepted raster reference",
                       "interpretation": "Perfect-foresight and persistence outputs are scenario contrasts. No operational forecast skill or hydraulic accuracy is claimed."},
        "a06_assumptions_reused": ["600 m grid", "20 Manning/infiltration parameter members", "WorldCover roughness/infiltration defaults", "zero-stage open-water and mapped-waterway sinks", "no storm-drain network", "no external catchment inflow", "GLO-30 is a surface model, not a building DSM"],
        "input_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in input_paths},
        "runtime_seconds": time.perf_counter() - tic,
    }
    (OUTPUT / "forecast_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    summary = run()
    print(json.dumps({"status": summary["status"], "runtime_seconds": summary["runtime_seconds"],
                      "events": {k: list(v["scenarios"]) for k, v in summary["events"].items()},
                      "horizons_hours": summary["horizons_hours"]}, indent=2))


if __name__ == "__main__":
    main()
