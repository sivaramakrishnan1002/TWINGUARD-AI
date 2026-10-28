"""Build separate proxy-free descriptive A11 outputs from frozen A07/A10 evidence.

These are research summaries. They are not vulnerability or official priority
zones, operational guidance, or independently validated hazard estimates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import rasterio
from rasterio.transform import Affine

ROOT = Path(__file__).resolve().parents[2]
A07 = ROOT / "data/features/impact/batch2_v4_contract"
A10 = ROOT / "data/features/decision/shelters/batch2_v3"
DEFAULT_OUTPUT = ROOT / "data/features/decision/priority_zones/batch2_v1/revision_2"
GRID = {"width": 69, "height": 88, "cell_size_m": 600, "crs": "EPSG:32644",
        "transform": [600.0, 0.0, 390000.0, 0.0, -600.0, 1471620.0]}
DEFAULT_THRESHOLD_M = 0.30
HAZARD_FIELDS = ["event_key", "scenario_key", "horizon_hours", "valid_at_utc",
                 "grid_cell_id", "threshold_m", "passability_probability",
                 "depth_mean_m", "depth_member_p05_m", "depth_member_p95_m",
                 "depth_valid_member_count", "member_count", "road_edge_count",
                 "road_length_m", "qc", "flood_screen_probability"]
FORBIDDEN = ("vulnerab", "composite", "weighted_score", "rank", "priority_score")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_records(a07_root: Path = A07) -> list[dict[str, Any]]:
    path = a07_root / "impact_results.jsonl"
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def hazard_cells(frame: pd.DataFrame, threshold_m: float = DEFAULT_THRESHOLD_M) -> pd.DataFrame:
    """Select A07's default screening threshold and expose its exceedance share."""
    required = {"event_key", "scenario_key", "valid_at_utc", "horizon_hours", "grid_cell_id",
                "threshold_m", "passability_probability", "depth_mean_m", "depth_member_p05_m",
                "depth_member_p95_m", "depth_valid_member_count", "member_count", "qc"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"A07 cell impact missing columns: {sorted(missing)}")
    selected = frame.loc[np.isclose(frame.threshold_m, threshold_m)].copy()
    if selected.empty:
        raise ValueError(f"A07 threshold {threshold_m} m has no rows")
    selected["flood_screen_probability"] = 1.0 - selected["passability_probability"]
    return selected


def validate_products(hazard: pd.DataFrame, exposures: pd.DataFrame,
                      access: pd.DataFrame, allocations: pd.DataFrame) -> None:
    for name, table in (("hazard", hazard), ("population exposure", exposures),
                        ("facility access loss", access), ("capacity allocation", allocations)):
        bad = [column for column in table.columns
               if any(term in column.lower() for term in FORBIDDEN)]
        if bad:
            raise ValueError(f"{name} includes forbidden composite/vulnerability fields: {bad}")
    if hazard.duplicated(["event_key", "scenario_key", "horizon_hours", "grid_cell_id"]).any():
        raise ValueError("hazard cell key is not unique")
    if not hazard.flood_screen_probability.dropna().between(0, 1).all():
        raise ValueError("flood_screen_probability outside [0,1]")
    if not hazard.passability_probability.dropna().between(0, 1).all():
        raise ValueError("passability_probability outside [0,1]")
    if not exposures.population_exposure_status.isin(["AVAILABLE", "PARTIAL", "UNAVAILABLE"]).all():
        raise ValueError("unknown population exposure status")
    if not {"population_nodata_30m_cells", "population_coverage_fraction"}.issubset(exposures.columns):
        raise ValueError("population exposure must expose NoData and coverage explicitly")
    if exposures.population_nodata_30m_cells.isna().any() or (exposures.population_nodata_30m_cells < 0).any():
        raise ValueError("population NoData count must be known and nonnegative")
    if not exposures.population_coverage_fraction.dropna().between(0, 1).all():
        raise ValueError("population coverage fraction outside [0,1]")
    if (((exposures.population_nodata_30m_cells > 0) &
         (exposures.population_exposure_status == "AVAILABLE")).any()):
        raise ValueError("population with source NoData cannot be marked fully available")
    if (access[["facility_count", "reachable_count", "unreachable_count", "unassessed_count"]]
            .dropna().lt(0).any().any()):
        raise ValueError("negative facility count")
    if not access.access_loss_fraction.dropna().between(0, 1).all():
        raise ValueError("access loss fraction outside [0,1]")
    if not allocations.qc_flags.map(lambda flags: isinstance(flags, (list, tuple, np.ndarray))).all():
        raise ValueError("A10 allocation QC flags missing")


