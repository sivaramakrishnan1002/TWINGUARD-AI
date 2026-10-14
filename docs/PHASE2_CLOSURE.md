# Phase 2 closure

This close-out verifies and reconciles Phase 2. It did not begin Phase 3 or write into `data/processed` or `data/features`. Raw data files were kept unchanged; the only raw-tree addition was the permitted Sentinel metadata `DOWNLOAD_LOG.txt`. Status refers to available data, not whether it is already model-ready.

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
| Sentinel-1 ASF GRD-HD image products | collected | `data/raw/satellite/senitnel1/{2015,2021,2023}/` | Ten ZIPs, all pass CRC and metadata/name checks; all acquisitions predate the provisional peaks; ASF licence terms remain to confirm. See `docs/SENTINEL_VERIFICATION.md`. |
| CAG 2017 audit report | manual-needed | Not saved | Official URL retry failed with TLS connection closed. |
| Boundary/census comparison | manual-needed | `docs/MANUAL_TODO.md` | Census comparison not completed. |

Read-only raw audit on 2026-10-14: 55 current data files (14,706,156,884 bytes) matched logged sizes and SHA-256 values; 0 mismatches and 0 current files without a comparable hash. Historical failed-attempt log records with 0 bytes and “not applicable” hashes are not present files. The only addition in `data/raw` was the permitted Sentinel metadata log; no raw data file was changed.

## Phase 3 readiness

This table is a readiness assessment only. Phase 3 remains unstarted until explicitly approved.

| Phase 3 task | Can start now? | Waiting for | Risk if started anyway |
|---|---|---|---|
| Terrain | Yes, after approval | Confirm the master grid and DSM vertical/surface limitations | Vegetation/buildings and depression treatment affect urban flow routing. |
| Rainfall | Yes, after approval, using current files | Decide whether Open-Meteo ERA5 and NASA POWER point samples are adequate | Model products are not gauges and may miss local rainfall peaks. |
| Road graph | Yes, after approval | Define OSM clipping, routing and connectivity rules | OSM omissions and disconnected components can distort evacuation routes. |
| Land cover | Yes, after approval | Decide how 2021 WorldCover represents 2015/2023 | Temporal mismatch; built-up fraction is only an imperviousness proxy. |
| Population exposure | Yes, after approval | Census comparison and explicit NoData handling | WorldPop alpha estimate is lower than believed census total; NoData is not zero. |
| Reservoir features | Partly, after approval | Verify capacities and source units; release time series are unavailable | Storage change is not outflow; no release series for most reservoirs/events. |
| Flood labels | No, not for final validation | Obtain 2015 Dec peak layers; manually digitise 2021/2023 PDFs or narrow validation scope | Current vector labels miss 1–8 Dec 2015; PDFs are not yet digitised. |
| Sentinel-1 processing | No, until processing is separately approved/planned | Confirm ASF licence; decide on post-peak 16 Nov 2021 pair; identify processing software/storage | All ten downloaded scenes are pre-peak; they cannot directly observe peak inundation. |

## Hand tasks, priority order

1. **NRSC: December 2015 layers.** Contact `flood@nrsc.gov.in` to request original observed 3–8 Dec layers, including the cumulative RISAT-1 product, metadata, acquisition dates, and reuse terms. The 2015 UNOSAT vector layers stop on 24 Nov.
2. **Sentinel-1 terms and optional post-peak acquisition.** Confirm the applicable ASF download licence/terms. The ten pre-peak products are already present and verified; decide whether the catalogue-only 16 Nov 2021 two-slice pair is worth acquiring.
3. **Reservoir records.** Verify the correct TN WRD/PWD record-holding office and PIO; submit the draft RTI or email in `docs/MANUAL_TODO.md` for the three event windows.
4. **WorldPop census comparison.** Compare Chennai district and CMA estimates with source census figures using matching boundary vintages; verify the believed 2011 CMA total before interpreting it.

## Known limitations

- The 2015 vector layers do not cover the 1-8 Dec peak; 2021/2023 reference maps are PDFs requiring manual digitising.
- Sentinel provisional peaks are not independently validated. All ten acquired products precede their provisional peaks: 2015 reference/event on 19 Oct/24 Nov, 2021 on 23 Oct/4 Nov, and 2023 on 18/30 Nov. The saved catalogue has a two-slice 16 Nov 2021 post-peak candidate; it has no post-peak 2015 or 2023 candidate. None of the downloaded products directly observes peak conditions.
- WorldPop R2025A is alpha and constrained; its roughly 6.2 million valid-cell-center sum is a model estimate, not census count, and nodata semantics do not tell whether every masked CMA cell is unsettled or missing.
- Reservoir event-window history is missing; the CWC advisory is a 2020 snapshot only.
- Dataset reuse terms differ; NRSC PDFs say “For official use”, and the CWC advisory's PDF-specific reuse terms were not found.
- Existing CMA boundary vintage may not match current administrative limits.
- No feature engineering, raster processing, model training, or outputs were created; Phase 3 has not started.

## Post-closure acquisition update — 13 October 2026

Kaggle Chennai Water Management, the six OpenCity monthly lake files, all nine distinct OpenCity Chennai flooding KML resources, Global Flood Database DFO event 4309, and the CAG executive summary were subsequently added and checked read-only. The executive summary is not the full audit report. The Global Flood Database event ends on 4 December 2015 and does not cover 5–8 December. The OpenCity return-period KMLs are modeled scenarios, not observed flood maps. Details and verification results are in DATA_MANIFEST.csv and DATA_QUALITY_REPORT.md. No Phase 3 processing was started.
