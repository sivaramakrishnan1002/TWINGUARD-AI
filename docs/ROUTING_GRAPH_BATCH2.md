# A08 — Time-dependent flood-aware graph overlay

## Result and scope

Built an offline, cell-keyed dynamic overlay for the existing directed OSM road graph using the completed A07 edge-to-cell index and the A05/A06 member depth arrays. Outputs are explicitly **SIMULATED RESEARCH OUTPUTS**. They do not calculate routes, establish safe roads, represent live conditions, or validate hydraulic truth.

The grid is the A07 600 m EPSG:32644 simulation grid (88 × 69). Each of 15 event/scenario archives stores depth and edge-state overlays for 20 members at five lead times (6, 12, 24, 48, 72 h): **1,500 time/member snapshots**, about **51.5 MB** of graph output. Snapshot arrays are keyed by 2,400 unique road-bearing grid cells rather than repeating a million-edge topology for every timestamp. `directed_arcs.parquet` preserves the static directed topology and links arcs to the snapshot cell and structure type; `snapshot_index.parquet` records each event, scenario, UTC valid time, lead, member and coverage/state counts.

## Graph and coverage counts

| Measure | Count |
|---|---:|
| Road nodes | 508,854 |
| Physical road segments | 566,307 |
| Directed OSM arcs | 1,071,656 |
| Segments with A07 eligible-cell midpoint sample | 405,601 (71.6%) |
| Segments without an A07 eligible-cell assignment | 160,706 |
| Directed arcs with a mapped A07 cell | 768,688 (71.7%) |
| Directed arcs without an A07 cell or with an ambiguous segment match | 302,968, including 4 ambiguous arcs |
| Unique mapped road-bearing grid cells | 2,400 of 2,430 eligible A07 cells |

One duplicate OSM `(osmid, endpoint pair)` key prevents an unambiguous segment-to-arc join for four directed arcs. Those arcs remain in the static graph index and are marked unassessed; they are not deleted. The other 302,964 arcs lack an A07 eligible-cell assignment. This can mean outside the modeled eligible grid; it does not assert that they are outside the CMA.

All 2,400 road-bearing cells have finite member depth in these saved A05 snapshots (3,600,000 valid cell snapshots and zero missing depth cells). This does **not** make the full graph fully assessed: 302,968 directed arcs have no unique A07 edge-depth assignment. The code also preserves a `UNKNOWN_NODATA` state and null/NaN speed factor if a future input contains a missing depth; tests confirm missing is never translated to open/dry.

## Structure and speed rules — assumptions

- Ordinary road edges are marked blocked at depth **≥0.30 m**. A sensitivity range of 0.15, 0.30 and 0.50 m is recorded from A07’s threshold screens; this task’s default overlay uses 0.30 m.
- OSM tunnel and `building_passage` tags use a lower **0.15 m** block threshold, under the assumption that underpasses flood first. The source graph does not independently identify every underpass, so a tunnel tag is only a proxy.
- Bridges are kept as `UNASSESSED_STRUCTURE`, even where the roadway-cell depth is finite. There is no bridge deck elevation/depth to compare with the water surface, so these edges are neither assumed open nor blocked.
- For a non-blocked, assessed edge, the assumed depth multiplier is `max(0.2, 1 - 0.8 × depth / threshold)`. At or above threshold the edge is blocked and multiplier is zero. This simple rule is a prototype assumption, not a calibrated speed-depth relationship.
- A single parseable OSM `maxspeed` value supplies the base speed for 10,546 segments. Highway-class defaults supply speeds for 555,761 segments; those defaults are assumptions. No travel-time route is computed here.

The graph contains 4,486 bridge-only segments, 3 segments tagged as both bridge and tunnel, and 330 tunnel/underpass-proxy-only segments. In the mapped directed graph, 3,535 bridge-only arcs and 6 bridge/tunnel arcs remain structurally unassessed.

## Transition check

The verifier reopened every archive, recalculated state and speed arrays from saved depth, matched all 1,500 rows to the index, checked per-class directed arc counts, and recomputed state changes between consecutive horizons. The initial 6-hour step is explicitly `NO_PREVIOUS_HORIZON`. Among the 300 member/scenario comparisons at each later horizon, non-zero changes occurred in 255 at 12 h, 260 at 24 h, 260 at 48 h, and 260 at 72 h. Median changed directed arcs (min–max) were 49,275.5 (0–624,654), 115,124.5 (0–657,143), 37,617 (0–765,147), and 66,542 (0–569,027), respectively. These are overlay state transitions, not observed road closures.

## Provenance and checks

The output `run_summary.json` records source hashes, all 15 member archive hashes, graph counts, assumptions, and caveats. Before writing, the builder checked the four source hashes recorded in the A07 run summary (forecast summary, static cell table, source OSM feature package and A06 simulation summary); it also hashed the A07 summary, A07 cell-impact and edge-cell tables, and the separate routing graph package. It verified that each of the 75 A07 event/scenario/horizon cell summaries agrees with the corresponding A05 ensemble mean, descriptive p05/p95 spread, valid-member counts and 0.30 m cell passability probability. The p05/p95 values are descriptive member spread, not calibrated uncertainty coverage.

Commands run:

```powershell
.\.venv\Scripts\python.exe pipelines\routing\time_dependent_batch2\graph_overlay.py
.\.venv\Scripts\python.exe pipelines\routing\time_dependent_batch2\graph_overlay.py --verify-only
.\.venv\Scripts\python.exe -m pytest -q tests\routing --import-mode=importlib
```

The focused routing folder has **8 passing tests**. The full applicable Lane A suite also passed: **105 passed** across `tests/routing`, `tests/labels`, `tests/explainability`, and Phase 8–13 test folders. The raw-data audit passed: 157 files / 30,544,672,450 bytes, 157/157 recorded hashes matched, zero mismatches. No files in `data/raw/` were modified. The implementation deliberately stops at a graph overlay; routing and safety claims require later work and independent validation.
