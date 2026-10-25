# SAR candidate application to 6 Dec 2015 and 16 Nov 2021

**Authoritative application: v2 only.** Version 1 did not apply the predeclared water/label eligibility mask and is superseded. The v1 files are preserved unchanged. Version 2 applies `eligible_for_model` from the existing Phase 9 label table and retains NoData elsewhere.

The 24-Nov 2015 model passed the pre-registered OOF map-reproduction gate (IoU 0.5977 ≥ 0.25), permitting a Tier C candidate for map reproduction only. Applied date products remain **DERIVED, Tier D pending independent validation**. The median of the five outer-fold thresholds (0.40) was held fixed; there was no retuning.

| Event | Eligible valid cells | Predicted area (km²; 900 m²/cell) |
|---|---:|---:|
| 2015-12-06 | 1,072,286 | 17.3367 |
| 2021-11-16 | 1,072,293 | 7.6032 |

## OpenCity independent-point spatial check (not date-matched validation)

All shares use 877 of the 945 approximate OpenCity points that fall on valid application cells. Confidence intervals are 95% 3-km point-block bootstrap intervals (2,000 replicates). The matched-chance comparator draws cells with the same built-up bin and dominant land-cover class. This checks spatial coincidence only; point dates are unclear.

| Event | Top-ranked cells | Points in ranked cells (share; 95% CI) | Matched chance (share; 95% CI) |
|---|---:|---:|---:|
| 2015-12-06 | top 1% | 0.00% (0.00–0.00%) | 0.09% (0.00–0.34%) |
| 2015-12-06 | top 5% | 0.11% (0.00–0.40%) | 0.61% (0.13–1.19%) |
| 2015-12-06 | top 10% | 0.23% (0.00–0.62%) | 1.46% (0.73–2.31%) |
| 2015-12-06 | top 20% | 1.03% (0.45–1.77%) | 3.27% (2.14–4.53%) |
| 2021-11-16 | top 1% | 0.00% (0.00–0.00%) | 0.14% (0.00–0.46%) |
| 2021-11-16 | top 5% | 0.00% (0.00–0.00%) | 0.89% (0.31–1.53%) |
| 2021-11-16 | top 10% | 0.11% (0.00–0.37%) | 1.66% (0.89–2.58%) |
| 2021-11-16 | top 20% | 1.14% (0.48–1.92%) | 3.64% (2.36–4.93%) |

For 6 Dec, model-compatible change features use 19 Oct as the baseline; 24 Nov is recorded as contextual reference only. For 16 Nov 2021, model-compatible change features use 4 Nov; 23 Oct is contextual only. This is not identical to a two-reference-scene feature design, which the trained model did not use.

## External comparisons and limitations

- **Global Flood Database event 4309:** the cited reference area is about 65.43 km² and the event ends 4 Dec 2015. No local GFD raster was found, so spatial overlap is **not computed**; the date and coarse resolution also make direct area comparison weak. The 6 Dec candidate area is much smaller but is two days after the GFD event window.
- **2021 NRSC map:** spatial comparison **not computed**. The PDF georeferencing CRS conflict is unresolved/manual-needed; do not infer agreement from it.
- **OpenCity:** points are approximate and dates unclear, so the tables above are an independent-source spatial check, not event validation.
- The 24 Nov UNOSAT map may have been derived from the same SAR scene. The high OOF result tests reproduction of that mapped extent, not flood physics or generalisation.
- No application output was loaded into the label database or called ground truth. No 2023 label was produced because there is no post-peak Sentinel scene for the specified event.

Rasters are under `data/features/labels/sar_calibrated_batch2/applied_v2/`. Their SHA-256 hashes and source data hashes are recorded in `SAR_CALIBRATED_LABELS_BATCH2_MODEL_REGISTRY.json`.
