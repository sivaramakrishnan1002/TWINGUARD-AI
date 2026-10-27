"""A09 simulated routing comparison on A08 snapshots (not operational guidance)."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components, dijkstra

ROOT = Path(__file__).resolve().parents[2]
GRAPH_DIR = ROOT / "data/features/routing/time_dependent_batch2"
ROAD_GPKG = ROOT / "data/features/roads/chennai_road_graph.gpkg"
OUT = ROOT / "data/features/routing/results/batch2_v1/revision_3"
DOC = ROOT / "docs/ROUTING_BATCH2.md"
SEED = 20261027
TRUTH_MEMBER_ID = 20
ACCESSIBILITY_MINIMUM = 0.80
METHODS = ("static", "current_flood_aware", "horizon_aware", "uncertainty_aware")
HORIZONS = (6, 24, 72)
EVENTS = ("2015-12-02", "2021-11-13", "2023-12-04")
SCENARIO = "perfect_foresight_imerg"
STATE_UNKNOWN, STATE_OPEN, STATE_REDUCED, STATE_BLOCKED, STATE_UNASSESSED = range(5)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def current_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                              capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def dijkstra_path(predecessor: np.ndarray, source: int, target: int) -> list[int] | None:
    """Reconstruct a node-index path from scipy's predecessor row."""
    if source == target:
        return [int(source)]
    if int(predecessor[target]) < 0:
        return None
    out = [int(target)]
    current = int(target)
    for _ in range(len(predecessor)):
        current = int(predecessor[current])
        if current < 0:
            return None
        out.append(current)
        if current == source:
            out.reverse()
            return out
    raise ValueError("predecessor cycle while reconstructing route")


def classify_route_states(states: np.ndarray) -> tuple[bool | None, float | None]:
    """Return (route_failed, passability_probability); unknown stays null."""
    a = np.asarray(states)
    if a.ndim != 1 or a.size == 0 or np.any((a == STATE_UNKNOWN) | (a == STATE_UNASSESSED)):
        return None, None
    failed = a == STATE_BLOCKED
    return bool(np.any(failed)), float(not np.any(failed))


def make_route_weights(
    states: np.ndarray, speed: np.ndarray, base_time: np.ndarray, *,
    failure_limit: float | None = None,
) -> np.ndarray:
    """Expected-time weights over forecast members; unknown edges are excluded."""
    states = np.asarray(states)
    speed = np.asarray(speed, dtype=np.float64)
    if states.ndim != 2 or speed.shape != states.shape:
        raise ValueError("states and speed must be member-by-arc arrays of equal shape")
    known = (states == STATE_OPEN) | (states == STATE_REDUCED) | (states == STATE_BLOCKED)
    p_block = np.divide((states == STATE_BLOCKED).sum(axis=0), known.sum(axis=0),
                        out=np.full(states.shape[1], np.nan), where=known.sum(axis=0) > 0)
    passable = (states == STATE_OPEN) | (states == STATE_REDUCED)
    # A blocked member contributes a large, explicit delay penalty. It is not treated as open.
    member_cost = np.where(passable, base_time[None, :] / np.maximum(speed, 1e-6),
                           np.where(states == STATE_BLOCKED, base_time[None, :] * 20.0, np.nan))
    finite_cost = np.isfinite(member_cost)
    cost_count = finite_cost.sum(axis=0)
    weights = np.divide(np.where(finite_cost, member_cost, 0.0).sum(axis=0), cost_count,
                        out=np.full(states.shape[1], np.inf), where=cost_count > 0)
    weights[~np.all(known, axis=0)] = np.inf
    if failure_limit is not None:
        weights[(~np.isfinite(p_block)) | (p_block > failure_limit)] = np.inf
    return weights


