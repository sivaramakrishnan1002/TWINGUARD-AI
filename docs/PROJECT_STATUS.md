# TwinGuard AI — project status

**Updated 14 October 2026.** TwinGuard AI is a flood Digital Twin project for Chennai. The current study boundary is the older CMA (about 1,187 km²), still provisional. Part B (Phase 3 feature preparation) is complete. No model was trained and no Phase 4 work was started.

## Done

- Project setup and PostgreSQL/PostGIS Compose files are present. Containers were not started.
- The raw-data folder has 58 data files and 18 download logs. A read-only size and SHA-256 audit matched all 58 files with zero mismatches. Raw files were not edited.
- There are 13 verified ASF Sentinel-1 ZIPs. All passed ZIP checks and metadata/name matching. This includes a 6 Dec 2015 scene within the flood window and two 16 Nov 2021 post-peak scenes. Sentinel files remain raw and unprocessed.
- Phase 3 created a shared 30 m EPSG:32644 grid, terrain and land-cover features, WorldPop aggregation, rainfall and reservoir tables, OSM road/facility/building/waterway layers, and exploratory flood-label inspection layers.
- Raster validation checked 18 outputs. All are aligned to the common grid and have valid values. Five old exploratory label rasters are tiled GeoTIFFs rather than COGs; they were preserved and are listed as warnings.
- WorldPop and OSM proximity summaries are model estimates and map-buffer summaries. They are not census headcounts, road accessibility, or evacuation demand.

## Manual decisions and limitations

- Confirm whether the older CMA or expanded CMA is the final study boundary.
- The collected UNOSAT vectors are dated 1 Sep, 14 Oct, 12 Nov, and 24 Nov 2015; they do not provide a vector label for the 1–8 Dec peak. The 6 Dec Sentinel scene is unprocessed. The 2021 and 2023 flood maps are PDFs and still need manual digitising.
- Inspect the DSM elevation artifacts and choose hydrologic conditioning before interpreting flow accumulation or TWI. Review OSM graph connectivity before routing.
- Check WorldPop totals against census data, verify weather units, and confirm historical reservoir capacities. Storage changes are not reservoir releases; the available CAG summary gives only limited Chembarambakkam release findings.
- Confirm Sentinel reuse terms and required attribution before redistribution. Do not treat the illustrative reservoir screen as a validated warning model.

## Next

Use `MANUAL_TODO.md` to resolve the study-boundary, label, data-quality, OSM-routing, and licence decisions. Review `PHASE3_LOG.md`, `PHASE3_VALIDATION.json`, and `DATA_QUALITY_REPORT.md` before deciding on any later modelling work.
