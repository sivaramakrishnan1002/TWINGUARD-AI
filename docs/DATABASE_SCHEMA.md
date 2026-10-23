# Stage 5 database schema and current load

Updated 2026-10-23 (Asia/Kolkata). The local `twinguard` database uses schema `twinguard`, PostgreSQL 18.6 and PostGIS 3.6.2. Scripts read `.env` with the project's custom parser; credentials and connection strings are never logged. `.env` is unchanged. No container or package installation was used for this update.

## Migrations

The checksum ledger contains eight migrations. `pipelines/stage5/apply_migrations.py` is safe to rerun and refuses a changed checksum for an applied migration.

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
| `data_manifest` | 117 | Snapshot of `docs/DATA_MANIFEST.csv` when loaded. |
| `dataset_catalog` | 59 | Source path, source layer, hash, CRS, row count, caveat/licence and boundary provenance. |
| `schema_migrations` | 8 | Applied migration names and SHA-256 checksums. |

All loaded records outside the catalogue include `source_id`, file SHA-256, loader name and load time. The full source-to-table reconciliation, labels, area values, invalid reasons, spatial query evidence and remaining caveats are in `docs/STAGE5_RECONCILIATION.md`.

## Geometry, CRS and views

Project grid and GIS geometry tables use EPSG:32644. Sentinel scene footprints remain EPSG:4326. The original 235 invalid UNOSAT geometries remain in `flood_references.geom`; polygon-only `ST_MakeValid` results are in `geom_repaired`, with `is_valid`. All repaired UNOSAT geometries pass validity checks. OpenCity labels likewise retain their imported geometry and have a separate repaired geometry and validity flag. `v_flood_references` and `v_flood_labels` return repaired geometries; the flood-reference MVT function uses repaired geometry too.

Five tile functions are installed: `mvt_study_area`, `mvt_roads`, `mvt_facilities`, `mvt_waterways`, and `mvt_flood_references`. Each returned a nonempty z=12 Chennai tile during the most recent smoke check. Indexed sample queries and their actual execution timings are recorded in `STAGE5_RECONCILIATION.md`.

## CMA boundary provenance

The boundary catalogue entry names `data/raw/boundary/chennai_cma_boundary.geojson`, SHA-256 `89e81f8309a40ea9f24cf5e35c832b75ed937b65b111389d8ed8df4931804ad7`, and source URL `https://github.com/datameet/Municipal_Spatial_Data`. The source retrieval date is not in the local records, so it is stored as unknown/NULL. The project-selected older boundary's source vintage and authoritative status remain unverified. The source boundary was not edited.

## Backup and restore history

The earlier Stage 5/6 acceptance report records the custom-format backup and the successful restore into a temporary database. All seven tables present at that time matched; the temporary database was dropped. The role's temporary `CREATEDB` permission was subsequently revoked by the user. This later Stage 5 completion added migrations 004–008 and additional tables; it did not create or restore any database. Do not use the earlier seven-table restore as a backup/restore check of the new extension tables.
