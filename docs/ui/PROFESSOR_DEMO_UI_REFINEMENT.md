# B37 — Professor-facing demo UI refinement

## Delivered

The existing seven-section demo remains the product surface. A five-step guided walkthrough now directs a presenter to select a local scenario, inspect its local demo steps, view impacts, compare response options, and explore a what-if. Walkthrough controls navigate to the existing sections; the scenario step returns to the overview and focuses the existing scenario selector. The existing section navigation and demo controls remain available.

The overview keeps the city concept artwork as its prominent workspace and preserves its explicit fictional/non-georeferenced and illustrative-water labels. The A21 decision-stability panel continues to show pending results. Its copy now states that A21 is in progress and its outputs remain unavailable until completion and review. No A21 output is consumed or inferred.

Reservoir history bars now show their existing synthetic sample values and explicitly say the sequence has no source dates. Zero-valued samples have zero-height bars and retain a visible `0` label; empty fixture histories remain unavailable. No source dates, observations, or values were added. Narrow layouts wrap the source/header controls and keep section navigation within the mobile viewport; the guided flow scrolls horizontally on narrow screens.

Unknown, unavailable, known zero, explicit dry, and NoData remain separate states. NoData remains unknown coverage. Response and shelter examples remain synthetic; reachability is not presented as flood passability or safety. B18/A20 scenario assets, routes, raster handling, provenance, exact saved times, hashes, CRS, masks, and NoData logic were not edited.

## Visual evidence

Captured with the installed headless Chrome against the local production preview at `127.0.0.1:4178`. Only the static frontend was served; no API or backend service was used. The preview was stopped after capture.

- Desktop overview, 1600 × 1200: [overview-desktop-1600x1200.png](../../tests/ui/product/evidence/professor-demo/overview-desktop-1600x1200.png)
- Mobile overview, 500 × 1200: [overview-mobile-500x1200.png](../../tests/ui/product/evidence/professor-demo/overview-mobile-500x1200.png)

Both screenshots were visually inspected. They are static captures, not a manual interaction, keyboard-only, screen-reader, or assistive-technology review. The responsive and keyboard-related checks below are automated.

## Checks

- `node --test tests/ui/product/professor-demo-refinement.test.mjs` — **4 passed**. Covers walkthrough order and action routing, active state per section, DEMO/illustrative labels, A21 pending state, distinct coverage states, readable history values without invented dates, mobile overflow rules, and focus/reduced-motion rules.
- `node --test --test-name-pattern="product shell retains|Demo and scenario state" tests/ui/product/product-experience.test.mjs` — **2 passed**, including responsive, keyboard focus, reduced-motion, and contrast-token checks.
- `node --test tests/ui/scenario3d/raster-view.test.mjs tests/ui/scenario3d/scenario-state.test.mjs tests/ui/scenario3d/scenario-api.test.mjs` — **9 passed**. Existing B18 raster values, masks/NoData, provenance, exact timestamps, routes, and 2D fallback checks pass.
- `npm run build` from `frontend/` — **passed** (`tsc --noEmit` and Vite production build).
- `.venv\Scripts\python.exe -m pytest tests\packaging\test_frontend_demo_only.py -q --import-mode=importlib` — **3 passed, 71 subtests passed**.
- Scoped `git diff --check` — **passed**.
- `.venv\Scripts\python.exe tools\audit_raw_logs.py` — **157 files, 30,544,672,450 bytes; 157 hash matches; 0 without comparable hashes; 0 mismatches**.

The full legacy `tests/ui/product/product-experience.test.mjs` run still has two pre-existing Overview assertions that expect an older `Scenario view` card and its `Select overview demo time step` label. The current B33 Overview uses the concept-art workspace and labels its control `Select illustrative demo time step`; those assertions were already stale before B37 and were not edited. The other product-section assertions and B37 focused tests pass. The Vite SSR test harness also printed its existing empty Tailwind content warning and, during parallel runs, a busy HMR WebSocket port warning.

## Scope and limitations

All mounted product data still comes from centralized local fixtures. No live feed, network/API client, backend behavior, factual values, contract, database, migration, Docker configuration, or credential was added or changed. No operational flood warning, validated prediction, safe route, verified shelter, or A21 result is claimed. B18/A20 implementation and source assets remain unchanged. A21 remains active on Lane A paths and its results remain unavailable to this UI pending completion and review.
