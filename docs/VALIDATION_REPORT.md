# Phase 25 validation report — A05, A06, A09

## Plain-language outcome

The checks show that the three pipelines produced internally consistent files and simulation records. They do **not** establish flood-depth accuracy or real-world forecast or route skill. There are no independent, date-matched depth observations for these windows, no accepted 2021/2023 raster flood labels, and no observed route outcomes. A06 has spatial holdout scores against the November 2015 UNOSAT map used in its calibration workflow; that is same-episode mapped-extent reproduction, not independent hydraulic validation.

## Validation matrix

| Product | Registered target/split and baseline | What was verified | Scientific validation result |
|---|---|---|---|
| A05 forecast/hindcast scenarios | Three 72-hour UTC event windows; five rainfall scenarios per window; 20 A06 members; horizons 6, 12, 24, 48 and 72 h. Rain-error q10/q50/q90 and previous-day persistence are scenario contrasts. | 300 member-runs, all finite and nonnegative; maximum relative mass-balance error 0.005907 (0.591%). 225 output GeoTIFFs, all float32 on the 88×69 EPSG:32644 grid at 600 m, each with 2,430 valid cells and −9999 NoData. | **Unavailable.** No archived NWP forecast or observed lead-time depth reference. Perfect-foresight IMERG uses hindsight; rainfall differences are not calibrated forecast errors. No forecast-skill score is claimed. |
| A06 shallow-water simulation | Two November 2015 UNOSAT event-map targets (12 and 24 Nov), 20 parameter members per map, five buffered 3 km spatial folds; thresholds and isotonic calibration fit on training blocks. Baseline-water/sea excluded as documented. | 40 runs, all finite and nonnegative; maximum relative mass-balance error 0.002633 (0.264%). 12 depth rasters, each float32, EPSG:32644, 600 m, 2,430 valid cells, −9999 NoData. | Same-episode map-reproduction metrics are available: 12 Nov ROC-AUC 0.673±0.045, PR-AUC 0.143±0.043, Brier 0.064±0.019, ECE 0.029±0.019, F1 0.214±0.085, IoU 0.122±0.052; 24 Nov 0.698±0.018, 0.169±0.057, 0.078±0.015, 0.042±0.046, 0.241±0.077, 0.139±0.048. These are buffered spatial-fold scores on the same 2015 mapping episode and are not independent flood-depth or event validation. |
| A09 route comparison | Six graph OD probes; 3 events × 3 horizons × 4 methods; member 20 hidden as simulated truth, members 1–19 forecast. Methods: static, current flood-aware, horizon-aware, uncertainty-aware. | 216 route records; output verifier passed schema and NoData checks. Graph has 508,854 nodes and 1,071,656 directed arcs; 768,688 arcs (71.73%) have mapped A07 depth cells, while 302,968 (28.27%) are unassessed or ambiguous. | OSSE only. Among 54 records per method, paths exist for 54 static, 18 current, 18 horizon-aware and 15 uncertainty-aware. Assessed simulated-truth failures are 0/0, 2/18, 2/18 and 0/15 respectively. Static route probability is unavailable because every sampled static route crosses unassessed edges. These are not observed route outcomes or real accessibility probabilities. |

The A06 block-fold metrics do not demonstrate generalization to a separate flood. Average parameter-member p05/p95 values are spread across simulation members, not calibrated 90% coverage. A09 accessibility fractions are proportions among 19 scenario members, not calibrated real-world probabilities. A05 percentile depth rasters likewise do not establish calibrated uncertainty coverage.

## Coverage, timing, units, and physical caveats

- A05 event windows are recorded in UTC. The 2015 scenario is a perfect-foresight hindsight replay, not an operational forecast. The 2021 NRSC map is PDF-only and the 2023 NDEM map is preliminary/not accepted. The December 2015 peak has no accepted official vector extent.
- A06 documented output depth unit is metres; the model uses a 600 m coarse grid. The DEM is a surface model, and simplified mapped-water sinks, land-cover roughness/infiltration assumptions, and the lack of storm drains/external catchment inflow limit physical interpretation. There are only two November 2015 event-map targets.
- A09 departure and valid-time snapshots are UTC and discrete; no intermediate flood state is invented. A topological route is separate from assessed flood accessibility. Missing or structurally unassessed edge depth is unknown, not dry/passable. Bridges lack deck elevation and remain unassessed; thresholds and speed reductions are assumptions.
- **GeoTIFF metadata issue:** the inspected A05 and A06 rasters report CRS EPSG:32644, 600 m resolution, float32 and −9999 NoData with the tag “outside assessed CMA; not dry.” Their band unit metadata is None (no explicit unit tag). Product documentation says depths are metres, but the files themselves do not encode that unit. This report flags the gap; source rasters were not modified.
- No CRS reprojection or resampling was performed for these checks. The A05/A06 rasters share 88×69 grids and EPSG:32644. The route graph uses projected metric coordinates; route geometry coverage remains limited by the edge-to-cell mapping above.

