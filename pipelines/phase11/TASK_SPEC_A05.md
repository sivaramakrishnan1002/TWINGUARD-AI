# A05 task spec — forecast and hindcast wrapper

## Scope

Produce 6, 12, 24, 48 and 72 hour depth ensembles by calling the existing A06 NumPy solver on the 600 m master simulation grid. This is a historical perfect-foresight hindcast and rainfall-scenario comparison. There are no archived numerical weather forecasts for these events, so no operational forecast skill can be estimated.

## Events and windows

- 2015 peak-rain window: 2015-11-30 through 2015-12-02 UTC (72 hours ending 2015-12-02 23:00 UTC; IMERG peak on Dec 1).
- 2021 reference window: 2021-11-11 through 2021-11-13 UTC (72 hours ending 2021-11-13 23:00 UTC; independent NRSC PDF not accepted as a raster reference).
- 2023 peak-rain window: 2023-12-02 through 2023-12-04 UTC (72 hours ending 2023-12-04 23:00 UTC; PDF map remains preliminary/manual-validation only).

## Scenarios

1. Perfect-foresight event rainfall: daily IMERG CMA means distributed across each UTC day by the matching ERA5 nine-point hourly pattern, scaled to preserve each IMERG daily amount. This is not an archived forecast.
2. Rainfall-error scenarios: add the empirical 10th, 50th, or 90th percentile of the matched daily ERA5-minus-IMERG residuals to each event day's IMERG mean, clip rainfall at zero, and distribute over the same ERA5 hourly shape. These residual quantiles are scenario perturbations, not a calibrated forecast-error distribution.
3. Persistence baseline: repeat the 24 hourly rainfall values from the UTC day before the 72-hour window for all three days. This is a simple baseline, not forecast evidence.

## Model and outputs

- Reuse A06 `load_static`, `parameter_members`, `infiltration_rate`, `simulate`, and `write_tif` without editing or rerunning A06 outputs.
- Run all 20 existing Manning/infiltration parameter combinations for each event/scenario.
- Save ensemble member snapshots at each horizon, plus p05/p50/p95 GeoTIFFs. Keep cells outside the eligible simulation mask as NoData.
- Validate finite/nonnegative depths and mass-balance error <=1% for every run; record runtime, step count, forcing sequence, source hashes, and scenario provenance.
- Report depth summaries only. No flood-depth observations are available at these horizons. UNOSAT dates do not coincide with every horizon; NRSC/NDEM PDFs are not accepted reference rasters. Therefore, no forecast accuracy or skill score is claimed.

## Reproducibility

Run `.venv/Scripts/python.exe -m pipelines.phase11.run`. Seed is inherited for the fixed A06 parameter-member list; the solver itself is deterministic and has no stochastic draw. CPU/NumPy only; no packages installed.
