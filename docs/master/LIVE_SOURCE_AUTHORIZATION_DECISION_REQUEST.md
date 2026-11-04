# Rainfall and reservoir source authorization decision request

**Status: PENDING owner decision.** This repository-only package does not select or authorize a source, contact a source owner, or establish that any feed exists. B34 classifies the candidate set as `NO_CANDIDATE_VERIFIED_LIVE`. Do not treat silence, a public URL, or historical files as authorization. The machine-readable source-by-source records are in [`live_source_authorization_decision_request.json`](live_source_authorization_decision_request.json).

## Decisions requested

| Decision | Current status | Authorized decision needed | Evidence required |
|---|---|---|---|
| D2 rainfall source/access | PENDING | Project owner selects an exact product/source for bounded replay or an explicitly authorized live prototype, rejects candidates, or defers. Accountable source owner confirms access. | Product/version; source owner and permitted access path; written permission and applicable terms, retention and redistribution rights; authentication design and credential custodian; cadence, publication latency, revisions; units, accumulation interval, valid/observation time and timezone; coverage/resolution; quality and missing-data behavior; provenance/sample/schema and exact hash; owner-approved freshness/outage/retry policy. |
| D3 reservoir source/access | PENDING | Project owner identifies the authoritative record holder and chooses an exact feed or bounded replay input, rejects candidates, or defers. Source owner confirms measurement schema and access. | Feed/product/version and reservoir coverage; owner/custodian and written access; terms, retention and redistribution; authentication/custodian; cadence, latency, revisions; units/meaning for level, storage, inflow, outflow and gates where supplied; measurement versus reporting/valid time and timezone; provenance/sample/schema/hash; missingness and owner-approved freshness/outage/retry policy. |
| D8 prototype source mode | PENDING separately from D2/D3 | Project owner chooses fixture/replay-only, a bounded live prototype for named approved sources, or defers live mode. | Named source set; authorization and terms; rate limits; secret handling; freshness and failure boundary; rollback; explicit exclusions. A D8 choice alone does not authorize an unapproved source. |

An answer of **defer** is valid. If a source is not selected or evidence is unavailable, retain `PENDING`/`UNKNOWN`; no adapter or endpoint becomes ready from a decision request alone.

## Candidate-by-candidate evidence and decision records

Every candidate below remains unapproved for live use. Historical `REPLAY` means only that local historical files or archive evidence exist. `PROPOSED` means the inventory did not collect a sample. The JSON contains explicit decision, permission, access, authentication, sample/hash, freshness, and missingness fields for each candidate.

### gpm_imerg_daily_v07b — GPM IMERG daily V07B

- **Category / inventory status:** rainfall / `REPLAY`; live access verified: `false`; live authorization: `PENDING`.
- **Product/version:** GPM IMERG daily V07B.
- **Owner/custodian:** NASA Earthdata / GPM; source-owner contact or access entitlement UNKNOWN.
- **Documented local access:** 86 local daily NetCDF4 files acquired manually; current live/API access is not configured or verified.
- **Authorized access path:** PENDING — no prospective live access path or written source-owner authorization is evidenced.
- **Permission and terms:** TO CONFIRM; product-specific terms are not verified in the manifest Written permission: PENDING — source-owner and project-owner approval not recorded. Retention: UNKNOWN — require explicit terms for storage, retention, and deletion. Redistribution: UNKNOWN — require explicit terms for derived/publication/distribution use.
- **Authentication / credential custodian:** UNKNOWN — do not infer an authentication scheme. Custodian: UNKNOWN — project owner must identify approved custodian; never place secrets in these records. No credentials recorded.
- **Cadence / latency / revisions:** Daily product cadence; repository holdings are selected historical windows, not an update stream / UNKNOWN / UNKNOWN — owner/source documentation required.
- **Units and field meanings:** mm/day per manifest verification Use only meanings stated in cited inventory/source metadata; additional fields and units require source-owner documentation.
- **Timestamp meaning / timezone:** Daily product interval labeled UTC; exact operational arrival/availability semantics UNKNOWN.
- **Coverage / resolution:** CMA pixel-centre sample on 0.1 degree grid (~10 km); 2015-11-01..2015-12-15, 2021-11-01..2021-11-20, 2023-11-25..2023-12-15; 86 files; gaps outside selected windows.
- **Provenance / evidence paths:** Per-file SHA-256 in data/raw/weather/imerg/DOWNLOAD_LOG.txt; manifest records 86/86 files and inspected CMA window; comparative analysis exists, but no gauge validation References: docs/DATA_MANIFEST.csv, data/raw/weather/imerg/DOWNLOAD_LOG.txt, docs/RAIN_SOURCES_COMPARISON.md, docs/trackb/AUDIT_AND_BACKTEST.md.
- **Sample/schema and hashes:** Inventory references only; file-level hashes are recorded for local historical holdings, but no authorized live sample/schema is supplied. Hashes recorded in inventory: UNKNOWN — no candidate sample hash recorded.
- **Missing/NoData behavior:** Missing days remain gaps/null; do not fill with zero.
- **Freshness, outage, and retry policy:** PENDING owner decision; do not infer thresholds from nominal cadence. See the per-field pending entries in the JSON record.
- **Decision:** PENDING; decision maker/date/evidence references are not recorded. Approve only with cited source-owner and project-owner evidence, reject with rationale, or defer.

