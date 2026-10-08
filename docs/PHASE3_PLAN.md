# Phase 3 plan — feature engineering and label preparation

**Status: planning only. No source data has been processed for Phase 3.** This plan describes proposed inputs, methods, outputs, spatial alignment, and checks. Resolve the boundary and label availability decisions before implementation.

## Shared spatial and time conventions

- **Study boundary:** use the currently collected older, pre-2022 CMA GeoJSON provisionally (about 1,187.46 km²). Confirm whether the study requires the expanded CMA before building final features.
- **Common analysis CRS:** use WGS 84 / UTM zone 44N (EPSG:32644) for the Chennai-area metric analysis, subject to confirming that every source is correctly georeferenced before reprojection. Keep original source CRS and metadata intact.
- **Proposed analysis grid:** use a 10 m grid aligned to the selected Sentinel-1 reference raster and snapped to a documented origin covering the chosen study boundary plus required context. This is a planning choice, not a claim that every source has 10 m information. Preserve source-resolution products; do not upsample coarse products and describe them as higher-resolution observations. Aggregate or resample according to data type, and document the method and nodata rules per layer. Revisit the grid if the selected Sentinel-1 product or project requirements make 10 m unsuitable.
- **Time:** store timestamps in UTC with source time zone and acquisition/valid-time metadata retained. Define event windows from documented event references; do not select scenes or labels based only on nominal event year.
- **Provenance:** every output should retain source identifiers, source dates, processing parameters, software versions, CRS/grid, nodata handling, and validation results.

## Planned data workstreams

### 1. Rainfall sequences

- **Inputs:** collected Open-Meteo ERA5 and NASA POWER point-series data; if later authorized and available, ERA5 CDS, GPM IMERG, and/or IMD observations. Current point and product coverage limitations are recorded in `DATA_QUALITY_REPORT.md` and `DATA_MANIFEST.csv`.
- **Tools:** Python with pandas/xarray and requests/API clients as appropriate; geopandas/rasterio for spatial joins or gridded rainfall. Use documented timezone and units conversions.
- **Planned outputs:** validated timestamped rainfall tables per location/source; event-window sequences and summaries such as rolling accumulations and antecedent rainfall; optionally spatial rainfall grids only when source sampling supports them.
- **CRS/grid:** point data retain WGS84 coordinates; spatial features are transformed to EPSG:32644 for analysis. A 10 m output grid does not add detail to coarse reanalysis or sparse points; preserve native support or use a justified interpolation/aggregation with uncertainty metadata.
- **Validation checks:** monotonic unique timestamps per series; expected temporal cadence and event-window coverage; units and timezone consistency; missing/duplicate/outlier checks; compare overlapping sources and note shared/coarse grid cells; ensure no future-time leakage into predictors.

### 2. DEM terrain and hydrology features

- **Inputs:** collected Copernicus GLO-30 DEM tiles covering the boundary and a hydrologically sufficient surrounding area.
- **Tools:** rasterio/GDAL and a documented hydrology workflow (for example WhiteboxTools or GRASS/QGIS) for mosaicking, sink handling, flow direction, and accumulation. Select and record the exact algorithm and parameters before running it.
- **Planned outputs:** elevation, slope, flow accumulation, and topographic wetness index (TWI), plus any intermediate hydrology surfaces needed for reproducibility. Keep source DSM/DEM distinctions and vertical datum metadata.
- **CRS/grid:** retain source tiles unchanged; reproject an analysis copy to EPSG:32644. Derive hydrology at the source DEM's effective resolution first; if a common 10 m grid is adopted, document any resampling and do not imply that resampling increases DEM detail. Ensure one consistent grid transform, dimensions, extent, and nodata mask for aligned outputs.
- **Validation checks:** source tile adjacency/overlap and nodata seams; horizontal and vertical units/datum; plausible elevation and slope ranges; compare flow paths/accumulation with drainage context; verify sinks/flats treatment and TWI handling of zero/undefined values; inspect boundary edges and hydrologic context beyond the CMA.

### 3. Flood labels and label risk

- **Inputs:** the 2015 UNOSAT archive and collected NRSC/NDEM PDFs for 2021 and 2023. Only the collected 2015 UNOSAT observations are vector flood layers. Those observations include 1 Sep, 14 Oct, 12 Nov, and 24 Nov 2015; they do not cover the **1–8 Dec 2015 peak**. The 2021 and 2023 products are PDF map sheets, not GIS-ready polygons, and need manual digitising for spatial labels.
- **Tools:** geopandas/Shapely/GDAL for vector inspection and geometry validation; QGIS georeferencer and digitising tools for PDF map interpretation when map controls/legend permit; a separately specified and validated Sentinel-1 classification workflow as an alternative label source.
- **Planned outputs:** date-specific inundation label geometries or rasters with source/date, class meaning, digitising or derivation method, confidence/uncertainty, and validation provenance. Keep observed, manually digitised, and algorithm-derived labels clearly distinguished.
- **CRS/grid:** preserve vector source coordinates and map georeferencing metadata; transform defensible label geometries to EPSG:32644. Raster labels should be aligned to the documented analysis grid using nearest-neighbour categorical assignment, with no interpolation of class IDs. Record georeferencing residuals and rasterization rules.
- **Validation checks:** verify event/acquisition date, source map legend and footprint, CRS and control-point residuals, topology/geometry validity, boundary coverage, class semantics, and positional uncertainty. Check for standing water/paddy ambiguity and urban SAR omissions. Do not use November 2015 as a proxy for December peak observations.

#### Baseline-water reference idea — verify before use

