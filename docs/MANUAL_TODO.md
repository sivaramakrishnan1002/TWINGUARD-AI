# Manual TODO — remaining manual verification

Complete the items below before treating the study data as final. Preserve raw files. For every later acquisition, record the exact URL, date/time, byte size, SHA-256, licence, and verification in its log and manifest. Phase 3 is complete; Phase 4 Part 1 preprocessing is recorded in `PHASE4_LOG.md`.

## 2015 December flood layers (highest priority)
1. Open the official Bhuvan disaster flood viewer: https://bhuvan-app1.nrsc.gov.in/disaster/usrtasks/flood/flood.php?uname=empty
2. Expand **Historical Floods → 2015 → Tamil Nadu**. Inspect 03/12/2015-06Hr, 04/12/2015, 05/12/2015, 05-07/12/2015 and 08/12/2015-18Hr, plus **chennai floods (Experimental Product) → Cumulative Inundation (RISAT-1: 3,4,6 Dec15)**. The page lists “Click here to zoom”; current inspection did not find direct public downloadable data-file links.
3. For each item, use the magnifier/zoom link, record the title, date, map scale, source imagery, and whether the page offers an actual export/download. Do not treat a screenshot or simulation as a vector flood polygon. Save an original product only if the viewer itself exposes a verified public download URL, in `data/raw/historical_floods/2015/<date>/`.
4. Email `flood@nrsc.gov.in` yourself to request the December 2015 Chennai CMA observed inundation layers for 03–08 Dec (including the cumulative RISAT-1 product), preferably original GIS/vector or raster files, projection/metadata, source imagery/acquisition dates, and terms of use. Include that the 12 and 24 Nov UNOSAT layers do not represent the 1–2 Dec peak. Do not send from Codex.

## 2015 coverage calculations
Follow the QGIS procedure in `docs/COVERAGE_2015.md` for the November flood polygons and their analysis-footprint layers. Coverage was computed read-only with the project-local `.venv`; numeric results and method are recorded in `docs/COVERAGE_2015.md`.

## Michaung 2023 NRSC
1. Open the official Bhuvan flood viewer linked above and go to Historical Floods → 2023 → Tamil Nadu.
2. The supplied NRSC URLs for `TN_7_12_2023_Michaung_Cyclone1of2.pdf` and `...2of2.pdf` were not obtainable (prior 404s; latest restricted-shell HTTP 000). Official NDEM equivalents were retrieved and verified: 7 Dec 2023 map is at `data/raw/historical_floods/2023/tncyclone50dsc07122023_0600hrs_map.pdf` and covers the northern districts including the target districts. The optional 18 Dec map at `data/raw/historical_floods/2023/tnflood50dsc12182023_1800hrs_vap1.pdf` covers Tuticorin only.
3. Request a vector/shapefile from `flood@nrsc.gov.in` yourself if GIS data are needed; specify event/date, CMA boundary, source imagery and terms.
4. NRSC marks the 7 Dec product preliminary; inundation may include rainwater/low-lying/paddy standing water and no ground verification was done. Keep the southern 18 Dec sheet separate from northern CMA labels.

## WorldPop
The user supplied `data/raw/population/ind_pop_2021_CN_100m_R2025A_v1.tif`. It opens as a one-band float32 GeoTIFF in EPSG:4326; its 0.00083333333-degree pixels cover the requested CMA bbox and existing boundary. SHA-256, byte size, licence, and verification are recorded in `data/raw/population/DOWNLOAD_LOG.txt` and `docs/DATA_MANIFEST.csv`. WorldPop labels the product page as an alpha version (R2025A). The read-only valid-cell-center sum within the existing CMA boundary is about 6,204,904; 23,812 nodata centers were excluded. This is a model estimate, not a census count, and may be understated due to nodata. No further download is needed.

- Manually compare WorldPop totals with census figures for Chennai district and the CMA. Verify the source years, administrative boundary definitions/vintages, and whether the approximate 2011 CMA total of 8.6–8.7 million is supported by census sources; document comparability limits before interpreting the difference.

## OpenStreetMap

The Geofabrik Southern Zone PBF is downloaded and inventoried. See `docs/OSM_COUNTS.md` and `docs/OSM_WATERWAYS.md` for counts, exact requested-name results, clipped lengths, and connectivity limits.

## Sentinel products
Thirteen ASF Sentinel-1 GRD-HD ZIPs were manually acquired and verified read-only on 2026-10-14. Keep their original names in `data/raw/satellite/senitnel1/2015`, `2021`, and `2023`; do not rename the existing misspelled folder or extract the archives. The ASF-specific licence and terms still need confirmation. Verification results and hashes are in `docs/SENTINEL_VERIFICATION.md` and the folder's `DOWNLOAD_LOG.txt`.

