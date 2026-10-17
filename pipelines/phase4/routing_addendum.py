#!/usr/bin/env python
"""Read-only route summaries for largest-SCC and population-weighted origins."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import rowcol
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipelines.phase3.fixups.check_road_graph import graph_components
from pipelines.phase4.routing_profile import INCLUDE, dijkstra, parse_speed

GPKG = ROOT / "data/features/osm/chennai_osm_features.gpkg"
POP = ROOT / "data/features/population/worldpop_2021_sum_resampled_30m.tif"
MASK = ROOT / "data/processed/grid/cma_mask.tif"
OUT = ROOT / "data/processed/routing/routing_origin_coverage.json"
REPORT = ROOT / "docs/ROUTING_PROFILE.md"
SEED = 42
N = 200


def _route_summary(origins: list[int], reverse: dict[int, list[tuple[int, float]]], targets: list[int]) -> dict:
    costs = dijkstra(reverse, targets)
    vals = [costs.get(node) for node in origins]
    reachable = np.asarray([v for v in vals if v is not None], dtype="float64")
    return {
        "origins": len(origins), "reachable": int(len(reachable)),
        "unreachable": int(len(origins) - len(reachable)),
        "median_travel_time_min": float(np.median(reachable)) if len(reachable) else None,
        "p90_travel_time_min": float(np.percentile(reachable, 90)) if len(reachable) else None,
        "within_30_min_share_of_all_origins": float(np.mean([v is not None and v <= 30 for v in vals])) if vals else None,
    }


def main() -> int:
    if OUT.exists():
        raise FileExistsError(f"Refusing to overwrite existing origin-coverage output: {OUT}")
    nodes = gpd.read_file(GPKG, layer="road_nodes")
    seg = gpd.read_file(GPKG, layer="road_segments")
    facilities = gpd.read_file(GPKG, layer="facilities")
    seg = seg[seg.highway.astype(str).isin(INCLUDE)].copy()
    if "access" in seg:
        seg = seg[~seg.access.astype(str).str.lower().isin(["no", "private"])]
    ids = nodes.osmid.astype("int64").to_numpy()
    id_index = {int(node): i for i, node in enumerate(ids)}
    src, dst, adjacency, reverse = [], [], {int(n): [] for n in ids}, {int(n): [] for n in ids}
    for edge in seg.itertuples():
        u, v = int(edge.node_a), int(edge.node_b)
        if u not in id_index or v not in id_index:
            continue
        speed, _ = parse_speed(getattr(edge, "maxspeed", None), str(edge.highway))
        minutes = float(edge.length_m or edge.geometry.length) / 1000 / speed * 60
        oneway = str(getattr(edge, "oneway", "")).lower()
        arcs = [(u, v)] if oneway in ("yes", "1", "true") else ([(v, u)] if oneway == "-1" else [(u, v), (v, u)])
        for a, b in arcs:
            src.append(id_index[a]); dst.append(id_index[b])
            adjacency[a].append((b, minutes)); reverse[b].append((a, minutes))
    src_a, dst_a = np.asarray(src, dtype="int32"), np.asarray(dst, dtype="int32")
    _, _, scc, scc_sizes = graph_components(len(ids), src_a, dst_a)
    largest_id = int(np.argmax(scc_sizes))
    largest_nodes = ids[scc == largest_id]

    node_geoms = nodes.geometry.to_numpy()
    tree = STRtree(node_geoms)
    targets = {"hospital": [], "shelter": []}
    for row in facilities.itertuples():
        category = str(getattr(row, "category", "")).lower()
        key = "hospital" if "hospital" in category else ("shelter" if "shelter" in category else None)
        if key:
            ix = int(tree.nearest(row.geometry))
            targets[key].append(int(ids[ix]))

    rng = random.Random(SEED)
    uniform_origins = rng.sample([int(n) for n in largest_nodes], min(N, len(largest_nodes)))

    # Map each eligible SCC node to its containing master-grid cell. Divide a cell's
    # WorldPop count equally among its eligible nodes, so dense node clusters do not
    # multiply the cell's population weight.
    eligible_ids, eligible_rows, eligible_cols, weights = [], [], [], []
    with rasterio.open(MASK) as mask_ds, rasterio.open(POP) as pop_ds:
        mask = mask_ds.read(1)
        pop = pop_ds.read(1, masked=False)
        node_idx = np.flatnonzero(scc == largest_id)
        xs = nodes.geometry.iloc[node_idx].x.to_numpy()
        ys = nodes.geometry.iloc[node_idx].y.to_numpy()
        rr, cc = rowcol(mask_ds.transform, xs, ys)
        rr, cc = np.asarray(rr), np.asarray(cc)
        inside_grid = (rr >= 0) & (rr < mask.shape[0]) & (cc >= 0) & (cc < mask.shape[1])
        inside_pos = np.flatnonzero(inside_grid)
        inside_pos = inside_pos[mask[rr[inside_pos], cc[inside_pos]] == 1]
        pos_pop = pop[rr[inside_pos], cc[inside_pos]].astype("float64")
        if pop_ds.nodata is not None:
            valid = np.isfinite(pos_pop) & (pos_pop != pop_ds.nodata) & (pos_pop > 0)
        else:
            valid = np.isfinite(pos_pop) & (pos_pop > 0)
        selected = inside_pos[valid]
        selected_rows, selected_cols = rr[selected], cc[selected]
        cell_key = selected_rows.astype("int64") * mask.shape[1] + selected_cols
        _, inverse, counts = np.unique(cell_key, return_inverse=True, return_counts=True)
        weights = pos_pop[valid] / counts[inverse]
        eligible_ids = [int(ids[node_idx[i]]) for i in selected]
        eligible_rows, eligible_cols = selected_rows.tolist(), selected_cols.tolist()
    if not eligible_ids or float(np.sum(weights)) <= 0:
        weighted_origins = []
    else:
        weighted_origins = rng.choices(eligible_ids, weights=[float(w) for w in weights], k=N)

    result = {
        "status": "DERIVED", "seed": SEED, "sample_size": N,
        "routing_graph": {"included_edges": len(seg), "directed_arcs": int(len(src_a)),
                          "nodes": len(ids), "scc_count": len(scc_sizes),
                          "largest_scc_nodes": int(len(largest_nodes)),
                          "largest_scc_share": float(len(largest_nodes) / len(ids))},
        "uniform_largest_scc_node_origins": uniform_origins,
        "population_weighted_largest_scc_node_origins": weighted_origins,
        "population_weighting": {
            "raster": "data/features/population/worldpop_2021_sum_resampled_30m.tif",
            "population_sum_weighted": float(np.sum(weights)) if len(weights) else 0.0,
            "eligible_nodes_with_positive_population": len(eligible_ids),
            "rule": "sample SCC nodes with probability proportional to WorldPop count in their 30 m CMA cell, divided equally among SCC nodes in the same cell; replacement is allowed",
            "worldpop_values_are_constrained_alpha_model_estimates_not_census_counts": True,
        },
        "uniform_routes": {key: _route_summary(uniform_origins, reverse, vals) for key, vals in targets.items()},
        "population_weighted_routes": {key: _route_summary(weighted_origins, reverse, vals) for key, vals in targets.items()},
        "limitations": ["Travel times use assumed speeds where maxspeed is absent.",
                        "No flood closures or bridge/underpass hazard was applied.",
                        "WorldPop R2025A is an alpha constrained estimate; weighted origins are a sensitivity sample, not observed evacuation demand."],
    }
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    with REPORT.open("a", encoding="utf-8") as stream:
        stream.write("\n## Largest-SCC and population-weighted origin addendum\n\n")
        stream.write(f"A fixed seed ({SEED}) selected {len(uniform_origins)} nodes uniformly from the largest strongly connected component ({len(largest_nodes):,} of {len(ids):,} graph nodes; {len(largest_nodes)/len(ids):.2%}). A second {len(weighted_origins)}-draw sample weighted node selection by the existing 30 m WorldPop value within the CMA, dividing a cell's value among eligible nodes in that cell; weighted draws are with replacement. The detailed per-origin IDs, route summaries and limitations are in `{OUT.relative_to(ROOT).as_posix()}`. WorldPop is an alpha model estimate, not census demand, and the route times use assumed speeds without flood closures.\n")
    print(f"LARGEST_SCC={len(largest_nodes)}; UNIFORM={len(uniform_origins)}; POP_WEIGHTED={len(weighted_origins)}; ARCS={len(src_a)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
