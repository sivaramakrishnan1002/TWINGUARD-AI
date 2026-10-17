# Phase 4 spatial alignment and registration

The project master grid is EPSG:32644, 30 m, 1,370 columns by 1,760 rows, with origin (390000, 1471620) m and pixel-centre CMA masking. Its CMA mask contains 1,319,380 cells. The authoritative inventory for this check is `data/processed/alignment/layer_registry_complete.json`.

The inventory contains 34 raster records and 36 vector layers. The 28 derived analysis rasters match the master grid's CRS, shape, cell size and whole-cell origin registration; there are zero unexplained analysis-grid misalignments and zero metadata errors. Six native raw raster inputs have different native grids and are correctly marked not applicable to the derived-grid alignment test. Raster nodata is read from GDAL masks and unmasked non-finite values are checked separately. The registry records extents, dtype, nodata, grid test and per-band valid/nodata counts.

WorldPop sum check: native 100 m sum 6,204,903.704; resampled 30 m sum 6,203,811.274; relative difference 0.0001761 (0.01761%). This passes the documented 0.1% preservation tolerance. The totals are model estimates and the 30 m resampling changes cell distribution while preserving the aggregate within tolerance.

The observed UNOSAT vector/raster area differences arise from rasterization on the 30 m pixel-centre grid: 12 Nov vector 84.9246 km² versus raster 84.7755 km²; 24 Nov vector 98.3137 km² versus raster 98.1603 km². These are recorded comparisons, not evidence that the raster exactly reproduces the source geometry.

The requested filename `layer_registry.json` already existed from an initial inventory pass. The no-overwrite rule required preserving it. That first-pass file has incorrect classifications and is **preliminary, do not use**; the corrected, complete inventory is the new `layer_registry_complete.json`. The corrected script also handles zipped shapefile layers. This naming deviation and the initial error are recorded in `ISSUES.md`.

Script: `pipelines/phase4/spatial_alignment.py`. No source data was modified.
