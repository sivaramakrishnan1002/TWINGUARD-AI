# B26 — Authoritative G0 status in the static UI

Date: 2026-10-31
Status: implementation and static package build complete

## Behavior

The packaged UI reads `VITE_GATE_G0_STATUS` at build time and shows the value in the top status indicator and footer. Only the exact values `ready` and `not_ready` render as those states. A missing, malformed, or unsupported value renders `G0 STATUS UNKNOWN`; there is no `NOT READY` fallback. The top indicator has a status role and accessible name.

`frontend/scripts/package-with-gate-state.ps1` reads the unique `G0` entry from the authoritative `docs/master/STATE.json`. It passes its exact valid status as a Docker build argument. A missing/invalid gate record maps to `unknown`. The Dockerfile embeds this value in the static Vite bundle. Compose defaults a direct frontend build to `unknown`. The resulting Nginx package has no runtime API, proxy, backend, or database dependency for the badge.

## Verification

- Current authoritative state at packaging: G0=`ready` in `docs/master/STATE.json`.
- Package command: `./frontend/scripts/package-with-gate-state.ps1` — passed. It reported `Packaged static frontend with authoritative G0 status: ready` and built only the frontend image; no container/service was started. Image ID: `sha256:fc4f949ca2f9360ea03213760c28406bbb9dbc4abeebd5df6afb51ded1acca78`.
- Focused and complete UI tests: `node --test tests/ui/gate-status/gate-status.test.mjs tests/ui/scenario3d/raster-view.test.mjs tests/ui/scenario3d/scenario-api.test.mjs tests/ui/scenario3d/scenario-state.test.mjs` — **16 passed**. The gate-status tests render the actual `App` with build-time values `ready`, `not_ready`, and absent/invalid values. DOM assertions check the accessible label and `data-gate-status`, and prove ready cannot display not-ready, not-ready cannot display ready, and unknown cannot display either.
- Package production build ran `tsc --noEmit` and Vite successfully. The existing large-bundle advisory remains (main JS about 1.28 MB; MapLibre worker about 520 kB). The UI SSR tests emit an existing Tailwind warning because the project Tailwind config has no content paths.
- `docker compose -p twinguard-b11 -f docker-compose.b11.yml config --quiet` — passed without printing rendered configuration.
- Raw audit: `DATA_FILES=157; DATA_BYTES=30544672450; HASH_MATCH=157; NO_COMPARABLE_HASH=0; MISMATCH=0`.

## Limits and boundaries

The packaged status is a snapshot of master state when the image is built; rebuilding with the registered script refreshes it. This is intentional for the static/no-proxy package and introduces no runtime service. No application service, database, migration, volume, gate state, contract, or C9 status was changed. G0 remains `ready`; C1–C8 remain frozen at v0; C9 remains proposed and unfrozen. B13 and I04 were not started.

The packaged browser was not launched because this task explicitly prohibited running services. The in-process React DOM assertions exercise the production App rendering with each build-time status, and the Docker build verifies the static package path without starting its container.
