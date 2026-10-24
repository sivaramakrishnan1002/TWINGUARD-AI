# Twin data model foundation

This is a schema and interface foundation, not a running or calibrated digital twin. Existing `twinguard` Stage 5 tables remain the read-only source of truth for the static grid, road edges, facilities, observations and labels. Migration `010_create_twin_schema.sql` adds the separate `twin` schema and seeds only event-window metadata plus four reservoir identities found in the loaded daily reservoir observations. It does not create forecast values.

## Entity map

| Entity | Representation | Dynamic state |
|---|---|---|
| Grid zone | `twin.grid_zones` view over the 1,319,380 existing `twinguard.grid_cells` rows; `zone_id` is the existing `cell_id`. | Cell-level rainfall, predicted depth and uncertainty stay in raster/cube files. `twin.grid_state_artifacts` records relative file path, SHA-256, valid time, variable manifest, coverage and NoData/QC policy. No new cell-level state rows are stored. |
| Road edge | Existing `twinguard.road_edges.feature_id`. | `twin.road_edge_state`: rainfall, depth mean plus p05/p95 or ensemble ID, accessibility probability, exposed people, capacity and QC/provenance. |
| Facility | Existing `twinguard.facilities.feature_id`. | `twin.facility_state`: rainfall, depth uncertainty, accessibility probability, exposure and capacity. Capacity remains NULL until a defensible source is added. |
| Reservoir | `twin.reservoirs`; the four loaded series identities are registered with unknown capacities. | `twin.reservoir_state`: storage, capacity, release, rainfall and provenance. Release/capacity are nullable; the current inputs do not provide reliable release series or validated capacity history. |

## Time, versions and provenance

All state timestamps are `timestamptz` in UTC. A run has `issued_at`, a half-open valid interval `[valid_from, valid_to_exclusive)`, and a positive `step_interval`; each entity-state row is keyed by its run, valid time and entity. `twin.model_versions` records component/version, code revision, configuration hash, artifact URI and provenance. `twin.state_runs` captures the replay/scenario/forecast kind, version key, source provenance and QC flags. Grid files must be stored outside Git and referenced by a project-relative URI and checksum.

Depth uncertainty is represented either by ordered `depth_p05_m <= depth_mean_m <= depth_p95_m`, or by an `ensemble_id`; database constraints prevent mixing those two encodings in one row. Accessibility is a probability in `[0,1]`. Exposure and capacities carry unit-specific column names. Null means not available, never zero. QC flags must distinguish missing inputs, modelled values, stale observations and assumptions.

## Event replay calendar

`twin.event_replays` has planned rows for all three windows from `docs/TIME_ALIGNMENT.md`:

| Replay | Inclusive local dates (Asia/Kolkata) | UTC interval (end exclusive) | State |
|---|---|---|---|
| Chennai 2015 | 1 Nov–15 Dec 2015 | 31 Oct 2015 18:30Z–15 Dec 2015 18:30Z | PLANNED |
| Chennai 2021 | 1–20 Nov 2021 | 31 Oct 2021 18:30Z–20 Nov 2021 18:30Z | PLANNED |
| Chennai 2023 | 25 Nov–15 Dec 2023 | 24 Nov 2023 18:30Z–15 Dec 2023 18:30Z | PLANNED |

These are aligned-data windows, not verified flood-onset windows. Event replay is historical input replay only until a forecast implementation, reviewed labels and model validation exist.

## Not implemented

There is no trained model, generated twin state, live update pipeline, calibrated uncertainty, production routing engine or alert logic. The schema has no populated predicted-state rows. API documents define intended contracts only.
