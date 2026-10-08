# Phase 2 closure

This close-out is an inventory and planning pass. It did not begin Phase 3 or write into `data/processed` or `data/features`. Existing raw files were kept unchanged. Status refers to available data, not whether it is already model-ready.

## Dataset inventory

| Dataset | Status | Path | Main caveat |
|---|---|---|---|
| CMA boundary | collected | `data/raw/boundary/chennai_cma_boundary.geojson` | Pre-expansion boundary; source/licence evidence and boundary vintage need confirmation. |
| UNOSAT flood layers, 2015 | partial | `data/raw/historical_floods/2015/2015-12-04/FL20151123IND_shp.zip` | 8 layers from 1 Sep, 14 Oct, 12 Nov and 24 Nov; none cover the 1-8 Dec peak. |
| NRSC flood map, 2021 | collected | `data/raw/historical_floods/2021/ChennaiCity-ChennaiCorporationTaluk-4.pdf` | PDF map, partial city coverage, needs manual digitising. |
| Supplied NRSC Michaung PDFs | missing | `data/raw/historical_floods/2023/` (not present) | Supplied links failed; do not count as collected. |
| Official NDEM 7 Dec 2023 map | collected | `data/raw/historical_floods/2023/tncyclone50dsc07122023_0600hrs_map.pdf` | Preliminary PDF, no ground verification; needs digitising. |
| Official NDEM 18 Dec 2023 map | collected | `data/raw/historical_floods/2023/tnflood50dsc12182023_1800hrs_vap1.pdf` | Tuticorin-only sheet, outside CMA. |
| December 2015 products | manual-needed | Viewer records only; no GIS layer saved | Viewer lists products but no direct public GIS file was found. |
| Open-Meteo ERA5 | collected | `data/raw/weather/` | Nine point samples; coarse reanalysis, not gauge measurements. |
| NASA POWER | collected | `data/raw/weather/` | Nine daily point samples; coarse model/satellite product, not gauges. |
| ERA5 CDS | manual-needed | Not collected | Requires user account/API request. |
| GPM IMERG | manual-needed | Not collected | Requires user-authenticated access and product choice. |
| IMD rainfall | manual-needed | Not collected | Product/access terms and station or grid source need confirmation. |
| Copernicus GLO-30 DEM | collected | `data/raw/dem/` | Four tiles cover the buffered area; DSM includes vegetation/buildings. |
| OpenStreetMap Southern Zone extract | collected | `data/raw/roads/southern-zone-latest.osm.pbf` | Broad extract; exact-name subset has 6 endpoint-connected components and 12 degree-one endpoints, but unnamed connectors may exist and OSM completeness is not assured. |
| ESA WorldCover 2021 | collected | `data/raw/landcover/` | Single 10 m classification epoch; may not match all event years. |
| WorldPop constrained 2021 R2025A | collected | `data/raw/population/ind_pop_2021_CN_100m_R2025A_v1.tif` | Alpha model estimate; 23,812 CMA pixel centers are nodata; compare with census. |
| CWC reservoir advisory | partial | `data/raw/reservoirs/cwc_chembarambakkam_poondi_reservoir_advisory.pdf` | One dated advisory snapshot, not event-window time series. |
| Chennai-basin reservoir series | missing | Not collected | No public historical series for the three event windows was verified; TN portal requires login/OTP. |
| Sentinel-1 public catalogue | partial | `data/raw/satellite/scenes_candidates.csv`; details in `docs/SENTINEL_PLAN.md` | Catalogue only; acquisitions do not always observe peak dates and adjacent slices are separate items. |
| Sentinel-1 image products | manual-needed | Not downloaded | User must download; raw subfolders/shortlist were not created because `data/raw` is read-only. |
| CAG 2017 audit report | manual-needed | Not saved | Official URL retry failed with TLS connection closed. |
| Boundary/census comparison | manual-needed | `docs/MANUAL_TODO.md` | Census comparison not completed. |

Existing raw file size/hash checks: 30 logged hashes with comparable files matched; 12 entries had no comparable hash value. No mismatch was found. Several log entries describe failed attempts and are not collected files. The raw tree was not changed during this close-out.

## Phase 3 readiness

“Can start now” is a readiness assessment only; Phase 3 remains unstarted pending explicit approval.

| Phase 3 task | Can start now? | Waiting for | Risk if started without it |
|---|---|---|---|
| Terrain features | Yes, after approval | Confirm common projected grid and DEM vertical/DSM limitations | Flow products can be misaligned; buildings and vegetation affect surface drainage. |
| Rainfall sequences | Partly, after approval | Decide whether current ERA5/POWER point sampling is adequate; gauge/IMERG/IMD improvements | Coarse gridded rainfall can miss local gradients and peak timing. |
| Road graph | Yes, after approval | Verify OSM waterway/road topology and define graph snapping rules | OSM omissions or disconnected segments may distort routing. |
| Land cover | Yes, after approval | Decide how 2021 WorldCover represents 2015/2023 | Temporal mismatch can misstate imperviousness and exposure. |
| Population exposure | Yes, after approval | Census comparison; decide nodata handling and boundary vintage | WorldPop alpha sum is below the believed 2011 CMA total; nodata is not zero. |
| Flood labels | No | December 2015 layers; manually digitise 2021/2023 PDFs; validate event dates and class meaning | Current labels miss the 2015 peak and combine dates/product types; severe timing and label bias. |
| Reservoir features | No | Historical level/inflow/release series and verified authority response | Missing reservoir operations can omit a major driver of the 2015 flood. |
| Satellite features | No | Manually download catalogued Sentinel-1 products and confirm which passes are temporally useful | No peak observation for 2015/2023 in current shortlist; change detection is limited by temporal gaps. |

## Hand tasks, priority order

1. **NRSC: December 2015 layers.** Contact `flood@nrsc.gov.in` to request original observed 3–8 Dec layers, including the cumulative RISAT-1 product, metadata, acquisition dates, and reuse terms. The 2015 UNOSAT vector layers stop on 24 Nov.
2. **Sentinel-1 downloads.** Use `docs/SENTINEL_PLAN.md` and `docs/SENTINEL_SHORTLIST.csv`; download the recommended event/reference products manually after resolving the raw-folder read-only constraint. Retain original ZIP names.
3. **Reservoir records.** Verify the correct TN WRD/PWD record-holding office and PIO; submit the draft RTI or email in `docs/MANUAL_TODO.md` for the three event windows.
4. **WorldPop census comparison.** Compare Chennai district and CMA estimates with source census figures using matching boundary vintages; verify the believed 2011 CMA total before interpreting it.

## Known limitations

- The 2015 vector layers do not cover the 1-8 Dec peak; 2021/2023 reference maps are PDFs requiring manual digitising.
- Sentinel provisional peaks are not independently validated; no 2015 or 2023 post-peak pass was returned in the specified event windows. The closest 2021 pass is 3 days before 7 Nov; the post-peak option is 9 days after.
- WorldPop R2025A is alpha and constrained; its roughly 6.2 million valid-cell-center sum is a model estimate, not census count, and nodata semantics do not tell whether every masked CMA cell is unsettled or missing.
- Reservoir event-window history is missing; the CWC advisory is a 2020 snapshot only.
- Dataset reuse terms differ; NRSC PDFs say “For official use”, and the CWC advisory's PDF-specific reuse terms were not found.
- Existing CMA boundary vintage may not match current administrative limits.
- No feature engineering, raster processing, model training, or outputs were created; Phase 3 has not started.
