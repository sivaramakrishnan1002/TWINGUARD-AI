# Stage 8 SAR label work log

**Date:** 2026-10-25 (Asia/Kolkata). Raw inputs were only read; no network, downloads or installs were used.

## 8.1 RTC verification

13 local HyP3 RTC ZIPs passed CRC checks and were linked to their matching Sentinel-1 source ZIPs: 3 (2015), 6 (2021), 4 (2023). Product rasters are EPSG:32644, 30 m, gamma-0 power; VV/VH, DEM, incidence-angle and layover/shadow layers are present. HyP3 speckle filter is off. License remains TO CONFIRM. See `HYP3_RTC_VERIFICATION.md` and `DOWNLOAD_LOG.txt`.

## 8.2–8.4 Processing and pilot

Lee filter 5×5 ran in linear power; local variance estimated from the lowest 10% CV neighbourhoods. Change detection was converted to dB. Otsu thresholds used valid CMA land only and were not selected from UNOSAT labels. Baseline mask used any nonzero class in either UNOSAT Sep 1 or Oct 14 layer plus WorldCover water fraction >0; dense urban is built-up fraction ≥0.5. All 13 products have layover/shadow masks (bit 4/16 excluded; untested mask 0 excluded), so no slope fallback was applied.

SciPy was available and was used for the 5×5 local Lee filter; scikit-image was not installed. Otsu histogram thresholding was implemented with NumPy, so no new dependency was needed. The 2021 adjacent-slice mosaics used deterministic first-valid fill; overlap pixels were 1,609 (23 Oct), 1,613 (4 Nov), and 1,615 (16 Nov).

The pilot comparison confirms the default Otsu results are poor as inundation extents: 24 Nov change method IoU 0.103, precision 0.103, recall 0.987, F1 0.187; excluding dense urban gives IoU 0.138 and F1 0.242. Event-backscatter Otsu IoU is 0.056, precision 0.056, recall 1.000, F1 0.106. The -3 dB sensitivity offset raises F1 to 0.545 and IoU to 0.374, but is a sensitivity diagnostic—not a replacement threshold selected from UNOSAT. Candidate areas are much too large: 363.49 km² on Nov 24, 482.38 km² on Dec 6, and 398.60 km² on Nov 16 2021. Do not treat these as accepted flood maps.

The Nov 24 source UNOSAT raster gross area is 98.16 km². In the common valid and water-excluded evaluation cells, its comparison area is 37.93 km² (37.51 km² excluding dense urban). The potential same Sentinel acquisition means this is pipeline/map agreement, not physical validation.

Dec 6 2015 candidate area increases 118.89 km² over Nov 24. Its overlap with the coarse GFD 4309 layer (ends Dec 4) is IoU 0.040 on common evaluation cells; GFD has 32,929 resampled flooded 30 m cells in the comparison mask. OpenCity has 399/945 points inside the candidate (42.2%), but the point timestamps are unspecified and do not constitute date-matched validation. 2021 Nov 16 area is 398.60 km²; NRSC Nov 13 PDF and 2015 OpenCity points cannot validate it numerically. No 2023 label: no post-peak image.

## Outputs and database

Four master-grid DERIVED candidate rasters and four GPKG polygon layers are recorded by the registry. Polygon simplification tolerance is 30 m. Database migration `013_sar_derived_labels.sql` created `labels.derived_flood_polygons`; 45,096 rows were inserted. Checks: 0 invalid, 0 outside CMA, 0 wrong SRID, 0 missing provenance; all rows marked DERIVED.

## Errors encountered and correction

The first vector export failed because Fiona was missing; installed `pyogrio` was used instead (no install). The first processing metadata JSON write failed on Rasterio's CRS object; it was converted/string-serialized. Outputs from failed passes were preserved per no-overwrite rules; the selected completed run is identified in the registry. An initial loader run looked for the default GPKG filename and failed; loader now resolves the registered vector path.

No model training was started. Manual QGIS instructions are in `MANUAL_TODO.md`.

The Stage 8 additions bring `docs/DATA_MANIFEST.csv` and its database snapshot to 130 rows. An idempotent second label load inserted 0 rows in each of the four layers and did not change the 45,096-row total. The full test suite initially found the manifest snapshot stale; it was refreshed with `tools.refresh_data_manifest`, and the old 117-row test expectation was changed to check the current CSV row count.

Final full test run: `pytest -q` — **38 passed, 0 failed**, with one pre-existing Starlette/httpx deprecation warning. Raw audit: **157 files, 30,544,672,450 bytes, 157 matches, 0 unmatched, 0 mismatches**.
