"""Build a new Euclidean-drainage physical susceptibility layer; never edits prior outputs."""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
import rasterio
from rasterio.features import rasterize
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipelines.phase9c import urban_censoring as p9c

TABLE = ROOT / "data/features/static/cell_table_phase9b_v2.parquet"
DEM = ROOT / "data/features/terrain/elevation_m.tif"
WATERWAYS = ROOT / "data/features/osm/chennai_osm_features.gpkg"
OUT = ROOT / "data/features/terrain/urban_physical_v1"
REPORT = ROOT / "docs/URBAN_PHYSICAL_LAYER.md"
METRICS = OUT / "metrics.json"
SEED = 20261025


def percentile_rank(values: np.ndarray, valid: np.ndarray, higher_is_wetter: bool) -> np.ndarray:
    """Map finite cells to [0,1] empirical ranks; optionally invert direction."""
    out = np.full(values.shape, np.nan, dtype=np.float32)
    ids = np.flatnonzero(valid & np.isfinite(values))
    if not len(ids):
        return out
    order = np.argsort(values.flat[ids], kind="mergesort")
    ranks = np.empty(len(ids), dtype=np.float32)
    ranks[order] = np.linspace(0.0, 1.0, len(ids), dtype=np.float32)
    if not higher_is_wetter:
        ranks = 1.0 - ranks
    out.flat[ids] = ranks
    return out


def physical_rank_score(height, depression, rel5, rel15, rel33, distance, valid):
    """Non-probability composite: lower height/relative elevation/distance, higher depression."""
    components = [
        percentile_rank(height, valid, False),
        percentile_rank(depression, valid, True),
        percentile_rank(rel5, valid, False),
        percentile_rank(rel15, valid, False),
        percentile_rank(rel33, valid, False),
        percentile_rank(distance, valid, False),
    ]
    stack = np.stack(components)
    available = np.isfinite(stack)
    n = available.sum(axis=0)
    result = np.full(valid.shape, np.nan, dtype=np.float32)
    use = valid & (n >= 3)
    result[use] = np.nansum(stack[:, use], axis=0) / n[use]
    return result


def _write(path: Path, data: np.ndarray, profile, desc: str):
    p = dict(profile)
    p.update(driver="GTiff", count=1, dtype="float32", nodata=-9999.0,
             compress="deflate", predictor=3, tiled=True, BIGTIFF="IF_SAFER")
    arr = np.where(np.isfinite(data), data, -9999.0).astype(np.float32)
    with rasterio.open(path, "w", **p) as dst:
        dst.write(arr, 1)
        dst.set_band_description(1, desc)
        dst.update_tags(status="PHYSICAL, NOT FITTED TO LABELS", method="Euclidean nearest OSM drainage; empirical rank composite")


