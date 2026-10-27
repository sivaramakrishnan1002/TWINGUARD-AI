"""Build compact, read-only-input time-dependent road graph overlays for A08."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FORECAST_ROOT = ROOT / "data/features/forecast/batch2_v1"
IMPACT_ROOT = ROOT / "data/features/impact/batch2_v4_contract"
ROADS_GPKG = ROOT / "data/features/roads/chennai_road_graph.gpkg"
OUTPUT = ROOT / "data/features/routing/time_dependent_batch2"
GRAPH_CRS = "EPSG:32644"
GRID_SHAPE = (88, 69)
GRID_CELL_COUNT = GRID_SHAPE[0] * GRID_SHAPE[1]
DEFAULT_ROAD_THRESHOLD_M = 0.30
TUNNEL_THRESHOLD_M = 0.15
SPEED_FLOOR = 0.20
SPEED_REDUCTION_AT_THRESHOLD = 0.80
SENSITIVITY_THRESHOLDS_M = (0.15, 0.30, 0.50)

STATE_UNKNOWN = 0
STATE_OPEN = 1
STATE_REDUCED = 2
STATE_BLOCKED = 3
STATE_STRUCTURE_UNASSESSED = 4
STATE_NAMES = {
    STATE_UNKNOWN: "UNKNOWN_NODATA",
    STATE_OPEN: "OPEN_ASSUMED",
    STATE_REDUCED: "SPEED_REDUCED_ASSUMED",
    STATE_BLOCKED: "BLOCKED_ASSUMED",
    STATE_STRUCTURE_UNASSESSED: "UNASSESSED_STRUCTURE",
}

DEFAULT_SPEED_KMH = {
    "motorway": 90.0, "motorway_link": 50.0,
    "trunk": 70.0, "trunk_link": 40.0,
    "primary": 50.0, "primary_link": 35.0,
    "secondary": 40.0, "secondary_link": 30.0,
    "tertiary": 35.0, "tertiary_link": 25.0,
    "residential": 30.0, "living_street": 10.0,
    "unclassified": 25.0, "road": 25.0, "service": 15.0,
    "track": 10.0, "cycleway": 10.0, "footway": 5.0,
    "path": 5.0, "pedestrian": 5.0, "steps": 3.0,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def positive_osm_flag(value: object) -> bool:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return False
    return str(value).strip().lower() not in {"", "no", "false", "0", "none", "nan"}


def edge_structure(bridge: object, tunnel: object) -> str:
    has_bridge, has_tunnel = positive_osm_flag(bridge), positive_osm_flag(tunnel)
    if has_bridge and has_tunnel:
        return "bridge_and_tunnel"
    if has_bridge:
        return "bridge"
    if has_tunnel:
        return "tunnel_underpass_proxy"
    return "ordinary"


def parse_speed_kmh(raw: object, highway: str) -> tuple[float, str]:
    """Parse a single OSM maxspeed token; otherwise use a documented class default."""
    if raw is not None and not (isinstance(raw, float) and math.isnan(raw)):
        match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(mph|km/?h|kph)?\s*", str(raw), re.I)
        if match:
            speed = float(match.group(1))
            if match.group(2) and match.group(2).lower() == "mph":
                speed *= 1.609344
            if speed > 0:
                return speed, "OSM_MAXSPEED"
    return DEFAULT_SPEED_KMH.get(highway, 20.0), "ASSUMED_HIGHWAY_DEFAULT"


def depth_state(depth_m: np.ndarray | float, threshold_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Return state code and assumed speed multiplier; unknown is not passable."""
    if threshold_m <= 0:
        raise ValueError("Depth block threshold must be positive")
    depth = np.asarray(depth_m, dtype=np.float32)
    finite = np.isfinite(depth)
    state = np.full(depth.shape, STATE_UNKNOWN, dtype=np.uint8)
    state[finite & (depth <= 0)] = STATE_OPEN
    state[finite & (depth > 0) & (depth < threshold_m)] = STATE_REDUCED
    state[finite & (depth >= threshold_m)] = STATE_BLOCKED
    speed = np.full(depth.shape, np.nan, dtype=np.float32)
    speed[finite & (depth <= 0)] = 1.0
    reduced = finite & (depth > 0) & (depth < threshold_m)
    speed[reduced] = np.maximum(
        SPEED_FLOOR,
        1.0 - SPEED_REDUCTION_AT_THRESHOLD * (depth[reduced] / threshold_m),
    )
    speed[state == STATE_BLOCKED] = 0.0
    return state, speed


def structure_state(depth_m: np.ndarray | float, structure: str) -> tuple[np.ndarray, np.ndarray]:
    depth = np.asarray(depth_m, dtype=np.float32)
    if structure in {"bridge", "bridge_and_tunnel"}:
        return (
            np.full(depth.shape, STATE_STRUCTURE_UNASSESSED, dtype=np.uint8),
            np.full(depth.shape, np.nan, dtype=np.float32),
        )
    threshold = TUNNEL_THRESHOLD_M if structure == "tunnel_underpass_proxy" else DEFAULT_ROAD_THRESHOLD_M
    return depth_state(depth, threshold)


