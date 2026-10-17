# Phase 4 Part 1 log — preprocessing

Run date: 17 October 2026 (Asia/Kolkata). No network, login, download, database operation, or model training was performed. Raw IMERG granules were read-only; the expressly requested metadata/hash sidecar was created in their folder. Existing Phase 3 terrain rasters were not overwritten. New processing outputs are isolated under `data/processed/terrain_cleaned/` and `data/processed/routing/`.

## T1 — terrain conditioning

- Applied the existing 30 m EPSG:32644 master grid. Masked 255 CMA cells below −5 m (0.2295 km²) and the mapped water footprint. In the CMA, 143,465 cells (129.1185 km²) are water-masked, inferred from new raster validity after subtracting the 255 low-elevation cells; see caveats in `TERRAIN_CONDITIONING.md`.
- Priority-Flood filled 339,532 cells; maximum fill 12.901 m and mean positive fill 0.515 m. The exact-match Adyar, Cooum, Kosasthalaiyar and Buckingham Canal lines were burned 2 m below the filled surface, an assumption to confirm.
- Created cleaned elevation, fill depth, slope, D8 flow direction, accumulation and TWI proxy layers. Added three edge-safe/valid-only derivative rasters under new names; original new outputs and all Phase 3 outputs were left intact.
- Difference statistics against old slope, flow-direction, accumulation and TWI layers are in `TERRAIN_CONDITIONING.md`. GLO-30 is a DSM including buildings/trees; no vertical datum conversion was applied.

## T2 — routing profile

- Created a filtered directed vehicle graph with 455,285 edges and 859,312 directed arcs. 445,338 edges use an assumed default speed because maxspeed is missing or unparsable; class speeds are listed in `ROUTING_PROFILE.md`.
- Added per-edge travel time, length, bridge/tunnel flags and cleaned-DEM min/mean/max elevations. Snapped 848 hospitals, 174 OSM shelters and 909 separate candidate shelters (schools/colleges, assumption); all counted features are within 500 m of their nearest road node, with distance summaries in the report.
- Deterministic 200-origin sample: 159 origins had a directed route to a hospital and 159 to a shelter. Hospital median/p90 travel time: 3.16/7.15 min; 79.5% of all origins reached a hospital within 30 min. Shelter median/p90: 6.36/11.28 min. Of the 41 unreachable origins, 40 had no destination in their weak component and 1 shared a weak component with a destination but had no directed path. Origin IDs and categories are in `data/processed/routing/routing_unreachable_audit.json`.
- A depth-passability function is defined but was not applied to flood data. Its 0.3 m blocked-edge threshold is an assumption to confirm from literature.

## T3 — Sentinel-1 label plan

`SAR_LABEL_PIPELINE.md` compares local SNAP processing with ASF On Demand/HyP3 terrain-corrected products, marks ASF credit limits as requiring user verification, defines the 2015 pilot and 2021 validation references, records required decisions/risks, and gives only grid-based storage estimates. No Sentinel ZIP was extracted or processed. Tool availability was checked locally; no packages were installed.

## T4 — IMERG

- Found 86 daily files totaling 2,563,070,392 bytes: 45/45 for 1 Nov–15 Dec 2015, 20/20 for 1–20 Nov 2021 and 21/21 for 25 Nov–15 Dec 2023. No dates are missing in those windows.
- Inspected the local NetCDF metadata and coordinate axes and read only the small longitude/latitude window covering the CMA. Precipitation units are mm/day and the daily periods are UTC. ERA5 hourly rainfall was summed by UTC day and point, then averaged over the nine points; NASA POWER rows are compared on the same UTC date labels. The CMA IMERG mean uses contained 0.1° pixel centres, an approximate coarse-grid boundary method.
- Product DOI is 10.5067/GPM/IMERGDF/DAY/07; product-specific licence is **TO CONFIRM**. Per-file size, filesystem modification time and SHA-256 are in the raw-directory `DOWNLOAD_LOG.txt`. Event peaks, window means, matched-day correlations/biases, and 1–2 Dec 2015 values are in `RAIN_SOURCES_COMPARISON.md`. No source is gauge truth.

## Output and validation notes

The six original conditioned terrain rasters, three added safety rasters, routing GeoPackage/metrics JSON, and the unreachable-origin audit are new files. Rasterio opened the terrain layers on the common 1,370 × 1,760 grid; the routing GeoPackage contains 455,285 edge records. No existing data/features file was changed. Any future use of route times, raster derivatives, flood passability, or gridded rainfall requires the assumptions and source limitations in the linked reports to be reviewed first.
