# B18 — Saved-raster 3D scenario view

Date: 2026-10-31
Status: implementation and local packaged UI verification complete; research-only caveats retained

## What the interface renders

The Spatial explorer now mounts `ScenarioRasterExplorer` inside the existing UI page through `frontend/src/ui/App.tsx`. The global shell and `frontend/src/main.tsx` were not changed. It calls only the approved B21/B23 AI-service catalog, exact detail, and exact raster GET routes at `http://127.0.0.1:8000`; requests use `credentials: omit`, `Accept`, and no write methods. The B24-approved browser origin remains `http://127.0.0.1:8081`.

The selector uses the exact `(event_id, scenario_id)` catalog identity and rejects missing or duplicate matches. Detail and raster selectors preserve exact saved `valid_time_utc` values and one of the manifest-listed p05/p50/p95 bands. Time stepping moves only among saved timestamps. There is no interpolation or synthetic time step.

The browser verifies raster response type, bounded byte length, SHA-256, selected manifest reference, grid, and NoData counts before display. The strict decoder supports only the bounded A20 single-band Float32 GeoTIFF layout. Its values remain in a `Float32Array`; the valid mask is kept separate. The 3D perspective draws one 600 m source cell for each valid source value, with extrusion height equal to that value in metres. The display-only color ramp rescales to the selected slice and does not rewrite or resample the TIFF. EPSG:32644 cell corners are transformed to WGS84 only for MapLibre display. The 2D fallback draws the original row/column grid, hatches invalid NoData cells and provides per-cell saved-value tooltips.

The view shows event/scenario, exact saved UTC time and lead, source mode, derived status, 600 m grid and projected extent, depth units and unit-metadata gap, valid/NoData cell counts, p05/p50/p95 semantics and member count, rainfall semantics, forecast/simulation summary paths, seeds and hashes, source-hash status, raster SHA-256, and source limitations. Unsupported basemap, terrain, building, road, live, warning, routing, and operational layers remain explicitly unavailable.

## Evidence and limitations

- A20 manifest: `data/features/visualization3d/batch2_v1/manifest.json`.
- Tested selected source: event `2015-12-02`, scenario `perfect_foresight_imerg`, saved valid time `2015-11-30T06:00:00Z`, band `p50`.
- Selected original band: 69 × 88 Float32, EPSG:32644, 600 m pixels, extent X 390000–431400 m / Y 1418820–1471620 m, NoData `-9999`; 2,430 valid cells and 3,642 unknown-coverage cells.
- The selected original TIFF SHA-256 is `d563c3780e5c7b611f2a8f13ada4945f1f692160e6b16beeff7b0e455917a1cd` (13,763 bytes). Browser verification matched the manifest before decoding.
- The saved source mode is `PERFECT_FORESIGHT_HINDCAST`. This is assumption-based historical research, not an archived forecast or observed flood. The member spread is parameter spread, not calibrated statistical confidence. The rainfall input uses observed daily IMERG totals distributed with ERA5 hourly shape. NoData denotes outside the assessed CMA or otherwise unmodelled; it is unknown, not dry. TIFF band-unit metadata is unset; the displayed metre basis comes from the A20 reports.
- The 3D view visualizes saved cell depths only. It contains no terrain, buildings, water flow, intermediate times, validated hydraulic behavior, live warning, safe-route result, or decision guidance. C9 remains proposed/unfrozen. C1–C8, G0 and scientific A20 files were not changed.
- Browser verification was local to the B11 app tier (frontend and AI service) with loopback ports. No backend, database, migration, shared service, volume cleanup, or live feed was used. Both containers started for B18 were stopped after verification; volumes were untouched.

## Checks

- `python tools/master/verify_state.py` and `python tools/master/next_task.py --lane B` at startup: state verifier passed; B18 was selector-ready, with no owned-output conflict. B18 was claimed through `tools/master/claim.py` under its existing registered task.
- `node --test tests/ui/scenario3d/raster-view.test.mjs tests/ui/scenario3d/scenario-state.test.mjs tests/ui/scenario3d/scenario-api.test.mjs` — **9 passed**. Checks cover exact A20 Float32 values/grid/CRS/mask, NoData omission from map features/range, grid mismatch fail-closed behavior, spatial transform, bounded exact GET routes and credential omission, provenance/hash preservation, exact selector matching including duplicate rejection, loading/error/2D state, exact saved-time stepping, and replay/research mode labeling.
- `npm run build` — passed (`tsc --noEmit` and Vite production build). Docker's locked frontend build also passed from the existing `package-lock.json`; its `npm ci` layer was cached, and no dependency was added or downloaded. Vite reports the existing large-bundle advisory (main JS ~1.28 MB; MapLibre worker ~520 kB).
- Packaged frontend: `docker compose -p twinguard-b11 -f docker-compose.b11.yml build --pull=false frontend` — passed; final image ID `sha256:8899afffdcf7a3fd5625a35f107ffddf7ed30dbf7fa550cea26739fe5314e2e6`. AI image reused from B25, ID `sha256:0987a6d5368f70b2c0e4e4f891eeaf67cd3360117bcc5020c437581182559e11`.
- `docker compose -p twinguard-b11 -f docker-compose.b11.yml config --quiet` — passed with no rendered configuration output.
- Local packaged browser check at `http://127.0.0.1:8081`: catalog and exact detail loaded; exact raster GET passed B24 CORS, size, hash, grid and mask verification; the 3D saved-cell view and 2D hatched fallback rendered. Selecting “Next saved time” advanced only from `2015-11-30T06:00:00Z` to saved slice `2015-11-30T12:00:00Z`. Keyboard Space switched from the 2D fallback to 3D. Browser accessibility tree exposed labeled scenario/time/band selectors, saved-time buttons, view controls, metadata and map navigation controls. Manual visual and accessibility-tree review passed for desktop viewport; browser console had no errors or warnings. Automated axe and cross-device/browser matrix checks were unavailable and are not claimed.
- `.venv\Scripts\python.exe tools\audit_raw_logs.py` — `DATA_FILES=157; DATA_BYTES=30544672450; HASH_MATCH=157; NO_COMPARABLE_HASH=0; MISMATCH=0`.

## Closeout

The deliverable renders exact saved raster evidence in 3D perspective and in a usable 2D fallback. B18 does not validate scientific results or enable operational use. I08 was not started and remains downstream of B18.
