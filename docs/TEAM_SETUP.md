# Team setup: local PostGIS database

These instructions are for a teammate using the project on Windows with Docker Desktop and Docker Compose. The service uses the local image `postgis/postgis:18-3.6-alpine`, publishes PostgreSQL only on `127.0.0.1`, and keeps data in the named Compose volume `twinguard_postgres_data` (with the Compose project prefix added to its Docker volume name).

## Keep secrets and dumps private

- Copy `.env.example` to `.env` once, then enter the database credentials locally. Compose reads the values from `.env`.
- Never paste, print, commit, or send `.env` values in screenshots, chat, shell output, or logs. Do not put credentials in a command line.
- Database dumps are large and are excluded from Git under `backups/`. Share a dump privately with the teammate who needs it; do not add it to Git.
- Keep `data/raw/` read-only.

## Start and check the database

From the project root, validate and start the service:

```powershell
docker compose config --quiet
docker compose up -d
docker compose ps
```

Wait until the `db` service reports `healthy`. The default host port is 5433, configurable with `DOCKER_POSTGRES_HOST_PORT` in `.env`; the local PostgreSQL server remains on its separate port. The published address should be `127.0.0.1`, not all network interfaces.

## Restore a privately shared dump

For a manual restore, use a fresh, empty project database. Do not restore over a database that already contains project schemas. Replace the example file name below with the exact privately shared archive name; keep the original dump in the ignored `backups/` folder.

```powershell
docker cp backups\twinguard_shared.dump tiwnguard-db-1:/tmp/twinguard_shared.dump
docker compose exec -T db sh -lc 'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore --exit-on-error --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB" /tmp/twinguard_shared.dump'
docker compose exec -T db rm -f /tmp/twinguard_shared.dump
```

The password is expanded inside the container process from the Compose environment and is not an argument or printed value. If restore reports an error, stop and preserve the dump; do not retry against a partially populated schema without first identifying the failure.

## Verify the restored database

List loaded tables and compare their counts with the checked-in Stage 5 report:

```powershell
docker compose exec -T db sh -lc 'psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT schemaname, tablename FROM pg_tables WHERE schemaname = $$twinguard$$ ORDER BY tablename;"'
```

For row counts, use the table totals in [Stage 5 and 6 report](STAGE_5_6_REPORT.md). The project clone helper, `tools/db_clone_to_docker.py`, reuses a local custom-format dump only when it is at least as new as the latest recorded migration; otherwise it creates a fresh dump. It first saves any existing Docker `twinguard` and `twin` schemas to a separate ignored pre-clone archive, then replaces those schemas, restores both schemas, compares every table count, and compares PostGIS validity and SRID checks. Run it only when the intention is to make Docker match local; the pre-clone archive is the recovery copy. It requires the local database, PostgreSQL client tools, and a healthy Docker database.

For a spot-check of geometry validity and SRIDs in a restored copy, first list its geometry columns, including repaired and original-preserved geometry columns:

```powershell
docker compose exec -T db sh -lc 'psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT f_table_name, f_geometry_column, srid FROM geometry_columns WHERE f_table_schema = $$twinguard$$ ORDER BY 1,2;"'
```

Then check each listed geometry column with `ST_IsValid(geom)` and `ST_SRID(geom)`, using its actual column name and expected SRID. Do not assume every geometry column is named `geom`.

## Stop safely

```powershell
docker compose stop
```

This stops the container and preserves the named database volume. **Do not run `docker compose down -v`**: `-v` deletes the database volume. Do not remove the named volume in Docker Desktop.

## Common problems

- **Port 5433 is busy:** check whether another local service is using it. Change only `DOCKER_POSTGRES_HOST_PORT` in `.env` to a free port, then run `docker compose up -d` again. Keep local `POSTGRES_PORT` separate.
- **Service is `starting` or `unhealthy`:** inspect `docker compose logs --tail 50 db`; do not delete the volume as a troubleshooting step.
- **Authentication failed:** check the local `.env` values and confirm they match the database initialized in the named volume. Never paste the values into a report.
- **`pg_restore` says the target schema already exists:** stop. The target is not empty; do not use `--clean` or drop the schema without an explicit recovery plan.
- **Connection refused or Docker reports a read-only filesystem:** leave the dump and volume in place, check Docker Desktop status, and retry only after the engine is healthy.
- **Dump is not a PostgreSQL custom archive:** check it with `pg_restore --list` before attempting restoration. Do not unzip or edit the archive.

## Current verification note

On 24 October 2026, the healthy Docker target was refreshed from local using `tools/db_clone_to_docker.py`. The helper created a fresh 288,988,977-byte local archive because the earlier dump predated migration 010, preserved the existing partial Docker schemas in a 242,582,654-byte pre-clone archive, restored both schemas, and matched every table count. Twenty geometry columns matched; the 54 and 235 invalid original polygon records were preserved as expected, repaired geometry columns were valid, and there were no SRID mismatches. Timings are recorded in `ISSUES.md`. Both archives are local-only under ignored `backups/`; share dumps privately, never through Git.
