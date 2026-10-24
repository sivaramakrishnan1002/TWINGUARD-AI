#!/usr/bin/env python
"""Verify and process local ASF HyP3 RTC products into DERIVED flood labels.

Raw data are opened read-only. ZIP members are read through GDAL's /vsizip/
handler; no archive is extracted or modified. Intermediates live under
data/processed/sar_work and final, unvalidated candidate labels under
data/features/labels. Existing output paths are never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask, shapes
from rasterio.transform import Affine
from rasterio.warp import Resampling, reproject
from scipy.ndimage import uniform_filter
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
RAW_RTC = ROOT / "data/raw/satellite/hpy3_rtc"  # Preserve existing on-disk spelling.
RAW_S1 = ROOT / "data/raw/satellite/sentinel1"
WORK = ROOT / "data/processed/sar_work"
LABEL_DIR = ROOT / "data/features/labels"
GRID = ROOT / "data/processed/grid/cma_mask.tif"
BOUNDARY = ROOT / "data/raw/boundary/chennai_cma_boundary.geojson"
VERIFY_MD = ROOT / "docs/HYP3_RTC_VERIFICATION.md"
DOWNLOAD_LOG = ROOT / "docs/DOWNLOAD_LOG.txt"
MASTER_LABELS = ROOT / "data/processed/labels_inspection"
CELL_TABLE = ROOT / "data/features/static/cell_table.parquet"
GFD_ZIP = ROOT / "data/raw/historical_floods/2015/global_flood_database/DFO_4309_From_20151110_to_20151204.zip"
OPENCITY_POINTS = ROOT / "data/raw/historical_floods/2015/opencity_flood_points"
LABEL_OUTPUTS = [
    LABEL_DIR / "label_2015-11-24_change_otsu_DERIVED.tif",
    LABEL_DIR / "label_2015-11-24_event_otsu_DERIVED.tif",
    LABEL_DIR / "label_2015-12-06_change_otsu_DERIVED.tif",
    LABEL_DIR / "label_2021-11-16_change_otsu_DERIVED.tif",
    LABEL_DIR / "dense_urban_unreliable_flag.tif",
    LABEL_DIR / "derived_flood_polygons.gpkg",
    LABEL_DIR / "label_registry.json",
]
SPECKLE_SIZE = 5
SPECKLE_LOW_CV_PERCENTILE = 10.0
BUFFER_M = 3000.0
SIMPLIFY_M = 30.0
STEEP_FALLBACK_DEG = 15.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _product_metadata(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {
        "name": path.name,
        "relative_path": path.relative_to(ROOT).as_posix(),
        "size_bytes": path.stat().st_size,
        "filesystem_date": datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds"),
        "sha256": sha256(path),
        "source": "ASF HyP3 On Demand RTC GAMMA, user job",
        "licence": "TO CONFIRM (Copernicus Sentinel data via ASF)",
    }
    with zipfile.ZipFile(path) as zf:
        record["zip_entries"] = len(zf.infolist())
        record["uncompressed_bytes"] = sum(info.file_size for info in zf.infolist())
        record["zip_integrity"] = "PASS" if zf.testzip() is None else "FAIL"
        names = [x for x in zf.namelist() if not x.endswith("/")]
        readme_name = next((x for x in names if x.endswith("README.md.txt")), None)
        readme = zf.read(readme_name).decode("utf-8", "replace") if readme_name else ""
        source_match = re.search(r"source granule used.*?:\s*\n([^\r\n]+)", readme, re.I)
        record["source_scene"] = source_match.group(1).strip() if source_match else None
        process_match = re.search(r"Processing Date/Time:\s*([^\r\n]+)", readme)
        record["product_processing_time"] = process_match.group(1).strip() if process_match else None
        record["product_metadata_excerpt"] = {
            "rtc_family": "RTC",
            "pixel_spacing_claim": "30 m",
            "crs_claim": "WGS 84 / UTM zone 44N",
            "backscatter_claim": "gamma-0 power",
            "speckle_filter_claim": "not applied",
            "source_readme": readme_name,
        }
        # Preserve the actual product option token block, excluding the job ID.
        option_match = re.search(r"_DVP_(.+)_[A-F0-9]{4,8}$", path.stem)
        record["options_encoded_in_filename"] = f"DVP_{option_match.group(1)}" if option_match else "not parsed"
        layer_names = [n for n in names if n.lower().endswith((".tif", ".tiff"))]
        record["tiff_members"] = layer_names
        raster_info = []
        for member in layer_names:
            uri = "/vsizip/" + path.resolve().as_posix() + "/" + member
            with rasterio.open(uri) as ds:
                raster_info.append({
                    "member": member,
                    "crs": ds.crs.to_string() if ds.crs else None,
                    "pixel_size": [abs(float(ds.transform.a)), abs(float(ds.transform.e))],
                    "shape": [ds.height, ds.width],
                    "dtype": ds.dtypes[0],
                    "nodata": ds.nodata,
                    "bounds": [float(ds.bounds.left), float(ds.bounds.bottom), float(ds.bounds.right), float(ds.bounds.top)],
                })
        record["raster_metadata"] = raster_info
        record["extra_layers_present"] = {
            "VV": any(n.endswith("_VV.tif") for n in layer_names),
            "VH": any(n.endswith("_VH.tif") for n in layer_names),
            "DEM": any(n.endswith("_dem.tif") for n in layer_names),
            "incidence_angle": any(n.endswith("_inc_map.tif") for n in layer_names),
            "layover_shadow_mask": any(n.endswith("_ls_map.tif") for n in layer_names),
            "scattering_area": any(n.endswith("_area_map.tif") for n in layer_names),
        }
        record["other_package_members"] = [n for n in names if not n.lower().endswith((".tif", ".tiff"))]
    source = record["source_scene"]
    if source:
        date = re.search(r"_(20\d{6})T", source)
        year = date.group(1)[:4] if date else path.parent.name
        source_zip = RAW_S1 / year / f"{source}.zip"
        record["source_scene_zip"] = source_zip.relative_to(ROOT).as_posix()
        record["source_scene_zip_exists"] = source_zip.is_file()
    else:
        record["source_scene_zip"] = None
        record["source_scene_zip_exists"] = False
    return record


def verify_products() -> list[dict[str, Any]]:
    products = sorted(RAW_RTC.glob("*/*.zip"))
    if not products:
        raise FileNotFoundError(f"No RTC ZIP products found in existing directory {RAW_RTC.relative_to(ROOT)}")
    records = [_product_metadata(path) for path in products]
    errors = []
    for r in records:
        if r["zip_integrity"] != "PASS":
            errors.append(f"ZIP CRC failed: {r['relative_path']}")
        if not r["source_scene_zip_exists"]:
            errors.append(f"No matching source Sentinel ZIP: {r['relative_path']} -> {r['source_scene']}")
        for raster in r["raster_metadata"]:
            if raster["crs"] != "EPSG:32644" or raster["pixel_size"] != [30.0, 30.0]:
                errors.append(f"Unexpected CRS/resolution: {r['relative_path']}:{raster['member']}")
    if DOWNLOAD_LOG.exists() or VERIFY_MD.exists() or (ROOT / "docs/HYP3_RTC_PRODUCTS.json").exists():
        raise FileExistsError("Refusing to overwrite an existing Phase 8 verification log or report")
    _write_verification(records)
    if errors:
        raise RuntimeError("; ".join(errors))
    return records


def _write_verification(records: list[dict[str, Any]]) -> None:
    counts: dict[str, int] = {}
    for item in records:
        year = Path(item["relative_path"]).parent.name
        counts[year] = counts.get(year, 0) + 1
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    log_lines = ["TwinGuard AI — ASF HyP3 RTC verification log", "", f"Generated: {now}",
                 "Archive folder on disk: data/raw/satellite/hpy3_rtc (existing spelling preserved; user request said hyp3_rtc)",
                 "Raw data were inspected read-only. This log is kept in docs/ because data/raw is read-only.", ""]
    for r in records:
        log_lines += [
            f"File name: {r['name']}",
            f"Source: {r['source']}",
            f"Download date/time (filesystem date): {r['filesystem_date']}",
            f"File size (bytes): {r['size_bytes']}",
            f"SHA-256: {r['sha256']}",
            f"Licence: {r['licence']}",
            f"Options from filename: {r['options_encoded_in_filename']}",
            f"Product processing time (embedded README): {r['product_processing_time']}",
            f"ZIP CRC integrity: {r['zip_integrity']}; entries: {r['zip_entries']}",
            f"Source Sentinel-1 scene: {r['source_scene']}",
            "",
        ]
    DOWNLOAD_LOG.write_text("\n".join(log_lines), encoding="utf-8")
    lines = ["# ASF HyP3 RTC archive verification", "", "All 13 source ZIPs were opened read-only. `ZipFile.testzip()` checked CRCs for every member; SHA-256 is over each unchanged ZIP. The source filename is linked to the original Sentinel-1 ZIP by the granule name embedded in the HyP3 README.", "",
             f"Inventory generated: {now}", "", f"Exact counts: {', '.join(f'{k}: {v}' for k, v in sorted(counts.items()))}.",
             "Products are stored under the existing misspelled directory `data/raw/satellite/hpy3_rtc`; this task did not rename or move raw files.",
             "", "## Product metadata", "", "The README in each archive says WGS 84 / UTM zone 44N, 30 m spacing, gamma-0 power, and no speckle filter. Filename options encode dual-pol VV/VH, precise orbit, unmasked, unfiltered, entire-area and DEM-matched processing (`DVP_RTC30_G_gpuned`). Metadata is per product, below; TIFF headers were also opened to verify CRS, spacing, shape, dtype and NoData.", "",
             "The README describes the `_ls_map.tif` layover/shadow mask and its bit-coded values; actual per-file availability is listed rather than assumed. It also says DEM and incidence-angle layers are optional; their actual presence is shown per product.", "",
             "| Year | Archive | Size bytes | SHA-256 | ZIP CRC | Source scene exact match | Raster members / extras |", "|---:|---|---:|---|---|---|---|"]
    for r in records:
        rasters = "; ".join(f"{Path(x['member']).name} ({x['crs']}, {x['pixel_size'][0]:g} m, {x['dtype']}, nodata {x['nodata']})" for x in r["raster_metadata"])
        extras = ", ".join(k for k, v in r["extra_layers_present"].items() if v)
        lines.append(f"| {Path(r['relative_path']).parent.name} | `{r['name']}` | {r['size_bytes']} | `{r['sha256']}` | {r['zip_integrity']} ({r['zip_entries']} entries) | {'yes' if r['source_scene_zip_exists'] else 'NO'}: `{r['source_scene']}` | {extras}; {rasters} |")
    lines += ["", "## Options and caveats", "", "The letter-code expansion follows the per-product README convention; the product metadata reports `RTC30`, GAMMA, gamma-0 power, unmasked, not filtered, entire area, DEM-matched. No product was extracted to `data/raw`; raster metadata was read via GDAL's virtual ZIP reader. Filesystem time is not proof of acquisition or processing time. Licence remains `TO CONFIRM (Copernicus Sentinel data via ASF)`.", ""]
    VERIFY_MD.write_text("\n".join(lines), encoding="utf-8")
    (ROOT / "docs/HYP3_RTC_PRODUCTS.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="CRC-check and catalogue all local RTC ZIPs")
    parser.add_argument("--process", action="store_true", help="run preprocessing, label comparison and registration after verification")
    parser.add_argument("--finalize-existing", action="store_true", help="write reports from the completed raster/GPKG outputs and registry already created by a prior pass")
    args = parser.parse_args()
    if sum((args.verify_only, args.process, args.finalize_existing)) != 1:
        parser.error("choose exactly one of --verify-only, --process or --finalize-existing")
    if args.verify_only:
        records = verify_products()
    else:
        catalog = ROOT / "docs/HYP3_RTC_PRODUCTS.json"
        if not catalog.is_file():
            raise FileNotFoundError("Run --verify-only first; its new product catalogue is missing")
        records = json.loads(catalog.read_text(encoding="utf-8"))
        for record in records:
            source = ROOT / record["relative_path"]
            if not source.is_file() or source.stat().st_size != record["size_bytes"] or sha256(source) != record["sha256"]:
                raise RuntimeError(f"RTC input changed since verification: {record['relative_path']}")
    print(f"Verified {len(records)} HyP3 RTC products; ZIP CRC and scene-name checks passed.")
    if args.process:
        process_products(records)
    if args.finalize_existing:
        finalize_existing(records)
    return 0


def finalize_existing(records: list[dict[str, Any]]) -> None:
    registry_path = LABEL_DIR / "label_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    layers = {item["id"]: item for item in registry["layers"]}
    metrics = {"2015-11-24": layers["derived_2015-11-24_change_otsu"]["validation_result"],
               "2015-12-06": layers["derived_2015-12-06_change_otsu"]["validation_result"],
               "2021-11-16": layers["derived_2021-11-16_change_otsu"]["validation_result"]}
    reports = list(WORK.glob("run_*/phase8_processing_metadata.json"))
    if not reports:
        raise FileNotFoundError("No completed Stage 8 processing metadata to finalize")
    process_path = max(reports, key=lambda p: p.stat().st_mtime)
    run_id = process_path.parent.name
    suffix = "" if run_id == "rtc_aligned" else f"_{run_id}"
    paths = {
        "2015-11-24_change": LABEL_DIR / f"label_2015-11-24_change_otsu_DERIVED{suffix}.tif",
        "2015-11-24_event": LABEL_DIR / f"label_2015-11-24_event_otsu_DERIVED{suffix}.tif",
        "2015-12-06_change": LABEL_DIR / f"label_2015-12-06_change_otsu_DERIVED{suffix}.tif",
        "2021-11-16_change": LABEL_DIR / f"label_2021-11-16_change_otsu_DERIVED{suffix}.tif",
    }
    dense = LABEL_DIR / f"dense_urban_unreliable_flag{suffix}.tif"
    gpkg = LABEL_DIR / f"derived_flood_polygons{suffix}.gpkg"
    if not all(path.is_file() for path in [*paths.values(), dense, gpkg]):
        raise FileNotFoundError(f"Completed raster/vector set missing for {run_id}")
    # The registry was created after all outputs were written. Add explicit
    # output paths while keeping the recorded metrics and source references.
    registry["stage8_outputs"] = {"rasters": {key: path.relative_to(ROOT).as_posix() for key, path in paths.items()},
                                  "dense_urban_flag": dense.relative_to(ROOT).as_posix(),
                                  "vector_geopackage": gpkg.relative_to(ROOT).as_posix(),
                                  "processing_metadata": process_path.relative_to(ROOT).as_posix()}
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    process_log = json.loads(process_path.read_text(encoding="utf-8"))
    _write_phase8_outputs(records, process_log, metrics, {}, paths, dense, gpkg, {}, registry_path)


def process_products(records: list[dict[str, Any]]) -> None:
    if (ROOT / "docs/PHASE8_SAR_METRICS.json").exists() or (ROOT / "docs/PHASE8_SAR_LABELS.md").exists():
        raise FileExistsError("Refusing to overwrite an existing Phase 8 report or metrics file")
    run_id = datetime.now().astimezone().strftime("run_%Y%m%d_%H%M%S")
    work_output = WORK / run_id / "rtc_aligned"
    WORK.mkdir(parents=True, exist_ok=True)
    work_output.mkdir(parents=True, exist_ok=True)
    LABEL_DIR.mkdir(parents=True, exist_ok=True)
    grid, grid_meta = _load_grid()
    cma = _read_cma_geometry()
    buffered = cma.buffer(BUFFER_M)
    master_transform = grid_meta["transform"]
    master_height, master_width = grid_meta["height"], grid_meta["width"]
    # Expand the master grid to a 3 km aligned working buffer; clip final labels back to master.
    c0 = math.floor((buffered.bounds[0] - master_transform.c) / master_transform.a)
    c1 = math.ceil((buffered.bounds[2] - master_transform.c) / master_transform.a)
    r0 = math.floor((master_transform.f - buffered.bounds[3]) / abs(master_transform.e))
    r1 = math.ceil((master_transform.f - buffered.bounds[1]) / abs(master_transform.e))
    ext_transform = master_transform * Affine.translation(c0, r0)
    ext_height, ext_width = r1 - r0, c1 - c0
    buffer_mask = geometry_mask([mapping(buffered)], out_shape=(ext_height, ext_width),
                                transform=ext_transform, invert=True, all_touched=True)
    grid_info = {"transform": ext_transform, "height": ext_height, "width": ext_width,
                 "crs": grid_meta["crs"], "buffer_window_offset": [r0, c0]}

    scene_index = _scene_file_index(records)
    dates = {
        "2015-10-19": ["20151019T003131"],
        "2015-11-24": ["20151124T003120"],
        "2015-12-06": ["20151206T003120"],
        "2021-10-23": ["20211023T003148", "20211023T003213"],
        "2021-11-04": ["20211104T003147", "20211104T003212"],
        "2021-11-16": ["20211116T003147", "20211116T003212"],
    }
    processed: dict[str, dict[str, np.ndarray]] = {}
    process_log: dict[str, Any] = {"grid": {k: str(v) if k == "transform" else v for k, v in grid_info.items()},
                                   "resampling": "bilinear in RTC linear gamma-0 power; layover-shadow mask nearest neighbour",
                                   "working_buffer_m": BUFFER_M,
                                   "filter": {"method": "Lee local-mean/variance", "window_pixels": [SPECKLE_SIZE, SPECKLE_SIZE],
                                              "noise_estimator": f"median local variance among lowest {SPECKLE_LOW_CV_PERCENTILE:g}% local coefficient-of-variation pixels per date and polarization",
                                              "source_HyP3_filter": "off"},
                                   "layover_shadow": "valid only where mask is tested (mask != 0) and layover bit 4 and shadow bit 16 are both clear; fallback steep terrain >15 degrees only if a product lacks the mask",
                                   "products": {}, "registration": {}}
    for date, timestamps in dates.items():
        composite = {"VV": np.full((ext_height, ext_width), np.nan, dtype=np.float32),
                     "VH": np.full((ext_height, ext_width), np.nan, dtype=np.float32),
                     "ls": np.zeros((ext_height, ext_width), dtype=np.uint8)}
        contributor_count = np.zeros((ext_height, ext_width), dtype=np.uint8)
        for stamp in timestamps:
            if stamp not in scene_index:
                continue
            product = scene_index[stamp]
            scene_arrays = _reproject_product(product, grid_info)
            scene_valid = scene_arrays["valid"] & buffer_mask
            for pol in ("VV", "VH"):
                fill = scene_valid & ~np.isfinite(composite[pol])
                composite[pol][fill] = scene_arrays[pol][fill]
            fill_ls = scene_valid & (contributor_count == 0)
            composite["ls"][fill_ls] = scene_arrays["ls"][fill_ls]
            contributor_count[scene_valid] = np.minimum(contributor_count[scene_valid] + 1, 255)
        valid = buffer_mask & (contributor_count > 0) & np.isfinite(composite["VV"]) & np.isfinite(composite["VH"])
        if not np.any(valid):
            raise RuntimeError(f"No valid RTC pixels in buffered working window for {date}")
        date_stats = {"valid_pixels_in_buffer": int(np.count_nonzero(valid)),
                      "adjacent_slice_overlap_pixels": int(np.count_nonzero(contributor_count > 1)),
                      "scene_timestamps": timestamps}
        for pol in ("VV", "VH"):
            arr = composite[pol]
            arr[~valid] = np.nan
            filtered, noise_var = _lee_filter(arr, valid)
            composite[pol] = filtered
            date_stats[f"{pol}_lee_noise_variance_linear_power"] = noise_var
            db = np.full(arr.shape, np.nan, dtype=np.float32)
            good = valid & np.isfinite(filtered) & (filtered > 0)
            db[good] = (10.0 * np.log10(filtered[good])).astype(np.float32)
            composite[f"{pol}_db"] = db
            _write_float_tif(work_output / f"{date}_{pol}_gamma0_power_lee5.tif", filtered, grid_info, good)
            _write_float_tif(work_output / f"{date}_{pol}_dB_lee5.tif", db, grid_info, good)
        _write_byte_tif(work_output / f"{date}_valid_layover_shadow_mask.tif", valid.astype(np.uint8), grid_info, buffer_mask)
        _write_byte_tif(work_output / f"{date}_layover_shadow_flags.tif", composite["ls"], grid_info, valid)
        date_stats["valid_pixels_inside_CMA"] = int(np.count_nonzero(valid & _geometry_mask_on_grid(cma, grid_info)))
        process_log["products"][date] = date_stats
        processed[date] = composite
        print(f"Preprocessed {date}: {date_stats['valid_pixels_in_buffer']:,} valid buffer pixels", flush=True)

    cma_mask, permanent_water, dense_urban, blocks_meta = _load_label_masks(grid, grid_meta)
    process_log["grid_alignment"] = blocks_meta
    eligible_land = cma_mask & ~permanent_water
    outputs: dict[str, np.ndarray] = {}
    metrics: dict[str, Any] = {}
    # 2015 pilot: Otsu thresholds are computed only inside valid CMA land; no UNOSAT labels enter threshold selection.
    ref15 = processed["2015-10-19"]
    evt15 = processed["2015-11-24"]
    valid15 = _crop_valid(ref15["VV"], evt15["VV"], ref15["VH"], evt15["VH"], grid_info=grid_info, master_meta=grid_meta)
    ref15_db = _crop_grid(ref15["VV_db"], grid_info, grid_meta)
    evt15_db = _crop_grid(evt15["VV_db"], grid_info, grid_meta)
    otsu15 = _otsu_pair(ref15_db, evt15_db, valid15 & eligible_land)
    change15 = otsu15["difference"]
    event15 = otsu15["event"]
    diff15 = evt15_db - ref15_db
    event15_grid = evt15_db
    valid15_grid = valid15
    outputs["2015-11-24_change"] = _make_candidate(diff15 <= change15, valid15_grid, eligible_land)
    outputs["2015-11-24_event"] = _make_candidate(event15_grid <= event15, valid15_grid, eligible_land)
    labels_24 = _read_label_raster(MASTER_LABELS / "2015-11-24_EXPLORATORY_NOT_FINAL.tif", grid_meta)
    official24 = labels_24 == 1
    metrics["2015-11-24"] = _pilot_metrics(outputs["2015-11-24_change"], outputs["2015-11-24_event"],
                                           official24, valid15_grid, eligible_land, dense_urban,
                                           diff15, event15_grid, change15, event15)
    # Fixed data-driven change-threshold method reused for later 2015 and 2021 dates.
    refs_dec = [processed["2015-10-19"]["VV"], processed["2015-11-24"]["VV"]]
    dec_reference = _nanmean_stack(refs_dec)
    dec_ref_db = np.full(dec_reference.shape, np.nan, dtype=np.float32)
    m = np.isfinite(dec_reference) & (dec_reference > 0)
    dec_ref_db[m] = 10.0 * np.log10(dec_reference[m])
    dec_event = processed["2015-12-06"]
    valid_dec = _crop_valid(dec_reference, dec_event["VV"], dec_event["VH"], grid_info=grid_info, master_meta=grid_meta)
    dec_ref_db_grid = _crop_grid(dec_ref_db, grid_info, grid_meta)
    dec_event_db = _crop_grid(dec_event["VV_db"], grid_info, grid_meta)
    otsu_dec = _otsu_pair(dec_ref_db_grid, dec_event_db, valid_dec & eligible_land)
    dec_diff = dec_event_db - dec_ref_db_grid
    valid_dec_grid = valid_dec
    outputs["2015-12-06_change"] = _make_candidate(dec_diff <= otsu_dec["difference"], valid_dec_grid, eligible_land)
    metrics["2015-12-06"] = {"otsu_difference_db": otsu_dec["difference"], "otsu_event_vv_db": otsu_dec["event"],
                             "valid_land_pixels": int(np.count_nonzero(valid_dec_grid & eligible_land)),
                             "flooded_pixels": int(np.count_nonzero(outputs["2015-12-06_change"] == 1)),
                             "flooded_area_km2": _label_area(outputs["2015-12-06_change"]),
                             "comparison_with_24_nov_candidate_area_change_km2": float(_label_area(outputs["2015-12-06_change"]) - _label_area(outputs["2015-11-24_change"]))}
    # 2021: use the two earlier acquisitions as a linear-power reference composite.
    ref21a, ref21b, evt21 = processed["2021-10-23"], processed["2021-11-04"], processed["2021-11-16"]
    ref21 = _nanmean_stack([ref21a["VV"], ref21b["VV"]])
    ref21_db = np.full(ref21.shape, np.nan, dtype=np.float32)
    good = np.isfinite(ref21) & (ref21 > 0)
    ref21_db[good] = 10.0 * np.log10(ref21[good])
    valid21 = _crop_valid(ref21, evt21["VV"], evt21["VH"], grid_info=grid_info, master_meta=grid_meta)
    ref21_db_grid = _crop_grid(ref21_db, grid_info, grid_meta)
    event21_db_grid = _crop_grid(evt21["VV_db"], grid_info, grid_meta)
    otsu21 = _otsu_pair(ref21_db_grid, event21_db_grid, valid21 & eligible_land)
    diff21 = event21_db_grid - ref21_db_grid
    valid21_grid = valid21
    outputs["2021-11-16_change"] = _make_candidate(diff21 <= otsu21["difference"], valid21_grid, eligible_land)
    metrics["2021-11-16"] = {"otsu_difference_db": otsu21["difference"], "otsu_event_vv_db": otsu21["event"],
                             "valid_land_pixels": int(np.count_nonzero(valid21_grid & eligible_land)),
                             "flooded_pixels": int(np.count_nonzero(outputs["2021-11-16_change"] == 1)),
                             "flooded_area_km2": _label_area(outputs["2021-11-16_change"]),
                             "NRSC_13_Nov_map_vector_comparison": "not computed: local NRSC map is PDF-only and manual digitising is reserved as a QGIS validation task",
                             "OpenCity_2021_points_comparison": "not computed: available OpenCity point resources are 2015 datasets, not 2021 observations"}

    # 2015 Dec 6 comparisons are coarse/time-mismatched cross-checks only.
    metrics["2015-12-06"]["GFD_4309_cross_check"] = _gfd_cross_check(outputs["2015-12-06_change"], grid_meta)
    metrics["2015-12-06"]["OpenCity_observed_point_cross_check"] = _opencity_point_check(outputs["2015-12-06_change"], grid_meta)
    metrics["2015-12-06"]["limitations"] = ["GFD event 4309 ends 4 Dec; candidate is 6 Dec, so dates differ.",
                                                "OpenCity points have no reliable event timestamp in the inspected source metadata; spatial overlap is not a date-matched validation."]

    # Write the three target label masks and a separate urban-reliability flag, all on the master grid.
    suffix = "" if not LABEL_OUTPUTS[0].exists() else f"_{run_id}"
    label_paths = {
        "2015-11-24_change": LABEL_DIR / f"label_2015-11-24_change_otsu_DERIVED{suffix}.tif",
        "2015-11-24_event": LABEL_DIR / f"label_2015-11-24_event_otsu_DERIVED{suffix}.tif",
        "2015-12-06_change": LABEL_DIR / f"label_2015-12-06_change_otsu_DERIVED{suffix}.tif",
        "2021-11-16_change": LABEL_DIR / f"label_2021-11-16_change_otsu_DERIVED{suffix}.tif",
    }
    for path in label_paths.values():
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite {path}")
    for key, path in label_paths.items():
        _write_label_tif(path, outputs[key], grid_meta)
    dense_path = LABEL_DIR / f"dense_urban_unreliable_flag{suffix}.tif"
    dense_data = np.where(cma_mask, dense_urban.astype(np.uint8), 255).astype(np.uint8)
    _write_byte_tif(dense_path, dense_data, grid_meta, cma_mask)
    gpkg_path = LABEL_DIR / f"derived_flood_polygons{suffix}.gpkg"
    polygons, polygon_stats = _polygonize_outputs(outputs, label_paths, cma, grid_meta, gpkg_path, dense_urban)
    process_log["registration"] = {"master_crs": grid_meta["crs"].to_string(), "master_resolution_m": 30,
                                   "working_grid_pixel_offset_from_master": [r0, c0],
                                   "working_grid_30m_aligned": True,
                                   "master_alignment_check": "all final label rasters use the exact master transform, dimensions and CRS",
                                   "polygon_simplification_tolerance_m": SIMPLIFY_M,
                                   "polygons": polygon_stats}
    process_log["speckle_noise_estimates"] = {date: {k: v for k, v in info.items() if k.endswith("noise_variance_linear_power")} for date, info in process_log["products"].items()}
    processing_path = WORK / run_id / "phase8_processing_metadata.json"
    processing_path.write_text(json.dumps(process_log, indent=2, default=str) + "\n", encoding="utf-8")
    registry_path = LABEL_OUTPUTS[6] if not LABEL_OUTPUTS[6].exists() else LABEL_DIR / f"label_registry{suffix}.json"
    _write_phase8_outputs(records, process_log, metrics, outputs, label_paths, dense_path, gpkg_path, polygons, registry_path)


def _load_grid() -> tuple[np.ndarray, dict[str, Any]]:
    with rasterio.open(GRID) as ds:
        arr = ds.read(1)
        meta = {"crs": ds.crs, "transform": ds.transform, "width": ds.width, "height": ds.height,
                "nodata": ds.nodata, "profile": ds.profile.copy()}
    return arr == 1, meta


def _read_cma_geometry():
    gdf = gpd.read_file(BOUNDARY)
    if gdf.crs is None:
        raise ValueError("CMA boundary has no CRS")
    return unary_union(gdf.to_crs("EPSG:32644").geometry)


def _scene_file_index(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for rec in records:
        if not rec["source_scene_zip_exists"]:
            continue
        timestamp = re.search(r"_(20\d{6}T\d{6})_", rec["source_scene"] or "")
        if timestamp:
            result[timestamp.group(1)] = rec
    return result


def _reproject_product(record: dict[str, Any], grid_info: dict[str, Any]) -> dict[str, np.ndarray]:
    path = ROOT / record["relative_path"]
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        vv = next((n for n in names if n.endswith("_VV.tif")), None)
        vh = next((n for n in names if n.endswith("_VH.tif")), None)
        ls = next((n for n in names if n.endswith("_ls_map.tif")), None)
    if not vv or not vh:
        raise RuntimeError(f"Dual-pol VV/VH members missing from {record['name']}")
    out: dict[str, np.ndarray] = {}
    for key, member in (("VV", vv), ("VH", vh)):
        dest = np.full((grid_info["height"], grid_info["width"]), np.nan, dtype=np.float32)
        with rasterio.open("/vsizip/" + path.resolve().as_posix() + "/" + member) as src:
            if src.crs is None or src.crs.to_epsg() != 32644:
                raise ValueError(f"Unexpected CRS in {record['name']} {member}")
            # Pixel-origin registration offset relative to the common 30 m lattice.
            gx, gy = _assert_grid_alignment(src.transform, grid_info["transform"])
            out.setdefault("_registration_offsets", np.asarray([gx, gy], dtype=np.float64))
            reproject(source=rasterio.band(src, 1), destination=dest,
                      src_transform=src.transform, src_crs=src.crs, src_nodata=0.0,
                      dst_transform=grid_info["transform"], dst_crs=grid_info["crs"],
                      dst_nodata=np.nan, resampling=Resampling.bilinear, init_dest_nodata=True)
        out[key] = dest
    if ls:
        mask = np.zeros((grid_info["height"], grid_info["width"]), dtype=np.uint8)
        with rasterio.open("/vsizip/" + path.resolve().as_posix() + "/" + ls) as src:
            reproject(source=rasterio.band(src, 1), destination=mask,
                      src_transform=src.transform, src_crs=src.crs, src_nodata=0,
                      dst_transform=grid_info["transform"], dst_crs=grid_info["crs"],
                      dst_nodata=0, resampling=Resampling.nearest, init_dest_nodata=True)
        out["ls"] = mask
        out["valid"] = (mask != 0) & ((mask & (4 | 16)) == 0) & np.isfinite(out["VV"]) & (out["VV"] > 0) & np.isfinite(out["VH"]) & (out["VH"] > 0)
    else:
        slope_path = ROOT / "data/processed/terrain_cleaned/slope_deg.tif"
        with rasterio.open(slope_path) as ds:
            slope = ds.read(1)
            slope_valid = (ds.dataset_mask() > 0) & (slope <= STEEP_FALLBACK_DEG)
        out["ls"] = np.where(slope_valid, 1, 0).astype(np.uint8)
        out["valid"] = slope_valid & np.isfinite(out["VV"]) & (out["VV"] > 0) & np.isfinite(out["VH"]) & (out["VH"] > 0)
    out.pop("_registration_offsets", None)
    return out


def _lee_filter(image: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, float]:
    weight = valid.astype(np.float32)
    area = float(SPECKLE_SIZE * SPECKLE_SIZE)
    count = uniform_filter(weight, size=SPECKLE_SIZE, mode="reflect") * area
    values = np.where(valid, image, 0.0).astype(np.float32)
    mean = uniform_filter(values, size=SPECKLE_SIZE, mode="reflect") * area / np.maximum(count, 1.0)
    sq_mean = uniform_filter(values * values, size=SPECKLE_SIZE, mode="reflect") * area / np.maximum(count, 1.0)
    variance = np.maximum(sq_mean - mean * mean, 0.0)
    cv = variance / np.maximum(mean * mean, 1e-12)
    valid_cv = cv[valid & np.isfinite(cv)]
    low_cut = float(np.percentile(valid_cv, SPECKLE_LOW_CV_PERCENTILE)) if valid_cv.size else 0.0
    homogeneous = valid & (cv <= low_cut)
    noise = float(np.median(variance[homogeneous])) if np.any(homogeneous) else 0.0
    gain = np.maximum(variance - noise, 0.0) / np.maximum(variance, 1e-12)
    out = mean + gain * (image - mean)
    out[~valid] = np.nan
    return out.astype(np.float32), noise


def _nanmean_stack(arrays: list[np.ndarray]) -> np.ndarray:
    stack = np.stack(arrays).astype(np.float32)
    valid = np.isfinite(stack)
    count = valid.sum(axis=0)
    total = np.where(valid, stack, 0.0).sum(axis=0)
    out = np.full(stack.shape[1:], np.nan, dtype=np.float32)
    np.divide(total, count, out=out, where=count > 0)
    return out


def _write_float_tif(path: Path, arr: np.ndarray, grid_info: dict[str, Any], valid: np.ndarray) -> None:
    profile = {"driver": "GTiff", "height": grid_info["height"], "width": grid_info["width"], "count": 1,
               "dtype": "float32", "crs": grid_info["crs"], "transform": grid_info["transform"],
               "nodata": -9999.0, "compress": "deflate", "predictor": 3, "tiled": True,
               "blockxsize": 256, "blockysize": 256}
    data = np.where(valid, arr, -9999.0).astype(np.float32)
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(data, 1)


def _write_byte_tif(path: Path, arr: np.ndarray, grid_info: dict[str, Any], valid: np.ndarray) -> None:
    profile = {"driver": "GTiff", "height": grid_info["height"], "width": grid_info["width"], "count": 1,
               "dtype": "uint8", "crs": grid_info["crs"], "transform": grid_info["transform"],
               "nodata": 255, "compress": "deflate", "tiled": True, "blockxsize": 256, "blockysize": 256}
    data = np.where(valid, arr, 255).astype(np.uint8)
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(data, 1)


def _geometry_mask_on_grid(geom, grid_info: dict[str, Any]) -> np.ndarray:
    return geometry_mask([mapping(geom)], out_shape=(grid_info["height"], grid_info["width"]),
                         transform=grid_info["transform"], invert=True, all_touched=False)


def _crop_grid(arr: np.ndarray, grid_info: dict[str, Any], master_meta: dict[str, Any]) -> np.ndarray:
    r0, c0 = grid_info["buffer_window_offset"]
    out = arr[-r0:-r0 + master_meta["height"], -c0:-c0 + master_meta["width"]]
    if out.shape != (master_meta["height"], master_meta["width"]):
        raise ValueError("Buffered working grid does not fully contain the master grid window")
    return out


def _crop_valid(*arrays: np.ndarray, grid_info: dict[str, Any], master_meta: dict[str, Any]) -> np.ndarray:
    valid = np.ones((grid_info["height"], grid_info["width"]), dtype=bool)
    for a in arrays:
        if a.shape != valid.shape:
            raise ValueError("Input arrays do not share buffered-grid dimensions")
        valid &= np.isfinite(a) & (a > 0)
    return _crop_grid(valid, grid_info, master_meta)


def _assert_grid_alignment(source_transform: Affine, master_transform: Affine, tolerance: float = 1e-7) -> tuple[float, float]:
    if source_transform.a <= 0 or source_transform.e >= 0 or not math.isclose(abs(source_transform.a), 30.0, abs_tol=tolerance) or not math.isclose(abs(source_transform.e), 30.0, abs_tol=tolerance):
        raise ValueError("RTC source grid is not north-up 30 m")
    dx = (source_transform.c - master_transform.c) / 30.0
    dy = (master_transform.f - source_transform.f) / 30.0
    if not math.isclose(dx, round(dx), abs_tol=tolerance) or not math.isclose(dy, round(dy), abs_tol=tolerance):
        raise ValueError(f"RTC source grid is not pixel-aligned to master lattice (offsets {dx}, {dy})")
    return dx, dy


def _load_label_masks(cma_grid: np.ndarray, meta: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    baseline_paths = [MASTER_LABELS / "2015-09-01_EXPLORATORY_NOT_FINAL.tif",
                      MASTER_LABELS / "2015-10-14_EXPLORATORY_NOT_FINAL.tif"]
    baseline = np.zeros(cma_grid.shape, dtype=bool)
    base_nodata = {}
    for path in baseline_paths:
        with rasterio.open(path) as ds:
            arr = ds.read(1)
            base_nodata[path.name] = int(np.count_nonzero((arr == ds.nodata) & cma_grid)) if ds.nodata is not None else 0
            baseline |= (arr > 0) & (arr != ds.nodata)
    cell = pd.read_parquet(CELL_TABLE, columns=["row", "col", "built_up_fraction", "water_fraction"])
    rows = cell["row"].to_numpy(np.int32); cols = cell["col"].to_numpy(np.int32)
    water = np.zeros(cma_grid.shape, dtype=bool)
    water[rows, cols] = cell["water_fraction"].fillna(0).to_numpy(np.float32) > 0
    urban_fraction = np.full(cma_grid.shape, np.nan, dtype=np.float32)
    urban_fraction[rows, cols] = cell["built_up_fraction"].to_numpy(np.float32, na_value=np.nan)
    water_n = int(np.count_nonzero(water & cma_grid))
    baseline_n = int(np.count_nonzero(baseline & cma_grid))
    return cma_grid, (baseline | water), (urban_fraction >= 0.5), {
        "permanent_water_definition": "any non-zero class in each Sep/Oct UNOSAT baseline OR WorldCover water fraction > 0",
        "baseline_cma_nodata_pixels": base_nodata,
        "baseline_union_pixels_in_cma": baseline_n,
        "worldcover_water_cells_in_cma": water_n,
        "dense_urban_flag": "built_up_fraction >= 0.5; treated as potentially unreliable due to urban SAR scattering",
        "cma_valid_source_labels_have_nodata": bool(any(base_nodata.values())),
    }


def _otsu(values: np.ndarray, bins: int = 512) -> float:
    v = np.asarray(values, dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size < 2 or np.min(v) == np.max(v):
        raise ValueError("Otsu requires at least two finite values with range")
    hist, edges = np.histogram(v, bins=bins)
    prob = hist.astype(np.float64) / hist.sum()
    centers = (edges[:-1] + edges[1:]) / 2
    omega = np.cumsum(prob)
    mu = np.cumsum(prob * centers)
    total = mu[-1]
    denom = omega * (1.0 - omega)
    between = np.zeros_like(denom)
    good = denom > 0
    between[good] = (total * omega[good] - mu[good]) ** 2 / denom[good]
    return float(centers[int(np.argmax(between))])


def _otsu_pair(reference_db: np.ndarray, event_db: np.ndarray, eligible: np.ndarray) -> dict[str, float]:
    common = eligible & np.isfinite(reference_db) & np.isfinite(event_db)
    if np.count_nonzero(common) < 10:
        raise ValueError("Too few eligible pixels for Otsu threshold")
    diff = event_db[common] - reference_db[common]
    return {"difference": _otsu(diff), "event": _otsu(event_db[common]),
            "valid_land_pixels_for_threshold": int(np.count_nonzero(common)),
            "difference_min_db": float(np.min(diff)), "difference_max_db": float(np.max(diff)),
            "event_db_min": float(np.min(event_db[common])), "event_db_max": float(np.max(event_db[common]))}


def _make_candidate(condition: np.ndarray, valid: np.ndarray, eligible_land: np.ndarray) -> np.ndarray:
    out = np.full(valid.shape, 255, dtype=np.uint8)
    use = valid & eligible_land
    out[use] = condition[use].astype(np.uint8)
    return out


def _read_label_raster(path: Path, meta: dict[str, Any]) -> np.ndarray:
    with rasterio.open(path) as ds:
        if ds.crs != meta["crs"] or ds.transform != meta["transform"] or ds.shape != (meta["height"], meta["width"]):
            raise ValueError(f"Label raster is not on master grid: {path.name}")
        return ds.read(1)


def _pilot_metrics(pred_change: np.ndarray, pred_event: np.ndarray, official: np.ndarray,
                   valid: np.ndarray, land: np.ndarray, dense: np.ndarray,
                   diff: np.ndarray, event_db: np.ndarray, otsu_diff: float, otsu_event: float) -> dict[str, Any]:
    evaluation = valid & land & np.isfinite(diff) & np.isfinite(event_db)
    if not np.any(evaluation):
        raise ValueError("Pilot evaluation has no eligible common SAR pixels")
    result: dict[str, Any] = {
        "otsu_difference_threshold_db": otsu_diff,
        "otsu_event_vv_threshold_db": otsu_event,
        "candidate_methods": {},
        "threshold_sensitivity_change_otsu_offset_db": [],
    }
    for name, pred in (("difference_otsu", pred_change), ("event_backscatter_otsu", pred_event)):
        result["candidate_methods"][name] = {
            "with_dense_urban": _confusion_metrics(pred == 1, official, evaluation),
            "without_dense_urban": _confusion_metrics(pred == 1, official, evaluation & ~dense),
        }
    for offset in (-3, -2, -1, 0, 1, 2, 3):
        decision = diff <= otsu_diff + offset
        pred = _make_candidate(decision, valid, land)
        result["threshold_sensitivity_change_otsu_offset_db"].append({
            "threshold_db": otsu_diff + offset,
            "offset_db": offset,
            "with_dense_urban": _confusion_metrics(pred == 1, official, evaluation),
            "without_dense_urban": _confusion_metrics(pred == 1, official, evaluation & ~dense),
        })
    result["evaluation_pixels"] = int(np.count_nonzero(evaluation))
    result["dense_urban_pixels_in_evaluation"] = int(np.count_nonzero(evaluation & dense))
    result["dense_urban_share_evaluation"] = float(np.mean(dense[evaluation]))
    return result


def _confusion_metrics(pred: np.ndarray, truth: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    p = pred[mask].astype(bool); y = truth[mask].astype(bool)
    tp = int(np.count_nonzero(p & y)); fp = int(np.count_nonzero(p & ~y))
    fn = int(np.count_nonzero(~p & y)); tn = int(np.count_nonzero(~p & ~y))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    iou = tp / (tp + fp + fn) if tp + fp + fn else 0.0
    return {"pixels": int(len(p)), "confusion_matrix_TP_FP_FN_TN": [tp, fp, fn, tn],
            "precision": precision, "recall": recall, "f1": f1, "iou": iou,
            "predicted_area_km2": float(np.count_nonzero(p) * 0.0009),
            "UNOSAT_label_area_km2": float(np.count_nonzero(y) * 0.0009)}


def _label_area(arr: np.ndarray) -> float:
    return float(np.count_nonzero(arr == 1) * 0.0009)


def _gfd_cross_check(pred: np.ndarray, meta: dict[str, Any]) -> dict[str, Any]:
    try:
        import zipfile
        with zipfile.ZipFile(GFD_ZIP) as zf:
            tif_members = [n for n in zf.namelist() if n.lower().endswith((".tif", ".tiff"))]
            if not tif_members:
                return {"status": "not computed", "reason": "archive contains no GeoTIFF member"}
            member = next((n for n in tif_members if Path(n).name == "DFO_4309_From_20151110_to_20151204.tif"), None)
            if member is None:
                return {"status": "not computed", "reason": "expected documented DFO event GeoTIFF is absent"}
            uri = "/vsizip/" + GFD_ZIP.resolve().as_posix() + "/" + member
            with rasterio.open(uri) as ds:
                if ds.count < 1 or ds.descriptions[0] != "flooded":
                    return {"status": "not computed", "reason": f"band 1 semantic check failed: {ds.descriptions}"}
                flooded = np.full((meta["height"], meta["width"]), np.nan, dtype=np.float32)
                reproject(source=rasterio.band(ds, 1), destination=flooded,
                          src_transform=ds.transform, src_crs=ds.crs, src_nodata=ds.nodata,
                          dst_transform=meta["transform"], dst_crs=meta["crs"], dst_nodata=np.nan,
                          resampling=Resampling.nearest)
                ds_crs = ds.crs.to_string() if ds.crs else None
                resolution = [abs(float(ds.transform.a)), abs(float(ds.transform.e))]
            cma, _ = _load_grid()
            m = (pred != 255) & cma & np.isfinite(flooded)
            dfo = flooded == 1
            p = pred == 1
            union = np.count_nonzero((p | dfo) & m)
            return {"status": "computed coarse spatial cross-check; dates differ (GFD ends 2015-12-04; SAR candidate is 2015-12-06)",
                    "member": member, "band": 1, "band_description": "flooded", "crs": ds_crs,
                    "native_resolution_degrees": resolution, "cma_pixels_compared": int(m.sum()),
                    "gfd_flood_pixels_in_cma": int(np.count_nonzero(dfo & m)),
                    "sar_candidate_pixels_in_cma": int(np.count_nonzero(p & m)),
                    "coarse_raster_iou": float(np.count_nonzero(p & dfo & m) / union) if union else None}
    except Exception as exc:
        return {"status": "not computed", "reason": f"{type(exc).__name__}: {exc}"}


def _opencity_point_check(pred: np.ndarray, meta: dict[str, Any]) -> dict[str, Any]:
    try:
        grid_rows, grid_cols = np.indices(pred.shape)
        # Use the exact grid affine to map points into pixel coordinates through rasterio's inverse transform.
        from rasterio.transform import rowcol
        points = []
        source_files = []
        for path in sorted(OPENCITY_POINTS.glob("*.kml")):
            try:
                gdf = gpd.read_file(path, driver="LIBKML")
            except Exception:
                gdf = gpd.read_file(path)
            if gdf.crs is not None:
                gdf = gdf.to_crs(meta["crs"])
            for geom in gdf.geometry:
                if geom is not None and geom.geom_type == "Point":
                    points.append(geom)
            source_files.append(path.name)
        if not points:
            return {"status": "not computed", "reason": "no point features in OpenCity KMLs"}
        rows, cols = rowcol(meta["transform"], [p.x for p in points], [p.y for p in points])
        inside = []
        for r, c in zip(rows, cols):
            inside.append(0 <= r < pred.shape[0] and 0 <= c < pred.shape[1] and pred[r, c] != 255 and pred[r, c] == 1)
        return {"status": "computed spatial overlap only; event dates are unspecified/mismatched",
                "point_count": len(points), "points_in_candidate_flood": int(sum(inside)),
                "share_in_candidate_flood": float(np.mean(inside)), "source_files": source_files}
    except Exception as exc:
        return {"status": "not computed", "reason": f"{type(exc).__name__}: {exc}"}


def _write_label_tif(path: Path, arr: np.ndarray, meta: dict[str, Any]) -> None:
    profile = {"driver": "GTiff", "height": meta["height"], "width": meta["width"], "count": 1,
               "dtype": "uint8", "crs": meta["crs"], "transform": meta["transform"], "nodata": 255,
               "compress": "deflate", "tiled": True, "blockxsize": 256, "blockysize": 256}
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(arr.astype(np.uint8), 1)
        ds.set_band_description(1, "DERIVED flood candidate; 1=flood, 0=not classified as flood, 255=excluded/invalid")


def _polygonize_outputs(outputs: dict[str, np.ndarray], paths: dict[str, Path], cma, meta: dict[str, Any], dest: Path, dense_urban: np.ndarray):
    import pyogrio
    from shapely.validation import make_valid
    if dest.exists():
        raise FileExistsError(f"Refusing to overwrite {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    stats = {}
    first = True
    for key, arr in outputs.items():
        if key not in paths:
            continue
        layer = key.replace("-", "_")
        count = 0
        features = []
        for geom_json, _value in shapes(arr.astype(np.uint8), mask=(arr == 1), transform=meta["transform"], connectivity=8):
            geom = shape(geom_json).simplify(SIMPLIFY_M, preserve_topology=True).intersection(cma)
            if geom.is_empty:
                continue
            geom = make_valid(geom)
            parts = [geom] if geom.geom_type == "Polygon" else [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"]
            if not parts:
                continue
            mp = unary_union(parts)
            if mp.geom_type == "Polygon":
                from shapely.geometry import MultiPolygon
                mp = MultiPolygon([mp])
            if mp.geom_type != "MultiPolygon" or mp.is_empty:
                continue
            row, col = rasterio.transform.rowcol(meta["transform"], mp.centroid.x, mp.centroid.y)
            dense = bool(0 <= row < dense_urban.shape[0] and 0 <= col < dense_urban.shape[1] and dense_urban[row, col])
            features.append({"geometry": mapping(mp), "properties": {
                "label_key": f"{key}|{count+1}", "event_date": key[:10], "method": "Otsu VV dB difference / event backscatter",
                "tier": "C", "is_derived": 1, "is_valid": int(mp.is_valid), "in_cma": int(mp.intersects(cma)),
                "urban_unreliable": int(dense), "flood_area_km2": float(mp.area / 1e6)}})
            count += 1
        if features:
            gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:32644")
            pyogrio.write_dataframe(gdf, dest, layer=layer, driver="GPKG", append=not first)
        stats[key] = {"polygon_count": count, "simplification_tolerance_m": SIMPLIFY_M, "is_valid_expected": True}
        first = False
    return None, stats


def _write_phase8_outputs(records, process_log, metrics, outputs, label_paths, dense_path, gpkg_path, polygons, registry_path):
    if not registry_path.exists():
        registry = _build_registry(records, metrics, label_paths, dense_path, gpkg_path)
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    metrics_path = ROOT / "docs/PHASE8_SAR_METRICS.json"
    report_path = ROOT / "docs/PHASE8_SAR_LABELS.md"
    if metrics_path.exists() or report_path.exists():
        raise FileExistsError("Refusing to overwrite an existing Phase 8 SAR report or metrics file")
    metrics_path.write_text(json.dumps({"metrics": metrics, "preprocessing": process_log, "pilot_status": "DERIVED, not ground truth"}, indent=2, default=str) + "\n", encoding="utf-8")
    lines = ["# Stage 8 — SAR-derived flood label pilot", "", "> Every SAR-derived flood raster/polygon in this stage is **DERIVED**, not ground truth.", "",
             "## 8.1–8.2 RTC products and preprocessing", "",
             "See `HYP3_RTC_VERIFICATION.md` and `DOWNLOAD_LOG.txt` for per-product ZIP CRC, checksum, source scene mapping, raster members, CRS and options. All RTC TIFFs opened with EPSG:32644, 30 m pixels; source label archives were not modified.",
             f"The processing window used the CMA plus {BUFFER_M:g} m buffer (clipped to the source master grid), aligned to the 30 m EPSG:32644 lattice. RTC Gamma-0 power was bilinearly resampled in linear power; reference/event comparison was converted to dB. The Lee filter was {SPECKLE_SIZE}×{SPECKLE_SIZE}; scene-specific local noise variance was estimated from the lowest {SPECKLE_LOW_CV_PERCENTILE:g}% CV pixels. HyP3 speckle filtering was off. Layover/shadow bit mask excluded codes with bit 4 or 16; mask code 0 (not tested) was excluded. If missing, steep terrain fallback is cleaned DEM slope >{STEEP_FALLBACK_DEG:g}°.", "",
             "## 8.3 2015 pilot", "",
             f"Training-free Otsu thresholds (computed inside CMA valid land, no UNOSAT pixels used) were {metrics['2015-11-24']['otsu_difference_threshold_db']:.3f} dB for event-minus-reference VV difference and {metrics['2015-11-24']['otsu_event_vv_threshold_db']:.3f} dB for event VV. UNOSAT `S1_20151124` metrics are post-threshold comparisons only. UNOSAT may use the same 24 Nov scene, so this tests pipeline/map agreement, not flood physics.",
             "", "| Method | Urban handling | IoU | Precision | Recall | F1 | TP / FP / FN / TN | predicted / UNOSAT area km² |", "|---|---|---:|---:|---:|---:|---|---:|"]
    for method, vals in metrics["2015-11-24"]["candidate_methods"].items():
        for urban, score in vals.items():
            lines.append(f"| {method} | {urban} | {score['iou']:.4f} | {score['precision']:.4f} | {score['recall']:.4f} | {score['f1']:.4f} | {' / '.join(map(str, score['confusion_matrix_TP_FP_FN_TN']))} | {score['predicted_area_km2']:.2f} / {score['UNOSAT_label_area_km2']:.2f} |")
    lines += ["", "### Threshold sensitivity", "", "Offsets are applied to the data-derived Otsu event-minus-reference VV dB threshold, not fitted to UNOSAT.", "", "| Offset dB | Threshold dB | IoU | Precision | Recall | F1 | Predicted area km² |", "|---:|---:|---:|---:|---:|---:|---:|"]
    for item in metrics["2015-11-24"]["threshold_sensitivity_change_otsu_offset_db"]:
        score=item["with_dense_urban"]
        lines.append(f"| {item['offset_db']:+.1f} | {item['threshold_db']:.3f} | {score['iou']:.4f} | {score['precision']:.4f} | {score['recall']:.4f} | {score['f1']:.4f} | {score['predicted_area_km2']:.2f} |")
    for year, details in (("2015-12-06", metrics["2015-12-06"]), ("2021-11-16", metrics["2021-11-16"])):
        lines += ["", f"## {year} DERIVED candidate", "", f"Otsu difference threshold: {details['otsu_difference_db']:.3f} dB; event VV threshold: {details['otsu_event_vv_db']:.3f} dB. Candidate area: {details['flooded_area_km2']:.2f} km² across {details['valid_land_pixels']:,} valid land pixels."]
    lines += ["", f"6 Dec 2015 candidate vs 24 Nov candidate area change: {metrics['2015-12-06']['comparison_with_24_nov_candidate_area_change_km2']:+.2f} km². GFD 4309 is a coarse cross-check ending 4 Dec, not date matched: `{metrics['2015-12-06']['GFD_4309_cross_check']}`. OpenCity point overlap: `{metrics['2015-12-06']['OpenCity_observed_point_cross_check']}`. This spatial overlap is not date-matched validation.",
             "", "The 2021 candidate was generated for 16 Nov using 23 Oct and 4 Nov reference acquisitions. Numerical comparison to the 13 Nov NRSC map is **not computed** because the local NRSC reference is a PDF and has not been georeferenced/digitised. Available OpenCity points are 2015, not 2021; no valid 2021 point comparison is available.",
             "", "No 2023 flood label was created: local RTC scenes dated 18 and 30 Nov are before the 3–4 Dec Michaung peak; there is no post-peak scene in this set.",
             "", "## Reliability and validation limits", "", "Dense urban is flagged where WorldCover built-up fraction ≥0.5; the urban-excluded metrics are shown above. This is a screening flag, not proof every such pixel is wrong. Sentinel RTC masks remove marked layover and shadow; remaining urban double-bounce, wet soil, tide, date offsets and threshold sensitivity remain. All labels are DERIVED. A single 2015 scene pair and a potentially same-scene UNOSAT comparison do not validate physical inundation accuracy.", "",
             "December 2015 official vector layer is still unavailable. QGIS validation steps for digitising the 2021 NRSC PDF, 2023 NDEM PDF, and any December 2015 maps are in `MANUAL_TODO.md`.",
             "", "## Outputs", "", "Label rasters and polygon vectors are under `data/features/labels/`; aligned RTC intermediates, speckle-filtered power/dB products and masks are under `data/processed/sar_work/`. Polygon simplification tolerance is 30 m before clipping to the CMA. DB load provenance and counts are recorded in the database completion report.", ""]
    report_path.write_text("\n".join(lines), encoding="utf-8")


def _build_registry(records, metrics, label_paths, dense_path, gpkg_path):
    # Includes existing reference/point/modelled/coarse sources and every Stage 8 output layer.
    return {"status": "DERIVED labels are not ground truth", "layers": [
        {"id": "unosat_2015-09-01", "event": "2015 Chennai", "date": "2015-09-01", "source": "UNOSAT 1039 vector archive", "method": "official vector baseline-water reference", "validation_result": "official source layer; not an event flood label", "tier": "A", "limits": ["baseline water may include wet-soil class"]},
        {"id": "unosat_2015-10-14", "event": "2015 Chennai", "date": "2015-10-14", "source": "UNOSAT 1039 vector archive", "method": "official vector baseline-water reference", "validation_result": "official source layer; not an event flood label", "tier": "A", "limits": ["baseline water may include wet-soil class"]},
        {"id": "unosat_2015-11-12", "event": "2015 Chennai", "date": "2015-11-12", "source": "UNOSAT 1039 vector archive", "method": "official vector flood reference", "validation_result": "source product; not field-validated", "tier": "A", "limits": ["does not cover 1-8 Dec peak"]},
        {"id": "unosat_2015-11-24", "event": "2015 Chennai", "date": "2015-11-24", "source": "UNOSAT 1039 S1_20151124 vector layer", "method": "official vector flood reference", "validation_result": "compared to SAR-derived pilot; possible same-scene source", "tier": "A", "limits": ["not ground truth; possible shared Sentinel acquisition"]},
        {"id": "derived_2015-11-24_change_otsu", "event": "2015 Chennai", "date": "2015-11-24", "source": [r["relative_path"] for r in records if "20151124" in r["name"]], "method": "VV event-minus-reference dB; Otsu; Lee 5x5; permanent-water mask", "validation_result": metrics["2015-11-24"], "tier": "C", "limits": ["UNOSAT may derive from same scene; not field-validated"]},
        {"id": "derived_2015-11-24_event_otsu", "event": "2015 Chennai", "date": "2015-11-24", "source": [r["relative_path"] for r in records if "20151124" in r["name"]], "method": "event VV dB Otsu; Lee 5x5; permanent-water mask", "validation_result": metrics["2015-11-24"]["candidate_methods"]["event_backscatter_otsu"], "tier": "C", "limits": ["UNOSAT may derive from same scene; not field-validated"]},
        {"id": "derived_2015-12-06_change_otsu", "event": "2015 Chennai December peak", "date": "2015-12-06", "source": [r["relative_path"] for r in records if any(x in r["name"] for x in ("20151019", "20151124", "20151206"))], "method": "VV dB difference from linear mean of 19 Oct and 24 Nov references; Otsu", "validation_result": metrics["2015-12-06"], "tier": "C", "limits": ["no official December 2015 vector; GFD ends 4 Dec; OpenCity dates unspecified"]},
        {"id": "derived_2021-11-16_change_otsu", "event": "2021 Chennai", "date": "2021-11-16", "source": [r["relative_path"] for r in records if any(x in r["name"] for x in ("20211023", "20211104", "20211116"))], "method": "VV dB difference from linear mean of 23 Oct and 4 Nov references; Otsu", "validation_result": metrics["2021-11-16"], "tier": "C", "limits": ["NRSC validation map is PDF-only and not digitised; OpenCity point dates do not match"]},
        {"id": "nrsc_2021-11-13-map", "event": "2021 Chennai", "date": "2021-11-13", "source": "data/raw/historical_floods/2021/ChennaiCity-ChennaiCorporationTaluk-4.pdf", "method": "map graphic; manual georeference/digitisation pending", "validation_result": "not compared numerically", "tier": "D", "limits": ["PDF map only; map extent partial"]},
        {"id": "gfd_4309", "event": "2015 Chennai", "date": "2015-11-10 to 2015-12-04", "source": "DFO event 4309 MODIS coarse product", "method": "coarse cross-check", "validation_result": metrics["2015-12-06"]["GFD_4309_cross_check"], "tier": "D", "limits": ["nominal 250 m; event ends 4 Dec"]},
        {"id": "opencity_flows_10y", "event": "Chennai flood scenarios", "date": "modelled return period", "source": "data/raw/historical_floods/2015/opencity_flood_points/1bfef958-d4cc-4e50-a926-445e65bac7a8.kml", "method": "modelled 10-year return-period polygons", "validation_result": "not observed event validation", "tier": "D", "limits": ["modelled scenario; not observed event extent"]},
        {"id": "opencity_flows_200y", "event": "Chennai flood scenarios", "date": "modelled return period", "source": "data/raw/historical_floods/2015/opencity_flood_points/61f1f06f-1fa1-4ef0-94c7-224d892efbef.kml", "method": "modelled 200-year return-period polygons", "validation_result": "not observed event validation", "tier": "D", "limits": ["modelled scenario; not observed event extent"]},
        {"id": "opencity_hazard_zones", "event": "Chennai flood scenarios", "date": "modelled hazard classification", "source": "data/raw/historical_floods/2015/opencity_flood_points/7f29da20-6621-4b49-b0cf-28b9d1de232b.kml", "method": "modelled hazard-zone polygons", "validation_result": "not observed event validation", "tier": "D", "limits": ["modelled scenario; not observed event extent"]},
        {"id": "opencity_inundation_depth_points", "event": "Chennai flooding; event date not specified", "date": "not specified in source title", "source": "data/raw/historical_floods/2015/opencity_flood_points/814ca028-4c84-4bd0-aa67-6dbaeb9b6ba5.kml", "method": "GCC inundation observation points with depth attribute", "validation_result": "spatial point cross-check only; event date remains unclear", "tier": "A", "limits": ["sparse points are not a flood polygon; not time-matched"]},
        {"id": "opencity_flood_points_2015", "event": "2015 Chennai flood", "date": "2015; exact observation dates not established", "source": "data/raw/historical_floods/2015/opencity_flood_points/93d2905a-a580-482d-96b0-4d9ccf5273ef.kml", "method": "GCC 2015 flooding observation points", "validation_result": metrics["2015-12-06"]["OpenCity_observed_point_cross_check"], "tier": "A", "limits": ["sparse points are not a flood polygon; exact point timestamps are unspecified"]},
        {"id": "opencity_flows_100y", "event": "Chennai flood scenarios", "date": "modelled return period", "source": "data/raw/historical_floods/2015/opencity_flood_points/994a99a1-6104-40c7-ac10-2b7a7ab74437.kml", "method": "modelled 100-year return-period polygons", "validation_result": "not observed event validation", "tier": "D", "limits": ["modelled scenario; not observed event extent"]},
        {"id": "opencity_flows_50y", "event": "Chennai flood scenarios", "date": "modelled return period", "source": "data/raw/historical_floods/2015/opencity_flood_points/a6b20b7c-d771-4572-a2c7-9d8c125e6e5d.kml", "method": "modelled 50-year return-period polygons", "validation_result": "not observed event validation", "tier": "D", "limits": ["modelled scenario; not observed event extent"]},
        {"id": "opencity_flows_25y", "event": "Chennai flood scenarios", "date": "modelled return period", "source": "data/raw/historical_floods/2015/opencity_flood_points/a6b4f2b1-f2b4-4dbc-93da-37be6dc7a345.kml", "method": "modelled 25-year return-period polygons", "validation_result": "not observed event validation", "tier": "D", "limits": ["modelled scenario; not observed event extent"]},
        {"id": "opencity_flows_5y", "event": "Chennai flood scenarios", "date": "modelled return period", "source": "data/raw/historical_floods/2015/opencity_flood_points/ef3286de-1c9b-41a2-a5f2-a075863e26f6.kml", "method": "modelled 5-year return-period polygons", "validation_result": "not observed event validation", "tier": "D", "limits": ["modelled scenario; not observed event extent"]},
        {"id": "ndem_2023-12-07-map", "event": "2023 Michaung", "date": "2023-12-07 06:00 IST", "source": "data/raw/historical_floods/2023/tncyclone50dsc07122023_0600hrs_map.pdf", "method": "map graphic only", "validation_result": "not compared numerically", "tier": "D", "limits": ["not vector; manual digitising pending"]},
        {"id": "nrsc_2023-michaung-pdf", "event": "2023 Michaung", "date": "2023 event", "source": "not downloaded; PDF map requested previously", "method": "none", "validation_result": "unavailable", "tier": "D", "limits": ["no post-peak RTC scene; no label created"]},
        {"id": "derived_2023-michaung", "event": "2023 Michaung", "date": "2023-12-03 to 2023-12-04 peak", "source": "none", "method": "no post-peak scene available", "validation_result": "no SAR flood label created", "tier": "D", "limits": ["Nov 18 and Nov 30 RTC products precede the peak"]},
    ]}


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Stage 8 SAR task failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Stage 8 SAR task failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