### open_meteo_era5_archive — Open-Meteo ERA5 archive output

- **Category / inventory status:** rainfall / `REPLAY`; live access verified: `false`; live authorization: `PENDING`.
- **Product/version:** UNKNOWN — exact operational product/version not selected or evidenced.
- **Owner/custodian:** Open-Meteo service; upstream ERA5 produced by ECMWF; source-owner agreement UNKNOWN.
- **Documented local access:** Historical archive API output saved locally for nine points; no live adapter configured.
- **Authorized access path:** PENDING — no prospective live access path or written source-owner authorization is evidenced.
- **Permission and terms:** Manifest states CC BY 4.0 data with non-commercial/rate-limited free API terms; exact project-use/redistribution review still required Written permission: PENDING — source-owner and project-owner approval not recorded. Retention: UNKNOWN — require explicit terms for storage, retention, and deletion. Redistribution: UNKNOWN — require explicit terms for derived/publication/distribution use.
- **Authentication / credential custodian:** UNKNOWN — do not infer an authentication scheme. Custodian: UNKNOWN — project owner must identify approved custodian; never place secrets in these records. No credentials recorded.
- **Cadence / latency / revisions:** Historical daily comparison and selected hourly event sequences; live refresh cadence UNKNOWN / UNKNOWN / UNKNOWN — owner/source documentation required.
- **Units and field meanings:** Rainfall comparisons report mm/day; variable-specific request metadata is evidence path dependent; verify before ingestion Use only meanings stated in cited inventory/source metadata; additional fields and units require source-owner documentation.
- **Timestamp meaning / timezone:** Request evidence uses Asia/Kolkata for event hourly selections; per-output/source timestamp rules must be retained; live timestamp behavior UNKNOWN.
- **Coverage / resolution:** Nine CMA sample points; ~25 km; daily 2015-01-01..2023-12-31 comparison (3,287 dates); hourly event windows 2015-11-01..2015-12-15, 2021-11-01..2021-11-20, 2023-11-25..2023-12-15; not station coverage.
- **Provenance / evidence paths:** Manifest retrieval date 2026-10-08 and size recorded; local download logs and comparison tables exist; ERA5/NASA POWER comparison is product agreement, not gauge validation References: docs/DATA_MANIFEST.csv, data/raw/weather/DOWNLOAD_LOG.txt, data/raw/weather/, docs/RAIN_SOURCES_COMPARISON.md, docs/PHASE3_LOG.md.
- **Sample/schema and hashes:** Inventory references only; file-level hashes are recorded for local historical holdings, but no authorized live sample/schema is supplied. Hashes recorded in inventory: UNKNOWN — no candidate sample hash recorded.
- **Missing/NoData behavior:** Keep missing periods null/gaps; no silent fill.
- **Freshness, outage, and retry policy:** PENDING owner decision; do not infer thresholds from nominal cadence. See the per-field pending entries in the JSON record.
- **Decision:** PENDING; decision maker/date/evidence references are not recorded. Approve only with cited source-owner and project-owner evidence, reject with rationale, or defer.

### nasa_power_daily — NASA POWER daily point product

