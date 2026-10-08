# Sentinel-1 acquisition plan (catalogue only)

Catalog queried read-only on 2026-10-08 at the public [Copernicus Data Space STAC search endpoint](https://stac.dataspace.copernicus.eu/v1/search), collection `sentinel-1-grd`, using the CMA boundary and requested event windows. No imagery was downloaded. Footprint coverage is the intersection area divided by the full CMA boundary area, with both geometries projected to EPSG:32644. Product sizes are the catalog `Product.file:size` values converted to decimal MB (bytes / 1,000,000), not downloaded sizes. The catalog returns adjacent slices separately; slices from one datatake may be needed together for full CMA coverage.

## Every intersecting event-window scene returned by the catalog

| Event | Product name | Acquisition UTC | Platform | Direction | Relative orbit | Polarisation | Product MB | CMA covered |
|---|---|---|---|---|---:|---|---:|---:|
| 2015 | S1A_IW_GRDH_1SDV_20151112T003120_20151112T003149_008564_00C241_7619_COG | 2015-11-12 00:31:20 | Sentinel-1A | descending | 92 | VV,VH | 1344.05 | 100.00% |
| 2015 | S1A_IW_GRDH_1SDV_20151124T003120_20151124T003149_008739_00C723_84B9_COG | 2015-11-24 00:31:20 | Sentinel-1A | descending | 92 | VV,VH | 1352.82 | 100.00% |
| 2021 | S1A_IW_GRDH_1SDV_20211104T003147_20211104T003212_040414_04CA78_6D88_COG | 2021-11-04 00:31:47 | Sentinel-1A | descending | 92 | VV,VH | 1158.64 | 27.64% |
| 2021 | S1A_IW_GRDH_1SDV_20211104T003212_20211104T003237_040414_04CA78_AF3A_COG | 2021-11-04 00:32:12 | Sentinel-1A | descending | 92 | VV,VH | 1191.06 | 72.33% |
| 2021 | S1A_IW_GRDH_1SDV_20211116T003147_20211116T003212_040589_04D094_898D_COG | 2021-11-16 00:31:47 | Sentinel-1A | descending | 92 | VV,VH | 1164.40 | 27.65% |
| 2021 | S1A_IW_GRDH_1SDV_20211116T003212_20211116T003237_040589_04D094_667C_COG | 2021-11-16 00:32:12 | Sentinel-1A | descending | 92 | VV,VH | 1187.46 | 72.32% |
| 2023 | S1A_IW_GRDH_1SDV_20231130T003201_20231130T003226_051439_06353D_6C35_COG | 2023-11-30 00:32:01 | Sentinel-1A | descending | 92 | VV,VH | 1181.16 | 86.44% |
| 2023 | S1A_IW_GRDH_1SDV_20231130T003226_20231130T003251_051439_06353D_15A1_COG | 2023-11-30 00:32:26 | Sentinel-1A | descending | 92 | VV,VH | 1200.47 | 13.54% |

## Same-orbit pre-event references

| Event | Product name | Acquisition UTC | Platform | Direction | Relative orbit | Polarisation | Product MB | CMA covered |
|---|---|---|---|---|---:|---|---:|---:|
| 2015 | S1A_IW_GRDH_1SDV_20151019T003131_20151019T003200_008214_00B8EF_F5CD_COG | 2015-10-19 00:31:31 | Sentinel-1A | descending | 92 | VV,VH | 1311.84 | 100.00% |
| 2021 | S1A_IW_GRDH_1SDV_20211023T003148_20211023T003213_040239_04C461_F698_COG | 2021-10-23 00:31:48 | Sentinel-1A | descending | 92 | VV,VH | 1141.08 | 27.69% |
| 2021 | S1A_IW_GRDH_1SDV_20211023T003213_20211023T003238_040239_04C461_DA24_COG | 2021-10-23 00:32:13 | Sentinel-1A | descending | 92 | VV,VH | 1178.91 | 72.28% |
| 2023 | S1A_IW_GRDH_1SDV_20231118T003202_20231118T003227_051264_062F3A_F15E_COG | 2023-11-18 00:32:02 | Sentinel-1A | descending | 92 | VV,VH | 1154.85 | 86.51% |
| 2023 | S1A_IW_GRDH_1SDV_20231118T003227_20231118T003252_051264_062F3A_046F_COG | 2023-11-18 00:32:27 | Sentinel-1A | descending | 92 | VV,VH | 1175.22 | 13.47% |

The pre-event listing above includes the nearest catalogued matching pass(s) by event. Additional qualifying pre-event slices were found: 2021-10-11 (same orbit 92, descending; 72.31% and 27.67% coverage) and 2023-11-06 (same orbit 92, descending; 86.48% and 13.50% coverage). These are farther from their respective event starts than 23 Oct 2021 and 18 Nov 2023.

## Timing recommendations and size

Provisional peak dates are not validated event observations: 1 Dec 2015, 7 Nov 2021, and 4 Dec 2023.

- **2015:** use 24 Nov 00:31 UTC as the closest available acquisition to the provisional peak (7 days before), and 19 Oct 00:31 UTC as the before-event reference (same descending relative orbit 92). The STAC result has one full-boundary slice for each acquisition. Neither event-window scene observes the 1-8 Dec peak.
- **2021:** 4 Nov 00:31-00:32 UTC is 3 days before the provisional peak; 16 Nov 00:31-00:32 UTC is 9 days after. Both acquisitions contain two catalog slices covering about 100% combined. Use 23 Oct 00:31-00:32 UTC as the closest matching pre-event reference, also two slices. If a single post-peak acquisition is required, 16 Nov is the available choice, with a 9-day lag.
- **2023:** the catalog returned no event-window pass on or after the provisional 4 Dec peak; 30 Nov 00:32 UTC is 4 days before it. Its two slices cover about 100% combined. Use 18 Nov 00:32 UTC as same-orbit pre-event reference (two slices). Both are pre-peak; this cannot establish peak inundation.

Recommended minimum full-coverage pairing: 2 products for 2015, 4 for 2021 (4 Nov event pass plus 23 Oct reference, both two-slice acquisitions), and 4 for 2023 (30 Nov plus 18 Nov, both two-slice acquisitions). Total: **10 products, 12,046,047,571 bytes (12,046.05 decimal MB; 12.05 GB)**. The 4 Nov 2021 pair is closest to the provisional peak; the 16 Nov pair is a separate post-peak option 9 days after the peak. The full requested event shortlist plus nearest reference acquisitions is **17 products, 20,419,832,685 bytes (20,419.83 MB; 20.42 GB)**. The event-window rows alone are 8 products, 9,780,059,543 bytes. These are catalogued product sizes and may differ from the manually downloaded file size if packaging changes.

D: had **247,457,554,432 bytes free** at the check, enough for either set. Keep additional headroom for extraction/processing later; do not extract into `data/raw`.

## Manual acquisition constraints

The project's raw folder is read-only for this close-out. Therefore this report is saved under `docs/`; no `data/raw/satellite/sentinel1_shortlist.csv` or event folders were created. Create the requested empty target folders and a CSV copy of the two tables only after resolving the raw-folder write restriction. In the Data Space Browser, select the exact full product names above, verify the name and acquisition timestamp, and keep the original `.zip` filename unchanged. See `MANUAL_TODO.md` for download and verifier steps.
