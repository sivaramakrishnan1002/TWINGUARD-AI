# Stage 8 — SAR-derived flood label pilot

> Every SAR-derived flood raster/polygon in this stage is **DERIVED**, not ground truth.

## 8.1–8.2 RTC products and preprocessing

See `HYP3_RTC_VERIFICATION.md` and `DOWNLOAD_LOG.txt` for per-product ZIP CRC, checksum, source scene mapping, raster members, CRS and options. All RTC TIFFs opened with EPSG:32644, 30 m pixels; source label archives were not modified.
The working grid covers the CMA plus a 3,000 m buffer and shares the master 30 m EPSG:32644 lattice; final labels are cropped to the exact master grid. RTC Gamma-0 power was bilinearly resampled in linear power; reference/event comparison was converted to dB. The Lee filter was 5×5; scene-specific local noise variance was estimated from the lowest 10% CV pixels. HyP3 speckle filtering was off. All 13 products include a layover/shadow mask; valid cells must be tested, and codes with bit 4 or 16 are excluded. The cleaned-DEM slope fallback (>15°) was not needed.

## 8.3 2015 pilot

Training-free Otsu thresholds (computed inside CMA valid land, no UNOSAT pixels used) were 0.783 dB for event-minus-reference VV difference and -2.724 dB for event VV. UNOSAT `S1_20151124` metrics are post-threshold comparisons only. UNOSAT may use the same 24 Nov scene, so this tests pipeline/map agreement, not flood physics.

| Method | Urban handling | IoU | Precision | Recall | F1 | TP / FP / FN / TN | predicted / UNOSAT area km² |
|---|---|---:|---:|---:|---:|---|---:|
| difference_otsu | with_dense_urban | 0.1029 | 0.1030 | 0.9874 | 0.1866 | 41614 / 362265 / 532 / 791809 | 363.49 / 37.93 |
| difference_otsu | without_dense_urban | 0.1376 | 0.1378 | 0.9896 | 0.2419 | 41248 / 258036 / 434 / 369818 | 269.36 / 37.51 |
| event_backscatter_otsu | with_dense_urban | 0.0559 | 0.0559 | 0.9997 | 0.1059 | 42133 / 711602 / 13 / 442472 | 678.36 / 37.93 |
| event_backscatter_otsu | without_dense_urban | 0.0699 | 0.0699 | 0.9997 | 0.1306 | 41671 / 554709 / 11 / 73145 | 536.74 / 37.51 |

### Threshold sensitivity

Offsets are applied to the data-derived Otsu event-minus-reference VV dB threshold, not fitted to UNOSAT.

| Offset dB | Threshold dB | IoU | Precision | Recall | F1 | Predicted area km² |
|---:|---:|---:|---:|---:|---:|---:|
| -3.0 | -2.217 | 0.3742 | 0.3842 | 0.9350 | 0.5446 | 92.31 |
| -2.0 | -1.217 | 0.2721 | 0.2750 | 0.9632 | 0.4278 | 132.86 |
| -1.0 | -0.217 | 0.1746 | 0.1752 | 0.9784 | 0.2972 | 211.79 |
| +0.0 | 0.783 | 0.1029 | 0.1030 | 0.9874 | 0.1866 | 363.49 |
| +1.0 | 1.783 | 0.0655 | 0.0656 | 0.9937 | 0.1230 | 574.91 |
| +2.0 | 2.783 | 0.0494 | 0.0494 | 0.9976 | 0.0941 | 766.43 |
| +3.0 | 3.783 | 0.0424 | 0.0424 | 0.9988 | 0.0813 | 893.84 |

## 2015-12-06 DERIVED candidate

Otsu difference threshold: -0.334 dB; event VV threshold: -3.089 dB. Candidate area: 482.38 km² across 1,196,210 valid land pixels.

## 2021-11-16 DERIVED candidate

Otsu difference threshold: -0.497 dB; event VV threshold: -2.880 dB. Candidate area: 398.60 km² across 1,196,226 valid land pixels.

6 Dec 2015 candidate vs 24 Nov candidate area change is **+118.89 km²**. GFD 4309 comparison (coarse; ends 4 Dec, so not date matched): 32,929 resampled GFD flooded 30 m cells and SAR/GFD IoU **0.040** on the shared masked cells. OpenCity point cross-check: 399 of 945 points (42.2%) fall inside the Dec 6 candidate; source event timestamps are unspecified, so this is spatial overlap only.

The 2021 candidate was generated for 16 Nov using 23 Oct and 4 Nov reference acquisitions. Numerical comparison to the 13 Nov NRSC map is **not computed** because the local NRSC reference is a PDF and has not been georeferenced/digitised. Available OpenCity points are 2015, not 2021; no valid 2021 point comparison is available.

No 2023 flood label was created: local RTC scenes dated 18 and 30 Nov are before the 3–4 Dec Michaung peak; there is no post-peak scene in this set.

## Reliability and validation limits

Dense urban is flagged where WorldCover built-up fraction ≥0.5; the urban-excluded metrics are shown above. This is a screening flag, not proof every such pixel is wrong. Sentinel RTC masks remove marked layover and shadow; remaining urban double-bounce, wet soil, tide, date offsets and threshold sensitivity remain. All labels are DERIVED. A single 2015 scene pair and a potentially same-scene UNOSAT comparison do not validate physical inundation accuracy.

December 2015 official vector layer is still unavailable. QGIS validation steps for digitising the 2021 NRSC PDF, 2023 NDEM PDF, and any December 2015 maps are in `MANUAL_TODO.md`.

## Outputs

The source UNOSAT raster's gross Nov 24 CMA area is 98.16 km². After the specified baseline-water and WorldCover-water exclusions plus the common valid-SAR footprint, the comparison mask contains 37.93 km² of Nov 24 UNOSAT positive cells (37.51 km² after dense-urban exclusion); this is why the comparison table reports less than the gross source area. The permanent-water mask is the union of both UNOSAT baseline dates and every WorldCover water-fraction cell above zero; their overlapping cells are counted once in the actual mask.

All four final raster products use the master transform, dimensions and CRS. Their vector polygons were simplified at 30 m and clipped to the CMA. The final GPKG has 45,096 polygon rows loaded in `labels.derived_flood_polygons`: 17,547 (24 Nov, both methods), 11,763 (6 Dec), and 15,786 (2021). Database checks found 0 non-DERIVED rows, 0 invalid geometries, 0 outside-CMA rows, 0 wrong-SRID rows and 0 missing-provenance rows. The 2021/6 Dec outputs are candidate labels only; their very large mapped areas and coarse/map-only references make them unsuitable as validated extents.