- **Category / inventory status:** rainfall / `REPLAY`; live access verified: `false`; live authorization: `PENDING`.
- **Product/version:** UNKNOWN — exact operational product/version not selected or evidenced.
- **Owner/custodian:** NASA POWER; operational contact/access agreement UNKNOWN.
- **Documented local access:** Nine historical daily JSON point responses saved locally; no live adapter configured.
- **Authorized access path:** PENDING — no prospective live access path or written source-owner authorization is evidenced.
- **Permission and terms:** POWER-specific license NOT FOUND in manifest; citation requested; terms require review Written permission: PENDING — source-owner and project-owner approval not recorded. Retention: UNKNOWN — require explicit terms for storage, retention, and deletion. Redistribution: UNKNOWN — require explicit terms for derived/publication/distribution use.
- **Authentication / credential custodian:** UNKNOWN — do not infer an authentication scheme. Custodian: UNKNOWN — project owner must identify approved custodian; never place secrets in these records. No credentials recorded.
- **Cadence / latency / revisions:** Daily historical series; live update cadence UNKNOWN / UNKNOWN / UNKNOWN — owner/source documentation required.
- **Units and field meanings:** PRECTOTCORR metadata in local responses says mm/day; verify variable metadata for every request Use only meanings stated in cited inventory/source metadata; additional fields and units require source-owner documentation.
- **Timestamp meaning / timezone:** Daily data identified as UTC in repository comparison notes; live publication/arrival timestamp semantics UNKNOWN.
- **Coverage / resolution:** Nine point samples over CMA; native grid resolution recorded as native grid and not quantified in manifest; daily 2015-01-01..2023-12-31.
- **Provenance / evidence paths:** Manifest retrieval 2026-10-08 and total size recorded; local response metadata and comparison with ERA5 exist; no gauge validation References: docs/DATA_MANIFEST.csv, data/raw/weather/, docs/MANUAL_TODO.md, docs/PHASE3_LOG.md.
- **Sample/schema and hashes:** Inventory references only; file-level hashes are recorded for local historical holdings, but no authorized live sample/schema is supplied. Hashes recorded in inventory: UNKNOWN — no candidate sample hash recorded.
- **Missing/NoData behavior:** Missing or unavailable parameter values remain null; do not coerce to zero.
- **Freshness, outage, and retry policy:** PENDING owner decision; do not infer thresholds from nominal cadence. See the per-field pending entries in the JSON record.
- **Decision:** PENDING; decision maker/date/evidence references are not recorded. Approve only with cited source-owner and project-owner evidence, reject with rationale, or defer.

### era5_cds_candidate — ERA5 via Copernicus Climate Data Store

- **Category / inventory status:** rainfall / `PROPOSED`; live access verified: `false`; live authorization: `PENDING`.
- **Product/version:** UNKNOWN — exact operational product/version not selected or evidenced.
- **Owner/custodian:** Copernicus Climate Data Store / ECMWF; project registration/access UNKNOWN.
- **Documented local access:** Proposed manual account and request; manifest marks not downloaded.
- **Authorized access path:** PENDING — no prospective live access path or written source-owner authorization is evidenced.
- **Permission and terms:** Product-specific terms NOT FOUND/NOT VERIFIED in manifest Written permission: PENDING — source-owner and project-owner approval not recorded. Retention: UNKNOWN — require explicit terms for storage, retention, and deletion. Redistribution: UNKNOWN — require explicit terms for derived/publication/distribution use.
- **Authentication / credential custodian:** UNKNOWN — do not infer an authentication scheme. Custodian: UNKNOWN — project owner must identify approved custodian; never place secrets in these records. No credentials recorded.
- **Cadence / latency / revisions:** Hourly product candidate; operational availability cadence UNKNOWN / UNKNOWN / UNKNOWN — owner/source documentation required.
- **Units and field meanings:** UNKNOWN for a selected request; product/variable dependent Use only meanings stated in cited inventory/source metadata; additional fields and units require source-owner documentation.
- **Timestamp meaning / timezone:** Hourly UTC convention not verified for a selected local artifact; candidate only.
- **Coverage / resolution:** Manifest candidate ~25 km, hourly; no local coverage or file collected.
- **Provenance / evidence paths:** No local file, hash, or validation result References: docs/DATA_MANIFEST.csv, docs/MANUAL_TODO.md, docs/batches/BATCH_2.md.
- **Sample/schema and hashes:** NONE EVIDENCED — no candidate source sample/schema collected. Hashes recorded in inventory: UNKNOWN — no candidate sample hash recorded.
- **Missing/NoData behavior:** UNKNOWN; adapter must preserve missing values as null/gaps.
- **Freshness, outage, and retry policy:** PENDING owner decision; do not infer thresholds from nominal cadence. See the per-field pending entries in the JSON record.
- **Decision:** PENDING; decision maker/date/evidence references are not recorded. Approve only with cited source-owner and project-owner evidence, reject with rationale, or defer.

