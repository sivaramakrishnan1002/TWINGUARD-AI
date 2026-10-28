"""Build a deterministic, read-only index of existing A05/A06 scenario rasters."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import rasterio

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "data/features/visualization3d/batch2_v1/manifest.json"
FORECAST_SUMMARY = ROOT / "data/features/forecast/batch2_v1/forecast_summary.json"
SIMULATION_SUMMARY = ROOT / "data/features/simulation/batch2_v1/simulation_summary.json"
HORIZONS = (6, 12, 24, 48, 72)
BANDS = ("p05", "p50", "p95")
GRID = {"crs": "EPSG:32644", "width": 69, "height": 88,
        "pixel_size_m": [600.0, 600.0],
        "affine_transform": [600.0, 0.0, 390000.0, 0.0, -600.0, 1471620.0]}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() != timedelta(0):
        raise ValueError(f"Expected UTC timestamp, got {value}")
    return parsed.astimezone(timezone.utc)


def raster_record(path: Path, expected_units: str = "m") -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"missing source raster: {rel(path)}")
    with rasterio.open(path) as dataset:
        grid = {"crs": dataset.crs.to_string() if dataset.crs else None,
                "width": dataset.width, "height": dataset.height,
                "pixel_size_m": [abs(float(dataset.transform.a)), abs(float(dataset.transform.e))],
                "affine_transform": [float(dataset.transform.a), float(dataset.transform.b),
                                     float(dataset.transform.c), float(dataset.transform.d),
                                     float(dataset.transform.e), float(dataset.transform.f)]}
        if (grid["crs"] != GRID["crs"] or grid["width"] != GRID["width"]
                or grid["height"] != GRID["height"]
                or grid["pixel_size_m"] != GRID["pixel_size_m"]
                or grid["affine_transform"] != GRID["affine_transform"]):
            raise ValueError(f"grid mismatch in {rel(path)}: {grid}")
        if dataset.count != 1 or dataset.dtypes != ("float32",):
            raise ValueError(f"expected one float32 band in {rel(path)}")
        if dataset.nodata != -9999.0:
            raise ValueError(f"unexpected NoData in {rel(path)}: {dataset.nodata}")
        mask = dataset.read_masks(1)
        valid_count = int((mask != 0).sum())
        nodata_count = int(mask.size - valid_count)
        tags = dataset.tags()
        band_units = dataset.units[0] if dataset.units else None
    return {"path": rel(path), "sha256": sha256(path), "size_bytes": path.stat().st_size,
            "grid": grid, "dtype": "float32", "band_units_metadata": band_units,
            "units": expected_units, "units_basis": "Phase 11/12 reports describe these depth products in metres; source TIFF unit metadata is unset.",
            "nodata_value": -9999.0,
            "nodata_meaning": tags.get("NODATA", "outside assessed CMA; not dry"),
            "valid_cell_count": valid_count, "nodata_cell_count": nodata_count,
            "source_status_tag": tags.get("STATUS")}


def input_hash_records(summary: dict[str, Any], hash_field: str) -> list[dict[str, str]]:
    records = []
    for raw_path, expected in sorted(summary[hash_field].items()):
        path = Path(raw_path)
        if not path.is_absolute():
            path = ROOT / path
        if not path.is_file():
            raise FileNotFoundError(f"declared source input missing: {raw_path}")
        actual = sha256(path)
        records.append({"path": rel(path), "expected_sha256": expected,
                        "actual_sha256": actual,
                        "status": "match" if actual == expected else "mismatch"})
    if any(row["status"] != "match" for row in records):
        raise ValueError("one or more declared A05/A06 source-input hashes no longer match")
    return records


def build_manifest(root: Path = ROOT) -> dict[str, Any]:
    global ROOT
    old_root = ROOT
    ROOT = root.resolve()
    try:
        forecast_path = ROOT / "data/features/forecast/batch2_v1/forecast_summary.json"
        simulation_path = ROOT / "data/features/simulation/batch2_v1/simulation_summary.json"
        forecast = json.loads(forecast_path.read_text(encoding="utf-8"))
        simulation = json.loads(simulation_path.read_text(encoding="utf-8"))
        if forecast.get("status") != "DERIVED_HINDCAST_SCENARIOS_NOT_FORECAST_SKILL":
            raise ValueError("unexpected A05 status")
        if simulation.get("status") != "DERIVED_ASSUMPTION_BASED_PILOT":
            raise ValueError("unexpected A06 status")
        if forecast.get("grid_cell_size_m") != 600 or simulation.get("grid_cell_size_m") != 600:
            raise ValueError("A05/A06 grid is not the registered 600 m grid")
        if forecast.get("crs") != GRID["crs"] or simulation.get("crs") != GRID["crs"]:
            raise ValueError("A05/A06 CRS differs from the registered grid")

        forecast_inputs = input_hash_records(forecast, "input_sha256")
        simulation_inputs = input_hash_records(simulation, "source_sha256")
        if len(forecast.get("parameter_members", [])) != 20 or len(simulation.get("parameters", [])) != 20:
            raise ValueError("expected 20 parameter members in each source")

        series = []
        for event_id, event in sorted(forecast["events"].items()):
            scenario_id = "perfect_foresight_imerg"
            scenario = event["scenarios"][scenario_id]
            if scenario.get("member_count") != 20:
                raise ValueError(f"unexpected member count for {event_id}/{scenario_id}")
            start = parse_utc(event["window_start_utc"])
            horizons_in_summary = {row["lead_hours"] for row in scenario["horizons"]}
            if horizons_in_summary != set(HORIZONS):
                raise ValueError(f"saved horizons differ from registered horizons: {event_id}")
            slices = []
            directory = ROOT / scenario["output_directory"]
            for lead in HORIZONS:
                valid = start + timedelta(hours=lead)
                files = {band: raster_record(directory / f"depth_lead{lead:02d}h_{band}_DERIVED.tif")
                         for band in BANDS}
                if any(row["valid_cell_count"] != 2430 for row in files.values()):
                    raise ValueError(f"unexpected valid-cell count in {event_id} lead {lead}")
                if len({row["nodata_cell_count"] for row in files.values()}) != 1:
                    raise ValueError(f"p05/p50/p95 coverage differs for {event_id} lead {lead}")
                slices.append({"lead_hours": lead,
                               "valid_time_utc": valid.isoformat(timespec="seconds").replace("+00:00", "Z"),
                               "valid_time_rule": "window_start_utc + saved lead_hours; end represents the state after that many hourly model updates",
                               "bands": files})
            series.append({"event_id": event_id, "scenario_id": scenario_id,
                           "source_mode": scenario["rainfall_provenance"]["type"],
                           "window_start_utc": event["window_start_utc"],
                           "window_end_utc_inclusive": event["window_end_utc"],
                           "member_count": 20,
                           "members": [{"member_id": row["member_id"],
                                        "manning_multiplier": row["manning_multiplier"],
                                        "infiltration_multiplier": row["infiltration_multiplier"]}
                                       for row in forecast["parameter_members"]],
                           "band_semantics": "per-cell p05/p50/p95 across the 20 A06 parameter members; parameter spread, not calibrated statistical uncertainty or confidence coverage",
                           "rainfall_semantics": "observed daily IMERG totals distributed with ERA5 hourly shape; hindsight scenario, not archived forecast or native hourly IMERG",
                           "slices": slices})

        context = []
        for event_id, event in sorted(simulation["events"].items()):
            start = datetime.fromisoformat(event_id).replace(tzinfo=timezone.utc) - timedelta(days=2)
            selected_index = int(event["peak_hour_index"])
            selected_time = start + timedelta(hours=selected_index + 1)
            for temporal_kind, suffix, valid_time, description in (
                ("selected_hour", "selected", selected_time.isoformat(timespec="seconds").replace("+00:00", "Z"),
                 "global hour maximizing ensemble-mean stored water; index is zero-based and products are saved after that hourly update"),
                ("per_cell_event_peak", "peak", None,
                 "per-cell maximum over the simulated 72-hour window; peak timing can differ by cell, so no single valid instant exists")):
                bands = {}
                for stat in ("mean", "p05", "p95"):
                    path = ROOT / "data/features/simulation/batch2_v1" / f"depth_{suffix}_{stat}_{event_id}_DERIVED.tif"
                    bands[stat] = raster_record(path)
                if any(row["valid_cell_count"] != 2430 for row in bands.values()):
                    raise ValueError(f"unexpected A06 valid-cell count for {event_id} {temporal_kind}")
                context.append({"event_id": event_id, "temporal_kind": temporal_kind,
                                "valid_time_utc": valid_time,
                                "window_start_utc": start.isoformat(timespec="seconds").replace("+00:00", "Z"),
                                "window_end_utc_inclusive": (start + timedelta(hours=71)).isoformat(timespec="seconds").replace("+00:00", "Z"),
                                "selected_hour_index_zero_based": selected_index if temporal_kind == "selected_hour" else None,
                                "time_semantics": description,
                                "bands": bands,
                                "band_semantics": "mean and p05/p95 across 20 parameter members; parameter spread only, not calibrated confidence coverage"})

        manifest = {
            "schema_version": "1.0.0",
            "status": "DERIVED_ASSUMPTION_BASED_RESEARCH_SCENARIO",
            "artifact_version": "batch2_v1",
            "grid": GRID,
            "depth_units": {"value": "m", "metadata_note": "Both source reports specify metres; inspected GeoTIFF band unit metadata is unset."},
            "nodata": {"value": -9999.0,
                       "meaning": "outside assessed CMA or otherwise unmodelled; it is unknown coverage, not dry",
                       "valid_cells_per_forecast_raster": 2430,
                       "source_raster_masks_preserved_by_reference": True},
            "time_basis": {"timezone": "UTC",
                           "valid_time_rule": "A05 saved state valid time is event window start plus the saved lead in hours. The 72 h state is at the exclusive end boundary after the final hourly update. A06 selected maps use the recorded zero-based peak_hour_index plus one update; per-cell peak maps have no single valid instant."},
            "scenario_series": series,
            "context_layers": context,
            "provenance": {
                "forecast_summary": {"path": rel(forecast_path), "sha256": sha256(forecast_path),
                                     "status": forecast["status"], "seed": forecast["seed"],
                                     "device": forecast["device"]},
                "simulation_summary": {"path": rel(simulation_path), "sha256": sha256(simulation_path),
                                       "status": simulation["status"], "seed": simulation["seed"],
                                       "runtime_seconds_total": simulation["runtime_seconds_total"]},
                "declared_input_hashes": [{"task": "A05", **row} for row in forecast_inputs]
                                        + [{"task": "A06", **row} for row in simulation_inputs],
                "source_hash_status": "all_declared_A05_A06_input_hashes_match_current_files"},
            "presentation_policy": "Interpolation between saved times, if later used for animation, is presentation-only. Do not change depth values, publish interpolated quantitative fields, or imply resolution finer than 600 m.",
            "limitations": [
                "Assumption-based research scenario only: not observed water and not validated hydraulic truth; it is not an operational forecast, safe evacuation guidance, or emergency advice.",
                "The 600 m source grid and source coverage are preserved; no street-level upscaling, invented intermediate depth times, or building water levels are provided.",
                "A05 perfect-foresight IMERG is a hindsight scenario; rainfall is daily IMERG distributed using an ERA5 hourly shape. Hindcasts do not establish operational forecast skill.",
                "A05/A06 p05/p50/p95 or mean fields describe spread/statistics over parameter members and are not calibrated confidence coverage.",
                "Depth values are documented as metres by source reports, but source GeoTIFF band unit metadata is unset.",
                "GLO-30 is a surface model, not bare-earth terrain or a building DSM; no building water levels are inferred.",
                "A06 November 2015 selected/peak summaries are temporal context only and do not validate December event windows." ]}
        validate_manifest(manifest, ROOT)
        return manifest
    finally:
        ROOT = old_root


def validate_manifest(manifest: dict[str, Any], root: Path = ROOT) -> None:
    schema_path = root / "pipelines/floodviz3d/manifest.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    required_schema_fields = {"schema_version", "status", "grid", "depth_units", "nodata",
                              "time_basis", "scenario_series", "context_layers", "provenance",
                              "presentation_policy", "limitations"}
    if not required_schema_fields.issubset(set(schema.get("required", []))):
        raise ValueError("manifest schema omits required contract fields")
    props = schema.get("properties", {})
    if (props.get("scenario_series", {}).get("minItems") != 3
            or props.get("context_layers", {}).get("minItems") != 4):
        raise ValueError("manifest schema cardinalities do not match the registered package")
    if manifest.get("schema_version") != "1.0.0" or manifest.get("status") != "DERIVED_ASSUMPTION_BASED_RESEARCH_SCENARIO":
        raise ValueError("unsupported manifest version or status")
    if manifest.get("grid") != GRID or manifest.get("depth_units", {}).get("value") != "m":
        raise ValueError("manifest grid or depth units invalid")
    if manifest.get("nodata", {}).get("value") != -9999.0:
        raise ValueError("manifest NoData value invalid")
    if manifest.get("time_basis", {}).get("timezone") != "UTC":
        raise ValueError("manifest timezone must be UTC")
    if len(manifest.get("scenario_series", [])) != 3:
        raise ValueError("expected three A05 event scenario series")
    expected_events = {"2015-12-02", "2021-11-13", "2023-12-04"}
    if {s["event_id"] for s in manifest["scenario_series"]} != expected_events:
        raise ValueError("unexpected A05 event IDs")
    time_keys = set()
    for series in manifest["scenario_series"]:
        if series.get("scenario_id") != "perfect_foresight_imerg" or series.get("member_count") != 20:
            raise ValueError("unexpected A05 scenario/member semantics")
        start = parse_utc(series["window_start_utc"])
        if len(series.get("slices", [])) != len(HORIZONS):
            raise ValueError("expected five saved horizons per scenario")
        for item, lead in zip(series["slices"], HORIZONS):
            if item.get("lead_hours") != lead:
                raise ValueError("unexpected quantitative lead time")
            expected_time = (start + timedelta(hours=lead)).isoformat(timespec="seconds").replace("+00:00", "Z")
            if item.get("valid_time_utc") != expected_time:
                raise ValueError("valid time does not match saved horizon")
            if set(item.get("bands", {})) != set(BANDS):
                raise ValueError("every saved time requires p05/p50/p95 references")
            for band in item["bands"].values():
                _validate_raster_reference(band, root)
                time_keys.add((series["event_id"], lead, band["path"]))
    if len(time_keys) != 45:
        raise ValueError("expected exactly 45 quantitative A05 raster references")
    if len(manifest.get("context_layers", [])) != 4:
        raise ValueError("expected four A06 context groups")
    for layer in manifest["context_layers"]:
        if layer["temporal_kind"] == "per_cell_event_peak" and layer.get("valid_time_utc") is not None:
            raise ValueError("per-cell peak must not claim one valid instant")
        if layer["temporal_kind"] == "selected_hour":
            if not layer.get("valid_time_utc") or layer.get("selected_hour_index_zero_based") is None:
                raise ValueError("selected-hour context needs its actual selected UTC time and index")
            parse_utc(layer["valid_time_utc"])
        if set(layer.get("bands", {})) != {"mean", "p05", "p95"}:
            raise ValueError("A06 context requires mean/p05/p95 references")
        for band in layer["bands"].values():
            _validate_raster_reference(band, root)
    if manifest.get("provenance", {}).get("source_hash_status") != "all_declared_A05_A06_input_hashes_match_current_files":
        raise ValueError("declared source input hash audit is not clean")
    for row in manifest["provenance"]["declared_input_hashes"]:
        if row.get("status") != "match":
            raise ValueError(f"source input hash mismatch: {row.get('path')}")
        path = root / row["path"]
        if not path.is_file() or sha256(path) != row["actual_sha256"]:
            raise ValueError(f"source input changed after manifest generation: {row.get('path')}")
    for source_key in ("forecast_summary", "simulation_summary"):
        source = manifest["provenance"][source_key]
        path = root / source["path"]
        if not path.is_file() or sha256(path) != source["sha256"]:
            raise ValueError(f"source summary changed after manifest generation: {source.get('path')}")
    limits = " ".join(manifest.get("limitations", [])).lower()
    for phrase in ("not observed water", "not validated hydraulic truth", "not calibrated confidence"):
        if phrase not in limits:
            raise ValueError(f"required limitation missing: {phrase}")


def _validate_raster_reference(record: dict[str, Any], root: Path) -> None:
    path = root / record["path"]
    if not path.is_file():
        raise FileNotFoundError(f"manifest raster reference missing: {record['path']}")
    if sha256(path) != record["sha256"]:
        raise ValueError(f"manifest raster hash mismatch: {record['path']}")
    if record["grid"] != GRID or record["nodata_value"] != -9999.0:
        raise ValueError(f"manifest raster grid/NoData mismatch: {record['path']}")
    with rasterio.open(path) as dataset:
        actual_grid = {"crs": dataset.crs.to_string() if dataset.crs else None,
                       "width": dataset.width, "height": dataset.height,
                       "pixel_size_m": [abs(float(dataset.transform.a)), abs(float(dataset.transform.e))],
                       "affine_transform": [float(dataset.transform.a), float(dataset.transform.b),
                                            float(dataset.transform.c), float(dataset.transform.d),
                                            float(dataset.transform.e), float(dataset.transform.f)]}
        actual_valid = int((dataset.read_masks(1) != 0).sum())
        if dataset.count != 1 or dataset.dtypes != ("float32",) or dataset.nodata != -9999.0:
            raise ValueError(f"manifest raster band metadata changed: {record['path']}")
        if actual_grid != record["grid"]:
            raise ValueError(f"raster metadata differs from manifest: {record['path']}")
        if dataset.units[0] != record["band_units_metadata"]:
            raise ValueError(f"raster unit metadata differs from manifest: {record['path']}")
    if record["valid_cell_count"] != 2430 or actual_valid != record["valid_cell_count"]:
        raise ValueError(f"unexpected raster coverage: {record['path']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", type=Path, help="validate an existing manifest and all source hashes without writing")
    args = parser.parse_args()
    if args.check:
        check_path = args.check if args.check.is_absolute() else ROOT / args.check
        manifest = json.loads(check_path.read_text(encoding="utf-8"))
        validate_manifest(manifest, ROOT)
        print(f"valid={rel(check_path)} series={len(manifest['scenario_series'])} slices=45 context_groups={len(manifest['context_layers'])}")
        return
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {rel(output)}")
    manifest = build_manifest(ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"manifest={rel(output)} series={len(manifest['scenario_series'])} slices=45 context_groups={len(manifest['context_layers'])}")


if __name__ == "__main__":
    main()