The saved catalogue contains a post-peak 16 Nov 2021 option (two slices) but no post-peak 2015 or 2023 option. Decide whether to acquire that optional pair after checking its timing and storage cost. No Sentinel processing has been done; use the future processing plan only after Phase 3 approval.

## Reservoir measurements
The TN Agriculture Reporting System requires officer login and OTP; obtain authorized access directly. Public search found the already-held CWC Chembarambakkam/Poondi advisory but no public historical time-series download. Check CWC's public reservoir bulletins and India-WRIS public pages; do not authenticate or submit forms here. Export current level/storage/inflow/outflow only if clearly public for Chembarambakkam, Poondi, Puzhal/Red Hills, Cholavaram and other basin reservoirs. Historical event windows remain missing.

Email/RTI template to TN WRD PIO or responsible reservoir division:

Subject: Request for Chennai-basin reservoir measurements and release records

Please provide machine-readable daily records for Chembarambakkam, Poondi, Puzhal (Red Hills), and Cholavaram reservoirs for 1 Nov–15 Dec 2015, 1–20 Nov 2021, and 25 Nov–15 Dec 2023. Include date/time and time zone, storage/level, inflow, outflow/release in cusecs, gate openings, units, station IDs, and release/operation logs. CSV or XLSX is preferred. Please identify unavailable periods and the responsible record-holding office.

The CWC advisory is saved under data/raw/reservoirs. The CAG executive summary was downloaded on 2026-10-13 to data/raw/reservoirs/reference_docs/; it opens as a 7-page PDF. It reports Chembarambakkam discharge of 20,960–29,000 cusecs and 29,000 cusecs for 21 hours on 1–2 Dec 2015. This is not a full release time series and gives no comparable releases for the other reservoirs. The full report remains uncollected. The earlier TLS failure applied to a previous direct-link attempt; the summary was subsequently obtained through the official CAG report listing.

## Login/request rainfall sources
- ERA5 CDS: register at https://cds.climate.copernicus.eu/ and request hourly event/baseline fields clipped to the buffered bbox.
- GPM IMERG: 86 daily V07B files are now present and compared. Confirm the actual source page/URL and product licence from the page used to acquire them; see `data/raw/weather/imerg/DOWNLOAD_LOG.txt` and `RAIN_SOURCES_COMPARISON.md`. Consider checking peak results against gauges or IMD products before relying on them.
- IMD: request station/gridded rainfall through https://mausam.imd.gov.in/; record actual terms/fees and do not automate forms.

## Environment
Project `.venv` now contains the pinned dependencies in `requirements.txt`; pip was bootstrapped into this environment. No global packages were installed.

## Reservoir request templates (ready to personalize; do not send from Codex)

**Recipient:** Public Information Officer, Tamil Nadu Water Resources Department / office holding Chennai reservoir operation records — **address to be confirmed**. A CWC source identifies CMWSSB as the operator of some Chennai reservoirs, but an official PIO directory/record-holder for the requested series was not verified. Confirm the correct authority before submitting. No request has been sent.

### RTI application draft

To: The Public Information Officer, [verified public authority and office address]

Subject: Information request — daily Chennai-basin reservoir storage, inflow, and release records

Please provide existing records in machine-readable CSV or XLSX format, if held, for Chembarambakkam, Poondi, Puzhal (Red Hills), Cholavaram, and other reservoirs operated in the Chennai basin for these periods:

- 1 November–15 December 2015
- 1–20 November 2021
- 25 November–15 December 2023

For each reservoir and timestamp, please include water level, storage (with units and capacity), inflow and outflow/release (including cusecs where recorded), gate opening/release operation logs, station identifiers, time zone, and the source/recording division. Please identify any missing dates, unavailable variables, or records held by another public authority, and provide the name of that authority/office if known. I request existing records; I am not asking the authority to create new analysis.

Applicant name: [your name]
Postal address: [your address]
Contact: [email/phone, if desired]
Date: [date]
Signature: [signature]

Submit only after checking the current RTI rules, application fee, correct PIO, and official submission channel for the verified authority.

### Email draft

To: [verified official TN WRD/PWD or reservoir-records division email]
Subject: Request for historical Chennai-basin reservoir operation records (2015, 2021, 2023)

Dear Sir/Madam,

I am conducting an academic study of flood events in the Chennai Metropolitan Area. Could you please provide any existing machine-readable daily or sub-daily records for Chembarambakkam, Poondi, Puzhal (Red Hills), Cholavaram, and other Chennai-basin reservoirs for 1 Nov–15 Dec 2015, 1–20 Nov 2021, and 25 Nov–15 Dec 2023? I am seeking timestamped level and storage, inflow, outflow/release (including cusecs where recorded), gate operation logs, units, station identifiers, and time zone. Please indicate missing periods and the office that maintains these records. CSV/XLSX is preferred.

