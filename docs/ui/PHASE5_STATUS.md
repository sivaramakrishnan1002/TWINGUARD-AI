# Phase 5 — Impacts, routes, shelters, and decisions

## UI implementation

- Added a decision-support panel for population exposure, affected facilities, and road impacts. All values are `Unknown`; there are no sample counts, zeros, or inferred road measurements.
- Added labeled origin, destination, departure-time, and travel-mode controls. They and the route request action remain disabled until a validated base run and route service are available. The result state has no line or claim of safety and identifies travel time, accessibility probability, provenance, and uncertainty as unavailable.
- Added separate empty candidate and verified shelter states plus an empty shelter-map slot with no markers. Operational status, location, capacity, and accessibility remain unknown.
- Added an empty emergency priority-zone view; no geometry or ranking is displayed.
- Added disabled scenario choices for bridge closure, earlier evacuation, and shelter unavailability. The UI does not evaluate or imply counterfactual outcomes.
- Added a shared decision context strip for source, time, run/version, assumptions, and uncertainty, and an evidence-label key for `REPLAY`, `LIVE`, `SIMULATED`, `DERIVED`, `ASSUMPTION`, and `PLACEHOLDER`. It explicitly states that none is connected to these panels.
- Added UI-owned typed result/request models and a no-network decision-support adapter boundary for impact, routes, shelters, priority zones, and scenario evaluation. All methods return an unavailable result; no endpoint is configured or called.

## B07 result-schema alignment — 2026-10-28

- `frontend/src/ui/types.ts` now represents the exact A07 `ImpactResult` and A09 `RouteResult` snake_case fields, and `frontend/src/ui/adapters/decisionSupport.ts` returns those types without enabling calls.
- Impact types preserve `SIMULATED` source mode, UTC event/valid/generated times, nullable aggregation interval plus its instantaneous-state basis, unit-bearing ensemble distributions with nullable values, facility access categories, thresholds, assessed/eligible/NoData coverage, uncertainty, source hashes, and QC flags.
- Route types preserve explicit route status, nullable topological reachability independently from flood-accessibility/failure probabilities, metres and seconds, nullable UTC arrival and measurements, edge coverage, graph/hazard provenance, assumed thresholds, uncertainty limitations, and QC flags. Missing edge coverage remains unknown; no route is described as safe.
- Models were reconciled against the completed A07/A09 JSONL outputs, B15 owner-output fixtures/DTOs, and current I05 OpenAPI projections. These are schema/fixture inputs only: the React UI does not load the simulation outputs or request the design API documents.
- Real impact, shelter, priority-zone, scenario, and route requests remain unavailable; route controls stay disabled. AI-service operations still return HTTP 501 and the Spring business routes remain unexposed while G0 is not ready. The existing MapLibre 2D view and perspective-only fallback remain unchanged.

## Service and science status

- A07 impact and A09 route result files now exist as simulated research outputs, but no result is connected to this UI. No service was started and no network request was made.
- `docs/api/ai-service.yaml` and `docs/api/backend.yaml` now project the A07/A09 schema fields, but remain design documents. The local AI-service impact/route operations still return HTTP 501; the Spring business routes remain unexposed. No request was sent to either service.
- The project board still lists Lane A impact, time-dependent routing, shelter ranking, priority zones, and counterfactuals as blocked prerequisites. The Batch 1 board says independent-event validation for the Phase 10 risk map is unavailable, so it is not operational evidence for emergency priorities.
- The UI does not invent or load example values; A07/A09 owner-produced files are used for type conformance only, not presented as connected/current operational results.

## Checks

- `npm run build` passed on 2026-10-28 using the existing lockfile-installed dependencies; no install or network access was performed. The existing production bundle warning remains documented in `B14_BUILD_CHECK.md`.
- The B14 report documents UI-state inspection of unknown impact values, disabled route requests, empty shelter/priority results, disabled counterfactual controls, visible source/time/run/assumption/uncertainty labels, and the 2D map default with perspective fallback. This does not validate the newly aligned result types visually or connect runtime data.
- Checks covered the locked production build and compile-time types only; there is no automated UI test suite, and manual browser validation is unavailable. No endpoint, result rendering, route, shelter operation, or decision result was tested.
- Previously documented three moderate Tailwind 3/PostCSS advisories remain. No dependencies were installed or upgraded.
- `frontend/` has no automated UI test suite.

## Remaining prerequisites

### Science and data

1. Complete and validate time-specific flood/depth inputs and their uncertainty, coverage, units, thresholds, and provenance. Preserve NoData as unknown.
2. Complete impact estimates with documented population/facility/road sources, definitions, spatial/time basis, and uncertainty; distinguish estimated exposure from observed impacts.
3. Produce a time-dependent routing graph with verified road/bridge/underpass treatment, passability semantics, calibrated or validated accessibility estimates, and route safety limitations.
4. Provide a shelter inventory with verified locations and operational status; document candidate versus verified designation and capacity provenance. Unknown capacity must remain null/unknown.
5. Produce priority-zone outputs from approved impact/shelter criteria and validated thresholds. Counterfactual outputs require a documented model, base run, scenario parameters, and uncertainty/limitations.

### Services and integration

1. Implement, version, and deploy reachable impact, route, scenario, shelter, and priority-zone APIs; document URL configuration, authentication/CORS, request/response schemas, and error behavior. Current design contracts alone are insufficient.
2. Confirm schema mapping and semantics, including units, time zone, run/version, provenance, source mode, uncertainty, candidate status, null handling, and NoData behavior.
3. Supply a validated base run and time context before enabling route/scenario requests. Add loading, empty, unavailable, and service-error states to the adapter lifecycle when actual service calls are authorized and available.
4. Validate results end to end with upstream owners before enabling operational language or recommendations. No claim that a route is safe or a shelter is operational is supported by this UI phase.
