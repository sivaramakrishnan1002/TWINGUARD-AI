# Phase 2 storage estimate

Current `data/raw` contains 26 non-log files totaling 879,922,239 bytes, plus 17 `DOWNLOAD_LOG.txt` files totaling 24,845 bytes: 43 files and 879,947,084 bytes total (879.95 MB decimal). `data/processed` and `data/features` remain empty. No `.part` or `.tmp` download files remain.

| Dataset | Current size | Pending estimate |
|---|---:|---|
| Boundary + 2015/2021 floods | 68,595,202 bytes | None for current records |
| 2023 NRSC/NDEM maps | 18,494,659 bytes | None for current records |
| Weather | 4,421,217 bytes | CDS/GPM/IMD unknown |
| Copernicus GLO-30 | 109,843,443 bytes | None for selected tiles |
| ESA WorldCover | 119,065,806 bytes | None for selected tile |
| OSM | 557,975,955 bytes | None for regional PBF |
| Reservoirs | 1,521,990 bytes | CAG/time series unknown |
| Satellite catalogue | 3,967 bytes | Scene sizes unknown; no scenes downloaded |

Known pending minimum estimate: WorldPop R2025A India file advertised at 728.76 MB; this is an advertised size, not an actual downloaded size. No files over 2 GB were downloaded. Disk free before the WorldPop retry was 248,189,861,888 bytes.
