# B29 — Frontend product experience

**Status:** implemented with validation caveat; DEMO/SIMULATED only. No services or network sources are connected.

## Product surface

The mounted product experience provides seven navigable sections: Situation Overview, 3D Flood Twin, Reservoirs & Alerts, Impacts, Emergency Response, What-if Lab, and Data & System. Navigation exposes the current section, works from keyboard, and adapts to narrow screens. Shared source badges, status states, metric cards, and section layouts use scoped design tokens and responsive styles.

The Flood Twin offers an isometric illustrative view and a 2D schematic fallback over the same selected fixture frame. Step, play/pause, reset, and layer controls update local UI state only. Reduced-motion preference prevents automatic motion. Shapes are demo geometry and do not depict measured or physically validated water flow.

Reservoir selection, alert examples, impact summaries, route comparison, candidate shelter availability, and what-if controls use deterministic local fixture data. Scenario inputs change only fixture-based arithmetic and illustration state. The Data & System section shows fixture provenance, source mode, time basis, units, uncertainty/limitations, and service readiness.

## Demo provenance and boundaries

All non-empty operational-looking values are explicitly marked `DEMO` or `SIMULATED` and are fictional interface fixtures. Dates and times are demo time bases, not historical observations or current operations. There are no HTTP clients, endpoints, backend health probes, or B18/C9 raster calls in the mounted B29 path. The typed `ProductExperienceAdapter` is the replacement boundary; its current implementation reads centralized local fixtures only.

Unknown, unavailable, numeric zero, dry, and NoData are modeled and rendered as distinct states. Unknown/null values are not coerced to zero. Missing coverage is not described as dry. Route topology is synthetic and does not establish hazard access or safety. Shelter candidates are not verified operational shelters. Impact values and alerts are not evidence or warnings. G0 status is displayed from the existing build-time configuration and is not changed by B29.

## Validation evidence

- `npm run build` (from `frontend/`): passed; production bundle generated from installed dependencies.
- `node --test tests/ui/product/product-experience.test.mjs tests/ui/gate-status/gate-status.test.mjs tests/ui/scenario3d/raster-view.test.mjs tests/ui/scenario3d/scenario-api.test.mjs tests/ui/scenario3d/scenario-state.test.mjs` (repository root): passed after semantic-table assertions were aligned.
- `python tests/packaging/test_frontend_demo_only.py -v` (repository root): passed; checks B29 source and generated bundle for network/service integration.
- `.venv/Scripts/python.exe tools/audit_raw_logs.py` (repository root): passed; 157 data files (30,544,672,450 bytes) had matching hashes, with no mismatches or incomparable hashes. Raw data was not modified.
- `git diff --check`: passed; Git reported only existing LF/CRLF normalization warnings on modified working-tree files.

Automated checks cover section navigation, local interactions, adapter behavior, state distinctions, evidence labels, responsive/focus/reduced-motion CSS, core token contrast pairs, and packaged demo-only behavior. Manual visual browser rendering and manual keyboard/screen-reader review were unavailable in this run: the desktop computer-use helper could not establish the current browser URL with sufficient confidence, so no browser interaction was performed. No data rendering or end-to-end integration is claimed.

## Remaining validation/integration

The experience is a frontend demo, not a connected digital twin. Replace the local adapter only when approved, documented, reachable service contracts and validated data with provenance are ready. Before operational use, validate screen rendering at target viewports, keyboard and assistive-technology behavior, source semantics, and each real result end to end. Preserve the distinction between unknown, unavailable, zero, dry, and NoData in any future adapter.
