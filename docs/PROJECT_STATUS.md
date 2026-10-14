# Project status — Phase 2 close-out

## Done

- Project setup, PostgreSQL/PostGIS Compose definition, and Phase 2 source inventory are documented. No container was started.
- Current raw inventory: 55 data files and 18 metadata logs. A read-only audit found all 55 data files match a logged size and SHA-256; no mismatches and no current file without a comparable hash. Failed download attempts in logs are historical records, not present files.
- Boundary, UNOSAT archive, NRSC/NDEM PDFs, weather products, four Copernicus DEM tiles, WorldCover, OSM extract, WorldPop, reservoir sources, OpenCity flood resources, Global Flood Database event 4309, and CAG executive summary are inventoried. Caveats are recorded in `DATA_QUALITY_REPORT.md`.
- Ten manually acquired ASF Sentinel-1A GRD-HD ZIPs (2015, 2021, 2023) pass ZIP integrity checks. SAFE metadata, hashes, acquisition names, orbits, coverage and post-peak catalogue options are in `SENTINEL_VERIFICATION.md`. The raw directory spelling `senitnel1` is intentionally unchanged.
- Git project setup and PostgreSQL/PostGIS Compose definition exist. No containers were started.

## Manual or unavailable

- The 2015 UNOSAT vector layers are dated 1 Sep, 14 Oct, 12 Nov and 24 Nov; they miss the 1–8 Dec peak. Global Flood Database event 4309 is a coarse 250 m cross-check and ends 4 Dec.
- The 2021 and 2023 official flood references are PDFs requiring manual digitising. OpenCity return-period layers are modelled, not observed.
- No public historic Chennai-basin reservoir release series was verified. The Kaggle/OpenCity datasets describe storage; Kaggle rainfall units are undocumented. The CAG executive summary gives some Chembarambakkam release figures for 1–2 Dec 2015, not a complete time series.
- WorldPop R2025A is alpha, constrained, and its roughly 6.2 million CMA sum is a model estimate; NoData is not zero. Census comparison remains to be done.
- Sentinel data licence terms for the ASF downloads remain to be confirmed. All downloaded scenes are before provisional flood peaks. The saved catalogue offers a 16 Nov 2021 two-slice post-peak pair, but no post-peak candidate for 2015 or 2023.
- Some historical raw logs preserve failures with zero bytes and no applicable hash. No corresponding present files were found.

## Next

1. Confirm applicable ASF licence/terms and decide whether to obtain the optional 16 Nov 2021 Sentinel pair.
2. Continue manual work on December 2015 flood references, digitising the 2021/2023 PDF maps, reservoir records, and the WorldPop/census comparison.
3. Review `PHASE2_CLOSURE.md` readiness risks. Phase 3 remains unstarted; wait for explicit approval before any processing.
