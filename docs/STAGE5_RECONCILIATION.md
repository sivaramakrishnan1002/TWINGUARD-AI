# Stage 5 gap reconciliation and verification

Run date: 2026-10-23 (Asia/Kolkata). All raw inputs were opened read-only. No network downloads or package installs occurred. Database credentials were read through `pipelines/stage5/db_common.py`; no credentials or connection strings were logged.

## C1 — source-to-database reconciliation

| Database table / source | Source features or records | Loaded | Explanation |
|---|---:|---:|---|
| `study_area` / `chennai_cma_boundary.geojson` | 1 | 1 | Same single boundary feature. Its vintage/retrieval date are unverified; it was not changed. |
| `road_edges` / `vehicle_edges.gpkg:vehicle_edges` | 455,285 | 455,285 | Exact source-layer match. The 1,071,656 graph arcs in `chennai_road_graph.gpkg` represent a different, broader directed graph from 566,307 road segments. Database edges use the narrower vehicle-routing profile: 15 highway classes, excluding cycleway, footway, path, pedestrian, steps and track; `access=no/private` are also filtered (84,784 source segments in the routing notes). Therefore the arc count is not the expected row count for the vehicle-edge table. |
| `facilities` / `chennai_facilities.gpkg:facilities` | 15,413 | 15,413 | Exact layer match. The selected categories are hospital 848, clinic 587, school 696, college 188, shelter 171, fire station 15 and police 121. The saved graph facility counts match these exactly. `OSM_COUNTS.md` uses a rectangular bounds inventory, while the extracted layer uses CMA plus 2 km and tag grouping/deduplication. Its counts are hospitals 908, clinics 607, schools 706, shelters 172, fire stations 15 and police 123. Differences are 60, 20, 10, 1, 0 and 2 respectively; the exact feature-by-feature differences remain unresolved without a same-snapshot, same-scope recount. |
| `waterways` / `chennai_waterways.gpkg:waterways` | 759 | 759 | Exact source-layer match. The comparison inventory reports 816 waterway-tagged ways in a rectangle. The saved extractor uses CMA plus 2 km, a selected set of seven `waterway` classes and keeps line results; the inventory counts all waterway-tagged ways intersecting its bounds. The 57-feature difference is a scope/filter difference, not evidence that 57 database rows were lost. An OSM-id crosswalk was not available to assign each difference to one filter. |
| `flood_references` / UNOSAT archive, four CMA-intersecting layers | 1,360 + 645 + 4,704 + 3,710 = 10,419 | 10,419 | Source-wide feature totals are larger: 12 Nov has 142,609 and 24 Nov has 88,684 features. The database stores only features intersecting the project boundary after the source bbox read: 4,704 and 3,710. It also includes the 1 Sep and 14 Oct baseline layers (1,360 and 645), giving 10,419 total. This is intentional spatial filtering, not a 2,190-feature shortfall. |
| `road_nodes` / `chennai_road_graph.gpkg:road_nodes` | 508,854 | 508,854 | Exact source-layer match; component ids are NULL because they were not present in the source node layer. |
| `grid_cells` / `cell_table.parquet` | 1,319,380 | 1,319,380 | Exact row match. Imported with batched PostgreSQL `COPY`; 30 m source cell values and NoData flags are retained. |
| `building_footprints` / `chennai_building_footprints.gpkg:building_footprints` | 382,294 | 382,294 | Exact source-layer match. The broader `OSM_COUNTS.md` bounding-box inventory is 385,373 buildings; it uses a different spatial scope. |
| Observation records | ERA5 18,576 rows × 5 variables; NASA POWER 9 × 3,287 dates × 5 variables; IMERG 86 documented daily CMA means; reservoir daily 24,728; reservoir monthly 1,164 | 92,880 + 147,915 + 86 + 24,728 + 1,164 = 266,773 | The loaders preserve the source cadence; ERA5 stays hourly and no hourly values were synthesized. NASA POWER units are taken from its JSON metadata. IMERG values are from the already documented `RAIN_SOURCES_COMPARISON.md` table and were not recalculated during the load. The 12 missing OpenCity monthly storage values are retained with `MISSING` QC flags. |
| `flood_labels` | UNOSAT 10,419; OpenCity points 945; OpenCity modelled zones 10,555; GFD metadata 1; derived exploratory rasters 7 | 21,927 | Observations, modelled return-period/hazard layers, coarse cross-check, and unvalidated derived labels have distinct types and confidence tiers. GFD is metadata-only, not a city-scale perimeter. OpenCity observed points have no exact observation day in the local source, so `event_date` is NULL. |
| `sentinel_scenes` | 13 verified ZIP archives | 13 | One record per scene, with read-only SAFE manifest metadata and footprint. All 13 footprints intersect the CMA; scene pixels were not loaded or processed. Absolute orbit is retained in metadata; relative orbit is left NULL rather than inferred. |
| `data_manifest` | 117 CSV rows | 117 | Snapshot of `docs/DATA_MANIFEST.csv` at load time. |

