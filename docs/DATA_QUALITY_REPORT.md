# Phase 2 data-quality report

The pre-expansion CMA boundary has one valid MultiPolygon in CRS84. Rings are closed and pass a self-intersection check. Direct EPSG:32644 projection gives 1,187.46 km², within 10% of expected ~1,189 km². Bbox: 80.003904–80.345315°E, 12.851488–13.292414°N; approximate 2 km buffer: 79.984–80.365°E, 12.833–13.311°N.

| Dataset | Source | Period and resolution | CRS / CMA coverage | Gaps and quality notes | Licence |
|---|---|---|---|---|---|
| CMA boundary | Existing GeoJSON | Static vector | CRS84; full | 1 feature; 1,187.46 km² | CC BY 4.0 (repository statement; see Licences section) |
| UNOSAT 2015 | UNOSAT product 1039 | Imagery 1 Sep, 14 Oct, 12 Nov, 24 Nov 2015 | WGS84; 12 Nov flood polygons 7.1518% CMA; 24 Nov 8.2793%; footprint 100% each | Eight Polygon shapefiles; see inventory and `COVERAGE_2015.md`. The 12 Nov and 24 Nov layers precede the 1–2 Dec peak and do not represent it. Satellite-derived, not field-validated; SAR can miss water in dense urban areas. | CC BY-NC-SA 3.0 Unported (official product map; see Licences section) |
| NRSC 2021 | NRSC / ISRO | Image 13 Nov 2021; 1-page PDF | Map graphic; partial Chennai City taluk | Map 2021/16, event 15-FL-2021-TN; opens, needs manual digitising; “For official use” legend. | NRSC non-commercial terms; broader redistribution unclear |
| NRSC 2023 | NRSC / NDEM | 7 Dec northern Tamil Nadu map + 18 Dec Tuticorin map PDFs | Map sheets; both files open | Verified official NDEM PDFs downloaded. 7 Dec includes Chennai and target northern districts; 18 Dec covers Tuticorin only. Supplied NRSC URLs failed. Rapid products are preliminary, may include paddy-field standing water, have no ground verification, and say “For official use”. | NRSC non-commercial terms; broader redistribution unclear |
| Open-Meteo ERA5 | Open-Meteo | 9 points; 2015–2023 daily + event hourly; ~25 km | WGS84; point samples | Rain/temp/humidity/wind/pressure; units retained; no nulls. Coarse reanalysis, not gauge truth. | CC BY 4.0 data; free API non-commercial and rate limited |
| NASA POWER | NASA POWER | 9 points; daily 2015–2023 | WGS84; point samples / coarse native grid | 3,287 values per variable per point; no -999 markers. | NOT FOUND (POWER-specific licence) |
| ERA5 CDS | Copernicus CDS | Event + baseline, ~25 km hourly | Not collected | Account/API setup required. | Terms to record |
| GPM IMERG | NASA Earthdata | 86 daily V07B NetCDF files for 2015, 2021 and 2023 event windows; 0.1° grid | CF longitude/latitude; CMA values summarized in `RAIN_SOURCES_COMPARISON.md` | All expected dates present (45/20/21). Local files omit the variable `units` attribute; NASA GES DISC defines daily `precipitation` as mm/day. | Product-specific licence not confirmed; see Licences section |
| IMD rainfall | IMD | Event windows; station/grid dependent | Not collected | Data request and terms unresolved. | NOT FOUND (product-specific terms) |
| Copernicus GLO-30 | Copernicus DEM | ~30 m; four 1° tiles | EPSG:4326 horizontal / EGM2008 vertical; bbox+buffer tiles | 3600x3600 float32 COGs; DSM includes buildings/vegetation; no processing. | Copernicus terms in log |
| OSM roads/buildings/hydrology/infrastructure | Geofabrik / OpenStreetMap | Southern Zone snapshot, 557,975,955 bytes | WGS84; buffered CMA rectangle; 131,218 highway ways, 385,373 buildings, 816 waterways, 1,319 natural=water features, 254 reservoirs | Parsed full regional PBF; group counts can overlap, relations excluded, OSM completeness not assured; exact requested-name results and named-subset connectivity are in `OSM_WATERWAYS.md`. | ODbL 1.0 |
| ESA WorldCover | ESA WorldCover 2021 v200 | 2021, 10 m | EPSG:4326; N12E078 intersects buffered bbox | TIFF header/dimensions/tags checked; tile extends beyond CMA. | CC BY 4.0 |
| WorldPop | WorldPop R2025A alpha version | 2021 estimate, nominal ~100 m constrained | EPSG:4326; raster contains requested CMA bbox and boundary | One-band float32 GeoTIFF opens; 0.00083333333° pixels; 764,157,097 bytes. Valid pixel-center sum inside existing CMA boundary is ~6,204,904; 171 pixels are exactly zero, 23,812 are nodata, and 118,636 are positive. Nodata is -99999 and distinct from zero. This is a model estimate, not a census count. About 100 m cells are coarse for road-segment decisions. | CC BY 4.0 |
| Reservoir advisory | CWC | Public advisory PDF, 9 pages | PDF; partial Chembarambakkam/Poondi | Opens; dated 23 Nov 2020; not historical series. | NOT FOUND (PDF-specific reuse terms) |
| Reservoir series | TN WRD / CWC / India-WRIS | Current and 2015/2021/2023 desired | Not collected | Reviewed public pages did not yield Chennai-basin historical series. TN historical portal requires login+OTP; no login attempted. | NOT FOUND (no file acquired) |
| Sentinel catalogue | Copernicus STAC | Event windows + same-orbit pre-event references | WGS84 footprints calculated in EPSG:32644 | Catalogue query only; 8 event-window and 9 pre-event Sentinel-1 GRD IW catalog items intersect. ASF products were acquired separately; see next row. Adjacent slices are separate items. | Sentinel Data Legal Notice; full, free, open |
| Sentinel-1 ASF GRD-HD scenes | NASA ASF Vertex (user downloads) | 13 ZIPs, 2015/2021/2023 | Individual CMA coverage and date unions in `SENTINEL_VERIFICATION.md` | All 13 ZIPs pass integrity and SAFE metadata/name checks. | Copernicus Sentinel data are open; verify ASF product-specific terms before redistribution |
| CAG 2017 executive summary | CAG India | 2015 context, report 2017 | Saved at `data/raw/reservoirs/reference_docs/` | Executive summary opens as a 7-page PDF; full audit report not collected. | PDF-specific reuse terms not located |

