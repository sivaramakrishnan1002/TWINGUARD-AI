# Phase 2 storage estimate

The last verified inventory contains 44 files under `data/raw` (27 non-log files, 17 logs), 1,644,105,109 bytes total. This figure reflects the existing inventory before this close-out and excludes all documentation/scripts created under `docs` and `tools`. No Sentinel scenes, reservoir time series, or CAG report were downloaded. `data/processed` and `data/features` remain empty. No raw file was changed in this close-out.

| Dataset | Current size | Pending estimate |
|---|---:|---|
| Boundary + 2015/2021 flood data | 68,595,202 bytes | No December 2015 peak product obtained |
| Official 2023 NDEM PDFs | 18,494,659 bytes | None for current PDF set |
| Weather | 4,421,217 bytes | CDS/GPM/IMD unknown |
| Copernicus GLO-30 | 109,843,443 bytes | None for selected tiles |
| ESA WorldCover | 119,065,806 bytes | None for selected tile |
| WorldPop R2025A alpha | 764,157,097 bytes | None for this raster |
| OSM regional PBF | 557,975,955 bytes | None for current extract |
| Reservoirs | 1,521,990 bytes | Historical series and CAG report unknown |
| Existing Sentinel candidates CSV | 3,967 bytes | 17 listed event/reference products: 20,419,832,685 catalogued bytes; recommended minimum: 12,046,047,571 bytes |

D: free space at Sentinel planning check: 247,457,554,432 bytes. Catalogued scene sizes are estimates for planning, not on-disk sizes. No partial downloads were created in this close-out. The prior WorldPop partial was removed before this close-out; the user-supplied full raster remains intact.
