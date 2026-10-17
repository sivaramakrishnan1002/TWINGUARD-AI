#!/usr/bin/env python
"""Build the DERIVED 30 m CMA cell table without changing existing features."""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import rowcol
from shapely import points
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data/features/static"
OUT = OUT_DIR / "cell_table.parquet"
DICT = OUT_DIR / "cell_table_data_dictionary.json"
MASK = ROOT / "data/processed/grid/cma_mask.tif"
FEATURES = {
    "elevation_m": ROOT / "data/processed/terrain_cleaned/cleaned_elevation_m.tif",
    "slope_deg": ROOT / "data/processed/terrain_cleaned/slope_deg_edge_safe.tif",
    "twi_d8_proxy": ROOT / "data/processed/terrain_cleaned/twi_d8_proxy_edge_safe.tif",
    "flow_accumulation_cells_d8": ROOT / "data/processed/terrain_cleaned/flow_accumulation_cells_d8.tif",
    "worldpop_2021": ROOT / "data/features/population/worldpop_2021_sum_resampled_30m.tif",
}
LANDCOVER = ROOT / "data/features/landcover/worldcover_2021_area_fractions_30m.tif"
BUILDINGS = ROOT / "data/features/buildings/chennai_building_footprints.gpkg"
WATERWAYS = ROOT / "data/features/hydrology/chennai_waterways.gpkg"
OSM_FEATURES = ROOT / "data/features/osm/chennai_osm_features.gpkg"
TARGET_RIVER_NAMES = {"Adyar River", "Cooum", "Kosasthalaiyar River", "Buckingham Canal"}


def nearest_m(x: np.ndarray, y: np.ndarray, geometries, chunk: int = 20000) -> np.ndarray:
    """Vectorized nearest geometry distance, processed in chunks."""
    tree = STRtree(np.asarray(geometries, dtype=object))
    result = np.full(len(x), np.nan, dtype="float32")
    for start in range(0, len(x), chunk):
        stop = min(start + chunk, len(x))
        query_points = points(x[start:stop], y[start:stop])
        _, distances = tree.query_nearest(query_points, all_matches=False, return_distance=True)
        result[start:stop] = distances.astype("float32")
    return result


def main() -> int:
    if OUT.exists() or DICT.exists():
        raise FileExistsError("Refusing to overwrite existing static table target(s)")
    # Do this before any large spatial work; no system/global installation is attempted.
    import pyarrow  # noqa: F401, PLC0415

    with rasterio.open(MASK) as mask_ds:
        mask = mask_ds.read(1)
        rows, cols = np.nonzero(mask == 1)
        transform, crs, profile = mask_ds.transform, mask_ds.crs, mask_ds.profile.copy()
        grid_shape = (mask_ds.width, mask_ds.height)
        x = transform.c + (cols + 0.5) * transform.a
        y = transform.f + (rows + 0.5) * transform.e
    import pandas as pd
    table = pd.DataFrame({"row": rows.astype("int32"), "col": cols.astype("int32"),
                          "x": x, "y": y,
                          "cell_id": [f"32644:{r}:{c}" for r, c in zip(rows, cols)]})

    for name, path in FEATURES.items():
        with rasterio.open(path) as src:
            if (src.width, src.height, src.transform, src.crs) != (*grid_shape, transform, crs):
                raise ValueError(f"Feature is not aligned with CMA grid: {path.relative_to(ROOT)}")
            values = src.read(1)[rows, cols].astype("float64")
            if src.nodata is not None:
                values[values == src.nodata] = np.nan
            table[name] = values
    table["population_is_nodata"] = table["worldpop_2021"].isna()

    with rasterio.open(LANDCOVER) as src:
        if (src.width, src.height, src.transform, src.crs) != (*grid_shape, transform, crs):
            raise ValueError("WorldCover fractions are not aligned with CMA grid")
        names = list(src.descriptions)
        def band_for(code: int) -> int:
            label = f"class_{code}_area_fraction"
            if label not in names:
                raise ValueError(f"Land-cover fraction band not found: {label}; descriptions={names}")
            return names.index(label) + 1
        table["built_up_fraction"] = src.read(band_for(50))[rows, cols]
        table["water_fraction"] = src.read(band_for(80))[rows, cols]

    bld = gpd.read_file(BUILDINGS).to_crs(crs)
    centroids = bld.geometry.centroid
    br, bc = rowcol(transform, centroids.x.to_numpy(), centroids.y.to_numpy())
    br, bc = np.asarray(br), np.asarray(bc)
    inside = (br >= 0) & (br < mask.shape[0]) & (bc >= 0) & (bc < mask.shape[1])
    inside_idx = np.flatnonzero(inside)
    inside_idx = inside_idx[mask[br[inside_idx], bc[inside_idx]] == 1]
    flat_counts = np.bincount(br[inside_idx] * mask.shape[1] + bc[inside_idx],
                               minlength=mask.size)
    table["building_density_per_km2"] = flat_counts[rows * mask.shape[1] + cols] / 0.0009

    nodes = gpd.read_file(OSM_FEATURES, layer="road_nodes").to_crs(crs)
    table["distance_to_nearest_road_node_m"] = nearest_m(x, y, nodes.geometry.to_numpy())

    rivers = gpd.read_file(WATERWAYS, layer="waterways").to_crs(crs)
    exact = rivers[rivers["name"].isin(TARGET_RIVER_NAMES)]
    if len(exact):
        table["distance_to_exact_named_waterway_m"] = nearest_m(x, y, exact.geometry.to_numpy())
    else:
        table["distance_to_exact_named_waterway_m"] = np.nan
    found_names = sorted(set(exact["name"].dropna().astype(str)))
    table["distance_to_coast_m"] = np.nan
    table["coast_distance_available"] = False

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    temp = OUT.with_suffix(".parquet.tmp")
    table.to_parquet(temp, index=False, engine="pyarrow")
    temp.replace(OUT)
    metadata = {
        "status": "DERIVED", "crs": "EPSG:32644", "cell_size_m": 30,
        "rows": len(table), "expected_cma_cells": int(len(rows)),
        "row_count_matches_cma_mask": len(table) == int((mask == 1).sum()),
        "river_names_matched_in_saved_waterways_layer": found_names,
        "river_names_not_found": sorted(TARGET_RIVER_NAMES - set(found_names)),
        "coast_distance": "not computed: no dedicated coastline feature layer is present in the saved feature layers",
        "population_nodata": "preserved as null with population_is_nodata flag; not converted to zero",
        "building_density": "OSM footprint centroid count per 30 m cell divided by 0.0009 km2; not building occupancy",
        "files": {"table": OUT.relative_to(ROOT).as_posix(), "dictionary": DICT.relative_to(ROOT).as_posix()},
    }
    DICT.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"WROTE={OUT.relative_to(ROOT)}; ROWS={len(table)}; CMA_CELLS={int((mask == 1).sum())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
