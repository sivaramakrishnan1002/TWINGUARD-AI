# Phase 3 processing log — Part B final report

Run date: 14 October 2026 (Asia/Kolkata). User approved Part B. Raw data files were treated as read-only; no download, unzip, PDF digitising, Sentinel processing, package installation, or model training was performed. The Sentinel verifier updated its allowed metadata log and report after finding newly present ZIPs.

## Preflight and Sentinel update

- Confirmed the project venv is required for geospatial tools. No packages were installed. `pyarrow`/`fastparquet`, NetworkX, SNAP, pyroSAR, and GDAL Python bindings/CLI are unavailable.
- During the final check, `data/raw/satellite/senitnel1/2021` contained six ZIPs, including two 16 Nov 2021 archives not in the previous four-file inventory. The Sentinel verifier also found a 6 Dec 2015 ZIP. All 13 archives were verified read-only: CRC/integrity PASS (13/13), filename and SAFE start/stop match PASS (13/13), total archive bytes 16,047,502,740. Updated `DOWNLOAD_LOG.txt`, `docs/SENTINEL_VERIFICATION.md`, and added the three missing source rows to `docs/DATA_MANIFEST.csv`.
- The 6 Dec 2015 Sentinel scene covers 100% of the provisional CMA footprint and falls within 1–8 Dec, but is unprocessed raw imagery, not an observed flood mask. The two 16 Nov 2021 acquisitions cover 27.65% and 72.32% individually and about 99.98% as a union; these are after the provisional 7 Nov peak.
- A read-only raw audit then counted 58 data files (17,775,232,566 bytes) and 18 metadata logs; all 58 data files matched logged size and SHA-256, with zero mismatches or missing comparable hashes.

## Common grid and raster features

- Master grid: provisional older CMA boundary, EPSG:32644, 30 m, 1,370 x 1,760, 2 km rectangular context buffer, bounds 390000–431100 m E and 1418820–1471620 m N. Centre-in-polygon CMA mask: 1,319,380 cells.
- Terrain products: elevation, slope, aspect, Laplacian curvature proxy, D8 direction, D8 accumulation, and TWI proxy. 2,411,200 valid context cells; CMA elevation -64.51 to 168.70 m, max slope 53.19°, and 121,883 CMA D8 sink/no-lower-neighbour cells. Copernicus GLO-30 is a DSM; coastal negative values and unconditioned urban/coastal hydrology need review. No height-above-drainage surface was created.
- ESA WorldCover outputs include 30 m categorical mode and 11 area-fraction bands. All 1,319,380 CMA cells have all 11 fractions; per-cell sums range 0.99999988–1.00000012, median 1.0. Observed classes: 10, 20, 30, 40, 50, 60, 80, 90.
- WorldPop sum-resampled 30 m surface: CMA model estimate 6,203,811; 1,123,409 positive cells, 1,010 valid zero cells, and 194,961 nodata cells. Alpha constrained product; use for relative patterns, not absolute headcount.

## Weather and reservoir features

- ERA5 hourly output: 18,576 rows across nine requested points and three event windows, with no within-event hourly cadence gaps. Rolling sums for 1/3/6/12/24/48/72/168 h plus other weather predictors are in CSV. Daily comparison has 3,287 matched dates; ERA5–NASA POWER Pearson r=0.7635, mean bias=-0.6768 mm/day, RMSE=6.5972 mm/day. These are coarse model products, not gauges; verify NASA POWER units before publication. Event peak summary is in `data/features/weather/event_peak_rainfall.json`.
- Kaggle daily reservoir features: 24,728 reservoir-day records, four reservoirs, 2004-01-01 through 2020-12-03. Six OpenCity series provide 1,164 monthly values. Monthly data are too coarse for event-day operation analysis. No storage change was treated as release.
- Illustrative Track B screen: storage >=80% of current published total capacity, rising versus three days earlier, and three-day mean ERA5 rain >= 2015 pre-Dec-1 P90 (23.4689 mm). Across 2,162 overlapping dates it flags 11 dates; five occur 20–24 Nov 2015, earliest 11-day lead; six fall outside that target window. It is not a validated warning model: current capacity history and complete daily flood outcomes are unavailable.

## Flood references and OSM/exposure

- UNOSAT exploratory 30 m raster areas: Sep 1 reference 46.42 km²; Oct 14 reference 51.74 km²; Nov 12 event 84.78 km²; Nov 24 event 98.16 km². November union 126.39 km²; subtracting the union of both reference masks gives 80.59 km². This subtraction is not validated because reference classes include potentially saturated/wet soil. December 1–8 remains without a collected vector label.
- Global Flood Database event 4309: 1,082 flooded-band pixel centres inside CMA (~65.43 km² using nominal local cell area), on a coarse ~250 m MODIS event layer spanning 10 Nov–4 Dec; event centroid is outside Chennai. Treat as broad regional overlap, not confirmed Chennai flood truth.
- OpenCity inventory includes nine KMLs. Incident points are distinct from return-period/hazard polygons; these modeled scenarios are not observed flood extent. Invalid geometry is handled per feature rather than unioned.
- Existing combined OSM GeoPackage was preserved and split into roads, facilities, buildings, and hydrology GeoPackages. Counts: 566,307 road segments, 1,071,656 directed arcs, 508,854 nodes, 15,413 facility points, 382,294 building outlines, and 759 waterways; total road-segment length about 18,849.6 km. Connectivity and routability were not recomputed in the inventory-only summary; this remains a routing prerequisite.
- WorldPop proximity summaries use unique CMA cells: 1,047,685 cells within 100 m of mapped roads (1,002,824 valid population cells; sum 6,072,870.5) and 724,797 within the union of 500 m facility circles (694,800 valid cells; sum 5,126,819.5). These are alpha model-count sums for proximity only. The 15,413 individual facility catchments overlap and must not be summed as unique population.

## Validation, storage, and outstanding work

- `docs/PHASE3_VALIDATION.json`: 18 rasters checked; all align to the master grid, are nonempty, and have valid band-1 data. Five existing label-inspection TIFFs are tiled GeoTIFFs but not COGs; this is a warning. No existing raster was rewritten to resolve it.
- Current raw tree: 58 data files and 18 logs; byte/hash audit 58/58 matched, zero mismatches. No raw data files were modified. Sentinel metadata changes were limited to the explicitly requested verification log; the verifier did not edit the ZIPs.
- Product size and free-space totals are in `docs/STORAGE_ESTIMATE.md`; exact per-file bytes and hashes for derived outputs and new Sentinel sources are in `docs/DATA_MANIFEST.csv`.
- Remaining manual tasks are in `docs/MANUAL_TODO.md`: boundary decision, hydrology review, flood label/digitising strategy, census comparison, source units/capacities, OSM connectivity and licensing.
- Part B is complete. No model training, PDF digitising, or Phase 4 activity was started.
