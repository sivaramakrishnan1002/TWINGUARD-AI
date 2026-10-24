# Project issues and failed requests

## Stage 7 foundation — 2026-10-24

- The separate `twin` schema migration (`010_create_twin_schema.sql`) applied successfully. Database verification found all 11 twin objects (including the grid-zone view), three event windows in `PLANNED` status, four reservoir identities with capacities left NULL, and 1,319,380 grid zones. No forecast/state rows were generated.
- The full pytest run completed with **14 passed, 1 failed**. The remaining failure is `test_postgis_schema_and_loaded_row_counts_match_catalog`: `stage5_data_manifest` still has the hash of the 117-row CSV snapshot from its load time, while `docs/DATA_MANIFEST.csv` has since been updated to record boundary provenance. All other source file/hash checks match. No reload was performed because the task did not authorize new loads; decide whether to refresh only the manifest snapshot and its provenance in a later approved database operation.
- Corrected the stale Stage 5 migration-count test expectation from eight to nine numbered Stage 5 migrations; migration 009 was added after that test was written. Migration 010 is the Stage 7 twin schema migration.
- Offline API validation first found malformed JSON in `docs/api/backend.yaml` (`JSONDecodeError: Expecting ',' delimiter`); the closing structure was corrected. Both JSON-as-YAML OpenAPI 3.1 contracts then passed required-path, operation, response and local-reference checks. No full external OpenAPI validator is installed.
- FastAPI/Starlette/httpx and Maven/Gradle were absent. No packages or global tools were installed; no application skeleton was added. Setup requirements and the exact installed versions are recorded in `SETUP_TOOLS.md`.
- Read-only lineage refresh completed with 67 rows. Raw audit matched all 144 files (20,338,302,958 bytes), zero mismatches and zero files without a comparable hash. Raw data was not modified.

## Docker database clone attempt — 2026-10-24

- `docker compose config --quiet` passed after changing the published mapping to localhost-only. The first `docker compose up -d` recreated the prior container but failed to bind `127.0.0.1:5433` with: `ports are not available: exposing port TCP 127.0.0.1:5433 -> 127.0.0.1:0: listen tcp4 127.0.0.1:5433: bind: Only one usage of each socket address (protocol/network address/port) is normally permitted.` Retrying `docker compose up -d` said `Started`.
- The local custom-format dump succeeded and was written as `backups/twinguard_20261024T050742Z.dump` (288,954,014 bytes). The folder is excluded from Git. Its runtime is approximately 93 seconds based on the UTC timestamp in the filename and the file modification time; the script's stopwatch value was not emitted. Restore runtime was not captured because the restore step failed before the script reached its report output.
- `.venv\Scripts\python.exe tools\db_clone_to_docker.py` stopped at restore: `RuntimeError: pg_restore failed with exit code 1; client diagnostics withheld`. A sanitized diagnostic from the same attempt was: `pg_restore: error: connection to server at "[ENDPOINT]", port [ENDPOINT] failed: Connection refused (0x0000274D/10061)`.
- Docker reported inconsistent state after the retry: `docker ps` showed the container running but with no published port; `docker inspect` showed no published ports, while another inspect read failed with `open /var/lib/docker/containers/.../hosts: read-only file system`. `docker compose logs --tail 25 db` also failed with `open /var/lib/docker/containers/.../local-logs/container.log: read-only file system`. The compose command did not remove the named volume. No restore or count comparison was verified.
- At the time of this failed attempt, the helper refused to overwrite a pre-existing `twinguard` target schema. Docker reachability was later restored and the retry is recorded below; no volume removal was used.

## Docker clone retry — resolved 2026-10-24

- Docker was reachable on the configured loopback port. The old 288,954,014-byte dump was older than the latest local migration (010), so the helper made a fresh local archive. Before replacing the partial Docker copy, it preserved both existing project schemas in a separate ignored pre-clone dump. No Compose shutdown, volume deletion, or raw-data change occurred.
- Updated `tools/db_clone_to_docker.py` to include both `twinguard` and `twin`, compare every base table in both schemas, and check all PostGIS geometry columns. The original flood-label (54) and flood-reference (235) geometries are intentionally retained invalid source geometries; their repaired columns are valid. The comparison accepts only those documented original counts, requires repaired/effective geometries valid, and requires matching SRIDs.
- Timings: fresh local dump 55.052 s; Docker pre-clone backup 53.681 s; restore 69.831 s; total including row counts and geometry checks 255.902 s. Fresh dump size 288,988,977 bytes; pre-clone backup size 242,582,654 bytes. Both are under ignored `backups/` and were not committed.
- All 24 base-table counts matched:

| Schema.table | Rows |
|---|---:|
| `twin.alerts` | 0 |
| `twin.event_replays` | 3 |
| `twin.facility_state` | 0 |
| `twin.grid_state_artifacts` | 0 |
| `twin.model_versions` | 0 |
| `twin.reservoir_state` | 0 |
| `twin.reservoirs` | 4 |
| `twin.road_edge_state` | 0 |
| `twin.scenarios` | 0 |
| `twin.state_runs` | 0 |
| `twinguard.building_footprints` | 382,294 |
| `twinguard.data_manifest` | 117 |
| `twinguard.dataset_catalog` | 59 |
| `twinguard.facilities` | 15,413 |
| `twinguard.flood_labels` | 21,927 |
| `twinguard.flood_references` | 10,419 |
| `twinguard.grid_cells` | 1,319,380 |
| `twinguard.observation_records` | 266,773 |
| `twinguard.road_edges` | 455,285 |
| `twinguard.road_nodes` | 508,854 |
| `twinguard.schema_migrations` | 10 |
| `twinguard.sentinel_scenes` | 13 |
| `twinguard.study_area` | 1 |
| `twinguard.waterways` | 759 |

- Twenty geometry columns matched between local and Docker; repaired columns and all other geometries passed validity checks, the 289 original-invalid geometries matched their expected preserved source counts, and there were zero SRID mismatches.
- Secret-safety scan: `.gitignore` and `requirements.txt` contain no `.env` values. `docker-compose.yml` contains no password value, but contains non-secret `.env` values used for the configured database name and PostgreSQL port; it is therefore left uncommitted under the instruction not to commit any `.env` value. No `.env` values were printed.

## Phase 4 completion update — 2026-10-17

- The user installed packages in `.venv`. Verified versions with `importlib.metadata`: `pyarrow==26.0.0`, `pytest==9.1.1`, `colorama==0.4.6`, `iniconfig==2.3.1`, `pluggy==1.7.0`, `Pygments==2.21.0`. No package was installed in this turn and no network was used. These exact six pins were appended to `requirements.txt`; existing dependency lines were preserved.
- The Parquet blocker is resolved. Created the 2015, 2021 and 2023 aligned event tables and the 30 m static CMA cell table. See `TIME_ALIGNMENT.md`, `FEATURE_DICTIONARY.md`, and the current Stage 4 report for row counts and field semantics.
- The previous lineage command refused to rerun because its generated report already existed. Fixed `pipelines/phase4/build_lineage.py` to atomically refresh only its generated `docs/DATA_LINEAGE.md`, as required for a re-runnable lineage tool; it does not edit source rasters or vector files.
- pytest ran the full `tests` suite: **6 passed, 0 failed, 0 skipped**. The earlier pytest/pyarrow absence and skipped-test notes above are historical and resolved.

Historical entries are dated 2026-10-08 unless another date is shown. SSL verification was never disabled.

