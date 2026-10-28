"""A10 coarse, simulated shelter-capacity allocation (not evacuation guidance)."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pyogrio
from scipy.spatial import cKDTree
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "data/features/decision/shelters/batch2_v3"
OSM = ROOT / "data/features/osm/chennai_osm_features.gpkg"
GRAPH = ROOT / "data/features/routing/time_dependent_batch2"
SEED = 20261028
EVENTS = ("2015-12-02", "2021-11-13", "2023-12-04")
HORIZONS = (6, 24, 72)
SCENARIO = "perfect_foresight_imerg"
DEFAULT_CAPACITY = {"shelter": 100.0, "school": 250.0, "college": 500.0}
CAPACITY_FACTORS = (0.5, 1.0, 2.0)
OPEN, REDUCED, BLOCKED = 1, 2, 3


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def allocate_by_component(
    demand: np.ndarray,
    origin_component: np.ndarray,
    origin_xy: np.ndarray,
    candidate_component: np.ndarray,
    candidate_xy: np.ndarray,
    candidate_capacity: np.ndarray,
) -> dict:
    """Greedy nearest snapped-node allocation inside weakly connected components."""
    demand = np.array(demand, dtype=np.float64, copy=True)
    unknown_demand_count = int((~np.isfinite(demand)).sum())
    valid_demand = np.isfinite(demand) & (demand > 0)
    available = np.isfinite(candidate_capacity) & (candidate_capacity > 0) & (candidate_component >= 0)
    demand_ix = np.flatnonzero(valid_demand)
    candidate_ix = np.flatnonzero(available)
    capacity_left = np.where(available, candidate_capacity, 0.0).astype(np.float64)
    served = np.zeros_like(demand)
    assigned_facilities = np.zeros(len(candidate_capacity), dtype=np.float64)
    allocation_rows: list[tuple[int, int, float]] = []
    if not len(demand_ix) or not len(candidate_ix):
        # With no candidate capacity, no origin can reach a usable candidate.
        unreachable = valid_demand
        return {"served": served, "capacity_used": assigned_facilities,
                "unserved_demand": float(np.nansum(demand[valid_demand])),
                "unserved_reachable_demand": 0.0,
                "known_demand": float(np.nansum(demand[np.isfinite(demand)])),
                "unknown_demand_cells": unknown_demand_count,
                "reachable_demand_cells": 0, "unreachable_demand": float(np.nansum(demand[unreachable])),
                "allocation_pairs": 0, "allocation_rows": allocation_rows}
    comp_to_candidates: dict[int, np.ndarray] = {}
    for comp in np.unique(candidate_component[candidate_ix]):
        comp_to_candidates[int(comp)] = candidate_ix[candidate_component[candidate_ix] == comp]
    pair_origins: list[np.ndarray] = []
    pair_candidates: list[np.ndarray] = []
    pair_distances: list[np.ndarray] = []
    reachable_demand = np.zeros(len(demand), dtype=bool)
    for comp, cand in comp_to_candidates.items():
        ori = demand_ix[(origin_component[demand_ix] >= 0) & (origin_component[demand_ix] == comp)]
        if not len(ori):
            continue
        delta = origin_xy[ori, None, :] - candidate_xy[cand][None, :, :]
        dist = np.sqrt(np.sum(delta * delta, axis=2))
        oi, ci = np.indices(dist.shape)
        pair_origins.append(ori[oi.ravel()])
        pair_candidates.append(cand[ci.ravel()])
        pair_distances.append(dist.ravel())
        reachable_demand[ori] = True
    if pair_distances:
        oi = np.concatenate(pair_origins)
        ci = np.concatenate(pair_candidates)
        dd = np.concatenate(pair_distances)
        # Stable tie-breaking on grid/facility row index makes the run deterministic.
        order = np.lexsort((ci, oi, dd))
        for k in order:
            o, c = int(oi[k]), int(ci[k])
            if demand[o] <= 0 or capacity_left[c] <= 0:
                continue
            take = min(float(demand[o]), float(capacity_left[c]))
            served[o] += take
            capacity_left[c] -= take
            assigned_facilities[c] += take
            demand[o] -= take
            allocation_rows.append((o, c, take))
    # demand is mutated only in its local numpy copy above; account served total as total-known minus remaining.
    known_demand = float(np.nansum(np.asarray(demand, dtype=np.float64) + served))
    remaining = np.asarray(demand, dtype=np.float64)
    remaining[~np.isfinite(remaining)] = 0
    unserved = float(np.maximum(remaining, 0).sum())
    unreachable_mask = valid_demand & ~reachable_demand
    unreachable_demand = float(np.maximum(np.asarray(demand)[unreachable_mask], 0).sum())
    unserved_reachable = unserved - unreachable_demand
    if unserved_reachable < -1e-7:
        raise ValueError("unreachable unserved demand exceeds total unserved demand")
    return {"served": served, "capacity_used": assigned_facilities,
            "unserved_demand": unserved,
            "unserved_reachable_demand": max(0.0, unserved_reachable),
            "known_demand": known_demand,
            "unknown_demand_cells": unknown_demand_count,
            "reachable_demand_cells": int(reachable_demand.sum()),
            "unreachable_demand": unreachable_demand,
            "allocation_pairs": int(sum(len(x) for x in pair_distances)),
            "allocation_rows": allocation_rows}


def _network_inputs(a06_data):
    nodes = pyogrio.read_dataframe(OSM, layer="road_nodes", columns=["osmid", "geometry"])
    node_xy = np.column_stack([nodes.geometry.x.to_numpy(), nodes.geometry.y.to_numpy()])
    tree = cKDTree(node_xy)
    facilities = pyogrio.read_dataframe(OSM, layer="facilities", columns=["osmid", "category", "name", "geometry"])
    cats = facilities.category.fillna("").astype(str).str.lower().to_numpy()
    keep = np.isin(cats, ["shelter", "school", "college"])
    facilities = facilities.loc[keep].copy().reset_index(drop=True)
    cats = cats[keep]
    active = np.asarray(a06_data["eligible"], dtype=bool)
    transform = a06_data["transform"]
    facility_xy = np.column_stack([facilities.geometry.x.to_numpy(), facilities.geometry.y.to_numpy()])
    height, width = active.shape
    fcol = np.floor((facility_xy[:, 0] - transform.c) / transform.a).astype(np.int64)
    frow = np.floor((facility_xy[:, 1] - transform.f) / transform.e).astype(np.int64)
    f_in = (frow >= 0) & (frow < height) & (fcol >= 0) & (fcol < width)
    f_active = np.zeros(len(facilities), dtype=bool)
    f_active[f_in] = active[frow[f_in], fcol[f_in]]
    facilities = facilities.loc[f_active].copy().reset_index(drop=True)
    cats = cats[f_active]
    facility_xy = facility_xy[f_active]
    nearest_facility_distance, facility_node_index = tree.query(facility_xy, k=1)
    facilities["facility_type"] = cats
    facilities["snapped_node_osmid"] = nodes.osmid.to_numpy()[facility_node_index]
    facilities["snap_distance_m"] = nearest_facility_distance
    facilities["assumed_capacity_people"] = [DEFAULT_CAPACITY[c] for c in cats]

    height, width = active.shape
    rows, cols = np.indices((height, width))
    xx = transform.c + (cols + 0.5) * transform.a
    yy = transform.f + (rows + 0.5) * transform.e
    grid_xy = np.column_stack([xx[active], yy[active]])
    pop_table = pq.read_table(ROOT / "data/features/static/cell_table.parquet",
                              columns=["x", "y", "worldpop_2021", "population_is_nodata"])
    px = pop_table["x"].to_numpy(zero_copy_only=False)
    py = pop_table["y"].to_numpy(zero_copy_only=False)
    pv = pop_table["worldpop_2021"].to_numpy(zero_copy_only=False).astype(np.float64)
    pn = pop_table["population_is_nodata"].to_numpy(zero_copy_only=False).astype(bool) | ~np.isfinite(pv)
    # Assign 30 m cell centres to 600 m model cells using the same A06 transform.
    pc = np.floor((px - transform.c) / transform.a).astype(np.int64)
    pr = np.floor((py - transform.f) / transform.e).astype(np.int64)
    inside = (pr >= 0) & (pr < height) & (pc >= 0) & (pc < width)
    pcell = np.full(len(px), -1, dtype=np.int64)
    pcell[inside] = pr[inside] * width + pc[inside]
    active_flat = active.ravel()
    mapped = np.zeros(len(pcell), dtype=bool)
    in_grid = pcell >= 0
    mapped[in_grid] = active_flat[pcell[in_grid]]
    known = mapped & ~pn
    unknown = mapped & pn
    pop = np.bincount(pcell[known], weights=pv[known], minlength=height * width).astype(np.float64)
    known_count = np.bincount(pcell[known], minlength=height * width)
    nodata_count = np.bincount(pcell[unknown], minlength=height * width)
    pop = pop.reshape(height, width)
    known_count = known_count.reshape(height, width)
    nodata_count = nodata_count.reshape(height, width)
    pop[(known_count == 0) & ((nodata_count > 0) | (known_count + nodata_count == 0))] = np.nan
    demand = pop[active]
    nodata_sources = nodata_count[active]
    origin_dist, origin_nodes = tree.query(grid_xy, k=1)
    return {"nodes": nodes, "node_xy": node_xy, "node_tree": tree,
            "facilities": facilities, "facility_xy": facility_xy,
            "facility_node_index": facility_node_index, "facility_snap_distance_m": nearest_facility_distance,
            "facility_snapped_xy": node_xy[facility_node_index],
            "facility_cap": facilities.assumed_capacity_people.to_numpy(np.float64),
            "grid_xy": grid_xy, "origin_node_index": origin_nodes,
            "origin_snapped_xy": node_xy[origin_nodes],
            "origin_snap_distance_m": origin_dist, "demand": demand,
            "population_nodata_source_cells": nodata_sources,
            "active": active, "grid_shape": active.shape,
            "source_rows": int(pop_table.num_rows),
            "known_population_sum": float(np.nansum(demand)),
            "known_30m_cells_mapped": int(known.sum()),
            "nodata_30m_cells_mapped": int(unknown.sum())}


def _case_graph(arcs: pd.DataFrame, cell_ids: np.ndarray, cell_pos: dict[int, int],
                states: np.ndarray, horizon_idx: int, member_idx: int, node_pos: dict[int, int], n_nodes: int):
    arc_cells = arcs.grid_cell_id.to_numpy(np.int64)
    cellix = np.fromiter((cell_pos.get(int(x), -1) for x in arc_cells), dtype=np.int32, count=len(arc_cells))
    structure = arcs.structure_class.astype(str).to_numpy()
    st = np.full(len(arcs), 0, dtype=np.uint8)
    mapped = cellix >= 0
    for cls, field in [("ordinary", "ordinary_state"), ("tunnel_underpass_proxy", "tunnel_state"),
                       ("bridge", "bridge_state"), ("bridge_and_tunnel", "bridge_state")]:
        ix = mapped & (structure == cls)
        if ix.any():
            st[ix] = states[field][member_idx, horizon_idx, cellix[ix]]
    # Access components are only a weak-connectivity screen. Missing and structural unknown edges do not connect.
    open_arc = (st == OPEN) | (st == REDUCED)
    src = np.array([node_pos[int(n)] for n in arcs.from_node.to_numpy()], dtype=np.int32)
    dst = np.array([node_pos[int(n)] for n in arcs.to_node.to_numpy()], dtype=np.int32)
    mat = csr_matrix((np.ones(int(open_arc.sum()), dtype=np.uint8), (src[open_arc], dst[open_arc])), shape=(n_nodes, n_nodes))
    ncomp, labels = connected_components(mat, directed=True, connection="weak", return_labels=True)
    return labels, {"weak_component_count": int(ncomp), "assessed_open_or_reduced_directed_arcs": int(open_arc.sum()),
                    "blocked_directed_arcs": int((st == BLOCKED).sum()),
                    "unknown_or_unassessed_directed_arcs": int((~np.isin(st, [OPEN, REDUCED, BLOCKED])).sum())}


def run(out: Path = OUTPUT) -> dict:
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output folder: {out}")
    start = time.perf_counter()
    sys.path.insert(0, str(ROOT))
    from pipelines.phase12 import simulate as a06
    a06_data = a06.load_static()
    network = _network_inputs(a06_data)
    arcs = pq.read_table(GRAPH / "directed_arcs.parquet").to_pandas()
    node_ids = np.unique(np.concatenate([arcs.from_node.to_numpy(np.int64), arcs.to_node.to_numpy(np.int64)]))
    node_pos = {int(x): i for i, x in enumerate(node_ids)}
    cell_rows = []
    snapshots = []
    output_cases = []
    allocation_detail = []
    active_cell_ids = np.flatnonzero(network["active"].ravel()).astype(np.int64)
    candidate_osm_ids = network["facilities"].osmid.to_numpy()
    for event in EVENTS:
        archive = GRAPH / f"{event}_{SCENARIO}_snapshots.npz"
        with np.load(archive, allow_pickle=False) as z:
            cells = z["grid_cell_ids"].astype(np.int64)
            cell_pos = {int(c): i for i, c in enumerate(cells)}
            horizons = list(map(int, z["horizons_hours"]))
            for horizon in HORIZONS:
                hi = horizons.index(horizon)
                for mi, member_id in enumerate(z["member_ids"].astype(int)):
                    labels, graph_counts = _case_graph(arcs, cells, cell_pos,
                                                       {k: z[k] for k in ("ordinary_state", "tunnel_state", "bridge_state")},
                                                       hi, mi, node_pos, len(node_ids))
                    origin_node_ix = network["origin_node_index"]
                    candidate_node_ix = network["facility_node_index"]
                    origin_component = labels[origin_node_ix]
                    candidate_component = labels[candidate_node_ix]
                    for factor in CAPACITY_FACTORS:
                        result = allocate_by_component(network["demand"].copy(), origin_component,
                                                       network["grid_xy"], candidate_component,
                                                       network["facility_xy"], network["facility_cap"] * factor)
                        record = {"event_key": event, "scenario_key": SCENARIO,
                                  "horizon_hours": horizon, "valid_at_utc": str(z["valid_at_utc"][hi]),
                                  "member_id": int(member_id), "capacity_factor": factor,
                                  "status": "SIMULATED_COARSE_COMPONENT_ALLOCATION",
                                  "source_mode": "SIMULATED", "known_demand_people_model_estimate": result["known_demand"],
                                  "unserved_demand_people_model_estimate": result["unserved_demand"],
                                  "served_demand_people_model_estimate": float(result["served"].sum()),
                                  "unserved_reachable_people_model_estimate": result["unserved_reachable_demand"],
                                  "unreachable_component_people_model_estimate": result["unreachable_demand"],
                                  "unknown_demand_cells": result["unknown_demand_cells"],
                                  "population_nodata_30m_cells": int(network["population_nodata_source_cells"].sum()),
                                  "capacity_people": float((network["facility_cap"] * factor).sum()),
                                  "capacity_used_people": float(result["capacity_used"].sum()),
                                  "candidate_count": int(len(network["facilities"])),
                                  "active_candidates_in_component": int((candidate_component >= 0).sum()),
                                  "reachable_demand_cells": result["reachable_demand_cells"],
                                  "component_count": graph_counts["weak_component_count"],
                                  "assessed_open_or_reduced_directed_arcs": graph_counts["assessed_open_or_reduced_directed_arcs"],
                                  "blocked_directed_arcs": graph_counts["blocked_directed_arcs"],
                                  "unknown_or_unassessed_directed_arcs": graph_counts["unknown_or_unassessed_directed_arcs"],
                                  "qc_flags": ["CAPACITY_ASSUMPTION", "WEAK_COMPONENT_NOT_ROUTING", "COARSE_600M_GRID",
                                               "WORLDPOP_MODEL_ESTIMATE", "NODATA_NOT_ZERO", "SIMULATION_MEMBER_NOT_OBSERVATION"]}
                        output_cases.append(record)
                        snapshots.append({**record, "allocation_pairs": result["allocation_pairs"]})
                        for origin_ix, candidate_ix, allocated_people in result["allocation_rows"]:
                            allocation_detail.append({
                                "event_key": event, "scenario_key": SCENARIO,
                                "horizon_hours": horizon, "valid_at_utc": str(z["valid_at_utc"][hi]),
                                "member_id": int(member_id), "capacity_factor": factor,
                                "grid_cell_id": int(active_cell_ids[origin_ix]),
                                "candidate_osm_id": int(candidate_osm_ids[candidate_ix]),
                                "allocated_people_model_estimate": float(allocated_people),
                                "allocation_distance_between_snapped_nodes_m": float(np.linalg.norm(
                                    network["origin_snapped_xy"][origin_ix] - network["facility_snapped_xy"][candidate_ix])),
                                "access_method": "weak-component screen plus planar snapped-node distance",
                                "qc": "SIMULATED_ASSUMPTION_BASED_NOT_ROUTING"})
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(output_cases).to_parquet(out / "allocation_cases.parquet", index=False)
    pd.DataFrame(snapshots).to_csv(out / "allocation_cases.csv", index=False, lineterminator="\n")
    pd.DataFrame(allocation_detail).to_parquet(out / "allocation_detail.parquet", index=False)
    facility_out = network["facilities"].copy()
    facility_out["candidate_id"] = [f"osm:{x}" for x in facility_out.osmid]
    facility_out.drop(columns="geometry").to_parquet(out / "candidate_facilities.parquet", index=False)
    input_paths = [OSM, GRAPH / "run_summary.json", GRAPH / "directed_arcs.parquet",
                   ROOT / "data/features/static/cell_table.parquet",
                   ROOT / "data/features/forecast/batch2_v1/forecast_summary.json"]
    summary = {"task": "A10 shelter capacity allocation", "status": "SIMULATED_RESEARCH_OUTPUT_NOT_OPERATIONAL",
               "generated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(), "seed": SEED,
               "grid": {"resolution_m": 600, "crs": str(a06_data["crs"]), "eligible_cell_count": int(network["active"].sum())},
               "candidate_counts": network["facilities"].facility_type.value_counts().to_dict(),
               "capacity_assumptions_people": DEFAULT_CAPACITY, "capacity_factors": list(CAPACITY_FACTORS),
               "known_population_model_estimate": network["known_population_sum"],
               "mapped_worldpop_30m_cells": network["known_30m_cells_mapped"],
               "nodata_worldpop_30m_cells": network["nodata_30m_cells_mapped"],
               "road_graph_nodes": int(len(node_ids)), "road_graph_directed_arcs": int(len(arcs)),
               "facility_snap_distance_m": {"median": float(np.median(network["facility_snap_distance_m"])),
                                            "p95": float(np.percentile(network["facility_snap_distance_m"],95)),
                                            "max": float(np.max(network["facility_snap_distance_m"]))},
               "demand_snap_distance_m": {"median": float(np.median(network["origin_snap_distance_m"])),
                                          "p95": float(np.percentile(network["origin_snap_distance_m"],95)),
                                          "max": float(np.max(network["origin_snap_distance_m"]))},
               "case_count": len(output_cases), "allocation_detail_rows": len(allocation_detail),
               "outputs": ["allocation_cases.parquet", "allocation_cases.csv", "allocation_detail.parquet", "candidate_facilities.parquet"],
               "input_sha256": {str(p.relative_to(ROOT)).replace("\\","/"): sha256(p) for p in input_paths},
               "runtime_seconds": round(time.perf_counter()-start,3),
               "limitations": ["The weak-component screen is not direction-aware routing or travel-time accessibility.",
                               "Candidate capacities are hypothetical assumptions, not verified capacity or operation.",
                               "Allocation is greedy on planar distances between snapped graph nodes within a coarse weak component.",
                               "WorldPop values are model estimates; NoData remains distinct and is not zero.",
                               "A05/A06/A08 are hindcast/simulation products; no safe evacuation or emergency guidance claim."]}
    (out / "run_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    return summary


def verify(out: Path = OUTPUT) -> dict:
    import pyarrow.parquet as pq
    table = pq.read_table(out / "allocation_cases.parquet")
    df = table.to_pandas()
    if len(df) != 540:
        raise ValueError(f"expected 540 event/horizon/member/capacity cases, got {len(df)}")
    if (df.served_demand_people_model_estimate > df.known_demand_people_model_estimate + 1e-6).any():
        raise ValueError("served population exceeds known demand")
    if not np.allclose(
        df.served_demand_people_model_estimate + df.unserved_demand_people_model_estimate,
        df.known_demand_people_model_estimate,
        atol=1e-5,
    ):
        raise ValueError("served plus unserved does not reconcile to known demand")
    if not np.allclose(
        df.unserved_reachable_people_model_estimate + df.unreachable_component_people_model_estimate,
        df.unserved_demand_people_model_estimate,
        atol=1e-5,
    ):
        raise ValueError("reachable and unreachable unserved demand do not reconcile")
    if (df.capacity_used_people > df.capacity_people + 1e-6).any():
        raise ValueError("allocated population exceeds assumed capacity")
    if not (df.qc_flags.map(lambda v: "NODATA_NOT_ZERO" in v)).all():
        raise ValueError("NoData caveat flag missing")
    if not (df.status == "SIMULATED_COARSE_COMPONENT_ALLOCATION").all():
        raise ValueError("simulated result label missing")
    detail = pq.read_table(out / "allocation_detail.parquet").to_pandas()
    if (detail.allocated_people_model_estimate <= 0).any():
        raise ValueError("non-positive allocation detail row")
    sums = detail.groupby(["event_key", "horizon_hours", "member_id", "capacity_factor"]).allocated_people_model_estimate.sum()
    expected = df.set_index(["event_key", "horizon_hours", "member_id", "capacity_factor"]).served_demand_people_model_estimate
    if not np.allclose(sums.reindex(expected.index, fill_value=0).to_numpy(), expected.to_numpy(), atol=1e-5):
        raise ValueError("allocation detail does not reconcile with case-level served totals")
    return {"case_count": len(df), "allocation_detail_rows": len(detail),
            "capacity_constraints": "PASS", "allocation_reconciliation": "PASS",
            "simulation_and_nodata_flags": "PASS"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--verify-only", action="store_true")
    a = p.parse_args()
    print(json.dumps(verify() if a.verify_only else run(), indent=2))


if __name__ == "__main__":
    main()