## Artifact paths and checksums

SHA-256 values were computed read-only. A05/A06 raster collection digests below are SHA-256 of the UTF-8 manifest formed by sorting relative paths and writing each relative path, a tab, its individual file SHA-256, and a line feed.

| Artifact | Path | Bytes or count | SHA-256 |
|---|---|---:|---|
| A05 run summary | data/features/forecast/batch2_v1/forecast_summary.json | 231,233 bytes | 0bc0e322041c0d264a214d995912fd648fbda3534616f3e4588122e292e94dba |
| A05 GeoTIFF set | data/features/forecast/batch2_v1/ | 225 TIFFs | 44474a1e6853805d6e87297fa120e6f151fe71fbbc8942da9432a943306d807c |
| A06 run summary | data/features/simulation/batch2_v1/simulation_summary.json | 33,795 bytes | 58f736b54a4b4971fcade55f653cc6d86867c66eec612b16d184d9c93f365697 |
| A06 selected spatial-CV results | data/features/simulation/batch2_v1/selected_model_spatialcv.json | 5,738 bytes | 2e48fd346f61d5b47344f0549d9284028583c2615a4a2e8e8a6f8522203167e1 |
| A06 selected-model cross-check | data/features/simulation/batch2_v1/validation_summary_selected_model.json | 1,809 bytes | 7bc7b781bc9faaf3451887ba4ce752f6645ae7b52559d3be26d6cb269719e39b |
| A06 GeoTIFF set | data/features/simulation/batch2_v1/ | 12 TIFFs | 15a7deea044c521a0d205754ab92877094b8c0b6fa31ac4728c9a83566f54c76 |
| A09 route records | data/features/routing/results/batch2_v1/revision_3/route_results.jsonl | 11,349,907 bytes | ee4e33b45268ba869cfc0f3f48eee1c10ac2c5ae83837b1d82165c6ca6c2ea7f |
| A09 comparison metrics | data/features/routing/results/batch2_v1/revision_3/comparison_metrics.csv | 15,497 bytes | b21f007f94c7307b8b0dee5d0500072f30462d66be20ac5a955cc13f42eea6ad |
| A09 run summary | data/features/routing/results/batch2_v1/revision_3/summary.json | 3,503 bytes | 3d0784a481aaaf451456e9e9f1bb1291461bb0a3680b6cc7019335d0501adc3b |

The A05/A06 run summaries carry their source input hashes. The A09 summary carries source hashes for the graph, A08 snapshots, A05 scenario and A07 impact artifacts. Run seeds are A05/A06 20261026 and A09 20261027; recorded runtimes are 687.71 s, 68.03 s and 49.956 s respectively.

## Commands and results

Commands run:

- .venv\Scripts\python.exe pipelines\routing\phase15_routing.py --verify-only --output data\features\routing\results\batch2_v1\revision_3 — 216 route records; schema PASS; NoData PASS.
- .venv\Scripts\python.exe -m pytest -q tests\routing tests\labels tests\explainability tests\phase8 tests\phase9 tests\phase9b tests\phase9c tests\phase10 tests\phase11 tests\phase12 tests\phase13 tests\decision tests\temporal_models --import-mode=importlib — 116 passed.
- .venv\Scripts\python.exe tools\audit_raw_logs.py — DATA_FILES=157; DATA_BYTES=30544672450; HASH_MATCH=157; NO_COMPARABLE_HASH=0; MISMATCH=0.

The read-only checks also reopened all 237 A05/A06 GeoTIFFs and inspected their grids, dtype, NoData, coverage and finite/nonnegative values. No files under data/raw/ were modified. CUDA was not used for these audits; GPU computation was not material to file and summary validation. The existing solver runs were CPU and retained their registered numerical method.

No figure was added: there are no independent scored validation observations to visualize, and the evidence is more clearly reported in the matrix above.

## Limitations and next evidence needed

1. Independent, date-matched flood extent/depth references for 2021/2023 or the December 2015 peak, after georeferencing and QA.
2. Gauge or surveyed depth/water-level observations on the A06 grid and time steps.
3. Observed road closure/access and route travel-time outcomes to evaluate A09 outside its OSSE.
4. Add explicit unit metadata to future depth rasters; preserve current files and their hashes.
