# Stage 5 and 6 report

Run date: 2026-10-22 (Asia/Kolkata). Raw files were read-only. No internet downloads, installs, container starts, or Stage 7 work occurred. No credentials or connection strings were printed or logged.

| Task | Result | File | Needs my decision? |
|---|---|---|---|
| Initial read-only database check | **PASS.** PostgreSQL 18.6, PostGIS 3.6 (extension 3.6.2). Only version information was printed for the initial check. | `pipelines/stage5/db_common.py`; `docs/ISSUES.md` | No |
| Dependency pins | **PASS.** All five versions verified in `.venv`; exact pins already existed, so `requirements.txt` was not changed. | `requirements.txt` | No |
| Compose and env example | **PASS.** Verified image `postgis/postgis:18-3.6-alpine`; volume path `/var/lib/postgresql`; named volume; Docker host port defaults to 5433; local port remains 5432. Containers were not started. | `docker-compose.yml`; `.env.example` | No |
| Schema and migrations | **PASS.** Three checksum-tracked migrations applied in the `twinguard` schema; rerun reports current. | `database/migrations/`; `pipelines/stage5/apply_migrations.py`; `docs/DATABASE_SCHEMA.md` | No |
| GIS imports | **PASS.** 1 boundary, 455,285 vehicle edges, 15,413 facilities, 759 waterways, and 10,419 UNOSAT reference features loaded. All imported SRIDs are 32644. 235 invalid geometries are confined to the source flood references and preserved without repair. | `pipelines/stage6/load_gis_layers.py`; `docs/GIS_DATABASE_LAYERS.md` | Review invalid flood geometries and confirm boundary vintage before relying on them. |
| GIS verification, views, MVT | **PASS with warning.** Views match table counts; five tile functions returned MVT payloads for the Chennai test tile. 15,162 facilities are inside the boundary; 414,822 road features intersect it; 687 waterways intersect it. | `pipelines/stage6/verify_gis.py`; migration `002`; `docs/GIS_DATABASE_LAYERS.md` | Optional: decide whether to build a viewer/API later. |
| Backup / restore | **PARTIAL.** Custom-format backup created (50,667,495 bytes; SHA-256 `0a646c600c737e386bb6a57e7aaa245af3b8d33f56df80165c11383157c31ee0`); archive verified, 58 TOC entries. App role lacks `CREATEDB`, so full restore into a separate temporary database could not run. Schema-only restore into a temporary schema succeeded (12 relations); that schema was dropped. | `pipelines/stage5/backup_restore.py`; `docs/DATABASE_SCHEMA.md`; `docs/ISSUES.md` | **Yes:** an authorized role with temporary `CREATEDB` privilege is needed to complete the separate-database restore acceptance test. |
| Tests | **PASS.** `pytest`: 10 passed, 0 failed. | `tests/phase4/`; `tests/stage5_6/` | No |
| Lineage and raw audit | **PASS.** Lineage refreshed to 67 rows. Raw audit: 144 files, 20,338,302,958 bytes; 144 size/hash matches, zero unmatched, zero mismatches. The audit parser was fixed for IMERG `File:` / `Size bytes:` entries. | `docs/DATA_LINEAGE.md`; `tools/audit_raw_logs.py`; `docs/ISSUES.md` | No |

## Table row counts

| Table | Rows |
|---|---:|
| `twinguard.study_area` | 1 |
| `twinguard.road_edges` | 455,285 |
| `twinguard.facilities` | 15,413 |
| `twinguard.waterways` | 759 |
| `twinguard.flood_references` | 10,419 |
| `twinguard.dataset_catalog` | 8 source records |
| `twinguard.schema_migrations` | 3 migration records |

## Verification timings

Observed wall-clock timings for the completed final checks (rounded to the nearest second unless noted):

| Check | Time |
|---|---:|
| Initial version query | 1.5 s |
| Migration idempotence check | 2.0 s |
| GIS verification query set | 7.2 s |
| Pytest suite (10 tests) | 16.8 s |
| Raw size/SHA-256 audit (144 files, about 20.3 GB) | 52.3 s |
| Lineage refresh (67 outputs) | 5.2 s |
| Backup, archive verification, privilege check and schema-only restore smoke test | 22.3 s |
| Loader idempotence check | 19.5 s |

The first full GIS import ran in two successful insert batches; the exact end-to-end duration was not measured. The 19.5 s figure above is the later checksum/idempotence recheck, not the initial import duration.

## Remaining acceptance item

Only the full restore into a separate temporary database remains blocked: the configured application role has `CREATEDB=false` and `SUPERUSER=false`; PostgreSQL returned `InsufficientPrivilege: permission denied to create database`. No other database was accessed or created. The optional viewer was not built. Stage 7 and later work remain unstarted.
