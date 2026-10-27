"""Create metadata-conformant copies of the immutable T6 depth rasters."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "data/features/depth/batch1_v1"
DEFAULT_OUTPUT_DIR = ROOT / "data/features/depth/c1_metadata_repair_v0"
EXPECTED_FILES = (
    "depth_mean_2015-11-12_UNOSAT_A_DERIVED.tif",
    "depth_mean_2015-11-24_UNOSAT_A_DERIVED.tif",
    "depth_p05_2015-11-12_UNOSAT_A_DERIVED.tif",
    "depth_p05_2015-11-24_UNOSAT_A_DERIVED.tif",
    "depth_p95_2015-11-12_UNOSAT_A_DERIVED.tif",
    "depth_p95_2015-11-24_UNOSAT_A_DERIVED.tif",
)
EVENT_METADATA = {
    "2015-11-12": {"run_time_utc": "2026-10-25T04:47:06.612287+00:00", "source_geometry_count": 4704},
    "2015-11-24": {"run_time_utc": "2026-10-25T04:47:42.948183+00:00", "source_geometry_count": 3710},
}
REQUIRED_TAGS = (
    "version", "status", "band_role", "units", "crs", "grid", "nodata",
    "event_date", "acquisition_time_utc", "run_time_utc", "source", "source_tier",
    "source_geometry_count", "method", "uncertainty_rule", "dem",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def band_role(filename: str) -> str:
    if "depth_mean_" in filename:
        return "mean_m"
    if "depth_p05_" in filename:
        return "lower_assumption_bound_m"
    if "depth_p95_" in filename:
        return "upper_assumption_bound_m"
    raise ValueError(f"Unrecognized T6 depth filename: {filename}")


def event_date(filename: str) -> str:
    for date in EVENT_METADATA:
        if date in filename:
            return date
    raise ValueError(f"No event date in T6 depth filename: {filename}")


def make_tags(filename: str) -> dict[str, str]:
    date = event_date(filename)
    count = EVENT_METADATA[date]["source_geometry_count"]
    return {
        "version": "batch1-depth-v1-c1-metadata-copy-v0",
        "status": "DERIVED_ASSUMPTION_NOT_OBSERVED",
        "band_role": band_role(filename),
        "units": "metres",
        "crs": "EPSG:32644",
        "grid": "CMA master grid; EPSG:32644; 30 m; aligned to cma_mask.tif",
        "nodata": "-9999.0",
        "event_date": date,
        "acquisition_time_utc": "UNKNOWN; serialize as JSON null",
        "run_time_utc": EVENT_METADATA[date]["run_time_utc"],
        "source": "labels.v_usable_flood_labels tier A official UNOSAT flood extent",
        "source_tier": "A",
        "source_geometry_count": str(count),
        "method": "Per 8-connected raster component: median cleaned-DEM elevation on rasterized flood boundary; depth=max(0, surface-DEM)",
        "uncertainty_rule": "lower=max(0,mean_m-4);upper=mean_m+4;not_calibrated_statistical_percentiles;DEFAULT_TO_CONFIRM",
        "dem": "Cleaned Copernicus GLO-30 DSM; buildings and vegetation remain; not bare-earth terrain",
        "AREA_OR_POINT": "Area",
    }


def create_copy(source: Path, destination: Path) -> dict[str, object]:
    with rasterio.open(source) as src:
        if src.count != 1 or src.dtypes != ("float32",) or src.crs is None or src.crs.to_epsg() != 32644:
            raise ValueError(f"Unexpected source raster contract: {source.name}")
        if src.nodata != -9999.0 or src.transform.a != 30 or src.transform.e != -30:
            raise ValueError(f"Unexpected source grid/NoData: {source.name}")
        data = src.read(1)
        mask = src.read_masks(1)
        source_profile = src.profile.copy()
        source_tags = src.tags()
    if "event_date" not in source_tags or "run_time_utc" not in source_tags:
        raise ValueError(f"Missing authoritative event/run time tags in {source.name}")
    if source_tags["event_date"] != event_date(source.name):
        raise ValueError(f"Filename and event_date disagree: {source.name}")
    if source_tags["run_time_utc"] != EVENT_METADATA[event_date(source.name)]["run_time_utc"]:
        raise ValueError(f"Existing T6 run time differs from checked summary: {source.name}")

    with rasterio.open(destination, "w", **source_profile) as dst:
        dst.write(data, 1)
        dst.write_mask(mask)
        dst.update_tags(**make_tags(source.name))
        dst.set_band_description(1, band_role(source.name))

    with rasterio.open(destination) as out:
        if out.tags().get("AREA_OR_POINT") != "Area":
            raise ValueError(f"AREA_OR_POINT did not persist: {destination.name}")
        if out.descriptions[0] != band_role(source.name):
            raise ValueError(f"Band description did not persist: {destination.name}")
        if not np.array_equal(out.read(1), data) or not np.array_equal(out.read_masks(1), mask):
            raise ValueError(f"Copied pixels/mask changed: {destination.name}")
        missing = sorted(set(REQUIRED_TAGS) - set(out.tags()))
        if missing:
            raise ValueError(f"Required tags missing from {destination.name}: {missing}")
    return {
        "file": destination.name,
        "source": str(source.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": sha256(source),
        "output_sha256": sha256(destination),
        "cell_values_unchanged": True,
        "mask_unchanged": True,
        "valid_cells": int(np.count_nonzero(mask)),
        "nodata_cells": int(mask.size - np.count_nonzero(mask)),
        "tags": make_tags(source.name),
        "acquisition_time_utc": None,
    }


def run(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty output directory: {output_dir}")
    missing = [name for name in EXPECTED_FILES if not (SOURCE_DIR / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing expected T6 source rasters: {missing}")
    output_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    results = [create_copy(SOURCE_DIR / name, output_dir / name) for name in EXPECTED_FILES]
    try:
        output_location = str(output_dir.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        output_location = str(output_dir)
    manifest = {
        "created_at_utc": started,
        "task": "A18 C1 T6 GeoTIFF metadata conformance copy",
        "source_directory": "data/features/depth/batch1_v1",
        "output_directory": output_location,
        "scientific_limit": "DERIVED assumption-based depth proxy, not observed or validated; GLO-30 is a surface model",
        "uncertainty_limit": "Legacy p05/p95 layers are max(0, mean-4m) and mean+4m assumption bounds, not calibrated statistical percentiles",
        "results": results,
    }
    (output_dir / "metadata_repair_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return output_dir / "metadata_repair_manifest.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    print(run(args.output_dir))


if __name__ == "__main__":
    main()
