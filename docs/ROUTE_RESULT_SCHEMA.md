# Scientific route-result schema — Lane A G0 repair proposal

**Status:** implementable Lane A proposal, not frozen, not a routing run, and not safety guidance. Local draft version `route-result-v0.1-draft`; shared C8 and C4 versions remain unchanged. No A08/A09 graph or route result is asserted to exist.

## Record and time model

The canonical wire format is UTF-8 JSON. One record describes one origin/destination route candidate under one graph version, hazard/twin run, scenario, travel mode, and departure instant. Route edge IDs are ordered from origin to destination. Timestamps are RFC 3339 date-times with explicit offset, serialized in UTC with `Z`. All validity intervals are half-open `[start,end)`.

`departure_at_utc` is the requested departure instant, not the forecast issue time. `hazard_run.issued_at_utc` is when its forcing/run was created; `hazard_run.valid_start_utc` and `valid_end_utc` delimit when hazard depth inputs exist. `requested_horizon_seconds` is `departure_at_utc - issued_at_utc`; if departure falls outside the run validity interval, return an unavailable/coverage status, not an extrapolated route. `arrival_at_utc` is nullable and equals departure plus the evaluated edge travel times only for a temporally assessed route.

## Field contract

| Field | Type / units | Semantics and null behavior |
|---|---|---|
| `schema_id`, `schema_version`, `result_id` | strings | Fixed identifiers for this proposal and unique result key. |
| `status` | enum | `ROUTE_FOUND`, `NO_TOPOLOGICAL_PATH`, `INSUFFICIENT_HAZARD_COVERAGE`, `BELOW_ACCESSIBILITY_CONSTRAINT`, or `INPUT_UNAVAILABLE`. Distinguish a graph path from a flood-accessible recommendation. |
| `run_id`, `scenario_key`, `source_mode` | integer, string, enum | Link to the run/scenario; mode is `OBSERVED`, `DERIVED`, `SIMULATED`, `ASSUMPTION`, `REPLAY`, or `NONE`. Simulation truth remains simulated. |
| `origin_id`, `destination_id`, `travel_mode` | strings, enum `vehicle`/`walking` | Stable endpoint IDs and selected graph mode. |
| `departure_at_utc`, `arrival_at_utc` | date-time, nullable date-time | Requested departure and computed arrival. Arrival is null if no path or required time/hazard data are unavailable. |
| `requested_horizon_seconds` | integer, nullable integer | Elapsed seconds from hazard-run issue time to departure. Null if no issue time is known. |
| `distance_m` | nonnegative number, nullable | Sum of graph-edge lengths in metres; null if no topological path. |
| `travel_time_seconds` | nonnegative number, nullable | Time-dependent sum of edge travel times in seconds; null if no path or insufficient time/edge data. Do not store minutes under this name. |
| `topologically_reachable` | boolean, nullable | Whether the selected graph has a route before hazard restrictions; null when graph inputs are unavailable. This is not a safety/passability decision. |
| `route_accessibility_probability` | number `[0,1]`, nullable | Fraction of available ensemble members for which every route edge is passable over its traversal interval. Null when ensemble or complete edge assessment is unavailable; do not substitute a deterministic boolean. |
| `route_failure_probability` | number `[0,1]`, nullable | `1 - route_accessibility_probability` only when the latter is defined. |
| `minimum_accessibility_probability` | number `[0,1]`, nullable | Requested decision constraint; route below it has status `BELOW_ACCESSIBILITY_CONSTRAINT`, not a claim that no graph path exists. |
| `route_geometry` | GeoJSON LineString or null | Ordered WGS84 longitude/latitude coordinates (RFC 7946), transformed from the graph CRS for serialization. Null unless a topological path exists. No fabricated straight line. |
| `edges` | array | Ordered edge records with `edge_id`, `entry_at_utc`, `exit_at_utc`, `distance_m`, `travel_time_seconds`, nullable `depth_max_m`, nullable `passable_probability`, `bridge`, `tunnel`, and `assessment_status`. Missing depth is `UNASSESSED`, never dry/passable. |
| `depth_thresholds` | object | `block_at_or_above_m` plus applied sensitivity values. The existing default 0.30 m is an assumption; the specified sensitivity interval is 0.15–0.50 m. Record bridge/underpass-specific rule separately; no unverified structure rule is silently applied. |
| `edge_coverage` | object | Integer `route_edge_count`, `assessed_edge_count`, `unassessed_edge_count`, and nullable `fraction_assessed`. Zero route edges has null fraction. Partial coverage makes route probability null unless the chosen method explicitly models missing edges and records that method. |
| `graph` | object | Required `graph_id`, `graph_version`, `graph_sha256` when available, `crs`, `edge_source_ids`, `build_algorithm`, `build_version`, and bridge/tunnel/default-speed assumptions. Unknown hashes remain null and are flagged. |
| `hazard_run` | object | `run_id`, `version`, `issued_at_utc`, validity interval, depth artifact/source id, source SHA-256, and `ensemble_id`; fields not known remain null. |
| `uncertainty` | object | Method, ensemble member count, travel-time spread (seconds; nullable), and stated limitations. A single deterministic result has null accessibility probability and explicit `NOT_AVAILABLE`, unless a probability is actually computed. |
| `provenance` | object | Required algorithm/version, code commit, graph and hazard references, depth model/source, parameter values, input file/source IDs and hashes where available, and `generated_at_utc`. |
| `qc_flags` | array of strings | E.g. `DEPTH_NODATA_ON_ROUTE`, `DEPARTURE_OUTSIDE_HAZARD_VALIDITY`, `ASSUMED_SPEED`, `BRIDGE_RULE_UNVERIFIED`, `SIMULATED_TRUTH`, or `GRAPH_HASH_UNKNOWN`. |

