# A19 — Accepted flood-label GeoJSON export

## Contract and behavior

The exporter reads only `labels.v_usable_flood_labels`, in a PostgreSQL read-only transaction. It performs no database writes or schema changes. A serialized feature must have tier A, B, or C, role `event_flood` or `baseline_water`, `is_valid=true`, `in_cma=true`, and valid, non-empty Polygon or MultiPolygon geometry. Tier D and other rows are excluded. Baseline water is retained as its own `reference_role`; it is never relabelled as a positive flood.

Each output is a GeoJSON FeatureCollection. The exact feature properties are `label_key`, `event_date`, `method`, `reference_role`, `tier`, `is_derived`, `is_valid`, `in_cma`, `source_id`, `source_sha256`, `loader`, and `load_time`. Geometry is transformed from stored EPSG:32644 to longitude/latitude EPSG:4326 (RFC 7946; no legacy `crs` member). SQL DATE values use `YYYY-MM-DD`; timezone-aware `timestamptz` values are converted to UTC RFC 3339 with `Z`. Unknown provenance values stay JSON null. A naive timestamp is rejected because its timezone cannot be inferred safely.

Rows with unsupported tiers/roles, invalid flags, null/empty/unreadable/invalid/non-polygon geometry, or failed geometry transformation are excluded and recorded with a QA rejection reason. Such a row is never emitted as an accepted feature with null geometry. The source view itself currently exposes only tiers A and event/baseline roles; the exporter and tests preserve the contract for accepted B/C rows if present later.

## Command and run result

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe pipelines\labels\export_usable_labels_geojson.py
```

The default creates new files only: `data/features/labels/usable_flood_labels_geojson_v0.geojson` and `data/features/labels/usable_flood_labels_geojson_v0.qa.json`. Existing output paths cause a refusal; choose a new `--output` path to create a separate export. The DB credentials are read from `.env` by the existing project-local parser and are never printed. PostgreSQL is configured read-only for the connection.

Current view inspection and export: **10,419 rows**, comprising 8,414 tier A `event_flood` and 2,005 tier A `baseline_water` rows; all source rows had valid MultiPolygon geometry in EPSG:32644 and non-null provenance fields. Exported count: **10,419**; rejected count: **0**. Output size is 50,658,670 bytes; GeoJSON SHA-256 is `9362f2b2db68a8569629e07c9ef165de9c909250cdc8dfa81f3d1e365845b557`. The QA sidecar hash is `84b4ab49d73a0ce838ad9586880f28094648b2666f5539dda5dbdf7849eafa09`. This is a serialization count, not an independent check that reference labels represent field truth.

## Checks

Unit tests cover exact property keys, WGS84 coordinates, UTC formatting, tier/role filtering, baseline semantics, null provenance, and null/empty/invalid/non-polygon geometry rejection. No raw data or accepted database rows were changed.
