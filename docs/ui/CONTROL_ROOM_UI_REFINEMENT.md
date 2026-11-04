# B31 — Control-room UI refinement

## What changed

The seven-section local demo now keeps the selected scenario, synthetic step, source mode, and evidence status visible across every section. The shared context bar also links directly to the What-if Lab so the same scenario context is easy to follow while moving between views.

Emergency Response now explains the planned three-state road evidence model—assessed passable, assessed blocked, and unknown/verify. It is explicitly marked as upcoming A21 analysis and says the current route rows do not use those classifications. The What-if Lab now has a decision-stability panel that describes the planned comparison without presenting counts, probabilities, or recommendations before A21 produces evidence.

The visual layer refines the navigation rail, scenario controls, page hierarchy, map stage, typography, spacing, surfaces, route table, and responsive layouts. It preserves the existing seven sections, local fixtures, reduced-motion behavior, keyboard controls, 2D fallback, and all DEMO/SIMULATED labels. No service calls, APIs, packages, real measurements, or geographic outputs were added.

## Verification

- `npm run build` — passed (`tsc --noEmit && vite build`).
- `git diff --check -- frontend/src/ui/product/ProductExperience.tsx frontend/src/ui/product/product.css docs/ui/CONTROL_ROOM_UI_REFINEMENT.md` — passed with the repository's LF/CRLF normalization warnings.
- Automated UI tests and the package guard were not run in this turn.
- Browser rendering and screenshot capture were unavailable because local browser use is disabled in Work settings. No visual pass is claimed.

## Limits and preserved work

The interface remains a local DEMO/SIMULATED experience. Water visuals and values are illustrative, A21 findings are pending, and no route safety or operational readiness is implied. Existing B29/B30 visual evidence remains historical and was not replaced. Lane A's running A21 task, its files, and its status were not changed.
