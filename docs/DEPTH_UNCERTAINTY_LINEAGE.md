# Depth scenario lineage (A03c)

| Output | Inputs | Method | Key parameters | Validation |
|---|---|---|---|---|
| `data/features/depth_scenarios/cr003_v1/` | Existing T6 mean-depth rasters; matching UNOSAT event extent rasters; cleaned elevation; CMA mask | Relative depth perturbation and spatially varying DEM-error perturbation; recompute connected-component boundary water surfaces for the latter | 100 draws, seed 20261025, Gaussian smoothing sigma 10 cells (about 300 m), relative error bounded ±20%, spatial DEM error bounded ±4 m | 30 m master-grid alignment; all class probabilities sum to 1 within Float32 precision; coverage and NoData counts checked; common +4 m DEM datum offset changes depth by 0 m |
| `docs/DEPTH_UNCERTAINTY_SCENARIOS.json` | Same as above | Machine-readable run summary | Same as above | Records event coverage, scenario class probabilities, ensemble depth quantiles and common-bias test |

The source raster extents have 94,195 cells (12 Nov) and 109,067 cells (24 Nov); valid T6 depths cover 30,235 and 32,627 cells respectively. These are calibration proxies, not depth observations, calibrated uncertainty bounds, or routing inputs. See `DEPTH_UNCERTAINTY_SCENARIOS.md` for numerical results and limitations. The raw-data audit matched all 157 files and hashes after the run.
