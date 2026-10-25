# Urban physical susceptibility layer

Status: **PHYSICAL, NOT FITTED TO LABELS.** This is a rank score, not a calibrated flood probability or forecast.

## Method

Rasterized 759 existing OSM waterway line features onto the EPSG:32644 30 m DEM grid (24,949 valid drainage pixels). For each CMA cell, the nearest drainage pixel was selected by Euclidean distance, without D8 flow routing. Height is `max(cell DEM − nearest drainage-pixel DEM, 0 m)`. The score averages empirical rank components: lower nearest-drainage height, higher local depression, lower relative elevation at 5/15/33 cells, and shorter drainage distance. This relative score has no probability interpretation.

The relative-elevation and local-depression values were read from the existing Phase 9B v2 cell table and copied into new rasters; the table and legacy D8 HAND were not modified. Only cells with all terrain components available are scored. Built-up fraction >=0.30 is used as a descriptive urban-point stratum.

## OpenCity independent spatial cross-check

The points have unclear dates and approximate locations, so point hits do not validate a dated event. Confidence intervals use 2,000 resamples of 3 km point blocks. Matched chance selects random score-domain cells with matching built-up bin and dominant land-cover class.

| Point set | Top rank share | Hit share (95% CI) | Matched chance (95% CI) | Scored points |
|---|---:|---:|---:|---:|
| All scored points | 1% | 1.51% (0.29%–2.94%) | 0.82% (0.31%–1.48%) | 927 |
| All scored points | 5% | 9.17% (6.18%–12.33%) | 4.85% (3.42%–6.31%) | 927 |
| All scored points | 10% | 15.75% (11.82%–19.52%) | 9.68% (7.80%–11.62%) | 927 |
| All scored points | 20% | 28.48% (22.29%–33.98%) | 18.90% (16.43%–21.48%) | 927 |
| Urban proxy: built-up >=0.30 | 1% | 1.38% (0.26%–2.70%) | 0.81% (0.25%–1.44%) | 867 |
| Urban proxy: built-up >=0.30 | 5% | 8.65% (5.58%–11.98%) | 4.82% (3.45%–6.30%) | 867 |
| Urban proxy: built-up >=0.30 | 10% | 15.57% (11.42%–19.48%) | 9.56% (7.70%–11.66%) | 867 |
| Urban proxy: built-up >=0.30 | 20% | 28.37% (22.04%–34.33%) | 18.82% (16.26%–21.37%) | 867 |

The matching is by built-up-fraction bin and dominant land-cover class, not exact fractional land-cover composition. The confidence intervals reflect the available spatial point blocks and should be read cautiously.

## Outputs

New rasters and machine-readable results are in `data/features/terrain/urban_physical_v1/`. The source Phase 9B cell table remains unchanged.