def _records_to_summaries(records: list[dict[str, Any]], input_hash: str
                          ) -> tuple[pd.DataFrame, pd.DataFrame]:
    exposure_rows: list[dict[str, Any]] = []
    access_rows: list[dict[str, Any]] = []
    for record in records:
        event = record["event"]
        key = {"event_key": event["event_key"], "scenario_key": record["scenario_key"],
               "valid_at_utc": record["valid_at_utc"],
               "horizon_hours": int(record["result_id"].rsplit("lead", 1)[1][:-1])}
        metric = record["metrics"]["population_exposed_people"]
        population_coverage = record["coverage"]["population"]
        exposure_rows.append({**key, "known_population_exposed_mean_people": metric.get("mean"),
                              "known_population_exposed_p05_people": metric.get("p05"),
                              "known_population_exposed_p50_people": metric.get("p50"),
                              "known_population_exposed_p95_people": metric.get("p95"),
                              "population_exposure_status": metric["status"],
                              "population_exposure_unit": metric["unit"],
                              "exposure_threshold_m": record["thresholds"]["population_exposure_threshold_m"],
                              "population_nodata_30m_cells": population_coverage["nodata_count"],
                              "population_coverage_fraction": population_coverage["fraction_assessed"],
                              "coverage_population": population_coverage,
                              "hazard_coverage_fraction": record["coverage"]["hazard_grid"]["fraction_assessed"],
                              "coverage_hazard_grid": record["coverage"]["hazard_grid"],
                              "uncertainty": record["uncertainty"], "qc_flags": record["qc_flags"],
                              "source_run_id": record["run_id"], "source_run_version": record["run_version"],
                              "source_sha256": input_hash,
                              "interpretation": "Known WorldPop model estimate exposed under A07 simulated depth screen; NoData is unknown, not zero."})
        for item in record["facility_access_by_category"]:
            base = item.get("baseline_core_count") or {}
            reachable = item.get("reachable_count_distribution") or {}
            unreachable = item.get("unreachable_count_distribution") or {}
            access_rows.append({**key, "category": item["category"],
                                "facility_count": item.get("facility_count"),
                                "baseline_core_count_mean": base.get("mean"),
                                "reachable_count": item.get("reachable_count"),
                                "reachable_count_mean": reachable.get("mean"),
                                "unreachable_count": item.get("unreachable_count"),
                                "unreachable_count_mean": unreachable.get("mean"),
                                "unassessed_count": item.get("unassessed_count"),
                                "access_loss_fraction": item.get("access_loss_fraction"),
                                "coverage_fraction": item.get("coverage_fraction_mean"),
                                "ensemble_member_count": base.get("member_count"),
                                "uncertainty_interpretation": base.get("interpretation"),
                                "access_method": "A07 coarse 600 m connected-component cascade; not OD routing",
                                "source_run_id": record["run_id"], "source_run_version": record["run_version"],
                                "source_sha256": input_hash,
                                "qc_flags": record["qc_flags"]})
    return pd.DataFrame(exposure_rows), pd.DataFrame(access_rows)