## 2015 UNOSAT shapefile inventory

| Shapefile | Features | CRS / geometry | Bbox xmin,ymin,xmax,ymax | Imagery date |
|---|---:|---|---|---|
| LS8_20151014_PreFlood.shp | 4,608 | Polygon, WGS84 | 79.394312,12.142123,80.624381,14.020478 | 14 Oct 2015 |
| LS8_20151014_PreFlood_Analysis_Extent.shp | 1 | Polygon, WGS84 | 79.337270,11.955224,81.426648,14.057962 | 14 Oct 2015 |
| S1_20150901_PreFlood.shp | 36,415 | Polygon, WGS84 | 78.243539,11.638837,80.489776,13.380401 | 1 Sep 2015 |
| S1_20150901_PreFlood_Analysis_Extent.shp | 1 | Polygon, WGS84 | 78.164332,11.581167,80.411349,13.574359 | 1 Sep 2015 |
| S1_20151112_Flood.shp | 142,609 | Polygon, WGS84 | 78.294594,12.287095,80.920460,14.363126 | 12 Nov 2015 |
| S1_20151112_Flood_Analysis_Extent.shp | 1 | Polygon, WGS84 | 78.283155,12.180762,80.916646,14.235403 | 12 Nov 2015 |
| S1_20151124_Flood.shp | 88,684 | Polygon, WGS84 | 78.281668,12.339911,80.920829,14.239452 | 24 Nov 2015 |
| S1_20151124_Flood_Analysis_Extent.shp | 1 | Polygon, WGS84 | 78.283155,12.180762,80.916646,14.235403 | 24 Nov 2015 |

### Attribute columns and metadata

All eight feature classes are ESRI Polygon shape type 5 with WGS 84 geographic coordinates (the `.prj` files identify GCS_WGS_1984; XML metadata files are present for all eight). The thematic-layer schemas are:

