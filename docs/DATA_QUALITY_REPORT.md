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
| GPM IMERG | NASA Earthdata | Event windows, ~10 km product dependent | Not collected | Earthdata login required. | Terms to record |
| IMD rainfall | IMD | Event windows; station/grid dependent | Not collected | Data request and terms unresolved. | NOT FOUND (product-specific terms) |
| Copernicus GLO-30 | Copernicus DEM | ~30 m; four 1° tiles | EPSG:4326 horizontal / EGM2008 vertical; bbox+buffer tiles | 3600x3600 float32 COGs; DSM includes buildings/vegetation; no processing. | Copernicus terms in log |
| OSM roads/buildings/hydrology/infrastructure | Geofabrik / OpenStreetMap | Southern Zone snapshot, 557,975,955 bytes | WGS84; buffered CMA rectangle; 131,218 highway ways, 385,373 buildings, 816 waterways, 1,319 natural=water features, 254 reservoirs | Parsed full regional PBF; group counts can overlap, relations excluded, OSM completeness not assured; exact requested-name results and named-subset connectivity are in `OSM_WATERWAYS.md`. | ODbL 1.0 |
| ESA WorldCover | ESA WorldCover 2021 v200 | 2021, 10 m | EPSG:4326; N12E078 intersects buffered bbox | TIFF header/dimensions/tags checked; tile extends beyond CMA. | CC BY 4.0 |
| WorldPop | WorldPop R2025A alpha version | 2021 estimate, nominal ~100 m constrained | EPSG:4326; raster contains requested CMA bbox and boundary | One-band float32 GeoTIFF opens; 0.00083333333° pixels; 764,157,097 bytes. Valid pixel-center sum inside existing CMA boundary is ~6,204,904; 171 pixels are exactly zero, 23,812 are nodata, and 118,636 are positive. Nodata is -99999 and distinct from zero. This is a model estimate, not a census count. About 100 m cells are coarse for road-segment decisions. | CC BY 4.0 |
| Reservoir advisory | CWC | Public advisory PDF, 9 pages | PDF; partial Chembarambakkam/Poondi | Opens; dated 23 Nov 2020; not historical series. | NOT FOUND (PDF-specific reuse terms) |
| Reservoir series | TN WRD / CWC / India-WRIS | Current and 2015/2021/2023 desired | Not collected | Reviewed public pages did not yield Chennai-basin historical series. TN historical portal requires login+OTP; no login attempted. | NOT FOUND (no file acquired) |
| Sentinel catalogue | Copernicus STAC | Event windows + same-orbit pre-event references | WGS84 footprints calculated in EPSG:32644 | 8 event-window and 9 pre-event Sentinel-1 GRD IW catalog items intersect; no images downloaded. Adjacent slices are separate items. See `SENTINEL_PLAN.md` and CSV. | Sentinel Data Legal Notice; full, free, open |
| CAG report | CAG India | 2015 context, report 2017 | Not saved | Official retry failed with SSL connection closed; see `ISSUES.md`. | NOT FOUND (report-specific reuse terms) |

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

The public STAC catalog was queried on 2026-10-08; scene metadata, full product sizes, same-orbit reference scenes, footprint percentages, and timing gaps are in `SENTINEL_PLAN.md` and `SENTINEL_SHORTLIST.csv`. Provisional peaks remain to be validated. No scene products were downloaded.

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
| GPM IMERG / NASA | NOT FOUND: no product-specific licence verified; NASA requests citation. No file acquired. | Cite NASA GPM IMERG and product version; verify terms. | [NASA Earthdata data-use policy](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy) | Low |
| IMD rainfall | NOT FOUND: no product-specific terms verified; no file acquired. | Confirm with selected IMD product. | [IMD](https://mausam.imd.gov.in/) | Low |
| CAG 2017 report | NOT FOUND: report-specific reuse terms not verified; official retry failed. | Credit CAG and cite official report if obtained. | [Official CAG report URL](https://www.cag.gov.in/uploads/download_audit_report/2017/Report_No_4_of_2017_-_Performance_Audit_of_Flood_Management_and_Response_in_Chennai_and_its_Suburban_Area.pdf) | Low |

These entries summarize source terms, not legal advice. Product-specific notices in source files take precedence.
