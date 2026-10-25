# Flood-map georeferencing and digitising guide

## Inventory and feasibility

The PDF check is read-only. Extracted native embedded images and low-resolution page previews are under `data/processed/pdf_maps/`; sources in `data/raw/` were not changed. The December 2015 map directory is absent, so no December PDF was inspected.

| Map | Observed contents | Graticule and legend | Automatic georeferencing decision |
|---|---|---|---|
| 2021 NRSC `ChennaiCity-ChennaiCorporationTaluk-4.pdf` | One page; NRSC map issued 14 Nov 2021; 6 embedded images. Six `/VP` viewports contain `/Measure /Subtype /GEO` and GPTS coordinates. | No printed lat/lon tick labels were visible on the map frames. Flooded locations are called out with “Inundated area” annotations/arrows over pre/during SAR imagery; there is no simple area-colour swatch for the whole image. | **Conditional only.** GeoPDF data exist, but the main viewports' WKT advertises WGS 84 UTM 45N while GPTS values look like degrees around 13 N, 80 E; inset viewports also use Everest/modified-Lambert definitions. Verify parsed coordinates against OSM controls before trusting. Prefer the embedded transform only if QGIS interprets it consistently and independent check points meet the RMS criterion. |
| 2023 Michaung `tncyclone50dsc07122023_0600hrs_map.pdf` | Two pages; NRSC/ISRO citation and NDEM logo; Map IDs 2023/CY/TN/01a and 01b; 24 embedded images. Three `/GEO` viewports per page; the map frames identify WGS 84 geographic coordinates. | No printed coordinate tick labels were visible. The map legend uses red fill for “Flood / Standing Water due to Rains”; district boundaries are outlined. Map disclaimer says preliminary and no ground verification. | **Feasible with validation.** GeoPDF coordinates are consistent WGS 84 geographic values, so QGIS/ GDAL should be able to honor the embedded transform. Verify against independent controls and do not treat the map as field truth. The map is NRSC/ISRO and carries an NDEM logo; the PDF text does not name an “NDEM PDF” product separately. |
| December 2015 | `data/raw/historical_floods/2015/december_maps` is absent. | Not inspected. | Pending; no source to georeference. |

Inspection evidence: `docs/PDF_MAP_INSPECTION.json`. Native extracted image dimensions and SHA-256 hashes are recorded there. Page previews are for visual inspection only and are not GIS outputs.

## Candidate control points

Candidate positions below come from `data/features/facilities/chennai_facilities.gpkg` (OSM-derived, EPSG:32644). Coordinates are offered as **candidate references**, not certified control points; digitisers must confirm each named landmark is visible and unambiguous in the map frame. The map and source feature dates may differ. Do not force a point match just to obtain a low RMS.

### 2021 NRSC map, page 1 local Chennai frame

| Candidate feature (OSM) | EPSG:4326 lon, lat | EPSG:32644 easting, northing (m) |
|---|---|---|
| Otteri platform | 80.251382, 13.097209 | 418848.48, 1448005.87 |
| Vyasarpadi Jeeva stop position | 80.258128, 13.109088 | 419583.60, 1449317.47 |
| Deepam Muthu Hospital | 80.260530, 13.099585 | 419840.98, 1448265.79 |
| Jamalia stop position | 80.249355, 13.106402 | 418631.73, 1449023.23 |
| Binny Mills platform | 80.252645, 13.102336 | 418987.01, 1448572.53 |
| A1 Beef Stall | 80.255308, 13.098698 | 419274.55, 1448169.29 |
| Brothers Cafe | 80.258097, 13.097319 | 419576.44, 1448015.88 |
| Mettupalayam platform | 80.253177, 13.105056 | 419045.60, 1448873.15 |
| Pattalam Clock Tower | 80.260525, 13.097063 | 419839.61, 1447986.86 |
| P2 Otteri Police Station | 80.251563, 13.100330 | 418869.14, 1448350.95 |

