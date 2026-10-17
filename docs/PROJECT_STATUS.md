# TwinGuard AI — project status

**Updated 17 October 2026.** TwinGuard AI is a flood Digital Twin project for Chennai. The current study boundary is the older CMA (about 1,187 km²), still provisional. Phase 3 feature preparation is complete. Phase 4 Part 1 preprocessing has started and its terrain, routing, SAR-plan and IMERG tasks are documented in `PHASE4_LOG.md`. No database work or model training was done.

## Done

- Project setup and PostgreSQL/PostGIS Compose files are present. Containers were not started.
- The raw-data folder has 58 data files and 18 download logs. A read-only size and SHA-256 audit matched all 58 files with zero mismatches. Raw files were not edited.
- There are 13 verified ASF Sentinel-1 ZIPs. All passed ZIP checks and metadata/name matching. This includes a 6 Dec 2015 scene within the flood window and two 16 Nov 2021 post-peak scenes. Sentinel files remain raw and unprocessed.
- Phase 3 created a shared 30 m EPSG:32644 grid, terrain and land-cover features, WorldPop aggregation, rainfall and reservoir tables, OSM road/facility/building/waterway layers, and exploratory flood-label inspection layers.
- Raster validation checked 18 outputs. All are aligned to the common grid and have valid values. Five old exploratory label rasters are tiled GeoTIFFs rather than COGs; they were preserved and are listed as warnings.
- WorldPop and OSM proximity summaries are model estimates and map-buffer summaries. They are not census headcounts, road accessibility, or evacuation demand.
- The fix-up reports are in `ERA5_2015_CHECK.md`, `TERRAIN_CHECK.md`, `ROAD_GRAPH_CHECK.md`, `LABEL_STRATEGY.md`, and `PHASE3_FIXUPS.md`. The −64.51 m terrain minimum appears to be a source DEM artefact; review it before trusting local terrain derivatives. The largest road SCC contains 99.25% of graph nodes, but routes still need safety/access validation.
- The 2015 ERA5 request contains Dec 1–2 rainfall (nine-point daily means 49.82 and 57.10 mm). Its 16 Nov peak is a full-request-window maximum, not a parsing error. Four-day ERA5/NASA POWER agreement is only a small-sample check (r=0.383, n=4).
- Phase 4 Part 1 generated separate conditioned terrain rasters and a vehicle routing profile without changing the Phase 3 terrain layers. Masked 255 CMA cells below −5 m; the CMA water-mask footprint is estimated at 129.12 km². Added edge-safe slope/TWI and valid-only fill-depth copies under new names after identifying mask-edge derivative risk.
- The routing profile has 455,285 included edges; 200 seeded sample origins yielded 159 reachable hospital routes, with median 3.16 minutes and 79.5% reaching a hospital within 30 minutes under assumed speeds. This is not an evacuation safety result.
- The locally present 86 GPM IMERG daily NetCDF files cover all three expected date windows (45/20/21, no missing days). Their per-file hashes and filesystem dates are in the raw-folder log; licence remains to confirm. See `RAIN_SOURCES_COMPARISON.md` for UTC-aligned comparisons.

## Manual decisions and limitations

- Confirm whether the older CMA or expanded CMA is the final study boundary.
- The collected UNOSAT vectors are dated 1 Sep, 14 Oct, 12 Nov, and 24 Nov 2015; they do not provide a vector label for the 1–8 Dec peak. The 6 Dec Sentinel scene is unprocessed. The 2021 and 2023 flood maps are PDFs and still need manual digitising.
- Manually review the −64.51 m DEM artifact and decide how to handle it before interpreting local hydrologic derivatives. Graph connectivity is now quantified, but routing still needs flood depth, access, closure and safety constraints.
- Check WorldPop totals against census data, verify weather units, and confirm historical reservoir capacities. Storage changes are not reservoir releases; the available CAG summary gives only limited Chembarambakkam release findings.
- Confirm Sentinel reuse terms and required attribution before redistribution. Do not treat the illustrative reservoir screen as a validated warning model.
- Confirm the 2 m channel burn depth, default road speeds, and 0.3 m flood-passability threshold before using the new terrain/routing products for decisions. Check the 2021/2023 rainfall discrepancies and IMERG licence with source documentation.

## Next

Use `MANUAL_TODO.md` to resolve the study-boundary, label, data-quality, OSM-routing, threshold and licence decisions. Review `PHASE3_LOG.md`, `PHASE4_LOG.md`, `PHASE3_VALIDATION.json`, and `DATA_QUALITY_REPORT.md` before any later phase. Phase 4 Part 1 is not a flood-routing validation; SAR label processing and subsequent phases remain separate work.