### imd_rainfall_candidate — India Meteorological Department rainfall

- **Category / inventory status:** rainfall / `PROPOSED`; live access verified: `false`; live authorization: `PENDING`.
- **Product/version:** UNKNOWN — exact operational product/version not selected or evidenced.
- **Owner/custodian:** India Meteorological Department; responsible office/contact UNKNOWN.
- **Documented local access:** Station or gridded request proposed at official service; no local file collected and no request made.
- **Authorized access path:** PENDING — no prospective live access path or written source-owner authorization is evidenced.
- **Permission and terms:** NOT FOUND; fees and product-specific terms unverified Written permission: PENDING — source-owner and project-owner approval not recorded. Retention: UNKNOWN — require explicit terms for storage, retention, and deletion. Redistribution: UNKNOWN — require explicit terms for derived/publication/distribution use.
- **Authentication / credential custodian:** UNKNOWN — do not infer an authentication scheme. Custodian: UNKNOWN — project owner must identify approved custodian; never place secrets in these records. No credentials recorded.
- **Cadence / latency / revisions:** Hourly/daily candidate; exact product cadence UNKNOWN / UNKNOWN / UNKNOWN — owner/source documentation required.
- **Units and field meanings:** UNKNOWN until selected product metadata is obtained Use only meanings stated in cited inventory/source metadata; additional fields and units require source-owner documentation.
- **Timestamp meaning / timezone:** UNKNOWN until selected product documentation is obtained.
- **Coverage / resolution:** Manifest says station/grid, product-dependent; no CMA coverage artifact.
- **Provenance / evidence paths:** No local file, hash, or validation result References: docs/DATA_MANIFEST.csv, docs/MANUAL_TODO.md.
- **Sample/schema and hashes:** NONE EVIDENCED — no candidate source sample/schema collected. Hashes recorded in inventory: UNKNOWN — no candidate sample hash recorded.
- **Missing/NoData behavior:** UNKNOWN; preserve missing station/grid records as missing.
- **Freshness, outage, and retry policy:** PENDING owner decision; do not infer thresholds from nominal cadence. See the per-field pending entries in the JSON record.
- **Decision:** PENDING; decision maker/date/evidence references are not recorded. Approve only with cited source-owner and project-owner evidence, reject with rationale, or defer.

### kaggle_chennai_reservoir_archive — Kaggle Chennai Water Management archive