def state_transition_count(previous: np.ndarray | None, current: np.ndarray, weights: np.ndarray | None = None) -> int:
    current = np.asarray(current)
    if previous is None:
        return 0
    changed = np.asarray(previous) != current
    if weights is None:
        return int(changed.sum())
    return int(np.sum(changed.astype(np.int64) * np.asarray(weights, dtype=np.int64)))


def _key(osmid: object, n1: object, n2: object) -> tuple[int, int, int] | None:
    try:
        if pd.isna(osmid) or pd.isna(n1) or pd.isna(n2):
            return None
        a, b = int(n1), int(n2)
        return int(osmid), min(a, b), max(a, b)
    except (ValueError, TypeError, OverflowError):
        return None


def build_static_graph() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    segments = pyogrio.read_dataframe(
        ROADS_GPKG, layer="road_segments",
        columns=["osmid", "node_a", "node_b", "highway", "oneway", "bridge", "tunnel", "maxspeed", "length_m"],
        read_geometry=False,
    ).reset_index(drop=True)
    arcs = pyogrio.read_dataframe(
        ROADS_GPKG, layer="directed_road_arcs",
        columns=["osmid", "from_node", "to_node", "direction"], read_geometry=False,
    ).reset_index(drop=True)
    nodes_info = pyogrio.read_info(ROADS_GPKG, layer="road_nodes")
    if len(segments) != 566_307 or len(arcs) != 1_071_656:
        raise ValueError(f"Unexpected source graph counts: segments={len(segments)}, arcs={len(arcs)}")

    edge_index_path = IMPACT_ROOT / "road_edge_grid_index.parquet"
    edge_index = pq.read_table(edge_index_path).to_pandas()
    required = {"edge_feature_index", "source_osmid", "node_a", "node_b", "highway", "bridge", "tunnel", "length_m", "grid_cell_id"}
    if not required.issubset(edge_index.columns):
        raise ValueError(f"A07 road edge index is missing columns: {sorted(required - set(edge_index.columns))}")
    if len(edge_index) != 405_601:
        raise ValueError(f"Unexpected A07 edge index count: {len(edge_index)}")
    segment_ids = edge_index.edge_feature_index.to_numpy(np.int64)
    if np.any(segment_ids < 0) or np.any(segment_ids >= len(segments)) or len(np.unique(segment_ids)) != len(segment_ids):
        raise ValueError("A07 edge_feature_index is outside or duplicates the static road segment rows")
    segment_by_id = segments.iloc[segment_ids]
    for a07_name, source_name in (("source_osmid", "osmid"), ("node_a", "node_a"), ("node_b", "node_b")):
        if not np.array_equal(edge_index[a07_name].to_numpy(), segment_by_id[source_name].to_numpy()):
            raise ValueError(f"A07 edge index row identity differs from source road_segments: {a07_name}")
    feature_to_cell = np.full(len(segments), -1, dtype=np.int32)
    feature_to_cell[segment_ids] = edge_index.grid_cell_id.to_numpy(np.int32)
    if np.any(edge_index.grid_cell_id.to_numpy() < 0) or np.any(edge_index.grid_cell_id.to_numpy() >= GRID_CELL_COUNT):
        raise ValueError("A07 edge grid ids are outside the expected 88x69 row-major grid")

    keys = [_key(r.osmid, r.node_a, r.node_b) for r in segments.itertuples(index=False)]
    counts = Counter(k for k in keys if k is not None)
    unique_key_to_id = {k: i for i, k in enumerate(keys) if k is not None and counts[k] == 1}
    ambiguous_keys = {k for k, count in counts.items() if count > 1}
    arc_feature = np.full(len(arcs), -1, dtype=np.int64)
    for i, row in enumerate(arcs.itertuples(index=False)):
        k = _key(row.osmid, row.from_node, row.to_node)
        if k is not None:
            arc_feature[i] = unique_key_to_id.get(k, -1)

    highway = segments.highway.fillna("unknown").astype(str).to_numpy()
    bridge = segments.bridge.to_numpy()
    tunnel = segments.tunnel.to_numpy()
    structure = np.asarray([edge_structure(b, t) for b, t in zip(bridge, tunnel, strict=True)], dtype=object)
    maxspeed = segments.maxspeed.to_numpy()
    speed_pairs = [parse_speed_kmh(raw, cls) for raw, cls in zip(maxspeed, highway, strict=True)]
    base_speed = np.asarray([x[0] for x in speed_pairs], dtype=np.float32)
    speed_source = np.asarray([x[1] for x in speed_pairs], dtype=object)
    seg_count = len(segments)
    segments_out = pd.DataFrame({
        "edge_feature_index": np.arange(seg_count, dtype=np.int32),
        "source_osmid": segments.osmid,
        "node_a": segments.node_a,
        "node_b": segments.node_b,
        "highway": highway,
        "oneway": segments.oneway.fillna("").astype(str),
        "bridge": segments.bridge.fillna("").astype(str),
        "tunnel": segments.tunnel.fillna("").astype(str),
        "structure_class": structure,
        "maxspeed_osm": segments.maxspeed.fillna("").astype(str),
        "base_speed_kmh": base_speed,
        "base_speed_source": speed_source,
        "length_m": pd.to_numeric(segments.length_m, errors="coerce").astype(np.float64),
        "grid_cell_id": feature_to_cell,
        "depth_assessment": np.where(feature_to_cell >= 0, "A07_COARSE_CELL_SAMPLE", "NO_A07_ELIGIBLE_CELL"),
    })
    arc_grid = np.full(len(arcs), -1, dtype=np.int32)
    arc_structure = np.full(len(arcs), "unassessed", dtype=object)
    arc_highway = np.full(len(arcs), "unknown", dtype=object)
    arc_length = np.full(len(arcs), np.nan, dtype=np.float64)
    arc_speed = np.full(len(arcs), np.nan, dtype=np.float32)
    arc_speed_source = np.full(len(arcs), "UNASSESSED", dtype=object)
    assessment = np.full(len(arcs), "AMBIGUOUS_OR_UNMATCHED_SEGMENT_KEY", dtype=object)
    valid_arc = arc_feature >= 0
    idx = arc_feature[valid_arc]
    arc_grid[valid_arc] = feature_to_cell[idx]
    arc_structure[valid_arc] = structure[idx]
    arc_highway[valid_arc] = highway[idx]
    arc_length[valid_arc] = pd.to_numeric(segments.length_m.iloc[idx], errors="coerce").to_numpy(np.float64)
    arc_speed[valid_arc] = base_speed[idx]
    arc_speed_source[valid_arc] = speed_source[idx]
    assessment[valid_arc & (arc_grid >= 0)] = "A07_CELL_ASSESSED_IF_DEPTH_VALID"
    assessment[valid_arc & (arc_grid < 0)] = "NO_A07_ELIGIBLE_CELL"
    arcs_out = pd.DataFrame({
        "arc_index": np.arange(len(arcs), dtype=np.int32),
        "source_osmid": arcs.osmid,
        "from_node": arcs.from_node,
        "to_node": arcs.to_node,
        "direction": arcs.direction,
        "edge_feature_index": arc_feature.astype(np.int32),
        "grid_cell_id": arc_grid,
        "structure_class": arc_structure,
        "highway": arc_highway,
        "length_m": arc_length,
        "base_speed_kmh": arc_speed,
        "base_speed_source": arc_speed_source,
        "assessment_status": assessment,
    })
    node_count = int(nodes_info["features"])
    mapping_stats = {
        "road_segment_count": int(len(segments)),
        "directed_arc_count": int(len(arcs)),
        "road_node_count": node_count,
        "a07_midpoint_assessed_segment_count": int(len(edge_index)),
        "segment_without_a07_cell_count": int(seg_count - len(edge_index)),
        "directed_arc_with_a07_cell_count": int((arc_grid >= 0).sum()),
        "directed_arc_without_a07_cell_count": int((arc_grid < 0).sum()),
        "ambiguous_duplicate_segment_key_count": int(sum(n - 1 for n in counts.values() if n > 1)),
        "ambiguous_or_unmatched_arc_count": int((arc_feature < 0).sum()),
        "unique_mapped_road_cells": int(np.unique(edge_index.grid_cell_id).size),
        "source_road_segment_classes": sorted(set(highway)),
        "structure_segment_counts": {k: int(v) for k, v in pd.Series(structure).value_counts().sort_index().items()},
        "directed_arc_assessment_counts": {k: int(v) for k, v in pd.Series(assessment).value_counts().sort_index().items()},
        "default_speed_segment_count": int((speed_source == "ASSUMED_HIGHWAY_DEFAULT").sum()),
        "osm_maxspeed_segment_count": int((speed_source == "OSM_MAXSPEED").sum()),
        "ambiguous_source_keys": [list(k) for k in sorted(ambiguous_keys)],
    }
    return segments_out, arcs_out, mapping_stats


