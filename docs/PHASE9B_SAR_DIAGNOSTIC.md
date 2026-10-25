# SAR diagnostic against the 24 November 2015 UNOSAT extent

**Result: a simple rule separates the mapped extent in this scene, but this is not an accepted flood label.** The comparison uses the exploratory-not-final UNOSAT 24 Nov raster in `data/processed/labels_inspection/`, the 24 Nov and 19 Oct RTC dB rasters in `data/processed/sar_work/rtc_aligned/`, and `cell_table_phase9b_v2.parquet`. It is a label-versus-scene diagnostic, not independent validation. UNOSAT may have used this same SAR acquisition.

## Alignment, eligibility and matching

The UNOSAT label grid is EPSG:32644, 30 m, 1,760 by 1,370 cells, with upper-left `(390000, 1471620)`. RTC is EPSG:32644, 30 m, 1,826 by 1,436 cells, with upper-left `(389010, 1472610)`. The 990 m origin difference equals 33 cells in both axes; the RTC label footprint is its `[33:1793, 33:1403]` crop. All 1,319,380 cell-table centres mapped inside the label grid. The script samples each raster by coordinates, rather than assuming same row/column origins.

The UNOSAT raster contains 109,067 mapped flooded cells within the CMA. Removing cells marked by either September/October baseline water or WorldCover water leaves 42,146 mapped positives. Of those, 39,697 have no finite HAND in the feature table. The strict matched analysis therefore uses the remaining 2,449 positives, with 2,449 non-flood cells matched exactly on dominant land-cover group and HAND bin (`<2`, `2–5`, `5–10`, `>=10 m`). Sampling is without replacement within each stratum, with fixed seed `20261025`, so the same grid cell is not duplicated across folds. Both samples also require valid RTC data and clear layover/shadow bits. This finite-HAND restriction is a material limitation: only 5.8% of the eligible positives enter the strict diagnostic.

## Direction-aware discrimination

Raw AUC below 0.5 means the flooded cells tend toward lower backscatter. Direction-aware AUC reverses the score in that case. No threshold was tuned to IoU.

| Variable | Raw AUC (flood=higher) | Direction-aware AUC | Observed direction | Spatial-block depth-1 stump AUC, mean ± SD | Training thresholds across folds |
|---|---:|---:|---|---:|---|
| 24 Nov VV dB | 0.035 | 0.965 | lower | 0.910 ± 0.029 | -11.38 to -11.96 dB |
| 24 Nov VH dB | 0.049 | 0.951 | lower | 0.879 ± 0.020 | -17.91 to -18.41 dB |
| VV dB change (24 Nov minus 19 Oct) | 0.044 | 0.956 | lower | 0.896 ± 0.034 | -2.22 to -2.31 dB |

The stump uses five spatial holdouts of 3 km block groups and fits one split per training fold. It is deliberately small and diagnostic, not a tuned classifier; no buffer was added, so these values are not a model-quality estimate. The result meets the prompt's “AUC at least 0.7” diagnostic condition. It does **not** meet a pre-registered acceptance rule for making or replacing labels, and no rule-derived label was created here.

## Shift and permanent-water checks

Mean IoU of the 24 Nov flooded extent against its four cardinally shifted copies was 0.763 at 1 cell, 0.633 at 2 cells, and 0.561 at 3 cells. This declining overlap shows that a one-cell registration error is consequential; it does not indicate that the current grids are shifted. The actual CRS, resolution and 33-cell RTC buffer offset agree exactly by world coordinates.

The baseline-water layers and WorldCover water are used at the UNOSAT cell centres. Among permanent-water cells with valid RTC, median event VV/VH were -14.20/-21.85 dB, versus -5.78/-12.84 dB for eligible land; 96.8%/97.3% of permanent-water cells were below the eligible-land median. This expected water response is a useful alignment sanity check, not proof of map accuracy.

## Decision

The extent **is separable from this scene by simple rules** on the strict matched subset. Keep the official UNOSAT November vector/raster product as the only Tier A training label. Keep all SAR-derived candidates Tier D and out of training and `labels.v_usable_flood_labels`. The same-scene possibility, small strict sample, missing HAND coverage, map date/scene relationship, and lack of dated independent flood truth prevent promoting these rules.

Reproduce with `.venv/Scripts/python.exe pipelines/labels/sar_diagnostic_v2.py`. Machine-readable metrics and input alignment are in `PHASE9B_SAR_DIAGNOSTIC.json`.
