# Roadmap and next steps

## Immediate order

The next step is **not automatically Stage 7**. First resolve open data decisions and the remaining database restore acceptance check; then start only the next approved phase. [repo: `docs/MANUAL_TODO.md`; user]

1. Confirm older versus expanded CMA boundary and record final choice.
2. Review GLO-30 coastal elevations and urban drainage artefacts; choose a documented hydrology-conditioning approach before interpreting flow accumulation/TWI.
3. Choose a defensible flood-label plan: seek December 2015 GIS labels; assess PDF digitising; decide how validation scope changes if they remain unavailable. Keep all label types distinct.
4. Reconcile OSM source/extract counts; validate directed road connectivity and facility-to-network mapping before routing.
5. Verify NASA POWER and Kaggle rainfall units, WorldPop/census comparability, reservoir historical capacities, Sentinel reuse terms, and licenses/attribution.
6. Complete the Stage 5 backup restore into a separate temporary database using an authorized role with `CREATEDB`; local PostgreSQL 18.6/PostGIS 3.6.2, schema and GIS layers are already verified. Docker remains stopped.
7. Confirm boundary and label strategy, review invalid flood geometries and source licences before Stage 7/API work or model training.

These tasks and dependencies are recorded in `docs/MANUAL_TODO.md` and the Part B handoff. [repo]

## Remaining roadmap: inputs, outputs and acceptance checks

The table expands the user's 26-phase plan. These are proposed scopes, not a schedule. All time estimates are **[estimate, to be agreed]** and are intentionally omitted until team capacity and deadlines are known. [user]

| Phase | Main inputs → outputs | Minimum acceptance evidence / dependency |
|---:|---|---|
| 4 Preprocessing/alignment | Raw sources → versioned, aligned modelling tables and rasters. | Boundary, CRS, units, timestamps, nodata, provenance and label policy approved; source data unchanged. |
| 5 Database | Schema, grid and selected layers → PostgreSQL/PostGIS. | Local connection works; spatial extension verified; migrations, backups, secrets and port documented. |
| 6 GIS layers | Loaded boundary, roads, hydrology, labels, facilities → queryable GIS layers. | Counts and spatial queries reproduce documented samples; metadata and licensing retained. |
| 7 Twin foundation | Database layers and time model → versioned twin state and scenario API. | State updates reproducibly; data time and freshness visible; audit trail works. |
| 8 Historical flood dataset | Observations, PDF-derived labels, SAR products → dated label registry. | Label source/type/confidence are explicit; event timing and coverage are checked. |
| 9 Baseline ML | Leakage-safe features and labels → simple baseline models. | Held-out split by event/time; baseline metrics and reproducible run record. |
| 10 Risk mapping | Baseline output and geography → interpretable risk map. | Calibration/uncertainty caveats shown; map aligns and can be traced to run inputs. |
| 11 Forecast modelling | Sequences and labels → forecast model candidates. | Compare with baseline; no future leakage; independent event evaluation. |
| 12 Flood simulation | Terrain and model forecasts → evolving flood-state scenarios. | Hydrology assumptions documented and checked against observations. |
| 13 Impact/cascading risk | Flood scenarios plus assets/population → impact estimates. | NoData and asset completeness exposed; impact unit and uncertainty defined. |
| 14 Road graph | OSM road network and flood exposure → validated directed graph. | Components, access restrictions, bridges, turn/connectivity rules and snapping documented. |
| 15 Evacuation routing | Time-varying road risk → candidate safe routes. | Compare with deterministic baseline; report route failure/exposure and uncertainty. |
| 16 Shelter ranking/allocation | Shelters, capacity and routes → assignment options. | Capacity sources verified; inaccessible and full shelters handled; alternatives visible. |
| 17 Emergency priorities | Impacts and response resources → priority queue. | Transparent criteria, review/override and equity considerations tested. |
| 18 Explainable AI | Models and decisions → reasons and uncertainty display. | Explanations checked against model behavior; no unsupported causal language. |
| 19 Temporal Transformer | Longitudinal data → sequence-model experiment. | Baselines and event-separated evaluation first; complexity justified. |
| 20 Satellite vision | Sentinel-1 plus defensible labels → SAR segmentation experiment. | Processing, license, label quality, urban/rice/water ambiguity and orbit matching documented. |
| 21 Multimodal fusion | Weather, satellite, terrain and other modalities → fused model. | Ablations show modality contribution; missing-modality behavior tested. |
| 22 Uncertainty/decision evaluation | Probabilistic forecasts and decisions → calibration and decision comparisons. | Reliability and route/decision metrics; thresholds chosen after baselines. |
| 23 Command centre | Validated APIs/results → operator map/interface. | Usability, warnings, stale data and uncertainty displayed; not mistaken for official alerts. |
| 24 Integration | Services, database, models and UI → end-to-end prototype. | Automated integration checks, traceable decisions and failure recovery. |
| 25 Historical validation | Held-out events and decision scenarios → final evaluation. | Event leakage addressed; limitations and failed hypotheses reported. |
| 26 Deployment/paper | Integrated prototype and results → reproducible handoff and thesis/paper. | Security, licence, test, deployment and supervisor review completed. |

## Scope cut list if time is short

The user’s brief identifies graph neural networks, foundation-model experiments, tide/surge, and soil-moisture estimates as optional or stretch work. Drop these before compromising label quality, baselines, validation, and honest uncertainty reporting. Redis/Kafka should remain only if a real stream-processing job justifies them. [user]

## Blockers

The immediate blockers are boundary and label decisions, incomplete release records, validation of the road graph, unit/licence checks, and unconfirmed local database setup. The final validation scope may need to narrow if observed December 2015 and PDF-derived labels remain unavailable. [repo: `docs/MANUAL_TODO.md`; user]