- NRSC original 2023 URL https://www.nrsc.gov.in/sites/default/files/pdf/DMSP/TN_7_12_2023_Michaung_Cyclone1of2.pdf returned HTTP 404; no file saved.
- NRSC unconfirmed alternate https://www.nrsc.gov.in/nrscnew/assets/pdf/DMSP/TN_7_12_2023_Michaung_Cyclone1of2.pdf returned HTTP 404; response began with gzip bytes and was not PDF.
- Overpass main endpoint https://overpass-api.de/api/interpreter returned HTTP 406 on three attempts. OSM usage guidance says wait 30 seconds after 406; our retries were too soon. No further request to that endpoint.
- Documented alternate https://overpass.private.coffee/api/interpreter timed out on tile 1: ReadTimeout, read timeout 15 seconds. Geofabrik Southern Zone PBF was subsequently acquired and counted; see `docs/OSM_COUNTS.md`.
- Four initially constructed WorldCover tile names N12E079/N12E080/N13E079/N13E080 returned 404. Official grid selected N12E078, which downloaded and validated.
- WorldPop 2024 file advertised 766,892,663 bytes; transfer stalled at 5,242,880 bytes over several minutes and was interrupted without an HTTP exception. Partial file removed. The newer R2025A file was found but not downloaded.
- CAG PDF requests timed out from www.cag.gov.in and cag.gov.in at 20 seconds; no report saved.
- TN reservoir portal returned a username/password + OTP login shell. No login/bypass was attempted; shell not retained.
- 2015 polygon coverage percentages were computed read-only with the project-local GeoPandas/Shapely/pyproj stack; detailed method/results are in `COVERAGE_2015.md`.
- Initial Sentinel-2 STAC limit 500 returned LimitValidationError; corrected limit 100 with fields extension yielded 10 qualifying S2 items. Final CSV reflects corrected results.
- Official Bhuvan flood viewer checked 2026-10-08: lists Tamil Nadu 2015 layers 03/12/2015-06Hr, 04/12/2015, 05/12/2015, 05-07/12/2015, 08/12/2015-18Hr and Chennai experimental RISAT-1 cumulative inundation (3,4,6 Dec). The displayed entries route to viewer zoom links; no public direct data file was identified. No December layer saved. The 07-Dec NRSC hydrological simulation report is not an observed inundation GIS layer.
- Geofabrik official listing shows Southern Zone OSM PBF about 532 MB (BBBike about 592 MB), both below 2 GB. First direct Geofabrik attempt failed: `curl: (7) Failed to connect to download.geofabrik.de:443 over proxy 127.0.0.1 after 2033 ms`. An authorized elevated retry later succeeded; see roads download log. OSM feature count pass completed read-only; see `docs/OSM_COUNTS.md`.
- WorldPop R2025A retry connected but stalled at 112,704,318 bytes. Curl stopped it: `(28) Operation too slow. Less than 1024 bytes/sec transferred the last 30 seconds`. The exact `.part` file from this attempt was removed. Disk free before attempt: 248,189,861,888 bytes. No raster retained.
- CAG report retry with a 120-second max-time failed: `curl: (28) Connection timed out after 120009 milliseconds`. The configured elevated curl's automatic retry was stopped to honor the task's one-retry limit. No file/partial remained.
- Required Michaung 2023 PDF 1 and optional PDF 2 were each tried once in this run; both returned curl HTTP 000 due proxy connection failures (`Failed to connect to www.nrsc.gov.in:443 over proxy 127.0.0.1 after about 2 seconds`). The primary URL had returned HTTP 404 in earlier attempts. The unconfirmed alternate URL was not retried.
- Official NDEM pages exposed 7 Dec 2023 map `tncyclone50dsc07122023_0600hrs_map.pdf` (includes Chennai and northern districts) and 18 Dec map `tnflood50dsc12182023_1800hrs_vap1.pdf` (Tuticorin district). Initial restricted-shell requests failed via proxy; elevated retries succeeded. Both PDFs are saved, logged, and verified. The official map descriptions state products are preliminary, may include rain/low-lying/paddy standing water, and have no ground verification.
- Project venv initially did not have pip: `python -m venv .venv` failed during ensurepip (`No module named pip`). Initial non-elevated package installation failed (`No matching distribution found`). An authorized elevated installation and pip bootstrap subsequently succeeded into `.venv` only; `requirements.txt` records the installed package versions. No global packages were installed.
- Read-only spatial intersections of November UNOSAT layers completed; results and method are in `COVERAGE_2015.md`.
- Read-only log audit found existing downloaded artifacts with their recorded sizes and hashes; unavailable files (WorldPop and CAG) are intentionally absent. Official 2023 NDEM PDFs and the Geofabrik OSM PBF are present. The 2015 zip is in its nested `2015\2015-12-04` directory and is present there; its original log's filename includes that subpath.
- The restricted shell proxy blocked initial external requests; authorized elevated retries succeeded for Geofabrik and official NDEM map PDFs. SSL verification was never disabled.

- CAG 2017 official report retry (2026-10-08), once with the requested 180-second timeout and normal SSL, failed before an HTTP response: `System.Net.Http.HttpRequestException: The SSL connection could not be established`; inner error `System.IO.IOException: Unable to read data from the transport connection: An existing connection was forcibly closed by the remote host`; socket error 10054, “An existing connection was forcibly closed by the remote host.” No SSL verification bypass was used and no file was saved.
- The Copernicus public STAC catalog returned the requested Sentinel-1 GRD item records for all three event windows. At that time no image downloads were made and the requested raw shortlist/year folders were not written because raw data was read-only for that planning pass. This historical status was superseded by the ten user-acquired ASF ZIPs verified on 2026-10-14; see `docs/SENTINEL_VERIFICATION.md` and the allowed metadata log under `senitnel1`.

