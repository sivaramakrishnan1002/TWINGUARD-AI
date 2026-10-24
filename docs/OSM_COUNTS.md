# OpenStreetMap inventory and counts

Source: official Geofabrik Southern Zone snapshot, downloaded 2026-10-08. The PBF was parsed locally using pyosmium; no extracted/processed files were written. Counts use ways/nodes whose geometry intersects the buffered CMA rectangle W 79.984, S 12.833, E 80.365, N 13.311. Point-in-bounds node locations were held in the in-memory sparse location index. The PBF's latest timestamp was 2026-10-06T20:21:06Z.

| Requested feature/tag group | Count in bounds | Notes |
|---|---:|---|
| highway ways | 131,218 | Ways intersecting bounds |
| bridge-tagged ways | 2,245 | May overlap highway ways |
| tunnel-tagged ways | 556 | May overlap highway ways |
| buildings | 385,373 | Building-tagged ways |
| waterways | 816 | Waterway-tagged ways |
| natural=water | 1,319 | Natural water features |
| reservoirs | 254 | Reservoir-tagged features |
| hospitals | 908 | amenity=hospital |
| clinics | 607 | amenity=clinic |
| schools | 706 | amenity=school |
| shelters | 172 | shelter-tagged features |
| fire stations | 15 | amenity=fire_station |
| police | 123 | amenity=police |
| emergency facilities | 64 | emergency-tagged features |
| social facilities | 10 | social-facility-tagged features |

## Facility and building reconciliation with extracted layers

The database facility rows match the saved extracted/graph counts exactly. This does not make them directly comparable to the table above: the table is a broad rectangle inventory of tag groups, while the extraction uses a CMA-plus-2-km polygon, category grouping and deduplication. No same-snapshot OSM-id crosswalk was computed.

| Type | Extracted graph and database | Rectangle inventory | Difference |
|---|---:|---:|---:|
| Hospital | 848 | 908 | -60 |
| Clinic | 587 | 607 | -20 |
| School | 696 | 706 | -10 |
| College | 188 | Not separately listed | — |
| Shelter | 171 | 172 | -1 |
| Fire station | 15 | 15 | 0 |
| Police | 121 | 123 | -2 |

For buildings, the 385,373 inventory is the number of building-tagged ways intersecting the buffered rectangular bounds. The extractor output has 382,294 footprints and the database matches that count. The extractor requires closed ways with available node coordinates and valid polygon geometry intersecting the CMA-plus-2-km buffer, then clips retained polygons. The exact number rejected by each rule was not recorded; the 3,079-count difference is therefore explained by differing inclusion rules in aggregate, not precisely allocated.

The parser considered 519,628 intersecting ways and read 89,682,822 total PBF objects. These are OpenStreetMap mapped objects, not a completeness estimate. Counts can overlap between tag groups and exclude relation geometries. Broad substring searches for Adyar, Cooum, Kosasthalaiyar, and Buckingham Canal produced false positives from POI/road names. Exact waterway/water-feature name-field matching, clipped lengths, way IDs, and named-subset endpoint connectivity are now documented in `OSM_WATERWAYS.md`; these do not establish ground completeness.

The regional PBF is licensed under ODbL 1.0. See the official [Geofabrik India download page](https://download.geofabrik.de/asia/india.html). Retain attribution and comply with ODbL when distributing derived databases.
