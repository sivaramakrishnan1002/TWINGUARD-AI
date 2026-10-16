# Engineering work in Phases 2 and 3

## What has been built

Phase 2 collected and inventoried the sources currently in the raw folders, added acquisition logs, checked checksums, and closed out known gaps. Phase 3 Part B then built exploratory aligned features, summaries and validation records. Raw data remained unchanged according to the latest Phase 3 audit. [repo: `docs/PHASE2_CLOSURE.md`, `docs/PHASE3_LOG.md`]

The repo contains a one-service Compose definition for PostgreSQL/PostGIS and an example environment file. The database containers were not started. No application backend, frontend, AI service or trained model is recorded. [repo: `docker-compose.yml`, `.env.example`, `docs/PROJECT_STATUS.md`]

## Common spatial grid

The working grid is EPSG:32644 (WGS 84 / UTM zone 44N), **30 m** cells, **1,370 columns × 1,760 rows**, with **1,319,380 CMA pixel centres** on the old-boundary mask. The raster rectangle extends **2 km** beyond the provisional CMA. The grid is a shared analysis frame; it does not make 100 m population, roughly 250 m flood imagery or coarse weather finer. [repo: `docs/GRID_DECISION.md`]

## Outputs and measured checks

| Workstream | Existing result |
|---|---|
| Weather | Hourly ERA5 event sequences and daily comparison tables. Peaks and source agreement are reported in [Research Foundation?] No: see `data/features/weather/event_peak_rainfall.json` and `daily_source_comparison.json`; see chapter 05/17. Correlation **0.7635**, bias **−0.6768 mm/day** across **3,287** dates. [repo: JSON files] |
| Terrain | Elevation, slope, aspect, curvature proxy, D8 direction/accumulation and TWI proxy. CMA elevation **−64.51 to 168.70 m**, maximum slope **53.19°**, and **121,883** D8 sinks/no-lower-neighbour cells. Unconditioned DSM-derived drainage needs review. Mean elevation and <5 m count were not computed. [repo: `docs/PHASE3_LOG.md`] |
| Land cover | ESA WorldCover 2021 class raster and 11 fraction bands. Built-up class (50) mean fraction **0.39427784** (about **39.43%**). Fraction sums for every CMA cell range **0.99999988–1.00000012**, median 1.0. This is not measured imperviousness; building-density correlation is not computed. [repo: `class_area_fraction_means_cma.json`, `docs/PHASE3_LOG.md`] |
| OSM | **566,307** road segments, **1,071,656** directed arcs, **508,854** nodes, **15,413** facilities, **382,294** building outlines, **759** waterway features; segment-length sum **18,849,562 m**. Connectivity statistics were not recomputed in summary. [repo: `osm_graph_summary.json`] |
| Named waterways | Exact-name results in `docs/OSM_WATERWAYS.md`; four key river/canal labels have a combined clipped length of about **189.146 km**. Named subset has **6 components** and **12** degree-one endpoints, but unnamed connectors were excluded. [repo: `docs/OSM_WATERWAYS.md`] |
| Population | Derived 30 m sum-resampled WorldPop surface: CMA estimate **6,203,811**, **1,123,409** positive cells, **1,010** valid zero cells, **194,961** NoData cells. NoData is not zero. [repo: `docs/PHASE3_LOG.md`] |
| Population proximity | **1,047,685** CMA cells within 100 m of mapped roads; population-model sum **6,072,870.5**. **724,797** cells in union of facility 500 m circles; sum **5,126,819.5**. These are geometric buffers, not travel/accessibility service areas. [repo: `population_exposure_summary.json`] |
| Reservoirs | **24,728** daily Kaggle rows across four reservoirs through **3 Dec 2020**; OpenCity has **1,164** monthly values. Track B screen flags **11** dates, including five before 1 Dec 2015; not a validated alert. [repo: `docs/PHASE3_LOG.md`, backtest JSON] |
| Flood inspection | Four UNOSAT layer dates; baseline subtraction test; GFD 4309 intersection; OpenCity KML inventory. These are exploratory references, not model-ready validation labels. [repo: `label_inspection_summary.json`] |

