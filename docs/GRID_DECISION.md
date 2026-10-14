# Phase 3 common grid decision

**Decision for this Phase 3 pass:** WGS 84 / UTM zone 44N (EPSG:32644), 30 m square cells, aligned to a global 30 m origin. The target rectangle covers the provisional older CMA boundary plus 2,000 m on every side. The extent is snapped outward to 30 m multiples.

The grid is 1,370 columns by 1,760 rows, with affine transform `30, 0, 390000, 0, -30, 1471620` (projected bounds 390000–431100 m E and 1418820–1471620 m N). The raster mask `data/processed/grid/cma_mask.tif` marks pixel centres inside the current CMA boundary (`all_touched=false`). The data grid includes the 2 km contextual buffer; the mask distinguishes CMA summary statistics from buffer cells.

This follows the explicit Phase 3 requirement for a 30 m analysis grid and supersedes the earlier planning-only 10 m proposal in `PHASE3_PLAN.md`. A 30 m grid is a working multi-source compromise: it does not create new detail from the roughly 30 m Copernicus GLO-30 DSM, the 100 m WorldPop estimate, sparse weather samples, or 250 m Global Flood Database. Sentinel-1 scenes must be geocoded and resampled onto this grid only in a separately approved processing step; they do not define its origin.

Resampling conventions:

- Continuous terrain and weather surfaces: bilinear where a raster surface is justified.
- Categorical land-cover classes: majority/mode; keep category values intact.
- Land-cover fractions: one-hot class masks averaged from 10 m to 30 m.
- Population counts: sum resampling, with source nodata kept distinct from zero. Compare totals before/after any future changes.
- Flood labels: nearest-neighbour categorical rasterization, using pixel-centre inclusion; label products in this pass are exploratory only.
- Vector networks and time series remain vector/table data; do not force them into raster cells unless a later modelling feature explicitly needs that representation.

Validation recorded for this pass: 1,319,380 CMA mask cells; all generated master-grid raster products must match CRS, transform, dimensions, and mask alignment. See `PHASE3_LOG.md` for measured values and limitations. The boundary is still the collected older CMA boundary, not the expanded post-2022 metropolitan jurisdiction; confirm before final modelling.