- **Category / inventory status:** reservoir / `REPLAY`; live access verified: `false`; live authorization: `PENDING`.
- **Product/version:** UNKNOWN — exact operational product/version not selected or evidenced.
- **Owner/custodian:** Dataset publisher sudalairajkumar; original measurement operator/record custodian UNKNOWN.
- **Documented local access:** Local immutable archive; no live source adapter or operator access.
- **Authorized access path:** PENDING — no prospective live access path or written source-owner authorization is evidenced.
- **Permission and terms:** CC0 1.0 shown on Kaggle licence page per manifest; original-source rights/attribution details UNKNOWN Written permission: PENDING — source-owner and project-owner approval not recorded. Retention: UNKNOWN — require explicit terms for storage, retention, and deletion. Redistribution: UNKNOWN — require explicit terms for derived/publication/distribution use.
- **Authentication / credential custodian:** UNKNOWN — do not infer an authentication scheme. Custodian: UNKNOWN — project owner must identify approved custodian; never place secrets in these records. No credentials recorded.
- **Cadence / latency / revisions:** Daily historical rows, 2004-01-01..2020-12-03; no refresh cadence / UNKNOWN; historical publication delay not documented / UNKNOWN — owner/source documentation required.
- **Units and field meanings:** Storage described as mcft; rainfall unit undocumented and remains unverified/inferred; release/inflow not supplied as a continuous series Use only meanings stated in cited inventory/source metadata; additional fields and units require source-owner documentation.
- **Timestamp meaning / timezone:** Date-only source_date. Historical observation instant, whether the date means measurement/reporting/aggregation day, and timezone remain UNKNOWN under C3. Preserve observed_at=null, observation_timezone=unknown, and distinct received_at; never synthesize midnight or an interval.
- **Coverage / resolution:** Four reservoirs (Poondi, Cholavaram, Red Hills/Puzhal, Chembarambakkam); daily archive through 2020-12-03; reservoir point values, not spatial grid; no subdaily operations.
- **Provenance / evidence paths:** Archive SHA-256 7645febde7ccc21871200487139d1c8a84ea90a6dd2eccc93b7d1f06faf69197; ZIP CRC passed; two CSV members, each 6,182 rows, complete daily dates per manifest; B28 selected-row/member hashes and unique line evidence; B19/C3 representation tests References: docs/DATA_MANIFEST.csv, data/raw/reservoirs/kaggle_chennai_water_management/archive.zip, data/raw/reservoirs/DOWNLOAD_LOG.txt, docs/trackb/AUDIT_AND_BACKTEST.md, docs/trackb/MESSAGES.md, docs/trackb/B13_REPLAY_FIXTURE_EVIDENCE.md, docs/master/contracts/c3_messages_v0.md.
- **Sample/schema and hashes:** Historical archive only; archive SHA-256 7645febde7ccc21871200487139d1c8a84ea90a6dd2eccc93b7d1f06faf69197; B28/B27 evidence identifies a row fixture, but this does not authorize live access or prove a live schema. Hashes recorded in inventory: 7645febde7ccc21871200487139d1c8a84ea90a6dd2eccc93b7d1f06faf69197.
- **Missing/NoData behavior:** Archive completeness reported for its date range; outside range unavailable; do not impute release/storage or infer observation time.
- **Freshness, outage, and retry policy:** PENDING owner decision; do not infer thresholds from nominal cadence. See the per-field pending entries in the JSON record.
- **Decision:** PENDING; decision maker/date/evidence references are not recorded. Approve only with cited source-owner and project-owner evidence, reject with rationale, or defer.

### opencity_monthly_reservoir_storage — OpenCity CMWSSB lake storage dataset

- **Category / inventory status:** reservoir / `REPLAY`; live access verified: `false`; live authorization: `PENDING`.
- **Product/version:** UNKNOWN — exact operational product/version not selected or evidenced.
- **Owner/custodian:** CMWSSB attributed by catalogue via OpenCity; exact data custodian/contact UNKNOWN.
- **Documented local access:** Local downloaded CSV snapshots through OpenCity; no live adapter configured.
- **Authorized access path:** PENDING — no prospective live access path or written source-owner authorization is evidenced.
- **Permission and terms:** Other (Public Domain) as listed by OpenCity in manifest; underlying source terms not independently evidenced Written permission: PENDING — source-owner and project-owner approval not recorded. Retention: UNKNOWN — require explicit terms for storage, retention, and deletion. Redistribution: UNKNOWN — require explicit terms for derived/publication/distribution use.
- **Authentication / credential custodian:** UNKNOWN — do not infer an authentication scheme. Custodian: UNKNOWN — project owner must identify approved custodian; never place secrets in these records. No credentials recorded.
- **Cadence / latency / revisions:** Monthly archive values, generally first-of-month labels; live refresh cadence UNKNOWN / UNKNOWN / UNKNOWN — owner/source documentation required.
- **Units and field meanings:** mcft per dataset description for storage Use only meanings stated in cited inventory/source metadata; additional fields and units require source-owner documentation.
- **Timestamp meaning / timezone:** Monthly calendar labels; measurement instant/timezone and month aggregation semantics UNKNOWN.
- **Coverage / resolution:** Reservoir point series for Poondi, Cholavaram, Chembarambakkam, Veeranam, Red Hills/Puzhal (2003-2021) and Kannankottai (2020-2021); Kannankottai has 11 blank month cells; not spatial coverage.
- **Provenance / evidence paths:** Per-file SHA-256 and row/value checks recorded in docs/DATA_MANIFEST.csv; monthly values cannot resolve event-day releases References: docs/DATA_MANIFEST.csv, data/raw/reservoirs/opencity_lake_levels/, docs/trackb/AUDIT_AND_BACKTEST.md.
- **Sample/schema and hashes:** Inventory references only; file-level hashes are recorded for local historical holdings, but no authorized live sample/schema is supplied. Hashes recorded in inventory: UNKNOWN — no candidate sample hash recorded.
- **Missing/NoData behavior:** Blank cells remain missing; do not fill or treat monthly labels as daily observations.
- **Freshness, outage, and retry policy:** PENDING owner decision; do not infer thresholds from nominal cadence. See the per-field pending entries in the JSON record.
- **Decision:** PENDING; decision maker/date/evidence references are not recorded. Approve only with cited source-owner and project-owner evidence, reject with rationale, or defer.