- 2026-10-13: CAG executive-summary PDF subsequently downloaded from the link exposed by the official report listing and verified as a readable 7-page PDF. The earlier SSL failures remain historical attempts; SSL verification was not disabled. Full audit remains uncollected.

- 2026-10-14: The ten manually acquired ASF Sentinel-1 GRD-HD ZIPs are stored under `data/raw/satellite/senitnel1` (the directory is misspelled in the existing raw tree). The name is preserved because raw data must not be moved or renamed. All ten ZIP CRC checks passed; see `SENTINEL_VERIFICATION.md`. ASF-specific download licence/terms should be confirmed before redistribution.
- 2026-10-14: Full read-only raw-file audit found 55 data files (14,706,156,884 bytes); all 55 matched a logged size and SHA-256, with zero mismatches. Older logs contain failed-attempt entries with zero bytes and “not applicable” hashes; these do not correspond to present files and were excluded from the file-level audit. No SSL verification bypass was used.

## Phase 3 fix-up findings and diagnostic errors — 2026-10-16

- ERA5's existing event-peak summary searches the entire stored 2015 request window (1 Nov–15 Dec), which is why it names 16 Nov. It does not establish the Dec 1–2 maximum. The new report confirms 1–2 Dec rainfall is present, but lower than the 16 Nov nine-point mean. Four-day ERA5/NASA POWER agreement is modest (r=0.383, n=4) and the sources use different time standards; see `ERA5_2015_CHECK.md`.
- Diagnostic script `check_weather_2015.py` initially stopped with the exact error `ValueError: Index contains duplicate entries, cannot reshape` while pivoting multiple hourly observations to date rows. The hourly data were grouped by local date and point before reshaping; the check then completed. No raw or existing feature file was changed by the failed run.
- SciPy was unavailable in the project's local environment (`ModuleNotFoundError: No module named 'scipy'`). The WorldCover/building correlation was calculated with pandas/numpy instead; no package was installed.
- Terrain check found 255 cells below −5 m (8 clusters; about 0.2295 km²). The −64.51 m minimum is already present in the native Copernicus tile and is likely a source DEM artefact. No terrain raster was regenerated or modified. Manual visual review against authoritative elevation data is still needed before relying on derivatives there.
- Road connectivity diagnostic found 192 weak and 740 strong components. It assigns all categorized facilities to nearest graph nodes only for diagnostics; nearest-node distance is not an entrance-access guarantee. No road network was edited. The 500 m population-proximity summary counts all road classes, including footpaths/service roads; it is not evidence of evacuation accessibility.
- WorldPop native/derived CMA sums differ by 1,092.43 (about 0.0176%); the exact contribution of grid/resampling/edge-mask effects is not separately identified. Native and 30 m NoData counts are at different resolutions and must not be interpreted as equal-area counts.
- OSM source-inventory counts and extracted facility-layer counts remain non-comparable without a like-for-like recount: 908 vs 848 hospitals, 706 vs 696 schools, and 172 vs 171 shelters. Scope and tagging/deduplication differences are possible, but the exact differences are unresolved.
- The five existing exploratory label TIFFs are tiled GeoTIFFs, not COGs. They were not converted or overwritten. Their current form is usable locally but less suitable for range-based/cloud delivery.

## Phase 4 Part 1 notes — 2026-10-17

