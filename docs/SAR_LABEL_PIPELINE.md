# Sentinel-1 flood-label pipeline plan

Plan only. No Sentinel data was opened, extracted, or processed by this script.

## Installed-tool inventory

| Tool/package | Available? | Version/path |
|---|---|---|
| SNAP gpt | no | `not found on PATH` |
| GDAL CLI gdalinfo | no | `not found on PATH` |
| rasterio | yes | `1.5.2` |
| GDAL Python bindings | no | `not installed` |
| SciPy | no | `not installed` |
| asf_search | no | `not installed` |
| hyp3_sdk | no | `not installed` |
| pyroSAR | no | `not installed` |

`rasterio` includes a bundled GDAL library in this environment, but the GDAL Python package/CLI is not separately installed. SNAP is absent. No package was installed for this plan.

## Processing options

### A. Local processing with ESA SNAP

Use a pinned SNAP Graph Processing Tool workflow on the original ZIPs, preserving the originals. Determine compatible orbit direction/relative orbit, apply precise orbit files where available, remove thermal/border noise as appropriate, calibrate VV/VH to sigma-nought, apply terrain correction using the selected DEM, and export consistent linear and dB rasters. Decide and document any radiometric terrain flattening. Co-register paired images before change detection and quantify residual alignment. Do not use a generic speckle filter without a comparison rationale.

### B. ASF On Demand / HyP3 terrain-corrected products

Request an appropriate terrain-corrected Sentinel-1 product through ASF On Demand/HyP3 and retain product metadata, processing recipe and citations. **To be verified by the user on the ASF site, including free credit limits.** No account access or request was made. Compare the output bands, projection, terrain correction and masks with the planned SNAP outputs before treating them as equivalent.

## Pilot and event application

1. Pilot reference acquisition: 19 Oct 2015; event acquisition: 24 Nov 2015. Derive an inundation candidate with a documented backscatter/change method and compare inside the CMA to the UNOSAT `S1_20151124` layer. Report intersection-over-union (IoU), precision and recall using the same binary grid and mask, plus the thresholded area and valid-pixel denominator.
2. **Leakage caveat:** the UNOSAT 24 Nov layer may have been derived from the same Sentinel acquisition. If so, the pilot tests whether our processing reproduces that map, not whether the inferred extent matches independent flood physics or ground truth.
3. Only after documenting pilot behavior, apply the fixed method to the 6 Dec 2015 acquisition using 19 Oct and 24 Nov as reference imagery. There is no independent collected vector label for the 1–8 Dec peak; label output remains an inferred candidate.
4. Apply to 16 Nov 2021 using 23 Oct and 4 Nov 2021 as reference imagery. Compare with the NRSC 13 Nov map (PDF; manual georeferencing/digitising required) and OpenCity observed flood points. Point overlap is not a full-extent accuracy score. Record map digitising uncertainty and timing mismatch.

## Decisions before processing

- Speckle filter: compare no filter and one documented filter/parameter set; choose by effect on urban and water boundaries.
- Threshold: pre-register a fixed VV/VH/change threshold or a training-free adaptive threshold; do not tune against the validation map without calling it calibration.
- Urban masking: decide whether to exclude built-up cells or treat urban double-bounce separately. Record WorldCover year/resolution and retain an urban-specific error summary.
- Permanent-water mask: test a mask from the 1 Sep and 14 Oct UNOSAT layers plus WorldCover class 80. These references and WorldCover do not guarantee complete or seasonally correct permanent-water mapping.
- Co-registration, orbit direction, polarization, DEM, layover/shadow handling, tide/time matching, nodata, resampling and common 30 m grid must be fixed before scoring.

## Storage and runtime planning

No local SNAP/HyP3 runtime or output-size benchmark exists, so a defensible numeric runtime/storage forecast is **not computed**. The 13 archived ZIPs total about 16.05 GB in the existing verification report; 6 Dec 2015 and the two 16 Nov 2021 ZIPs are a subset. The final CMA master grid is 1,370 × 1,760: a single uncompressed float32 band on that grid is about 9.6 MB, so final 2-band VV/VH rasters for the four key dates would be roughly 77 MB before masks/overviews. Full-scene SAFE/processing intermediates are much larger; reserve at least the selected ZIP bytes plus temporary workspace, check the exact scene sizes and free disk before starting, then benchmark the pilot and update the estimate. The grid-only number is not a full-scene estimate.

## Main risks

- A single 6 Dec 2015 scene and sparse 2021 acquisitions may miss event timing or peak water; 16 Nov 2021 is after the reported 13 Nov map date.
- Urban structures, wet soil, paddy fields, tide, layover/shadow and permanent water can mimic or hide inundation in SAR backscatter.
- UNOSAT 24 Nov may share the event acquisition, and 2021 NRSC PDF digitising plus OpenCity points provide imperfect validation references.

No Phase 4 SAR processing was performed.
