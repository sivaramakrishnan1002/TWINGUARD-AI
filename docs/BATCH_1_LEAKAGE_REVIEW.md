# Batch 1 leakage and physical-sanity review

**Scope:** Batch 1 T1–T7 artifacts as of 25 Oct 2026. This review distinguishes software checks from scientific validation. It does not label any SAR-derived output as ground truth.

## Leakage and evaluation

### Phase 9 susceptibility model

- Predictors are static features from the cell table; they are not computed from the November target rasters. Entire 3 km blocks are held together, a one-block neighbor buffer is removed from training, and imputation/scaling/sampling are fit within each training fold. Held-out test blocks are evaluated at true target prevalence.
- The random forest's reported spatial-fold PR-AUC is 0.3415, ROC-AUC 0.8911, F1 0.3499, IoU 0.2143, Brier 0.0398 and ECE 0.0093. Its PR-AUC exceeds the same-split elevation-only (0.0515), river-distance-only (0.0465), and random (0.0512) baselines. These are spatial splits of the same November 2015 union label, not independent event/date validation.
- F1 thresholds were selected from in-sample training predictions, so thresholded F1 may be optimistic. The target itself subtracts baseline-water and WorldCover-water cells; the 1 Sep/14 Oct polygons are proxies and can include wet soil. A single 2015 event cannot establish cross-event skill or support claims about future forecasts.
- The 20-fit bootstrap mean/p05/p95 rasters use a model fit to all eligible 2015 data. There is no held-out-label coverage calculation for the interval. It represents resampling/model spread only; it is not an event-transfer or total predictive interval.
- Phase 9 permutation importance ranks elevation and slope highest, followed by TWI, built-up fraction, roads, and population. The water-fraction feature is constant after the water mask and has zero measured importance; building-density importance is near zero. No implausible dominant feature is evident from that summary, but this does not rule out label or source bias.

### T3/T4 fixed SAR rule

- The rule parameters were frozen before comparing the 24 Nov candidate with the official UNOSAT vector. No threshold or mask was tuned against that reference.
- On the full observable CMA domain, run `20261025_03` scores IoU 0.001337, precision 0.6033, recall 0.001339, F1 0.002671, with 0.2178 km² predicted versus 98.1576 km² reference raster area. It is tier D. The eligible-only IoU 0.5328 covers only 13,533 cells and 0.1602 km² reference flood, so it is not an acceptance score.
- UNOSAT may derive from the same 24 Nov Sentinel acquisition. Agreement is therefore not independent physics validation. This deterministic binary screen has no probability output; model probability/calibration/uncertainty gates are not applicable to its T4 acceptance test.
- An initial run admitted finite slope NoData −9999; it was superseded. A preliminary area calculation included geometry outside the CMA; it was superseded too. Corrected run `20261025_03` excludes the NoData sentinel and reports clipped vector area. The earlier JSON filenames are clearly marked superseded.
- **Known metadata defect:** the existing T3 run `20261025_03` HAND GeoTIFF has a stale text tag saying the D8 threshold was 1,000 cells. The actual code, summary JSON and generated values used 100 cells. The source raster was preserved, not overwritten. T5 outputs from the corrected script have the correct 100-cell tag. Do not rely on the stale T3 GeoTIFF tag.

### T5 fixed-rule applications

- The 6 Dec 2015 candidate is only 0.2322 km²; GFD native-grid coarse IoU is 0.00179, but event 4309 ends on 4 Dec. It does not validate the 6 Dec label. None of 944 in-CMA OpenCity point observations fell on the candidate; their source date is not specified, so this is not time-matched validation.
- The 16 Nov 2021 candidate is 0.0918 km². The available NRSC map is a PDF dated 13 Nov and remains undigitized; no numeric IoU, precision, recall, or accepted tier can be computed. Both candidates remain tier D and excluded from the usable-label view. No 2023 label was made because all available SAR scenes predate the peak.

### T6 depth fields

- The method infers a flat local surface from each raster component's median DEM boundary, then subtracts the cleaned DSM. Small/one-cell components naturally produce zero depth; that is visible in the zero median. It is an extent-based proxy, not a hydraulic solution.
- Valid depth covers 30,235/94,195 cells (32.10%) on 12 Nov and 32,627/109,067 (29.91%) on 24 Nov. Remaining mapped extent is NoData because the cleaned DEM has no valid value there. Maximum mean estimates are 22.817 m and 6.376 m; the high 12 Nov maximum requires visual/manual review and may reflect DSM/source artifacts.
- The ±4 m p05/p95 allowance is a deterministic DEFAULT_TO_CONFIRM. Its coverage was not measurable because no held-out, event-matched point-depth truth is available. It must not be called a calibrated 90% interval.

## Highest risks

1. **No independent accepted event label:** prevents Phase 10 risk-map transfer evaluation; 2021/2023 map PDFs need careful georeferencing and digitizing, and December 2015 peak lacks official vector truth.
2. **Very narrow SAR rule coverage:** only 1.03% of CMA cells are eligible under HAND/slope and other masks; the candidate fails full-domain acceptance by orders of magnitude.
3. **Depth/map uncertainty:** only about 30–32% of November flood extent has valid DEM depth, the surface is a DSM with known artifacts, and the ±4 m interval has no empirical coverage check.

The full T4/T5 numbers are in `LABEL_EVALUATION.md`, `T5_FIXED_RULE_APPLICATION.md` and their JSON reports. Depth definitions and coverage are in `DEPTH_FIELD_CONTRACT.md` and `T6_DEPTH_OUTPUTS.json`.