def _write_hazard_rasters(hazard: pd.DataFrame, out: Path, source_sha256: str) -> list[str]:
    names: list[str] = []
    transform = Affine(*GRID["transform"][:6])
    bands = ["depth_mean_m", "depth_member_p05_m", "depth_member_p95_m",
             "flood_screen_probability", "depth_valid_member_count"]
    for key, group in hazard.groupby(["event_key", "scenario_key", "horizon_hours", "valid_at_utc"], sort=True):
        arrays = {band: np.full((GRID["height"], GRID["width"]), -9999, dtype=np.float32)
                  for band in bands}
        for row in group.itertuples(index=False):
            cid = int(row.grid_cell_id)
            if cid < 0 or cid >= GRID["width"] * GRID["height"]:
                raise ValueError(f"grid_cell_id outside A06 grid: {cid}")
            r, c = divmod(cid, GRID["width"])
            for band in bands:
                value = getattr(row, band)
                if pd.notna(value):
                    arrays[band][r, c] = float(value)
        event, scenario, horizon, _ = key
        safe_scenario = str(scenario).replace("/", "_")
        name = f"hazard_{event}_{safe_scenario}_lead{int(horizon):02d}h.tif"
        path = out / name
        with rasterio.open(path, "w", driver="GTiff", height=GRID["height"], width=GRID["width"],
                           count=len(bands), dtype="float32", crs=GRID["crs"], transform=transform,
                           nodata=-9999.0, compress="deflate", predictor=3) as ds:
            for i, band in enumerate(bands, 1):
                ds.write(arrays[band], i)
                ds.set_band_description(i, band)
            ds.update_tags(STATUS="DERIVED_SIMULATED_DESCRIPTIVE_HAZARD_NOT_LIVE",
                          CELL_SIZE_M="600", THRESHOLD_M=str(DEFAULT_THRESHOLD_M),
                          SOURCE_RUN_VERSION="A07 batch2_v4_contract",
                          SOURCE_CELL_IMPACT_SHA256=source_sha256,
                          FLOOD_SCREEN_PROBABILITY="1 - A07 passability_probability; ensemble fraction at or above assumed threshold",
                          MEMBER_QUANTILES="descriptive ensemble spread, not calibrated statistical intervals",
                          NODATA="outside A07 eligible simulation cells or unassessed; not dry")
        names.append(name)
    return names


def build(output: Path = DEFAULT_OUTPUT, a07_root: Path = A07, a10_root: Path = A10) -> dict[str, Any]:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    a07_cell = a07_root / "cell_impact.parquet"
    a07_json = a07_root / "impact_results.jsonl"
    a07_summary = a07_root / "run_summary.json"
    a10_cases = a10_root / "allocation_cases.parquet"
    inputs = {"a07_cell_impact": sha256(a07_cell), "a07_impact_results": sha256(a07_json),
              "a07_run_summary": sha256(a07_summary), "a10_allocation_cases": sha256(a10_cases)}
    cell_frame = pq.read_table(a07_cell).to_pandas()
    hazard = hazard_cells(cell_frame)
    hazard["source_run_id"] = 7004
    hazard["source_run_version"] = "batch2_v4_contract"
    hazard["source_sha256"] = inputs["a07_cell_impact"]
    records = load_records(a07_root)
    exposure, access = _records_to_summaries(records, inputs["a07_impact_results"])
    allocations = pq.read_table(a10_cases).to_pandas()
    allocations["source_run_version"] = "batch2_v3"
    allocations["source_sha256"] = inputs["a10_allocation_cases"]
    validate_products(hazard, exposure, access, allocations)

    hazard_path = output / "hazard_cells.parquet"
    exposure_path = output / "population_exposure_summary.parquet"
    access_path = output / "facility_access_loss_summary.parquet"
    allocation_path = output / "capacity_allocation_context.parquet"
    hazard.to_parquet(hazard_path, index=False)
    exposure.to_parquet(exposure_path, index=False)
    access.to_parquet(access_path, index=False)
    allocations.to_parquet(allocation_path, index=False)
    rasters = _write_hazard_rasters(hazard, output, inputs["a07_cell_impact"])
    outputs = {p.name: {"sha256": sha256(p), "bytes": p.stat().st_size}
               for p in [hazard_path, exposure_path, access_path, allocation_path,
                         *(output / name for name in rasters)]}
    summary = {"schema_id": "twinguard.a11_proxy_free_outputs", "schema_version": "1.0",
               "status": "DERIVED_SIMULATED_DESCRIPTIVE_NOT_LIVE_NOT_VULNERABILITY",
               "generated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
               "grid": GRID, "default_screening_threshold_m": DEFAULT_THRESHOLD_M,
               "case_count": int(hazard.groupby(["event_key", "scenario_key", "horizon_hours"]).ngroups),
               "hazard_cell_rows": len(hazard), "population_exposure_summary_rows": len(exposure),
               "facility_access_loss_category_rows": len(access), "a10_capacity_allocation_rows": len(allocations),
               "raster_count": len(rasters), "raster_files": rasters,
               "input_sha256": inputs, "outputs": outputs,
               "indicators_are_separate": True,
               "forbidden_outputs_created": False,
               "population_semantics": "WorldPop model estimate; NoData is unknown, not zero.",
               "hazard_semantics": "A07 600 m simulated depths; threshold exceedance share is descriptive ensemble fraction.",
               "facility_access_semantics": "A07 coarse connected-component access proxy; A10 capacity allocation retained separately.",
               "uncertainty": "A07 ensemble spread is descriptive and not calibrated statistical uncertainty.",
               "limitations": ["A05 hindcasts/scenarios are not operational forecast skill.",
                               "A06 is a coarse assumption-based 600 m simulation without independent hydraulic validation.",
                               "A07 facility access is not OD routing, facility operation, or safe access.",
                               "A10 shelter capacities are hypothetical; schools and colleges are candidate shelters by assumption.",
                               "No vulnerability proxy, composite score, weights, ranking, or official priority designation is produced."]}
    manifest = output / "run_manifest.json"
    manifest.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return summary


