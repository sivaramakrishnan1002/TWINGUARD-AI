# Track B G0 repair evidence and Integrator review proposals

Updated 2026-10-27. This file records Lane B evidence and proposed edits to Integrator-owned OpenAPI contracts. It does not modify `docs/api/ai-service.yaml`, `docs/api/backend.yaml`, `docs/master/`, or the shared database.

## B19 date-only correction — 2026-10-28

B19 supersedes the earlier C3 description of midnight `Asia/Kolkata` as a provisional replay encoding. The source archive still provides only calendar dates; no authoritative measurement-time or timezone evidence was found. Track B no longer emits that default for date-only historical rows. The canonical representation is `source_date` (`YYYY-MM-DD`), `time_precision="date"`, `observation_timezone="unknown"`, and `observed_at=null`; `received_at` is a separate aware ingestion instant. Date-only derived alerts also have null exact-validity fields. Real timestamped rows preserve their supplied offset and instant. Producer, replay, consumer, persistence payload, and API serialization follow this representation. **C3 remains unresolved** until source-owner evidence establishes date semantics/timezone.

Migrations 010/100 have non-null instant requirements and timestamp keys for `twin.reservoir_state`, `twin.alerts`, `trackb.alert_events`, and `twin.trackb_recompute_markers`. B19 adds `database/migrations/101_trackb_date_only_reservoir_observations.sql` as an additive proposal: date-keyed reservoir state and recompute markers, plus a date-only alert event table with separate `received_at`. Existing tables and timestamped data are unchanged. Date-only alerts are not projected into `twin.alerts`, whose required exact interval cannot represent them. Migration 101 was not applied; no database was connected to or modified. Shared `twinguard` and isolated `twinguard_trackb_test` were left untouched.

## C3 — historical reservoir timezone

- Inspected the raw archive `data/raw/reservoirs/kaggle_chennai_water_management/archive.zip` read-only. It contains `chennai_reservoir_levels.csv` and `chennai_reservoir_rainfall.csv`; both headers are `Date` plus reservoir names. The source fields contain calendar dates only and declare neither a timezone nor a measurement time.
- Repository source notes and the archive do not establish the historical timezone. Do not infer one from value patterns. C3 remains **unconfirmed / blocked on source-owner evidence**.
- Producer behavior: `pipelines/trackb/streaming.py` and `pipelines/trackb/replay.py` encode daily replay rows at midnight `Asia/Kolkata`, mark `date_timezone=Asia/Kolkata` and preserve `timezone_status=DEFAULT, to confirm`.
- Consumer behavior: `validate_event` requires an offset-bearing `observed_at`; `_rain` and `_reservoir` derive daily keys from its source-calendar date without host-timezone conversion; alert validity adds one day to the same offset-aware timestamp; persistence stores the timestamp in PostgreSQL `timestamptz`. Producer and consumer therefore agree on the encoded instant and date key, while the historical source timezone itself remains unresolved.
- Required closure evidence: a source-owner/specification stating the timezone and what the date denotes (measurement instant, reporting day, or aggregation period). Until then, preserve the default/unconfirmed marker.

## C4 — Track B DTOs and OpenAPI changes for Integrator

Track B backend DTOs now carry the AI request's optional `minimum_accessibility_probability` (0–1) and the AI response's optional `route_accessibility_probability` (0–1). `travel_time_minutes` remains minutes and nullable. Missing numeric outputs are JSON `null`, never zero. Track B API responses already require a source class (`replay|live|simulated`) on rows and label backtest summaries `DERIVED`; backend gateway placeholders return unavailable/not-configured and do not fabricate a successful result. AI route/forecast/impact endpoints remain HTTP 501 stubs.

The following are proposals for Integrator to apply to `docs/api/ai-service.yaml` and `docs/api/backend.yaml`:

1. Add `minimum_accessibility_probability` (optional number, range [0,1]) to backend `RouteRequest`; keep its AI name and range unchanged.
2. Add nullable `route_accessibility_probability` (number, range [0,1]) to backend `RouteResult`, matching AI `RouteResponse`. Mark `travel_time_minutes` nullable in both. Specify that null means “not calculated/unavailable”; zero is a measured result, and missing coverage is not a negative result.
3. Use a common required provenance object with `source` enum `replay|live|simulated`, `source_id`, `schema_version`, and optional `source_file`, `source_sha256`, `run_id`, and `assumptions`; prohibit credentials and unbounded identifiers in public labels. Track B can provide the event source and provenance; the gateway must preserve them.
4. Add `source` to response records that expose Track B-derived state/alerts. Preserve exact source values; do not map replay to live. Define app alert severity projection as `Normal→INFO`, `Watch→WATCH`, `Warning→WARNING`, `Critical→EMERGENCY`; keep the Track B alert vocabulary in the underlying Track B API.
5. Keep responses semantically distinct: AI unimplemented operation is 501; configured service with unavailable dependency is 503; an unknown run/time is 404; successful response with unavailable measurements uses explicit nullable values plus coverage/NoData metadata. Backend not-configured gateway results must not be represented as HTTP 200 successful domain results.
6. Extend AI `Layer` with `source_crs: string`, `units: object<string,string>` (empty object when no units are verified), nullable `zoom: {min: integer 0..22, max: integer 0..22}`, nullable `attribution`, nullable `vintage`, `provenance: {source_sha256: string|null, source_url: string|null}`, `nodata: string`, and `tile_endpoint_available: boolean`. Keep `target_srid` and `loaded_row_count`. Clarify this is catalogue metadata; a database MVT function does not imply an HTTP tile route.

No master OpenAPI file was edited. Integrator review is still needed to accept and apply these proposals.

## C5 — layer catalogue and tile capability

The Track B-owned AI `/layers` adapter now exposes the catalogued source CRS, target SRID, source hash/URL provenance, licence/attribution, source vintage, loaded row count, known units, and explicit NoData/tile availability fields. Fields unavailable in the source catalogue are `null`, `{}`, or explicit `not_declared_in_catalogue`; they are not inferred. A loaded count of zero means no features are loaded for that catalogue entry.

Migration `002_gis_views_and_mvt.sql` defines database MVT functions for study area, roads, facilities, waterways, and flood references. Those functions constrain zoom to 0–22 and serialize Mapbox Vector Tiles, but no HTTP tile route is implemented. The adapter therefore reports `tile_endpoint_available=false`; a possible MVT zoom range is included only for the evidenced function families. It does not invent a URL or claim tiles are served. Raster/no-data conventions must be supplied by a raster catalogue before advertising raster layers.

Units are exposed only when the layer's source-field mapping is established (currently road length `m`, speed `km/h`, travel time `min`; reservoir observations `mcft` when that named source layer is present). Other units remain absent rather than guessed. Attribution is copied from the catalog's licence note; vintage is nullable unless the catalog records it.

## C6 — Track B serialization versus twin schema

Track B events use UTF-8 JSON Lines, one JSON object per line, with versioned `schema`, stable `event_id`, offset-bearing timestamps, source class, provenance, unit-named numeric fields, nullable missing measurements, and QC arrays. JSON integers/numbers/strings/booleans/null map to corresponding PostgreSQL scalar types; nested event/provenance/trigger payloads map to `jsonb`; timestamp strings with offsets map to `timestamptz`; source is constrained to `replay|live|simulated`. `event_id`/marker keys provide idempotency keys.

Migration 100 stores alert event payloads as `jsonb`, timestamps as `timestamptz`, and source as a constrained text enum-like check. Twin reservoir state uses unit-bearing columns (`rainfall_mm`, `storage_mcft`, `capacity_mcft`, `release_cusecs`) and nullable capacity/release; `twin.alerts` carries alert values and interval timestamps; link/marker keys are unique for idempotency. Null means unavailable and is not coerced to zero. The Track B persistence adapter preserves source and event provenance in payloads and normalizes reservoir identifiers to the seeded twin keys.

Schema compatibility was checked from migration SQL and the Track B adapter. The isolated database `twinguard_trackb_test` has migrations 001/005/010/100 and prior persistence/idempotency evidence; the shared `twinguard` database is not touched by this repair. This static mapping is not itself a new database write or a claim of live runtime integration. C6 remains pending Integrator freeze review.
