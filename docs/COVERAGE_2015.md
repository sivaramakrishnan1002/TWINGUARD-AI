# 2015 flood and footprint coverage within the old CMA

## Computed results

Boundary area used: 1,187.460287 km² in EPSG:32644. Values below are area of dissolved polygon union intersecting the CMA. Percentages use the boundary area above.

| Image date | Flood area inside CMA | CMA flooded (%) | Analysis footprint inside CMA | CMA observed (%) |
|---|---:|---:|---:|---:|
| 12 Nov 2015 | 84.924564 km² | 7.151781% | 1,187.460287 km² | 100.000000% |
| 24 Nov 2015 | 98.313748 km² | 8.279329% | 1,187.460287 km² | 100.000000% |

These dates are November observations and do not describe the December 1–2 peak. The analysis-extent polygons fully cover this CMA geometry, but satellite-derived flood polygons cover only the stated percentages. Extent coverage is not evidence that the rest of the CMA was dry at those dates.

## Exact method

Used the project-local `.venv` with GeoPandas 1.2.0, pyogrio 0.13.0, Shapely 2.2.0 and pyproj (EPSG:32644 transformation). Opened the existing ZIP read-only via GDAL `/vsizip/` paths; no extraction or derived spatial file was created. Loaded the CMA GeoJSON and dissolved its one feature in memory. For each flood layer, queried the GeoPandas spatial index with exact `intersects` against the CMA boundary in WGS84, transformed only candidate flood geometries and the boundary to EPSG:32644, repaired invalid candidate geometries in memory with `shapely.make_valid`, unioned/dissolved the candidates with `shapely.union_all`, intersected that union with the CMA, then measured planar square metres and converted to km². The 12 Nov layer had 4,704 candidate polygons, 34 initially invalid; the 24 Nov layer had 3,710 candidates, 120 initially invalid. Both one-feature analysis extents intersected the CMA and were measured separately with the same CRS and intersection method. Percentages are `100 × area inside CMA / 1,187.460287 km²`.

Results are spatial-analysis estimates dependent on source geometry validity and the stated equal-area-appropriate local UTM projection. No ground validation was performed. Raw ZIP and boundary remain unchanged.

Study boundary area and results above are based on the existing UNOSAT archive. The archive's other layers and inventory are documented in `DATA_QUALITY_REPORT.md`; bboxes alone are not footprint coverage.

## Reproducible QGIS procedure

1. Open the existing `data/raw/boundary/chennai_cma_boundary.geojson` in QGIS.
2. Open the ZIP read-only as a virtual layer source, e.g. `/vsizip/D:/TIWNGUARD/data/raw/historical_floods/2015/2015-12-04/FL20151123IND_shp.zip/S1_20151112_Flood.shp`. Repeat for `S1_20151124_Flood.shp` and both corresponding `*_Analysis_Extent.shp` layers. Do not extract or alter the archive.
3. Set the project CRS to EPSG:32644 and use **Reproject layer** to create temporary/in-memory copies only. Confirm all input CRSs before transforming.
4. Run **Dissolve** on each flood layer (no dissolve field) to union overlapping polygons, then **Intersection** with the projected CMA boundary. Separately intersect each analysis extent with the CMA boundary.
5. Read the resulting geometry area in square metres, divide by 1,000,000 for km², and calculate `100 * area_km2 / 1187.46`. For footprint coverage, use the dissolved extent-intersection area; do not combine it with flooded area.
6. Check geometry validity, CRS, units, and that union area is not greater than CMA area. Save only the numeric results and method in this document; do not save derived spatial files.

No December 2015 flood layer was downloaded in this run. Bhuvan publicly lists 03 Dec, 04 Dec, 05 Dec, 05–07 Dec and 08 Dec layers and a Chennai experimental cumulative RISAT-1 (3, 4, 6 Dec) layer, but this inspection did not find a direct public data-file link for the layers. The official page directs users to a “Click here to zoom” map viewer. Request vector/rasters from NRSC or manually use the viewer; see `MANUAL_TODO.md`.
