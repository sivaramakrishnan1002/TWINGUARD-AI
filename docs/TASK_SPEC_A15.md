# A15 task specification — Phase 25 validation synthesis

## Registered scope

Create a validation matrix for A05 forecast/hindcast scenarios, A06 shallow-water simulation, and A09 routing comparison. Recheck existing numerical and physical checks, coverage, CRS/units/NoData, uncertainty meaning, route assessed coverage, exact artifact hashes and test/audit evidence. Use only accepted, date-matched references for scored scientific validation. Where such reference data do not exist, report the metric as unavailable. Do not overwrite outputs or claim operational forecast skill, hydraulic accuracy, safe routes, or emergency readiness.

## Fixed decisions

- Use the existing registered reports and run summaries as evidence, then independently recheck run counts, finite/nonnegative arrays, mass-balance maxima, raster grids, output inventories, A09 schema/NoData verification, and raw-data audit.
- Treat A06 November 2015 UNOSAT spatial-block results as same-event mapped-extent reproduction/calibration evidence, not independent hydraulic validation. GFD and OpenCity comparisons remain coarse/undated spatial cross-checks.
- A05 has hindsight and product-disagreement rainfall scenarios, not archived NWP forecasts or measured depth targets. Forecast-skill metrics are unavailable.
- A09 is an OSSE with member 20 hidden as simulated truth and members 1–19 as forecasts. This is simulated routing evidence, not real-world route validation.
- Report that depth bands are metres by product semantics and documentation, while the inspected GeoTIFFs lack explicit band-unit metadata; preserve files and flag the metadata gap.
- Do not create a new figure where no independent validation metric supports one; provide the evidence matrix and route summaries in the report.
