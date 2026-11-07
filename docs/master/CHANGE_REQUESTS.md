# Shared change requests

| ID | Request | Status | Decision/evidence |
|---|---|---|---|
| CR-001 | Track B migration 100 adds twin alert/reservoir state linkage | authored, not applied | File exists; DB shows migrations only through 014. Apply at an authorized integration gate after collision review. |
| CR-002 | Phase 9C urban label censoring, independent point validation, and spatial Mondrian conformal calibration | implemented with caveats | Lane A A04b committed as `553a1fc3ff7aa8d23e20bc51315db64964754fac`; Phase 9 labels and prior outputs preserved. Only 111/945 OpenCity points had scores and hit rates were below dominant-class-matched chance; single SAR-derived event only. |
| CR-003 | Label Strategy V2, SAR separability diagnostic, PDF-map georeferencing preparation, Phase 10 without out-of-event validation, and depth uncertainty scenarios | approved/in progress | User-authorized Lane A work: A03b (L1–L3, with 30/20/120 minute subtask caps), A03c (L5, 60 minutes), and reopened A03 (L4, 90 minutes). Raw inputs are immutable; map-derived labels remain Tier B/C only after georeferencing QA. |

Changes to existing shared tables must add nullable columns only and be recorded here before merge.


| CR-004 | Phase 9C eligibility and hazard feature audit; remove population-NoData eligibility; exposure-free hazard models; revise Phase 10 coverage display | implemented with caveats | A04b corrected on 2026-10-25. WorldPop NoData is not a hazard mask or predictor; 25,551 positive cells audited. OpenCity ranking did not beat matched chance overall; single SAR-derived event. A03 composite refreshed to phase10_cr004_v9. |

| CR-005 | Lane A Batch 2: urban physical layer, GeoPDF map validation, calibrated SAR diagnostic, shallow-water simulation and downstream forecast/impact/routing/decision tasks | approved by user 2026-10-25 | Task specs and dependencies registered in STATE.json; raw data immutable; new versioned outputs only; simulated outputs are not live guidance. |

| CR-006 | Add a time-stepped 3D flood-scenario visualization to TwinGuard | approved by user 2026-10-27; phased tasks registered | Sequence: A20 audits/exports science-backed visualization time series after A15; I07 defines a separately versioned post-G0 display contract; B17 serves bounded read-only scenario assets after G0 and service prerequisites; B18 adds accessible MapLibre 3D timeline with 2D fallback; I08 runs end-to-end replay acceptance. Current A06/A05 products are 600 m scenario outputs with coarse time steps and assumption-based hydraulics; the first visualization must not claim street-scale flow, validated hydraulic accuracy, live warning, or emergency guidance. Existing outputs and raw data remain immutable; version new outputs. |

| CR-007 | A11 priority-zone scope revised to separate hazard, population exposure, and facility access-loss outputs without vulnerability labels or a weighted composite ranking | approved by project owner 2026-10-28; awaiting Lane A owner acknowledgement | WorldPop is exposure, not vulnerability; no suitable sourced vulnerability layer was found. The Integrator updated A11's master acceptance; A11 remains blocked until Lane A acknowledges the revised output/schema/test scope. Any future vulnerability weighting requires a separate approved method and evidence. |

| CR-008 | B08 deterministic selection of registered A07/A09 artifact results | approved by project owner 2026-10-29; I14 versioned projection in progress | A07 `(run_id, valid_at, scenario_key)` uniquely selects saved results; A09 `result_id` is unique only within saved revision 3 and no integer run mapping exists. Approved: add the dedicated impact selector and a separate revision-3-scoped saved-result lookup; keep `POST /route` unavailable absent a supported route-run mapping. Preserve C7/C8 response schemas. C4 v0 remains frozen; any new request/operation semantics are separately versioned through I14. See `docs/master/CR-008_B08_ARTIFACT_SELECTORS.md` and `docs/CR008_LANEA_SELECTOR_EVIDENCE.md`. |

