# Document control

## Scope and sources

Prepared on **16 Oct 2026** from the current repository and the user-supplied project brief. No network or login was used. Raw data were not read/processed for this handbook; existing reports, logs, manifests, Git metadata, directory names, source code docstrings and recorded JSON summaries were consulted. [repo: system clock, files named in Coverage Matrix; user]

Repository sources reviewed include `README.md`, all current files under `docs/`, the data manifest, all raw `DOWNLOAD_LOG.txt` files, Phase 3 and tool Python scripts, `requirements.txt`, `docker-compose.yml`, `.env.example`, `.gitignore`, folder listings and Git history. See [Coverage Matrix](COVERAGE_MATRIX.md). The absent `docs/LABEL_STRATEGY.md` was not available to read. [repo]

## Ten spot-checked facts

| Fact | Source |
|---|---|
| Old CMA area 1,187.460287 km² | `docs/COVERAGE_2015.md` |
| Common grid EPSG:32644 at 30 m | `docs/GRID_DECISION.md` |
| Grid dimensions 1,370 × 1,760 | `docs/GRID_DECISION.md` |
| CMA mask contains 1,319,380 cells | `docs/GRID_DECISION.md` |
| CMA elevation range −64.5088 to 168.7034 m | `docs/PHASE3_VALIDATION.json` (`elevation_m.tif`) and `docs/PHASE3_LOG.md` |
| Daily comparison has 3,287 matched dates and Pearson r 0.7634648440 | `data/features/weather/daily_source_comparison.json` |
| WorldCover class 50 mean fraction 0.3942778409 | `data/features/landcover/class_area_fraction_means_cma.json` |
| Road graph summary has 566,307 road segments, 1,071,656 arcs and 508,854 nodes | `data/features/osm/osm_graph_summary.json` |
| 13 Sentinel ZIPs passed integrity/name checks | `docs/SENTINEL_VERIFICATION.md` |
| Track B screen earliest target flag 20 Nov 2015, 11 days before 1 Dec | `data/features/reservoirs/illustrative_track_b_backtest.json` |

## Read-only raw integrity check

On 16 Oct 2026, `tools/audit_raw_logs.py` completed against the existing raw archive: **58 files, 17,775,232,566 bytes; all 58 matched a logged size and SHA-256; zero mismatches; zero files without a comparable hash record.** The script read raw bytes only to calculate hashes; it did not edit, move, extract or interpret the files. This is an integrity check against the project logs, not a validation of the source data's scientific accuracy. [repo: command output from `tools/audit_raw_logs.py`]

## Conflicts and reconciliations

| Conflict | Handling in this handbook |
|---|---|
| `README.md` says Phase 3 is planned/not started; later status and Phase 3 log say Part B is complete. | Treat dated `docs/PHASE3_LOG.md` and `docs/PROJECT_STATUS.md` as current. README is stale and was not edited except for the allowed handbook link. [repo: README, PHASE3_LOG, PROJECT_STATUS] |
| `docs/PHASE2_CLOSURE.md` says 55 raw data files, 10 Sentinel ZIPs and Phase 3 unstarted; `docs/PHASE3_LOG.md` says 58 data files, 13 ZIPs and Part B complete. | Phase 2 closure predates later acquisitions and Phase 3. Use the later dated Phase 3 audit for current status. [repo: files named] |
| Sentinel folder is actually `data/raw/satellite/sentinel1/`; manifest rows and some older notes use `senitnel1`. | Do not rename anything. Record the path mismatch for metadata/path reconciliation. [repo: directory listing, `docs/DATA_MANIFEST.csv`, `docs/PHASE3_LOG.md`] |
| WorldPop raw CMA NoData is reported as 23,812 pixel centres in Phase 2/data quality, while the derived 30 m WorldPop grid reports 194,961 CMA NoData cells. | These are different grids and should not be compared as equal cell counts. Keep both figures tied to their specific methods. The raw count source is `docs/DATA_QUALITY_REPORT.md`; derived count is `docs/PHASE3_LOG.md`. |
| UNOSAT polygon-intersection areas in `COVERAGE_2015.md` differ slightly from 30 m rasterized areas in label summary. | Present them separately with their methods; do not combine them. |
| OSM source inventory counts differ from extracted summary, including hospital 908 vs 848, school 706 vs 696 and shelter 172 vs 171. | Show as unresolved; likely extraction/tag/geometry scope differs, but cause has not been established. [repo: `docs/OSM_COUNTS.md`, `data/features/osm/osm_graph_summary.json`] |
| `LABEL_STRATEGY.md` is requested in the source checklist but absent in `docs/`. | Say unavailable. Use only the extant guidance from `docs/PHASE3_PLAN.md`; no attributed recommendation from the missing file. |
| Phase 2 closure says supplied NRSC Michaung PDFs missing; current manifest lists NDEM 7 Dec and 18 Dec PDFs collected, while supplied two-part NRSC PDF remains not downloaded. | Distinguish the NDEM equivalents from the supplied pair; do not describe them as identical. [repo: manifest, `docs/MANUAL_TODO.md`] |

## Open questions and placeholders

### Personal/project details to fill

- Project team member names: **[TO BE FILLED]**.
- Institution/department: **[TO BE FILLED]**.
- Guide/supervisor: **[TO BE FILLED]**.
- Submission/deadline dates: **[TO BE FILLED]**.
- Team roles: **[TO BE FILLED]**.
- Hypothesis success thresholds: **[TO BE FILLED]** after baselines.

### Technical questions

- Is the older CMA boundary final, or must the expanded jurisdiction be used?
- What exact rainfall units and NASA POWER metadata apply to the comparison?
- What is the correct historical reservoir capacity series and are releases available?
- Are Dec 2015 flood layers obtainable? If not, which documented fallback is chosen?
- What is the validated meaning of the Sep/Oct “PreFlood” classes?
- What caused OSM inventory/extract count differences? What are graph connectivity and facility snapping results?
- What does WorldPop NoData represent in the relevant CMA places, and how do totals compare on matched census boundaries?
- What exact Sentinel ASF terms permit processing and any redistribution?
- Which local PostgreSQL/PostGIS install is active, and what port is free?
- Are current listed literature citations correct after opening the supplied papers? Has the full literature search supported the gap statement?

### Explicitly unverified claims

- The believed 2011 CMA census total of about 8.6–8.7 million is **[unverified]** and requires census-source checking. [repo: `docs/DATA_QUALITY_REPORT.md`]
- The literature gap and possible local novelty around reservoir releases are **[unverified]** until a fuller review. [user]
- User-supplied event/impact framing is project context, not independently sourced historical analysis. **[unverified]** until referenced sources are read and cited. [user]
- No deadline, personal names, institution, guide or role assignment is present in repository evidence. **[unverified]**

## File/number tagging convention

Important project claims in this handbook end with `[repo: <path>]`, `[user]`, or `[unverified]`. A source path points to evidence available in the project; a user tag denotes planning-chat facts not independently validated in repository files. Data results are not upgraded into ground truth by being repeated here. [repo/user]

## Change log

| Date | Change |
|---|---|
| 16 Oct 2026 | First handbook draft assembled from current repository and user-supplied project context; export and quality checks recorded in the final report. |
