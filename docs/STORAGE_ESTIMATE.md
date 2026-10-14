# Phase 2 storage estimate

## Current raw-data inventory (2026-10-14)

The raw tree contains 73 files: 55 data files and 18 `DOWNLOAD_LOG.txt` files. Data files total **14,706,156,884 bytes**; including logs the tree totals **14,706,194,481 bytes**. The ten Sentinel-1 ASF ZIPs are **12,978,427,058 bytes** in total. All 55 data files matched their logged byte size and SHA-256; no mismatches or current files without a comparable hash were found. Failed historical download attempts recorded with size 0 and `SHA-256: not applicable` are log entries, not files.

| Raw folder | Bytes on disk, including its logs |
|---|---:|
| boundary | 42,927 |
| buildings | 435 |
| dem | 109,845,676 |
| historical_floods | 170,229,746 |
| hydrology | 435 |
| infrastructure | 440 |
| landcover | 119,066,401 |
| osm | 429 |
| population | 764,158,921 |
| reservoirs | 2,005,724 |
| roads | 557,977,519 |
| satellite (including the 10 ASF ZIPs) | 12,978,435,611 |
| weather | 4,430,217 |
| **Total** | **14,706,194,481** |

D: free space at the current check: **237,648,322,560 bytes**. `data/processed` and `data/features` remain unprocessed; Phase 3 has not started. The saved catalogue includes an optional post-peak 16 Nov 2021 Sentinel-1 pair, but neither scene was downloaded. Its candidate catalogue sizes are 536.138 MB and 549.281 MB; these are catalogue values, not measured files.

No raw files were extracted, renamed, or edited. Sentinel ZIPs were read in place for hashes, ZIP CRC checks and metadata. SSL verification was never disabled.
