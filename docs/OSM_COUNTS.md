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

The parser considered 519,628 intersecting ways and read 89,682,822 total PBF objects. These are OpenStreetMap mapped objects, not a completeness estimate. Counts can overlap between tag groups and exclude relation geometries. Broad substring searches for Adyar, Cooum, Kosasthalaiyar, and Buckingham Canal produced false positives from POI/road names; therefore exact named-watercourse presence remains unverified and should be checked against waterway geometries/names specifically.

The regional PBF is licensed under ODbL 1.0. See the official [Geofabrik India download page](https://download.geofabrik.de/asia/india.html). Retain attribution and comply with ODbL when distributing derived databases.