| Layer(s) | Attribute columns (excluding geometry) | Notes |
|---|---|---|
| LS8_20151014_PreFlood.shp; S1_20150901_PreFlood.shp; S1_20151112_Flood.shp | `Water_Clas`, `Sensor_ID`, `Sensor_Dat`, `Confidence`, `Field_Vali`, `Water_Stat`, `Notes`, `Area_m2`, `Area_ha`, `SenorID_ol`, `StaffID`, `EventCode` | Categorical/sensor IDs are character fields; Sensor_Dat is date; area fields are numeric. |
| S1_20151124_Flood.shp | Same 12 column names as above | Water_Clas, Sensor_ID, Confidence, Field_Vali, Water_Stat, SenorID_ol, and StaffID are numeric in this layer; Notes/EventCode character, Sensor_Dat date, areas numeric. |
| LS8_20151014_PreFlood_Analysis_Extent.shp; S1_20150901_PreFlood_Analysis_Extent.shp; S1_20151112_Flood_Analysis_Extent.shp | `SensorDate`, `SensorID`, `Notes`, `Area_m2`, `StaffID`, `EventCode`, `Area_ha` | The XML geoprocessing metadata and SensorDate values identify 14 Oct 2015, 1 Sep 2015, and 12 Nov 2015 respectively. |
| S1_20151124_Flood_Analysis_Extent.shp | Same 7 column names as above | SensorDate metadata identifies 24 Nov 2015; SensorID and StaffID numeric in this layer. |

XML metadata documents each layer's source/export and processing; imagery dates are established by layer names and SensorDate/Sensor_Dat attributes, not inferred from archive folder name. No one of these eight layers is a December 1–8 peak observation.

Flood-layer bounding boxes extend beyond and contain CMA bounds, but do not mean all CMA locations are mapped as flooded. Dissolved flooded-polygon and separate analysis-footprint percentages were computed in memory; see `COVERAGE_2015.md`.

## Known limitations

1. UNOSAT 2015 12 Nov and 24 Nov layers precede the 1–2 Dec peak and do not by themselves represent the peak. Flood extents are satellite-derived, not field-validated; SAR struggles in dense urban areas.
2. NRSC rapid products are preliminary and may include paddy-field standing water. The 2021 PDF needs manual digitising. The official 2023 NDEM map is held, but has no ground verification and may include standing paddy/rain water.
3. Sentinel revisit gaps may miss flood peaks; imagery is mainly for label generation.
4. WorldPop R2025A is identified as an alpha version; its approximately 100 m cells are coarser than road-segment decisions. The CMA sum excludes 23,812 nodata pixel centers and is a model estimate, not a census count.
5. Historical reservoir release time series remain a major data gap.
6. Gaps include no December 2015 layer, failure of the supplied NRSC 2023 URLs, CAG TLS connection closure, and 23,812 WorldPop nodata centers. The user-supplied complete WorldPop raster was verified; earlier incomplete transfer attempts were not retained.
7. ERA5/POWER are coarse reanalysis, not gauge observations; multiple point requests may share cells.

### WorldPop R2025A population caveat and nodata review

WorldPop R2025A is an alpha, constrained product. The sum inside the CMA (about 6.2 million) appears lower than the 2011 census total for the CMA, which is believed to be about 8.6-8.7 million (to be verified against census sources). Use it for relative exposure patterns, not as an absolute headcount.

