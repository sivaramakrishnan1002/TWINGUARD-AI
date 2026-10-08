# Project status — Phase 2 close-out

## Done

- Phase 2 source inventory and checksum audit: 30 comparable logged SHA-256 records matched the on-disk files; 12 log entries did not have a comparable hash. No mismatch was found. Existing raw files remain untouched.
- The CMA boundary, 2015 UNOSAT archive, 2021 NRSC PDF, 2023 official NDEM PDFs, WorldPop raster, weather data, DEM, land cover, OSM regional extract, and CWC advisory are inventoried. The WorldPop file opens as a raster; its model estimate and nodata limits are documented.
- OSM regional feature counts, exact named-waterway matches and the named-subset connectivity check, and the catalogue-only Sentinel scene shortlist are documented. Sentinel image products were not downloaded.
- Usage terms and attribution checks are summarized in the data quality report. Phase 2 close-out and Phase 3 readiness are in `PHASE2_CLOSURE.md`.
- Git project setup and the PostgreSQL/PostGIS Compose definition exist. No containers were started.

## Manual or unavailable

- No December 2015 peak flood vector layers were obtained; NRSC should be contacted. The collected UNOSAT layers are dated 1 Sep, 14 Oct, 12 Nov, and 24 Nov and miss the 1–8 Dec peak.
- The 2021 and 2023 flood references are PDF maps and need manual digitising. NRSC products carry “For official use” legends; redistribution terms need confirmation.
- No public Chennai-basin historical reservoir series for the requested windows was verified. The TN historical portal requires login/OTP; no login was attempted. A ready RTI/email draft is in `MANUAL_TODO.md`; correct PIO address is unverified.
- The CAG official PDF retry failed with a TLS connection close; retain the URL for manual retrieval.
- Sentinel catalogue rows and full product sizes are documented, but the raw folder remained read-only. User must create the requested year folders and download products manually; no Phase 3 processing has started.
- WorldPop totals need comparison with census figures and boundary vintages.

## Next

1. Request December 2015 flood layers from NRSC.
2. Download the selected Sentinel-1 products manually after resolving the raw-folder write constraint.
3. Request historical reservoir records from the verified record-holding authority.
4. Compare WorldPop totals with census estimates.
5. Only after explicit approval, begin Phase 3 preparation and validation.
