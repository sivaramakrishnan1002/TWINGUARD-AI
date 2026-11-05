"""A21 preregistered three-state routing and stability OSSE.

Run from the repository root with .venv/Scripts/python pipelines/routing/three_state_batch3/analyze.py.
The script reads immutable A05/A08/A09/A10 artifacts and writes a new, versioned A21 directory only.
"""
from __future__ import annotations

import hashlib
import heapq
import json
import math
import os
import sqlite3
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/features/routing/three_state_batch3_v1"
PREREG = ROOT / "docs/ROUTING_THREE_STATE_BATCH3_PREREGISTRATION.md"
BASE = ROOT / "data/features/routing/time_dependent_batch2"
ARCS_PATH = BASE / "directed_arcs.parquet"
NODES_PATH = ROOT / "data/features/roads/chennai_road_graph.gpkg"
SNAP_PATH = BASE / "snapshot_index.parquet"
A09_PATH = ROOT / "data/features/routing/results/batch2_v1/revision_3/route_results.jsonl"
A10_DIR = ROOT / "data/features/decision/shelters/batch2_v3"

SEED = 21031
EVENTS = {"2015-12-02", "2021-11-13", "2023-12-04"}
SCENARIOS = {"perfect_foresight_imerg", "persistence_previous_day", "rain_error_q10", "rain_error_q50", "rain_error_q90"}
HORIZONS = {6, 24, 72}
STATE_NAMES = {0: "UNKNOWN", 1: "ASSESSED_PASSABLE", 2: "ASSESSED_PASSABLE", 3: "ASSESSED_BLOCKED", 4: "UNKNOWN"}
_ARC_MASK_CACHE: dict[int, dict[str, np.ndarray]] = {}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_registered_inputs() -> dict[str, str]:
    """Check the exact static inputs and every A05/A08 archive hash against frozen prereg text."""
    text = PREREG.read_text(encoding="utf-8")
    fixed = [
        "data/features/routing/time_dependent_batch2/directed_arcs.parquet",
        "data/features/routing/time_dependent_batch2/static_segments.parquet",
        "data/features/routing/time_dependent_batch2/snapshot_index.parquet",
        "data/features/routing/time_dependent_batch2/run_summary.json",
        "data/features/roads/chennai_road_graph.gpkg",
        "data/features/forecast/batch2_v1/forecast_summary.json",
        "data/features/routing/results/batch2_v1/revision_3/route_results.jsonl",
        "data/features/routing/results/batch2_v1/revision_3/comparison_metrics.csv",
        "data/features/routing/results/batch2_v1/revision_3/summary.json",
        "data/features/decision/shelters/batch2_v3/allocation_cases.parquet",
        "data/features/decision/shelters/batch2_v3/allocation_detail.parquet",
        "data/features/decision/shelters/batch2_v3/candidate_facilities.parquet",
        "data/features/decision/shelters/batch2_v3/run_summary.json",
        "docs/ROUTING_GRAPH_BATCH2.md", "docs/ROUTING_BATCH2.md",
        "docs/VALIDATION_REPORT.md", "docs/DECISION_LAB_BATCH2.md",
        "docs/SHELTER_ALLOCATION_BATCH2.md",
    ]
    result: dict[str, str] = {}
    for rel in fixed:
        p = ROOT / rel
        actual = sha256(p)
        if actual not in text:
            raise RuntimeError(f"PREREG_HASH_MISMATCH: {rel}")
        result[rel] = actual
    for directory, pattern in [(ROOT / "data/features/routing/time_dependent_batch2", "*_snapshots.npz"),
                                (ROOT / "data/features/forecast/batch2_v1", "depth_members_by_horizon_DERIVED.npz")]:
        found = sorted(directory.rglob(pattern))
        if len(found) != 15:
            raise RuntimeError(f"PREREG_INPUT_COUNT_MISMATCH: {directory} {len(found)} != 15")
        for p in found:
            actual = sha256(p)
            if actual not in text:
                raise RuntimeError(f"PREREG_HASH_MISMATCH: {p.relative_to(ROOT).as_posix()}")
            result[p.relative_to(ROOT).as_posix()] = actual
    return result


def _dense(ids: np.ndarray, values: np.ndarray) -> np.ndarray:
    pos = np.searchsorted(ids, values)
    valid = (pos < len(ids))
    valid[valid] &= ids[pos[valid]] == values[valid]
    return np.where(valid, pos, -1).astype(np.int32)


def _collapse(n: int, rows: np.ndarray, cols: np.ndarray, weights: np.ndarray,
              arc_index: np.ndarray) -> tuple[object, np.ndarray, np.ndarray, np.ndarray]:
    """Keep the minimum-weight parallel directed arc, arc index breaks equal-edge ties."""
    ok = (rows >= 0) & (cols >= 0) & np.isfinite(weights) & (weights >= 0)
    rows, cols, weights, arc_index = rows[ok], cols[ok], weights[ok], arc_index[ok]
    order = np.lexsort((arc_index, weights, cols, rows))
    rows, cols, weights, arc_index = rows[order], cols[order], weights[order], arc_index[order]
    first = np.ones(len(rows), dtype=bool)
    if len(rows) > 1:
        first[1:] = (rows[1:] != rows[:-1]) | (cols[1:] != cols[:-1])
    rows, cols, weights, arc_index = rows[first], cols[first], weights[first], arc_index[first]
    return coo_matrix((weights, (rows, cols)), shape=(n, n)).tocsr(), rows, cols, arc_index


def _collapse_preordered(n: int, rows: np.ndarray, cols: np.ndarray, weights: np.ndarray,
                         active: np.ndarray, arc_index: np.ndarray,
                         pair_order: np.ndarray, pair_starts: np.ndarray):
    """Collapse parallel arcs using a static row/column/arc ordering (no per-source sort)."""
    ordered=pair_order
    ow=np.where(active[ordered],weights[ordered],np.inf)
    minima=np.minimum.reduceat(ow,pair_starts)
    repeated=np.repeat(minima,np.diff(np.r_[pair_starts,len(ordered)]))
    candidate=np.where(ow==repeated,arc_index[ordered],np.iinfo(np.int64).max)
    chosen=np.minimum.reduceat(candidate,pair_starts)
    good=np.isfinite(minima)
    rr=rows[ordered[pair_starts]][good]; cc=cols[ordered[pair_starts]][good]
    aa=chosen[good]
    graph=coo_matrix((minima[good],(rr,cc)),shape=(n,n)).tocsr()
    return graph,rr,cc,aa


def _arc_lookup(n: int, rows: np.ndarray, cols: np.ndarray, arc_indices: np.ndarray):
    keys = rows.astype(np.int64) * n + cols
    order = np.argsort(keys, kind="stable")
    return keys[order], arc_indices[order]


