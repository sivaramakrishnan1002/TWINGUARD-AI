# I08 — Saved A20 3D scenario replay acceptance

Date: 2026-10-31  
Status: accepted with caveats (`done_with_caveats`)

## Scope and prerequisites

I08 was verified after B18 completed at commit `9ea2cb5`. The B18 report at `docs/ui/FLOOD_3D_SCENARIO_VIEW.md` and its registered output paths were checked against that commit. The report records a local packaged UI check, exact selected A20 raster hash/grid/mask, saved-time stepping, 2D fallback, and research limitations. It explicitly does not claim automated axe or cross-device/browser coverage. A20 readiness/manifest evidence, I07 C9 v0/v1 records, B17/B21/B23/B24/B25 route and package evidence, and current B11 packaging constraints were also reviewed. G0 is left ready; C1–C8 remain frozen at v0; C9 remains proposed and unfrozen.

Only the B11 `frontend` and `ai-service` services were started, using existing images (`up -d --no-build --pull never`). The backend service was not started. No database, migration, shared data, or Docker volume was accessed or changed. The frontend and AI service containers started for I08 were stopped with service-scoped `docker compose stop` after verification; no `down` or cleanup command was used.

## Deterministic saved selection and API evidence

Selected A20 record:

- Event `2015-12-02`, scenario `perfect_foresight_imerg`, source mode `PERFECT_FORESIGHT_HINDCAST`.
- Exact saved valid time `2015-11-30T06:00:00Z` (lead 6 h), band `p50`.
- Manifest: `data/features/visualization3d/batch2_v1/manifest.json`.
- Referenced original: `data/features/forecast/batch2_v1/2015-12-02/perfect_foresight_imerg/depth_lead06h_p50_DERIVED.tif`.
- Expected and observed SHA-256: `d563c3780e5c7b611f2a8f13ada4945f1f692160e6b16beeff7b0e455917a1cd`; expected and observed size: 13,763 bytes.

Against the packaged local B11 runtime at `http://127.0.0.1:8000`, with browser origin `http://127.0.0.1:8081`:

- Catalog `GET /scenario-visualization-assets`: **200**; exact detail `GET /scenario-visualization-assets/2015-12-02/perfect_foresight_imerg`: **200**.
- Exact raster `GET /scenario-visualization-assets/2015-12-02/perfect_foresight_imerg/raster?valid_time_utc=2015-11-30T06%3A00%3A00Z&band=p50`: **200**, `image/tiff`, 13,763 bytes. ETag and body SHA-256 matched the manifest reference. Response bytes compared equal to the original file bytes.
- Invalid band selector returned **400**; an absent exact scenario returned **404**. The response included `Access-Control-Allow-Origin: http://127.0.0.1:8081` for the approved origin.
- In-memory Rasterio inspection of the response confirmed single-band Float32, EPSG:32644, 69 × 88 pixels, 600 m pixels, affine transform `(390000, 600, 0, 1471620, 0, -600)`, and NoData `-9999`. The decoded values and mask matched the original file exactly: 2,430 valid cells and 3,642 masked/NoData cells. Valid values were finite, from approximately `0.0000835479` to `0.0207649` metres.

The UI selected the same event/scenario and exact 06:00Z saved slice; it displayed the matching SHA-256, grid, extent, unit evidence, source mode, input hashes, and provenance. It represented NoData as unknown coverage, not dry or zero. The UI's Next saved time control moved to the exact next saved time `2015-11-30T12:00:00Z` (lead 12 h), with no intermediate timestamps. The 2D fallback rendered the original 69 × 88 grid with unknown NoData cells hatched. The 3D view labels one cell per 600 m source cell and uses each saved value as its display height. Research-only and assumption-based limitations were visible, including the absence of observed/validated hydraulic truth, forecast skill, street-level upscaling, safe-route guidance, and emergency advice.

## Checks

- `node --test tests/ui/scenario3d/raster-view.test.mjs tests/ui/scenario3d/scenario-state.test.mjs tests/ui/scenario3d/scenario-api.test.mjs` — **9 passed**.
- `npm run build` in `frontend/` — passed (`tsc --noEmit` and Vite build). Vite emitted the existing large-chunk advisory (main JS about 1.28 MB; worker about 520 kB).
- `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib tests\ai_service` — **88 passed**, one existing Starlette/httpx deprecation warning.
- `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib tests\master\test_scenario_visualization_contract.py` — **4 passed**.
- `python tools\validate_api_contracts.py` — AI OpenAPI 3.1.0, 11 paths/11 operations; backend OpenAPI 3.1.0, 10 paths/11 operations; passed.
- `.venv\Scripts\python.exe tools\audit_raw_logs.py` — `DATA_FILES=157; DATA_BYTES=30544672450; HASH_MATCH=157; NO_COMPARABLE_HASH=0; MISMATCH=0`.
- Packaged runtime was started from already-built local images; runtime evidence and status codes are recorded above. Only the two I08-started services were stopped afterward.

## Caveats and limits

- B18's desktop accessibility review was manual. Automated axe and cross-device/browser matrix checks were unavailable and remain unclaimed; I08 does not expand that coverage.
- During browser verification, the pre-existing global shell banner displayed `G0 NOT READY` even though the current master state and gate report record G0 as ready. The scenario view itself continued to label the selected data as saved research/simulation evidence and explicitly denied live/operational interpretation. This stale global badge is recorded for Lane B UI follow-up; it did not change G0 or the saved scenario result.
- A20 remains a coarse, assumption-based regional research product. The view is not validated hydraulics, physical water-flow simulation, a live prediction, operational warning, route guidance, or safety advice. The I08 evidence does not establish scientific validation or live operation.
- No Docker image was rebuilt for I08, no backend route was exercised, and no database or volume was touched.
