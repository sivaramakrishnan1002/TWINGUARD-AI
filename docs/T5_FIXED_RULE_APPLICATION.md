# T5 — Applying the fixed Flood Rule v2

**Status:** both outputs are DERIVED screening candidates, tier D, and not accepted for label use. Parameters were held fixed from T2/T3; they were not retuned to these events. No ground-truth claim is made.

## Fixed procedure

The rule uses the frozen VV/VH event backscatter midpoint screens and dry-land change screens from `T2_PHYSICS_THRESHOLDS.json`; references are averaged in linear power before converting to dB. It excludes WorldCover class 80 and UNOSAT baseline water from the usable-label view, invalid SAR/layover-shadow, slope above 5°, HAND above 5 m, built-up fraction above 0.5, and components smaller than five 8-connected cells. The stream threshold is 100 D8 accumulation cells (0.09 km² upstream area). These terrain thresholds remain defaults to confirm. WorldCover 2021 is used for both events.

| Event scene | Reference scenes | Candidate cells / area | Eligible CMA cells | Confidence cells (high / medium) | Tier/status |
|---|---|---:|---:|---:|---|
| 6 Dec 2015 | 19 Oct and 24 Nov 2015 | 258 / 0.2322 km² | 13,533 (1.03%) | 119 / 139 | D — no official vector for the December peak |
| 16 Nov 2021 | 23 Oct and 4 Nov 2021 | 102 / 0.0918 km² | 13,533 (1.03%) | 80 / 22 | D — NRSC reference is a PDF and is not numerically digitized |

The full metrics are in `T5_APPLY_METRICS_v2.json`; the execution summaries are `T3_FLOOD_RULE_V2_20261025_T5_20151206.json` and `T3_FLOOD_RULE_V2_20261025_T5_20211116.json`.

## Physical plausibility and cross-checks

The median HAND among candidates is low: 0.735 m on 6 Dec and 0.532 m on 16 Nov, compared with 3.745 m among the 25,196 CMA cells with valid HAND. However, median absolute elevation of candidates is 25.00 m and 24.89 m, respectively, compared with 15.76 m across valid CMA DEM cells. This is a warning, not a convincing low-elevation flood pattern. Only 1.91% of CMA cells have valid HAND, and the GLO-30 product is a surface model; the rule cannot currently support a reliable area-wide flood extent.

| WorldCover class | 6 Dec flooded / eligible | 6 Dec share | 16 Nov flooded / eligible | 16 Nov share |
|---|---:|---:|---:|---:|
| Tree | 32 / 3,120 | 1.03% | 1 / 3,120 | 0.03% |
| Shrub | 9 / 554 | 1.62% | 2 / 554 | 0.36% |
| Grass | 82 / 2,231 | 3.68% | 41 / 2,231 | 1.84% |
| Cropland | 132 / 7,368 | 1.79% | 57 / 7,368 | 0.77% |
| Built-up | 0 / 100 | 0% | 0 / 100 | 0% |
| Bare | 2 / 154 | 1.30% | 0 / 154 | 0% |
| Wetland | 1 / 6 | 16.67% | 1 / 6 | 16.67% |

The denominators show the coverage problem: across the CMA only 13,533 cells are eligible and water is excluded, while most of the built-up class is masked. The table is not the fraction of all CMA land that flooded; it is the candidate fraction among cells eligible within each class.

For the 6 Dec 2015 candidate, the GFD event 4309 coarse-grid comparison (maximum aggregation of the 30 m candidate to the GFD grid) has IoU 0.00179: 37 candidate-touched coarse cells, 1,084 GFD flood cells, and 2 overlapping cells across 19,648 in-CMA cells with valid GFD coverage. GFD 4309 ends on 4 Dec, two days before this SAR scene, so this is only a date-mismatched coarse cross-check. Across the two OpenCity observed-point files (945 point features total), 944 points fall inside the CMA and zero fall on a candidate flood cell. Their event dates are not reliably specified, so this is not time-matched validation. The other OpenCity return-period/hazard files are modelled layers and were not treated as observations.

For 16 Nov 2021, the available NRSC 13 Nov map is PDF-only; it has not been georeferenced or digitized. No numerical IoU/tier B or C result can be computed. OpenCity observations are from the 2015 collection and are not a 2021 reference. The candidate stays tier D pending a manual comparison.

## QGIS manual overlay for the NRSC 2021 map

These are future validation steps only; no PDF was processed in this task.

1. Keep the source PDF unchanged. In QGIS, load the CMA boundary and the DERIVED `label_2021-11-16_rule_v2_20261025_T5_20211116_DERIVED.tif` candidate.
2. Open **Raster → Georeferencer**, select the local NRSC 13 Nov 2021 PDF, and use the map frame (not the page border). Add at least four well-spread control points to identifiable road junctions, coastline bends, or other features shared with a trusted projected basemap. Record the control points and residual error.
3. Set target CRS to EPSG:32644. Use a suitable affine/polynomial transform only if residuals are acceptable across the map; otherwise flag the map as unsuitable for numeric comparison. Export the georeferenced copy to a new validation-work folder, never over the source PDF.
4. Digitize only the mapped flood extent as a separate validation polygon, recording the source PDF, page/map date, georeferencing method and uncertainty. Compare against the 16 Nov candidate only where the NRSC map actually covers the same area; report IoU, precision, recall, and overlap area with the partial coverage clearly stated.
5. Do not promote the candidate by visual judgement alone. Apply the preregistered numeric gates only if a defensible event-matched vector reference is produced; retain the PDF-derived layer as map interpretation, not field truth.

## Registry and database disposition

Both new raster candidates and their confidence rasters are recorded locally in the ignored `data/features/labels/label_registry.json` with hashes, metrics and tier D. The database already contains 11,763 6 Dec rows and 15,786 16 Nov rows, all tier D / `REJECTED_PENDING_REWORK`; the accepted-label view excludes them. No new database rows or accepted labels were added because neither event has an available matching official numeric reference. This is the safe result of the requested registry/database check, not a missing load of accepted layers.

The script records correct 100-cell stream-threshold metadata on new T5 HAND outputs. The earlier T3 run 20261025_03 GeoTIFF tag has a stale text string claiming 1,000 cells, although its T3 JSON and actual code record 100 cells; this metadata discrepancy is tracked for correction without modifying that existing raster.

Reproduce with `.venv/Scripts/python.exe -m pipelines.phase8.flood_rule_v2 --run-id 20261025_T5_20151206 --event 2015-12-06 --reference-scenes 2015-10-19,2015-11-24` and the equivalent `20261025_T5_20211116` / `2021-11-16` command using references `2021-10-23,2021-11-04`; then run `.venv/Scripts/python.exe -m pipelines.phase8.evaluate_t5_candidates`.
