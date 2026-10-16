#!/usr/bin/env python
"""Read-only diagnostics for the saved OSM road graph; writes new report/JSON only."""
from __future__ import annotations

import argparse
import heapq
import json
from collections import Counter
from pathlib import Path

import geopandas as gpd
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
GPKG = ROOT / "data/features/osm/chennai_osm_features.gpkg"
OUT_MD = ROOT / "docs/ROAD_GRAPH_CHECK.md"
OUT_JSON = ROOT / "data/features/osm/osm_graph_connectivity.json"
SUMMARY = ROOT / "data/features/osm/osm_graph_summary.json"
CATEGORIES = ["hospital", "clinic", "school", "college", "shelter", "fire_station", "police"]
EXTRACTED_HIGHWAY_CLASSES = {"motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link", "tertiary", "tertiary_link", "unclassified", "residential", "living_street", "service", "road", "track", "path", "footway", "cycleway", "pedestrian", "bridleway", "steps"}


def graph_components(n: int, src: np.ndarray, dst: np.ndarray) -> tuple[np.ndarray, list[int], np.ndarray, list[int]]:
    """Return weak/SCC labels and sizes with iterative union-find and Kosaraju CSR."""
    parent = np.arange(n, dtype=np.int32)
    rank = np.zeros(n, dtype=np.uint8)
    for a, b in zip(src, dst):
        a, b = int(a), int(b)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = int(parent[a])
        while parent[b] != b:
            parent[b] = parent[parent[b]]
            b = int(parent[b])
        if a != b:
            if rank[a] < rank[b]:
                a, b = b, a
            parent[b] = a
            if rank[a] == rank[b]:
                rank[a] += 1
    roots = np.empty(n, dtype=np.int32)
    for i in range(n):
        x = i
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = int(parent[x])
        roots[i] = x
    _, weak_labels = np.unique(roots, return_inverse=True)
    weak_sizes = np.bincount(weak_labels).tolist()

    def csr(u: np.ndarray, v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        counts = np.bincount(u, minlength=n)
        ptr = np.empty(n + 1, dtype=np.int64)
        ptr[0] = 0
        np.cumsum(counts, out=ptr[1:])
        ix = np.empty(len(v), dtype=np.int32)
        cursor = ptr[:-1].copy()
        for a, b in zip(u, v):
            ix[cursor[a]] = b
            cursor[a] += 1
        return ptr, ix

    fptr, findices = csr(src, dst)
    rptr, rindices = csr(dst, src)
    seen = np.zeros(n, dtype=np.bool_)
    order: list[int] = []
    for start in range(n):
        if seen[start]:
            continue
        seen[start] = True
        stack_nodes = [start]
        stack_next = [int(fptr[start])]
        while stack_nodes:
            v = stack_nodes[-1]
            j = stack_next[-1]
            if j < fptr[v + 1]:
                w = int(findices[j])
                stack_next[-1] = j + 1
                if not seen[w]:
                    seen[w] = True
                    stack_nodes.append(w)
                    stack_next.append(int(fptr[w]))
            else:
                order.append(v)
                stack_nodes.pop()
                stack_next.pop()
    scc = np.full(n, -1, dtype=np.int32)
    sizes: list[int] = []
    cid = 0
    for start in reversed(order):
        if scc[start] >= 0:
            continue
        count = 0
        scc[start] = cid
        stack = [start]
        while stack:
            v = stack.pop()
            count += 1
            for j in range(int(rptr[v]), int(rptr[v + 1])):
                w = int(rindices[j])
                if scc[w] < 0:
                    scc[w] = cid
                    stack.append(w)
        sizes.append(count)
        cid += 1
    return weak_labels.astype(np.int32), weak_sizes, scc, sizes


def dijkstra(start: int, stop: int, adj: list[list[tuple[int, float]]]) -> float | None:
    dist = {start: 0.0}
    queue = [(0.0, start)]
    while queue:
        d, v = heapq.heappop(queue)
        if d != dist.get(v):
            continue
        if v == stop:
            return d
        for w, weight in adj[v]:
            nd = d + weight
            if nd < dist.get(w, float("inf")):
                dist[w] = nd
                heapq.heappush(queue, (nd, w))
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-own-outputs", action="store_true", help="Refresh only this script's newly created report and JSON.")
    args = parser.parse_args()
    occupied = [str(p) for p in (OUT_MD, OUT_JSON) if p.exists()]
    if occupied and not args.refresh_own_outputs:
        raise FileExistsError("Refusing to overwrite: " + ", ".join(occupied))

    print("Reading saved road nodes...", flush=True)
    nodes = gpd.read_file(GPKG, layer="road_nodes", columns=["osmid", "geometry"])
    nodes = nodes.drop_duplicates("osmid").reset_index(drop=True)
    ids = nodes.osmid.to_numpy(dtype=np.int64)
    id_index = {int(node): i for i, node in enumerate(ids)}
    print("Reading saved directed arcs...", flush=True)
    arcs = gpd.read_file(GPKG, layer="directed_road_arcs", columns=["from_node", "to_node"])
    valid = arcs.from_node.isin(id_index) & arcs.to_node.isin(id_index)
    src = arcs.loc[valid, "from_node"].map(id_index).to_numpy(dtype=np.int32)
    dst = arcs.loc[valid, "to_node"].map(id_index).to_numpy(dtype=np.int32)
    print(f"Computing components for {len(nodes):,} nodes and {len(src):,} arcs...", flush=True)
    weak, weak_sizes, scc, scc_sizes = graph_components(len(nodes), src, dst)
    scc_counts = np.bincount(scc, minlength=len(scc_sizes))
    largest_scc_id = int(np.argmax(scc_counts))
    largest_scc_nodes = int(scc_counts[largest_scc_id])
    largest_weak_nodes = max(weak_sizes)

    print("Reading road segment metadata...", flush=True)
    segments = gpd.read_file(GPKG, layer="road_segments", columns=["node_a", "node_b", "highway", "oneway", "length_m"])
    pair_lengths: dict[tuple[int, int], float] = {}
    for row in segments.itertuples(index=False):
        a, b = int(row.node_a), int(row.node_b)
        length = float(row.length_m)
        key = (a, b)
        pair_lengths[key] = min(length, pair_lengths.get(key, float("inf")))
    arc_weights: list[float] = []
    for row in arcs.loc[valid, ["from_node", "to_node"]].itertuples(index=False, name=None):
        a, b = int(row[0]), int(row[1])
        arc_weights.append(pair_lengths.get((a, b), pair_lengths.get((b, a), float(np.hypot(nodes.geometry.iloc[id_index[a]].x - nodes.geometry.iloc[id_index[b]].x, nodes.geometry.iloc[id_index[a]].y - nodes.geometry.iloc[id_index[b]].y)))))
    lengths = np.asarray(arc_weights, dtype=np.float64)
    arc_largest_length = float(lengths[scc[src] == largest_scc_id].sum())
    largest_scc_node_share = largest_scc_nodes / len(nodes)
    largest_scc_arc_share = float((scc[src] == largest_scc_id).sum() / len(src))
    length_total_directed = float(lengths.sum())
    largest_scc_length_share = arc_largest_length / length_total_directed if length_total_directed else 0.0

    # Count unique neighbours; degree-one nodes are topological dead ends.
    neighbours: list[set[int]] = [set() for _ in range(len(nodes))]
    for a, b in zip(src, dst):
        neighbours[int(a)].add(int(b))
        neighbours[int(b)].add(int(a))
    degree = np.fromiter((len(x) for x in neighbours), dtype=np.int32, count=len(nodes))
    dead_ends = int((degree == 1).sum())
    component_rows = []
    for label, count in enumerate(weak_sizes):
        if count == largest_weak_nodes:
            continue
        ix = np.flatnonzero(weak == label)
        component_rows.append({"weak_component": label, "nodes": int(count), "arcs": int(np.isin(src, ix).sum()),
                              "reason": "separate in the saved endpoint topology; source cause (island, clipped edge, disconnected OSM mapping, or access restriction) cannot be distinguished from these layers alone"})

    print("Reading facility points and calculating nearest-node distances...", flush=True)
    facilities = gpd.read_file(GPKG, layer="facilities", columns=["osmid", "source_type", "category", "name", "nearest_road_distance_m", "geometry"])
    nodes_sindex = nodes.sindex
    category_stats = {}
    snapped_rows = {}
    for category in CATEGORIES:
        sub = facilities.loc[facilities.category == category].copy()
        distances = []
        attached = []
        for geom in sub.geometry:
            near_ix = int(nodes_sindex.nearest(geom, return_all=False)[1, 0])
            distances.append(float(geom.distance(nodes.geometry.iloc[near_ix])))
            attached.append(near_ix)
        nearest_road = sub.nearest_road_distance_m.astype(float).dropna().to_numpy()
        category_stats[category] = {"feature_count": int(len(sub)), "assigned_to_nearest_node": int(len(attached)),
                                    "within_500m_of_node": int(sum(d <= 500 for d in distances)),
                                    "node_snap_distance_m": {"min": float(np.min(distances)) if distances else None,
                                                             "median": float(np.median(distances)) if distances else None,
                                                             "p95": float(np.percentile(distances, 95)) if distances else None,
                                                             "max": float(np.max(distances)) if distances else None},
                                    "nearest_road_segment_distance_m": {"median": float(np.median(nearest_road)) if len(nearest_road) else None,
                                                                          "p95": float(np.percentile(nearest_road, 95)) if len(nearest_road) else None}}
        snapped_rows[category] = [(i, float(d)) for i, d in zip(attached, distances)]

    # One closest hospital/shelter pair by map distance, plus a second pair when available.
    hosp = facilities.loc[facilities.category == "hospital"]
    shelters = facilities.loc[facilities.category == "shelter"]
    sample_routes = []
    adj: list[list[tuple[int, float]]] = [[] for _ in range(len(nodes))]
    for a, b, w in zip(src, dst, lengths):
        adj[int(a)].append((int(b), float(w)))
    h_attach = [int(nodes_sindex.nearest(g, return_all=False)[1, 0]) for g in hosp.geometry]
    s_attach = [int(nodes_sindex.nearest(g, return_all=False)[1, 0]) for g in shelters.geometry]
    if h_attach and s_attach:
        hp = hosp.geometry.to_numpy()
        sp = shelters.geometry.to_numpy()
        h_order = np.argsort([float(hp[i].distance(sp[0])) for i in range(len(hp))])[:5]
        pairs = []
        for hi in h_order:
            si = int(np.argmin([float(hp[int(hi)].distance(p)) for p in sp]))
            pairs.append((int(hi), si, float(hp[int(hi)].distance(sp[si]))))
        used: set[tuple[int, int]] = set()
        for hi, si, straight in pairs:
            if (hi, si) in used:
                continue
            used.add((hi, si))
            length = dijkstra(h_attach[hi], s_attach[si], adj)
            hospital_name = hosp.iloc[hi].get("name")
            shelter_name = shelters.iloc[si].get("name")
            hospital_name = "unnamed" if hospital_name is None or str(hospital_name).lower() == "nan" else str(hospital_name)
            shelter_name = "unnamed" if shelter_name is None or str(shelter_name).lower() == "nan" else str(shelter_name)
            sample_routes.append({"hospital_name": hospital_name, "shelter_name": shelter_name,
                                  "straight_distance_m": straight, "routed_length_m": length, "routable": length is not None})
            if len(sample_routes) >= 3:
                break

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    classes = summary.get("road_segment_counts_by_highway", {})
    all_len = float(segments.length_m.sum())
    # Segment length counted once when both endpoints belong to the largest SCC.
    largest_node_ids = set(int(ids[i]) for i in np.flatnonzero(scc == largest_scc_id))
    largest_seg_len = float(segments.loc[segments.node_a.isin(largest_node_ids) & segments.node_b.isin(largest_node_ids), "length_m"].sum())
    largest_seg_share = largest_seg_len / all_len if all_len else 0
    # Largest SCC weak-component association and small-component inventory.
    payload = {"source": "Read-only calculation from saved OSM GeoPackage; no source or existing feature changed",
               "graph": {"nodes": int(len(nodes)), "directed_arcs": int(len(src)), "weak_component_count": len(weak_sizes),
                         "strong_component_count": len(scc_sizes), "largest_weak_component_nodes": largest_weak_nodes,
                         "largest_strong_component_nodes": largest_scc_nodes, "largest_strong_component_node_share": largest_scc_node_share,
                         "largest_strong_component_directed_arc_share": largest_scc_arc_share,
                         "largest_strong_component_road_length_m": largest_seg_len,
                         "largest_strong_component_road_length_share": largest_seg_share,
                         "largest_strong_component_directed_arc_length_share": largest_scc_length_share,
                         "dead_end_nodes_degree_1": dead_ends, "weak_components_outside_largest": component_rows,
                         "note": "No additional components were dropped by this diagnostic. Components listed are disconnected in the saved graph; cause cannot be uniquely assigned without auditing source geometry, clipping, access, and extraction decisions."},
               "highway_classes_included_by_extractor": sorted(EXTRACTED_HIGHWAY_CLASSES),
               "highway_classes_with_saved_segments_and_counts": classes,
               "highway_classes_included_but_zero_saved_segments": sorted(EXTRACTED_HIGHWAY_CLASSES - set(classes)),
               "highway_class_exclusion_rule": "Only the listed highway values were accepted by the extractor; other values and missing highway tags were excluded.",
               "facility_counts_and_distances": category_stats,
               "hospital_shelter_sample_routes": sample_routes,
               "population_road_proximity": {"existing_all_roads_100m_population": 6072870.5, "existing_cma_population": 6203811.3,
                                              "share_percent": 6072870.5 / 6203811.3 * 100,
                                              "interpretation": "All extracted classes, including footway, path, service, steps, and track, contribute. This proximity statistic does not establish flood-safe access; contribution by individual class was not separately recomputed."}}
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    rows = ["# Road graph sanity check", "", "Read-only diagnosis of the existing graph and facility layers. The output JSON is a new file; no existing features were changed.", "",
            "## Connectivity", "", f"| Metric | Result |", "|---|---:|",
            f"| Nodes | {len(nodes):,} |", f"| Directed arcs | {len(src):,} |", f"| Weakly connected components | {len(weak_sizes):,} |",
            f"| Strongly connected components | {len(scc_sizes):,} |", f"| Largest weak component | {largest_weak_nodes:,} nodes ({largest_weak_nodes/len(nodes)*100:.2f}%) |",
            f"| Largest SCC | {largest_scc_nodes:,} nodes ({largest_scc_node_share*100:.2f}%) |", f"| Largest SCC directed arcs | {largest_scc_arc_share*100:.2f}% |",
            f"| Road length with both segment endpoints inside largest SCC | {largest_seg_len/1000:,.1f} km / {all_len/1000:,.1f} km ({largest_seg_share*100:.2f}%) |",
            f"| Directed arc length retained inside largest SCC | {arc_largest_length/1000:,.1f} km-equivalent / {length_total_directed/1000:,.1f} ({largest_scc_length_share*100:.2f}%) |",
            f"| Degree-1 dead-end nodes | {dead_ends:,} |", "", "The saved graph has no separately recorded dropped-component table. The table below lists every weak component outside the largest, as isolated components in the saved topology; the exact cause is not inferable from the saved layers alone. This diagnostic did not drop nodes or edges.", "",
            "| Component ID | Nodes | Directed arcs | Reason/status |", "|---:|---:|---:|---|"]
    rows += [f"| {x['weak_component']} | {x['nodes']} | {x['arcs']} | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |" for x in component_rows]
    rows += ["", "## Highway classes", "", "The extractor accepted these OSM `highway` values: " + ", ".join(f"`{x}`" for x in sorted(EXTRACTED_HIGHWAY_CLASSES)) + ". Present in the saved segment layer (counts are segments): " + ", ".join(f"`{k}` {v:,}" for k, v in sorted(classes.items())) + ". `bridleway` was accepted by code but has no saved segment. Other highway values and missing highway tags were excluded by the extraction filter.", "",
             "## Facilities", "", "Every listed facility point was assigned to its nearest saved road node to compute a diagnostic distance; this is not a validated turn-access snap rule. The 500 m count uses straight-line distance to the nearest road node. Segment distances use the existing `nearest_road_distance_m` field.", "",
             "| Category | OSM facility points | Assigned nearest node | Within 500 m node | Node distance median / p95 / max (m) | Road segment distance median / p95 (m) |", "|---|---:|---:|---:|---|---|"]
    for c in CATEGORIES:
        x = category_stats[c]; d=x["node_snap_distance_m"]; rd=x["nearest_road_segment_distance_m"]
        rows.append(f"| {c} | {x['feature_count']:,} | {x['assigned_to_nearest_node']:,} | {x['within_500m_of_node']:,} | {d['median']:.1f} / {d['p95']:.1f} / {d['max']:.1f} | {rd['median']:.1f} / {rd['p95']:.1f} |")
    rows += ["", "The source inventory reports 908 hospitals, 706 schools and 172 shelters, compared with 848, 696 and 171 in this facility layer. The inventory uses a rectangular bounding box; the extracted layer covers the CMA polygon plus 2 km, and geometry conversion, tag grouping and deduplication may also differ. These are plausible scope/method causes, but the exact 60/10/1 differences remain unresolved without a like-for-like recount of the PBF using the same geometry, tags and deduplication rules. [repo: `docs/OSM_COUNTS.md`, saved `facilities` layer]", "",
             "## Example routes", "", "Sample hospital-to-shelter routes use nearest-node attachments and Dijkstra over saved directed arcs weighted by segment lengths. This only tests graph connectivity; it does not check closures, bridge capacity, flood depth, access restrictions, or safety.", "",
             "| Hospital | Shelter | Straight distance (m) | Directed network path (m) | Routable? |", "|---|---|---:|---:|---|"]
    for x in sample_routes:
        dist = f"{x['routed_length_m']:.0f}" if x["routed_length_m"] is not None else "no directed path"
        rows.append(f"| {x['hospital_name']} | {x['shelter_name']} | {x['straight_distance_m']:.0f} | {dist} | {'yes' if x['routable'] else 'no'} |")
    rows += ["", "## 100 m population proximity", "", f"The existing all-road buffer contains an estimated {6072870.5:,.1f} of {6203811.3:,.1f} population-grid total ({6072870.5/6203811.3*100:.2f}%). The buffer includes footpaths, service roads, steps, tracks and other minor classes, so the high coverage is not evidence that 98% of residents have a usable evacuation route. The individual contribution of minor classes was not recomputed in this fix-up. [repo: existing road-buffer population summary]", "",
             "## Limitations", "", "The source graph is a static OSM snapshot. The SCC is a strict directed reachability measure and can be small where one-way links or disconnected access roads exist. Nearest-node assignment uses no maximum snap distance; counts within 500 m show how often nearest nodes are close, not that each facility is actually connected to a usable entrance. No graph edges were removed during this check.", ""]
    OUT_MD.write_text("\n".join(rows), encoding="utf-8")
    print(f"Wrote {OUT_MD.relative_to(ROOT)} and {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