Thank you,
[Name]
[Institution / project]
[Contact]

## Reservoir public-source re-check (2026-10-08)

Public CWC/NWDP pages expose general reservoir datasets and bulletins, but the reviewed CWC manual daily reservoir-water-level dataset currently lists Odisha and Madhya Pradesh resources, not Chennai-basin files. CWC's public reservoir monitoring dashboard describes current monitored reservoirs, not a downloadable historical series for these three event windows. TN Agrisnet's public page is a current summary; its historical reservoir page presents login/OTP and was not accessed. The held CWC advisory is a single 23 Nov 2020 snapshot for Chembarambakkam and Poondi, not a 2015/2021/2023 time series. No new file was added because the raw folder is read-only and no qualifying public Chennai time-series file was verified.

## CAG 2017 report

Official URL retried once with 180-second timeout and normal SSL on 2026-10-08. The request failed with an SSL connection closed error; keep the official URL above for manual retrieval. No mirror was used.
# Phase 3 follow-up checks — 2026-10-14

- Confirm the final study boundary (older CMA vs expanded jurisdiction) before locking any final model features.
- Inspect the GLO-30 coastal negative elevations, DSM artifacts, pits/flats, and flow paths in QGIS; decide and document a hydrologic conditioning method before using flow accumulation/TWI as model predictors.
- Verify the current published reservoir capacities against historical capacities for the 2004–2020 periods. The present capacity percentages are contextual only.
- Verify Kaggle rainfall column units/source metadata; do not compare its rainfall field directly until units are established.
- Compare WorldPop totals with census figures for Chennai district and the CMA; WorldPop is an alpha constrained model estimate and should be used for relative exposure until explained.
- Recheck NASA POWER `PRECTOTCORR` units and metadata from the official product documentation before reporting the ERA5 comparison as physical bias.
- Obtain/confirm authoritative peak/event windows for Sentinel comparison. Two 16 Nov 2021 ZIPs are now downloaded and verified, and a 6 Dec 2015 ZIP is available within the 1–8 Dec event window; all Sentinel products remain unprocessed. Confirm ASF/Copernicus terms before any redistribution.
- Decide whether to digitize the 2021/2023 NRSC/NDEM PDFs or narrow validation to observed dates/places. For the Dec 1–8 2015 peak, continue searching only official channels for observed GIS layers; do not use the November vectors as a December substitute.
- Review OpenCity metadata and keep incident points separate from modeled return-period/hazard polygons.
- Verify any Sentinel-1 preprocessing environment and ASF redistribution terms before starting a separately approved Sentinel task.
- Install or otherwise approve a Parquet engine if downstream workflows require Parquet. Current reproducible weather and reservoir outputs are CSV because `pyarrow`/`fastparquet` are absent.
- Audit OSM extraction completeness, directed connectivity and largest-component shares; review nearest-road snapping distances and named waterways. OSM absence is not proof of real-world absence; comply with ODbL attribution/share-alike obligations.

## Phase 4 Part 1 decisions — 2026-10-17

- Confirm the 2 m river/canal burn depth, default vehicle speeds, and 0.3 m flood-passability cutoff before interpreting terrain or route times. The flood cutoff is an assumption requiring literature confirmation.
- Review `slope_deg_edge_safe.tif` and `twi_d8_proxy_edge_safe.tif` and the remaining −64.51 m source DEM artefact before relying on terrain derivatives.
- On the ASF site, verify availability, required inputs, and free credit limits for HyP3/On Demand before selecting it over local SNAP. No account or network check was performed here.
- Confirm the actual IMERG source page and licence. Consider obtaining or consulting IMD gridded daily rainfall as an independent comparison; no IMD files were collected in this task.

- To complete Phase 4.1 and 4.4, arrange an approved offline `.whl` for `pyarrow` (or `fastparquet`) and install it into `D:\TIWNGUARD\.venv`, then rerun `pipelines\phase4\time_alignment.py` and `pipelines\phase4\static_feature_stack.py`. The current prompt prohibited network access, so Codex did not fetch or install packages. Also install the pinned test runner `pytest` from an approved offline wheel before rerunning `pytest tests\phase4`.
- Review the preliminary `data\processed\alignment\layer_registry.json` versus the corrected `layer_registry_complete.json`; decide later whether to archive the preliminary file under a distinct name or leave both. It was preserved to comply with the no-overwrite rule.

### Completion note — 2026-10-17

The user installed the approved local packages into `.venv`; Phase 4 event and static Parquet outputs were generated and all pytest checks passed. The earlier Parquet/pytest installation task above is resolved. The coastline-source and preliminary-registry review items remain open.
