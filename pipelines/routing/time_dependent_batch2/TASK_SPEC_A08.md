# A08 task spec — time-dependent flood-aware graph overlay

## Inputs

- Completed A07 outputs under `data/features/impact/batch2_v4_contract/`.
- A05 member depth arrays under `data/features/forecast/batch2_v1/{event}/{scenario}/depth_members_by_horizon_DERIVED.npz`.
- Static road segments, directed arcs, and nodes in `data/features/roads/chennai_road_graph.gpkg`.

## Outputs

- Compact cell-keyed dynamic graph overlays for each event/scenario, with member and horizon axes, under `data/features/routing/time_dependent_batch2/`.
- Static segment and directed-arc indexes that preserve original graph topology and link overlay cells to edge ids.
- A snapshot index and JSON summary with graph counts, per-snapshot coverage/state counts, and state transitions.
- Implementation, tests, and scientific interpretation in Lane A-owned `pipelines/routing/`, `tests/routing/`, and `docs/` paths.

## Fixed interpretation

This is an offline simulated research overlay, not a live graph, route result, safety assessment, or operational recommendation. Base topology remains the existing directed OSM graph. Dynamic state is keyed to the A07 600 m midpoint-sample cell index, not to local roadway hydraulics. Ordinary edges use a 0.30 m block threshold; any OSM tunnel or `building_passage` uses a lower 0.15 m threshold under the explicit “underpasses flood first” assumption. Speed factor is the assumption `max(0.2, 1 - 0.8 * depth / threshold)` below threshold. Bridge edges remain unassessed because no bridge-deck elevation/depth is available. NoData is always unknown, never dry or open.

## Acceptance

- Verify input hashes and A07/A05 depth-statistic consistency before producing outputs.
- Preserve road segment/directed arc topology, bridge/tunnel attributes, edge-to-cell lookup, and unknown coverage.
- Save compact snapshots indexed by event, scenario, horizon time, and ensemble member.
- Validate base graph counts, state transitions across horizons, and NoData/structure handling in tests.
- Run focused tests and the raw-data audit. Do not alter `data/raw/` or any prior outputs.
