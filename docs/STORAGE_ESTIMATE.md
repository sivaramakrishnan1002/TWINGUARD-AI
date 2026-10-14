# Project storage estimate — 14 October 2026

## Raw inputs

`data/raw` contains 58 data files totalling **17,775,232,566 bytes** and 18 `DOWNLOAD_LOG.txt` files. The complete raw tree, including logs, is **17,775,271,364 bytes**. The read-only audit matched all 58 current data files against recorded sizes and SHA-256 hashes; there were no mismatches or missing comparable hashes.

| Raw folder | Files, including logs | Bytes on disk |
|---|---:|---:|
| boundary | 2 | 42,927 |
| buildings | 1 | 435 |
| dem | 5 | 109,845,676 |
| historical_floods | 19 | 170,229,746 |
| hydrology | 1 | 435 |
| infrastructure | 1 | 440 |
| landcover | 2 | 119,066,401 |
| osm | 1 | 429 |
| population | 2 | 764,158,921 |
| reservoirs | 10 | 2,005,724 |
| roads | 2 | 557,977,519 |
| satellite | 16 | 16,047,512,494 |
| weather | 14 | 4,430,217 |
| **Total** | **76** | **17,775,271,364** |

There are 13 Sentinel-1 ZIPs totalling **16,047,502,740 bytes**. The satellite folder total also includes its metadata log. The ZIPs were verified in place and not extracted or modified.

## Derived Phase 3 outputs

The current `data/processed` and `data/features` folders contain **39 files totalling 1,000,374,841 bytes**. The largest is the combined OSM GeoPackage at 457,863,168 bytes; no individual derived output is near 2 GB.

| Largest derived files | Bytes |
|---|---:|
| `data/features/osm/chennai_osm_features.gpkg` | 457,863,168 |
| `data/features/roads/chennai_road_graph.gpkg` | 365,477,888 |
| `data/features/buildings/chennai_building_footprints.gpkg` | 90,013,696 |
| `data/features/landcover/worldcover_2021_area_fractions_30m.tif` | 18,144,418 |

Available space on D: at the latest check was **233,587,265,536 bytes**. Derived rasters and vector outputs were written only beneath `data/processed` and `data/features`; Git ignores these data outputs. Sentinel and other raw file contents remain unchanged.