Consider the 1 Sep and 14 Oct 2015 UNOSAT pre-flood layers as a baseline-water reference when interpreting later flood labels. This is an idea to verify, not an established rule. Confirm the meaning of the source's “PreFlood” classes, seasonal/acquisition comparability, and suitability for the event before use. If supported, maintain baseline water as a separate reference class; do not automatically call it flood water or subtract it without a documented method.

#### If December 2015 layers are never obtained

Choose and document a fallback before producing labels:

1. **Digitise from PDFs:** georeference and manually digitise relevant NRSC map sheets only where their frame, scale, legend, and spatial reference support defensible mapping. Record control points, residuals, interpretation choices, digitiser, and uncertainty; mark these as digitised derivatives, not original vector data.
2. **Derive labels from Sentinel-1:** classify suitable pre-event/event scenes with a separately validated method. Confirm scene timing against 1–8 Dec, account for revisit gaps and dense-urban SAR limitations, and retain method/confidence metadata.
3. **Narrow validation scope:** restrict validation to dates and places with defensible observations and state explicitly that the December 2015 peak is unvalidated. Do not substitute November vectors for the December event.

### 4. Land cover

- **Inputs:** collected ESA WorldCover 2021 v200 10 m raster; confirm that its year and class definitions fit each event analysis.
- **Tools:** rasterio/GDAL for reprojection, masking, and class tabulation; pandas/geopandas for summaries.
- **Planned outputs:** aligned categorical land-cover layer and documented class-to-analysis grouping/crosswalk; optional zonal class summaries.
- **CRS/grid:** preserve the source; reproject to EPSG:32644 and align categorically to the proposed analysis grid with nearest-neighbour resampling. Keep class codes categorical and retain nodata separately.
- **Validation checks:** source CRS, dimensions, transform, class codes and metadata; boundary/buffer coverage; nodata and edge seams; verify resampling did not create new class values; document the temporal mismatch between 2021 land cover and other event years.

### 5. OSM road graph and infrastructure

- **Inputs:** collected Geofabrik Southern Zone PBF (ODbL 1.0) and the provisional CMA boundary/buffer. Existing counts and known limitations are in `OSM_COUNTS.md`.
- **Tools:** pyosmium/osmium for PBF filtering and tag extraction; OSMnx/NetworkX or GeoPandas/Shapely for graph construction and spatial checks. Keep an untouched source snapshot and comply with ODbL attribution/share-alike obligations.
- **Planned outputs:** study-area road graph with stable source OSM identifiers, road class, direction/access/bridge/tunnel attributes where present, and separate linked infrastructure/hydrology layers. Derived extracts are planned outputs only and have not been created.
- **CRS/grid:** retain source WGS84 geometries; project analytical copies to EPSG:32644. A raster grid is not the road graph's native representation; if road features are rasterized for a model, document the 10 m alignment and preserve vector source features.
- **Validation checks:** graph connectivity and dangling-edge review; duplicate/invalid geometry checks; clip/buffer edge handling; tag completeness and counts against `OSM_COUNTS.md`; review exact named-waterway findings and connectivity limitations in `OSM_WATERWAYS.md` (ground completeness remains uncertain); confirm snapshot date and ODbL attribution. OSM absence is not proof a feature is absent on the ground.

### 6. WorldPop population exposure

- **Inputs:** intended WorldPop R2025A constrained India 2021 raster (CC BY 4.0), which is currently unavailable because its transfer stalled and the partial file was removed. Retry acquisition only when authorized and a stable connection is available.
- **Tools:** rasterio/GDAL for metadata, alignment, masking, and zonal/road-buffer summaries; pandas/geopandas for reporting.
- **Planned outputs:** aligned population exposure surface or summarized population exposure by road segment/area, with source year, constrained/unconstrained definition, and aggregation method recorded.
- **CRS/grid:** retain the native raster; project to EPSG:32644 for local metrics. Its approximately 100 m source cells are coarser than the proposed 10 m grid; do not upsample and imply new population detail. Prefer native-cell or defensible area-weighted summaries; if an aligned model raster is needed, document resampling and preserve the source support.
- **Validation checks:** confirm file integrity/hash, GeoTIFF readability, year/product type, CRS, nodata, units, raster bounds/coverage, nonnegative plausible values, and agreement of totals before/after reprojection/masking within stated tolerance. Check that analysis does not interpret population cells as precise road-segment counts.

### 7. Reservoir time series

- **Inputs:** desired daily or finer level/storage/inflow/outflow/gate records for Chembarambakkam, Poondi, Puzhal/Red Hills, Cholavaram, and relevant basin reservoirs for event and baseline windows. Only a CWC advisory PDF is currently held; historical time series are not collected. Manual access/request steps are in `MANUAL_TODO.md`.
- **Tools:** manually authorized source acquisition; pandas for timestamp/unit normalization and quality control; geopandas only if associating reservoirs to catchments or study-area features.
- **Planned outputs:** provenance-preserving reservoir time-series table with station/reservoir IDs, timestamps/timezone, units, missingness, release/gate metadata, and event-window aggregates. Keep unavailable periods explicit.
- **CRS/grid:** point locations retain WGS84 and may be projected to EPSG:32644 for spatial joins. Reservoir series are temporal point data and should not be forced onto the 10 m raster grid; spatial association to catchments must be separately justified.
- **Validation checks:** source/permission and licence; station identity; duplicate/missing timestamps; timezone and unit consistency; physically plausible levels/storage/flows; discontinuity and release-event review; compare summaries with source bulletins. Never infer missing release values from an advisory map without evidence.

## Phase 3 readiness gate

Before processing starts, confirm the final CMA boundary, choose the event windows, settle the December 2015 label strategy, decide whether the proposed 10 m grid is appropriate, and determine whether missing WorldPop/reservoir sources are blockers or documented scope limits. Keep all raw sources immutable and save processing outputs only in the appropriate processed/features locations after this plan is approved.
