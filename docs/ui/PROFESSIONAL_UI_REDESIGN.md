# B14 — Professional live-ready UI redesign (design-only)

## Status

- B14 was claimed through the project protocol on 2026-10-27.
- The redesign is a frontend presentation change only. No API, database, map tile, or live data integration was added.
- G0 remains `not_ready`. All live, replay, simulated, and operational results remain unavailable until their sources and integration are approved and verified.
- Work is limited to UI-owned files. No dependencies were installed or changed.

## Screens and interaction

- **Situation overview:** workspace context, no-source system notice, source health, map preview, and link to the static evidence view.
- **Map and layers:** existing MapLibre empty style, 2D default and perspective-only 3D toggle, unavailable layer catalogue, NoData legend, and map-source provenance.
- **Reservoirs and alerts:** existing Phase 4 panel and its explicit Track B unavailable state.
- **Impacts and decisions:** existing Phase 5 panel with unknown impact values and disabled route/scenario actions.
- **Research evidence:** a locally bundled static sensitivity/explainability figure with source documents, study scope, and caveats. It is not connected to the selected event, a map layer, or a live result.

The event selector uses the documented Phase 3 planned input windows and historical replay-candidate window. It does not claim a flood onset date or actual replay playback. The shared header and source badges keep source mode and G0 status visible across sections.

## Design and accessibility

- Added a light, restrained visual system with reusable spacing, surface, border, typography, status, and layout rules in `frontend/src/ui/styles.css`.
- Added a reusable text-and-marker status badge in `frontend/src/ui/components/StatusBadge.tsx`. Status meaning is communicated by words and symbols, not color alone.
- Kept semantic navigation, labeled controls, visible focus styling, skip-to-content navigation, responsive layouts, and reduced-motion handling.
- Retained the empty-map source behavior and local MapLibre worker. No remote tile or font request is configured.

## Evidence and source boundary

- No live service, time-indexed flood layer, reservoir feed, route result, shelter inventory, or priority-zone result is connected.
- The static figure is copied into the UI-owned asset tree from `docs/figures/phase12_parameter_sensitivity_batch2.png` so the interface does not depend on loading a source file outside `frontend/` at runtime.
- `docs/PHASE12_SIMULATION.md` describes coarse assumption-based simulation; `docs/EXPLAINABILITY_BATCH2.md` documents a single-fold explanation. The UI labels these as static, derived/assumption-based research and states that parameter spread is not calibrated uncertainty, the model has no independent-event validation, and neither is emergency guidance.
- Unknown and NoData remain unknown; no sample measurements, capacities, routes, risk scores, or alert outcomes were introduced.

## Verification

- Existing local dependencies were available in `frontend/node_modules`; no install or network access was performed for B14.
- `npm run build` passed with TypeScript and Vite.
- Vite reports the production JavaScript chunk exceeds its 500 kB advisory threshold (about 1.25 MB uncompressed, about 350 kB gzip). The three moderate Tailwind 3/PostCSS advisories already documented by the project remain; no forced upgrade or Tailwind v4 migration was performed.
- The local production preview was started. A manual browser visual check could not be completed because the available local browser automation surface reports that browser use is disabled in Work settings. Build validation therefore confirms compilation, not visual rendering or data integration.
- No automated UI test suite is configured in `frontend/package.json`.

## G0 and integration prerequisites

G0 must be formally ready before any operational source is enabled. Relevant backend and AI services must be implemented, mounted, reachable, and authorized; upstream result schemas and semantics must be verified; and source mode, timestamps, time basis, units, run/version, provenance, uncertainty, coverage, null handling, and NoData behavior must be validated end to end. Flood tiles and compatible terrain/basemap sources also need verified availability and attribution. Until then, the empty map, unavailable feeds, and unknown values are intentional.
