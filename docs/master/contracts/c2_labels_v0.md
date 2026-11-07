# C2 accepted label registry v0

**Status:** frozen v0 contract for G0 (2026-10-28). Consumers use only `labels.v_usable_flood_labels`; accepted tiers A/B/C are eligible. Tier D, rejected, invalid, or unaccepted derived candidates are excluded. Preserve rejected source rows and provenance; this view is not field ground truth.

## Serialization and geometry

- A database record is a row of `labels.v_usable_flood_labels`. Wire/export representation is a GeoJSON Feature with the exact properties `label_key`, `event_date`, `method`, `reference_role`, `tier`, `is_derived`, `is_valid`, `in_cma`, `source_id`, `source_sha256`, `loader`, and `load_time`; `geom` is emitted as RFC 7946 WGS84 geometry.
- Stored geometry is valid polygonal geometry in SRID 32644. Do not clip stored geometry to the CMA; a CMA-only consumer intersects it explicitly.
- Accepted geometry is non-null, non-empty, valid polygonal geometry. Null/empty/invalid/non-polygon geometry must fail acceptance with a QA reason and must never appear as an accepted feature with `geometry:null`.
- Provenance keys remain present. Unknown source hash/loader metadata is JSON null and marks provenance incomplete; do not invent identifiers.

## Time and label semantics

- `event_date` is SQL DATE / JSON `YYYY-MM-DD` for the map/reference date, not onset or acquisition instant.
- `load_time` is PostgreSQL `timestamptz`, serialized as UTC RFC 3339.
- `reference_role=baseline_water` remains distinct from `event_flood` and is never a positive flood label. The view exposes official event/baseline references and only derived rows with tier A/B/C, valid/in-CMA flags and `review_status=ACCEPTED`.

Evidence: `database/migrations/014_stage8_label_hygiene.sql`, `docs/LABEL_DATASET.md`, `docs/LANE_A_G0_REPAIR_PROPOSALS.md`, A19's `pipelines/labels/export_usable_labels_geojson.py` and `tests/labels/test_usable_labels_geojson.py`, and `docs/LABEL_GEOJSON_EXPORT.md`. A19 records 10,419 serialized rows (8,414 `event_flood`, 2,005 `baseline_water`), zero rejected rows, output and QA hashes, and focused serialization tests for exact properties, WGS84 geometry, UTC time, null provenance, filtering and invalid-geometry rejection. This evidences the local GeoJSON export shape, not field truth or a deployed API. The G0 freeze records this serialization contract only; it does not assert field truth or deployed API operation.