def run():
    if REPORT.exists() or METRICS.exists():
        raise FileExistsError("Refusing to overwrite existing urban physical report/metrics")
    OUT.mkdir(parents=True, exist_ok=True)
    raster_names = ["height_above_nearest_osm_drainage_m.tif", "euclidean_distance_to_osm_drainage_m.tif",
                    "relative_elevation_5cells_m.tif", "relative_elevation_15cells_m.tif",
                    "relative_elevation_33cells_m.tif", "local_depression_depth_m.tif",
                    "physical_susceptibility_rank.tif"]
    present = [ (OUT / name).exists() for name in raster_names ]
    if any(present) and not all(present):
        raise FileExistsError("Partial raster output exists; refusing to overwrite any raster")
    rasters_already_written = all(present)
    with rasterio.open(DEM) as src:
        profile = src.profile.copy()
        shape = (src.height, src.width)
        transform, crs = src.transform, src.crs
        elevation = src.read(1).astype(np.float32)
        dem_valid = (elevation != src.nodata) & np.isfinite(elevation)
    table = pq.read_table(TABLE).to_pandas()
    rows = table.row.to_numpy(dtype=np.int32)
    cols = table.col.to_numpy(dtype=np.int32)
    if np.any((rows < 0) | (rows >= shape[0]) | (cols < 0) | (cols >= shape[1])):
        raise ValueError("cell table row/col is outside the master raster")
    cma = np.zeros(shape, dtype=bool); cma[rows, cols] = True
    if int(cma.sum()) != len(table):
        raise ValueError("cell table has duplicate row/col positions")

    import geopandas as gpd
    waterways = gpd.read_file(WATERWAYS, layer="waterways")
    if waterways.crs is None:
        raise ValueError("OSM waterways layer has no CRS")
    if waterways.crs != crs:
        waterways = waterways.to_crs(crs)
    shapes = [(g, 1) for g in waterways.geometry if g is not None and not g.is_empty]
    drainage = rasterize(shapes, out_shape=shape, transform=transform, fill=0,
                         all_touched=True, dtype="uint8").astype(bool)
    drainage &= dem_valid
    if not drainage.any():
        raise ValueError("No drainage cells overlap valid DEM")
    # EDT returns the nearest source cell in projected Euclidean distance (30 m cells).
    distance_cells, nearest = distance_transform_edt(~drainage, sampling=(30.0, 30.0), return_indices=True)
    nearest_elev = elevation[nearest[0], nearest[1]]
    height = np.maximum(elevation - nearest_elev, 0.0).astype(np.float32)
    height[~(dem_valid & cma)] = np.nan
    distance = distance_cells.astype(np.float32)
    distance[~(dem_valid & cma)] = np.nan

    def field(name):
        grid = np.full(shape, np.nan, dtype=np.float32)
        vals = table[name].to_numpy(dtype=np.float32, na_value=np.nan)
        grid[rows, cols] = vals
        return grid
    depression = field("local_depression_depth_m")
    rel5, rel15, rel33 = (field(x) for x in ("relative_elevation_5cells_m", "relative_elevation_15cells_m", "relative_elevation_33cells_m"))
    valid = cma & np.isfinite(height) & np.isfinite(depression) & np.isfinite(rel5) & np.isfinite(rel15) & np.isfinite(rel33)
    score = physical_rank_score(height, depression, rel5, rel15, rel33, distance, valid)
    if not rasters_already_written:
        for name, arr, desc in [
            ("height_above_nearest_osm_drainage_m.tif", height, "max(DEM cell minus nearest rasterized OSM waterway elevation, 0 m)"),
            ("euclidean_distance_to_osm_drainage_m.tif", distance, "Euclidean distance to nearest rasterized OSM waterway cell"),
            ("relative_elevation_5cells_m.tif", rel5, "Existing Phase 9B v2 relative elevation, 5-cell window"),
            ("relative_elevation_15cells_m.tif", rel15, "Existing Phase 9B v2 relative elevation, 15-cell window"),
            ("relative_elevation_33cells_m.tif", rel33, "Existing Phase 9B v2 relative elevation, 33-cell window"),
            ("local_depression_depth_m.tif", depression, "Existing Phase 9B v2 local depression depth"),
            ("physical_susceptibility_rank.tif", score, "Uncalibrated empirical rank composite; not a probability"),
        ]:
            _write(OUT / name, arr, profile, desc)

    # Reuse the established 3 km block-bootstrap and dominant land-cover-matched chance procedure.
    built = field("built_up_fraction")
    lc = p9c.dominant_landcover_grid(table, rows, cols, shape)
    meta = {"crs": crs, "transform": transform, "height": shape[0], "width": shape[1]}
    score_domain = cma & np.isfinite(score) & np.isfinite(built)
    points = p9c.point_features(built, lc, score, score, cma, score_domain, meta)
    for point in points:
        if point["row"] is not None and point["col"] is not None:
            point["risk"] = float(score[point["row"], point["col"]]) if np.isfinite(score[point["row"], point["col"]]) else None
    results = {}
    for label, subset in [("all_scored", points), ("urban_proxy_built_up_ge_0p30", [p for p in points if p["built"] is not None and p["built"] >= 0.30])]:
        results[label] = {}
        for pct in (1, 5, 10, 20):
            results[label][str(pct)] = p9c.block_bootstrap_point_hits(
                [dict(p) for p in subset], score, built, score_domain, pct, SEED + pct + (100 if label.startswith("urban") else 0), reps=2000, landcover_grid=lc)
    metrics = {
        "label": "PHYSICAL, NOT FITTED TO LABELS; rank score, not probability",
        "input_table": "data/features/static/cell_table_phase9b_v2.parquet",
        "drainage_source": "data/features/osm/chennai_osm_features.gpkg layer waterways",
        "drainage_feature_count": int(len(waterways)), "rasterized_drainage_cells": int(drainage.sum()),
        "valid_cma_cells": int(valid.sum()), "valid_score_cells": int(score_domain.sum()),
        "nearest_drainage_height_definition": "max(DEM elevation at CMA cell minus DEM elevation at nearest rasterized OSM waterway cell, 0); Euclidean distance in EPSG:32644, 30 m pixels; no flow direction used",
        "score_components": ["inverse empirical rank of nearest-drainage height", "empirical rank of local depression depth", "inverse ranks of 5/15/33-cell relative elevation", "inverse empirical rank of distance to OSM drainage"],
        "urban_proxy": "built_up_fraction >= 0.30; analytical stratum only",
        "point_validation": results,
        "point_limit": "OpenCity point dates unclear and locations approximate; this is a spatial cross-check, not dated event validation.",
        "seed": SEED, "bootstrap_replicates": 2000,
        "limitations": ["OSM drainage completeness and positional accuracy are uncertain.", "Nearest-channel cell elevation is a Euclidean proxy, not a hydraulic HAND calculation.", "Existing relative-elevation and depression fields were reused; no old feature was changed."]
    }
    METRICS.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    def pct(x): return "not estimable" if x is None else f"{100*x:.2f}%"
    report = ["# Urban physical susceptibility layer", "", "Status: **PHYSICAL, NOT FITTED TO LABELS.** This is a rank score, not a calibrated flood probability or forecast.", "",
      "## Method", "", f"Rasterized {len(waterways):,} existing OSM waterway line features onto the EPSG:32644 30 m DEM grid ({int(drainage.sum()):,} valid drainage pixels). For each CMA cell, the nearest drainage pixel was selected by Euclidean distance, without D8 flow routing. Height is `max(cell DEM − nearest drainage-pixel DEM, 0 m)`. The score averages empirical rank components: lower nearest-drainage height, higher local depression, lower relative elevation at 5/15/33 cells, and shorter drainage distance. This relative score has no probability interpretation.", "", "The relative-elevation and local-depression values were read from the existing Phase 9B v2 cell table and copied into new rasters; the table and legacy D8 HAND were not modified. Only cells with all terrain components available are scored. Built-up fraction >=0.30 is used as a descriptive urban-point stratum.", "", "## OpenCity independent spatial cross-check", "", "The points have unclear dates and approximate locations, so point hits do not validate a dated event. Confidence intervals use 2,000 resamples of 3 km point blocks. Matched chance selects random score-domain cells with matching built-up bin and dominant land-cover class.", "", "| Point set | Top rank share | Hit share (95% CI) | Matched chance (95% CI) | Scored points |", "|---|---:|---:|---:|---:|"]
    for label, title in [("all_scored", "All scored points"), ("urban_proxy_built_up_ge_0p30", "Urban proxy: built-up >=0.30")]:
        for k, d in results[label].items():
            ci=d.get("observed_ci_95"); cci=d.get("matched_chance_ci_95")
            fmt=lambda v, bounds: "not estimable" if v is None else f"{pct(v)} ({pct(bounds[0])}–{pct(bounds[1])})" if bounds else pct(v)
            report.append(f"| {title} | {k}% | {fmt(d.get('observed_share'),ci)} | {fmt(d.get('matched_chance_share'),cci)} | {d.get('n',0)} |")
    report += ["", "The matching is by built-up-fraction bin and dominant land-cover class, not exact fractional land-cover composition. The confidence intervals reflect the available spatial point blocks and should be read cautiously.", "", "## Outputs", "", "New rasters and machine-readable results are in `data/features/terrain/urban_physical_v1/`. The source Phase 9B cell table remains unchanged.", ""]
    REPORT.write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({"valid_cma_cells": int(valid.sum()), "valid_score_cells": int(score_domain.sum()), "drainage_features": len(waterways), "point_counts": {k: v["1"]["n"] for k,v in results.items()}, "output": str(OUT.relative_to(ROOT)), "report": str(REPORT.relative_to(ROOT))}, indent=2))


if __name__ == "__main__":
    run()