def _outgoing_by_arc(n: int, rows: np.ndarray, cols: np.ndarray, weights: np.ndarray,
                     arc_indices: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    order = np.lexsort((arc_indices, rows))
    rr, cc, ww, aa = rows[order], cols[order], weights[order], arc_indices[order]
    offsets = np.zeros(n + 1, dtype=np.int64)
    np.add.at(offsets, rr + 1, 1)
    np.cumsum(offsets, out=offsets)
    return offsets, cc, ww, aa


def _recover_lex(source: int, target: int, total_cost: float, reverse_dist: np.ndarray,
                 target_row: int, offsets: np.ndarray, cols: np.ndarray, weights: np.ndarray,
                 arc_indices: np.ndarray) -> list[int] | None:
    """Exact shortest-cost path with lexicographically smallest arc-index sequence on ties."""
    if source == target:
        return []
    path=[]; node=int(source); prefix=0.0; n=len(offsets)-1
    tol=1e-9*max(1.0,abs(float(total_cost)))
    for _ in range(n):
        chosen=None
        for j in range(offsets[node],offsets[node+1]):
            tail=float(reverse_dist[target_row,cols[j]])
            if np.isfinite(tail) and abs((prefix+float(weights[j])+tail)-total_cost)<=tol:
                chosen=j
                break
        if chosen is None:
            return None
        path.append(int(arc_indices[chosen])); prefix+=float(weights[chosen]); node=int(cols[chosen])
        if node==target:
            return path
    raise RuntimeError("lexicographic shortest-path extraction exceeded node count")


def _recover(source: int, target: int, source_row: int, pred: np.ndarray,
             keys: np.ndarray, arc_for_key: np.ndarray, n: int) -> list[int] | None:
    if source == target:
        return []
    rev = []
    node = int(target)
    for _ in range(n):
        prev = int(pred[source_row, node])
        if prev < 0:
            return None
        key = prev * n + node
        idx = int(np.searchsorted(keys, key))
        if idx >= len(keys) or keys[idx] != key:
            return None
        rev.append(int(arc_for_key[idx]))
        node = prev
        if node == source:
            return rev[::-1]
    raise RuntimeError("predecessor cycle in shortest-path tree")


def sample_pairs(nodes: pd.DataFrame, arcs: pd.DataFrame, ids: np.ndarray,
                 rows: np.ndarray, cols: np.ndarray) -> tuple[list[dict], list[dict]]:
    rng = np.random.Generator(np.random.PCG64(SEED))
    xy = np.column_stack([nodes.geometry.x.to_numpy(), nodes.geometry.y.to_numpy()])
    node_ids = nodes.osmid.to_numpy(dtype=np.int64)
    node_pos = np.searchsorted(ids, node_ids)
    medx, medy = np.median(xy[:, 0]), np.median(xy[:, 1])
    sector = np.where(xy[:, 1] >= medy, np.where(xy[:, 0] >= medx, "NE", "NW"),
                      np.where(xy[:, 0] >= medx, "SE", "SW"))
    static, sr, sc, sa = _collapse(len(ids), rows, cols, arcs.length_m.to_numpy(float),
                                   arcs.arc_index.to_numpy(np.int64))
    skeys, sarcs = _arc_lookup(len(ids), sr, sc, sa)
    required = {(s, b): 10 for s in ("NW", "NE", "SW", "SE") for b in ("short", "medium", "long")}
    selected: list[dict] = []
    path_map: dict[tuple[int, int], list[int]] = {}
    seen: set[tuple[int, int]] = set()
    for sec in ("NW", "NE", "SW", "SE"):
        candidates = np.flatnonzero(sector == sec)
        candidates = rng.permutation(candidates)
        origins_examined = 0
        for oi in candidates:
            if origins_examined >= 500 or all(v == 0 for (s, _), v in required.items() if s == sec):
                break
            origins_examined += 1
            src = int(node_pos[oi])
            dist, pred = dijkstra(static, directed=True, indices=src, return_predecessors=True)
            for band, lo, hi in (("short", 0.0, 5000.0), ("medium", 5000.0, 15000.0), ("long", 15000.0, np.inf)):
                if required[(sec, band)] <= 0:
                    continue
                dests = np.flatnonzero(np.isfinite(dist) & (dist >= lo) & (dist < hi) & (np.arange(len(ids)) != src))
                for di in rng.permutation(dests):
                    dst = int(di)
                    pair = (int(ids[src]), int(ids[dst]))
                    if pair in seen:
                        continue
                    pth = _recover(src, dst, 0, pred[None, :], skeys, sarcs, len(ids))
                    if pth is None:
                        continue
                    seen.add(pair)
                    path_map[pair] = pth
                    selected.append({"od_id": len(selected), "origin_osmid": pair[0], "destination_osmid": pair[1],
                                     "origin_dense": src, "destination_dense": dst, "sector": sec,
                                     "distance_band": band, "static_distance_m": float(dist[dst]),
                                     "sampling_class": "PRIMARY", "static_shortest_arc_indices": pth})
                    required[(sec, band)] -= 1
                    break
        print(f"sampling {sec}: origins_examined={origins_examined}, remaining=" +
              str({b: required[(sec, b)] for b in ("short", "medium", "long")} ), flush=True)
    if len(selected) < 120:
        raise RuntimeError(f"PRIMARY_SAMPLE_INFEASIBLE: selected {len(selected)} of 120; remaining={required}")

    # Supplement only topologically disconnected directed pairs, using SCCs as candidate strata.
    _, labels = connected_components(static, directed=True, connection="strong")
    supplement = []
    for sec in ("NW", "NE", "SW", "SE"):
        candidates = rng.permutation(np.flatnonzero(sector == sec))
        for oi in candidates:
            if len([x for x in supplement if x["sector"] == sec]) >= 3:
                break
            src = int(node_pos[oi])
            dist = dijkstra(static, directed=True, indices=src, return_predecessors=False)
            ds = rng.permutation(np.flatnonzero((labels != labels[src]) & ~np.isfinite(dist)))
            if not len(ds):
                continue
            dst = int(ds[0]); pair=(int(ids[src]), int(ids[dst]))
            if pair in seen: continue
            seen.add(pair)
            supplement.append({"od_id": len(selected)+len(supplement), "origin_osmid": pair[0], "destination_osmid": pair[1],
                               "origin_dense":src,"destination_dense":dst,"sector":sec,"distance_band":"DISCONNECTED",
                               "static_distance_m":None,"sampling_class":"STATIC_DISCONNECTED_SUPPLEMENT",
                               "static_shortest_arc_indices":[]})
        if len([x for x in supplement if x["sector"] == sec]) < 3:
            print(f"supplement {sec}: only {len([x for x in supplement if x['sector']==sec])}/3 feasible", flush=True)
    return selected, supplement


def edge_states(archive: dict, mi: int, hi: int, arcs: pd.DataFrame, arc_grid_pos: np.ndarray,
                state_order: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(arcs)
    cache_key=id(arcs)
    if cache_key not in _ARC_MASK_CACHE:
        structures=arcs.structure_class.to_numpy()
        status=arcs.assessment_status.to_numpy()
        _ARC_MASK_CACHE[cache_key]={
            "ordinary":np.flatnonzero(structures=="ordinary"),
            "tunnel":np.flatnonzero(structures=="tunnel_underpass_proxy"),
            "special":np.flatnonzero(np.isin(structures,["bridge","bridge_and_tunnel","unassessed"])),
            "no_map":status=="NO_A07_ELIGIBLE_CELL",
            "ambiguous":status=="AMBIGUOUS_OR_UNMATCHED_SEGMENT_KEY",
        }
    masks=_ARC_MASK_CACHE[cache_key]
    state = np.zeros(n, np.uint8)
    reason = np.full(n, "NO_A07_ELIGIBLE_CELL", dtype=object)
    multiplier = np.ones(n, np.float64)
    good = arc_grid_pos >= 0
    # Sort each snapshot grid once; arc_grid_pos is built in that same id space.
    if good.any():
        gridpos = state_order[arc_grid_pos[good]]
        selected_pos = np.flatnonzero(good)
        for indices, key, mult_key in ((masks["ordinary"], "ordinary_state", "ordinary_speed_multiplier"),
                                        (masks["tunnel"], "tunnel_state", "tunnel_speed_multiplier")):
            ix=indices[good[indices]]
            if not len(ix): continue
            gp = gridpos[np.searchsorted(selected_pos,ix)]
            vals = archive[key][mi, hi, gp]
            mvals = archive[mult_key][mi, hi, gp]
            state[ix] = vals
            multiplier[ix] = mvals
            reason[ix] = np.where(vals == 0, "UNKNOWN_NODATA", np.where(vals == 4, "UNASSESSED_STRUCTURE", "ASSESSED"))
        # Bridges, bridge+tunnel and unassessed structures stay UNKNOWN regardless of underlying depth.
        ix=masks["special"][good[masks["special"]]]
        if len(ix):
            state[ix] = 4
            reason[ix] = "UNASSESSED_STRUCTURE"
    # Preserve source graph omissions/ambiguous joins as explicit unknown reason codes.
    no_map = masks["no_map"]
    ambiguous = masks["ambiguous"]
    state[no_map] = 0; reason[no_map] = "NO_A07_ELIGIBLE_CELL"
    state[ambiguous] = 0; reason[ambiguous] = "AMBIGUOUS_OR_UNMATCHED_SEGMENT_KEY"
    # ordinary/tunnel A08 state 0/4 remains unknown. Convert state codes only, never depth NoData to dry.
    return state, reason, multiplier


def state_route_graph(n: int, arcs: pd.DataFrame, rows: np.ndarray, cols: np.ndarray,
                      states: np.ndarray, mult: np.ndarray):
    lengths = arcs.length_m.to_numpy(np.float64)
    speed = arcs.base_speed_kmh.to_numpy(np.float64)
    idx = arcs.arc_index.to_numpy(np.int64)
    passable = np.isin(states, [1, 2])
    unknown = np.isin(states, [0, 4])
    blocked = states == 3
    base_secs = np.divide(lengths * 3.6, speed * mult, out=np.full(len(arcs), np.inf), where=(speed > 0) & (mult > 0))
    weights = np.where(passable, base_secs, np.inf)
    active = passable
    graph, rr, cc, kept = _collapse(n, rows[active], cols[active], weights[active], idx[active])
    keys, arc_for_key = _arc_lookup(n, rr, cc, kept)
    offsets, outcols, outweights, outarcs = _outgoing_by_arc(n, rr, cc, weights[kept], kept)
    return graph, keys, arc_for_key, (offsets,outcols,outweights,outarcs)


def conditional_paths_for_source(n: int, arcs: pd.DataFrame, rows: np.ndarray, cols: np.ndarray,
                                 states: np.ndarray, multipliers: np.ndarray,
                                 source: int, destinations: list[int],
                                 unknown_distance: np.ndarray | None = None,
                                 pair_order: np.ndarray | None = None,
                                 pair_starts: np.ndarray | None = None) -> dict[int, list[int] | None]:
    """Strictly minimize unknown metres, then assessed travel seconds, then arc-index sequence."""
    lengths=arcs.length_m.to_numpy(np.float64); arc_ids=arcs.arc_index.to_numpy(np.int64)
    passable=np.isin(states,[1,2]); unknown=np.isin(states,[0,4]); eligible=passable|unknown
    uweights=np.where(unknown,lengths,0.0)
    if unknown_distance is None:
        ug,_,_,_=_collapse(n,rows[eligible],cols[eligible],uweights[eligible],arc_ids[eligible])
        du=dijkstra(ug,directed=True,indices=int(source),return_predecessors=False)
    else:
        du=unknown_distance
    finite=np.isfinite(du[rows]) & np.isfinite(du[cols])
    with np.errstate(invalid="ignore"):
        delta=du[rows]+uweights-du[cols]
    tight=eligible & finite & (np.abs(delta)<=1e-9*np.maximum(1.0,np.abs(du[cols])))
    speed=arcs.base_speed_kmh.to_numpy(np.float64)
    pass_secs=np.divide(lengths*3.6,speed*multipliers,out=np.full(len(arcs),np.inf),where=(speed>0)&(multipliers>0))
    sweights=np.where(passable,pass_secs,0.0)
    if pair_order is None or pair_starts is None:
        graph,rr,cc,kept=_collapse(n,rows[tight],cols[tight],sweights[tight],arc_ids[tight])
    else:
        graph,rr,cc,kept=_collapse_preordered(n,rows,cols,sweights,tight,arc_ids,pair_order,pair_starts)
    outgoing=_outgoing_by_arc(n,rr,cc,sweights[kept],kept)
    dests=np.asarray(sorted(set(map(int,destinations))),dtype=np.int32)
    reverse=dijkstra(graph.transpose().tocsr(),directed=True,indices=dests,return_predecessors=False)
    paths={}
    for dst in dests:
        dst=int(dst)
        # Reverse distances provide each target's exact assessed-time distance to the source.
        # This avoids a redundant source-rooted Dijkstra while preserving the arc-sequence tie rule.
        target_ix=int(np.searchsorted(dests,dst))
        cost=float(reverse[target_ix,int(source)])
        paths[dst]=None if not np.isfinite(cost) else _recover_lex(int(source),dst,cost,reverse,target_ix,*outgoing)
    return paths


def route_details(path: list[int] | None, states: np.ndarray, reasons: np.ndarray,
                  lengths_by_arc: np.ndarray, speed_by_arc: np.ndarray,
                  multiplier: np.ndarray) -> dict:
    if path is None:
        return {"status": "NO_PATH", "arc_indices": [], "unknown_edge_count": None,
                "unknown_distance_m": None, "path_length_m": None, "travel_time_seconds": None,
                # Keep the Parquet column schema stable: non-empty routes store a
                # reason-count mapping, so the no-path value must also be a mapping.
                "assessed_edge_fraction": None, "unknown_reasons": {}}
    unknown_len = 0.0; total_len = 0.0; secs = 0.0; assessed = 0; reasons_count = Counter()
    for ai in path:
        ai = int(ai); length = float(lengths_by_arc[ai]); total_len += length
        st = int(states[int(ai)])
        if st in (0, 4):
            unknown_len += length; reasons_count[str(reasons[int(ai)])] += 1
        else:
            assessed += 1
            if st in (1, 2):
                secs += length * 3.6 / (float(speed_by_arc[ai]) * float(multiplier[ai]))
    status = "CONDITIONAL_NEEDS_VERIFICATION" if unknown_len > 0 else "ASSESSED_PASSABLE_UNDER_A08_ASSUMPTIONS"
    return {"status":status,"arc_indices":path,"unknown_edge_count":sum(reasons_count.values()),
            "unknown_distance_m":unknown_len,"path_length_m":total_len,"travel_time_seconds_assessed_edges_only":secs,
            "assessed_edge_fraction":assessed / len(path) if path else 1.0,
            "unknown_reasons":dict(reasons_count)}


def normalize_route_reason_counts(route_rows: list[dict]) -> None:
    """Normalize legacy checkpoint fields without changing recorded path choices."""
    for row in route_rows:
        if row.get("unknown_reasons") == []:
            row["unknown_reasons"] = {}
        if row.get("unknown_arc_indices") is None:
            path=row.get("proposed_arc_indices") or []
            states=row.get("proposed_edge_states") or []
            if len(path)!=len(states):
                raise RuntimeError("LEGACY_CHECKPOINT_EDGE_STATE_LENGTH_MISMATCH")
            row["unknown_arc_indices"]=[int(ai) for ai,state in zip(path,states) if state=="UNKNOWN"]
            count=row.get("unknown_edge_count")
            if count is not None and len(row["unknown_arc_indices"])!=int(count):
                raise RuntimeError("LEGACY_CHECKPOINT_UNKNOWN_EDGE_COUNT_MISMATCH")


def greedy_unknown_edge_priority(exposure: dict[int,set[tuple]], edge_lengths: dict[int,float]) -> list[int]:
    """Exact lazy greedy coverage order with stable distance and arc-ID tie breaks."""
    if not exposure:
        return []
    remaining=set().union(*exposure.values())
    queue=[(-len(cases),-float(edge_lengths[ai]),int(ai)) for ai,cases in exposure.items()]
    heapq.heapify(queue)
    ranked=[]
    while queue:
        neg_upper,neg_len,ai=heapq.heappop(queue)
        actual=len(exposure[ai]&remaining)
        current=(-actual,neg_len,ai)
        # Cached marginal counts are upper bounds. Accept only when this exact key
        # outranks every remaining upper-bound key; otherwise recompute later.
        if queue and current>queue[0]:
            heapq.heappush(queue,(-actual,neg_len,ai))
            continue
        ranked.append(ai)
        remaining.difference_update(exposure[ai])
    return ranked


def main() -> None:
    started = time.time()
    checkpoint_path=OUT/"checkpoint.sqlite"
    final_names={"sampled_od_pairs.parquet","static_reference_paths.parquet","route_cases.parquet","coverage_cases.parquet",
        "heldout_member20_osse.parquet","snapshot_edge_counts.parquet","unknown_verification_priority.parquet",
        "unknown_input_decision_priority.parquet","verification_budget_coverage.parquet","shelter_choice_by_case.parquet",
        "route_choice_changes.parquet","shelter_choice_changes.parquet","run_summary.json","manifest.json"}
    if OUT.exists() and any((OUT/name).exists() for name in final_names):
        raise RuntimeError(f"REFUSE_EXISTING_FINAL_OUTPUT: {OUT}")
    hashes = verify_registered_inputs()
    print(f"verified {len(hashes)} preregistered inputs", flush=True)
    nodes = pyogrio.read_dataframe(NODES_PATH, layer="road_nodes")
    arcs = pd.read_parquet(ARCS_PATH)
    snaps = pd.read_parquet(SNAP_PATH)
    nodes = nodes.sort_values("osmid", kind="stable").reset_index(drop=True)
    ids = nodes.osmid.to_numpy(np.int64)
    rows = np.searchsorted(ids, arcs.from_node.to_numpy(np.int64)).astype(np.int32)
    cols = np.searchsorted(ids, arcs.to_node.to_numpy(np.int64)).astype(np.int32)
    if (np.any(ids[rows] != arcs.from_node.to_numpy(np.int64)) or np.any(ids[cols] != arcs.to_node.to_numpy(np.int64))
            or not np.array_equal(arcs.arc_index.to_numpy(np.int64),np.arange(len(arcs),dtype=np.int64))):
        raise RuntimeError("AMBIGUOUS_GRAPH_NODE_JOIN")
    pair_order=np.lexsort((arcs.arc_index.to_numpy(np.int64),cols,rows))
    pair_starts=np.r_[0,np.flatnonzero((rows[pair_order][1:]!=rows[pair_order][:-1])|
                                      (cols[pair_order][1:]!=cols[pair_order][:-1]))+1].astype(np.int64)
    grid_ids_base = arcs.grid_cell_id.to_numpy(np.int64)
    # Archive grid ids are verified per archive; mapping is a binary search over the sorted archive cell ids.
    selected, supplement = sample_pairs(nodes, arcs, ids, rows, cols)
    pairs = selected + supplement
    primary_count = len(selected)
    print(f"sampled primary={primary_count}, supplement={len(supplement)}", flush=True)
    snapshots = snaps[snaps.event_key.isin(EVENTS) & snaps.scenario_key.isin(SCENARIOS) & snaps.horizon_hours.isin(HORIZONS)].copy()
    if len(snapshots) != 900:
        raise RuntimeError(f"SNAPSHOT_COUNT_MISMATCH: {len(snapshots)} != 900")

    # Match route provenance to A10 shelter decisions and validate exact case keys before analysis.
    alloc_cases = pd.read_parquet(A10_DIR / "allocation_cases.parquet")
    alloc_detail = pd.read_parquet(A10_DIR / "allocation_detail.parquet")
    case_key = ["event_key", "scenario_key", "horizon_hours", "valid_at_utc", "member_id", "capacity_factor"]
    if alloc_cases.duplicated(case_key).any():
        raise RuntimeError("DUPLICATE_A10_CASE_KEY")
    route_rows = []
    coverage_rows = []
    truth_rows = []
    unknown_case_sets: dict[int, set[tuple]] = defaultdict(set)
    unknown_length_by_arc: Counter = Counter()
    snapshot_stats = []
    OUT.mkdir(parents=True,exist_ok=True)
    checkpoint=sqlite3.connect(checkpoint_path)
    checkpoint.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    checkpoint.execute("CREATE TABLE IF NOT EXISTS snapshots (snapshot_key TEXT PRIMARY KEY, route_json TEXT NOT NULL, coverage_json TEXT NOT NULL, truth_json TEXT NOT NULL, stats_json TEXT NOT NULL, unknown_json TEXT NOT NULL)")
    expected_meta={"preregistration_sha256":sha256(PREREG),"registered_input_hashes":json.dumps(hashes,sort_keys=True)}
    old_meta=dict(checkpoint.execute("SELECT key,value FROM meta"))
    if old_meta and old_meta!=expected_meta:
        checkpoint.close(); raise RuntimeError("CHECKPOINT_METADATA_MISMATCH")
    checkpoint.executemany("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)",expected_meta.items()); checkpoint.commit()
    cached=list(checkpoint.execute("SELECT route_json,coverage_json,truth_json,stats_json,unknown_json FROM snapshots"))
    for route_json,coverage_json,truth_json,stats_json,unknown_json in cached:
        route_rows.extend(json.loads(route_json)); coverage_rows.extend(json.loads(coverage_json))
        truth_rows.extend(json.loads(truth_json)); snapshot_stats.append(json.loads(stats_json))
        for row in json.loads(unknown_json):
            key=(row["event_key"],row["scenario_key"],int(row["horizon_hours"]),int(row["member_id"]),int(row["od_id"]))
            ai=int(row["arc_index"]); unknown_case_sets[ai].add(key); unknown_length_by_arc[ai]+=float(row["length_m"])
    if cached: print(f"resuming from {len(cached)}/{len(snapshots)} saved snapshot checkpoints",flush=True)
    worker_count=max(1,min(12,(os.cpu_count() or 2)-2))
    conditional_pool=ThreadPoolExecutor(max_workers=worker_count)
    # Cache decoded archives so their content is opened once, with no writes to source files.
    archives = {}
    for archive_name, group in snapshots.groupby("archive", sort=True):
        p = BASE / str(archive_name)
        with np.load(p, allow_pickle=False) as z:
            archives[str(archive_name)] = {k:z[k] for k in z.files}
    # Enrich routes from a checkpoint created before edge-state detail was added.
    # Recompute only the recorded snapshot edge states from immutable A08 arrays;
    # route selection and sampling remain exactly as checkpointed.
    route_by_snapshot=defaultdict(list)
    for rr_i,row in enumerate(route_rows):
        if "proposed_edge_states" not in row:
            route_by_snapshot[(row["event_key"],row["scenario_key"],int(row["horizon_hours"]),int(row["member_id"]))].append(rr_i)
    if route_by_snapshot:
        snap_lookup={(str(r.event_key),str(r.scenario_key),int(r.horizon_hours),int(r.member_id)):r for _,r in snapshots.iterrows()}
        for skey,indices in route_by_snapshot.items():
            sr=snap_lookup[skey]; archive=archives[str(sr.archive)]
            gids=archive["grid_cell_ids"].astype(np.int64); order=np.argsort(gids,kind="stable"); sg=gids[order]
            pos0=np.searchsorted(sg,grid_ids_base)
            arcpos=np.where((pos0<len(sg))&(sg[np.minimum(pos0,len(sg)-1)]==grid_ids_base),pos0,-1)
            st,reason,_=edge_states(archive,int(sr.member_index),int(sr.horizon_index),arcs,arcpos,order)
            for i in indices:
                row=route_rows[i]
                for prefix,key in (("proposed","proposed_arc_indices"),("baseline","baseline_arc_indices")):
                    path=[int(x) for x in row[key]]
                    row[f"{prefix}_edge_states"]=[STATE_NAMES[int(st[x])] for x in path]
                    row[f"{prefix}_edge_reasons"]=[str(reason[x]) for x in path]
    normalize_route_reason_counts(route_rows)
    by_arc = arcs.set_index("arc_index", drop=False)
    lengths_by_arc = arcs.length_m.to_numpy(np.float64)
    speeds_by_arc = arcs.base_speed_kmh.to_numpy(np.float64)
    source_to_pairs = defaultdict(list)
    for pair in pairs: source_to_pairs[pair["origin_dense"]].append(pair)
    truth_state_cache: dict[tuple, np.ndarray] = {}
    ordered_snapshots = snapshots.sort_values(["event_key","scenario_key","horizon_hours","member_id"], kind="stable")
    for si, (_, snap) in enumerate(ordered_snapshots.iterrows(),1):
        snapshot_key=(str(snap.event_key),str(snap.scenario_key),int(snap.horizon_hours),int(snap.member_id))
        snapshot_key_text=json.dumps(snapshot_key,separators=(",",":"))
        if checkpoint.execute("SELECT 1 FROM snapshots WHERE snapshot_key=?",(snapshot_key_text,)).fetchone():
            continue
        route_start=len(route_rows); coverage_start=len(coverage_rows); truth_start=len(truth_rows)
        unknown_rows=[]
        archive = archives[str(snap.archive)]
        gridids = archive["grid_cell_ids"].astype(np.int64)
        if len(np.unique(gridids)) != len(gridids): raise RuntimeError("DUPLICATE_ARCHIVE_GRID_ID")
        order = np.argsort(gridids, kind="stable")
        sg = gridids[order]
        arcpos0 = np.searchsorted(sg, grid_ids_base)
        arcpos = np.where((arcpos0 < len(sg)) & (sg[np.minimum(arcpos0, len(sg)-1)] == grid_ids_base), arcpos0, -1)
        mi, hi = int(snap.member_index), int(snap.horizon_index)
        states, reasons, multipliers = edge_states(archive, mi, hi, arcs, arcpos, order)
        # state distributions are recorded per saved graph snapshot.
        scount = Counter(np.where(np.isin(states,[1,2]),"ASSESSED_PASSABLE",np.where(states==3,"ASSESSED_BLOCKED","UNKNOWN")))
        # Static shortest reference corridor coverage, recorded separately from flood-aware route outcomes.
        for pair in pairs:
            refpath = pair["static_shortest_arc_indices"]
            if pair["sampling_class"] != "PRIMARY":
                continue
            if refpath:
                vals = states[np.asarray(refpath,dtype=np.int64)]
                ac = int(np.isin(vals,[1,2,3]).sum()); unk=len(vals)-ac
                cls="FULL" if unk==0 else ("ABSENT_OR_AMBIGUOUS" if ac==0 else "PARTIAL")
            else:
                cls="STATIC_NO_PATH"
            coverage_rows.append({"event_key":str(snap.event_key),"scenario_key":str(snap.scenario_key),
                "horizon_hours":int(snap.horizon_hours),"member_id":int(snap.member_id),"od_id":pair["od_id"],
                "coverage_class_on_static_reference_path":cls,"reference_edge_count":len(refpath)})
        pass_graph, pkeys, parc, pass_out = state_route_graph(len(ids), arcs, rows, cols, states, multipliers)
        origins = np.asarray(sorted(source_to_pairs),dtype=np.int32)
        dist = dijkstra(pass_graph,directed=True,indices=origins,return_predecessors=False)
        origin_row = {int(o):i for i,o in enumerate(origins)}
        targets = np.asarray(sorted({int(p["destination_dense"]) for p in pairs}),dtype=np.int32)
        pass_reverse = dijkstra(pass_graph.transpose().tocsr(),directed=True,indices=targets,return_predecessors=False)
        target_row={int(t):i for i,t in enumerate(targets)}
        # Conditional graph is built only where fail-closed routing returns no path.
        needs_cond = [p for p in pairs if not np.isfinite(dist[origin_row[p["origin_dense"]],p["destination_dense"]])]
        cresult = {}
        if needs_cond:
            # Strict lexicographic objective in two stages: minimum unknown-edge metres,
            # then minimum assessed-passable travel seconds on paths attaining that minimum.
            cond_origins=np.asarray(sorted({p["origin_dense"] for p in needs_cond}),dtype=np.int32)
            source_groups={int(src):[p for p in needs_cond if p["origin_dense"]==int(src)] for src in cond_origins}
            # Unknown-distance stage is identical for every source in this snapshot, so solve
            # all origins in one batched sparse-Dijkstra call. Keep the exact two-stage objective.
            lengths=arcs.length_m.to_numpy(np.float64); arc_ids=arcs.arc_index.to_numpy(np.int64)
            passable=np.isin(states,[1,2]); unknown=np.isin(states,[0,4]); eligible=passable|unknown
            uweights=np.where(unknown,lengths,0.0)
            unknown_graph,_,_,_=_collapse(len(ids),rows[eligible],cols[eligible],uweights[eligible],arc_ids[eligible])
            unknown_distances=dijkstra(unknown_graph,directed=True,indices=cond_origins,return_predecessors=False)
            cond_origin_row={int(src):i for i,src in enumerate(cond_origins)}
            futures={int(src):conditional_pool.submit(conditional_paths_for_source,len(ids),arcs,rows,cols,states,multipliers,
                int(src),[p["destination_dense"] for p in source_groups[int(src)]],unknown_distances[cond_origin_row[int(src)]],
                pair_order,pair_starts) for src in cond_origins}
            for src,future in futures.items():
                source_paths=future.result()
                for p in source_groups[src]: cresult[p["od_id"]]=source_paths[int(p["destination_dense"])]
        for pair in pairs:
            ori,dst=pair["origin_dense"],pair["destination_dense"]
            rr=origin_row[ori]
            baseline_path=None if not np.isfinite(dist[rr,dst]) else _recover_lex(ori,dst,float(dist[rr,dst]),
                pass_reverse,target_row[dst],*pass_out)
            proposed=baseline_path if baseline_path is not None else cresult.get(pair["od_id"])
            bdetail=route_details(baseline_path,states,reasons,lengths_by_arc,speeds_by_arc,multipliers)
            pdetail=route_details(proposed,states,reasons,lengths_by_arc,speeds_by_arc,multipliers)
            case_tuple=(str(snap.event_key),str(snap.scenario_key),int(snap.horizon_hours),int(snap.member_id),int(pair["od_id"]))
            if proposed is not None:
                path_arr=np.asarray(proposed,dtype=np.int64)
                unknown_arcs=path_arr[np.isin(states[path_arr],[0,4])]
                for unknown_arc in unknown_arcs:
                    ai=int(unknown_arc); unknown_case_sets[ai].add(case_tuple)
                    unknown_length_by_arc[ai] += lengths_by_arc[ai]
                    unknown_rows.append({"event_key":case_tuple[0],"scenario_key":case_tuple[1],"horizon_hours":case_tuple[2],
                        "member_id":case_tuple[3],"od_id":case_tuple[4],"arc_index":ai,"length_m":float(lengths_by_arc[ai])})
            route_rows.append({"event_key":str(snap.event_key),"scenario_key":str(snap.scenario_key),
                "horizon_hours":int(snap.horizon_hours),"valid_at_utc":str(snap.valid_at_utc),"member_id":int(snap.member_id),
                "od_id":pair["od_id"],"origin_osmid":pair["origin_osmid"],"destination_osmid":pair["destination_osmid"],
                "sampling_class":pair["sampling_class"],"sector":pair["sector"],"distance_band":pair["distance_band"],
                "baseline_status":"ASSESSED_ROUTE" if baseline_path is not None else "NO_ASSESSED_PATH",
                "baseline_arc_indices":bdetail["arc_indices"],"proposed_status":pdetail["status"],
                "proposed_arc_indices":pdetail["arc_indices"],"unknown_edge_count":pdetail["unknown_edge_count"],
                "proposed_edge_states":[STATE_NAMES[int(states[x])] for x in pdetail["arc_indices"]],
                "proposed_edge_reasons":[str(reasons[x]) for x in pdetail["arc_indices"]],
                "baseline_edge_states":[STATE_NAMES[int(states[x])] for x in bdetail["arc_indices"]],
                "baseline_edge_reasons":[str(reasons[x]) for x in bdetail["arc_indices"]],
                "unknown_arc_indices":[int(x) for x in pdetail["arc_indices"] if int(states[x]) in (0,4)],
                "unknown_distance_m":pdetail["unknown_distance_m"],"path_length_m":pdetail["path_length_m"],
                "assessed_edge_fraction":pdetail["assessed_edge_fraction"],"unknown_reasons":pdetail["unknown_reasons"],
                "baseline_equals_proposed":baseline_path==proposed if baseline_path is not None else None,
                "route_cost_seconds_assessed_only":pdetail.get("travel_time_seconds_assessed_edges_only"),
                "is_simulated_research_output":True})
            # Held-out truth is A08 member 20 only; unknown on any route arc makes the truth unavailable.
            if 1 <= int(snap.member_id) <= 19:
                truth_key=(str(snap.event_key),str(snap.scenario_key),int(snap.horizon_hours))
                if truth_key not in truth_state_cache:
                    truth_state_cache.clear()
                    truth_state_cache[truth_key]=edge_states(archive,19,hi,arcs,arcpos,order)[0]
                ts=truth_state_cache[truth_key]
                for method, path in (("fail_closed",baseline_path),("three_state",proposed)):
                    if path is None:
                        outcome="NO_SELECTED_ROUTE"; assessed_truth=False
                    else:
                        vals=ts[np.asarray(path,dtype=np.int64)]
                        if np.any(np.isin(vals,[0,4])):
                            outcome="UNKNOWN_TRUTH"; assessed_truth=False
                        else:
                            outcome="SIMULATED_BLOCKED" if np.any(vals==3) else "SIMULATED_PASSABLE_UNDER_A08_RULE"
                            assessed_truth=True
                    truth_rows.append({"event_key":str(snap.event_key),"scenario_key":str(snap.scenario_key),
                        "horizon_hours":int(snap.horizon_hours),"member_id":int(snap.member_id),"truth_member_id":20,
                        "od_id":pair["od_id"],"method":method,"outcome":outcome,"fully_assessed_truth":assessed_truth,
                        "path_edge_count":None if path is None else len(path)})
        stat_row={"event_key":str(snap.event_key),"scenario_key":str(snap.scenario_key),
            "horizon_hours":int(snap.horizon_hours),"member_id":int(snap.member_id),"directed_arc_count":len(arcs),
            "passable_count":scount["ASSESSED_PASSABLE"],"blocked_count":scount["ASSESSED_BLOCKED"],
            "unknown_count":scount["UNKNOWN"],"route_case_count":len(pairs)}
        snapshot_stats.append(stat_row)
        checkpoint.execute("INSERT INTO snapshots VALUES (?,?,?,?,?,?)",(snapshot_key_text,
            json.dumps(route_rows[route_start:],separators=(",",":")),json.dumps(coverage_rows[coverage_start:],separators=(",",":")),
            json.dumps(truth_rows[truth_start:],separators=(",",":")),json.dumps(stat_row,separators=(",",":")),
            json.dumps(unknown_rows,separators=(",",":"))))
        checkpoint.commit()
        print(f"route snapshots {si}/{len(snapshots)} elapsed={time.time()-started:.1f}s",flush=True)

    # Shelter choice stability from the saved A10 member/capacity cases, not a route recommendation.
    sums=alloc_detail.groupby(case_key+["candidate_osm_id"],dropna=False,as_index=False).allocated_people_model_estimate.sum()
    shelter_rows=[]
    for key, group in sums.groupby(case_key,dropna=False,sort=True):
        mx=group.allocated_people_model_estimate.max()
        top=group[group.allocated_people_model_estimate==mx].sort_values("candidate_osm_id",kind="stable") if mx>0 else group.iloc[0:0]
        ids_top=[int(x) for x in top.candidate_osm_id.dropna().tolist()]
        shelter_rows.append(dict(zip(case_key,key if isinstance(key,tuple) else (key,))) | {
            "selected_candidate_osm_id":ids_top[0] if ids_top else None,"top_tie_count":len(ids_top),
            "top_allocation_people_model_estimate":float(mx),"decision_made":bool(ids_top),
            "interpretation":"DESCRIPTIVE_MODELED_ALLOCATION_NOT_SHELTER_RECOMMENDATION"})
    selected_shelters=pd.DataFrame(shelter_rows)
    shelter_df=alloc_cases[case_key+["status","source_mode"]].merge(selected_shelters,on=case_key,how="left",validate="one_to_one")
    shelter_df["decision_made"]=shelter_df["decision_made"].fillna(False).astype(bool)
    shelter_df["top_tie_count"]=shelter_df["top_tie_count"].fillna(0).astype(int)
    shelter_comparisons=[]; shelter_changes=[]
    for keycols, baseline_desc in [(["event_key","scenario_key","horizon_hours","capacity_factor"],"member12_cf1"),
                                   (["event_key","horizon_hours","member_id","capacity_factor"],"perfect_foresight_scenario")]:
        # Scenario contrast is structurally unavailable because A10 records only perfect_foresight_imerg.
        if baseline_desc=="perfect_foresight_scenario":
            shelter_comparisons.append({"comparison":baseline_desc,"status":"UNAVAILABLE_SINGLE_SAVED_SCENARIO",
                                        "eligible_case_count":len(shelter_df),"decision_count":int(shelter_df.decision_made.sum())})
            continue
        lookup={(r.event_key,r.scenario_key,int(r.horizon_hours),int(r.member_id),float(r.capacity_factor)):r
                for r in shelter_df.itertuples(index=False)}
        n=ident=changed=ties=unmatched=0
        for r in shelter_df.itertuples(index=False):
            if float(r.capacity_factor)!=1.0 or (int(r.member_id)==12 and float(r.capacity_factor)==1.0): continue
            basekey=(r.event_key,r.scenario_key,int(r.horizon_hours),12,1.0)
            br=lookup.get(basekey)
            if br is None or not r.decision_made or not br.decision_made:
                unmatched+=1; continue
            n+=1; ties+=int(r.top_tie_count>1)
            if r.selected_candidate_osm_id==br.selected_candidate_osm_id: ident+=1
            else:
                changed+=1
                shelter_changes.append({"comparison":"MEMBER_VS_MEMBER12_CF1","event_key":r.event_key,
                    "scenario_key":r.scenario_key,"horizon_hours":int(r.horizon_hours),"member_id":int(r.member_id),
                    "capacity_factor":float(r.capacity_factor),"baseline_member_id":12,
                    "selected_candidate_osm_id":int(r.selected_candidate_osm_id),
                    "baseline_candidate_osm_id":int(br.selected_candidate_osm_id),
                    "selected_allocation_people_model_estimate":float(r.top_allocation_people_model_estimate),
                    "baseline_allocation_people_model_estimate":float(br.top_allocation_people_model_estimate),
                    "change_correlate":"member differs; event/scenario/horizon/capacity factor matched",
                    "recorded_condition":"A10 hypothetical capacity/demand allocation; not a shelter recommendation"})
        shelter_comparisons.append({"comparison":baseline_desc,"eligible_case_count":len(shelter_df),"matched_decisions":n,
            "identical_numerator":ident,"stability_denominator":n,"changed_numerator":changed,"change_denominator":n,
            "ties":ties,"unmatched_or_no_decision":unmatched})

    # Route stability for each fixed method against member 12 and matched PFI scenario.
    rdf=pd.DataFrame(route_rows)
    stability=[]
    key_member=["event_key","scenario_key","horizon_hours","od_id"]
    route_lookup={(r.event_key,r.scenario_key,int(r.horizon_hours),int(r.od_id),int(r.member_id)):r
                  for r in rdf.itertuples(index=False)}
    if len(route_lookup)!=len(rdf): raise RuntimeError("DUPLICATE_ROUTE_CASE_KEY")
    method_defs={"FAIL_CLOSED":"baseline_arc_indices","THREE_STATE":"proposed_arc_indices"}
    route_stability_member={}; route_stability_scenario={}
    pfi="perfect_foresight_imerg"
    scen_lookup={(r.event_key,int(r.horizon_hours),int(r.member_id),int(r.od_id),r.scenario_key):r
                 for r in rdf.itertuples(index=False)}
    for method,path_column in method_defs.items():
        matched=identical=changed=unmatched=0
        for r in rdf[rdf.member_id.between(1,19)].itertuples(index=False):
            if int(r.member_id)==12: continue
            b=route_lookup.get((r.event_key,r.scenario_key,int(r.horizon_hours),int(r.od_id),12))
            rpath=getattr(r,path_column); bpath=None if b is None else getattr(b,path_column)
            if b is None or not rpath or not bpath:
                unmatched+=1; continue
            matched+=1
            if rpath==bpath: identical+=1
            else:
                changed+=1
                stability.append({"method":method,"comparison":"MEMBER_VS_MEMBER12","event_key":r.event_key,
                    "scenario_key":r.scenario_key,"horizon_hours":int(r.horizon_hours),"od_id":int(r.od_id),
                    "member_id":int(r.member_id),"baseline_member_id":12,
                    "change_correlate":"member differs; event/scenario/horizon/OD matched",
                    "recorded_condition":"A08 saved ensemble; ordinary 0.30 m, tunnel proxy 0.15 m, bridges UNKNOWN",
                    "change_attribution":"MEMBER_ASSOCIATED_NOT_CAUSAL"})
        eligible=int((rdf.member_id.between(1,19)&(rdf.member_id!=12)).sum())
        decisions=int((rdf.member_id.between(1,19)&(rdf.member_id!=12)&rdf[path_column].map(bool)).sum())
        route_stability_member[method]={"eligible_member_decisions":eligible,"member_decisions_made":decisions,
            "scenario_count_coverage_numerator":decisions,"scenario_count_coverage_denominator":eligible,
            "matched_decisions":matched,"identical_numerator":identical,"stability_denominator":matched,
            "changed_numerator":changed,"change_denominator":matched,"unmatched_or_no_decision":unmatched}
        scenario_matched=scenario_changed=scenario_unmatched=0
        subset=rdf[(rdf.member_id.between(1,19))&(rdf.scenario_key!=pfi)]
        for r in subset.itertuples(index=False):
            b=scen_lookup.get((r.event_key,int(r.horizon_hours),int(r.member_id),int(r.od_id),pfi))
            rpath=getattr(r,path_column); bpath=None if b is None else getattr(b,path_column)
            if b is None or not rpath or not bpath:
                scenario_unmatched+=1; continue
            scenario_matched+=1
            if rpath!=bpath:
                scenario_changed+=1
                stability.append({"method":method,"comparison":"SCENARIO_VS_PFI","event_key":r.event_key,
                    "scenario_key":r.scenario_key,"horizon_hours":int(r.horizon_hours),"od_id":int(r.od_id),
                    "member_id":int(r.member_id),"baseline_scenario_key":pfi,
                    "change_correlate":f"scenario {r.scenario_key} vs {pfi}; event/horizon/member/OD matched",
                    "recorded_condition":"A05 saved scenario label; associated condition, not causal attribution",
                    "change_attribution":"SCENARIO_LABEL_ASSOCIATED_NOT_CAUSAL"})
        eligible=len(subset); decisions=int(subset[path_column].map(bool).sum())
        route_stability_scenario[method]={"eligible_member_comparisons":eligible,"decisions_made":decisions,
            "scenario_count_coverage_numerator":decisions,"scenario_count_coverage_denominator":eligible,
            "matched_decisions":scenario_matched,"identical_numerator":scenario_matched-scenario_changed,
            "stability_denominator":scenario_matched,"changed_numerator":scenario_changed,
            "change_denominator":scenario_matched,"unmatched_or_no_decision":scenario_unmatched}

    # Preserve the registered decision counts and denominators at event/scenario/horizon strata.
    stability_strata=[]
    for method,path_column in method_defs.items():
        member_subset=rdf[rdf.member_id.between(1,19)&(rdf.member_id!=12)]
        for (event,scenario,horizon),group in member_subset.groupby(["event_key","scenario_key","horizon_hours"],sort=True):
            eligible=len(group); decisions=0; matched=identical=changed=unmatched=0
            for r in group.itertuples(index=False):
                rp=getattr(r,path_column); decisions+=int(bool(rp))
                b=route_lookup.get((event,scenario,int(horizon),int(r.od_id),12))
                bp=None if b is None else getattr(b,path_column)
                if not rp or not bp: unmatched+=1; continue
                matched+=1
                if rp==bp: identical+=1
                else: changed+=1
            stability_strata.append({"decision_type":"ROUTE","method":method,"comparison":"MEMBER_VS_MEMBER12",
                "event_key":event,"scenario_key":scenario,"horizon_hours":int(horizon),"capacity_factor":None,
                "eligible_case_count":eligible,"decision_count":decisions,"matched_decisions":matched,
                "identical_numerator":identical,"stability_denominator":matched,"changed_numerator":changed,
                "change_denominator":matched,"tie_case_count":0,"tie_note":"Deterministic arc-index sequence resolves equal-cost paths; residual path-choice ties not enumerated.",
                "unmatched_or_no_decision":unmatched})
        scenario_subset=rdf[rdf.member_id.between(1,19)&(rdf.scenario_key!=pfi)]
        for (event,scenario,horizon),group in scenario_subset.groupby(["event_key","scenario_key","horizon_hours"],sort=True):
            eligible=len(group); decisions=0; matched=identical=changed=unmatched=0
            for r in group.itertuples(index=False):
                rp=getattr(r,path_column); decisions+=int(bool(rp))
                b=scen_lookup.get((event,int(horizon),int(r.member_id),int(r.od_id),pfi))
                bp=None if b is None else getattr(b,path_column)
                if not rp or not bp: unmatched+=1; continue
                matched+=1
                if rp==bp: identical+=1
                else: changed+=1
            stability_strata.append({"decision_type":"ROUTE","method":method,"comparison":"SCENARIO_VS_PFI",
                "event_key":event,"scenario_key":scenario,"horizon_hours":int(horizon),"capacity_factor":None,
                "eligible_case_count":eligible,"decision_count":decisions,"matched_decisions":matched,
                "identical_numerator":identical,"stability_denominator":matched,"changed_numerator":changed,
                "change_denominator":matched,"tie_case_count":0,
                "tie_note":"Deterministic arc-index sequence resolves equal-cost paths; residual path-choice ties not enumerated.",
                "unmatched_or_no_decision":unmatched})
    nominal_shelters=shelter_df[shelter_df.capacity_factor==1.0]
    shelter_lookup={(r.event_key,r.scenario_key,int(r.horizon_hours),int(r.member_id),float(r.capacity_factor)):r
                    for r in nominal_shelters.itertuples(index=False)}
    for (event,scenario,horizon),group in nominal_shelters[nominal_shelters.member_id!=12].groupby(
            ["event_key","scenario_key","horizon_hours"],sort=True):
        eligible=len(group); decisions=int(group.decision_made.sum()); matched=identical=changed=unmatched=0
        for r in group.itertuples(index=False):
            b=shelter_lookup.get((event,scenario,int(horizon),12,1.0))
            if not r.decision_made or b is None or not b.decision_made: unmatched+=1; continue
            matched+=1
            if r.selected_candidate_osm_id==b.selected_candidate_osm_id: identical+=1
            else: changed+=1
        stability_strata.append({"decision_type":"SHELTER_ALLOCATION_CANDIDATE","method":"A10_SAVED_ALLOCATION",
            "comparison":"MEMBER_VS_MEMBER12_CF1","event_key":event,"scenario_key":scenario,
            "horizon_hours":int(horizon),"capacity_factor":1.0,"eligible_case_count":eligible,"decision_count":decisions,
            "matched_decisions":matched,"identical_numerator":identical,"stability_denominator":matched,
            "changed_numerator":changed,"change_denominator":matched,
            "tie_case_count":int((group.top_tie_count>1).sum()),"tie_note":"Lowest numeric OSM ID represents equal top allocation; tie counts retained.",
            "unmatched_or_no_decision":unmatched})
    for (event,horizon),group in nominal_shelters.groupby(["event_key","horizon_hours"],sort=True):
        stability_strata.append({"decision_type":"SHELTER_ALLOCATION_CANDIDATE","method":"A10_SAVED_ALLOCATION",
            "comparison":"SCENARIO_VS_PFI","event_key":event,"scenario_key":pfi,"horizon_hours":int(horizon),
            "capacity_factor":1.0,"status":"UNAVAILABLE_SINGLE_SAVED_SCENARIO","eligible_case_count":0,
            "decision_count":0,"matched_decisions":0,"identical_numerator":None,"stability_denominator":0,
            "changed_numerator":None,"change_denominator":0,"tie_case_count":None,
            "tie_note":"A10 saved only the perfect-foresight scenario; no contrast exists.","unmatched_or_no_decision":0})

    # Unknown-road verification queue: count distinct conditional cases traversing each arc.
    exposure=unknown_case_sets; unknown_len=unknown_length_by_arc
    rank=greedy_unknown_edge_priority(exposure,unknown_len)
    priority=[]
    for rank_i,ai in enumerate(rank,1):
        row=by_arc.loc[ai]
        priority.append({"rank":rank_i,"arc_index":int(ai),"source_osmid":int(row.source_osmid),
            "from_node":int(row.from_node),"to_node":int(row.to_node),"distinct_conditional_cases":len(exposure[ai]),
            "unknown_distance_contribution_m_sum":unknown_len[ai],"verification_only":True})
    budgets=[]
    for budget in (1,5,10,25,50,100):
        chosen=set(rank[:budget]); covered=set()
        for ai in chosen: covered |= exposure[ai]
        budgets.append({"edge_budget":budget,"conditional_case_count_covered":len(covered),
                        "conditional_case_denominator":int((rdf.proposed_status=="CONDITIONAL_NEEDS_VERIFICATION").sum())})

    pd.DataFrame(pairs).drop(columns=["static_shortest_arc_indices"]).to_parquet(OUT/"sampled_od_pairs.parquet",index=False)
    # Keep reference route edge ids in separate explicit file for coverage audit.
    pd.DataFrame([{"od_id":p["od_id"],"static_shortest_arc_indices":p["static_shortest_arc_indices"]} for p in pairs]).to_parquet(OUT/"static_reference_paths.parquet",index=False)
    rdf.to_parquet(OUT/"route_cases.parquet",index=False)
    pd.DataFrame(coverage_rows).to_parquet(OUT/"coverage_cases.parquet",index=False)
    pd.DataFrame(truth_rows).to_parquet(OUT/"heldout_member20_osse.parquet",index=False)
    pd.DataFrame(snapshot_stats).to_parquet(OUT/"snapshot_edge_counts.parquet",index=False)
    pd.DataFrame(priority).to_parquet(OUT/"unknown_verification_priority.parquet",index=False)
    pd.DataFrame(budgets).to_parquet(OUT/"verification_budget_coverage.parquet",index=False)
    shelter_df.to_parquet(OUT/"shelter_choice_by_case.parquet",index=False)
    pd.DataFrame(stability).to_parquet(OUT/"route_choice_changes.parquet",index=False)
    pd.DataFrame(stability_strata).to_parquet(OUT/"decision_stability_by_stratum.parquet",index=False)
    pd.DataFrame(shelter_changes).to_parquet(OUT/"shelter_choice_changes.parquet",index=False)
    # A09 comparison is constrained to exact saved OD/event/horizon/method keys and is never widened.
    a09=[json.loads(x) for x in A09_PATH.read_text(encoding="utf-8").splitlines() if x.strip()]
    sampled={(p["origin_osmid"],p["destination_osmid"]) for p in pairs}
    a09match=[r for r in a09 if (int(str(r.get("origin_id","")).split(":")[-1]),int(str(r.get("destination_id","")).split(":")[-1])) in sampled
              and str(r.get("scenario_key","")).split("/")[-1] in SCENARIOS
              and int(r.get("requested_horizon_seconds",-1)) in {21600,86400,259200}]
    # Summary denominators and explicit absent comparisons.
    scount=Counter(rdf.proposed_status)
    basecount=Counter(rdf.baseline_status)
    coverage_count=Counter(pd.DataFrame(coverage_rows).coverage_class_on_static_reference_path)
    truthdf=pd.DataFrame(truth_rows)
    tsummary={method:{status:int(count) for status,count in grp.outcome.value_counts().items()}
              for method,grp in truthdf.groupby("method")} if len(truthdf) else {}
    nominal=shelter_df[shelter_df.capacity_factor==1.0]
    a10_missing={}
    for col in ["unknown_demand_cells","population_nodata_30m_cells"]:
        vals=alloc_cases[col].astype(float)
        a10_missing[col]={"explicit_positive_case_count":int((vals>0).sum()),"eligible_case_count":int(len(vals)),
                          "null_metadata_case_count":int(vals.isna().sum()),
                          "recorded_total_across_nonnull_cases":float(vals.sum(min_count=1))}
    unknown_input_priority=[]
    route_case_denominator=int((rdf.proposed_status=="CONDITIONAL_NEEDS_VERIFICATION").sum())
    for edge in priority:
        unknown_input_priority.append({"input_type":"ROAD_EDGE","input_key":str(edge["arc_index"]),
            "affected_decision_count":int(edge["distinct_conditional_cases"]),"decision_denominator":route_case_denominator,
            "count_method":"distinct conditional OD/event/scenario/horizon/member cases traversing this edge"})
    for key,values in a10_missing.items():
        unknown_input_priority.append({"input_type":"A10_RECORDED_MISSING_INPUT","input_key":key,
            "affected_decision_count":values["explicit_positive_case_count"],"decision_denominator":values["eligible_case_count"],
            "count_method":"saved allocation cases with an explicit positive missing-input field; not probability"})
    unknown_input_priority.sort(key=lambda x:(-x["affected_decision_count"],x["input_type"],x["input_key"]))
    for i,row in enumerate(unknown_input_priority,1): row["count_rank"]=i
    pd.DataFrame(unknown_input_priority).to_parquet(OUT/"unknown_input_decision_priority.parquet",index=False)
    shelter_summary={
        "saved_case_count":len(shelter_df),"decisions_made":int(shelter_df.decision_made.sum()),
        "no_decision":int((~shelter_df.decision_made).sum()),"tie_case_count":int((shelter_df.top_tie_count>1).sum()),
        "nominal_capacity_factor_1_eligible_cases":int(len(nominal)),
        "nominal_capacity_factor_1_decisions":int(nominal.decision_made.sum()),
        "non_nominal_capacity_cases_context_only":int((shelter_df.capacity_factor!=1.0).sum()),
        "member12_comparison":shelter_comparisons[0],"scenario_comparison":shelter_comparisons[1],
        "limitation":"A10 saved only perfect_foresight_imerg; no cross-scenario shelter comparison is available."}
    conditional_pool.shutdown(wait=True)
    summary={"analysis_version":"A21-three-state-v1","source_mode":"SIMULATED_OSSE_ONLY",
      "created_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"input_hashes":hashes,
      "preregistration_sha256":sha256(PREREG),"analysis_script_sha256":sha256(Path(__file__).resolve()),
      "sampling":{"seed":SEED,"primary_od_count":primary_count,"supplement_count":len(supplement),
        "unique_directed_primary_pairs":len({(p['origin_osmid'],p['destination_osmid']) for p in selected}),"coverage_by_class":dict(coverage_count)},
      "route_cases":{"eligible_cases":len(rdf),"expected_primary_cases":primary_count*900,
        "baseline_status_counts":dict(basecount),"proposed_status_counts":dict(scount),
        "conditional_share_of_eligible_cases":float(scount["CONDITIONAL_NEEDS_VERIFICATION"]/len(rdf)) if len(rdf) else None,
        "no_path_share_of_eligible_cases":float(scount["NO_PATH"]/len(rdf)) if len(rdf) else None,
        "route_change_when_baseline_exists":int((rdf.baseline_equals_proposed==False).sum()),
        "a09_saved_rows":len(a09),"a09_exact_sampled_od_rows":len(a09match),
        "a09_note":"A09 run_id is null and its six saved probes are not a full member×scenario×horizon baseline; only exact sampled OD pairs are matchable."},
      "heldout_member20_osse":tsummary,"route_decision_stability":{"member_vs_member12":route_stability_member,
        "scenario_vs_perfect_foresight":route_stability_scenario,"shelters":shelter_summary,
        "shelter_choice_change_rows":len(shelter_changes),"explicit_A10_missing_inputs":a10_missing},
      "verification_budget":budgets,"unknown_priority_edge_count":len(priority),
      "compute":{"cpu_worker_threads":worker_count,"gpu":False,"torch_version":__import__('torch').__version__,
             "cuda_available":bool(__import__('torch').cuda.is_available()),
             "used":False,"compute":"CPU SciPy sparse graph algorithms; CUDA unavailable and graph operation CPU-bound in accepted implementation."},
      "runtime_seconds":time.time()-started,
      "limits":["No observed closures, route outcomes, or date-matched depth truth.",
        "A08 depth and edge speed/closure rules are assumption-based; bridge edges remain UNKNOWN.",
        "Shelter candidates and capacities are modeled; no shelter recommendation.",
        "UNKNOWN is not traversed as passable; any conditional route requires field verification.",
        "No operational guidance, route safety claim, or validated hydraulic truth."]}
    (OUT/"run_summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False),encoding="utf-8")
    output_hashes={p.relative_to(OUT).as_posix():sha256(p) for p in sorted(OUT.rglob("*")) if p.is_file()}
    manifest={"analysis_version":"A21-three-state-v1","preregistration_sha256":sha256(PREREG),
        "analysis_script_sha256":sha256(Path(__file__).resolve()),"source_hashes":hashes,
        "output_hashes_before_manifest":output_hashes,"note":"Hashes cover every data artifact and run_summary; manifest self-hash is intentionally not embedded."}
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    checkpoint.close()
    # Re-read immutable sources after writing and stop if any changed during this run.
    if verify_registered_inputs()!=hashes:
        raise RuntimeError("SOURCE_HASH_CHANGED_DURING_A21_RUN")
    print(json.dumps({"primary_pairs":primary_count,"supplement":len(supplement),"route_cases":len(rdf),
      "baseline":dict(basecount),"proposed":dict(scount),"coverage":dict(coverage_count),
      "summary":str((OUT/'run_summary.json').relative_to(ROOT)),"elapsed_seconds":time.time()-started},indent=2),flush=True)


if __name__ == "__main__":
    main()
