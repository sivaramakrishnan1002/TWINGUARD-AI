# Urban physical layer lineage

Generated from existing feature products only; no raw file was edited. Input hashes are SHA-256.

## Inputs

- `data/features/static/cell_table_phase9b_v2.parquet` — `c54c21d8145adde7600d817169b80ebe2d936ce7edae59e2248e40a8280dbf86`
- `data/features/osm/chennai_osm_features.gpkg` — `0005220d76f928892a4aeb5589fe8335179c82a4fe80d76df7ebe9d232cdcb33`
- `data/features/terrain/elevation_m.tif` — `938c2b9cd4c5cd59a0d559ed5d767db409a47b01cb55b9d29bb161848544f609`

## Output checks

- Grid: EPSG:32644, 30 m, 1,760 × 1,370 cells.
- Height statistics (m): min=0.000, p50=2.184, mean=3.541, p95=11.270, max=139.663.
- Output raster hashes and byte sizes are recorded in `data/features/terrain/urban_physical_v1/metrics.json` supplement below.

## Output files

- `data/features/terrain/urban_physical_v1/euclidean_distance_to_osm_drainage_m.tif` — 1,845,737 bytes; SHA-256 `900ad46cbabbddce8ea913475f6fd3161930457b2e1dd7cc6d5602a217c39146`
- `data/features/terrain/urban_physical_v1/height_above_nearest_osm_drainage_m.tif` — 3,624,253 bytes; SHA-256 `776cad4fe7a76bcf17360defc787755ca03842c9ab542510ff11b035d984180c`
- `data/features/terrain/urban_physical_v1/local_depression_depth_m.tif` — 1,726,352 bytes; SHA-256 `bd7eb6f3222b9da3850fad98b779565c6458da15c465fd7aaa01ee9075b7730a`
- `data/features/terrain/urban_physical_v1/physical_susceptibility_rank.tif` — 4,051,981 bytes; SHA-256 `d1026efb035b406f7d77cc045c7a7f5aceab820d00b91ca7d5e24eb3118aa61a`
- `data/features/terrain/urban_physical_v1/relative_elevation_15cells_m.tif` — 4,413,320 bytes; SHA-256 `db6225d46c184979a97cfd4abcacde35454e67587719270411e11f5dbb8303bf`
- `data/features/terrain/urban_physical_v1/relative_elevation_33cells_m.tif` — 4,334,896 bytes; SHA-256 `c05a0c51e32720f764e64a6e5c38b207fa455114d58251c39a709502133847ad`
- `data/features/terrain/urban_physical_v1/relative_elevation_5cells_m.tif` — 4,498,803 bytes; SHA-256 `a97e89137aff1b0e9b55573b5f5e1600ada67e96ed072cc1e801df6d47be8d61`
