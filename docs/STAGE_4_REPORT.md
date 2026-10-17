# Stage 4 report — Phase 4 completion check

Date: 2026-10-17. Scope: Stage 4 only. No Phase 5/database work, model training, network access, or raw-data modification was performed. New data outputs are DERIVED and ignored by Git.

| Task | Result | File | Needs my decision? |
|---|---|---|---|
| 4.0 State and raw audit | **Complete.** All 144 raw data files (20,338,302,958 bytes) matched logged sizes and SHA-256; no mismatch and no unlogged data file. IMERG detail and the routing origin addendum were already present and checked. | `pipelines/phase4/state_check.py`; `docs/PHASE4_LOG.md` | No |
| 4.1 Time alignment | **Pending output.** Script and conventions are ready. No Parquet files were produced because `pyarrow`/`fastparquet` are absent and network access is prohibited. No daily values were expanded to hourly. | `pipelines/phase4/time_alignment.py`; `docs/TIME_ALIGNMENT.md` | Yes: provide an approved offline Parquet wheel if Parquet outputs are required |
| 4.2 Spatial alignment | **Complete with filename deviation.** Corrected inventory reports 34 raster records, 36 vector layers, 28 derived rasters aligned, zero analysis misalignments and zero metadata errors. Population sums differ by 0.01761%, within 0.1%. Existing first-pass `layer_registry.json` was preserved; use `layer_registry_complete.json`. | `data/processed/alignment/layer_registry_complete.json`; `docs/SPATIAL_ALIGNMENT.md` | Yes: decide later whether to keep or separately archive the preliminary registry |
| 4.3 Missingness and outliers | **Complete.** QC sidecars contain 498,954 row-variable flags across 29 variables. Corrected v2 flags use source wind units (km/h) and nonnegative checks for daily rain. Nothing was filled, deleted or clipped. | `data/features/events/qc_flags_v2.csv`; `data/features/events/qc_summary_v2.json`; `docs/QC_POLICY.md` | No |
| 4.4 Static feature table | **Pending output.** Script/schema cover supported fields. Coast distance is not computed because there is no coastline source in the selected repository inventory. Parquet table is blocked by the missing engine. | `pipelines/phase4/static_feature_stack.py`; `docs/FEATURE_DICTIONARY.md` | Yes: approve an offline Parquet wheel; provide/identify a coastline source if coast distance is required |
| 4.5 Validation strategy | **Complete.** Exactly 3,000 m blocks (100 × 100 30 m cells); 164 blocks intersect the CMA. The split plan is not a model run. | `data/processed/alignment/spatial_blocks.tif`; `docs/SPLIT_STRATEGY.md` | No |
| 4.6 Tests | `pytest` could not start because it is not installed. Built-in unittest fallback ran six checks: five passed and the static Parquet row-count test was skipped because the output is pending. | `tests/phase4/test_phase4_alignment.py`; `docs/ISSUES.md` | Yes: approved offline pytest wheel to satisfy the requested runner |
| 4.7 Lineage | **Complete.** File-level lineage includes all 61 current files in `data/processed` and `data/features` with inputs, script, filesystem timestamp, size and SHA-256. | `tools/build_lineage.py`; `docs/DATA_LINEAGE.md` | No |
| 4.8 Assumptions | **Complete as a register of documented choices.** Assumptions and source limitations are listed; review the entries before using routes or labels for decisions. | `docs/ASSUMPTIONS.md` | Review recommended |
| 4.9 Project records and commit | **Complete after commit.** Project status, issue log, manual tasks, manifest and Phase 4 log updated. The commit contains only scripts, tests and docs; no data files. | `docs/PROJECT_STATUS.md`; `docs/ISSUES.md`; `docs/MANUAL_TODO.md`; `docs/DATA_MANIFEST.csv`; `docs/PHASE4_LOG.md` | No |

## Main risks

1. Two requested Parquet deliverables remain pending until a Parquet engine and pytest can be made available through an approved offline install source.
2. The corrected routing graph's largest strongly connected component is 402,683 of 508,854 nodes (79.14%), markedly below the older full-graph figure (99.25%). This reflects the filtered vehicle graph and means some locations are disconnected for routing.
3. Flood labels remain uneven and incomplete: the 2015 official vectors do not cover the December peak, while 2021 and 2023 references are PDFs requiring digitising. No flood-label processing or Stage 5 work was started here.

Full exact errors and the preserved preliminary registry note are in `docs/ISSUES.md`. **Stopped at Stage 4.**

## Completion update — 2026-10-17

This update supersedes the earlier pending statuses for 4.1, 4.4, 4.6 and 4.7. The user installed the packages; verified `.venv` versions are `pyarrow==26.0.0`, `pytest==9.1.1`, `colorama==0.4.6`, `iniconfig==2.3.1`, `pluggy==1.7.0`, and `Pygments==2.21.0`. These pins were appended to `requirements.txt`; no other dependency line was changed and no package installation or network access was performed by Codex.

| Item | Result | File |
|---|---|---|
| Event alignment | Created 2015 (1,080 hourly + 180 date-only reservoir rows), 2021 (480 hourly), and 2023 (504 hourly) Parquet tables. ERA5 hourly and daily POWER/IMERG data have source presence/missing flags; daily values remain at UTC bucket boundaries; reservoir time was not invented. | `data/features/events/aligned_2015.parquet`, `aligned_2021.parquet`, `aligned_2023.parquet`; `docs/TIME_ALIGNMENT.md` |
| Static stack | Created 1,319,380 rows × 18 columns, matching the CMA mask. 194,961 population NoData cells remain null with `population_is_nodata=true`; zero values remain zero. Coast distance is unavailable and flagged false/null because no coastline layer exists. | `data/features/static/cell_table.parquet`; `docs/FEATURE_DICTIONARY.md` |
| Tests | Full pytest run: **6 passed, 0 failed, 0 skipped**. | `tests/phase4/`; `docs/ISSUES.md` |
| Lineage | Reran after making the lineage builder refreshable; new Parquet files are indexed with size and SHA-256. | `tools/build_lineage.py`; `docs/DATA_LINEAGE.md` |
| Raw audit | 144 files, 20,338,302,958 bytes; 144 size/hash matches, zero mismatches. | `pipelines/phase4/state_check.py` |

No aligned/static processing script bug surfaced. The lineage script's previous “refuse existing report” guard was fixed so its generated report can be refreshed. Remaining data limits: reservoir inputs end in 2020; Cooum did not match the exact target name in the saved waterway layer; no coastline source is present. No Stage 5/database work or model training was started.
