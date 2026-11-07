# Phase 2 — Map, terrain, and 3D

## Delivered in the UI

- Added MapLibre GL JS with a Vite-bundled worker and MapLibre controls. The map view starts in 2D, supports zoom/pan, and has a 3D perspective toggle that resets to a usable 2D camera view.
- The map uses a neutral empty style. No third-party basemap, project geometry, flood measurements, terrain, buildings, or other vector/raster data are rendered.
- The left panel lists study boundary, cleaned terrain, buildings, roads/waterways, flood depth, risk, and uncertainty/NoData as unavailable. Controls stay disabled until a source adapter is available.
- The legend states that NoData is transparent and missing coverage is not dry. The older CMA extent is labeled provisional and is not drawn.
- 3D mode changes camera perspective only and states that terrain tiles are unavailable. No terrain surface or building extrusion is shown.

## Source inspection and blockers

- `database/migrations/002_gis_views_and_mvt.sql` defines `mvt_study_area`, `mvt_roads`, `mvt_facilities`, `mvt_waterways`, and `mvt_flood_references`. Project docs record successful historical smoke checks, but these are PostgreSQL functions returning MVT bytes, not HTTP tile endpoints. No UI-accessible map tile service or endpoint is documented, so none is connected.
- The documented functions do not include a buildings MVT endpoint. Building footprints are not loaded by the UI.
- `data/processed/terrain_cleaned/cleaned_elevation_m.tif` and conditioning metadata exist. Project documentation identifies the source as a cleaned GLO-30 digital surface model with known artifacts and no vertical datum conversion during conditioning. The tile recipe, MapLibre raster-DEM encoding/compatibility, and terrain tiles are not verified. No tile generation or storage was attempted.
- Flood depth outputs are derived, incomplete, and not exposed through a UI service. No flood or risk source is connected.
- `data/raw/` and Lane A/shared data paths were not modified. No files outside `frontend/` and `docs/ui/` were edited.

## Required owner actions before data integration

1. The integrator/API owner must provide or approve an HTTP tile endpoint that exposes the documented project MVT functions, including URL pattern, CRS/zoom coverage, attribution, layer names, and authentication/CORS behavior. Database functions alone cannot be consumed by MapLibre in the browser.
2. The data owner must approve a generated-data location and tile recipe before anyone converts the cleaned DSM to terrain tiles. The tile format, encoding, vertical reference, NoData behavior, bounds, and provenance must be documented and verified. This UI did not create tiles because the approved output owner/path and recipe are absent.
3. Building tiles require an approved, zoom-aware endpoint and a verified height field. Any fallback height would need an explicit `ASSUMPTION` property and legend. The UI must not fetch the full 382,000-building set.
4. A flood-depth/risk layer requires a documented API/data adapter, fixed legend, event/run timestamps, provenance, uncertainty, and NoData coverage. Until then the layer controls remain unavailable.

## Checks

- `npm install` completed from `frontend/` after explicit M3 approval and generated `package-lock.json`.
- Phase 1 production build passed before Phase 2 edits.
- Production build passed after Phase 2 changes and the MapLibre worker bundling fix.
- The built preview was opened in the in-app browser. The accessibility tree confirmed the 2D default, MapLibre zoom controls, enabled 3D perspective toggle, transparent-NoData legend, and explicit unavailable-source state. The 3D and 2D controls were both exercised.
- The build reports a 1.23 MB main JavaScript chunk (343 KB gzip) above Vite's 500 kB advisory threshold; no performance claim is made.
- `npm audit` reports three moderate advisories in the Tailwind 3 / `postcss-nested` / `postcss-selector-parser` dependency chain. The available forced remediation upgrades to Tailwind 4, a breaking framework change; no forced upgrade was applied in this phase.
- No automated UI test suite exists in `frontend/`.
