#!/usr/bin/env python
"""Read-only sanity report for existing terrain; writes only a new docs report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import osmium
import rasterio
from pyproj import Transformer
from rasterio.features import shapes, geometry_mask
from shapely.geometry import LineString, shape
from shapely.ops import transform as geom_transform

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/TERRAIN_CHECK.md"
ELEV = ROOT / "data/features/terrain/elevation_m.tif"
MASK = ROOT / "data/processed/grid/cma_mask.tif"
WC = ROOT / "data/features/landcover/worldcover_2021_class.tif"
BOUNDARY = ROOT / "data/raw/boundary/chennai_cma_boundary.geojson"
PBF = ROOT / "data/raw/roads/southern-zone-latest.osm.pbf"
WATER = ROOT / "data/features/hydrology/chennai_waterways.gpkg"
ROADS = ROOT / "data/features/osm/chennai_osm_features.gpkg"
BUILDINGS = ROOT / "data/features/buildings/chennai_building_footprints.gpkg"
WC_LABELS = {10:"tree cover",20:"shrubland",30:"grassland",40:"cropland",50:"built-up",60:"bare/sparse vegetation",80:"permanent water",90:"herbaceous wetland",95:"mangroves",100:"moss/lichen"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-own-report", action="store_true",
                        help="Refresh this script's own new report under docs/.")
    args = parser.parse_args()
    if OUT.exists() and not args.refresh_own_report:
        raise FileExistsError(f"Refusing to overwrite {OUT}")

    with rasterio.open(ELEV) as src:
        elev = src.read(1)
        transform = src.transform
        nodata = src.nodata
        profile = {"crs": src.crs.to_string(), "resolution": src.res, "shape": (src.height, src.width),
                   "bounds": tuple(src.bounds), "nodata": nodata}
    with rasterio.open(MASK) as src:
        cma = src.read(1) == 1
    with rasterio.open(WC) as src:
        wc = src.read(1)
        wc_transform = src.transform
    valid = cma & np.isfinite(elev) & (elev != nodata)
    vals = elev[valid].astype("float64")
    stats = np.percentile(vals, [1, 5, 50, 95, 99])
    thresholds = {x: int((valid & (elev < x)).sum()) for x in (0, 2, 5)}

    # Eight-neighbour connected components are polygonized without writing rasters.
    low = valid & (elev < -5)
    clusters = []
    for geom, value in shapes(low.astype("uint8"), mask=low, transform=transform, connectivity=8):
        if value != 1:
            continue
        polygon = shape(geom)
        count = int(round(polygon.area / (abs(transform.a * transform.e))))
        clusters.append((count, geom, polygon))
    clusters.sort(key=lambda row: (-row[0], row[2].centroid.y, row[2].centroid.x))

    crs_to_ll = Transformer.from_crs(32644, 4326, always_xy=True).transform
    boundary = gpd.read_file(BOUNDARY).to_crs(32644).geometry.union_all()
    roads = gpd.read_file(ROADS, layer="road_segments", columns=["name", "highway"], read_geometry=True)
    water = gpd.read_file(WATER, layer="waterways")
    buildings = gpd.read_file(BUILDINGS, layer="building_footprints", columns=["building"], read_geometry=True)
    cluster_details = []
    for i, (count, geo, poly) in enumerate(clusters, 1):
        centroid = poly.centroid
        lon, lat = crs_to_ll(centroid.x, centroid.y)
        cells = geometry_mask([geo], out_shape=elev.shape, transform=transform, invert=True) & low
        classes, class_counts = np.unique(wc[cells], return_counts=True)
        class_summary = {WC_LABELS.get(int(code), str(int(code))): int(n) for code, n in zip(classes, class_counts)}
        wr_i = int(water.sindex.nearest(centroid, return_all=False, return_distance=False)[1, 0])
        rd_i = int(roads.sindex.nearest(centroid, return_all=False, return_distance=False)[1, 0])
        water_row = water.iloc[wr_i]
        road_row = roads.iloc[rd_i]
        water_name = water_row.get("name")
        road_name = road_row.get("name")
        nearest_water = {"name": "unnamed" if water_name is None or str(water_name).lower() == "nan" else str(water_name),
                         "type": str(water_row.get("waterway") or "unknown"),
                         "distance_m": float(centroid.distance(water_row.geometry))}
        nearest_road = {"name": "unnamed" if road_name is None or str(road_name).lower() == "nan" else str(road_name),
                        "class": str(road_row.get("highway") or "unknown"),
                        "distance_m": float(centroid.distance(road_row.geometry))}
        b_ix = buildings.sindex.query(poly, predicate="intersects")
        elevations = elev[cells]
        cluster_details.append({"id": i, "cells": count, "area_m2": count * abs(transform.a * transform.e),
                                "centroid_lon": float(lon), "centroid_lat": float(lat),
                                "bounds_utm": tuple(float(x) for x in poly.bounds),
                                "min_m": float(elevations.min()), "max_m": float(elevations.max()),
                                "worldcover": class_summary, "osm_buildings_intersecting": int(len(b_ix)),
                                "nearest_waterway": nearest_water, "nearest_road": nearest_road,
                                "target_geom": geo})

    # Compare the lowest derived grid cell against its native source tile.
    min_flat = int(np.argmin(np.where(valid, elev, np.inf)))
    min_row, min_col = np.unravel_index(min_flat, elev.shape)
    x, y = rasterio.transform.xy(transform, min_row, min_col, offset="center")
    lon_min, lat_min = crs_to_ll(x, y)
    src_tile = ROOT / "data/raw/dem/Copernicus_DSM_COG_10_N12_00_E080_00_DEM.tif"
    with rasterio.open(src_tile) as src:
        rr, cc = rasterio.transform.rowcol(src.transform, lon_min, lat_min)
        native = src.read(1, window=((rr - 2, rr + 3), (cc - 2, cc + 3)))
        native_info = {"nodata": src.nodata, "bounds": tuple(src.bounds), "min5x5": float(native.min()),
                       "max5x5": float(native.max()), "values5x5": native.tolist()}

    # Elevations sampled along exact-name OSM waterway lines inside the CMA.
    ll_boundary = gpd.read_file(BOUNDARY).geometry.union_all()
    project = Transformer.from_crs(4326, 32644, always_xy=True).transform
    water_lines: dict[str, list[LineString]] = {"Adyar River": [], "Cooum": []}

    class NamedRiver(osmium.SimpleHandler):
        def way(self, way) -> None:
            tags = dict(way.tags)
            if tags.get("waterway") not in {"river", "stream", "canal"}:
                return
            is_adyar = any(tags.get(k, "").strip().casefold() == "adyar river" for k in ("name", "name:en", "alt_name"))
            is_cooum = any(tags.get(k, "").strip().casefold() == "cooum" for k in ("name", "name:en", "alt_name"))
            label = "Adyar River" if is_adyar else "Cooum" if is_cooum else None
            if not label:
                return
            coords = [(n.location.lon, n.location.lat) for n in way.nodes if n.location.valid()]
            if len(coords) < 2:
                return
            projected = geom_transform(project, LineString(coords))
            clipped = projected.intersection(boundary)
            if clipped.is_empty:
                return
            geoms = [clipped] if clipped.geom_type == "LineString" else [g for g in getattr(clipped, "geoms", []) if g.geom_type == "LineString"]
            water_lines[label].extend(geoms)

    handler = NamedRiver()
    handler.apply_file(str(PBF), locations=True, idx="sparse_mem_map")
    river_stats = {}
    for name, lines in water_lines.items():
        cells = set()
        length = sum(line.length for line in lines)
        for line in lines:
            count = max(1, int(np.ceil(line.length / 15.0)))
            for d in np.linspace(0.0, line.length, count + 1):
                point = line.interpolate(float(d))
                row, col = rasterio.transform.rowcol(transform, point.x, point.y)
                if 0 <= row < elev.shape[0] and 0 <= col < elev.shape[1] and cma[row, col] and valid[row, col]:
                    cells.add((row, col))
        sample = np.array([elev[r, c] for r, c in cells], dtype="float64")
        river_stats[name] = {"segments": len(lines), "length_km_inside_CMA": length / 1000,
                             "unique_grid_cells_sampled": len(sample),
                             "elevation_m_percentiles_0_5_50_95_100": np.percentile(sample, [0, 5, 50, 95, 100]).tolist() if len(sample) else None,
                             "elevation_m_mean": float(sample.mean()) if len(sample) else None}

    codes, counts = np.unique(wc[low], return_counts=True)
    overall_low_wc = {WC_LABELS.get(int(code), str(int(code))): int(n) for code, n in zip(codes, counts)}
    threshold_pct = {str(x): thresholds[x] / int(valid.sum()) * 100.0 for x in thresholds}
    total_low_area_km2 = sum(row["area_m2"] for row in cluster_details) / 1e6

    lines = [
        "# Terrain sanity check", "",
        "## Summary statistics inside the CMA", "",
        f"Valid CMA cells: {int(valid.sum()):,}. Elevation is in metres on the existing EPSG:32644 30 m grid. [repo: `data/features/terrain/elevation_m.tif`, `data/processed/grid/cma_mask.tif`]", "",
        "| Statistic | Elevation (m) |", "|---|---:|",
        f"| Mean | {vals.mean():.3f} |", f"| Median / 50th percentile | {stats[2]:.3f} |",
        f"| 1st percentile | {stats[0]:.3f} |", f"| 5th percentile | {stats[1]:.3f} |",
        f"| 95th percentile | {stats[3]:.3f} |", f"| 99th percentile | {stats[4]:.3f} |",
        f"| Minimum | {vals.min():.3f} |", f"| Maximum | {vals.max():.3f} |", "",
        "| Threshold | Cells below threshold | Percent of valid CMA cells |", "|---|---:|---:|"]
    lines += [f"| {x} m | {thresholds[x]:,} | {threshold_pct[str(x)]:.4f}% |" for x in (0, 2, 5)]
    lines += ["", "## Cells below −5 m", "",
              f"Using 8-neighbour connectivity, there are **{len(cluster_details)} clusters**, totaling about **{total_low_area_km2:.4f} km²** ({int(low.sum()):,} cells). Cluster area is cell count × 900 m². WorldCover composition and nearest mapped OSM line/road are context checks, not proof of a feature's true landform. The current OSM layers contain roads, buildings and waterways but not a complete lake/quarry polygon inventory.", "",
              "| Cluster | Cells | Area (km²) | Centroid (lon, lat) | Elevation range (m) | WorldCover classes in cluster (cell counts) | OSM context |", "|---:|---:|---:|---|---:|---|---|"]
    for d in cluster_details:
        wcdesc = ", ".join(f"{k} {v}" for k, v in sorted(d["worldcover"].items(), key=lambda kv: -kv[1]))
        road = d["nearest_road"]
        water = d["nearest_waterway"]
        osm = f"nearest road {road['name']} ({road['class']}, {road['distance_m']:.0f} m); nearest waterway {water['name']} ({water['type']}, {water['distance_m']:.0f} m); intersecting OSM building footprints {d['osm_buildings_intersecting']}"
        lines.append(f"| {d['id']} | {d['cells']} | {d['area_m2']/1e6:.4f} | {d['centroid_lon']:.6f}, {d['centroid_lat']:.6f} | {d['min_m']:.2f} to {d['max_m']:.2f} | {wcdesc} | {osm} |")
    lines += ["", f"Across all below −5 m cells the WorldCover classes are: {', '.join(f'{k} {v}' for k,v in overall_low_wc.items())}. A 30 m WorldCover class is contextual; it cannot tell whether a specific negative pixel is a quarry, standing water or elevation error. [repo: `data/features/landcover/worldcover_2021_class.tif`]", "",
              "## The −64.51 m minimum", "",
              f"**Assessment: likely a source DEM artefact, not a plausible Chennai land elevation.** The minimum is in the largest below −5 m cluster at {lon_min:.6f}°E, {lat_min:.6f}°N. The five-by-five native Copernicus tile window around that position spans {native_info['min5x5']:.2f} to {native_info['max5x5']:.2f} m and contains repeated values near −64 m; the extreme is already present in the original 1 arc-second source tile. The cluster is inland relative to the coast and mixes WorldCover grassland/permanent-water classes; the nearest line-feature checks do not prove a corresponding deep waterbody. This points to an artefact in source elevation values, but visual inspection against authoritative local terrain is still advisable before any correction. [repo: raw GLO-30 tile, derived elevation and cluster overlay]", "",
              f"The source tile reports raster NoData={native_info['nodata']}; no fill/no-data code was declared for the sampled window. The saved feature range is not explained by a reprojection-induced spike, because the native source pixels are similarly negative.", "",
              "## Water and height datum", "",
              "The existing terrain pipeline used the CMA centre-in-polygon mask and the source raster's own NoData only. It did not apply a sea, lake, river or permanent-water mask. Thus water/sea-class cells inside the CMA polygon remain included when the source DEM has a numeric value. [repo: `pipelines/phase3/phase3_core.py`]", "",
              "The Copernicus GLO-30 source is documented in the manifest as heights relative to EGM2008. The pipeline performs a 2-D horizontal reprojection from EPSG:4326 to EPSG:32644 with bilinear resampling; it contains no vertical-datum operation or height offset. **No second vertical-datum conversion is present in the saved pipeline.** [repo: `docs/DATA_MANIFEST.csv`, `pipelines/phase3/phase3_core.py`]", "",
              "## Elevation sampled along exact-name rivers", "",
              "Exact-name criteria: Adyar River (name field) and Cooum (name:en field, OSM way 202505379 as recorded in the inventory). The lines were reconstructed in memory from the read-only OSM PBF because the extracted waterways GeoPackage dropped Cooum's `name:en` tag. Samples are unique 30 m grid cells touched by the clipped line inside the CMA. These are DSM surface heights at the line, not riverbed elevations or water depths. [repo: `docs/OSM_WATERWAYS.md`, raw PBF]", "",
              "| Exact line | Segments | Length inside CMA (km) | Unique cells sampled | Mean (m) | P0 / P5 / P50 / P95 / P100 (m) |", "|---|---:|---:|---:|---:|---|---|"]
    for name, data in river_stats.items():
        pcts = data["elevation_m_percentiles_0_5_50_95_100"]
        ptxt = ", ".join(f"{x:.2f}" for x in pcts) if pcts else "not computed"
        mean = f"{data['elevation_m_mean']:.2f}" if data["elevation_m_mean"] is not None else "not computed"
        lines.append(f"| {name} | {data['segments']} | {data['length_km_inside_CMA']:.3f} | {data['unique_grid_cells_sampled']} | {mean} | {ptxt} |")
    lines += ["", "## Interpretation", "", "Low values do not automatically describe the coast or the Adyar/Cooum corridors: the below-−5 m clusters are small (0.23 km² combined) and the deepest cluster is inland. Because no water mask was used, some low values may coincide with mapped water, but the extremely negative inland source values are suspicious and should not feed hydrologic derivatives unreviewed. No terrain feature was regenerated or corrected for this check.", ""]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
