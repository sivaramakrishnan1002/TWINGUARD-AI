# B36 — UI source and freshness boundary

## Behavior

The default product continues to use its centralized local demo adapter and fixtures. Its source mode is `SIMULATED`, visibly labeled `DEMO · SIMULATED`. The displayed availability is `current` only in the UI sense that the local fixture is loaded; the panel says explicitly that source age and refresh are not measured. Source timestamp, timezone, receipt/refresh time, and hash remain unknown/not supplied when the fixture provides none.

Source mode and availability/freshness are separate types:

- Source mode: `LIVE`, `REPLAY`, `SIMULATED`.
- Availability/freshness: `current`, `STALE`, `UNAVAILABLE`.
- Observation value/coverage: value, unknown, unavailable, known zero, explicit dry, or NoData.

An unconnected live-source slot is `UNAVAILABLE` with a reason and unknown source/receipt/provenance metadata. The UI does not render a LIVE source-mode badge for it. A verified `LIVE` current/stale record is rejected unless owner authorization, runtime evidence, source and receipt instants, measured age, and matching provenance hash are supplied. No provider is wired to supply such a record. The adapter remains replaceable and performs no network or service calls.

The generic card can render a timestamped `REPLAY` stale example only with an example label. Date-only records keep their calendar date, unknown observation time/timezone, and separate receipt time; they cannot become stale by comparing `receivedAt` to a fabricated instant. Existing zero, dry, unknown, unavailable, and NoData presentation remains distinct.

The B36 additions do not change the separate B18/A20 scenario viewer. Its saved times, provenance, hashes, raster masks, and NoData behavior remain untouched; the default product continues not to load those assets.

## Verification

- `node --test tests/ui/live-readiness/source-freshness.test.mjs` — **5 passed**.
- `node --test --test-name-pattern="product shell retains|Demo and scenario state" tests/ui/product/product-experience.test.mjs` — **2 passed**, including responsive breakpoints, keyboard focus, reduced motion, and design-token contrast checks.
- `.venv\Scripts\python.exe -m pytest tests\packaging\test_frontend_demo_only.py -q --import-mode=importlib` — **3 passed, 64 subchecks passed**; the new source/freshness path is included in the no-network/demo-only scan and built bundle checks.
- `cd frontend; npm run build` — **passed** (`tsc --noEmit` and Vite production build).
- `git diff --check` for registered B36 paths — **passed**.
- `.venv\Scripts\python.exe tools\audit_raw_logs.py` — **157 files, 30,544,672,450 bytes; 157 hash matches; 0 without comparable hashes; 0 mismatches**.

The unfiltered legacy `tests/ui/product/product-experience.test.mjs` has an existing Overview expectation mismatch: it expects a “Scenario view” label and an “Select overview demo time step” control that are absent from the current B33 Overview markup. B36 did not change that section or its test. The focused system/state and accessibility checks pass. No manual browser visual review was performed.

No data feeds, backend services, databases, credentials, or A21 outputs were accessed. No contract, A20 asset, or B18 viewer file was changed. No operational recommendation or live-source claim is made.
