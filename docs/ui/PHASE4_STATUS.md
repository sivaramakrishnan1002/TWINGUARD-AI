# Phase 4 — Reservoir and alerts

## Implemented UI

- Added a reservoir status and alerts panel with selector options for Poondi, Cholavaram, Red Hills / Puzhal, and Chembarambakkam. Selection updates the displayed reservoir context only; it does not fetch or imply a record.
- Storage uses an explicitly empty gauge. Storage, capacity, release, observation time, run, and source mode remain unknown or unavailable. Capacity is stated as “Unknown · not zero”; no capacity value, percentage, alert, or timeline marker is fabricated.
- Units are labeled only where documented (`mcft` storage and `cusecs` release). The panel records the documented daily archive coverage (01 Jan 2004–03 Dec 2020) as coverage metadata, not a current observation. It warns that historical analysis capacity denominators are current-published assumptions, not verified historical capacity.
- Alert labels `Normal`, `Watch`, `Warning`, and `Critical` appear as definitions only; each state remains unknown. The alert timeline displays the selected event window as context but has no alert marks or replay progress.
- Source-mode definitions distinguish `REPLAY`, `LIVE`, and `SIMULATED`; none is represented as connected. Replay candidates are described as candidates, not live alerts or validated flood outcomes.
- Added a UI-owned typed Track B adapter seam mapped to the documented reservoir/alert read operations. Its implementation returns an explicit unavailable result. It has no configured endpoint and makes no network request.
- The panel uses accessible headings, a labeled native selector, text alongside status styling, visible focus styles from the existing shell, and responsive cards.

## Source availability and blockers

- Track B documentation describes reservoir and alert routes, but the router is not mounted in the host application; adapter injection and host mount remain deferred. No verified reachable endpoint was found, and no Track B service was started.
- The offline 2015 alert-candidate replay is not a connected UI feed. It cannot supply current storage, a live alert, or a validated flood outcome.
- The historical reservoir archive coverage is documented through 03 Dec 2020. It does not establish a current reading or historical capacity truth.
- No reservoir, capacity, release, alert, alert-history, timestamp, or run data is connected. The only tested state is the explicit unavailable/unknown UI state.

## Checks

- `npm run build` passed using the already-installed dependencies. No package installation, network access, or service start was performed.
- Local production preview manually checked: reservoir selection updated the context (Red Hills / Puzhal); storage and capacity stayed unknown; alert levels remained definitions only; the API unavailable state and empty timeline remained visible; and the map 3D perspective toggle switched to 3D and back to the 2D fallback.
- These checks verify UI behavior only. No API integration or data rendering was tested.
- Existing dependency audit notes remain: three moderate advisories in the Tailwind 3 / PostCSS dependency chain. The production bundle remains about 1.24 MB (about 346 KB gzip), above Vite’s 500 kB advisory threshold. No forced dependency upgrade was performed.
- No automated UI test suite is present in `frontend/`.

## Integration prerequisites

1. Track B owner/integrator must mount the documented router in the host app and provide a reachable, approved endpoint and environment-specific URL configuration.
2. Confirm response schema-to-view-model mapping, source modes (`replay`, `live`, `simulated`), time basis/time zone, units, run/version, provenance, quality flags, and null semantics. Null capacity must remain unknown.
3. For alert history, provide validated time-bounded records and distinguish replay candidates from live alerts and verified outcomes. Define loading, empty, and request-error behavior at the adapter boundary.
4. Capacity should be labeled as current published assumption unless a historically valid capacity source is supplied with provenance.
