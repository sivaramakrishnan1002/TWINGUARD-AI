# Lane A Batch 2 — Spec loading, urban validation, independent labels, calibrated SAR, and 2D simulation

Follow docs/master/PROTOCOL.md. Lane A owns this batch; do not touch Track B. Keep data/raw read-only, never expose credentials, never run expanded Compose config, and never install packages without explicit user approval. Save new outputs only and preserve all prior Phase 9/10 results. Specs, dependencies and task status live in docs/master/STATE.json; progress is tracked in docs/batches/BATCH_2_PROGRESS.md.

## S0 — Load specifications
Register A05–A13 with complete inputs, outputs, acceptance and dependencies. Register the scoped prerequisite work as separate Lane A tasks: A04c (S1), A03d (S2), and A04d (S3). Mark ready only when dependencies are complete. Record reasonable defaults in docs/master/DECISIONS_PENDING.md.

## S1 / A04c — Urban physical layer
Replace D8 HAND with Euclidean nearest-drainage/water height, plus multi-scale relative elevation and local depression depth, defined for CMA cells wherever input data permit. Evaluate on OpenCity points using top 1%, 5%, 10%, and 20% hits against land-cover-matched chance with confidence intervals, overall and for urban points; report Phase 9C lift (PR-AUC/prevalence) where applicable. Label the layer PHYSICAL, NOT FITTED TO LABELS. Preserve old HAND. New outputs: pipelines/phase9c/urban_physical.py, data/features/terrain/urban_physical_v1/, tests/phase9c/test_urban_physical.py, docs/URBAN_PHYSICAL_LAYER.md.

## S2 / A03d — GeoPDF map labels and out-of-event check
Time-box map processing. For the 2023 NDEM PDF, inspect embedded georeferencing, extract the red flood/standing-water legend class, polygonise, and QA using overlay, legend-colour check, and OSM control-point error. Resolve the 2021 NRSC CRS inconsistency first; if not resolvable, mark manual-needed. Skip absent December maps. Load only QA-accepted geometry as DERIVED-FROM-MAP tier B (<= one grid cell error) or C. Test the Phase 9C model trained on November 2015 against the 2023 map within assessed cells; compare with S1 physical layer everywhere and report lift. State that RISAT-1A preliminary maps may include standing paddy water. New outputs: data/processed/pdf_maps/batch2/, data/features/labels/map_batch2/, docs/GEO_PDF_LABELS_BATCH2.md, docs/PHASE9C_OUT_OF_EVENT_2023.md, scripts/tests in Lane A paths.

## S3 / A04d — Calibrated SAR candidate labels
Time-box. For the 24 Nov 2015 scene, train a small model using VV, VH, dB change, HAND, slope and land cover with spatial-block CV. Evaluate held-out IoU, precision and recall. Preregistered acceptance: tier C only if held-out IoU >=0.25; otherwise tier D and stop. If accepted, apply unchanged to 6 Dec 2015 (19 Oct and 24 Nov references) and 16 Nov 2021 (23 Oct and 4 Nov references), then compare with GFD event 4309, OpenCity points, and accepted S2 maps. State that UNOSAT may use the same scene; held-out IoU only measures reproduction of its mapping method, not independent flood accuracy. Never call these labels ground truth. New outputs: data/features/labels/sar_calibrated_batch2/, docs/SAR_CALIBRATED_LABELS_BATCH2.md, scripts/tests in Lane A paths.