### tn_wrd_reservoir_operations_candidate — TN WRD / reservoir operator level, inflow, release and gate series

- **Category / inventory status:** reservoir / `PROPOSED`; live access verified: `false`; live authorization: `PENDING`.
- **Product/version:** UNKNOWN — exact operational product/version not selected or evidenced.
- **Owner/custodian:** TN WRD or responsible reservoir division/operator; exact record holder and PIO UNKNOWN; CMWSSB operation is mentioned for some reservoirs but authority for requested series is unverified.
- **Documented local access:** Historical series marked manual-needed; Agrisnet page described as login/OTP; no authentication, request, or data retrieval performed.
- **Authorized access path:** PENDING — no prospective live access path or written source-owner authorization is evidenced.
- **Permission and terms:** UNKNOWN; no series collected and no terms/access authorization recorded Written permission: PENDING — source-owner and project-owner approval not recorded. Retention: UNKNOWN — require explicit terms for storage, retention, and deletion. Redistribution: UNKNOWN — require explicit terms for derived/publication/distribution use.
- **Authentication / credential custodian:** UNKNOWN — do not infer an authentication scheme. Custodian: UNKNOWN — project owner must identify approved custodian; never place secrets in these records. No credentials recorded.
- **Cadence / latency / revisions:** UNKNOWN; hourly/daily is a desired candidate, not verified availability / UNKNOWN / UNKNOWN — owner/source documentation required.
- **Units and field meanings:** UNKNOWN for source series; desired variables include level/storage/inflow/release/gates Use only meanings stated in cited inventory/source metadata; additional fields and units require source-owner documentation.
- **Timestamp meaning / timezone:** UNKNOWN; authoritative measurement-time and timezone documentation absent.
- **Coverage / resolution:** Reservoirs/basin coverage, spatial references, periods, and resolution UNKNOWN; requested Chennai-basin event windows are not collected.
- **Provenance / evidence paths:** No time-series file/hash or source-owner evidence; project manual todo says no request was sent References: docs/DATA_MANIFEST.csv, docs/MANUAL_TODO.md, docs/master/FINAL_YEAR_ARCHITECTURE_REBASELINE.md, docs/trackb/REALTIME_DESIGN.md.
- **Sample/schema and hashes:** NONE EVIDENCED — no candidate source sample/schema collected. Hashes recorded in inventory: UNKNOWN — no candidate sample hash recorded.
- **Missing/NoData behavior:** UNKNOWN; must preserve gaps and distinguish unavailable from zero if acquired.
- **Freshness, outage, and retry policy:** PENDING owner decision; do not infer thresholds from nominal cadence. See the per-field pending entries in the JSON record.
- **Decision:** PENDING; decision maker/date/evidence references are not recorded. Approve only with cited source-owner and project-owner evidence, reject with rationale, or defer.

### cwc_public_reservoir_monitoring_candidate — CWC public reservoir monitoring/bulletin sources