| CR-009 | Activate proposed C9 read-only catalog and exact-detail operations in AI service and Spring backend | approved by project owner 2026-10-30; Integrator review I16 complete; implementation registered as B21 | Both existing GET paths only; approved 400 invalid input, 404 no exact match, 409 duplicate/ambiguous identity on catalog or detail, 503 missing/unreadable/unavailable asset with no partial result. C9 remains proposed/unfrozen and separate from frozen C1–C8. No live feeds, predictions, alerts, routing, database writes, migrations, or science regeneration. Decision: `docs/master/CR-009_C9_ROUTE_ACTIVATION.md`. |
| CR-010 | Add a bounded exact read-only A20 GeoTIFF delivery operation for the B18 browser map | approved by project owner 2026-10-30; Integrator review I19 in progress; implementation B23/B24 | AI-service-only additive proposed C9 v1 operation returning exact manifest-selected Float32 GeoTIFF bytes after selector, containment, size, SHA-256, and TIFF-metadata validation. Exact CORS approval: `http://127.0.0.1:8081`, GET, Accept, no credentials. No arbitrary paths, tile generation, transformation, science regeneration, live feeds, DB writes, or migrations. Decision: `docs/master/CR-010_C9_RASTER_DELIVERY_DECISION.md`. |
| CR-013 | Final-year architecture rebaseline: bounded real-time-style Chennai flood digital-twin prototype | planning proposal recorded 2026-10-31; owner/domain decisions pending; no implementation authorized | Target is timestamped rainfall/reservoir replay or separately approved feeds, time-stepped scenarios, 3D presentation, and impact/access/shelter analyses with explicit provenance/uncertainty. Novelty is provisional pending literature review. Data rights, terrain/datum, authoritative timestamped sources, independent validation, hardware, model criteria, and deployment boundary require owner decisions. Existing results and caveats are preserved; G5/G6 remain not_ready; C1–C8 frozen v0 unchanged; C9 proposed/unfrozen. See `docs/master/FINAL_YEAR_ARCHITECTURE_REBASELINE.md` and `docs/master/FINAL_YEAR_OWNER_DECISIONS.md`. |
| CR-014 | Use Open-Meteo Forecast API for Chennai weather-model context in local educational prototype | approved by project owner 2026-11-06; bounded to public no-key non-commercial model data display | Current model estimates and hourly precipitation may appear with provider valid time, fetch time, model-output labeling, CC BY 4.0 attribution, and provider limits. Not gauge observations; does not drive existing flood simulation, alerts, impacts, routes, shelters, or reservoir values. No persistence, credentials, backend route, or C1–C8/C9 changes. See `docs/master/CR-014_OPEN_METEO_WEATHER_CONTEXT.md`. |
| CR-015 | Bounded Open-Meteo spatial rainfall snapshot for A06 feasibility and one possible research run | approved by project owner 2026-11-06; conditional on A23 feasibility gate | Authorizes only one minimum-requests, terms-compliant unauthenticated precipitation snapshot over the A06 domain and a complete 72-hour window, retained under `data/features/weather/openmeteo_a06_domain_v1/`; one versioned research-only A23 run is allowed only if feasibility passes. No recurring/live solver, credentials, other provider, downstream API/UI, or operational use. CR-014 remains unchanged. See `docs/master/CR-015_OPEN_METEO_GRID_FORCING_RESEARCH.md`. |


## CR-016 — Public CFM-DSS reservoir dashboard source

Approved 2026-11-06 for low-volume, on-demand, non-operational academic prototype reads from the publicly accessible Chennai Flood Monitoring dashboard. The decision does not claim source-owner endorsement, formal terms, operational freshness, or permission to redistribute. Preserve date-only C3 semantics; see `CR-016_PUBLIC_RESERVOIR_DASHBOARD_SOURCE.md`.

## CR-017 — On-demand CFM-DSS reservoir snapshot API

Approved 2026-11-06; implemented by B44. See `CR-017_CFM_RESERVOIR_SNAPSHOT_API.md`.

## CR-018 — Live prototype integration

Approved 2026-11-07 under the owner's delegated authority: same-origin `/api/ai/` proxy, B45 live reservoir panel, and live recomputation runs as later sections are added. See `CR-018_LIVE_PROTOTYPE_INTEGRATION.md`.

## CR-015 note — request disclosure and supersession (2026-11-07)

A23 disclosed extra preparatory Open-Meteo requests beyond the single retained 3-model snapshot (`docs/PHASE12_OPEN_METEO_GRID_FEASIBILITY.md` item 5): one 2-point probe per candidate model (11 requests) and one 0.03° trial across four models, in which GFS returned HTTP 429. These trial responses were neither retained nor used. They exceeded CR-015's "minimum request set" wording only by small preparatory probes, and are recorded here for transparency. CR-015's one-snapshot/no-polling limit is now replaced by OD-2026-11-07 item 7: on-demand, cached, 600 s minimum interval, no background polling.

## CR-019 — Product rebaseline: reference UI, Google 3D Tiles, C4 v3 API

Approved by the project owner as OD-2026-11-07. Tasks A25 (Lane A simulation), B47 (Lane B API) and B48 (UI session) are registered with disjoint file ownership. The contract is C4 v3 in `docs/api/ai-service.yaml` § `x-c4-v3-product-api`. A24/I26/B46 are superseded. See `CR-019_PRODUCT_REBASELINE_UI_API.md`.
