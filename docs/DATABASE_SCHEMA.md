# Stage 5 database schema and current load

Updated 2026-10-24 (Asia/Kolkata). The local `twinguard` database uses schema `twinguard`, PostgreSQL 18.6 and PostGIS 3.6.2. Scripts read `.env` with the project's custom parser; credentials and connection strings are never logged. `.env` is unchanged. No container, network, or package installation was used for this update.

## Migrations

The original Stage 5 closure covered migrations 001–008. Migration 009 records the corrected boundary catalogue provenance; migration 010 creates the Digital Twin foundation schema; migration 011 adds CMA-intersection flags without deleting rows. The checksum ledger now has 11 entries total (nine `00*` migrations plus `010` and `011`). `pipelines/stage5/apply_migrations.py` is safe to rerun and refuses a changed checksum for an applied migration.

| Migration | Purpose |
|---|---|
| `001_core_schema.sql` | Original GIS schema, catalogue, views and indexes. |
| `002_gis_views_and_mvt.sql` | GIS query views and five MVT functions. |
| `003_catalog_licence_notes.sql` | Licence/caveat notes in the source catalogue. |
| `004_provenance_repaired_floods_and_boundary.sql` | Boundary catalogue provenance fields, row-level provenance on original GIS tables, repaired UNOSAT geometry, valid flag and repaired flood view/MVT. |
| `005_stage5_complementary_tables.sql` | Road nodes, cells, buildings, observations, labels, Sentinel scenes and loaded manifest. |
| `006_rebuild_incomplete_imerg_daily_load.sql` | Removes the incomplete first IMERG load made by the initial loader attempt so the corrected full series can load. |
| `007_clear_unverified_opencity_event_day.sql` | Clears an exact day assigned to OpenCity observed points; only the year is sourced, so day remains unknown. |
| `008_preserve_and_repair_label_geometries.sql` | Keeps original flood label geometries and adds valid repaired geometry for spatial views. |
| `009_record_cma_source_details.sql` | Records the Datameet community boundary source file, approximate retrieval date, area and authority caveat without changing geometry. |
| `010_create_twin_schema.sql` | Adds replay windows, versions, runs, scenarios, grid-artifact references, edge/facility/reservoir states and alerts in the separate `twin` schema. |
| `011_add_in_cma_flags.sql` | Adds `in_cma` to roads, nodes, facilities, waterways and buildings using `ST_Intersects` in EPSG:32644; adds it to analysis views and map tile attributes without removing rows. |

## Tables and counts

| Table | Current rows | Main contents |
|---|---:|---|
| `study_area` | 1 | Selected older CMA boundary. |
| `road_edges` | 455,285 | Filtered vehicle-routing edges from the vehicle profile. |
| `facilities` | 15,413 | OSM facility/amenity points. |
| `waterways` | 759 | OSM waterway lines. |
| `flood_references` | 10,419 | CMA-intersecting UNOSAT baseline/event polygons; originals retained. |
| `road_nodes` | 508,854 | Road graph nodes; component id is NULL because the source layer does not provide it. |
| `grid_cells` | 1,319,380 | CMA master cells loaded by batched PostgreSQL COPY. |
| `building_footprints` | 382,294 | OSM-derived building geometries. |
| `observation_records` | 266,773 | ERA5 hourly, NASA POWER daily, IMERG daily CMA means, reservoir daily storage and OpenCity monthly storage. |
| `flood_labels` | 21,927 | UNOSAT, observed/modelled OpenCity, GFD coarse cross-check and derived exploratory labels with confidence tiers. |
| `sentinel_scenes` | 13 | Scene metadata and SAFE-manifest footprints; no image pixels. |
| `data_manifest` | 117 | Current snapshot of `docs/DATA_MANIFEST.csv`; latest load record is verified against the file hash. |
| `dataset_catalog` | 59 | Source path, source layer, hash, CRS, row count, caveat/licence and boundary provenance. |
| `schema_migrations` | 11 | Applied migration names and SHA-256 checksums (001–011). |

### CMA intersection flags

The five OSM tables retain their original buffered-extract rows and now have an indexed `in_cma` boolean. It is true when the EPSG:32644 feature geometry intersects the selected CMA polygon; a feature that only touches the boundary is therefore counted inside. Use `WHERE in_cma` (or `NOT in_cma`) for CMA-only analysis. The `v_roads`, `v_facilities`, `v_waterways`, and new `v_buildings` views expose the flag; road, facility and waterway vector tiles also carry it. Full facility category counts are in `CMA_FACILITY_COUNTS.csv`.

| Table | Inside | Outside | Total |
|---|---:|---:|---:|
| `road_edges` | 414,822 | 40,463 | 455,285 |
| `road_nodes` | 463,926 | 44,928 | 508,854 |
| `facilities` | 15,162 | 251 | 15,413 |
| `waterways` | 687 | 72 | 759 |
| `building_footprints` | 375,832 | 6,462 | 382,294 |

All loaded records outside the catalogue include `source_id`, file SHA-256, loader name and load time. The full source-to-table reconciliation, labels, area values, invalid reasons, spatial query evidence and remaining caveats are in `docs/STAGE5_RECONCILIATION.md`.

## Geometry, CRS and views

Project grid and GIS geometry tables use EPSG:32644. Sentinel scene footprints remain EPSG:4326. The original 235 invalid UNOSAT geometries remain in `flood_references.geom`; polygon-only `ST_MakeValid` results are in `geom_repaired`, with `is_valid`. All repaired UNOSAT geometries pass validity checks. OpenCity labels likewise retain their imported geometry and have a separate repaired geometry and validity flag. `v_flood_references` and `v_flood_labels` return repaired geometries; the flood-reference MVT function uses repaired geometry too.

Five tile functions are installed: `mvt_study_area`, `mvt_roads`, `mvt_facilities`, `mvt_waterways`, and `mvt_flood_references`. Each returned a nonempty z=12 Chennai tile during the most recent smoke check. Indexed sample queries and their actual execution timings are recorded in `STAGE5_RECONCILIATION.md`.

## CMA boundary provenance

The boundary catalogue entry records the Datameet `Municipal_Spatial_Data` file `Chennai/CMA.geojson`, with retrieval around 8 Sep 2026 based on its filesystem date. The geometry area is 1,187.46 km², consistent with the pre-2022 CMA of about 1,189 km². It is a community dataset and not an official CMDA product; exact vintage and authoritative status remain unverified. The local path is `data/raw/boundary/chennai_cma_boundary.geojson` (SHA-256 `89e81f8309a40ea9f24cf5e35c832b75ed937b65b111389d8ed8df4931804ad7`). The boundary was not edited.

## Digital Twin foundation schema

The separate `twin` schema is a versioned state-model foundation, not a second copy of static GIS data. `twin.grid_zones` views the existing grid-cell dimension, while dynamic cell state is referenced by file path and SHA-256. Edge and facility states reference Stage 5 feature IDs; four reservoir identities are seeded from existing daily observations, with unknown capacities left NULL. Replay windows are PLANNED; no predicted state rows or models have been created. See `docs/TWIN_MODEL.md`.

## Backup and restore history

The earlier Stage 5/6 acceptance report records the custom-format backup and the successful restore into a temporary database. All seven tables present at that time matched; the temporary database was dropped. The role's temporary `CREATEDB` permission was subsequently revoked by the user. This later Stage 5 completion added migrations 004–008 and additional tables; it did not create or restore any database. Do not use the earlier seven-table restore as a backup/restore check of the new extension tables.
