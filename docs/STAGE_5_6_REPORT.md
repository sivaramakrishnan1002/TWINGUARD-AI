# Stage 5 and 6 report

Updated 2026-10-23 (Asia/Kolkata). `data/raw` remained read-only. No network download, login, install, or container start occurred. Credentials were used only by the local DB parser and were not printed or logged.

## Stage 5 completion

Migrations 001–008 are applied to the existing `twinguard` schema. Added repeat-safe loaders and read-only verification in `pipelines/stage5/`. The 1,319,380-row grid was imported in PostgreSQL COPY batches. Observation tables preserve native cadence and missing-value flags; label records distinguish UNOSAT, observed, modelled, coarse cross-check and derived/unvalidated sources. Sentinel rows store metadata and footprints only.

| Table | Rows |
|---|---:|
| `study_area` | 1 |
| `road_edges` | 455,285 |
| `facilities` | 15,413 |
| `waterways` | 759 |
| `flood_references` | 10,419 |
| `road_nodes` | 508,854 |
| `grid_cells` | 1,319,380 |
| `building_footprints` | 382,294 |
| `observation_records` | 266,773 |
| `flood_labels` | 21,927 |
| `sentinel_scenes` | 13 |
| `data_manifest` | 117 |
| `dataset_catalog` | 59 |
| `schema_migrations` | 8 |

The loaded UNOSAT count is 10,419 because it includes four source layers spatially intersecting the selected CMA: 4,704 (12 Nov), 3,710 (24 Nov), 1,360 (1 Sep baseline) and 645 (14 Oct baseline). These are subsets of larger source-wide counts. The routing edge table matches its own 455,285-row vehicle edge source; the 1,071,656 all-class directed graph arcs are a different graph. Facilities and waterways source-count scope differences are documented in `STAGE5_RECONCILIATION.md`.

The 235 invalid original UNOSAT geometries were preserved; repaired polygon-only geometries are stored separately and all pass validity checks. An additional 54 invalid OpenCity polygons were also preserved with valid repaired geometry. Dissolved/intersected EPSG:32644 event areas are 84.9246 km² (12 Nov) and 98.3137 km² (24 Nov), each within 1% of the referenced 84.78 and 98.16 km² values.

Catalog-count comparison and orphan provenance checks both returned zero discrepancies. All 13 Sentinel footprints intersect the CMA. Every required MVT smoke-test tile was nonempty. Four sample `EXPLAIN ANALYZE` spatial queries used their GiST indexes; timings are in the reconciliation report. Source extents are not fully covered by the CMA for some roads, nodes, facilities, buildings and waterways because source geometries can cross or extend beyond the boundary; they were retained as imported.

## Stage 6 and earlier acceptance work

PostgreSQL 18.6 and PostGIS 3.6.2 were verified locally. Compose uses `postgis/postgis:18-3.6-alpine`, PostgreSQL 18's `/var/lib/postgresql` volume path, a named volume and host port 5433; containers were not started. Existing local DB connection settings are read from `.env`; `.env` was not edited or printed.

The earlier backup/restore acceptance test passed before the current Stage 5 extension was added: a 50,667,495-byte custom-format backup (SHA-256 `22e45700e2b18b4a1454050a184c5fa783e500c17563f6ad367bff62fa6d377f`, 58 TOC entries) was restored to a temporary database cloned with PostGIS, the seven then-existing table counts matched, and that temporary database was dropped. The user later confirmed the temporary `CREATEDB` grant was revoked. That historical restore did not exercise the new tables from migrations 004–008.

## Tests, lineage and raw audit

- `pytest -q`: **12 passed, 0 failed** in 129.67 seconds.
- Loader idempotence rerun: all source counts were reported unchanged; the 86 IMERG records, all 13 Sentinel scenes and label rows were not duplicated. The loader returned 0 newly inserted Sentinel rows because all 13 were already present.
- Lineage refreshed: **67 rows** in `docs/DATA_LINEAGE.md`.
- Read-only raw audit: **144 files**, 20,338,302,958 bytes; **144 hash matches**, 0 missing comparable hashes, 0 mismatches. Raw files were not changed.
- Migration runner was rerun in module form after its import fix and returned `none; schema is current`.

The Stage 5 extended backup/restore was not attempted: the earlier temporary `CREATEDB` grant is revoked, and this task did not authorize changing that grant or touching another database. The former restore test covered only the seven tables present before migrations 004–008.

Commit: **03fafe5ab6a2b2ecf15e47cd82476dfd04a0f961** (`Complete Stage 5 data loading and verification`)

## Scope boundary

Stage 7, database/API work beyond this schema/load completion, model training and viewer work were not started.