## Example

Shape-only example; it is not a computed route.

```json
{
  "schema_id": "twinguard.route_result",
  "schema_version": "0.1-draft",
  "result_id": "example-not-a-real-route",
  "status": "INPUT_UNAVAILABLE",
  "run_id": 0,
  "scenario_key": "example",
  "source_mode": "SIMULATED",
  "origin_id": "origin-example",
  "destination_id": "destination-example",
  "travel_mode": "vehicle",
  "departure_at_utc": "2026-01-01T00:00:00Z",
  "arrival_at_utc": null,
  "requested_horizon_seconds": null,
  "distance_m": null,
  "travel_time_seconds": null,
  "topologically_reachable": null,
  "route_accessibility_probability": null,
  "route_failure_probability": null,
  "minimum_accessibility_probability": null,
  "route_geometry": null,
  "edges": [],
  "depth_thresholds": {"block_at_or_above_m": 0.3, "threshold_is_assumption": true, "sensitivity_m": [0.15, 0.3, 0.5]},
  "edge_coverage": {"route_edge_count": 0, "assessed_edge_count": 0, "unassessed_edge_count": 0, "fraction_assessed": null},
  "graph": {"graph_id": null, "graph_version": null, "graph_sha256": null, "crs": "EPSG:32644", "edge_source_ids": [], "build_algorithm": null, "build_version": null, "assumptions": []},
  "hazard_run": {"run_id": null, "version": null, "issued_at_utc": null, "valid_start_utc": null, "valid_end_utc": null, "depth_source_id": null, "depth_source_sha256": null, "ensemble_id": null},
  "uncertainty": {"method": "NOT_AVAILABLE", "ensemble_member_count": 0, "travel_time_spread_seconds": null, "limitations": ["No route was calculated."]},
  "provenance": {"algorithm": null, "algorithm_version": null, "code_commit": null, "generated_at_utc": "2026-01-01T00:00:00Z", "parameters": {}},
  "qc_flags": ["EXAMPLE_ONLY", "ROUTE_NOT_COMPUTED"]
}
```

## API/UI compatibility findings and exact integrator recommendations

Read-only comparison of current consumers found:

- `docs/api/ai-service.yaml` `RouteRequest` has `run_id`, `departure_at`, `origin`, `destination`, mode and optional accessibility minimum. Its `RouteResponse` has `reachable`, `edge_ids`, `travel_time_minutes`, optional `route_accessibility_probability`, and open-ended provenance; no distance, arrival, horizon, graph/hazard versions, edge coverage, depth threshold, uncertainty or explicit null behavior.
- `docs/api/backend.yaml` `RouteRequest` is similar, but `RouteResult` omits `route_accessibility_probability` and also lacks distance/coverage/threshold fields. `services/backend/.../RouteResponse.java` does implement `travel_time_minutes` and `route_accessibility_probability`, so the backend spec/DTO mismatch itself requires owner B/I review.
- UI `RouteSummary` in `frontend/src/ui/types.ts` has `reachable`, optional `travelTimeMinutes`, optional `accessibilityProbability`, and `provenance`; the current panel explicitly requires geometry, travel time, probability, graph version, and uncertainty, and displays no route as safe. It has no distance or edge coverage fields.

**Proposed projection mapping for integrator/API owners:** retain current `reachable` only as a compatibility projection of `topologically_reachable`; add `status`, `distance_m`, `travel_time_seconds` (or document an exact seconds-to-`travel_time_minutes` projection), `arrival_at_utc`, `requested_horizon_seconds`, `route_accessibility_probability`, `route_failure_probability`, `minimum_accessibility_probability`, `graph_version`, `hazard_run`, `depth_thresholds`, `edge_coverage`, typed `uncertainty`, and typed `provenance` to both OpenAPI response schemas. Mark graph/path/measurement fields nullable where inputs are unavailable; require explicit status/QC flags. The UI adapter can project seconds to minutes and snake_case to camelCase but must preserve nulls and show unassessed coverage as unknown. Lane A does not edit either shared OpenAPI document or UI code.

**NoData rules:** no topological path means `distance_m`, `travel_time_seconds`, `arrival_at_utc`, and geometry are null; `edges=[]`; `status=NO_TOPOLOGICAL_PATH`. Missing hazard depth for any route edge is not evidence of passability. Report counts and fraction; if any required segment is unassessed, report the accessibility probability null and a partial-coverage status/flag. A zero travel time, zero length or probability zero is emitted only when actually computed with valid inputs. Never call a route safe without independent validation.

No routing result, graph output, database row, API compatibility, or safety claim is produced by this schema proposal. A08/A09 remain subject to the selector/dependencies and G0 review.
