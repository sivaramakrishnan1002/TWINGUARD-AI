# A06 execution record — Phase 12 simulation

Source: `docs/batches/BATCH_2.md`, A06 section. Registered outputs: `pipelines/phase12/`, `data/features/simulation/batch2_v1/`, `docs/PHASE12_SIMULATION.md`, and `tests/phase12/`.

## Acceptance items

- NumPy local-inertial solver on cleaned DEM; choose 30 m or coarser using measured runtime.
- WorldCover Manning classes; documented building representation; land-cover infiltration/drainage assumptions; explicit water boundaries.
- At least 20 parameter members; spatial-block holdout calibration to November 2015 UNOSAT; compare GFD, OpenCity and accepted A03d maps when available.
- Numerical stability, relative mass balance at or below 1%, runtime, peak/selected depth mean/p05/p95 and limitations under the depth-field contract.

## Chosen defaults

- 600 m cells (20 × 20 native cells), EPSG:32644, aligned with the 30 m raster origin; 72 UTC hours per November map date.
- Rainfall uses local IMERG daily CMA means, with the ERA5 nine-point hourly UTC shape scaled to the IMERG daily amount. Spatially uniform CMA forcing; no invented spatial downscaling.
- Five 3 km block folds and a 3 km buffer. Coarse label cells are positive at 10% mapped subcell area; training-fold thresholds are selected from 1, 3, 5, 10, 15, 30 and 50 cm.
- Twenty members span fixed Manning and infiltration multipliers. Building porosity is 0.70 for coarse cells at least 50% built-up. Separate storm-drain loss is zero because there is no network/throughput evidence; mapped water is the only open-drain boundary.
- Fixed seed 20261026. Derived uncertainty percentiles represent parameter spread only.

All numeric values, input SHA-256 values, limitations, tests, raw audit and the commit are recorded in `docs/PHASE12_SIMULATION.md` and the task finish record.
