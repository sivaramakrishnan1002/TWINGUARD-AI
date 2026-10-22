# Team guide

## People and roles

Names, institution, guide/supervisor, deadlines and role assignments are **[TO BE FILLED]**. Suggested roles—not assignments—are: data stewardship and provenance; flood-label review; modelling/evaluation; backend/database; interface and user testing; integration/documentation. One person may cover several roles. [user]

## Machine setup already recorded

- Project root is `D:\TIWNGUARD`, branch `main`. [repo: current Git state]
- Python dependencies are pinned in `requirements.txt`. The Phase 3 report says to use `.venv` and records no global package installation. [repo: `requirements.txt`, `docs/PHASE3_LOG.md`]
- `docker-compose.yml` uses verified `postgis/postgis:18-3.6-alpine`, a named data volume at PostgreSQL 18's `/var/lib/postgresql` path, and a health check. It reads credentials from `.env`; `.env.example` contains no real secrets. Containers were not started. [repo: Compose files]
- Local PostgreSQL 18.6/PostGIS 3.6.2 and the `twinguard` database are verified. Local scripts use port 5432; Compose defaults to host port 5433. A separate-database restore test remains pending the app role's `CREATEDB` privilege. [repo: `docs/STAGE_5_6_REPORT.md`]
- Never paste passwords, access tokens or real `.env` values into chat, Git or this handbook. Add `.env` locally and keep it untracked. [repo: `.gitignore`; user]

## Folder map

`data/raw/` is the immutable source archive. `data/processed/` and `data/features/` contain derived work and are excluded from Git. `docs/` contains plans, manifests, checks and reports. `pipelines/phase3/` contains the recorded Phase 3 scripts; `tools/` contains verification/audit helpers. `services/`, `frontend/`, `notebooks/` and `experiments/` are planned spaces. Use [Coverage Matrix](COVERAGE_MATRIX.md) for a fuller path map. [repo: `.gitignore`, `README.md`, folder tree]

## Golden rules

1. Never change, rename, move, unzip or delete raw originals. [user]
2. Log each new source with exact URL, date/time, size, SHA-256, licence and verification. Never invent missing licence details. [user; repo: `data/raw/**/DOWNLOAD_LOG.txt`]
3. Do not commit raw data, derived data or secrets. Check `git status` before and after each change. [repo: `.gitignore`; user]
4. Read a script and its output paths before running it. Some scripts create files and intentionally refuse overwrite. [repo: `pipelines/phase3/*.py`]
5. Use the project environment, record versions and preserve logs. [repo: `docs/PHASE3_LOG.md`]
6. Keep observed, PDF-digitised and model-derived labels distinct. [repo: `docs/PHASE3_PLAN.md`]

## Script map and safe use

Existing scripts and functions are described in [Engineering Phases](08_Engineering_Phase2_and_Phase3.md). To inspect options, read the script or invoke its documented help only if that does not execute a processing path. Scripts can write under `data/features`/`data/processed`; do not rerun them without an approved scope, clean output plan and backup/no-overwrite review. `tools/audit_raw_logs.py`, `tools/verify_asf_sentinel.py` and `tools/osm_waterways_inventory.py` are described as read-only, but verify their current code before relying on them. [repo: scripts]

### Recorded Phase 3 command order (reference only)

The repository documents this order in `pipelines/phase3/README.md`; these commands can create or update derived files, so this list is for understanding and reproducibility, not permission to run them. Phase 3 has already been run and no processing is requested in this handbook task. [repo: `pipelines/phase3/README.md`; user]

From `D:\TIWNGUARD`, the documented commands are:

1. `.venv\Scripts\python.exe pipelines\phase3\phase3_core.py --task all` — grid, terrain, WorldCover and WorldPop derivatives.
2. `.venv\Scripts\python.exe pipelines\phase3\weather_reservoirs.py` — rainfall and reservoir summaries, including the illustrative Track B screen.
3. `.venv\Scripts\python.exe pipelines\phase3\flood_labels_inspection.py` — exploratory UNOSAT/GFD/OpenCity label inspection.
4. `.venv\Scripts\python.exe pipelines\phase3\osm_extract_graph.py` — roads, facilities, buildings and waterways; refuses to overwrite an existing GeoPackage.
5. `.venv\Scripts\python.exe pipelines\phase3\split_osm_layers.py` — splits the GeoPackage; refuses existing destinations.
6. `.venv\Scripts\python.exe pipelines\phase3\summarize_osm_gpkg.py` — inventories the existing GeoPackage.
7. `.venv\Scripts\python.exe pipelines\phase3\population_exposure.py` — population summaries in road and facility buffers.
8. `.venv\Scripts\python.exe pipelines\phase3\summarize_event_peak_rainfall.py` — peak rainfall summaries from the existing hourly table.
9. `.venv\Scripts\python.exe pipelines\phase3\validate_outputs.py` — checks derived raster alignment, valid data and layout.
10. `.venv\Scripts\python.exe tools\audit_raw_logs.py` — read-only raw-file size/hash comparison; read the script first because it hashes every raw file and can take time.
11. `.venv\Scripts\python.exe tools\update_phase3_manifest.py` — refreshes derived-output rows in the manifest.

The Phase 3 README states that raw inputs are read-only, PDFs are not digitised, Sentinel-1 is not processed, no model is trained and no software is installed. It also records that CSV is used because no Parquet engine is installed and the OSM extractor uses a custom graph routine because NetworkX/GDAL CLI bindings were unavailable. Check disk space before any approved future output above 2 GB. [repo: `pipelines/phase3/README.md`]

The project venv has no NetworkX, SNAP, pyroSAR, GDAL Python bindings/CLI, `pyarrow` or `fastparquet`, according to the Phase 3 report. Do not install a package globally. Ask before changing dependencies. [repo: `docs/PHASE3_LOG.md`]

## Manual tasks for the student

- Decide old versus expanded CMA boundary. [repo: `docs/MANUAL_TODO.md`]
- Ask NRSC for original Dec 2015 flood GIS products or document the fallback. The assistant must not send requests. [repo: `docs/MANUAL_TODO.md`; user]
- Digitise 2021/2023 map PDFs only after checking legend/frame/scale and documenting control points and positional error. [repo: `docs/PHASE3_PLAN.md`]
- Compare WorldPop with compatible census totals; resolve NoData and boundary-vintage differences. [repo: `docs/MANUAL_TODO.md`]
- Verify rainfall units, reservoir capacity history and missing release records. [repo: `docs/MANUAL_TODO.md`]
- Confirm Sentinel data terms and OSM attribution obligations. [repo: `docs/SENTINEL_VERIFICATION.md`, `docs/OSM_COUNTS.md`]

## Suggested Git habit

Work on one small change at a time. Review `git diff`, verify that no data or secret is staged, commit a clear message, and record evidence in documentation. This is a suggestion, not an existing team policy. [user]

## Asking for help

Share the exact file path, command and error text, but remove credentials, personal tokens and `.env` values. For confusing QGIS/browser steps, capture a screenshot without personal information. [user]
