# Phase 3 pipeline run order

Run from the project root using `.venv\\Scripts\\python.exe`.

1. `pipelines\\phase3\\phase3_core.py --task all` creates the EPSG:32644 30 m grid, terrain derivatives, WorldCover class/fraction rasters, and sum-resampled WorldPop surface.
2. `pipelines\\phase3\\weather_reservoirs.py` creates hourly rainfall predictors, source comparisons, reservoir tables, and an explicitly illustrative Track B screen.
3. `pipelines\\phase3\\flood_labels_inspection.py` rasterizes exploratory UNOSAT layers and baseline references, and summarizes GFD and OpenCity. These are not final training labels.
4. `pipelines\\phase3\\osm_extract_graph.py` extracts OSM roads, facilities, buildings, and waterways. It refuses to overwrite an existing GeoPackage.
5. `pipelines\\phase3\\split_osm_layers.py` splits the existing combined GeoPackage into roads, facilities, buildings, and hydrology files; it refuses existing destinations.
6. `pipelines\\phase3\\summarize_osm_gpkg.py` makes an inventory summary from the existing GeoPackage without rereading the PBF.
7. `pipelines\\phase3\\population_exposure.py` estimates WorldPop model counts in unique road 100 m buffers and facility 500 m buffers. Per-facility catchments overlap.
8. `pipelines\\phase3\\summarize_event_peak_rainfall.py` derives peak summaries from the existing hourly CSV without rewriting that CSV.
9. `pipelines\\phase3\\validate_outputs.py` checks raster grid alignment, valid data, and file layout. Run `tools\\audit_raw_logs.py` for a read-only raw size/hash audit.
10. `tools\\update_phase3_manifest.py` refreshes the derived-output rows in `docs/DATA_MANIFEST.csv`.

Raw inputs are read-only: no downloads, unzipping, edits, or Sentinel-1 processing. No software is installed, no model is trained, and PDF maps are not digitized. Weather/reservoir tables use CSV because no Parquet engine is installed. NetworkX and GDAL Python bindings/CLI are unavailable; the OSM extractor uses a custom graph routine, and rasterio's GDAL is used for raster operations. Check available disk space before any future output that may exceed 2 GB.
