# Phase 3 fix-up findings

Read-only checks against existing raw and derived files on 16 October 2026. The detailed rainfall, terrain and graph results are in their companion reports. This file records the remaining requested cross-dataset findings.

## Sentinel preprocessing plan

`docs/SENTINEL_PREPROCESSING_PLAN.md` exists. It describes the 13 raw ASF scenes, acquisition timing, recommended preprocessing and limitations. The ZIPs remain unprocessed raw imagery.

## Land cover and OSM buildings

On the common 30 m CMA grid (1,319,380 cells), WorldCover's built-up class fraction was compared with the count of OSM building-footprint centroids per cell. Pearson correlation is **0.4243** and Spearman rank correlation is **0.4946** (n=1,319,380 cells, including zeros). This is a moderate positive spatial association, not validation of building completeness, floor area, occupancy or population. The calculation uses a centroid count, so it does not count building footprint area. Inputs: `data/features/landcover/worldcover_2021_area_fractions_30m.tif` and `data/features/buildings/chennai_building_footprints.gpkg`.

## Reservoir and lake coverage

### Kaggle daily storage series

The archive was read in place; its members were not extracted or altered. Each daily series has **6,182 dates**, 2004-01-01 through 2020-12-03, one record per day with no date gaps:

| Reservoir series | First date | Last date | Missing days |
|---|---|---|---:|
| Poondi | 2004-01-01 | 2020-12-03 | 0 |
| Cholavaram | 2004-01-01 | 2020-12-03 | 0 |
| Red Hills | 2004-01-01 | 2020-12-03 | 0 |
| Chembarambakkam | 2004-01-01 | 2020-12-03 | 0 |

The included rainfall table does not declare units in its local file or accompanying local download record. **Rainfall units are unknown/unverified.** Do not infer units from magnitude.

### OpenCity monthly lake series

| Lake series | First month | Last month | Expected months | Present | Missing |
|---|---|---|---:|---:|---:|
| Poondi | 2003-01 | 2021-12 | 228 | 228 | 0 |
| Cholavaram | 2003-01 | 2021-12 | 228 | 228 | 0 |
| Chembarambakkam | 2003-01 | 2021-12 | 228 | 228 | 0 |
| Red Hills / Puzhal | 2003-01 | 2021-12 | 228 | 228 | 0 |
| Veeranam | 2003-01 | 2021-12 | 228 | 227 | 1 (2020-04) |
| Kannankottai | 2020-12 | 2021-12 | 13 within its published interval | 13 | 0 within interval; earlier 2020-01–11 absent before series start |

These monthly values are useful for broad storage context, not event-day release reconstruction.

## Track B reservoir screen — illustrative only

Rule in the existing feature: total storage at least 80% of the combined current-capacity denominator (11,257 mcft), storage greater than its value three days earlier, and three-day mean ERA5 rainfall at least the 2015 pre-1-Dec 90th percentile (23.4689 mm). This is a retrospective screen, not a warning model. Its records are in `data/features/reservoirs/illustrative_track_b_backtest.csv`.

| Flag date | Aggregate storage (% of 11,257 mcft) | Poondi (% capacity) | Cholavaram (% capacity) | Red Hills (% capacity) | Chembarambakkam (% capacity) | Required aggregate threshold | 3-day rainfall (mm; threshold 23.4689) | Lead/status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 2015-11-20 | 80.421% | 84.96% | 57.82% | 73.18% | 89.66% | ≥80% | 53.811 | 11 days before 1 Dec |
| 2015-11-21 | 81.274% | 84.49% | 57.08% | 78.94% | 87.71% | ≥80% | 52.722 | 10 days before |
| 2015-11-22 | 82.820% | 85.05% | 56.71% | 84.55% | 87.02% | ≥80% | 35.711 | 9 days before |
| 2015-11-23 | 83.832% | 84.40% | 60.50% | 85.85% | 88.42% | ≥80% | 37.767 | 8 days before |
| 2015-11-24 | 85.138% | 86.41% | 64.48% | 87.03% | 88.42% | ≥80% | 32.900 | 7 days before |
| 2015-12-01 | 82.358% | 84.96% | 55.04% | 84.55% | 86.17% | ≥80% | 78.378 | Event window |
| 2015-12-02 | 90.370% | 86.88% | 74.38% | 95.94% | 93.17% | ≥80% | 118.378 | Event window |
| 2015-12-03 | 85.769% | 82.61% | 82.89% | 90.79% | 84.88% | ≥80% | 131.233 | Event window |
| 2015-12-04 | 83.601% | 82.61% | 81.41% | 82.73% | 85.93% | ≥80% | 89.989 | Event window |
| 2020-11-28 | 80.563% | 84.87% | 33.40% | 85.30% | 86.45% | ≥80% | 27.278 | Other year |
| 2020-12-03 | 84.143% | 88.73% | 54.58% | 87.21% | 86.06% | ≥80% | 64.978 | Other year |

There are five pre-event flags (20–24 Nov 2015) and six other flags (four in the target event window and two in 2020). Therefore a lead of 7–11 days is observed for the pre-event flags, with the earliest at 11 days. **False-alarm rate is not computed**: the data do not define daily flood/no-flood truth over all evaluated dates, and the six remaining flags cannot automatically be called false alarms. The screen uses current capacities as if fixed historically and storage is not release data.

## WorldPop totals and NoData

The native 100 m WorldPop CMA centre-in-boundary sum is **6,204,903.7045**; the derived 30 m grid sum is **6,203,811.2745**. Difference: **1,092.4300**, about **0.0176%** of the native sum. The grids differ in resolution, projection, resampling and centre-in-boundary sampling. The saved outputs do not isolate how much of the small difference comes from edge support versus resampling, so the exact cause is **not separately attributed**.

NoData counts are **23,812 cells on the native 100 m raster** and **194,961 cells on the derived 30 m grid**. Cell counts are not directly comparable across resolutions. Within the 30 m CMA mask, NoData overlaps WorldCover built-up cells as well as water and other classes, so NoData cannot safely be interpreted as uninhabited or replaced by zero. Treat NoData as unknown unless checked against source semantics. The population sum is a constrained model estimate, not a census count.

“Population-proximity summary” means: count unique 30 m CMA cells whose pixel centres fall within a 100 m buffer of any mapped road or within a 500 m circle of any mapped facility, then sum valid WorldPop values in those unique cells once. Existing results are: roads 1,047,685 cells total (1,002,824 with valid population; sum 6,072,870.5) and facility-circle union 724,797 cells (694,800 valid; sum 5,126,819.5). These are raster sums in proximity zones, not populations living on roads, service catchments, or evacuation demand. Facility circles overlap, so individual facility totals are not additive.

## Existing label-raster COG warning

The validation record reports five exploratory label-inspection TIFFs as tiled GeoTIFFs but not Cloud Optimized GeoTIFFs (COGs). These are existing inspection outputs, not raw data and not final flood-label sources. Their current structure does not prevent reading in the local raster workflow, but it can make range-based access and web/cloud serving less efficient. No files were converted or overwritten; a future export can create separately named COG copies if needed.
