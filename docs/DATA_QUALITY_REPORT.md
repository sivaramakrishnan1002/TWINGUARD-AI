# Phase 2 data-quality report

The pre-expansion CMA boundary has one valid MultiPolygon in CRS84. Rings are closed and pass a self-intersection check. Direct EPSG:32644 projection gives 1,187.46 km², within 10% of expected ~1,189 km². Bbox: 80.003904–80.345315°E, 12.851488–13.292414°N; approximate 2 km buffer: 79.984–80.365°E, 12.833–13.311°N.

| Dataset | Source | Period and resolution | CRS / CMA coverage | Gaps and quality notes | Licence |
|---|---|---|---|---|---|
| CMA boundary | Existing GeoJSON | Static vector | CRS84; full | 1 feature; 1,187.46 km² | LICENCE NOT FOUND |
| UNOSAT 2015 | UNOSAT product 1039 | Imagery 1 Sep, 14 Oct, 12 Nov, 24 Nov 2015 | WGS84; 12 Nov flood polygons 7.1518% CMA; 24 Nov 8.2793%; footprint 100% each | Eight Polygon shapefiles; see inventory and `COVERAGE_2015.md`. The 12 Nov and 24 Nov layers precede the 1–2 Dec peak and do not represent it. Satellite-derived, not field-validated; SAR can miss water in dense urban areas. | LICENCE NOT FOUND |
| NRSC 2021 | NRSC / ISRO | Image 13 Nov 2021; 1-page PDF | Map graphic; partial Chennai City taluk | Map 2021/16, event 15-FL-2021-TN; opens, needs manual digitising. | LICENCE NOT FOUND |
| NRSC 2023 | NRSC / NDEM | 7 Dec northern Tamil Nadu map + 18 Dec Tuticorin map PDFs | Map sheets; both files open | Verified official NDEM PDFs downloaded after elevated retry. 7 Dec includes Chennai and target northern districts; 18 Dec covers Tuticorin only. Supplied NRSC URLs had prior 404 and current proxy failures. Rapid products are preliminary, may include paddy-field standing water, and have no ground verification. | LICENCE NOT FOUND |
| Open-Meteo ERA5 | Open-Meteo | 9 points; 2015–2023 daily + event hourly; ~25 km | WGS84; point samples | Rain/temp/humidity/wind/pressure; units retained; no nulls. Coarse reanalysis, not gauge truth. | Terms in log |
| NASA POWER | NASA POWER | 9 points; daily 2015–2023 | WGS84; point samples / coarse native grid | 3,287 values per variable per point; no -999 markers. | API docs in log |
| ERA5 CDS | Copernicus CDS | Event + baseline, ~25 km hourly | Not collected | Account/API setup required. | Terms to record |
| GPM IMERG | NASA Earthdata | Event windows, ~10 km product dependent | Not collected | Earthdata login required. | Terms to record |
| IMD rainfall | IMD | Event windows; station/grid dependent | Not collected | Data request and terms unresolved. | LICENCE NOT FOUND |
| Copernicus GLO-30 | Copernicus DEM | ~30 m; four 1° tiles | EPSG:4326 horizontal / EGM2008 vertical; bbox+buffer tiles | 3600x3600 float32 COGs; DSM includes buildings/vegetation; no processing. | Copernicus terms in log |
| OSM roads/buildings/hydrology/infrastructure | Geofabrik / OpenStreetMap | Southern Zone snapshot, 557,975,955 bytes | WGS84; buffered CMA rectangle; 131,218 highway ways, 385,373 buildings, 816 waterways, 1,319 natural=water features, 254 reservoirs | Parsed full regional PBF; group counts can overlap, relations excluded, OSM completeness not assured; named watercourses not yet exactly verified. | ODbL 1.0 |
| ESA WorldCover | ESA WorldCover 2021 v200 | 2021, 10 m | EPSG:4326; N12E078 intersects buffered bbox | TIFF header/dimensions/tags checked; tile extends beyond CMA. | CC BY 4.0 |
| WorldPop | WorldPop R2025A | 2021 estimate, ~100 m constrained | EPSG:4326; not downloaded | Transfer stalled at 112,704,318 bytes and the partial was removed; no raster to inspect. Advertised size about 728.76 MB. Cells coarse versus road decisions. | CC BY 4.0 |
| Reservoir advisory | CWC | Public advisory PDF, 9 pages | PDF; partial Chembarambakkam/Poondi | Opens; not historical series. | LICENCE NOT FOUND |
| Reservoir series | TN WRD / CWC / India-WRIS | Current and 2015/2021/2023 desired | Not collected | TN portal login+OTP; open historical releases not found. | LICENCE NOT FOUND |
| Sentinel catalogue | Copernicus STAC | Events + previous 30 days | WGS84; intersecting bbox | 27 rows: 17 S1 IW, 10 S2 L2A <40% cloud. No scenes downloaded. S1 date gaps 7/3/4 days to proxy peak dates. | Copernicus terms |
| CAG report | CAG India | 2015 context, report 2017 | Not saved | Official hosts timed out. | LICENCE NOT FOUND |

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
4. WorldPop ~100 m cells are coarser than road-segment decisions.
5. Historical reservoir release time series remain a major data gap.
6. Gaps include Overpass failures, CAG timeout, WorldPop transfer stall, failure of the supplied NRSC 2023 URLs, and no December 2015 layer obtained.
7. ERA5/POWER are coarse reanalysis, not gauge observations; multiple point requests may share cells.

## December 2015 official product check

The official Bhuvan flood viewer lists Tamil Nadu products dated 03/12/2015-06Hr, 04/12/2015, 05/12/2015, 05-07/12/2015 and 08/12/2015-18Hr, plus “chennai floods (Experimental Product)” with cumulative RISAT-1 inundation (3, 4, 6 Dec 2015). The linked product entries open a viewer via “Click here to zoom”; this run did not establish a public direct data-file link. No December flood layer was saved. The Bhuvan page also links NRSC's 07 Dec hydrological simulation report; it describes an approximate modeled scenario, not a machine-readable observed inundation polygon. Manual access/request steps are in `MANUAL_TODO.md`.

## 2015 archive attribute fields

The archive's shapefile attribute schema includes `Water_Clas`, `Sensor_ID`, `Sensor_Dat`, `Confidence`, `Field_Vali`, `Water_Stat`, `Notes`, `Area_m2`, `Area_ha`, `SenorID_ol`, `StaffID`, and `EventCode` (fields vary across layers). Names/attributes identify imagery dates: 1 Sep, 14 Oct, 12 Nov, and 24 Nov 2015. The four `*_Analysis_Extent` layers represent analysis footprints, not flood extents. No December 1–8 peak layer appears among the archive's eight layers.

## Sentinel-1 catalogue timing

For the provisional 1–3 Dec 2015 peak window (peak reference date 1 Dec, to be validated), the nearest Sentinel-1 pass in the existing catalogue is 24 Nov 2015 at 00:31:20 UTC, **7 days before 1 Dec** and **9 days before 3 Dec**. This is only a catalogue candidate; it does not observe the 1–3 Dec peak. The CSV has no later December 2015 pass in its queried results. The 2021 and 2023 proxy dates also remain provisional/to be validated.