The PDF names Otteri Nala, ESI Government Staff Quarters, Centre of Indian Trade Union, Buckingham Carnatic Mills and Corporation Primary School. Where an OSM point is absent or not a definite one-to-one match, digitise a visible road junction/stream crossing from the map and use its OSM geometry only after visually identifying that same junction. Do not substitute the nearby candidate name blindly.

### 2023 Michaung regional map, Chennai/CMA area

| Candidate feature (OSM) | EPSG:4326 lon, lat | EPSG:32644 easting, northing (m) |
|---|---|---|
| Suriya Ayurveda Hospital | 80.056094, 12.858863 | 397579.84, 1421715.82 |
| Madha Engineering College | 80.086138, 12.992868 | 400892.96, 1436524.72 |
| Velammal Vidyalaya Paruthipattu | 80.118180, 13.088063 | 404404.67, 1447040.90 |
| R B Gothi Jain College For Women | 80.194000, 13.194593 | 412662.30, 1458795.46 |
| Attipattu Pudunagar station | 80.300008, 13.249104 | 424166.65, 1464789.63 |
| Chokani Jetty | 80.299891, 13.097305 | 424107.15, 1448001.45 |
| St. Joseph Higher Secondary School | 80.252817, 12.938573 | 418952.53, 1430461.09 |
| Baby Child Clinic | 80.184499, 12.890230 | 411524.56, 1425137.24 |
| Peoples Nursing Home, Chennai | 80.215950, 13.069630 | 414997.91, 1444967.37 |

These are widely spaced candidates from the CMA facility layer. Because the NRSC map is at district scale, use them only if the corresponding feature is actually identifiable in the sheet; otherwise use visible district/coastline/road junctions from the project OSM layers. The map's own GeoPDF transform is the preferred starting point.

## Transformation and acceptance

1. In QGIS, open the original PDF directly if the installed GDAL/PDF driver exposes its GeoPDF frames. Choose the named main event map frame, not the locator inset or page layout. Inspect layer CRS, corner coordinates and the graticule/GPTS relationship.
2. For the 2023 sheet, honor the embedded WGS 84 transform, then reproject to EPSG:32644. Independently check 8–10 well-distributed visible OSM controls.
3. For the 2021 sheet, first test the embedded frame and its conflicting WKT/GPTS. If QGIS cannot produce consistent positions, use 8–10 manually matched, well-distributed controls and a first-order affine transform for a rectified north-up map frame. Use a projective transform only if the frame itself is demonstrably skewed. Do not warp the whole page layout as one map.
4. Target independent-check RMS <=30 m (one 30 m grid cell) for Tier B. Above 30 m is Tier C. A low fit RMS alone is insufficient: reserve at least two check points from fitting and report both fit and independent check RMS.

## Polygonisation and QA

1. Select only the main map frame; exclude locator maps, legends, marginalia, no-data, shadows and image coverage gaps.
2. Follow the printed legend. For 2023, digitise only the red “Flood / Standing Water due to Rains” class. Keep 2021 annotation interpretation separate from image colours; distinguish flood/inundation calls from shadow, cloud and permanent water.
3. Digitise flood polygons into the empty `data/processed/labels_manual/digitised_labels.gpkg` template. Preserve `event`, map issue date, source filename, digitiser, confidence, notes, georeferencing RMS and created time. Do not manufacture dry polygons from unmarked space.
4. Validate Polygon/MultiPolygon geometry and EPSG:32644. Record RMS; the loader assigns B at <=30 m, C above 30 m. Its `--load` option inserts only real, validated rows with `PENDING_MANUAL_REVIEW`; it does not mark them accepted or ground truth. The current template has zero features, so no database rows were loaded.
5. Check map-to-OSM alignment at reserved control points, CMA clipping, polygon validity, source/date attributes, overlay with permanent water and known standing-water/urban confusion, and a saved screenshot before accepting a tier.

Expected manual time: 2–4 hours for the 2021 local map sheet, 3–5 hours for the two 2023 regional map pages, plus QA. December 2015 time is unknown because no map files were provided.
