# Stage 5 — database foundation

## Database and connection handling

The configured local database was reached read-only first. `SELECT version(), postgis_version()` returned PostgreSQL **18.6** and PostGIS **3.6**; the installed extension reports PostGIS **3.6.2**. No other database was queried for application work. The project schema is isolated as `twinguard` inside database `twinguard`.

Scripts use `pipelines/stage5/db_common.py`, a small `KEY=VALUE` parser for `.env`; it does not use `python-dotenv`, echo values, or log connection URLs. `.env` remains unmodified and ignored by Git. `.env.example` contains only example values/placeholders. Local scripts default to `POSTGRES_HOST=localhost`, `POSTGRES_PORT=5432`; Compose publishes to `${DOCKER_POSTGRES_HOST_PORT:-5433}` so it does not collide with local PostgreSQL. Containers were not started.

The Compose image is `postgis/postgis:18-3.6-alpine`, confirmed on the official [PostGIS image tags](https://hub.docker.com/r/postgis/postgis/tags). PostgreSQL 18 uses `/var/lib/postgresql` as its volume path; the configuration uses a separate named volume `twinguard_postgres_data`. The five requested DB libraries are present in `.venv` at the requested versions and were already pinned in `requirements.txt`: psycopg 3.3.6, psycopg-binary 3.3.6, SQLAlchemy 2.1.6, GeoAlchemy2 0.20.0, typing-extensions 4.16.0. No package was installed and requirements lines were not changed.

## Migration design

SQL migrations are ordered, SHA-256 checked, and recorded in `twinguard.schema_migrations`. An already-applied migration with a changed checksum is rejected. `apply_migrations.py` can be rerun safely; it reports no-op when schema state is current.

- `001_core_schema.sql`: schema, migration ledger, source catalog, provisional study boundary, roads, facilities, waterways, flood references, geometry/date indexes.
- `002_gis_views_and_mvt.sql`: query views and five PostGIS Mapbox Vector Tile (`bytea`) functions.
- `003_catalog_licence_notes.sql`: explicit licence/terms note in source catalog.

All database geometry uses EPSG:32644, matching the project grid. Data catalog entries carry source-relative path, source layer, file SHA-256, source CRS, row count, caveat and licence note. Unknown source terms remain explicitly unconfirmed.

## Backup and restore check

`pipelines/stage5/backup_restore.py` created a 50,667,495-byte custom-format logical backup of schema `twinguard`; archive listing passed (58 TOC entries). The temporary backup was removed when the check finished; its SHA-256 is recorded in `STAGE_5_6_REPORT.md`.

The application role does not have `CREATEDB`. Creating the requested temporary database failed with the exact non-secret error `InsufficientPrivilege: permission denied to create database`. To validate DDL recovery without touching another database, a schema-only dump was restored into a uniquely named temporary schema inside `twinguard`; 12 relations (tables and views) were restored and the temporary schema was dropped. This is not a substitute for a full data restore into a separate database. A database administrator must grant the app role `CREATEDB` temporarily or perform the restore test with an authorized role before that acceptance check is complete.

No optional viewer was created. Stage 7 (Twin/API), model training, and later stages were not started.