class RoutingInputs:
    def __init__(self) -> None:
        self.arcs = pq.read_table(GRAPH_DIR / "directed_arcs.parquet").to_pandas()
        self.snapshot_index = pq.read_table(GRAPH_DIR / "snapshot_index.parquet").to_pandas()
        self.summary = json.loads((GRAPH_DIR / "run_summary.json").read_text(encoding="utf-8"))
        self.node_ids = np.unique(np.concatenate((self.arcs.from_node.to_numpy(np.int64),
                                                   self.arcs.to_node.to_numpy(np.int64))))
        node_pos = {int(n): i for i, n in enumerate(self.node_ids)}
        self.src = self.arcs.from_node.map(node_pos).to_numpy(np.int32)
        self.dst = self.arcs.to_node.map(node_pos).to_numpy(np.int32)
        self.arc_count = len(self.arcs)
        base_speed = self.arcs.base_speed_kmh.to_numpy(np.float64)
        self.base_time = self.arcs.length_m.to_numpy(np.float64) / np.maximum(base_speed / 3.6, 1e-4)
        # Collapse parallel directed arcs by ordered node pair, keeping the cheapest arc dynamically.
        order = np.lexsort((self.dst, self.src))
        ordered_codes = self.src[order].astype(np.int64) * len(self.node_ids) + self.dst[order]
        starts = np.r_[0, np.flatnonzero(ordered_codes[1:] != ordered_codes[:-1]) + 1]
        self.order = order
        self.group_starts = starts
        self.group_codes = ordered_codes[starts]
        self.group_src = self.src[order[starts]]
        self.group_dst = self.dst[order[starts]]
        self.graph_shape = (len(self.node_ids), len(self.node_ids))
        self.static_arc_weight = self.base_time
        self.static_group_weight = self._reduce_min(self.static_arc_weight)
        self.static_graph = self._csr(self.static_group_weight)
        ncomp, labels = connected_components(self.static_graph, directed=True, connection="strong")
        sizes = np.bincount(labels, minlength=ncomp)
        self.largest_component = int(np.argmax(sizes))
        self.component_labels = labels
        self.largest_component_nodes = np.flatnonzero(labels == self.largest_component)
        self.node_id_to_pos = node_pos
        self.grid_cell_to_pos: dict[int, int] = {}
        self._archives: dict[tuple[str, str], dict[str, np.ndarray]] = {}

    def _reduce_min(self, arc_weights: np.ndarray) -> np.ndarray:
        # Each (from,to) group has at least one arc. Group order is CSR row-major.
        return np.minimum.reduceat(arc_weights[self.order], self.group_starts)

    def _csr(self, group_weights: np.ndarray) -> csr_matrix:
        return csr_matrix((group_weights, (self.group_src, self.group_dst)), shape=self.graph_shape)

    def archive(self, event: str, scenario: str = SCENARIO) -> dict[str, np.ndarray]:
        key = (event, scenario)
        if key not in self._archives:
            filename = f"{event}_{scenario}_snapshots.npz"
            with np.load(GRAPH_DIR / filename, allow_pickle=False) as z:
                self._archives[key] = {k: z[k] for k in z.files}
            if self._archives[key]["schema_version"].item() != "A08-cell-overlay-v1":
                raise ValueError(f"unexpected A08 schema in {filename}")
            cells = self._archives[key]["grid_cell_ids"]
            self.grid_cell_to_pos = {int(c): i for i, c in enumerate(cells)}
        return self._archives[key]

    def edge_arrays(self, event: str, horizon: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        a = self.archive(event)
        hi = list(map(int, a["horizons_hours"])).index(horizon)
        nmember = len(a["member_ids"])
        states = np.full((nmember, self.arc_count), STATE_UNKNOWN, dtype=np.uint8)
        speeds = np.full((nmember, self.arc_count), np.nan, dtype=np.float32)
        depth = np.full((nmember, self.arc_count), np.nan, dtype=np.float32)
        cell_positions = np.fromiter((self.grid_cell_to_pos.get(int(c), -1)
                                      for c in self.arcs.grid_cell_id.to_numpy()),
                                     dtype=np.int32, count=self.arc_count)
        mapped = cell_positions >= 0
        classes = self.arcs.structure_class.astype(str).to_numpy()
        for cls, state_key, speed_key in (
            ("ordinary", "ordinary_state", "ordinary_speed_multiplier"),
            ("tunnel_underpass_proxy", "tunnel_state", "tunnel_speed_multiplier"),
            ("bridge", "bridge_state", "bridge_speed_multiplier"),
            ("bridge_and_tunnel", "bridge_state", "bridge_speed_multiplier"),
        ):
            ix = mapped & (classes == cls)
            if ix.any():
                states[:, ix] = a[state_key][:, hi, cell_positions[ix]]
                speeds[:, ix] = a[speed_key][:, hi, cell_positions[ix]]
                depth[:, ix] = a["depth_m"][:, hi, cell_positions[ix]]
        return states, speeds, depth

    def find_paths(self, weights: np.ndarray, pairs: list[tuple[int, int]]) -> list[list[int] | None]:
        graph = self._csr(self._reduce_min(weights))
        origins = np.array([s for s, _ in pairs], dtype=np.int32)
        _, predecessors = dijkstra(graph, directed=True, indices=origins,
                                   return_predecessors=True)
        if predecessors.ndim == 1:
            predecessors = predecessors[None, :]
        return [dijkstra_path(predecessors[i], source, target)
                for i, (source, target) in enumerate(pairs)]

    def arc_path(self, node_path: list[int]) -> list[int]:
        out: list[int] = []
        for u, v in zip(node_path[:-1], node_path[1:]):
            code = int(u) * len(self.node_ids) + int(v)
            gi = int(np.searchsorted(self.group_codes, code))
            if gi >= len(self.group_codes) or self.group_codes[gi] != code:
                raise ValueError("shortest path references a missing directed arc")
            start = int(self.group_starts[gi])
            end = int(self.group_starts[gi + 1]) if gi + 1 < len(self.group_starts) else len(self.order)
            out.append(int(self.order[start:end][0]))
        return out


def choose_pairs(inp: RoutingInputs) -> tuple[list[tuple[int, int]], dict]:
    """Choose reproducible node pairs inside the largest directed SCC."""
    rng = np.random.default_rng(SEED)
    candidates = inp.largest_component_nodes
    if len(candidates) < 20:
        raise ValueError("largest strongly connected component too small for OSSE route sample")
    chosen: list[tuple[int, int]] = []
    attempts = 0
    while len(chosen) < 6 and attempts < 40:
        s, t = rng.choice(candidates, size=2, replace=False)
        pair = (int(s), int(t))
        if pair not in chosen:
            chosen.append(pair)
        attempts += 1
    return chosen, {"selection": "6 deterministic directed-road-node OD pairs sampled within largest static SCC",
                    "seed": SEED, "largest_scc_node_count": int(len(candidates)),
                    "largest_scc_share": float(len(candidates) / len(inp.node_ids)),
                    "pairs": [{"origin_node": int(inp.node_ids[s]), "destination_node": int(inp.node_ids[t])}
                              for s, t in chosen]}


def _truth_and_forecast(states: np.ndarray, truth_index: int) -> tuple[np.ndarray, np.ndarray]:
    forecast_indices = np.array([i for i in range(states.shape[0]) if i != truth_index], dtype=np.int32)
    return states[forecast_indices], states[truth_index]


def _path_summary(inp: RoutingInputs, arc_ids: list[int], states: np.ndarray, speed: np.ndarray,
                  depths: np.ndarray, *, forecast_ids: np.ndarray, truth_index: int,
                  horizon_idx: int) -> dict:
    if not arc_ids:
        return {"coverage": {"route_edge_count": 0, "assessed_edge_count": 0,
                             "unassessed_edge_count": 0, "fraction_assessed": None},
                "forecast_accessibility_probability": None, "forecast_failure_probability": None,
                "truth_failed": None,
                "expected_time_seconds": None, "expected_exposure_depth_distance_m2": None,
                "truth_exposure_depth_distance_m2": None, "edges": []}
    route_states = states[:, arc_ids]
    forecast = route_states[forecast_ids]
    truth = route_states[truth_index]
    forecast_fail = []
    forecast_times = []
    forecast_exposure = []
    truth_unknown = bool(np.any((truth == STATE_UNKNOWN) | (truth == STATE_UNASSESSED)))
    truth_failed = None if truth_unknown else bool(np.any(truth == STATE_BLOCKED))
    lengths = inp.arcs.length_m.to_numpy(np.float64)[arc_ids]
    arc_base = inp.base_time[arc_ids]
    d = depths[:, arc_ids]
    for mi in range(len(forecast_ids)):
        st = forecast[mi]
        if np.any((st == STATE_UNKNOWN) | (st == STATE_UNASSESSED)):
            forecast_fail.append(None)
        else:
            forecast_fail.append(bool(np.any(st == STATE_BLOCKED)))
        if forecast_fail[-1] is None or forecast_fail[-1]:
            forecast_times.append(np.nan)
        else:
            forecast_times.append(float(np.sum(arc_base / np.maximum(speed[forecast_ids[mi], arc_ids], 1e-6))))
        dep = d[forecast_ids[mi]]
        forecast_exposure.append(float(np.sum(lengths * dep)) if np.all(np.isfinite(dep)) else np.nan)
    known_fails = [v for v in forecast_fail if v is not None]
    access_prob = None if len(known_fails) != len(forecast_ids) else float(1 - np.mean(known_fails))
    fail_prob = None if access_prob is None else float(1 - access_prob)
    known_route = all(v is not None for v in forecast_fail)
    truth_exp = float(np.sum(lengths * d[truth_index])) if np.all(np.isfinite(d[truth_index])) and not truth_unknown else None
    good_times = np.asarray(forecast_times, dtype=float)
    good_times = good_times[np.isfinite(good_times)]
    good_exp = np.asarray(forecast_exposure, dtype=float)
    good_exp = good_exp[np.isfinite(good_exp)]
    route_success_members = np.array([v is False for v in forecast_fail], dtype=bool)
    edge_records = []
    for j, arc_id in enumerate(arc_ids):
        ast, _ = classify_route_states(forecast[:, j])
        ppass = None
        if ast is not None:
            ppass = float(np.mean(forecast[:, j] != STATE_BLOCKED))
        edge_time = None
        if route_success_members.any():
            member_times = inp.base_time[arc_id]
            member_times = member_times / np.maximum(speed[forecast_ids[route_success_members], arc_id], 1e-6)
            edge_time = float(np.mean(member_times))
        edge_records.append({
            "edge_id": int(arc_id), "entry_at_utc": None, "exit_at_utc": None,
            "distance_m": float(lengths[j]), "travel_time_seconds": edge_time,
            "depth_max_m": float(np.nanmax(d[:, j])) if np.isfinite(d[:, j]).any() else None,
            "passable_probability": ppass,
            "bridge": str(inp.arcs.structure_class.iloc[arc_id]) in ("bridge", "bridge_and_tunnel"),
            "tunnel": str(inp.arcs.structure_class.iloc[arc_id]) in ("tunnel_underpass_proxy", "bridge_and_tunnel"),
            "assessment_status": "ASSESSED_SIMULATED" if ppass is not None else "UNASSESSED_OR_NODATA"
        })
    assessed_edges = sum(x["assessment_status"] == "ASSESSED_SIMULATED" for x in edge_records)
    return {
        "coverage": {"route_edge_count": len(arc_ids), "assessed_edge_count": assessed_edges,
                     "unassessed_edge_count": len(arc_ids) - assessed_edges,
                     "fraction_assessed": float(assessed_edges / len(arc_ids))},
        "forecast_accessibility_probability": None if not known_route else access_prob,
        "forecast_failure_probability": None if not known_route else fail_prob,
        "truth_failed": truth_failed,
        "expected_time_seconds": float(np.mean(good_times)) if len(good_times) else None,
        "expected_time_spread_seconds": float(np.std(good_times, ddof=1)) if len(good_times) > 1 else None,
        "expected_exposure_depth_distance_m2": float(np.mean(good_exp)) if len(good_exp) else None,
        "truth_exposure_depth_distance_m2": truth_exp,
        "edges": edge_records,
    }


def _coordinates(node_ids: list[int]) -> dict[int, list[float]]:
    import pyogrio
    from pyproj import Transformer
    frame = pyogrio.read_dataframe(ROAD_GPKG, layer="road_nodes", columns=["osmid", "geometry"])
    wanted = set(node_ids)
    transformer = Transformer.from_crs("EPSG:32644", "EPSG:4326", always_xy=True)
    coords = {}
    for row in frame.loc[frame.osmid.isin(wanted)].itertuples():
        x, y = transformer.transform(row.geometry.x, row.geometry.y)
        coords[int(row.osmid)] = [float(x), float(y)]
    return coords


def _route_geometry(node_path: list[int] | None, inp: RoutingInputs, coords: dict[int, list[float]]) -> dict | None:
    if not node_path:
        return None
    seq = [coords.get(int(inp.node_ids[p])) for p in node_path]
    if any(p is None for p in seq):
        return None
    return {"type": "LineString", "coordinates": seq}


def _route_result(inp: RoutingInputs, *, event: str, horizon: int, method: str,
                  pair_index: int, pair: tuple[int, int], path: list[int] | None,
                  graph_method: str, edge_states: np.ndarray, edge_speeds: np.ndarray,
                  edge_depths: np.ndarray, forecast_ids: np.ndarray, truth_index: int,
                  coords: dict[int, list[float]], valid_at: str, issue_at: str,
                  static_time_seconds: float | None) -> dict:
    if path is None:
        arc_ids: list[int] = []
        route_status = "NO_TOPOLOGICAL_PATH"
    else:
        arc_ids = inp.arc_path(path)
        route_status = "ROUTE_FOUND"
    summary = _path_summary(inp, arc_ids, edge_states, edge_speeds, edge_depths,
                            forecast_ids=forecast_ids, truth_index=truth_index, horizon_idx=horizon)
    coverage = summary["coverage"]
    access_prob = summary.get("forecast_accessibility_probability")
    failure_prob = summary.get("forecast_failure_probability")
    status = route_status
    if path is not None and coverage["unassessed_edge_count"]:
        status = "INSUFFICIENT_HAZARD_COVERAGE"
    elif path is not None and method == "uncertainty_aware" and (access_prob is None or access_prob < ACCESSIBILITY_MINIMUM):
        status = "BELOW_ACCESSIBILITY_CONSTRAINT"
    requested_seconds = int(horizon * 3600)
    departure = datetime.fromisoformat(valid_at.replace("Z", "+00:00"))
    travel_time = summary.get("expected_time_seconds")
    arrival = (departure + timedelta(seconds=travel_time)).isoformat().replace("+00:00", "Z") if travel_time is not None and path else None
    path_node_ids = [int(inp.node_ids[p]) for p in path] if path else []
    # C8 proposal fields plus explicit OSSE evaluation metadata. All depth exposure units are m².
    return {
        "schema_id": "twinguard.route_result", "schema_version": "0.1-draft",
        "result_id": f"A09-{event}-{horizon:02d}h-{method}-od{pair_index+1:02d}",
        "status": status, "run_id": None, "scenario_key": f"{event}/{SCENARIO}",
        "source_mode": "SIMULATED", "method": method,
        "origin_id": f"osm-road-node:{int(inp.node_ids[pair[0]])}",
        "destination_id": f"osm-road-node:{int(inp.node_ids[pair[1]])}", "travel_mode": "vehicle",
        "departure_at_utc": valid_at, "arrival_at_utc": arrival,
        "requested_horizon_seconds": requested_seconds,
        "distance_m": float(sum(inp.arcs.length_m.iloc[a] for a in arc_ids)) if path else None,
        "travel_time_seconds": travel_time if path else None,
        "topologically_reachable": path is not None,
        "route_accessibility_probability": access_prob,
        "route_failure_probability": failure_prob,
        "minimum_accessibility_probability": ACCESSIBILITY_MINIMUM if method == "uncertainty_aware" else None,
        "route_geometry": _route_geometry(path, inp, coords), "node_path": path_node_ids,
        "edges": summary["edges"],
        "depth_thresholds": {"ordinary_block_at_or_above_m": 0.30,
                             "tunnel_proxy_block_at_or_above_m": 0.15,
                             "bridge_rule": "UNASSESSED_STRUCTURE", "thresholds_are_assumptions": True,
                             "uncertainty_route_accessibility_minimum": ACCESSIBILITY_MINIMUM,
                             "sensitivity_m": [0.15, 0.30, 0.50]},
        "edge_coverage": coverage,
        "graph": {"graph_id": "chennai_road_graph_plus_A08", "graph_version": "A08-cell-overlay-v1",
                  "graph_sha256": sha256(GRAPH_DIR / "directed_arcs.parquet"),
                  "crs": "EPSG:32644", "edge_source_ids": ["OSM directed road arcs"],
                  "build_algorithm": "A08 mapped directed graph overlay; scipy sparse Dijkstra for route selection",
                  "build_version": "A09-v1", "assumptions": ["A08 speeds and depth multipliers are assumptions"]},
        "hazard_run": {"run_id": None, "version": "A05/A06/A08 simulated hindcast", "issued_at_utc": issue_at,
                       "valid_start_utc": inp.archive(event)["valid_at_utc"][0].item(),
                       "valid_end_utc": (datetime.fromisoformat(inp.archive(event)["valid_at_utc"][-1].item().replace("Z", "+00:00"))
                                          + timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
                       "depth_source_id": f"A08:{event}/{SCENARIO}",
                       "depth_source_sha256": sha256(GRAPH_DIR / f"{event}_{SCENARIO}_snapshots.npz"),
                       "ensemble_id": f"A05/A06-members-excluding-{TRUTH_MEMBER_ID}"},
        "uncertainty": {"method": "19-member OSSE ensemble; descriptive simulated member frequency",
                        "ensemble_member_count": len(forecast_ids),
                        "travel_time_spread_seconds": summary.get("expected_time_spread_seconds"),
                        "failure_probability_constraint": ACCESSIBILITY_MINIMUM,
                        "limitations": ["Hidden truth is another simulation member, not observed truth.",
                                        "A08 member spread is not calibrated confidence coverage."]},
        "provenance": {"algorithm": "static/current/horizon/ensemble-weighted shortest path",
                       "algorithm_version": "A09-v1", "code_commit": current_commit(),
                       "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                       "parameters": {"seed": SEED, "hidden_truth_member_id": TRUTH_MEMBER_ID,
                                      "forecast_member_ids": [int(i+1) for i in forecast_ids],
                                      "expected_delay_seconds_vs_static_route": (
                                          None if travel_time is None or static_time_seconds is None else travel_time-static_time_seconds),
                                      "expected_exposure_depth_distance_m2": summary.get("expected_exposure_depth_distance_m2"),
                                      "hidden_truth_route_failed": summary.get("truth_failed"),
                                      "hidden_truth_exposure_depth_distance_m2": summary.get("truth_exposure_depth_distance_m2"),
                                      "graph_method_used": graph_method}},
        "qc_flags": ["SIMULATED_TRUTH", "SIMULATED_RESEARCH_OUTPUT", "NOT_SAFE_OR_OPERATIONAL_GUIDANCE"] +
                    (["PARTIAL_EDGE_COVERAGE"] if coverage["unassessed_edge_count"] else []) +
                    (["DEPTH_NODATA_OR_STRUCTURE_UNASSESSED"] if summary.get("forecast_accessibility_probability") is None and path else []) +
                    (["UNCERTAINTY_ACCESSIBILITY_CONSTRAINT_NOT_MET"] if status == "BELOW_ACCESSIBILITY_CONSTRAINT" else []),
    }


def run(out: Path = OUT) -> dict:
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output directory: {out}")
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    inp = RoutingInputs()
    pairs, pair_meta = choose_pairs(inp)
    pair_nodes = [int(inp.node_ids[x]) for p in pairs for x in p]
    coords = _coordinates(pair_nodes)
    if len(coords) != len(set(pair_nodes)):
        raise ValueError("could not retrieve all sampled graph-node coordinates")
    # All seven A08 horizons are checked; A09 reports three fixed departure horizons.
    rows = []
    summary_rows = []
    truth_index = list(map(int, inp.archive(EVENTS[0])["member_ids"])).index(TRUTH_MEMBER_ID)
    forecast_ids = np.array([i for i in range(len(inp.archive(EVENTS[0])["member_ids"])) if i != truth_index])
    for event in EVENTS:
        archive = inp.archive(event)
        member_ids = list(map(int, archive["member_ids"]))
        truth_index = member_ids.index(TRUTH_MEMBER_ID)
        forecast_ids = np.array([i for i in range(len(member_ids)) if i != truth_index], dtype=np.int32)
        issue_dt = datetime.fromisoformat(archive["valid_at_utc"][0].item().replace("Z", "+00:00")) - timedelta(hours=6)
        issue_at = issue_dt.isoformat().replace("+00:00", "Z")
        for horizon in HORIZONS:
            valid_at = archive["valid_at_utc"][list(map(int, archive["horizons_hours"])).index(horizon)].item()
            states, speeds, depths = inp.edge_arrays(event, horizon)
            forecast_states, truth_states = _truth_and_forecast(states, truth_index)
            forecast_speeds = speeds[forecast_ids]
            base = inp.base_time
            static_paths = inp.find_paths(base, pairs)
            static_arc_paths = [inp.arc_path(p) if p else [] for p in static_paths]
            static_time = [float(sum(base[a] for a in ids)) if p else None
                           for p, ids in zip(static_paths, static_arc_paths)]
            current_horizon = 6
            current_states, current_speeds, _ = inp.edge_arrays(event, current_horizon)
            current_weights = make_route_weights(current_states[forecast_ids], current_speeds[forecast_ids], base)
            horizon_weights = make_route_weights(forecast_states, forecast_speeds, base)
            robust_weights = make_route_weights(forecast_states, forecast_speeds, base,
                                                failure_limit=1.0-ACCESSIBILITY_MINIMUM)
            current_paths = inp.find_paths(current_weights, pairs)
            horizon_paths = inp.find_paths(horizon_weights, pairs)
            robust_paths = inp.find_paths(robust_weights, pairs)
            method_paths = {"static": static_paths, "current_flood_aware": current_paths,
                            "horizon_aware": horizon_paths, "uncertainty_aware": robust_paths}
            for pi, pair in enumerate(pairs):
                for method, paths in method_paths.items():
                    graph_method = {"static": "static free-flow network", "current_flood_aware": "6-hour forecast state; fixed current-state route",
                                    "horizon_aware": f"reoptimized at {horizon}-hour valid-time snapshot",
                                    "uncertainty_aware": "expected member time, removing edges with estimated failure >20%"}[method]
                    route = _route_result(inp, event=event, horizon=horizon, method=method,
                                          pair_index=pi, pair=pair, path=paths[pi], graph_method=graph_method,
                                          edge_states=states, edge_speeds=speeds, edge_depths=depths,
                                          forecast_ids=forecast_ids, truth_index=truth_index,
                                          coords=coords, valid_at=valid_at, issue_at=issue_at,
                                          static_time_seconds=static_time[pi])
                    # Edge timing uses the same forecast members that pass the complete route.
                    # The hazard state itself remains a discrete A08 snapshot (no temporal interpolation).
                    edge_clock = datetime.fromisoformat(valid_at.replace("Z", "+00:00"))
                    timing_known = bool(route["edges"]) and all(e["travel_time_seconds"] is not None for e in route["edges"])
                    for edge in route["edges"]:
                        edge["entry_at_utc"] = edge_clock.isoformat().replace("+00:00", "Z") if timing_known else None
                        if timing_known:
                            edge_clock += timedelta(seconds=edge["travel_time_seconds"])
                            edge["exit_at_utc"] = edge_clock.isoformat().replace("+00:00", "Z")
                        else:
                            edge["exit_at_utc"] = None
                    rows.append(route)
                    summary_rows.append({"event_key": event, "horizon_hours": horizon, "method": method,
                                         "od_pair": pi+1, "status": route["status"],
                                         "route_edge_count": route["edge_coverage"]["route_edge_count"],
                                         "assessed_edge_count": route["edge_coverage"]["assessed_edge_count"],
                                         "forecast_route_failure_probability": route["route_failure_probability"],
                                         "hidden_simulated_truth_failed": route["provenance"]["parameters"]["hidden_truth_route_failed"],
                                         "expected_travel_time_seconds": route["travel_time_seconds"],
                                         "expected_exposure_depth_distance_m2": route["provenance"]["parameters"]["expected_exposure_depth_distance_m2"]})
    # Save RFC-compatible JSONL and a machine-readable summary.
    with (out / "route_results.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
    pd.DataFrame(summary_rows).to_csv(out / "comparison_metrics.csv", index=False, lineterminator="\n")
    output = {"task": "A09 Phase 15 routing decision comparison",
              "status": "SIMULATED_RESEARCH_OUTPUT_NOT_OPERATIONAL_OR_VALIDATED",
              "schema": "docs/ROUTE_RESULT_SCHEMA.md (Lane A draft v0.1)",
              "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
              "seed": SEED, "event_keys": list(EVENTS), "scenario_key": SCENARIO,
              "hidden_truth_member_id": TRUTH_MEMBER_ID,
              "forecast_member_ids": [int(i+1) for i in forecast_ids],
              "horizons_hours": list(HORIZONS), "methods": list(METHODS),
              "accessibility_minimum": ACCESSIBILITY_MINIMUM,
              "pair_selection": pair_meta,
              "graph_counts": {"nodes": int(len(inp.node_ids)), "directed_arcs": int(inp.arc_count),
                               "unique_directed_node_pairs": int(len(inp.group_codes)),
                               "largest_strongly_connected_component_nodes": int(len(inp.largest_component_nodes))},
              "overall_graph_edge_mapping_fraction": float((inp.arcs.grid_cell_id >= 0).mean()),
              "route_result_count": len(rows), "route_result_path": "route_results.jsonl",
              "metrics_path": "comparison_metrics.csv",
              "input_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): sha256(p) for p in (
                  GRAPH_DIR / "run_summary.json", GRAPH_DIR / "directed_arcs.parquet",
                  GRAPH_DIR / "snapshot_index.parquet", ROAD_GPKG,
                  ROOT / "data/features/forecast/batch2_v1/forecast_summary.json",
                  ROOT / "data/features/impact/batch2_v4_contract/run_summary.json")},
              "runtime_seconds": round(time.perf_counter()-started, 3),
              "limitations": ["The hidden member is simulated, not observed truth.",
                              "A05 perfect-foresight IMERG scenario is hindsight forcing, not forecast skill.",
                              "A08 unmapped/ambiguous arcs remain unknown; they are excluded from flood-aware candidates.",
                              "Bridge and tunnel/underpass rules, speed reductions, and 0.15/0.30/0.50 m thresholds are assumptions.",
                              "Expected exposure is depth-distance integral (m²), not exposed population.",
                              "Discrete snapshots are used; no intermediate flood states are invented.",
                              "No route is safe, operational, or validated emergency guidance."]}
    (out / "summary.json").write_text(json.dumps(output, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    return output


def verify(out: Path = OUT) -> dict:
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    route_path = out / "route_results.jsonl"
    rows = [json.loads(line) for line in route_path.read_text(encoding="utf-8").splitlines()]
    if len(rows) != summary["route_result_count"]:
        raise ValueError("route result count does not match summary")
    ids = set()
    for r in rows:
        validate_route_record(r)
        if r["result_id"] in ids:
            raise ValueError("duplicate route result id")
        ids.add(r["result_id"])
    return {"route_results": len(rows), "schema_checks": "PASS", "no_data_checks": "PASS"}


def validate_route_record(r: dict) -> None:
    required = ("schema_id", "schema_version", "result_id", "status", "departure_at_utc",
                "arrival_at_utc", "distance_m", "travel_time_seconds", "topologically_reachable",
                "route_accessibility_probability", "route_failure_probability", "edge_coverage",
                "depth_thresholds", "graph", "hazard_run", "uncertainty", "provenance", "qc_flags")
    if any(k not in r for k in required):
        raise ValueError("route record is missing a required C8 draft field")
    if r["source_mode"] != "SIMULATED" or "SIMULATED_TRUTH" not in r["qc_flags"]:
        raise ValueError("route output lost simulated-result flag")
    if r["topologically_reachable"] != bool(r["node_path"]):
        raise ValueError("topological reachability does not match node path")
    ec = r["edge_coverage"]
    if ec["assessed_edge_count"] + ec["unassessed_edge_count"] != ec["route_edge_count"]:
        raise ValueError("edge coverage counts do not reconcile")
    access, failure = r["route_accessibility_probability"], r["route_failure_probability"]
    if access is not None and not math.isclose(access + failure, 1.0, abs_tol=1e-9):
        raise ValueError("route accessibility and failure probabilities do not complement")
    if ec["unassessed_edge_count"] and access is not None:
        raise ValueError("unassessed route unexpectedly has accessibility probability")
    if access is None and failure is not None:
        raise ValueError("failure probability must be null when accessibility is unknown")
    if not r["topologically_reachable"] and any(r[k] is not None for k in ("distance_m", "travel_time_seconds", "arrival_at_utc", "route_geometry")):
        raise ValueError("no-path route has fabricated geometry or measurements")
    if any(e["assessment_status"] == "UNASSESSED_OR_NODATA" and e["passable_probability"] is not None for e in r["edges"]):
        raise ValueError("unknown edge was assigned a probability")
    if any((e["entry_at_utc"] is None) != (e["exit_at_utc"] is None) for e in r["edges"]):
        raise ValueError("edge entry/exit time null semantics do not match")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    print(json.dumps(verify(output) if args.verify_only else run(output), indent=2))


if __name__ == "__main__":
    main()