- IMERG's GDAL NetCDF subdataset opened with `NotGeoreferencedWarning: Dataset has no geotransform, gcps, or rpcs. The identity matrix will be returned.` The product uses separate CF longitude/latitude coordinate arrays, so the CMA calculation was changed to use the local NetCDF C API and the coordinate axes directly. The first draft used the GDAL array orientation incorrectly; its report was regenerated from the NetCDF dimension order `(time, lon, lat)`. Do not use that first draft's rainfall numbers. No raw granule was modified.
- A terrain script rerun stopped safely with `FileExistsError: Refusing to overwrite existing target(s): ['D:\\\\TIWNGUARD\\\\data\\\\processed\\\\terrain_cleaned', 'D:\\\\TIWNGUARD\\\\docs\\\\TERRAIN_CONDITIONING.md']`. The already generated outputs were preserved. A separate `--repair-generated-derivatives` option wrote three new, edge-safe/valid-only raster files without replacing them.
- Diagnostic inspection attempts failed with exact errors, without modifying project data: `KeyError: "['natural', 'water'] not in index"` (those fields are absent from the saved waterways layer); `ModuleNotFoundError: No module named 'fiona'` (the installed GeoPackage reader is pyogrio); `UnicodeEncodeError: 'charmap' codec can't encode characters in position 31-35: character maps to <undefined>` (Windows console encoding for Tamil text); and PowerShell `A parameter cannot be found that matches parameter name 'Pattern'.` (corrected using `Select-String`).
- No package was installed. `docs/SAR_LABEL_PIPELINE.md` records SNAP, ASF/HyP3, GDAL CLI, SciPy, pyroSAR and ASF Python package availability.
- Routing uses assumed speeds where `maxspeed` is missing and an unvalidated 0.3 m flood-passability threshold. A follow-up component audit classified the 41 unreachable sampled origins: 40 had no destination in their weak component and 1 shared a weak component with a destination but had no directed path. See `ROUTING_PROFILE.md` and the per-origin JSON.
- IMERG licence and exact download page are unavailable from local metadata and remain `TO CONFIRM`. The comparison report identifies IMERG, ERA5 and NASA POWER as estimates, not gauge truth.
# Phase 3 implementation notes — 2026-10-14

- Corrected a Python syntax error in `pipelines/phase3/phase3_core.py` before generating the grid: `SyntaxError: unmatched ')'` in the TWI expression. No source files or valid earlier outputs were changed by the failed invocation; the corrected script generated the grid and rasters.
- First `flood_labels_inspection.py` invocation reached OpenCity KML aggregation and failed with `shapely.errors.GEOSException: TopologyException: side location conflict at 80.207362282712694 13.078078266593458 0. This can occur if the input geometry is invalid.` The KMLs contain invalid polygon geometry. The pipeline was changed to check per-feature intersections rather than unioning invalid source polygons; the rerun completed without failed per-feature predicates. Raw KML remains untouched.
- First `osm_extract_graph.py` invocation reached the PBF way records and failed with `NameError: cannot access free variable 'LineString' where it is not associated with a value in enclosing scope`. A redundant local import shadowed the module import. It was removed; the corrected read-only PBF pass is running. No OSM feature output was written by the failed attempt.
- The environment has no `pyarrow` or `fastparquet` (`importlib.util.find_spec` returned false), so Phase 3 weather/reservoir tables are CSV. No package was installed. Parquet is a pending convenience-format item, not a missing measurement.
- NetworkX is absent from the project environment. The OSM pipeline uses custom adjacency, union-find, and iterative Kosaraju component logic, and records that method; verify component statistics before graph use.
- `osgeo`, SNAP `gpt.exe`, `snappy`, `snapista`, pyroSAR, and GDAL command-line tools were not available. Rasterio's bundled GDAL was used for the non-Sentinel rasters. Sentinel ZIPs were not extracted or processed.
- A first one-hot land-cover average reprojection emitted GDAL warnings that source value 0 had been changed to a tiny float (`1.401298464324817e-45`) to avoid nodata collision. The pipeline was changed to use a distinct destination nodata value; the rerun and fraction-sum validation are recorded in `PHASE3_LOG.md`.

