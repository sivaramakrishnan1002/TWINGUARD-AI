# Research foundation

## Research gap and novelty

The intended research gap is not “flood AI is new.” The user’s literature notes say that reviewed work advances individual capabilities, while the team has not yet found a Chennai study that tests forecast uncertainty all the way through road accessibility, evacuation and shelter decisions in one connected pipeline. This is a provisional gap statement based on titles and abstracts supplied by the user; it is not a completed systematic review. [user]

The proposed contribution is to build and experimentally test a decision-centred workflow: combine evidence, carry uncertainty into impacts and route choices, then compare actions. Do not claim this is the first such system. [user]

## Proposed contributions

| ID | Proposed contribution | Status |
|---|---|---|
| C1 | Multimodal flood intelligence using weather, satellite, terrain/GIS and, if adequate, reservoir telemetry. | Proposed; no flood model trained. [user; repo: `docs/PROJECT_STATUS.md`] |
| C2 | Carry uncertainty from predicted flood extent into exposure and road access. | Proposed. [user] |
| C3 | Predictive, time-aware evacuation routing and shelter choice. | Proposed; graph connectivity still needs validation. [repo: `docs/PHASE3_LOG.md`] |
| C4 | A decision-centred twin for comparing alternative actions. | Proposed. [user] |
| C5 | A fast rain-and-storage alert track. | Proposed; exploratory retrospective screen exists, not a validated alert model. [repo: `docs/PHASE3_LOG.md`] |

The final contribution list is still open for the student team to update and approve. [user]

## Hypotheses and test direction

| Hypothesis | Proposed comparison | Evidence needed |
|---|---|---|
| H1: Multimodal inputs improve flood prediction over single modalities. | Weather-only, terrain-only, satellite-only where labels support it, then fused inputs. | Defensible date-matched flood labels and leakage-safe splits. [user] |
| H2: Explicit uncertainty improves calibration. | Deterministic output versus probabilistic/interval output. | Held-out observed events and calibration measures. [user] |
| H3: Passing flood uncertainty into road-access estimates supports safer evacuation. | Deterministic route risk versus uncertainty-aware route risk. | Validated road graph, time-matched flood conditions, route outcomes. [user] |
| H4: Horizon-aware routes fail less often than routes chosen from current conditions. | Current-state shortest/safest path versus predicted journey-time risk. | Time-varying flood/road observations. [user] |
| H5: Counterfactual twin simulation improves decision quality over a static risk map. | Compare decisions under alternate closures, departure times and shelter availability. | Defined decision outcomes and evaluation protocol. [user] |
| Track B: storage plus rainfall may provide useful warning lead time. | Retrospective rule screen against documented event timing. | Historical capacities, releases and complete flood outcomes. Existing screen is only illustrative. [repo: `data/features/reservoirs/illustrative_track_b_backtest.json`] |

No success thresholds have been selected. Set them after baselines and data review. [user]

## Literature supplied for review

The project brief says the following works were checked only by title and abstract, except where explicitly noted. The links have not been opened during this task. Treat details and relevance as user-supplied leads, not verified citations. [user]

| Work (short title) | Year | What it may contribute | Status |
|---|---:|---|---|
| “Digital Twin Technology for Urban Flood Risk Management” (Remote Sensing 17(17):3104) | 2025 | Review of urban flood digital twins and remote sensing. | Title/abstract only; supplied URL. |
| Taghikhah et al., digital-twin disaster decision support review | 2025 | Frameworks for disaster decision support. | Title/abstract only; supplied URL. |
| University of Hertfordshire, flood visualisation technologies review | 2024 | Visualisation methods for flood management. | Title/abstract only; supplied URL. |
| Razavi et al., generative-AI-aided flood twin | 2024 | Example of AI and twin integration. | Title/abstract only; supplied URL. |
| Chennai extended Elman/spiking-neural-network flood prediction | 2025 | Chennai rainfall/flood prediction comparison. | Title/abstract only; supplied URL. |
| Chennai flood susceptibility mapping | 2024 | Chennai spatial susceptibility baseline context. | Title/abstract only; supplied URL. |
| Chennai high-resolution topography monitoring/simulation | 2026 | Terrain-based local flood modelling. | Title and venue only; supplied URL. |
| IIT Madras Sentinel-1A Chennai flood mapping page | Date not shown | Potential 2015/2021 remote-sensing context. | Research page lead; supplied URL. |
| Pianforini et al., transformer flood-map forecasting for dam breaks | 2024 | Forecasting model design. | Title/abstract only; supplied URL. |
| FloodSformer | 2025 | Transformer-based flood modelling lead. | Title/abstract only; supplied URL. |
| Lou et al., CNN-ConvLSTM urban flood forecasting | 2026 | Deep-learning forecast baseline lead. | Title/abstract only; supplied URL. |
| Peng et al., Bayesian deep learning for disaster prediction | 2025 | Uncertainty methods. | Title/abstract only; supplied URL. |
| Albared, Beise and Stueber, Natural Hazards paper | 2025 | Uncertainty/hazard prediction lead. | Title/abstract only; supplied URL. |
| Saberian et al., EGU abstract | 2026 | Uncertainty research lead. | Conference abstract lead; supplied URL. |
| TerraMind flood mapping preprint | 2025 | Satellite multimodal/foundation-model lead. | Preprint lead; supplied URL. |
| Presto sensor-adaptive flood mapping preprint | 2025 | Sensor-adaptive satellite mapping lead. | Preprint lead; supplied URL. |
| Huang et al., real-time heuristic evacuation pathfinding | 2024 | Flood-aware route methods. | Supplied URL marked for checking. |
| Yoon and Lee, flood-aware evacuation after dam collapse | 2026 | Journey safety under flood scenarios. | Citation details supplied; verify before use. |
| Compound building-road-emergency-facility flood network | 2024 | Cascading spatial network impact assessment. | Title/abstract lead; supplied URL. |
| ASCE safe evacuation and rescue route framework | 2024 | Evacuation/rescue routing methods. | Citation lead; supplied DOI. |

Background sources supplied: CAG’s Chennai flood audit executive summary and IISc ICWaR’s 2015 rapid assessment. The project context says sources describe the role of Chembarambakkam releases and extreme rain differently; the handbook takes no side. The full CAG report was not collected; the executive summary is present. [user; repo: `docs/DATA_MANIFEST.csv`, `docs/MANUAL_TODO.md`]

## Claim discipline

The reservoir-release element may be a useful local research angle, but the user’s supplied search did not find a Chennai paper treating release as a first-class input. This needs a fuller literature search before any gap or novelty claim. Never say “first.” [user]
