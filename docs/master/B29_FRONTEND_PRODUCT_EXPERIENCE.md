# B29 — Frontend product experience (DEMO/SIMULATED only)

**Owner:** Lane B UI owner. **Status at registration:** ready/unclaimed. **Mode:** frontend-only demo; no implementation performed in the Integrator session.

## Scope and boundaries

Complete the frontend product experience with these sections: Situation Overview; 3D Flood Twin with time-stepped illustrative demo water animation and working 2D fallback; Reservoirs & Alerts; Impacts; Emergency Response with route and shelter panels; What-if Lab with interactive demo controls; Data & System with provenance, source mode, and service-readiness states.

Use centralized, clearly labeled `DEMO`/`SIMULATED` fixture data and a typed adapter boundary designed for later replacement. Make no network or service calls, including to existing B18/B23 raster or C9 endpoints. Keep B18's completed components, evidence, task history, and G5/G6 status intact. Within B29's registered frontend mount and new product experience only, B29 may supersede which demo/runtime view is mounted. Do not edit backend services, Lane A outputs, Track B implementation, OpenAPI projections, or contracts.

The 3D animation is illustrative UI motion over demo geometry, not a backend result, saved raster, hydraulic simulation, physically validated flow, forecast, warning, or safety guidance. Keep current B18 saved-raster implementation available in its existing code and evidence; B29 must not call it.

## Owned outputs

- `frontend/src/ui/App.tsx` — mount/navigation for the B29 product experience only.
- `frontend/src/ui/product/` — page shell, navigation, shared UI components, responsive layouts, and scoped styles.
- `frontend/src/ui/demo/` — centralized typed fixtures, source-mode labels, demo state transitions, and typed replaceable adapter interface/implementation.
- `tests/ui/product/` — page, navigation, interaction, state-label, and accessibility-focused tests.
- `tests/packaging/test_frontend_demo_only.py` — static/package guard that verifies no service/network client is imported or invoked by the B29 UI path.
- `docs/ui/FRONTEND_PRODUCT_EXPERIENCE.md` — feature inventory, demo-data provenance, interactions, limitations, build/test evidence, and future adapter replacement boundary.

Preserve other existing frontend paths, including `frontend/src/ui/scenario3d/`, `frontend/src/ui/replay/`, B18's tests/docs, package manifests, and the application bootstrap unless a later separately registered task authorizes edits. If implementation discovers a required overlapping path, stop and request an ownership reconciliation before editing it.

## Dependencies and acceptance

Dependencies: B14 professional redesign evidence, B18 saved-scenario visualization evidence, and B27 replay/UI evidence are complete. These are design/behavior references only; B29 must not reuse their service calls or alter their completion records. G0 remains ready, G5/G6 remain as currently recorded; their state does not authorize live integration.

Acceptance criteria:

1. All seven named sections are reachable through working navigation with clear active state and useful responsive layouts across desktop, tablet, and narrow mobile widths.
2. The 3D Flood Twin presents a time-stepped **illustrative DEMO animation** using only centralized demo fixture values; controls visibly advance/pause/reset the illustrative animation. A working 2D fallback presents the same selected demo time/state. Neither view calls raster, catalog, detail, backend, AI, or other network/service endpoints.
3. Reservoirs & Alerts, Impacts, Emergency Response route/shelter panels, and What-if Lab have meaningful deterministic demo interactions using fixtures only. Any calculated/changed values are labeled `DEMO` or `SIMULATED`; interactions do not imply authoritative prediction or safe routing.
4. A typed data adapter boundary separates views from centralized fixtures and exposes no HTTP client. Automated tests or static guards fail if the B29 UI path imports or invokes `fetch`, Axios, WebSocket, EventSource, a service SDK, or B18/C9 endpoint adapters.
5. Unknown, unavailable, numeric zero, dry, and NoData are visually and semantically distinct in reusable components and tested. Null/unknown/NoData is never converted to zero or dry. Missing service readiness is shown as unavailable/unknown, not healthy or live.
6. Provenance, source mode, units where known, timestamps/date-only semantics, uncertainty/limitations, and service-readiness state are visible with clear demo labels. No historical time, live operation, emergency readiness, physical water flow, validated flood behavior, or safety claim is introduced.
7. Meet WCAG 2.2 AA intent for keyboard navigation, focus visibility, contrast, semantic landmarks/headings, accessible names, reduced-motion preference, and status announcements. Record automated checks and manual keyboard/screen-reader limitations honestly.
8. Run locked frontend install-free build/tests using existing local dependencies, responsive/accessibility tests, demo-only network guard, and packaged UI smoke checks without starting AI/backend services. Do not fetch/install packages unless a separate approval authorizes it.
9. Finish through Lane B protocol with report, exact commands/results, screenshots or test evidence as appropriate, and a list of any unavailable validation. Leave G0, G5, G6, C1–C8, C9, services, databases, and B18 evidence unchanged.