def _percentile_and_mean(stack: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    valid_count = np.isfinite(stack).sum(axis=0)
    mean = np.full(stack.shape[1:], np.nan, dtype=np.float32)
    p05 = np.full_like(mean, np.nan)
    p95 = np.full_like(mean, np.nan)
    good = valid_count > 0
    if good.any():
        selected = stack[:, good]
        mean[good] = np.nanmean(selected, axis=0).astype(np.float32)
        p05[good] = np.nanpercentile(selected, 5, axis=0).astype(np.float32)
        p95[good] = np.nanpercentile(selected, 95, axis=0).astype(np.float32)
    return mean, p05, p95, valid_count


def _validate_a07_case(case_rows: pd.DataFrame, member_depth: np.ndarray, horizons: np.ndarray, label: str) -> list[str]:
    problems: list[str] = []
    if member_depth.ndim != 4 or member_depth.shape[0] != 20 or tuple(member_depth.shape[2:]) != GRID_SHAPE:
        raise ValueError(f"Unexpected A05 member array for {label}: {member_depth.shape}")
    if len(horizons) != member_depth.shape[1] or len(set(horizons.tolist())) != len(horizons):
        raise ValueError(f"Forecast horizon metadata invalid for {label}")
    if len(case_rows) != len(horizons) * 2430:
        raise ValueError(f"A07 has wrong cell/horizon row count for {label}: {len(case_rows)}")
    for hi, horizon in enumerate(horizons):
        sample = case_rows.loc[case_rows.horizon_hours == int(horizon)].sort_values("grid_cell_id")
        cells = sample.grid_cell_id.to_numpy(np.int64)
        if len(cells) != 2430 or len(np.unique(cells)) != 2430 or np.any(cells < 0) or np.any(cells >= GRID_CELL_COUNT):
            raise ValueError(f"A07 eligible cells do not match A05 for {label} horizon {horizon}")
        stack = member_depth[:, hi].reshape(20, -1)[:, cells]
        mean, p05, p95, valid_count = _percentile_and_mean(stack)
        expected = {
            "depth_mean_m": mean,
            "depth_member_p05_m": p05,
            "depth_member_p95_m": p95,
        }
        for col, calc in expected.items():
            source = sample[col].to_numpy(np.float32)
            if not np.allclose(source, calc, rtol=2e-5, atol=2e-5, equal_nan=True):
                problems.append(f"A07 {col} mismatch at {label} horizon {horizon}")
        sample_probability = sample.passability_probability.to_numpy(np.float32)
        valid = np.isfinite(stack)
        count = valid.sum(axis=0)
        pass_count = ((stack < DEFAULT_ROAD_THRESHOLD_M) & valid).sum(axis=0)
        probability = np.divide(pass_count, count, out=np.full(count.shape, np.nan), where=count > 0)
        if not np.allclose(sample_probability, probability, rtol=0, atol=1e-6, equal_nan=True):
            problems.append(f"A07 passability probability mismatch at {label} horizon {horizon}")
        if not np.array_equal(sample.depth_valid_member_count.to_numpy(np.int64), valid_count.astype(np.int64)):
            problems.append(f"A07 valid-member count mismatch at {label} horizon {horizon}")
    return problems


def _summarize_states(states: np.ndarray, arc_counts_by_cell: np.ndarray) -> dict[str, int]:
    counts = {
        STATE_NAMES[code].lower(): int(np.sum(arc_counts_by_cell[states == code], dtype=np.int64))
        for code in STATE_NAMES
    }
    return counts


def build(output: Path = OUTPUT) -> dict[str, object]:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing A08 output: {output}")
    partial = output.with_name(output.name + ".partial")
    if partial.exists():
        raise FileExistsError(f"Refusing to reuse partial A08 output: {partial}")
    required_inputs = [
        FORECAST_ROOT / "forecast_summary.json",
        IMPACT_ROOT / "run_summary.json",
        IMPACT_ROOT / "cell_impact.parquet",
        IMPACT_ROOT / "road_edge_grid_index.parquet",
        ROADS_GPKG,
    ]
    for path in required_inputs:
        if not path.is_file():
            raise FileNotFoundError(f"Required A08 input missing: {path.relative_to(ROOT)}")
    impact_summary = json.loads((IMPACT_ROOT / "run_summary.json").read_text(encoding="utf-8"))
    expected_hashes = impact_summary.get("input_sha256", {})
    for rel, expected in expected_hashes.items():
        source = ROOT / Path(rel.replace("\\", "/"))
        if not source.is_file() or sha256(source) != expected:
            raise ValueError(f"A07 recorded input hash no longer matches: {rel}")

    partial.mkdir(parents=True)
    segments, arcs, graph_stats = build_static_graph()
    pq.write_table(pa.Table.from_pandas(segments, preserve_index=False), partial / "static_segments.parquet", compression="zstd")
    pq.write_table(pa.Table.from_pandas(arcs, preserve_index=False), partial / "directed_arcs.parquet", compression="zstd")
    arc_cell_counts: dict[str, np.ndarray] = {}
    for cls in ("ordinary", "tunnel_underpass_proxy", "bridge", "bridge_and_tunnel"):
        subset = arcs.loc[(arcs.grid_cell_id >= 0) & (arcs.structure_class == cls), "grid_cell_id"].to_numpy(np.int64)
        arc_cell_counts[cls] = np.bincount(subset, minlength=GRID_CELL_COUNT).astype(np.int64)

    impact_cells = pq.read_table(
        IMPACT_ROOT / "cell_impact.parquet",
        columns=["event_key", "scenario_key", "valid_at_utc", "horizon_hours", "grid_cell_id", "threshold_m",
                 "passability_probability", "depth_mean_m", "depth_member_p05_m", "depth_member_p95_m", "depth_valid_member_count"],
    ).to_pandas()
    impact_cells = impact_cells[np.isclose(impact_cells.threshold_m.to_numpy(np.float32), DEFAULT_ROAD_THRESHOLD_M)]
    case_groups = impact_cells.groupby(["event_key", "scenario_key"], sort=True)
    archive_index_rows: list[dict[str, object]] = []
    case_reports: list[dict[str, object]] = []
    all_problems: list[str] = []
    case_count = 0
    for (event_key, scenario_key), rows in case_groups:
        case_count += 1
        source_npz = FORECAST_ROOT / event_key / scenario_key / "depth_members_by_horizon_DERIVED.npz"
        if not source_npz.is_file():
            raise FileNotFoundError(f"A05 member-depth archive missing: {source_npz.relative_to(ROOT)}")
        with np.load(source_npz, allow_pickle=False) as z:
            member_depth = z["depth_m"].astype(np.float32, copy=False)
            horizons = z["horizons_hours"].astype(np.int16, copy=False)
            member_ids = z["member_ids"].astype(np.int16, copy=False)
            seed = int(z["seed"])
            if member_ids.tolist() != list(range(1, 21)):
                raise ValueError(f"Unexpected member IDs for {event_key}/{scenario_key}: {member_ids.tolist()}")
            case_rows = rows.reset_index(drop=True)
            problems = _validate_a07_case(case_rows, member_depth, horizons, f"{event_key}/{scenario_key}")
            all_problems.extend(problems)
            if problems:
                raise ValueError("A07/A05 input consistency check failed: " + "; ".join(problems))

            grid_cells = np.sort(rows.grid_cell_id.unique().astype(np.int32))
            road_grid_cells = np.sort(segments.loc[segments.grid_cell_id >= 0, "grid_cell_id"].unique().astype(np.int32))
            if not np.isin(road_grid_cells, grid_cells).all():
                raise ValueError("Road overlay grid cells are not present in the A07 eligible cell table")
            case_horizons = np.sort(rows.horizon_hours.unique().astype(np.int16))
            valid_at_by_horizon = {}
            for h in case_horizons:
                ts = rows.loc[rows.horizon_hours == int(h), "valid_at_utc"].unique()
                if len(ts) != 1:
                    raise ValueError(f"A07 has inconsistent valid_at_utc for {event_key}/{scenario_key}/{h}")
                valid_at_by_horizon[int(h)] = str(ts[0])
            if case_horizons.tolist() != horizons.tolist():
                raise ValueError(f"A07/A05 horizon mismatch for {event_key}/{scenario_key}")

            cell_n = len(road_grid_cells)
            depth_snapshot = np.full((len(member_ids), len(horizons), cell_n), np.nan, dtype=np.float32)
            valid_snapshot = np.zeros((len(member_ids), len(horizons), cell_n), dtype=np.bool_)
            road_state = np.full((len(member_ids), len(horizons), cell_n), STATE_UNKNOWN, dtype=np.uint8)
            road_speed = np.full((len(member_ids), len(horizons), cell_n), np.nan, dtype=np.float32)
            tunnel_state = np.full_like(road_state, STATE_UNKNOWN)
            tunnel_speed = np.full_like(road_speed, np.nan)
            bridge_state = np.full_like(road_state, STATE_STRUCTURE_UNASSESSED)
            bridge_speed = np.full_like(road_speed, np.nan)
            previous_states: dict[str, np.ndarray | None] = {"ordinary": None, "tunnel_underpass_proxy": None, "bridge": None, "bridge_and_tunnel": None}
            for hi, horizon in enumerate(horizons):
                depth_grid = member_depth[:, hi].reshape(len(member_ids), -1)
                sampled = depth_grid[:, road_grid_cells]
                depth_snapshot[:, hi] = sampled
                valid_snapshot[:, hi] = np.isfinite(sampled)
                road_state[:, hi], road_speed[:, hi] = depth_state(sampled, DEFAULT_ROAD_THRESHOLD_M)
                tunnel_state[:, hi], tunnel_speed[:, hi] = depth_state(sampled, TUNNEL_THRESHOLD_M)
                bridge_state[:, hi] = STATE_STRUCTURE_UNASSESSED
                bridge_speed[:, hi] = np.nan
                # In this bundle, states are cell-keyed and static arc rows map each arc to its cell/class.
                # Aggregate transition counts by mapped directed arcs, not by cell count alone.
                category_state = {
                    "ordinary": road_state[:, hi],
                    "tunnel_underpass_proxy": tunnel_state[:, hi],
                    "bridge": bridge_state[:, hi],
                    "bridge_and_tunnel": bridge_state[:, hi],
                }
                for mi, member_id in enumerate(member_ids):
                    summary = {
                        "event_key": event_key,
                        "scenario_key": scenario_key,
                        "valid_at_utc": valid_at_by_horizon[int(horizon)],
                        "horizon_hours": int(horizon),
                        "member_id": int(member_id),
                        "archive": f"{event_key}_{scenario_key}_snapshots.npz",
                        "member_index": mi,
                        "horizon_index": hi,
                        "grid_cell_count": cell_n,
                        "depth_valid_cell_count": int(np.isfinite(sampled[mi]).sum()),
                        "depth_nodata_cell_count": int((~np.isfinite(sampled[mi])).sum()),
                        "unassessed_directed_arc_count": int(graph_stats["directed_arc_without_a07_cell_count"]),
                        "graph_node_count": graph_stats["road_node_count"],
                        "graph_directed_arc_count": graph_stats["directed_arc_count"],
                    }
                    transition_total = 0
                    for cls, state_by_member in category_state.items():
                        arc_weights = arc_cell_counts[cls][road_grid_cells]
                        state_vec = state_by_member[mi]
                        status_counts = _summarize_states(state_vec, arc_weights)
                        for name, count in status_counts.items():
                            summary[f"{cls}_{name}_arcs"] = count
                        transition_total += state_transition_count(previous_states[cls][mi] if previous_states[cls] is not None else None, state_vec, arc_weights)
                    summary["state_changed_directed_arc_count_from_previous_horizon"] = transition_total
                    summary["transition_comparison"] = "NO_PREVIOUS_HORIZON" if hi == 0 else "CELL_STATE_CHANGE_WEIGHTED_BY_MAPPED_DIRECTED_ARCS"
                    archive_index_rows.append(summary)
                for cls, states in category_state.items():
                    if previous_states[cls] is None:
                        previous_states[cls] = states.copy()
                    else:
                        previous_states[cls] = states.copy()

            case_archive = partial / f"{event_key}_{scenario_key}_snapshots.npz"
            np.savez_compressed(
                case_archive,
                schema_version=np.asarray("A08-cell-overlay-v1"),
                event_key=np.asarray(event_key), scenario_key=np.asarray(scenario_key),
                member_ids=member_ids, horizons_hours=horizons,
                valid_at_utc=np.asarray([valid_at_by_horizon[int(h)] for h in horizons], dtype="U32"),
                grid_cell_ids=road_grid_cells,
                depth_m=depth_snapshot, depth_valid=valid_snapshot,
                ordinary_state=road_state, ordinary_speed_multiplier=road_speed,
                tunnel_state=tunnel_state, tunnel_speed_multiplier=tunnel_speed,
                bridge_state=bridge_state, bridge_speed_multiplier=bridge_speed,
                state_codes=np.asarray([json.dumps(STATE_NAMES, sort_keys=True)]),
                parameters_json=np.asarray([json.dumps({
                    "ordinary_block_threshold_m": DEFAULT_ROAD_THRESHOLD_M,
                    "tunnel_underpass_proxy_block_threshold_m": TUNNEL_THRESHOLD_M,
                    "speed_factor_rule": "max(0.2, 1 - 0.8 * depth_m / threshold_m) below threshold; blocked edges have factor 0",
                    "bridge_handling": "UNASSESSED_STRUCTURE: bridge deck elevation/depth unavailable",
                    "nodata_handling": "UNKNOWN_NODATA; speed multiplier NaN; never treated as dry/open",
                    "threshold_sensitivity_m": list(SENSITIVITY_THRESHOLDS_M),
                }, sort_keys=True)]),
                a06_member_seed=np.asarray(seed, dtype=np.int64),
            )
            case_reports.append({
                "event_key": event_key, "scenario_key": scenario_key,
                "member_count": int(len(member_ids)), "horizon_count": int(len(horizons)),
                "horizons_hours": horizons.astype(int).tolist(),
                "valid_at_utc": [valid_at_by_horizon[int(h)] for h in horizons],
                "archive": case_archive.name,
                "archive_sha256": sha256(case_archive),
                "archive_bytes": case_archive.stat().st_size,
                "snapshot_count": int(len(member_ids) * len(horizons)),
                "forecast_archive": str(source_npz.relative_to(ROOT)).replace("\\", "/"),
                "forecast_archive_sha256": sha256(source_npz),
                "member_seed": seed,
            })
    if case_count != 15 or len(archive_index_rows) != 1500:
        raise ValueError(f"Unexpected snapshot count: cases={case_count}, snapshots={len(archive_index_rows)}")
    pq.write_table(pa.Table.from_pandas(pd.DataFrame(archive_index_rows), preserve_index=False), partial / "snapshot_index.parquet", compression="zstd")
    (partial / "run_summary.json").write_text(json.dumps({
        "task": "A08 time-dependent flood-aware road graph overlay",
        "status": "SIMULATED_RESEARCH_OUTPUT_NOT_LIVE_OR_OPERATIONAL",
        "generated_at_utc": pd.Timestamp.now(tz="UTC").isoformat().replace("+00:00", "Z"),
        "graph_crs": GRAPH_CRS,
        "grid": {"shape": list(GRID_SHAPE), "cell_size_m": 600, "road_sample": "A07 road-segment midpoint on model grid"},
        "graph_counts": graph_stats,
        "snapshot_case_count": case_count,
        "snapshot_count": len(archive_index_rows),
        "snapshot_index": "snapshot_index.parquet",
        "snapshot_files": case_reports,
        "assumptions": {
            "ordinary_edge_block_threshold_m": DEFAULT_ROAD_THRESHOLD_M,
            "tunnel_and_underpass_block_threshold_m": TUNNEL_THRESHOLD_M,
            "underpass_first": "Assumption: any tunnel-tagged segment is treated as an underpass proxy; graph has no verified underpass or invert/elevation field.",
            "bridge": "Bridge edges remain unassessed because A07 cell depth is not bridge-deck depth and no deck elevation is available.",
            "speed_factor": "Assumption: max(0.2, 1 - 0.8 * depth_m / threshold_m) below threshold; blocked factor is zero.",
            "base_speed": "OSM maxspeed parsed where a single numeric token is available; otherwise class defaults in implementation are assumptions, not calibrated travel speeds.",
            "no_data": "NoData is unknown, not dry/open; missing A07 cell assignment, ambiguous segment joins and missing depth remain separately counted as unassessed.",
            "threshold_sensitivity_m": list(SENSITIVITY_THRESHOLDS_M),
        },
        "limits": [
            "All time states derive from A05/A06 simulated hindcast ensembles, not observed depth or live forecasts.",
            "Road depth is a 600 m cell midpoint proxy and can miss local roadway flooding, structure deck elevation, underpasses, drainage and sub-cell variation.",
            "No route is calculated or certified safe; this output is not operational guidance or validated hydraulic truth.",
            "A07 descriptive member spread is not calibrated uncertainty coverage.",
        ],
        "input_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): sha256(p) for p in required_inputs},
        "a07_input_sha256_verified": expected_hashes,
    }, indent=2) + "\n", encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    partial.rename(output)
    return json.loads((output / "run_summary.json").read_text(encoding="utf-8"))


def validate_output(output: Path = OUTPUT) -> dict[str, int]:
    """Read-only validation of graph topology, snapshot states, transitions and coverage."""
    output = output.resolve()
    summary = json.loads((output / "run_summary.json").read_text(encoding="utf-8"))
    segments = pq.read_table(output / "static_segments.parquet").to_pandas()
    arcs = pq.read_table(output / "directed_arcs.parquet").to_pandas()
    index = pq.read_table(output / "snapshot_index.parquet").to_pandas()
    if len(segments) != 566_307 or len(arcs) != 1_071_656 or len(index) != 1_500:
        raise ValueError(f"Graph/snapshot count mismatch: segments={len(segments)}, arcs={len(arcs)}, snapshots={len(index)}")
    key_cols = ["event_key", "scenario_key", "horizon_hours", "member_id"]
    if index.duplicated(key_cols).any() or index["member_id"].nunique() != 20 or index["horizon_hours"].nunique() != 5:
        raise ValueError("Snapshot index is not a unique 15 x 5 x 20 event/scenario/time/member lattice")
    expected_snapshots = int(summary["snapshot_case_count"] * 5 * 20)
    if len(index) != expected_snapshots:
        raise ValueError(f"Summary/index snapshot counts differ: {expected_snapshots} versus {len(index)}")
    state_field = {
        "ordinary": "ordinary_state",
        "tunnel_underpass_proxy": "tunnel_state",
        "bridge": "bridge_state",
        "bridge_and_tunnel": "bridge_state",
    }
    speed_field = {
        "ordinary": "ordinary_speed_multiplier",
        "tunnel_underpass_proxy": "tunnel_speed_multiplier",
        "bridge": "bridge_speed_multiplier",
        "bridge_and_tunnel": "bridge_speed_multiplier",
    }
    arc_weights = {}
    for cls in state_field:
        cell_ids_for_arcs = arcs.loc[(arcs.grid_cell_id >= 0) & (arcs.structure_class == cls), "grid_cell_id"].to_numpy(np.int32)
        arc_weights[cls] = np.bincount(cell_ids_for_arcs, minlength=GRID_CELL_COUNT).astype(np.int64)
    row_lookup = index.set_index(key_cols)
    checked = 0
    missing_values = 0
    state_transitions = 0
    for case in summary["snapshot_files"]:
        archive = output / case["archive"]
        if sha256(archive) != case["archive_sha256"]:
            raise ValueError(f"Snapshot archive hash mismatch: {archive.name}")
        with np.load(archive, allow_pickle=False) as z:
            members = z["member_ids"].astype(int)
            horizons = z["horizons_hours"].astype(int)
            cells = z["grid_cell_ids"].astype(np.int32)
            depths = z["depth_m"]
            valid = z["depth_valid"]
            if depths.shape != (20, 5, len(cells)) or valid.shape != depths.shape or len(cells) != 2400:
                raise ValueError(f"Snapshot array shape mismatch: {archive.name}")
            if not np.array_equal(valid, np.isfinite(depths)):
                raise ValueError(f"Depth validity mask differs from NoData values: {archive.name}")
            if np.any(cells[1:] <= cells[:-1]):
                raise ValueError(f"Snapshot cell IDs are not unique sorted values: {archive.name}")
            previous = {cls: None for cls in state_field}
            case_index = index[(index.event_key == case["event_key"]) & (index.scenario_key == case["scenario_key"])]
            if len(case_index) != len(members) * len(horizons):
                raise ValueError(f"Snapshot index rows missing for {archive.name}")
            for hi, horizon in enumerate(horizons):
                arrays_by_class = {}
                for cls, field in state_field.items():
                    state_arr = z[field][...,] if cls in {"bridge", "bridge_and_tunnel"} else z[field]
                    state = state_arr[:, hi, :]
                    arrays_by_class[cls] = state
                    if cls == "ordinary":
                        expected, factor = depth_state(depths[:, hi, :], DEFAULT_ROAD_THRESHOLD_M)
                    elif cls == "tunnel_underpass_proxy":
                        expected, factor = depth_state(depths[:, hi, :], TUNNEL_THRESHOLD_M)
                    else:
                        expected = np.full(state.shape, STATE_STRUCTURE_UNASSESSED, dtype=np.uint8)
                        factor = np.full(state.shape, np.nan, dtype=np.float32)
                    if not np.array_equal(state, expected):
                        raise ValueError(f"Stored state disagrees with depth/structure rules: {archive.name}/{cls}/{horizon}")
                    if not np.allclose(z[speed_field[cls]][:, hi, :], factor, equal_nan=True, rtol=1e-6, atol=1e-6):
                        raise ValueError(f"Stored speed multiplier disagrees with rule: {archive.name}/{cls}/{horizon}")
                for mi, member in enumerate(members):
                    key = (case["event_key"], case["scenario_key"], int(horizon), int(member))
                    if key not in row_lookup.index:
                        raise ValueError(f"Snapshot index row missing: {key}")
                    row = row_lookup.loc[key]
                    expected_valid = int(valid[mi, hi].sum())
                    if int(row.depth_valid_cell_count) != expected_valid or int(row.depth_nodata_cell_count) != len(cells) - expected_valid:
                        raise ValueError(f"NoData coverage counts disagree: {key}")
                    if int(row.unassessed_directed_arc_count) != int(summary["graph_counts"]["directed_arc_without_a07_cell_count"]):
                        raise ValueError(f"Unmapped graph coverage count differs: {key}")
                    changed = 0
                    for cls, states in arrays_by_class.items():
                        weights = arc_weights[cls][cells]
                        state_vec = states[mi]
                        counts = _summarize_states(state_vec, weights)
                        for status, count in counts.items():
                            column = f"{cls}_{status}_arcs"
                            if int(row[column]) != count:
                                raise ValueError(f"Snapshot graph state count differs: {key}/{column}")
                        prev = previous[cls][mi] if previous[cls] is not None else None
                        changed += state_transition_count(prev, state_vec, weights)
                    if int(row.state_changed_directed_arc_count_from_previous_horizon) != changed:
                        raise ValueError(f"State transition count differs: {key}")
                    if hi == 0 and row.transition_comparison != "NO_PREVIOUS_HORIZON":
                        raise ValueError(f"First horizon must be explicitly marked no prior time: {key}")
                    checked += 1
                    missing_values += int(row.depth_nodata_cell_count)
                    state_transitions += changed
                for cls in previous:
                    previous[cls] = arrays_by_class[cls].copy()
    if checked != expected_snapshots:
        raise ValueError(f"Not all snapshots validated: {checked}/{expected_snapshots}")
    return {
        "road_segments": len(segments), "directed_arcs": len(arcs), "snapshots_validated": checked,
        "missing_depth_cells_across_snapshots": missing_values,
        "transition_edge_changes_across_noninitial_snapshots": state_transitions,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--verify-only", action="store_true", help="Validate an existing output directory without modifying it")
    args = parser.parse_args()
    if args.verify_only:
        print(json.dumps(validate_output(args.output), indent=2))
        return
    summary = build(args.output)
    print(json.dumps({
        "status": summary["status"], "snapshot_count": summary["snapshot_count"],
        "graph_counts": summary["graph_counts"], "output": str(args.output.resolve()),
    }, indent=2))


if __name__ == "__main__":
    main()
