# Manual TODO — Phase 2

Complete remaining items before Phase 3. Preserve raw files. For every later acquisition, record the exact URL, date/time, byte size, SHA-256, licence, and verification in its log and manifest.

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
Latest official source found: WorldPop R2025A India, constrained 2021, about 100 m, 728.76 MB advertised, CC BY 4.0: https://hub.worldpop.org/geodata/summary?id=73803

Direct file: https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2021/IND/v1/100m/constrained/ind_pop_2021_CN_100m_R2025A_v1.tif

Download the single India raster (below 2 GB) to data/raw/population; no bbox endpoint was established. Previous attempt stalled at 112,704,318 bytes and its partial was removed. Retry on a stable connection. Verify GeoTIFF, year, constrained type, CRS, size, and SHA-256. About 100 m cells are coarser than road-segment decisions.

## OpenStreetMap

The Geofabrik Southern Zone PBF is downloaded and inventoried. See `docs/OSM_COUNTS.md` for counts and limitations. Exact named-watercourse presence remains to be verified against waterway geometries/names.

## Sentinel products
1. Register at https://dataspace.copernicus.eu/
2. Use data/raw/satellite/scenes_candidates.csv to choose Sentinel-1 GRD IW and Sentinel-2 L2A; S2 rows already meet cloud <40%.
3. Download selected intersecting products; retain original packages. CSV asset sizes may not equal full product size.
4. Nearest S1 dates to reference peak proxies: 24 Nov 2015 (7 days from 1 Dec), 4 Nov 2021 (3 days from 7 Nov), 30 Nov 2023 (4 days from 4 Dec). Validate peak dates before use.

## Reservoir measurements
The TN Agriculture Reporting System requires officer login and OTP; obtain authorized access directly. Public search found the already-held CWC Chembarambakkam/Poondi advisory but no public historical time-series download. Check CWC's public reservoir bulletins and India-WRIS public pages; do not authenticate or submit forms here. Export current level/storage/inflow/outflow only if clearly public for Chembarambakkam, Poondi, Puzhal/Red Hills, Cholavaram and other basin reservoirs. Historical event windows remain missing.

Email/RTI template to TN WRD PIO or responsible reservoir division:

Subject: Request for Chennai-basin reservoir measurements and release records

Please provide machine-readable daily records for Chembarambakkam, Poondi, Puzhal (Red Hills), and Cholavaram reservoirs for 1 Nov–15 Dec 2015, 1–20 Nov 2021, and 25 Nov–15 Dec 2023. Include date/time and time zone, storage/level, inflow, outflow/release in cusecs, gate openings, units, station IDs, and release/operation logs. CSV or XLSX is preferred. Please identify unavailable periods and the responsible record-holding office.

The CWC advisory is saved under data/raw/reservoirs. The official CAG 2017 report link is https://www.cag.gov.in/uploads/download_audit_report/2017/Report_No_4_of_2017_-_Performance_Audit_of_Flood_Management_and_Response_in_Chennai_and_its_Suburban_Area.pdf . Hosts timed out; try manually and save to data/raw/reservoirs/reference_docs.

## Login/request rainfall sources
- ERA5 CDS: register at https://cds.climate.copernicus.eu/ and request hourly event/baseline fields clipped to the buffered bbox.
- GPM IMERG: use an authorized NASA Earthdata account at https://urs.earthdata.nasa.gov/ and request event precipitation clipped to bbox.
- IMD: request station/gridded rainfall through https://mausam.imd.gov.in/; record actual terms/fees and do not automate forms.

## Environment
Project `.venv` now contains the pinned dependencies in `requirements.txt`; pip was bootstrapped into this environment. No global packages were installed.