Read-only counts use pixel centers within the existing CMA boundary: 171 values are exactly 0, 23,812 are the raster's declared NoData value (-99999), and 118,636 are positive. The stored NoData sentinel is distinct from a zero-population value. WorldPop's R2025A release statement describes ocean and major inland waterbodies as NoData, while its constrained methodology allocates estimates only to cells mapped as built settlements ([release statement](https://data.worldpop.org/repo/prj/Global_2015_2030/R2025A/doc/Global2_Release_Statement_R2025A_v1.pdf), [constrained methodology](https://www.worldpop.org/methods/top_down_constrained_vs_unconstrained/)). A read-only nearest-cell comparison with ESA WorldCover at the NoData centers found mixed classes, including water, cropland, vegetation, and 150 built-up samples. The raster therefore identifies these cells as intentionally masked NoData rather than encoded zeros, but the value alone cannot establish whether each CMA cell is genuinely unsettled, excluded by water/settlement masks, or a settlement omission. Do not treat these NoData cells as zero population or claim their exact land-use meaning without further source-specific validation.

## December 2015 official product check

The official Bhuvan flood viewer lists Tamil Nadu products dated 03/12/2015-06Hr, 04/12/2015, 05/12/2015, 05-07/12/2015 and 08/12/2015-18Hr, plus “chennai floods (Experimental Product)” with cumulative RISAT-1 inundation (3, 4, 6 Dec 2015). The linked product entries open a viewer via “Click here to zoom”; this run did not establish a public direct data-file link. No December flood layer was saved. The Bhuvan page also links NRSC's 07 Dec hydrological simulation report; it describes an approximate modeled scenario, not a machine-readable observed inundation polygon. Manual access/request steps are in `MANUAL_TODO.md`.

## 2015 archive attribute fields

The archive's shapefile attribute schema includes `Water_Clas`, `Sensor_ID`, `Sensor_Dat`, `Confidence`, `Field_Vali`, `Water_Stat`, `Notes`, `Area_m2`, `Area_ha`, `SenorID_ol`, `StaffID`, and `EventCode` (fields vary across layers). Names/attributes identify imagery dates: 1 Sep, 14 Oct, 12 Nov, and 24 Nov 2015. The four `*_Analysis_Extent` layers represent analysis footprints, not flood extents. No December 1–8 peak layer appears among the archive's eight layers.

## Sentinel-1 catalogue timing

The public STAC catalog was queried on 2026-10-08; its shortlist and timing gaps are in `SENTINEL_PLAN.md` and `SENTINEL_SHORTLIST.csv`. On 2026-10-14, 13 Sentinel-1A GRD-HD ZIPs manually downloaded from NASA ASF Vertex were verified in place. Detailed hashes, ZIP integrity, SAFE metadata, metadata/name checks, and CMA coverage are in `SENTINEL_VERIFICATION.md`. The raw folder is intentionally spelled `senitnel1`; it has not been renamed. The 6 Dec 2015 scene is within the 1–8 Dec flood window and has a 100% CMA footprint, but it has not been processed and is not a flood label. Two 16 Nov 2021 ZIPs are post-peak; neither they nor any other Sentinel scenes were processed in Part B.

All 13 ZIPs pass `zipfile.testzip()` and their names match acquisition start/stop times in SAFE metadata. They are IW mode, VV+VH, relative orbit 92, descending. Acquired slices on the same date have matching orbit, direction, and polarisation. Individually, paired 2021 and 2023 slices cover nearly all the CMA. ASF download licence terms remain to be confirmed before redistribution. The 6 Dec 2015 raw scene requires careful processing and temporal/context validation before any flood interpretation.

## Licences and attribution

Terms checked against primary or provider pages on 8 October 2026. “NOT FOUND” means reuse rights for the specific file were not established; verify before redistribution.

| Dataset | Licence or terms | Attribution text required | URL | Confidence |
|---|---|---|---|---|
| Chennai CMA boundary (DataMeet Municipal Spatial Data) | CC BY 4.0 per repository data-licence statement; separate LICENSE file not identified. | “<dataset> by DataMeet India community (CC BY 4.0)” and repository link. | [Municipal_Spatial_Data](https://github.com/datameet/Municipal_Spatial_Data) | Medium |
| UNOSAT 2015 flood product | CC BY-NC-SA 3.0 Unported stated on official map; HDX-specific terms not independently verified. | UNITAR-UNOSAT; cite product 1039 and retain licence notice. | [UNOSAT product 1039](https://unosat.org/products/1039) | Medium |
| NRSC/NDEM 2021 and 2023 maps | NRSC site terms allow non-commercial use with attribution, but PDFs say “For official use”; public republication rights unclear. | “Source: NRSC, ISRO/DOS”; seek permission before redistribution. | [NRSC Terms](https://www.nrsc.gov.in/nrscnew/termsConditions.php); [Bhuvan Terms](https://bhuvan.nrsc.gov.in/home/index.php/newsletter.php) | Medium-low |
| CWC reservoir advisory PDF | NOT FOUND: no PDF-specific reuse licence located. | Credit Central Water Commission; attribution does not establish permission. | [CWC advisory PDF](https://cwc.gov.in/sites/default/files/advisory-chembarambakkam-and-poondi-reservoir.pdf) | Low |
| Open-Meteo | CC BY 4.0 for data; free API tier is non-commercial and rate-limited. | Attribute Open-Meteo and underlying model/data source. | [Open-Meteo Terms](https://open-meteo.com/en/terms) | High |
| NASA POWER | NOT FOUND: no POWER-specific licence identified; NASA requests source citation. | Cite NASA POWER and its data source; verify before redistribution. | [NASA POWER FAQs](https://power.larc.nasa.gov/docs/faqs/data/) | Low |
| Copernicus DEM GLO-30 | Copernicus DEM public-use licence terms; preserve required DLR/Airbus/Copernicus notice. | `© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.` | [DEM collection](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM); [licence PDF](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf) | High |
| Copernicus Sentinel data | Free, full and open under the Sentinel data legal notice. | “Contains modified Copernicus Sentinel data [year]” or “Copernicus Sentinel data [year]”. | [Sentinel Data Legal Notice](https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice) | High |
| OpenStreetMap / Geofabrik | ODbL 1.0; attribution and share-alike apply to qualifying adapted databases. | “© OpenStreetMap contributors” with OSM copyright/licence; credit Geofabrik extract. | [OSM copyright](https://www.openstreetmap.org/copyright); [Geofabrik Southern Zone](https://download.geofabrik.de/asia/india/southern-zone.html) | High |
| ESA WorldCover | CC BY 4.0 according to project terms. | Credit ESA WorldCover 2021 and cite project. | [WorldCover](https://worldcover2021.esa.int/) | Medium |
| WorldPop R2025A | CC BY 4.0 per product/release; explicitly alpha version. | Attribute WorldPop and cite R2025A release. | [R2025A release statement](https://data.worldpop.org/repo/prj/Global_2015_2030/R2025A/doc/Global2_Release_Statement_R2025A_v1.pdf) | Medium |
| Reservoir series | NOT FOUND: no Chennai-basin time-series file acquired and no file-specific terms available. | Not established. | [CWC NWDP reservoir dataset](https://nwdp.nwic.gov.in/en/dataset/reservoir-water-level-manual-daily-centre-water-commission_cwc) | Low |
| ERA5 / C3S | Copernicus data policy applies; preserve product citation. No file acquired. | Credit Copernicus Climate Change Service (C3S) and ERA5. | [Climate Data Store](https://cds.climate.copernicus.eu/) | Medium |
| GPM IMERG / NASA | 86 V07B daily files acquired; product-specific licence not verified. NASA requests citation. | Cite NASA GPM IMERG and product version; confirm the terms for the accessed product. | [NASA Earthdata data-use policy](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy) | Low |
| IMD rainfall | NOT FOUND: no product-specific terms verified; no file acquired. | Confirm with selected IMD product. | [IMD](https://mausam.imd.gov.in/) | Low |
| CAG 2017 full audit report | NOT FOUND: full-report reuse terms not verified; the full report remains uncollected. Its executive summary is collected separately. | Credit CAG and cite official report if obtained. | [Official CAG report URL](https://www.cag.gov.in/uploads/download_audit_report/2017/Report_No_4_of_2017_-_Performance_Audit_of_Flood_Management_and_Response_in_Chennai_and_its_Suburban_Area.pdf) | Low |

These entries summarize source terms, not legal advice. Product-specific notices in source files take precedence.

### Additional downloads checked on 13 October 2026

| Dataset | Licence or terms | Attribution / use note | Source |
|---|---|---|---|
| Kaggle Chennai Water Management | CC0 1.0 Universal, as shown in the user-provided Kaggle licence screenshot. | Public-domain dedication; cite the dataset page for provenance. | [Kaggle dataset](https://www.kaggle.com/sudalairajkumar/chennai-water-management) |
| OpenCity Chennai lake levels | Other (Public Domain), as listed by OpenCity. | Source listed as CMWSSB. | [OpenCity dataset](https://data.opencity.in/dataset/chennai-lake-leves-since-2003) |
| OpenCity Chennai Flooding Data | Other (Public Domain), as listed by OpenCity. | Source listed as GCC; resource page credits Vaidyanathan R. | [OpenCity dataset](https://data.opencity.in/dataset/chennai-flooding-data) |
| Global Flood Database DFO 4309 | CC BY-NC 4.0 per the README inside the downloaded archive. | Non-commercial terms apply; cite Cloud to Street / Dartmouth Flood Observatory and the dataset paper. | [GFD event explorer](https://global-flood-database.cloudtostreet.info/#interactive-map); [Earth Engine catalogue](https://developers.google.com/earth-engine/datasets/catalog/GLOBAL_FLOOD_DB_MODIS_EVENTS_V1) |
| CAG 2017 executive summary | PDF-specific reuse terms not located. | Cite CAG Report No. 4 of 2017; do not infer redistribution permission. | [Official CAG report page](https://cag.gov.in/en/audit-report/details/45722) |



## Download verification — 13 October 2026

User-acquired downloads were checked read-only. Raw datasets were not extracted, renamed, edited, or resaved. Browser file modification times are used as local download-time evidence. File sizes and SHA-256 values are in the raw download logs and DATA_MANIFEST.csv.

- **Kaggle reservoir archive:** archive.zip passes the ZIP CRC check and contains two CSVs. Each has 6,182 daily rows from 1 Jan 2004 through 3 Dec 2020, with no missing or duplicate dates and no blank cells. Reservoir storage is described in mcft. The archive does not document rainfall units; do not assume them. The Kaggle licence page shown by the user identifies CC0 1.0 Universal.
- **OpenCity lake levels:** six CSVs are present. Five cover 2003–2021 monthly; Kannankottai covers 2020–2021 and has 11 blank month cells. The page describes values as mcft and readings on the first of each month. These are storage data, not releases, and too coarse for event-day operations. OpenCity lists the dataset as Public Domain.
- **OpenCity Chennai Flooding Data:** all nine expected KML resources are now present, each with distinct content, and all parse as XML. They include two point layers, return-period hazard scenarios, and a hazard-zone classification. Return-period layers are modelled scenarios, not observed 2015 flood extents. No inundated-area statistic was inferred from these KMLs.
- **Global Flood Database:** ZIP check passes; archive contains GeoTIFF, README, licence, and metadata. Event metadata identifies DFO 4309 (India), 10 Nov–4 Dec 2015. GeoTIFF is EPSG:4326, five bands, nominal 250 m pixels, 3-day MODIS composites. With the existing CMA boundary and pixel-centre inclusion, 1,082 flooded-band cells occur in the CMA; 195 overlap the permanent-water band. Excluding that overlap leaves 887 cells, approximately 53.7 km2 using nominal local pixel area. This is a coarse grid estimate, not a high-resolution boundary-clipped measurement. It ends 4 Dec and does not cover 5–8 Dec. The archive README states CC BY-NC 4.0.
- **CAG executive summary:** downloaded PDF opens as an unencrypted seven-page document. The summary reports Chembarambakkam Tank discharge of 20,960–29,000 cusecs and states 29,000 cusecs for 21 hours on 1–2 Dec 2015. These are audit findings, not a complete timestamped reservoir series. No release figures for Poondi, Puzhal/Red Hills, or Cholavaram were identified in the summary. The full CAG audit report was not downloaded; PDF-specific reuse terms were not located.

Archive/PDF checks establish readability, not scientific accuracy. Phase 3 feature-preparation outputs have now been generated; this does not mean flood labels are final or a model has been trained.

## Raw-data log reconciliation — 14 October 2026

The current `data/raw` tree contains 58 data files (17,775,232,566 bytes) and 18 download logs. A read-only check recomputed SHA-256 and byte sizes for all 58 files: 58 matched, 0 mismatches, and 0 current files lacked a comparable logged hash. Failed historical attempts with zero-byte/not-applicable hash entries are not present files. All 13 Sentinel ZIP records are in `data/raw/satellite/senitnel1/DOWNLOAD_LOG.txt`.

## Phase 3 feature preparation — 14 October 2026

The 30 m EPSG:32644 grid, exploratory terrain and land-cover features, sum-resampled WorldPop surface, hourly weather and reservoir tables, OSM vector layers, exposure buffers, and flood-label inspection layers are described in `PHASE3_LOG.md` and `FEATURE_DICTIONARY.md`. All 18 checked rasters align to the master grid and contain valid cells. Five existing exploratory label rasters are tiled GeoTIFFs but not COGs; they were preserved without rewriting. They are not final flood labels. Raw data remained unchanged in the audit.

WorldPop 30 m buffer sums are proximity estimates only: 6,072,870.5 model-count units within 100 m of mapped roads and 5,126,819.5 within the union of 500 m mapped facility buffers. The buffered areas overlap and must not be interpreted as people on roads, unique evacuation demand, or service reach. Both derive from the alpha constrained WorldPop product.
# Phase 3 processing note — 2026-10-14

The approved Phase 3 pass uses a provisional older-CMA, EPSG:32644, 30 m grid with a 2 km rectangular buffer. See `GRID_DECISION.md`. New feature outputs are derived copies; source files under `data/raw` remain read-only.

- Copernicus GLO-30 is a DSM. The 30 m CMA output spans about -64.51 to 168.70 m and reaches a 53.19° maximum slope. Negative coastal values and a high D8 sink count (121,883 CMA cells) need map inspection and hydrologic conditioning before operational use. The current D8 products are unconditioned exploratory derivatives. Height-above-drainage was not generated because no suitable hydrology package is installed.
- WorldCover 2021 class and area-fraction rasters are on the 30 m grid. Mean CMA class fractions are in `data/features/landcover/class_area_fraction_means_cma.json`. WorldCover built-up area is only a land-cover proxy; it is not a direct imperviousness measurement.
- WorldPop 30 m sum-resampling gives a CMA total of 6,203,811 (about 6.2 million), about 0.018% below the earlier native-grid pixel-centre estimate of 6,204,904. This small difference reflects different reprojection/grid aggregation and boundary inclusion methods and should be checked before publishing. It is an alpha constrained model product, not a census. The output grid has 194,961 CMA nodata cells and 1,010 valid zero-count cells; these are 30 m grid cells, not the previous 100 m native-cell counts. Do not interpret nodata as zero population.
- Rainfall features have 18,576 hourly rows across nine ERA5 locations and three event-window files; no within-event hourly gaps were found. Across 3,287 dates, daily nine-point means give ERA5 versus NASA POWER Pearson r=0.763, mean ERA5-minus-POWER bias=-0.677 mm/day, and RMSE=6.597 mm/day. The local NASA POWER JSON metadata declares `PRECTOTCORR` in mm/day. These gridded/model-based products are not ground gauges.
- Reservoir storage tidy output covers 2004-01-01 through 2020-12-03; four daily reservoirs and six monthly OpenCity series are represented. No storage change is a release measurement. The illustrative 2015 Track B screen uses current public capacities and has five pre-1-Dec alert dates (Nov 20–24), an earliest 11-day lead, and 11 alert days over the rainfall-overlap data; six alert days fall outside the target pre-event window. With no full daily flood outcome record, those cannot be called validated false alarms. It is not an operational warning model.
- The CAG executive summary states (paragraph 5.8.5) that on 1 Dec 2015 storage at Chembarambakkam was 3.481 TMC of 3.645 TMC and describes releases of 20,960–29,000 cusecs, including 29,000 cusecs for 21 hours across 1–2 Dec. This is a summary-level statement, not a daily release time series; retain the original PDF and verify against the complete audit report before detailed hydrologic use.
- Exploratory UNOSAT masks include only Sep 1/Oct 14 references and Nov 12/Nov 24 2015 events. A basic Nov-minus-reference test reduces the union area from 126.39 to 80.59 km², but uncertain wet-soil pre-flood classes make that subtraction unvalidated. The Dec 1–8 peak remains unlabelled by the collected vector layers.
- Global Flood Database event 4309 has 1,082 flooded native-grid pixel centres inside the CMA, corresponding to about 65.43 km² using the approximate cell area at the CMA latitude. It is a coarse ~250 m MODIS event surface for a broader Nov 10–Dec 4 event; its centroid is outside Chennai. Treat it as a coarse regional overlap, not a Chennai-specific verified label.
- OpenCity KML incident points and modeled return-period polygons are inventoried separately. Modeled hazard zones are not observed flood extents. The original KML datasets have invalid geometries; per-feature intersection checks completed without failed predicates.

