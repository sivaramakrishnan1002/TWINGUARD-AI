# Terrain sanity check

## Summary statistics inside the CMA

Valid CMA cells: 1,319,380. Elevation is in metres on the existing EPSG:32644 30 m grid. [repo: `data/features/terrain/elevation_m.tif`, `data/processed/grid/cma_mask.tif`]

| Statistic | Elevation (m) |
|---|---:|
| Mean | 16.770 |
| Median / 50th percentile | 15.395 |
| 1st percentile | 0.997 |
| 5th percentile | 2.820 |
| 95th percentile | 33.768 |
| 99th percentile | 43.218 |
| Minimum | -64.509 |
| Maximum | 168.703 |

| Threshold | Cells below threshold | Percent of valid CMA cells |
|---|---:|---:|
| 0 m | 634 | 0.0481% |
| 2 m | 38,070 | 2.8854% |
| 5 m | 159,031 | 12.0535% |

## Cells below −5 m

Using 8-neighbour connectivity, there are **8 clusters**, totaling about **0.2295 km²** (255 cells). Cluster area is cell count × 900 m². WorldCover composition and nearest mapped OSM line/road are context checks, not proof of a feature's true landform. The current OSM layers contain roads, buildings and waterways but not a complete lake/quarry polygon inventory.

| Cluster | Cells | Area (km²) | Centroid (lon, lat) | Elevation range (m) | WorldCover classes in cluster (cell counts) | OSM context |
|---:|---:|---:|---|---:|---|---|
| 1 | 130 | 0.1170 | 80.112080, 12.953406 | -64.51 to -5.13 | permanent water 59, grassland 55, bare/sparse vegetation 10, tree cover 3, shrubland 3 | nearest road unnamed (residential, 162 m); nearest waterway Adyar River (river, 948 m); intersecting OSM building footprints 0 |
| 2 | 62 | 0.0558 | 80.097854, 13.014960 | -12.00 to -5.01 | permanent water 61, tree cover 1 | nearest road unnamed (residential, 47 m); nearest waterway Chembarambakkam irrigation canal (canal, 792 m); intersecting OSM building footprints 0 |
| 3 | 20 | 0.0180 | 80.231613, 12.946639 | -11.50 to -5.15 | bare/sparse vegetation 19, permanent water 1 | nearest road unnamed (service, 73 m); nearest waterway unnamed (river, 565 m); intersecting OSM building footprints 2 |
| 4 | 20 | 0.0180 | 80.096759, 13.012474 | -6.00 to -5.10 | permanent water 16, grassland 3, bare/sparse vegetation 1 | nearest road unnamed (residential, 221 m); nearest waterway Chembarampakkam water for irrigation (stream, 623 m); intersecting OSM building footprints 0 |
| 5 | 13 | 0.0117 | 80.263527, 13.189686 | -16.82 to -5.01 | built-up 8, tree cover 4, permanent water 1 | nearest road unnamed (service, 138 m); nearest waterway unnamed (drain, 992 m); intersecting OSM building footprints 1 |
| 6 | 5 | 0.0045 | 80.074028, 12.946697 | -8.59 to -5.30 | permanent water 3, bare/sparse vegetation 2 | nearest road unnamed (residential, 131 m); nearest waterway unnamed (drain, 1162 m); intersecting OSM building footprints 0 |
| 7 | 4 | 0.0036 | 80.302013, 13.236545 | -9.21 to -5.22 | tree cover 3, built-up 1 | nearest road unnamed (tertiary, 129 m); nearest waterway unnamed (stream, 902 m); intersecting OSM building footprints 0 |
| 8 | 1 | 0.0009 | 80.222127, 12.973059 | -5.85 to -5.85 | built-up 1 | nearest road unnamed (residential, 21 m); nearest waterway unnamed (drain, 201 m); intersecting OSM building footprints 5 |

Across all below −5 m cells the WorldCover classes are: tree cover 11, shrubland 3, grassland 58, built-up 10, bare/sparse vegetation 32, permanent water 141. A 30 m WorldCover class is contextual; it cannot tell whether a specific negative pixel is a quarry, standing water or elevation error. [repo: `data/features/landcover/worldcover_2021_class.tif`]

## The −64.51 m minimum

**Assessment: likely a source DEM artefact, not a plausible Chennai land elevation.** The minimum is in the largest below −5 m cluster at 80.112116°E, 12.952906°N. The five-by-five native Copernicus tile window around that position spans -65.55 to -50.48 m and contains repeated values near −64 m; the extreme is already present in the original 1 arc-second source tile. The cluster is inland relative to the coast and mixes WorldCover grassland/permanent-water classes; the nearest line-feature checks do not prove a corresponding deep waterbody. This points to an artefact in source elevation values, but visual inspection against authoritative local terrain is still advisable before any correction. [repo: raw GLO-30 tile, derived elevation and cluster overlay]

The source tile reports raster NoData=None; no fill/no-data code was declared for the sampled window. The saved feature range is not explained by a reprojection-induced spike, because the native source pixels are similarly negative.

## Water and height datum

The existing terrain pipeline used the CMA centre-in-polygon mask and the source raster's own NoData only. It did not apply a sea, lake, river or permanent-water mask. Thus water/sea-class cells inside the CMA polygon remain included when the source DEM has a numeric value. [repo: `pipelines/phase3/phase3_core.py`]

The Copernicus GLO-30 source is documented in the manifest as heights relative to EGM2008. The pipeline performs a 2-D horizontal reprojection from EPSG:4326 to EPSG:32644 with bilinear resampling; it contains no vertical-datum operation or height offset. **No second vertical-datum conversion is present in the saved pipeline.** [repo: `docs/DATA_MANIFEST.csv`, `pipelines/phase3/phase3_core.py`]

## Elevation sampled along exact-name rivers

Exact-name criteria: Adyar River (name field) and Cooum (name:en field, OSM way 202505379 as recorded in the inventory). The lines were reconstructed in memory from the read-only OSM PBF because the extracted waterways GeoPackage dropped Cooum's `name:en` tag. Samples are unique 30 m grid cells touched by the clipped line inside the CMA. These are DSM surface heights at the line, not riverbed elevations or water depths. [repo: `docs/OSM_WATERWAYS.md`, raw PBF]

| Exact line | Segments | Length inside CMA (km) | Unique cells sampled | Mean (m) | P0 / P5 / P50 / P95 / P100 (m) |
|---|---:|---:|---:|---:|---|---|
| Adyar River | 4 | 36.279 | 1355 | 8.01 | 0.00, 0.50, 7.48, 16.83, 19.52 |
| Cooum | 1 | 41.390 | 1539 | 13.03 | 0.00, 0.90, 11.47, 26.85, 32.17 |

## Interpretation

Low values do not automatically describe the coast or the Adyar/Cooum corridors: the below-−5 m clusters are small (0.23 km² combined) and the deepest cluster is inland. Because no water mask was used, some low values may coincide with mapped water, but the extremely negative inland source values are suspicious and should not feed hydrologic derivatives unreviewed. No terrain feature was regenerated or corrected for this check.