## A06 — 2D shallow-water simulation
Implement a NumPy local-inertial shallow-water solver (Bates 2010 style) on cleaned DEM; choose 30 m or coarser by measured runtime and justify. Use land-cover Manning roughness; model buildings by an explicitly stated assumption (default: porosity, not DSM obstacles); document drainage/infiltration losses by land cover as assumptions because no storm-drain network exists. Define sea/river boundaries. An optional CAG figure for 1–2 Dec 2015 can be an explicitly labelled reservoir scenario input, not observed release truth. Run >=20 parameter members, calibrate on Nov 2015 UNOSAT with spatial-block holdout; validate against GFD, OpenCity and accepted S2 map layers when available. Check stability, mass balance within 1%, and runtime. Output peak/selected-hour depth mean, p05, p95 under the existing depth-field contract. State limitations: no drain network, GLO-30 is not a building DSM, few events, no hydraulic-accuracy claim. New outputs: pipelines/phase12/, data/features/simulation/batch2_v1/, docs/PHASE12_SIMULATION.md, tests.

## A05 — Forecast/hindcast wrapper
At horizons 6, 12, 24, 48, 72 h, map rainfall scenarios through A06 to depth ensembles. No archived NWP forecasts exist for 2015: characterize skill only with perfect-foresight hindcasts, rainfall-error ensembles derived from IMERG/ERA5 differences, and persistence baselines. State this limitation plainly. New outputs: pipelines/phase11/, data/features/forecast/batch2_v1/, docs/PHASE11_FORECAST_BATCH2.md, tests.

## A07 — Impact
For each time/ensemble step, estimate edge-passability probability using depth threshold 0.30 m and sensitivity 0.15–0.50 m; preserve WorldPop NoData as NoData. Report population exposure distributions, facility-access loss, and hospital/shelter cascades. Write only to the existing impact result schema using its approved contracts. Outputs: pipelines/phase13/, data/features/impact/batch2_v1/, docs/PHASE13_IMPACT_BATCH2.md, tests.

## A08 — Time-dependent graph
Document speed reduction with depth as an assumption; block edges above threshold. Treat bridges and tunnels separately, with underpasses assumed to flood first. Store compact snapshots per time step and ensemble member. Outputs: pipelines/routing/, data/features/routing/time_dependent_batch2/, docs/ROUTING_GRAPH_BATCH2.md, tests.

## A09 — Routing
Evaluate static, current-state flood-aware, forecast-horizon-aware time-dependent, and uncertainty-aware routing (expected delay plus failure-probability constraint). Use an observing-system simulation experiment: one simulation member is hidden truth, other members provide forecasts. Report route failure and expected exposure. State plainly that the truth is simulated. Outputs: data/features/routing/results/batch2_v1/, docs/ROUTING_BATCH2.md, tests.

## A10 — Shelter allocation
Use OSM shelters plus schools/colleges as a candidate set, explicitly an assumption. Flag capacity assumptions. Allocate capacity under flood access and assign population from WorldPop to nearest network nodes, keeping NoData as NoData. Outputs: data/features/decision/shelters/batch2_v1/, docs/SHELTER_ALLOCATION_BATCH2.md, tests.

## A11 — Priority zones
Combine hazard probability, exposure, access loss and a documented vulnerability proxy; perform weight sensitivity analysis. Outputs: data/features/decision/priority_zones/batch2_v1/, docs/PRIORITY_ZONES_BATCH2.md, tests.

## A12 — Explainability
Compute permutation importance and partial dependence for the data-driven model; run parameter sensitivity across simulation members. Outputs: experiments/explainability/batch2_v1/, docs/EXPLAINABILITY_BATCH2.md, tests.

## A13 — Decision lab
Compare evacuate now versus one hour later, bridge X closed, and shelter unavailable. Define confidence as the ensemble fraction in which option A beats B. Run H2–H5 paired bootstrap experiments. Keep all decisions as simulations, not live guidance. Outputs: experiments/decision_lab/batch2_v1/, docs/DECISION_LAB_BATCH2.md, tests.

## S5 — Report and closure
Write docs/PHASE12_SIMULATION.md and a concise status. Update STATE.json, CHANGELOG.md, NEXT.md and DECISIONS_PENDING.md; run task tests and raw audit; commit Lane A paths only. Continue by the master protocol until a stop condition or ready gate. Never touch Track B.
