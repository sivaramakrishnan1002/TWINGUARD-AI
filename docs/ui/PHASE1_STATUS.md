# UI phase board

| Phase | Scope | Status | Notes |
|---|---|---|---|
| 1 | App foundation and shell | Implemented; production build passes | React/TypeScript/Tailwind/Vite scaffold and data-free command-center shell. Approved dependencies installed from lockfile. |
| 2 | Map, terrain, and 3D | UI implemented; source integration blocked | MapLibre canvas and perspective control are in place. No HTTP tile service or verified terrain tiles are available. See `PHASE2_STATUS.md`. |
| 3 | Flood event explorer | Metadata controls implemented; source integration blocked | Documented windows can be selected; no time-indexed playback or map layers are connected. See `PHASE3_STATUS.md`. |
| 4 | Reservoir and alerts | UI implemented; source integration blocked | Four-reservoir selection, unknown storage/capacity states, alert definitions and unavailable timeline; Track B adapter remains unconfigured because its router is not mounted. See `PHASE4_STATUS.md`. |
| 5 | Impacts, decisions, and integration | UI states implemented; service/science integration blocked | Impact, route, shelter, priority-zone, and counterfactual panels remain unavailable; no approved endpoint or verified result files were available. See `PHASE5_STATUS.md`. |

## Phase 1 delivery

- `frontend/src/ui/App.tsx`: responsive map-first shell with event/run/time/source status, layer controls, a 2D map placeholder, provenance/limitations, and unavailable replay controls.
- `frontend/src/ui/styles.css`: reusable design tokens and status badge styles, responsive layout, keyboard-visible focus, explicit missing-data patterns.
- `frontend/src/ui/types.ts`: view models for map layers, events, runs, alerts, routes, shelters, evidence, provenance, and source modes (`LIVE`, `REPLAY`, `SIMULATED`, `NONE`). Evidence statuses include `DERIVED`, `ASSUMPTION`, and `PLACEHOLDER`.
- `frontend/`: React/TypeScript/Tailwind/Vite scaffold. M3 was approved; dependencies are installed from the lockfile.

## Evidence and limitations

- The initial screen renders no map, historical replay, flood depth, risk result, alert, route, or shelter values. No fixtures or mocked production values are included.
- A patterned NoData key is shown to communicate that missing coverage is not equivalent to dry conditions.
- The API documents in `docs/api/` describe planned interfaces and are not live services. They were read for field naming only and were not edited.
- The older CMA boundary remains provisional. No boundary geometry is displayed by this phase.
- Node.js 24.16.0 and npm 11.13.0 are present. No UI test files are present. The production build passes; see `PHASE2_STATUS.md` and `PHASE3_STATUS.md` for current verification and advisories.

## Phase 2 prerequisites

- Use the existing frontend lockfile with `npm ci` when refreshing installed dependencies.
- Verify basemap, terrain, and any building tile sources, including source attribution, licence, CRS, coverage, resolution, and provenance; do not render unverified tiles.
- Confirm the documented project grid/CRS and layer metadata for any connected source. Preserve NoData separately from dry values.
- Confirm browser support and a 2D fallback before enabling optional 3D terrain; show assumed building heights as assumptions and load extrusions selectively by zoom.
- Keep the map view marked as unavailable until a verified source and adapter are connected.
