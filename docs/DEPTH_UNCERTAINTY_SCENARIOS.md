# Depth uncertainty scenarios (CR-003 / A03c)

## Result and limits

This is a sensitivity exercise over the existing T6 depth proxies for 12 and 24 November 2015. It does not create measured depths, calibrated probabilities, or routing inputs. The input extent is an official UNOSAT extent, but its associated depth values are derived from the cleaned Copernicus GLO-30 surface model. That surface model includes buildings and vegetation, and valid depth coverage is limited by DEM NoData.

The run used 100 Monte Carlo draws, seed `20261025`, and Gaussian-smoothed spatial error fields with a 10-cell (approximately 300 m) smoothing scale. The relative scenario applies a spatially correlated multiplicative depth error bounded at ±20%. The absolute scenario applies spatially correlated DEM elevation error bounded at ±4 m, then re-estimates each connected component's water surface from its boundary and recomputes depth. The latter is not equivalent to adding or subtracting 4 m directly from depth.

| Event | Rasterized flood cells | Cells with existing T6 depth and valid DEM | Depth coverage of mapped extent | 8-connected covered components |
|---|---:|---:|---:|---:|
| 2015-11-12 | 94,195 | 30,235 | 32.10% | 3,464 |
| 2015-11-24 | 109,067 | 32,627 | 29.91% | 2,056 |

The low coverage means these outputs describe only the portion where the earlier depth proxy exists. Outside that footprint, outputs are NoData and the coverage raster is 255; no missing cell is treated as dry or zero depth.

## Numerical checks

A uniform +4 m vertical offset was applied to both the component boundary-derived water surface and cell DEM. The maximum change in calculated depth was **0.000 m** for each event: the common offset cancels in the surface-minus-DEM equation. A spatially varying, smoothed DEM error does not cancel uniformly; it changes component-edge estimates and local depths, which is represented by the absolute-error scenario.

The following are the average of cell-wise class probabilities over covered cells, not shares of the entire CMA. Class bounds are `<0.15 m`, `0.15–<0.30 m`, `0.30–<0.50 m`, and `>=0.50 m`.

| Event | Scenario | <0.15 m | 0.15–<0.30 m | 0.30–<0.50 m | >=0.50 m | Mean cell-wise depth p05 / p95 (m) |
|---|---|---:|---:|---:|---:|---:|
| 2015-11-12 | Relative ±20% | 82.80% | 7.83% | 4.65% | 4.73% | 0.080 / 0.112 |
| 2015-11-12 | Spatial DEM ±4 m | 66.13% | 8.17% | 7.11% | 18.59% | 0.018 / 1.062 |
| 2015-11-24 | Relative ±20% | 79.05% | 9.30% | 5.57% | 6.08% | 0.105 / 0.145 |
| 2015-11-24 | Spatial DEM ±4 m | 63.27% | 8.02% | 7.15% | 21.56% | 0.011 / 1.251 |

Per-cell class probabilities sum to 1 within Float32 rounding error (observed range approximately 0.99999988–1.00000012). All probability and interval rasters retain the master grid: EPSG:32644, 30 m, 1760 × 1370. Every event/scenario raster has 30,235 or 32,627 valid cells, respectively, and NoData in all remaining cells.

## Outputs

New outputs are under `data/features/depth_scenarios/cr003_v1/`; no T6 file was changed. There are four class-probability rasters plus cell-wise depth p05 and p95 per event and scenario, and one coverage mask per event. Machine-readable run statistics are in [DEPTH_UNCERTAINTY_SCENARIOS.json](DEPTH_UNCERTAINTY_SCENARIOS.json).

Reproduce with:

```powershell
.venv\Scripts\python.exe -m pipelines.phase10.depth_scenarios --draws 100
```

The command refuses to overwrite an existing output folder or summary. These are scenario-dependent calibration proxies, not observations, calibrated uncertainty intervals, or routing inputs. The 2015 input events are not independent validation events.