- 2026-10-14 Phase 3: a shell invocation using system Python (instead of the project environment) failed with `ModuleNotFoundError: No module named 'geopandas'`. Re-ran using `.venv\\Scripts\\python.exe`; no packages were installed.
- 2026-10-14 Phase 3 OSM pass: the extractor reached its final built-up comparison and failed with `NameError: name 'np' is not defined. Did you mean: 'n'?`. The combined GeoPackage had already been written. It was not overwritten or rescanned; the missing inventory summary was generated read-only from its existing layers. A later summary-helper attempt failed with `AttributeError: 'DataFrame' object has no attribute 'exact_target_name_match'`; corrected by matching the actual `name` field, and the summary completed.
- 2026-10-14 Phase 3 exposure: the first summary attempt was interrupted with `KeyboardInterrupt` while repeatedly buffering/rasterizing existing geometries; the two buffer masks had already been written. The script now reuses existing masks after grid checks and computes per-point 500 m pixel-centre sums with vectorized offsets. The final CSV/JSON completed; existing mask files were preserved.
- 2026-10-14 Phase 3 validation: the first pass reported `not stored as a cloud optimized GeoTIFF ... (layout=None)` for the five existing exploratory label rasters. They are aligned, nonempty tiled GeoTIFFs, but are not COGs. To preserve existing outputs, the validator records this as a warning; all 18 rasters pass data/grid checks. No label raster was rewritten.
- 2026-10-14 Sentinel verification: two new 2021-11-16 ZIPs and one 2015-12-06 ZIP were found. `verify_asf_sentinel.py` was updated to allow the expanded collection and verified all 13 archives in place: CRC checks and metadata/name matches passed. Sentinel logs/report and three missing manifest rows were updated; raw archives were not changed. The 2015-12-06 acquisition falls within the 1–8 Dec event window but remains unprocessed imagery, not a flood label.
- 2026-10-14 manifest refresh: an initial helper constructed paths without the existing `senitnel1` directory and duplicated Sentinel records. The path mapping was corrected; the malformed duplicate rows were removed and replaced with three correct rows (`satellite/senitnel1/...`). Final manifest verification found 13 Sentinel ZIP entries.

## Phase 4 completion notes — 2026-10-17

- **Temporal alignment and static cell Parquet pending.** Exact error from `pipelines/phase4/time_alignment.py`: `ModuleNotFoundError: No module named 'pyarrow'`. Exact error from `pipelines/phase4/static_feature_stack.py`: `ModuleNotFoundError: No module named 'pyarrow'`. The virtual environment also lacks `fastparquet`; the local package cache is empty. The task forbids network access, so no package could be installed. The scripts stop before creating their requested Parquet outputs; no raw or existing feature files were changed.
- **pytest runner unavailable.** Exact error: `D:\TIWNGUARD\.venv\Scripts\python.exe: No module named pytest`. No network install was attempted. The tests were run with Python's built-in `unittest` discovery instead: five passed and the Parquet row-count test was skipped because the static Parquet output is pending.
- **Test temporary path permission issue, resolved.** Initial unittest run failed writing a temporary TIFF under the system temp path with `rasterio.errors.RasterioIOError: Attempt to create new tiff file 'C:\Users\msk10\AppData\Local\Packages\sandbox.{22117b46-294d-4c28-a80a-b938211d2a93}\AC\Temp\tmpn3udm18_\tiny.tif' failed: ... Permission denied`. The test now creates its temporary file under the project root; the rerun passed.
- **First routing addendum invocation error, resolved.** Exact error: `ModuleNotFoundError: No module named 'pipelines'`. The command-line script now adds the project root to its import path; the rerun completed and wrote the origin coverage JSON and report addendum.
- **First spatial registry pass, preserved as required.** Exact error reading zipped UNOSAT input: `DataLayerError: Layer 'LS8_20151014_PreFlood.shp' could not be opened`. The corrected script opens the archive layers using GDAL's `/vsizip` path and completed. The original `data/processed/alignment/layer_registry.json` is retained as a preliminary first pass; use the corrected `layer_registry_complete.json` for reporting. It records no analysis-grid misalignments or metadata errors.
- **No local-only install source.** The requested environment check found neither Parquet engine nor pytest and no cached wheel. With the task's explicit no-network requirement, tools were not installed and `requirements.txt` was not changed.


## Stage 5/6 — 2026-10-22