The Stage 5 extension also produced 59 catalogue rows. Loaded records have source id, source-file SHA-256, loader name and load timestamp. The exception is the existing `dataset_catalog` itself, whose row is the provenance record. Catalog-count reconciliation found zero mismatches and provenance orphan checks found zero.

## C2 — invalid flood geometry repair

The 235 invalid original geometries in `flood_references` were grouped as follows:

| UNOSAT layer | `ST_IsValidReason` | Count |
|---|---|---:|
| `LS8_20151014_PreFlood` | Ring Self-intersection | 50 |
| `S1_20150901_PreFlood` | Ring Self-intersection | 31 |
| `S1_20151112_Flood` | Ring Self-intersection | 34 |
| `S1_20151124_Flood` | Ring Self-intersection | 119 |
| `S1_20151124_Flood` | Interior is disconnected | 1 |
| **Total** |  | **235** |

Migration 004 preserved each original `geom`, added `geom_repaired` and `is_valid`, ran `ST_MakeValid`, extracted polygon parts and stored MultiPolygons. All 10,419 repaired rows are non-empty/valid; 235 originals remain invalid by design. Migration 008 applied the same preserve-and-repair approach to the 54 invalid OpenCity KML polygon labels; all label `geom_repaired` geometries are valid. Both flood views expose repaired geometry, and the flood-reference MVT function queries `geom_repaired`.

Per-layer feature-area sums (all source feature extents, not dissolved CMA areas):

| Source layer | Original sum (km²) | Repaired sum (km²) | Delta (km²) |
|---|---:|---:|---:|
| `LS8_20151014_PreFlood` | 7,262.6673 | 7,262.6673 | 0.0000 |
| `S1_20150901_PreFlood` | 3,606.6888 | 3,606.6888 | 0.0000 |
| `S1_20151112_Flood` | 17,648.2566 | 17,648.2566 | 0.0000 |
| `S1_20151124_Flood` | 14,194.6650 | 14,194.6650 | 0.0000 |

The 4-decimal area sums were unchanged by repair. They include overlapping features and portions outside the CMA, so they are not inundated area totals. After dissolving each repaired event layer and intersecting it with the CMA in EPSG:32644, the 12 Nov result is **84.9246 km²**, versus the earlier 84.78 km² reference (difference **0.171%**); the 24 Nov result is **98.3137 km²**, versus 98.16 km² (difference **0.157%**). Neither comparison differs by more than 1%.

## C4 — database checks

All spatial tables use their expected SRID: project GIS layers and observations are EPSG:32644; Sentinel footprints are EPSG:4326. The original UNOSAT `geom` column has 235 invalid rows, while its repaired column has zero. Original OpenCity label geometry has 54 invalid polygons; the new repaired column has zero invalid geometries. All other checked geometry columns have zero invalid geometries.

Containment uses `ST_CoveredBy` against the selected CMA polygon. Outside/not-fully-covered counts are road edges 41,088; road nodes 44,928; facilities 251; buildings 6,571; waterways 93; grid cells 0. These source geometries were retained rather than clipped or moved; most are source features crossing the boundary. Sentinel footprints intersect the CMA: 13 of 13.

Representative `EXPLAIN (ANALYZE, BUFFERS)` checks used the spatial indexes and returned sample results:

| Query | Indexed relation | Rows returned | Execution time |
|---|---|---:|---:|
| Nearest hospital by KNN | `facilities_geom_gix` | 1 | 0.727 ms |
| Road lines intersecting one repaired Nov 24 flood feature | `road_edges_geom_gix` | 50 | 8.370 ms |
| Building footprints intersecting that feature | `building_footprints_geom_gix` | 50 | 3.662 ms |
| Grid cells intersecting that feature | `grid_cells_geom_gix` | 50 | 1.879 ms |

Five vector tile functions returned nonempty tiles at z=12 near Chennai: study area 666 bytes, roads 824,817 bytes, facilities 93,196 bytes, waterways 1,433 bytes, flood references 22,928 bytes. Timings ranged from 0.006 to 1.948 seconds in this run. These are smoke checks, not a map-service load test.

## C5 — boundary catalogue record

The catalogue records source path `data/raw/boundary/chennai_cma_boundary.geojson`, SHA-256 `89e81f8309a40ea9f24cf5e35c832b75ed937b65b111389d8ed8df4931804ad7`, and source URL `https://github.com/datameet/Municipal_Spatial_Data`. Retrieval date is explicitly NULL/unknown because no local record provides it. The project uses the older CMA boundary; its exact source vintage, authoritative status, and source-specific terms remain unverified. The boundary file and geometry were not changed.

## C6 — tooling and raw audit

The new read-only verifier is `pipelines/stage5/verify_stage5_complementary.py`; loader is `pipelines/stage5/load_stage5_complementary.py`. Both were run against the local `twinguard` database. The loader is hash/catalog gated and idempotent; running it again returned the same counts without duplicate inserts. Migrations 001–008 are checksum tracked. Tests, lineage refresh and raw audit results are recorded in `STAGE_5_6_REPORT.md`.