- **Category / inventory status:** reservoir / `PROPOSED`; live access verified: `false`; live authorization: `PENDING`.
- **Product/version:** UNKNOWN — exact operational product/version not selected or evidenced.
- **Owner/custodian:** Central Water Commission; dataset-specific source owner/access terms UNKNOWN.
- **Documented local access:** Repository notes public dashboard/bulletin pages as candidates; no Chennai-basin historical file verified and no live adapter exists.
- **Authorized access path:** PENDING — no prospective live access path or written source-owner authorization is evidenced.
- **Permission and terms:** UNKNOWN for a usable time-series product Written permission: PENDING — source-owner and project-owner approval not recorded. Retention: UNKNOWN — require explicit terms for storage, retention, and deletion. Redistribution: UNKNOWN — require explicit terms for derived/publication/distribution use.
- **Authentication / credential custodian:** UNKNOWN — do not infer an authentication scheme. Custodian: UNKNOWN — project owner must identify approved custodian; never place secrets in these records. No credentials recorded.
- **Cadence / latency / revisions:** UNKNOWN for Chennai reservoirs; general current monitoring is mentioned, not an evidenced feed cadence / UNKNOWN / UNKNOWN — owner/source documentation required.
- **Units and field meanings:** UNKNOWN for a prospective feed; confirm per variable Use only meanings stated in cited inventory/source metadata; additional fields and units require source-owner documentation.
- **Timestamp meaning / timezone:** UNKNOWN for a prospective feed.
- **Coverage / resolution:** Manual todo notes reviewed CWC dataset resources did not provide the requested Chennai-basin historical time-series files; current monitored-reservoir coverage not established for these assets.
- **Provenance / evidence paths:** No applicable live/time-series artifact or hash References: docs/MANUAL_TODO.md, docs/DATA_MANIFEST.csv.
- **Sample/schema and hashes:** NONE EVIDENCED — no candidate source sample/schema collected. Hashes recorded in inventory: UNKNOWN — no candidate sample hash recorded.
- **Missing/NoData behavior:** UNKNOWN.
- **Freshness, outage, and retry policy:** PENDING owner decision; do not infer thresholds from nominal cadence. See the per-field pending entries in the JSON record.
- **Decision:** PENDING; decision maker/date/evidence references are not recorded. Approve only with cited source-owner and project-owner evidence, reject with rationale, or defer.

## Required owner response format

For each rainfall/reservoir candidate: `decision = approve | reject | defer`; exact source/product/version; project decision maker/date; accountable source owner and evidence reference; access/permission and terms; data rights; authentication method and custodian (never credentials); schema and units; valid/observation timestamp meaning and timezone; coverage/resolution; cadence, publication latency, revision/backfill; missing/QC behavior; freshness/current/stale/unavailable and outage/retry thresholds; sample/schema identity and SHA-256 when lawfully available; and limitations. List follow-up task IDs only after the scope is concrete.

For D8, separately record replay-only versus precisely bounded live prototype, named approved feeds, rate limits, secret custody, rollback, and exclusions. Replay approval is not live approval.

## C3, B35, and B36 constraints

- Historical reservoir `source_date` stays date-only. Historical observation instant and timezone stay unknown/null; do not synthesize midnight or infer a timezone. Keep `received_at` separate. Genuine timestamped sources preserve the supplied offset and instant. Historical measurement-time meaning remains unknown.
- B35 is an in-memory fixture-only boundary: it does not establish a source connector, production readiness, freshness SLA, or live ingestion.
- B36 keeps the centralized local demo fixture as the mounted provider. LIVE/REPLAY UI examples are local examples; unconnected live sources remain unavailable. No network or service call is authorized by this request.
- Source-dependent adapter, persistence, routing, or UI tasks must be registered separately after source-owner evidence, project approval, a lawful sample/schema, and freshness semantics exist. Any required contract or gate change follows change control; no frozen contract or gate is modified here.

## Evidence references and limits

- `docs/trackb/LIVE_SOURCE_READINESS_INVENTORY.md` and `docs/trackb/live_source_readiness_inventory.json` (B34): repository-only candidate inventory; no candidate verified live.
- `docs/master/LIVE_DATA_INTEGRATION_MAP.md` (I23): current source-to-UI evidence map and unresolved D2/D3/D8.
- `docs/trackb/INGESTION_READINESS_DESIGN.md` (B35) and `docs/ui/LIVE_DATA_READINESS_UI.md` (B36): fixture-only boundaries.
- `docs/master/FINAL_YEAR_OWNER_DECISIONS.md`, `docs/master/contracts/c3_messages_v0.md`, `docs/master/C3_DATE_ONLY_DECISION.json`.

No external feeds, credentials, source owners, databases, services, or Docker state were accessed for this decision package. G0/G5/G6, frozen contracts, and Lane A outputs remain outside scope.