- **Earlier sandbox connection block resolved.** The prior error was `psycopg.OperationalError: connection failed: connection to server at "127.0.0.1", port 5432 failed: Permission denied (0x0000271D/10013)`. After the user enabled session network access, the read-only version query succeeded; no credentials or connection string were recorded.
- **Separate-database restore initially blocked by role permissions; resolved 2026-10-22.** The initial error was `InsufficientPrivilege: permission denied to create database`. After temporary `CREATEDB` was granted, the first restore exposed missing PostGIS in a fresh `template0` database. The script now clones `twinguard`, removes the project schema in the temporary copy, restores the archive, compares seven table counts, then drops the temporary database. All counts matched; see `STAGE_5_6_REPORT.md`. Revoke temporary `CREATEDB` now that testing is complete.
- **Migration checksum correction.** A migration checksum mismatch occurred after editing `001_core_schema.sql` after its first application. Restored the already-applied migration contents and moved the new catalogue column/backfill into `003_catalog_licence_notes.sql`; checksum verification then passed.
- **GIS loader fixes.** Fixed the CLI import path (`ModuleNotFoundError: No module named 'db_common'`), avoided renaming a geometry column already named `geom` (`ValueError: Column named geom already exists`), allowed separately catalogued UNOSAT layers in their shared target (`Refusing to append to nonempty target table without a catalog record: flood_references`), and checked the inserted row-count delta for that shared table (`expected 645, got 2005`). The rerun loaded all eight sources and the next rerun skipped them by matching source hashes.
- **Test discovery and verification fixes.** Pytest first collected the utility as a test module and failed to import `db_common`; renamed it to `backup_restore.py`. The next run exposed a missing `source_sha256` selection in the verifier (`KeyError: 'source_sha256'`); corrected the query. Final result: 10 passed, 0 failed.
- **Raw audit parser fix.** The audit initially reported 86 files without comparable hashes because the IMERG log uses `File:` and `Size bytes:`. The parser now accepts those labels; rerun matched all 144 files, with zero unmatched hashes and zero mismatches.
- **Initial compile invocation correction.** PowerShell passed `pipelines\stage5\*.py` literally to `py_compile`, returning `[Errno 22] Invalid argument: 'pipelines\\stage5\\*.py'`. Re-ran compilation by enumerating each `.py` file; compilation and later test imports succeeded.

- **Restore test completed 2026-10-22.** The final run created the temporary database, restored the project schema, matched all seven source/restored table counts, and dropped the temporary database. No other database was created or modified.

## Stage 5 gap completion — 2026-10-23

- **Migration module invocation.** Initial module-style run failed with exact error `ModuleNotFoundError: No module named 'db_common'` because the migration runner imported its helper as a top-level module. Fixed `apply_migrations.py` to put the project root on `sys.path` and import `pipelines.stage5.db_common`, so direct-script and module invocation both resolve the same helper. No credentials were printed.
- **Repaired flood view typmod.** Migration 004 first failed with `cannot change data type of view column "geom" from geometry(Geometry,32644) to geometry(MultiPolygon,32644)`. The repaired geometry is now cast to generic `geometry(Geometry,32644)` in the replacement view. The transaction rolled back on the failed attempt; corrected migrations 004 and 005 then applied.
- **Road node staging type.** First complementary loader run failed with `column "component_id" is of type bigint but expression is of type text`. GeoPackage NULLs were inferred as text by staging; the loader now explicitly selects `NULL::bigint` for the absent source component id. No node rows were duplicated; the rerun loaded 508,854.
- **OpenCity KML Z coordinates.** Flood-label insert first failed with `Geometry has Z dimension but column does not`. The loader now uses `shapely.force_2d` on imported geometries while retaining original KML files unchanged. A later validation found 54 invalid KML polygon geometries; migration 008 preserves those originals and stores valid MakeValid polygon parts separately.
- **GFD JSON bind parsing.** SQLAlchemy interpreted the JSON number `65.43` as a bind parameter, raising `A value is required for bind parameter '65'`. The metadata is now passed as a bound JSON string and cast to `jsonb` in SQL.
- **Derived-label JSON parameter.** SQL execution raised `could not determine data type of parameter $3` for `jsonb_build_object` in the derived-label insert. The loader now supplies a bound JSON string with explicit `jsonb` cast. Seven derived assets are registered as unvalidated metadata without geometry.
- **IMERG partial-load correction.** The first loader attempt used the same first-eight-character filename key for every `3B-DAY.MS...` file and loaded only one record. The source-date index now uses the complete file list and deduplicates the two repeated report dates; the corrected import contains 86 daily records. Migration 006 removed only the incomplete first row/catalog record produced by this task. The daily values are read from the existing comparison report and were not recalculated from raw NetCDF in this step.
- **OpenCity exact date correction.** The initial metadata row assigned the flood peak day to observed points although the local source only identifies 2015. Migration 007 cleared that unsupported day; the observed-point `event_date` remains NULL.
- **Slow spatial sample.** The first broad `EXISTS` plan scanned too much of the building/flood layers and was canceled. The final reproducible sample uses a single repaired Nov 24 flood feature and verifies roads, buildings and cells through their GiST indexes. This is a representative index smoke test, not a workload benchmark.
- **Final loader reruns.** A full rerun after corrections skipped catalogued sources by matching hash and row count; counts stayed unchanged, including 86 IMERG rows. Catalog count checks and provenance orphan checks both returned zero.
