# Lane A G0 repairs — proposed field-level changes

**Date:** 2026-10-27  
**Status:** Lane A documentation repair evidence only. G0 remains not ready; no shared contract is frozen. No task was claimed or marked complete. The current `next_task.py --lane A` selector reports no ready Lane A task, and A07/A08 remain `blocked_prerequisite`. These proposals do not bypass that task state or authorize implementation/data work.

## Ownership and evidence reviewed

Read-only review covered `docs/master/GATE_G0_REPORT.md`, `docs/master/PROTOCOL.md`, `docs/master/OWNERSHIP.md`, `docs/master/STATE.json`, `docs/master/NEXT.md`, `docs/batches/BATCH_2.md`, `docs/batches/BATCH_2_PROGRESS.md`, C1/C2/C7/C8 v0 drafts, T6 depth docs/JSON/TIFF metadata, migration 014, AI/backend OpenAPI, AI and backend route DTOs, and UI types/panel. The Lane A state verifier passed. No shared `docs/master/` file, OpenAPI document, API/UI source, database, or raw data was edited.

## Exact recommendations for the integrator

### C1 — depth file and metadata contract

Use the Lane A detail in `docs/DEPTH_FIELD_CONTRACT.md`:

1. State one-band-per-file GeoTIFF, band 1 Float32 metres, EPSG:32644, 30 m master-grid alignment, `AREA_OR_POINT=Area`, and raster NoData `-9999.0`.
2. Enumerate required tags: `version`, `status`, `band_role`, `units`, `crs`, `grid`, `nodata`, `event_date`, `acquisition_time_utc`, `run_time_utc`, `source`, `source_tier`, `source_geometry_count`, `method`, `uncertainty_rule`, `dem`.
3. Define `event_date` as the source map/reference date (date only); `acquisition_time_utc` as a separately evidenced source acquisition instant (null/unknown for current T6 products); `run_time_utc` as processing time. Do not fabricate midnight timestamps.
4. Explicitly say legacy `p05`/`p95` files store `max(0, mean−4 m)` and `mean+4 m` assumption bounds, not calibrated statistical percentiles or coverage intervals. Recommend semantic `band_role` names while retaining old filenames until a separately authorized migration.
5. Keep DERIVED, assumption-based, GLO-30 surface-model, NoData, low coverage, and unvalidated-depth caveats. Existing T6 TIFF tags were read-only inspected; they lack `band_role`, acquisition time, unit/source-tier/NoData tags, and their ± glyph displays as a replacement character on this host. No TIFF was changed.

### C2 — accepted label row

Use `docs/LABEL_DATASET.md`'s row contract:

1. Accepted output is the `labels.v_usable_flood_labels` row serialized as a GeoJSON Feature. Database geometry is valid polygonal SRID 32644; export coordinates as RFC 7946 WGS84. Do not clip the stored geometry; a CMA-only consumer intersects it explicitly.
2. Preserve the view's exact fields: `label_key`, `event_date`, `method`, `reference_role`, `tier`, `is_derived`, `is_valid`, `in_cma`, `geom`, `source_id`, `source_sha256`, `loader`, `load_time`.
3. `event_date` is SQL DATE / JSON `YYYY-MM-DD`, the map/reference date—not onset or acquisition instant. `load_time` is `timestamptz`, normalized to UTC RFC 3339. Baseline-water rows remain distinct from event-flood rows and are never positive flood labels.
4. Geometry is non-null for an accepted row. Null/empty/invalid/non-polygon geometry is excluded with a QA rejection reason, never serialized as accepted `geometry:null`. Provenance keys remain present; unknown metadata is JSON null and explicitly incomplete. Tier D/rejected candidates remain out of the accepted contract.

### C7 — impact result

Use `docs/IMPACT_RESULT_SCHEMA.md` as the proposed JSON wire/storage shape. It defines an aggregate keyed by run × event × scenario × valid time; UTC event/valid/aggregation/processing semantics; metrics in people, facilities, metres, fractions and probabilities; ensemble descriptive distributions; exact population/facility/road coverage; null versus zero; typed source/hash/model provenance; and QC flags. It preserves WorldPop NoData and does not call a modeled population estimate a census count.

API/UI reconciliation for owners I/B: current AI `ImpactResponse` requires non-null scalar `exposure_people`/`affected_facilities` and open-ended provenance; current UI `ImpactSummary` allows null and also expects affected roads/unit, provenance and uncertainty. Recommend nullable values plus `status`, coverage, units, intervals, uncertainty and typed provenance in the AI projection; map to UI camelCase in the adapter. Backend has no impact response today. Lane A did not edit these shared schemas or UI files.

### C8 — route result

Use `docs/ROUTE_RESULT_SCHEMA.md` as the proposed scientific JSON result. It defines metres and seconds; departure, issue, validity, requested horizon and arrival times; ordered route edges and nullable GeoJSON; graph/hazard hashes and versions; 0.30 m assumed edge threshold and 0.15–0.50 m sensitivity; ensemble route passability; assessed/unassessed edge coverage; explicit status and null behavior; and provenance/QC fields. It separates topological reachability from flood accessibility and never calls a route safe.

API/UI reconciliation for owners I/B: AI OpenAPI currently emits `travel_time_minutes` and optional accessibility probability; backend OpenAPI omits the probability, although its Java DTO includes it. Both omit distance, arrival/horizon, graph/hazard provenance, thresholds, edge coverage, uncertainty and missing-data semantics. Recommend adding one consistent projection to both specs and matching DTOs: canonical `distance_m`, `travel_time_seconds` (or a documented seconds-to-minutes projection), `arrival_at_utc`, `requested_horizon_seconds`, `status`, `route_accessibility_probability`, `edge_coverage`, threshold and provenance objects. Keep UI camelCase conversion in its adapter and preserve nulls. Lane A did not edit shared API/UI files.

## Readiness and disposition

The Lane A selector returned no ready tasks at review time. A05 and A12 are complete with caveats; A07 and A08 are still recorded blocked. The report's ownership boundary assigns shared API reconciliation to I/B and the contract registry/G0 decision to the integrator. The integrator should review these exact field proposals, reconcile the API projections, update the master-owned drafts/checklist, then run the verifier/selector and G0 gate review. Nothing here marks C1/C2/C7/C8 as frozen or A07/A08 as complete.