def verify(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
    expected = {"hazard_cells.parquet", "population_exposure_summary.parquet",
                "facility_access_loss_summary.parquet", "capacity_allocation_context.parquet"}
    if not expected.issubset({p.name for p in output.iterdir()}):
        raise ValueError("one or more required A11 products are missing")
    if manifest.get("status") != "DERIVED_SIMULATED_DESCRIPTIVE_NOT_LIVE_NOT_VULNERABILITY":
        raise ValueError("A11 output status label is invalid")
    if manifest.get("indicators_are_separate") is not True or manifest.get("forbidden_outputs_created") is not False:
        raise ValueError("A11 separation/forbidden-output declaration invalid")
    hazard, exposure, access, allocations = [pd.read_parquet(output / name) for name in
        ("hazard_cells.parquet", "population_exposure_summary.parquet",
         "facility_access_loss_summary.parquet", "capacity_allocation_context.parquet")]
    validate_products(hazard, exposure, access, allocations)
    if len(hazard) != manifest["hazard_cell_rows"] or len(exposure) != manifest["population_exposure_summary_rows"]:
        raise ValueError("A11 manifest row counts disagree")
    if len(access) != manifest["facility_access_loss_category_rows"] or len(allocations) != manifest["a10_capacity_allocation_rows"]:
        raise ValueError("A11 manifest row counts disagree")
    for filename, detail in manifest["outputs"].items():
        path = output / filename
        if not path.is_file() or sha256(path) != detail["sha256"] or path.stat().st_size != detail["bytes"]:
            raise ValueError(f"A11 output hash/size mismatch: {filename}")
    for filename in manifest["raster_files"]:
        with rasterio.open(output / filename) as ds:
            if (ds.width, ds.height, ds.crs.to_string(), ds.transform) != (
                    GRID["width"], GRID["height"], GRID["crs"], Affine(*GRID["transform"])):
                raise ValueError(f"A11 hazard raster grid mismatch: {filename}")
            if ds.count != 5 or ds.nodata != -9999.0:
                raise ValueError(f"A11 hazard raster bands/nodata mismatch: {filename}")
    return {"status": "ok", "hazard_cell_rows": len(hazard), "exposure_rows": len(exposure),
            "access_rows": len(access), "allocation_rows": len(allocations),
            "rasters": len(manifest["raster_files"])}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    output = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    result = verify(output) if args.verify_only else build(output)
    compact = {key: result[key] for key in ("schema_id", "schema_version", "status", "case_count",
               "hazard_cell_rows", "population_exposure_summary_rows",
               "facility_access_loss_category_rows", "a10_capacity_allocation_rows", "raster_count")
               if key in result}
    if "status" in result and result.get("status") == "ok":
        compact = result
    print(json.dumps(compact, indent=2))


if __name__ == "__main__":
    main()
