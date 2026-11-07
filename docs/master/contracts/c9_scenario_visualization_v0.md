# C9 — Scenario visualization assets v0

**Status:** proposed post-G0 contract; project-owner approved for implementation under CR-009 on 2026-10-30. C9 remains unfrozen and outside the shared contract registry. C1–C8 remain frozen at their existing v0 versions and are not changed. CR-010 separately approves an additive proposed C9 v1 AI-service raster-byte operation; that operation is documented in `c9_scenario_visualization_v1.md` and is not part of this v0 projection.

## Source and identity

The source of truth is the read-only A20 manifest `data/features/visualization3d/batch2_v1/manifest.json`, with `schema_version=1.0.0`, `artifact_version=batch2_v1`, and status `DERIVED_ASSUMPTION_BASED_RESEARCH_SCENARIO`. A scenario series is uniquely identified by `(artifact_version, event_id, scenario_id)`; the current A05 series use `scenario_id=perfect_foresight_imerg` for three distinct event IDs. A06 context layers use `(artifact_version, event_id, temporal_kind, selected_hour_index_zero_based)`; peak layers have no selected index.

`source_mode` is copied from the manifest. Current A05 series use `PERFECT_FORESIGHT_HINDCAST`; this is hindsight forcing built from daily IMERG totals distributed with an ERA5 hourly shape, not an archived forecast or live source. A06 context records are simulation context. Do not infer additional modes.

## Time semantics

- A05 series expose only the exact `valid_time_utc` values in saved `slices`: 6, 12, 24, 48, and 72 hours after `window_start_utc`, as recorded in the manifest. These saved times are unevenly spaced. Preserve the exact UTC `Z` timestamps and their source `valid_time_rule`.
- A06 selected-hour context uses the recorded `valid_time_utc` and zero-based selected-hour index from the manifest. A06 `per_cell_event_peak` context has `valid_time_utc=null` and `selected_hour_index_zero_based=null`, because each cell can peak at a different instant.
- Never synthesize timestamps, interpolate quantitative depth values, or present an interpolated time as a saved/modelled state. A visual transition may be presentation-only and must not change or imply quantitative intermediate values.

## Spatial grid, units, bands and coverage

The manifest records EPSG:32644, a 69 × 88 grid, 600 m square pixels, and affine transform `[600, 0, 390000, 0, -600, 1471620]`. Each asset reference is a single Float32 GeoTIFF with the exact CRS, grid, NoData value, byte size, and SHA-256 recorded in the manifest.

Depth is represented in metres (`m`) based on the Phase 11/12 reports. The source GeoTIFF band-unit metadata is unset (`null`); preserve that fact and do not describe the units as raster-tag-confirmed. Keep the manifest's `units_basis` text. `p05`/`p50`/`p95` describe spread over 20 parameter members, not calibrated confidence or statistical coverage.

NoData is `-9999.0`; the manifest-level description is `outside assessed CMA or otherwise unmodelled; it is unknown coverage, not dry`, while each current raster reference records `outside assessed CMA; not dry`. Preserve each source string, masks, and recorded valid/NoData counts. Do not normalize these distinct provenance fields or replace NoData/missing values with zero.

## Provenance and API projection

Every raster reference retains its manifest-relative path, SHA-256, byte size, grid, dtype, band unit metadata, units and units basis, NoData and coverage counts, and source status. Top-level provenance retains the A05/A06 declared-input SHA-256 records, forecast/simulation summary paths and hashes, and `source_hash_status`.

The new projection is deliberately separate from frozen C4 `/scenario` and backend `/scenarios`:

| Method and path | Operation ID | Purpose |
|---|---|---|
| `GET /scenario-visualization-assets` | `listScenarioVisualizationAssets` | List manifest-backed event/scenario identities and temporal context. |
| `GET /scenario-visualization-assets/{event_id}/{scenario_id}` | `getScenarioVisualizationAsset` | Return the saved series and its manifest-backed asset references. |

CR-009 approves both operations in the AI service and Spring backend. B21 mounted and verified the catalog/detail operations in the local B11 app-tier package; its report records successful catalog/detail smoke responses and read-only mount inspection. This evidence is limited to that local package and does not establish any live feed, operational flood behavior, database integration, or deployment outside B11. Catalog and exact-detail success projections are the manifest-backed shapes described above. Detail selector and failure mappings are: invalid input 400; no exact match 404; duplicate/ambiguous identity 409; missing, unreadable, changed, or unavailable manifest/assets 503 with no partial result. Catalog failures use 503 with no partial result. These mappings do not make C9 frozen or operational.

## Approved HTTP response semantics (CR-009)

- `GET /scenario-visualization-assets`: 200 catalog; 409 if the validated manifest contains a duplicate or ambiguous scenario identity; 503 if the manifest or any required referenced asset cannot be completely validated. B21 verified the local B11 package.
- `GET /scenario-visualization-assets/{event_id}/{scenario_id}`: 200 exact detail; 400 invalid selector; 404 no exact identity; 409 duplicate/ambiguous identity; 503 missing, unreadable, changed, or unavailable manifest/assets, with no partial result. B21 verified the local B11 package.
- Only these two GET operations are approved. No prediction, live-feed, alert, routing, database, migration, or science-generation behavior is in scope.

## Limits

This is a regional research presentation on the saved 600 m grid with coarse, unevenly spaced scenario times. It is not validated hydraulics, street-level flow, building water levels, a live prediction, warning, safe route, or emergency guidance. A05 hindcasts and A06 scenario outputs remain derived/assumption-based; p05/p95 are parameter spread, not calibrated uncertainty. GLO-30 is a surface model, not a bare-earth DEM or building DSM. No new scientific values or higher spatial/temporal resolution are implied.

## Evidence

`docs/FLOOD_3D_SCENARIO_READINESS.md`, `data/features/visualization3d/batch2_v1/manifest.json`, `data/features/forecast/batch2_v1/forecast_summary.json`, `data/features/simulation/batch2_v1/simulation_summary.json`, `docs/api/ai-service.yaml`, `docs/api/backend.yaml`, and `tests/master/test_scenario_visualization_contract.py`.