## Scripts and their jobs

The following script roles come from source docstrings and CLI descriptions. Run commands and options can change; inspect the script before running it. Do not run these during documentation review. [repo: `pipelines/phase3/*.py`, `tools/*.py`]

| Script | Recorded job |
|---|---|
| `pipelines/phase3/phase3_core.py` | Build common grid and terrain, land-cover and population features; task choices include grid, terrain, landcover, population and all. |
| `pipelines/phase3/weather_reservoirs.py` | Prepare weather and reservoir tables from raw inputs. |
| `pipelines/phase3/summarize_event_peak_rainfall.py` | Summarize peak rolling rainfall from the existing hourly CSV. |
| `pipelines/phase3/osm_extract_graph.py` | Extract local roads, amenities, buildings and waterways from the OSM PBF. |
| `pipelines/phase3/split_osm_layers.py` | Organize existing OSM GeoPackage layers into feature folders. |
| `pipelines/phase3/summarize_osm_gpkg.py` | Summarize inventory counts from an existing OSM GeoPackage. |
| `pipelines/phase3/population_exposure.py` | Summarize modelled population near roads and facilities. |
| `pipelines/phase3/flood_labels_inspection.py` | Exploratory label checks; explicitly not final training labels. |
| `pipelines/phase3/validate_outputs.py` | Read-only raster/grid validation. |
| `tools/audit_raw_logs.py` | Read-only raw file size/hash log audit. |
| `tools/verify_asf_sentinel.py` | Read-only ASF ZIP integrity, metadata and footprint verification. |
| `tools/verify_sentinel.py` | Verify manually downloaded Sentinel ZIPs against a shortlist; defaults are listed in its source. |
| `tools/osm_waterways_inventory.py` | Read-only exact-name waterway inventory. |
| `tools/add_verified_sentinel_manifest_rows.py` | Add newly verified Sentinel records to the manifest. |
| `tools/update_phase3_manifest.py` | Refresh derived-output rows in the manifest. |

## Validation and warnings

### Rainfall peaks from the stored event summary

The summary selects the maximum rolling accumulation over the existing ERA5 event-hourly table and nine points. Dates are local time (IST). These are reanalysis estimates, not gauge totals. [repo: `data/features/weather/event_peak_rainfall.json`]

| Year | 1-hour maximum | 3-hour maximum | 24-hour maximum |
|---|---|---|---|
| 2015 | 25.9 mm, 16 Nov 2015 14:00 | 69.6 mm, 16 Nov 2015 14:00 | 158.9 mm, 16 Nov 2015 16:00 |
| 2021 | 12.5 mm, 10 Nov 2021 23:00 | 31.6 mm, 11 Nov 2021 03:00 | 155.5 mm, 11 Nov 2021 12:00 |
| 2023 | 18.2 mm, 4 Dec 2023 22:00 | 49.7 mm, 4 Dec 2023 23:00 | 259.6 mm, 5 Dec 2023 01:00 |

The rainfall sequences are hourly for 2015-11-01–2015-12-15, 2021-11-01–2021-11-20 and 2023-11-25–2023-12-15, with no within-event hourly cadence gaps recorded. The daily comparison is a nine-point spatial-mean comparison, not station validation. [repo: raw weather logs, `docs/PHASE3_LOG.md`, `data/features/weather/daily_source_comparison.json`]

`docs/PHASE3_VALIDATION.json` records **18** raster checks. All pass grid alignment and nonempty valid-band checks; there are no errors. Five label-inspection TIFFs are tiled GeoTIFFs but not COGs; they were retained, and this is a layout warning, not a claim of bad cell content. The raw audit recorded **58** data files and **18** logs with size/hash matches. [repo: `docs/PHASE3_VALIDATION.json`, `docs/PHASE3_LOG.md`]

The build log documents handled script failures (syntax, invalid KML geometry, missing imports, environment mismatch, and first-pass interruption). This history matters for reproducibility: preserve existing outputs and use the project environment, but do not blindly rerun scripts that write files. [repo: `docs/PHASE3_LOG.md`]
