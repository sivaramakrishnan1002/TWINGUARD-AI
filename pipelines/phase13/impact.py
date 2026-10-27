"""Summarize coarse, simulated flood impact from saved A05 ensembles.

All products are DERIVED scenario outputs. NoData is kept unassessed.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio
import rasterio
import shapely

from pipelines.phase12 import simulate as a06

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "data/features/impact/batch2_v4_contract"
REPORT = ROOT / "docs/PHASE13_IMPACT_BATCH2_V4.md"
GPKG = ROOT / "data/features/osm/chennai_osm_features.gpkg"
CELL_TABLE = ROOT / "data/features/static/cell_table.parquet"
FORECAST = ROOT / "data/features/forecast/batch2_v1"
SUMMARY = FORECAST / "forecast_summary.json"
THRESHOLDS_M = (0.15, 0.30, 0.50)
DEFAULT_THRESHOLD_M = 0.30
SCHEMA_ID = "twinguard.impact_result"
SCHEMA_VERSION = "0.1-draft"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def grid_indices(x: np.ndarray, y: np.ndarray, transform, height: int, width: int) -> np.ndarray:
    """Map projected coordinates to row-major cell IDs, or -1 outside the grid."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    col = np.floor((x - transform.c) / transform.a).astype(np.int64)
    row = np.floor((transform.f - y) / abs(transform.e)).astype(np.int64)
    inside = (row >= 0) & (row < height) & (col >= 0) & (col < width)
    out = np.full(row.shape, -1, dtype=np.int64)
    out[inside] = row[inside] * width + col[inside]
    return out


def member_distribution(values, unit: str, status: str = "AVAILABLE") -> dict:
    """Descriptive member spread; it is not a calibrated confidence interval."""
    array = np.asarray(values, dtype=np.float64)
    array = array[np.isfinite(array)]
    if not len(array):
        return {"status": "UNAVAILABLE", "unit": unit, "mean": None,
                "p05": None, "p50": None, "p95": None, "member_count": 0,
                "interpretation": "NoData or unavailable; not zero."}
    q = np.quantile(array, [0.05, 0.5, 0.95])
    return {"status": status, "unit": unit, "mean": float(array.mean()),
            "p05": float(q[0]), "p50": float(q[1]), "p95": float(q[2]),
            "member_count": int(len(array)),
            "interpretation": "Descriptive simulated ensemble spread; not calibrated uncertainty."}


def probability_below(values: np.ndarray, threshold: float) -> tuple[np.ndarray, np.ndarray]:
    """Return passability probability and number of valid members per cell."""
    data = np.asarray(values, dtype=np.float32)
    valid = np.isfinite(data)
    count = valid.sum(axis=0)
    passed = (valid & (data < float(threshold))).sum(axis=0)
    probability = np.divide(passed, count, out=np.full(count.shape, np.nan, dtype=np.float32), where=count > 0)
    return probability, count


def known_population_exposure(depth: np.ndarray, population: np.ndarray,
                              valid_source_count: np.ndarray, nodata_source_count: np.ndarray,
                              threshold: float) -> tuple[float, int, int]:
    """Return known exposed estimate, exposed NoData source cells, and assessed flood cells."""
    d = np.asarray(depth, dtype=np.float64)
    flooded = np.isfinite(d) & (d >= float(threshold))
    known = flooded & (np.asarray(valid_source_count) > 0)
    known_people = float(np.nansum(np.asarray(population, dtype=np.float64)[known]))
    unknown = int(np.asarray(nodata_source_count, dtype=np.int64)[flooded].sum())
    assessed_flood_cells = int(flooded.sum())
    return known_people, unknown, assessed_flood_cells


def _xy_to_cell(x, y, transform, eligible: np.ndarray) -> np.ndarray:
    h, w = eligible.shape
    flat = grid_indices(x, y, transform, h, w)
    good = flat >= 0
    result = np.full(flat.shape, -1, dtype=np.int64)
    result[good] = np.where(eligible.ravel()[flat[good]], flat[good], -1)
    return result


def aggregate_population(transform, eligible: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict]:
    """Aggregate 30 m CMA cell-table values onto the 600 m model cells."""
    table = pq.read_table(CELL_TABLE, columns=["x", "y", "worldpop_2021", "population_is_nodata"])
    x = table.column("x").to_numpy(zero_copy_only=False)
    y = table.column("y").to_numpy(zero_copy_only=False)
    vals = table.column("worldpop_2021").to_numpy(zero_copy_only=False).astype(np.float64)
    no_data = (table.column("population_is_nodata").to_numpy(zero_copy_only=False).astype(bool)
               | ~np.isfinite(vals))
    h, w = eligible.shape
    cell = _xy_to_cell(x, y, transform, eligible)
    keep = (cell >= 0)
    pop = np.bincount(cell[keep & ~no_data], weights=vals[keep & ~no_data], minlength=h*w)
    valid_count = np.bincount(cell[keep & ~no_data], minlength=h*w)
    nodata_count = np.bincount(cell[keep & no_data], minlength=h*w)
    pop = pop.reshape(h, w).astype(np.float64)
    nodata_count = nodata_count.reshape(h, w).astype(np.int64)
    valid_count = valid_count.reshape(h, w).astype(np.int64)
    pop[~eligible] = np.nan
    pop[(valid_count.reshape(h, w) == 0) & eligible] = np.nan
    nodata_count[~eligible] = 0
    valid_count[~eligible] = 0
    meta = {
        "source_table": "data/features/static/cell_table.parquet",
        "source_rows": int(table.num_rows),
        "cma_cells_mapped_to_model_grid": int(keep.sum()),
        "known_population_source_cells": int((keep & ~no_data).sum()),
        "population_nodata_source_cells": int((keep & no_data).sum()),
        "known_population_sum_people_model_domain": float(np.nansum(pop)),
        "note": "Only known CMA-limited 30 m cells are summed. NoData remains separately counted and is not zero.",
    }
    return pop, nodata_count, {**meta, "valid_count": valid_count}


def load_roads(transform, eligible: np.ndarray) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict]:
    """Build a road-to-cell lookup and a coarse cell connectivity graph."""
    roads = pyogrio.read_dataframe(GPKG, layer="road_segments",
                                   columns=["osmid", "node_a", "node_b", "highway", "bridge", "tunnel", "length_m"])
    geom = roads.geometry.array
    mid = shapely.line_interpolate_point(geom, 0.5, normalized=True)
    xy_mid = shapely.get_coordinates(mid)
    edge_cell = _xy_to_cell(xy_mid[:, 0], xy_mid[:, 1], transform, eligible)
    first = shapely.get_point(geom, 0)
    last = shapely.get_point(geom, -1)
    xy_first = shapely.get_coordinates(first)
    xy_last = shapely.get_coordinates(last)
    end_a = _xy_to_cell(xy_first[:, 0], xy_first[:, 1], transform, eligible)
    end_b = _xy_to_cell(xy_last[:, 0], xy_last[:, 1], transform, eligible)
    lengths = pd.to_numeric(roads["length_m"], errors="coerce").fillna(0).to_numpy(np.float64)
    # The impact grid is coarse; midpoint is the declared representative depth sample.
    modeled = (edge_cell >= 0) & (lengths > 0)
    edge_ids = np.flatnonzero(modeled)
    edge_lookup = pd.DataFrame({
        "edge_feature_index": edge_ids.astype(np.int64),
        "source_osmid": roads.osmid.to_numpy()[edge_ids],
        "node_a": roads.node_a.to_numpy()[edge_ids],
        "node_b": roads.node_b.to_numpy()[edge_ids],
        "highway": roads.highway.fillna("unknown").astype(str).to_numpy()[edge_ids],
        "bridge": roads.bridge.fillna("").astype(str).to_numpy()[edge_ids],
        "tunnel": roads.tunnel.fillna("").astype(str).to_numpy()[edge_ids],
        "length_m": lengths[edge_ids],
        "grid_cell_id": edge_cell[edge_ids],
        "grid_row": edge_cell[edge_ids] // eligible.shape[1],
        "grid_col": edge_cell[edge_ids] % eligible.shape[1],
        "depth_sample": "road-segment midpoint on 600 m grid",
    })
    # Coarse graph link: connect the 600 m cells containing each segment's endpoints.
    graph_ok = modeled & (end_a >= 0) & (end_b >= 0) & (end_a != end_b)
    graph_ids = np.flatnonzero(graph_ok)
    pair = np.column_stack([np.minimum(end_a[graph_ids], end_b[graph_ids]),
                            np.maximum(end_a[graph_ids], end_b[graph_ids])])
    unique_pairs, inverse = np.unique(pair, axis=0, return_inverse=True)
    edge_lengths_by_pair = np.bincount(inverse, weights=lengths[graph_ids], minlength=len(unique_pairs))
    static_by_cell = np.bincount(edge_cell[modeled], weights=lengths[modeled], minlength=eligible.size).reshape(eligible.shape)
    edge_len_by_cell = np.bincount(edge_cell[modeled], weights=lengths[modeled], minlength=eligible.size)
    road_counts_by_cell = np.bincount(edge_cell[modeled], minlength=eligible.size)
    graph = {
        "pairs": unique_pairs.astype(np.int64),
        "inverse": inverse.astype(np.int64),
        "graph_edge_ids": graph_ids.astype(np.int64),
        "pair_road_length_m": edge_lengths_by_pair,
        "edge_cell_all": edge_cell.astype(np.int64),
        "edge_lengths_all": lengths,
        "modeled_edge_ids": edge_ids.astype(np.int64),
        "edge_len_by_cell": edge_len_by_cell.reshape(eligible.shape),
        "road_counts_by_cell": road_counts_by_cell.reshape(eligible.shape),
        "graph_cell_ids": np.unique(unique_pairs.ravel()) if len(unique_pairs) else np.array([], dtype=np.int64),
    }
    report = {
        "source_layer": "road_segments",
        "source_feature_count": int(len(roads)),
        "midpoint_assessed_edge_count": int(modeled.sum()),
        "midpoint_unassessed_edge_count": int((~modeled).sum()),
        "midpoint_assessed_road_length_m": float(lengths[modeled].sum()),
        "coarse_graph_link_count": int(len(unique_pairs)),
        "coarse_graph_edge_feature_count": int(len(graph_ids)),
        "coarse_graph_method": "Road endpoint cells are connected when the source road segment has a modeled midpoint; parallel segments collapse to a coarse cell-pair link.",
    }
    return edge_lookup, graph["edge_cell_all"], graph["edge_lengths_all"], graph_ids, inverse, {**report, "_graph": graph}


def load_facilities(transform, eligible: np.ndarray) -> tuple[pd.DataFrame, dict]:
    facilities = pyogrio.read_dataframe(GPKG, layer="facilities", columns=["osmid", "category", "name"])
    xy = shapely.get_coordinates(facilities.geometry.array)
    cell = _xy_to_cell(xy[:, 0], xy[:, 1], transform, eligible)
    raw_category = facilities.category.fillna("").astype(str).str.lower().to_numpy()
    group = np.full(len(facilities), "", dtype=object)
    group[raw_category == "hospital"] = "hospital"
    group[raw_category == "shelter"] = "shelter"
    group[np.isin(raw_category, ["school", "college"])] = "candidate_shelter"
    keep = (cell >= 0) & (group != "")
    out = pd.DataFrame({"facility_feature_index": np.flatnonzero(keep),
                        "source_osmid": facilities.osmid.to_numpy()[keep],
                        "category": raw_category[keep], "cascade_group": group[keep],
                        "grid_cell_id": cell[keep]})
    counts = {k: int((out.cascade_group == k).sum()) for k in ("hospital", "shelter", "candidate_shelter")}
    meta = {"source_layer": "facilities", "source_feature_count": int(len(facilities)),
            "mapped_target_facility_count": int(len(out)),
            "unassessed_target_facility_count": int(np.isin(raw_category, ["hospital", "shelter", "school", "college"]).sum() - len(out)),
            "mapped_counts_by_cascade_group": counts,
            "candidate_shelter_definition": "OSM schools plus colleges, kept separate from mapped shelters; this is a candidate set assumption."}
    return out, meta


class UnionFind:
    def __init__(self, size: int):
        self.parent = np.arange(size, dtype=np.int64)
        self.size = np.ones(size, dtype=np.int64)

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = int(self.parent[x])
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(int(a)), self.find(int(b))
        if ra == rb:
            return
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]


def baseline_core(graph: dict, grid_size: int) -> np.ndarray:
    pairs = graph["pairs"]
    uf = UnionFind(grid_size)
    for u, v in pairs:
        uf.union(int(u), int(v))
    weights = np.zeros(grid_size, dtype=np.float64)
    for i, cell in enumerate(graph["graph_cell_ids"]):
        weights[uf.find(int(cell))] += 0.0
    for (u, v), weight in zip(pairs, graph["pair_road_length_m"]):
        weights[uf.find(int(u))] += float(weight)
    roots = np.unique([uf.find(int(c)) for c in graph["graph_cell_ids"]]) if len(graph["graph_cell_ids"]) else np.array([], dtype=int)
    if not len(roots):
        return np.array([], dtype=np.int64)
    root = int(roots[np.argmax(weights[roots])])
    return np.asarray([c for c in graph["graph_cell_ids"] if uf.find(int(c)) == root], dtype=np.int64)


def facility_cascade(depth: np.ndarray, graph: dict, facilities: pd.DataFrame,
                     baseline_anchor: int | None, baseline_cells: np.ndarray,
                     threshold: float, grid_size: int) -> dict:
    """Connected-component access proxy, referenced to the baseline largest component."""
    pairs = graph["pairs"]
    edge_ids = graph["graph_edge_ids"]
    pair_for_edge = graph["inverse"]
    edge_cell = graph["edge_cell_all"][edge_ids]
    d = depth.ravel()[edge_cell]
    valid = np.isfinite(d)
    open_edge = valid & (d < threshold)
    pair_n = len(pairs)
    open_count = np.bincount(pair_for_edge[open_edge], minlength=pair_n)
    assessed_count = np.bincount(pair_for_edge[valid], minlength=pair_n)
    open_pair = open_count > 0
    uf = UnionFind(grid_size)
    for (u, v), is_open in zip(pairs, open_pair):
        if is_open:
            uf.union(int(u), int(v))
    core_roots = {uf.find(int(baseline_anchor))} if baseline_anchor is not None else set()
    graph_cells = graph["graph_cell_ids"]
    in_graph = set(int(c) for c in graph_cells)
    baseline_set = set(int(c) for c in baseline_cells)
    result = {}
    for category in ("hospital", "shelter", "candidate_shelter"):
        subset = facilities[facilities.cascade_group == category]
        assessed = subset[subset.grid_cell_id.isin(in_graph)]
        baseline_assessed = assessed[assessed.grid_cell_id.isin(baseline_set)]
        reachable = sum(uf.find(int(c)) in core_roots for c in baseline_assessed.grid_cell_id.to_numpy())
        result[category] = {"facility_count": int(len(subset)), "assessed_count": int(len(assessed)),
                            "reachable_count": int(reachable), "unreachable_count": int(len(baseline_assessed) - reachable),
                            "unassessed_count": int(len(facilities[facilities.cascade_group == category]) - len(assessed)),
                            "outside_baseline_core_count": int(len(assessed) - len(baseline_assessed)),
                            "baseline_core_count": int(subset.grid_cell_id.isin(baseline_set).sum())}
    result["network_coverage"] = {"pair_count": int(pair_n),
                                  "assessed_pair_count": int((assessed_count > 0).sum()),
                                  "unassessed_pair_count": int((assessed_count == 0).sum()),
                                  "method": "Coarse 600 m connected components; only facilities in the pre-event largest component are tested for continued connection to its highest-road-length anchor cell."}
    return result


def _distribution_status(values: list[float], incomplete: bool) -> str:
    return "UNAVAILABLE" if not values else ("PARTIAL" if incomplete else "AVAILABLE")


def _json_safe(value):
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def validate_impact_result(record: dict) -> None:
    """Check the local C7 draft's key time, units, coverage, and NoData fields."""
    required = {"schema_id", "schema_version", "result_id", "run_id", "run_version", "source_mode",
                "event", "valid_at_utc", "aggregation_interval", "generated_at_utc", "scenario_key",
                "thresholds", "metrics", "facility_access_by_category", "coverage", "uncertainty",
                "provenance", "qc_flags"}
    missing = required - record.keys()
    if missing:
        raise ValueError(f"impact result missing C7 draft fields: {sorted(missing)}")
    if not isinstance(record["run_id"], int):
        raise ValueError("run_id must be an integer under the C7 draft")
    if record["source_mode"] != "SIMULATED" or record["event"].get("time_basis") != "UTC":
        raise ValueError("impact result must be simulated and explicitly UTC-based")
    threshold = record["thresholds"].get("road_block_depth_m")
    if not isinstance(threshold, (int, float)) or threshold <= 0:
        raise ValueError("road blocking threshold must be a positive metre value")
    population = record["metrics"].get("population_exposed_people")
    if population is not None and population.get("unit") != "people":
        raise ValueError("population estimate must declare people units")
    if "nodata_count" not in record["coverage"].get("population", {}):
        raise ValueError("population coverage must state NoData count")
    for row in record["facility_access_by_category"]:
        for field in ("facility_count", "reachable_count", "unreachable_count", "unassessed_count",
                      "access_loss_fraction", "coverage_fraction"):
            if field not in row:
                raise ValueError(f"facility cascade is missing {field}")


def run() -> dict:
    if OUTPUT.exists() and any(OUTPUT.iterdir()):
        raise FileExistsError(f"refusing to overwrite nonempty output: {OUTPUT.relative_to(ROOT)}")
    if REPORT.exists():
        raise FileExistsError(f"refusing to overwrite report: {REPORT.relative_to(ROOT)}")
    start = time.perf_counter()
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    OUTPUT.mkdir(parents=True, exist_ok=True)

    static = a06.load_static()
    eligible = static["eligible"]
    transform = static["transform"]
    height, width = eligible.shape
    grid_size = height * width
    pop_grid, pop_nodata_grid, pop_meta_all = aggregate_population(transform, eligible)
    pop_known_count_grid = pop_meta_all.pop("valid_count")
    roads_frame, edge_cell_all, edge_length_all, graph_edge_ids, graph_inverse, road_meta_all = load_roads(transform, eligible)
    graph = road_meta_all.pop("_graph")
    facilities, facility_meta = load_facilities(transform, eligible)
    baseline_cells = baseline_core(graph, grid_size)

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    events = summary["events"]
    event_lines = []
    member_records = []
    cell_tables = []
    per_combo = []
    edge_index_path = OUTPUT / "road_edge_grid_index.parquet"
    pq.write_table(pa.Table.from_pandas(roads_frame, preserve_index=False), edge_index_path,
                   compression="zstd", version="2.6")
    cell_meta_path = OUTPUT / "input_coverage.json"

    eligible_flat = eligible.ravel()
    road_length_by_cell = graph["edge_len_by_cell"].ravel()
    road_count_by_cell = graph["road_counts_by_cell"].ravel()
    pop_flat = pop_grid.ravel()
    pop_nodata_flat = pop_nodata_grid.ravel()
    pop_known_flat = pop_known_count_grid.ravel()
    baseline_anchor = (int(baseline_cells[np.argmax(road_length_by_cell[baseline_cells])])
                       if len(baseline_cells) else None)

    for event_key, event_data in events.items():
        event_start = datetime.fromisoformat(event_data["window_start_utc"].replace("Z", "+00:00"))
        event_end = datetime.fromisoformat(event_data["window_end_utc"].replace("Z", "+00:00"))
        for scenario_key, scenario in event_data["scenarios"].items():
            case = FORECAST / event_key / scenario_key
            npz_path = case / "depth_members_by_horizon_DERIVED.npz"
            with np.load(npz_path, allow_pickle=False) as z:
                depths = z["depth_m"].astype(np.float32, copy=False)
                horizons = z["horizons_hours"].astype(int)
                member_ids = z["member_ids"].astype(int)
            if depths.shape[0] != len(member_ids) or depths.shape[-2:] != eligible.shape:
                raise ValueError(f"forecast array/grid shape mismatch: {npz_path.relative_to(ROOT)}")
            if tuple(horizons.tolist()) != tuple(summary["horizons_hours"]):
                raise ValueError(f"forecast horizons differ from summary for {npz_path.relative_to(ROOT)}")
            for hix, horizon in enumerate(horizons):
                stack = depths[:, hix]
                valid = np.isfinite(stack) & eligible[None, :, :]
                valid_count = valid.sum(axis=0)
                mean_depth = np.divide(np.nansum(np.where(valid, stack, np.nan), axis=0), valid_count,
                                       out=np.full(eligible.shape, np.nan, dtype=np.float32), where=valid_count > 0)
                with np.errstate(all="ignore"):
                    q05 = np.nanpercentile(np.where(valid, stack, np.nan), 5, axis=0).astype(np.float32)
                    q95 = np.nanpercentile(np.where(valid, stack, np.nan), 95, axis=0).astype(np.float32)
                q05[valid_count == 0] = np.nan
                q95[valid_count == 0] = np.nan
                valid_at = event_start + timedelta(hours=int(horizon))
                member_vals = {float(t): {"pop": [], "road": [], "facility": [], "access": {}}
                               for t in THRESHOLDS_M}
                coverage_flags = {float(t): False for t in THRESHOLDS_M}
                coverage_flags[float(DEFAULT_THRESHOLD_M)] = (
                    road_meta_all["midpoint_unassessed_edge_count"] > 0
                    or facility_meta["unassessed_target_facility_count"] > 0
                    or pop_meta_all["population_nodata_source_cells"] > 0
                )
                cell_frame_rows = []
                for threshold in THRESHOLDS_M:
                    ppass, nvalid = probability_below(stack, threshold)
                    cell_frame_rows.append(pd.DataFrame({
                        "event_key": event_key, "scenario_key": scenario_key,
                        "valid_at_utc": valid_at.isoformat().replace("+00:00", "Z"),
                        "horizon_hours": int(horizon), "grid_cell_id": np.flatnonzero(eligible_flat),
                        "threshold_m": threshold,
                        "passability_probability": ppass.ravel()[eligible_flat],
                        "depth_mean_m": mean_depth.ravel()[eligible_flat],
                        "depth_member_p05_m": q05.ravel()[eligible_flat],
                        "depth_member_p95_m": q95.ravel()[eligible_flat],
                        "depth_valid_member_count": nvalid.ravel()[eligible_flat],
                        "member_count": int(stack.shape[0]),
                        "road_edge_count": road_count_by_cell[eligible_flat],
                        "road_length_m": road_length_by_cell[eligible_flat],
                        "qc": np.where(nvalid.ravel()[eligible_flat] == 0, "DEPTH_NODATA_UNASSESSED", "DERIVED_SIMULATED_COARSE_GRID"),
                    }))
                cell_tables.extend(cell_frame_rows)

                for mix, member_id in enumerate(member_ids):
                    dflat = stack[mix].ravel()
                    validflat = np.isfinite(dflat) & eligible_flat
                    for threshold in THRESHOLDS_M:
                        flooded_cell = validflat & (dflat >= threshold)
                        pop_known, affected_pop_nodata, _ = known_population_exposure(
                            stack[mix], pop_grid, pop_known_count_grid, pop_nodata_grid, threshold)
                        hazard_unassessed_cells = int((eligible_flat & ~validflat).sum())
                        member_vals[float(threshold)]["pop"].append(pop_known)
                        member_vals[float(threshold)]["road"].append(float(road_length_by_cell[flooded_cell].sum()))
                        facility_cell = facilities.grid_cell_id.to_numpy(np.int64)
                        facility_groups = facilities.cascade_group.to_numpy()
                        mapped_fac_cell = facility_cell >= 0
                        fac_depth = dflat[facility_cell[mapped_fac_cell]]
                        fac_valid = np.isfinite(fac_depth)
                        exposed = fac_valid & (fac_depth >= threshold)
                        member_vals[float(threshold)]["facility"].append(float(exposed.sum()))
                        incomplete = bool(affected_pop_nodata or hazard_unassessed_cells or (~fac_valid).any()
                                          or road_meta_all["midpoint_unassessed_edge_count"] > 0
                                          or facility_meta["unassessed_target_facility_count"] > 0
                                          or pop_meta_all["population_nodata_source_cells"] > 0)
                        coverage_flags[float(threshold)] |= incomplete
                        cascade = facility_cascade(stack[mix], graph, facilities, baseline_anchor, baseline_cells,
                                                   threshold, grid_size)
                        member_vals[float(threshold)]["access"].setdefault("cascade", []).append(cascade)
                        baseline_facility_count = sum(cascade[k]["baseline_core_count"]
                                                      for k in ("hospital", "shelter", "candidate_shelter"))
                        reachable_facility_count = sum(cascade[k]["reachable_count"]
                                                       for k in ("hospital", "shelter", "candidate_shelter"))
                        member_record = {
                            "event_key": event_key, "scenario_key": scenario_key,
                            "valid_at_utc": valid_at.isoformat().replace("+00:00", "Z"),
                            "horizon_hours": int(horizon), "member_id": int(member_id),
                            "threshold_m": threshold,
                            "population_exposed_known_people": pop_known,
                            "population_nodata_30m_cells_in_exposed_600m_cells": affected_pop_nodata,
                            "affected_road_length_m": float(road_length_by_cell[flooded_cell].sum()),
                            "road_length_unassessed_m": float(road_length_by_cell[eligible_flat & ~validflat].sum()),
                            "facilities_exposed_count": int(exposed.sum()),
                            "facilities_unassessed_count": int((~fac_valid).sum()),
                            "facility_access_baseline_core_count": int(baseline_facility_count),
                            "facility_access_reachable_count": int(reachable_facility_count),
                            "facility_access_loss_fraction": (float(1.0 - reachable_facility_count / baseline_facility_count)
                                                              if baseline_facility_count else None),
                            "hazard_unassessed_grid_cells": hazard_unassessed_cells,
                            "coarse_graph_unassessed_pairs": int(cascade["network_coverage"]["unassessed_pair_count"]),
                        }
                        for category in ("hospital", "shelter", "candidate_shelter"):
                            member_record[f"{category}_reachable_from_baseline_anchor"] = int(cascade[category]["reachable_count"])
                            member_record[f"{category}_in_baseline_core"] = int(cascade[category]["baseline_core_count"])
                            member_record[f"{category}_outside_baseline_core"] = int(cascade[category]["outside_baseline_core_count"])
                        member_records.append(member_record)

                # Primary result at 0.30 m; sensitivity and all member-level values are retained separately.
                primary_ix = THRESHOLDS_M.index(DEFAULT_THRESHOLD_M)
                sensitivity = []
                for threshold in THRESHOLDS_M:
                    values = member_vals[float(threshold)]
                    cascades = values["access"].get("cascade", [])
                    access_categories = []
                    for category in ("hospital", "shelter", "candidate_shelter"):
                        category_rows = [r[category] for r in cascades]
                        base_n = int(facility_meta["mapped_counts_by_cascade_group"][category])
                        med_reachable = int(round(float(np.median([r["reachable_count"] for r in category_rows])))) if category_rows else None
                        med_unreachable = int(round(float(np.median([r["unreachable_count"] for r in category_rows])))) if category_rows else None
                        mean_assessed = float(np.mean([r["assessed_count"] for r in category_rows])) if category_rows else 0.0
                        mean_reachable = float(np.mean([r["reachable_count"] for r in category_rows])) if category_rows else 0.0
                        access_categories.append({
                            "category": category,
                            "facility_count": base_n,
                            "reachable_count": med_reachable,
                            "unreachable_count": med_unreachable,
                            "unassessed_count": int(category_rows[0]["unassessed_count"]) if category_rows else base_n,
                            "access_loss_fraction": ((float(med_unreachable) / (med_reachable + med_unreachable))
                                                     if med_reachable is not None and med_unreachable is not None
                                                     and med_reachable + med_unreachable > 0 else None),
                            "coverage_fraction": (mean_assessed / base_n if base_n else None),
                            "baseline_core_count": member_distribution([r["baseline_core_count"] for r in category_rows], "facilities"),
                            "baseline_core_reachable_count_distribution": member_distribution([r["reachable_count"] for r in category_rows], "facilities"),
                            "unreachable_from_anchor_count": member_distribution([r["unreachable_count"] for r in category_rows], "facilities"),
                            "outside_baseline_core_count": member_distribution([r["outside_baseline_core_count"] for r in category_rows], "facilities"),
                            "reachable_count_distribution": member_distribution([r["reachable_count"] for r in category_rows], "facilities"),
                            "unreachable_count_distribution": member_distribution([r["unreachable_count"] for r in category_rows], "facilities"),
                            "coverage_fraction_mean": (mean_assessed / base_n if base_n else None),
                            "interpretation": "Counts are median across ensemble members; distributions preserve member variation. Access is only a coarse connected-component proxy.",
                        })
                    access_loss = [1.0 - sum(r[k]["reachable_count"] for k in ("hospital", "shelter", "candidate_shelter")) /
                                   max(1, sum(r[k]["baseline_core_count"] for k in ("hospital", "shelter", "candidate_shelter")))
                                   for r in cascades
                                   if sum(r[k]["baseline_core_count"] for k in ("hospital", "shelter", "candidate_shelter")) > 0]
                    sensitivity.append({
                        "threshold_m": threshold,
                        "population_exposed_known_people": member_distribution(values["pop"], "people", _distribution_status(values["pop"], coverage_flags[float(threshold)])),
                        "affected_road_length_m": member_distribution(values["road"], "m", _distribution_status(values["road"], coverage_flags[float(threshold)])),
                        "mapped_facilities_exposed_count": member_distribution(values["facility"], "facilities", _distribution_status(values["facility"], coverage_flags[float(threshold)])),
                        "facility_access_loss_fraction": member_distribution(access_loss, "fraction"),
                        "facility_access_by_category": access_categories,
                    })
                primary = sensitivity[primary_ix]
                cascade_members = member_vals[float(DEFAULT_THRESHOLD_M)]["access"].get("cascade", [])
                access_by_category = primary["facility_access_by_category"]
                primary["facility_access_loss_fraction"]["status"] = (
                    "PARTIAL" if facility_meta["unassessed_target_facility_count"] > 0 else
                    primary["facility_access_loss_fraction"]["status"]
                )
                valid_cells = int(np.isfinite(stack[:, eligible]).sum())
                eligible_member_cells = int(eligible.sum() * stack.shape[0])
                pop_unknown_30m = int(pop_nodata_grid.sum())
                pop_known_cma = float(np.nansum(pop_grid))
                coverage = {
                    "population": {"assessed_count": int(pop_known_count_grid[eligible].sum()),
                                   "eligible_count": int(pop_known_count_grid[eligible].sum() + pop_unknown_30m),
                                   "nodata_count": pop_unknown_30m,
                                   "fraction_assessed": (float(pop_known_count_grid[eligible].sum()) /
                                                         float(pop_known_count_grid[eligible].sum() + pop_unknown_30m)) if (pop_known_count_grid[eligible].sum() + pop_unknown_30m) else None},
                    "roads": {"assessed_count": int(road_meta_all["midpoint_assessed_edge_count"]),
                              "eligible_count": int(road_meta_all["source_feature_count"]),
                              "nodata_count": int(road_meta_all["midpoint_unassessed_edge_count"]),
                                   "fraction_assessed": float(road_meta_all["midpoint_assessed_edge_count"] / max(1, road_meta_all["source_feature_count"])),
                                   "coverage_basis": "source road-segment midpoint maps to an eligible 600 m model cell"},
                    "facilities": {"assessed_count": int(facility_meta["mapped_target_facility_count"]),
                                   "eligible_count": int(facility_meta["mapped_target_facility_count"] + facility_meta["unassessed_target_facility_count"]),
                                   "nodata_count": int(facility_meta["unassessed_target_facility_count"]),
                                   "fraction_assessed": float(facility_meta["mapped_target_facility_count"] / max(1, facility_meta["mapped_target_facility_count"] + facility_meta["unassessed_target_facility_count"])),
                                   "coverage_basis": "target OSM facilities located in eligible 600 m solver cells"},
                    "hazard_grid": {"assessed_count": valid_cells, "eligible_count": eligible_member_cells,
                                    "nodata_count": eligible_member_cells-valid_cells,
                                    "fraction_assessed": float(valid_cells/max(1,eligible_member_cells))},
                }
                refs = [
                    {"source_id": "A05_FORECAST_ENSEMBLE", "source_sha256": sha256(npz_path), "version": "batch2_v1", "role": "simulated_depth_ensemble"},
                    {"source_id": "OSM_ROAD_AND_FACILITY_GPKG", "source_sha256": sha256(GPKG), "version": "existing extracted OSM layer", "role": "road_graph_and_facilities"},
                    {"source_id": "WORLDPOP_STATIC_CELL_TABLE", "source_sha256": sha256(CELL_TABLE), "version": "cell_table.parquet", "role": "population exposure with explicit NoData"},
                ]
                result = {
                    "schema_id": SCHEMA_ID, "schema_version": SCHEMA_VERSION,
                    "result_id": f"a07-batch2-v4-{event_key}-{scenario_key}-lead{int(horizon):02d}h",
                    "run_id": 7004, "run_version": "batch2_v4_contract",
                    "source_mode": "SIMULATED",
                    "event": {"event_key": event_key, "event_start_utc": event_start.isoformat().replace("+00:00", "Z"),
                              "event_end_utc": event_end.isoformat().replace("+00:00", "Z"), "time_basis": "UTC"},
                    "valid_at_utc": valid_at.isoformat().replace("+00:00", "Z"),
                    "aggregation_interval": None,
                    "aggregation_basis": "INSTANTANEOUS_SIMULATED_STATE_AT_VALID_TIME; no temporal aggregate was computed",
                    "generated_at_utc": generated_at,
                    "scenario_key": scenario_key,
                    "thresholds": {"road_block_depth_m": DEFAULT_THRESHOLD_M,
                                   "road_threshold_is_assumption": True,
                                   "sensitivity_depth_thresholds_m": list(THRESHOLDS_M),
                                   "mapped_facility_exposure_threshold_m": DEFAULT_THRESHOLD_M,
                                   "population_exposure_threshold_m": DEFAULT_THRESHOLD_M,
                                   "exposure_thresholds_are_assumptions": True},
                    "metrics": {
                        "population_exposed_people": {**primary["population_exposed_known_people"],
                            "interpretation": "Known WorldPop estimate in cells whose simulated depth meets the threshold; incomplete where population NoData or hazard coverage occurs; not a census count."},
                        "affected_road_length_m": primary["affected_road_length_m"],
                        "affected_facilities_count": primary["mapped_facilities_exposed_count"],
                    "facility_access_loss_fraction": primary["facility_access_loss_fraction"],
                    },
                    "facility_access_by_category": access_by_category,
                    "sensitivity": sensitivity,
                    "coverage": coverage,
                    "uncertainty": {"method": "20-member A05/A06 parameter and rainfall scenario ensemble",
                                    "ensemble_id": f"{event_key}:{scenario_key}", "member_count": int(len(member_ids)),
                                    "interpretation": "Descriptive scenario/member spread only, not calibrated statistical uncertainty."},
                    "provenance": {"sources": refs, "algorithm": "600m cell exposure and collapsed OSM road-cell connectivity",
                                   "algorithm_version": "A07-batch2-v4-contract",
                                   "code_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                                                  check=True, capture_output=True, text=True).stdout.strip(),
                                   "parameters": {"road_and_exposure_thresholds_m": list(THRESHOLDS_M),
                                                  "road_sample": "road segment midpoint", "connectivity": "endpoint cells, largest baseline connected component",
                                                  "grid_cell_m": int(summary["grid_cell_size_m"]), "member_count": int(len(member_ids))},
                                   "grid": {"crs": str(summary["crs"]), "resolution_m": int(summary["grid_cell_size_m"])}},
                    "qc_flags": ["DERIVED_SIMULATED_NOT_LIVE", "COARSE_600M_ROAD_MIDPOINT_SAMPLE",
                                 "ACCESS_IS_COARSE_COMPONENT_PROXY_NOT_ROUTING", "WORLDPOP_NOData_NOT_ZERO",
                                 "EXPOSURE_DEPTH_THRESHOLD_IS_ASSUMPTION", "ENSEMBLE_SPREAD_NOT_CALIBRATED",
                                 "C7_SCHEMA_IS_LANE_A_DRAFT_NOT_APPROVED_OR_FROZEN"],
                    "event_reference_note": event_data.get("reference_note"),
                }
                validate_impact_result(result)
                event_lines.append(_json_safe(result))
                per_combo.append({"event_key": event_key, "scenario_key": scenario_key,
                                  "horizon_hours": int(horizon), "valid_at_utc": valid_at.isoformat().replace("+00:00", "Z"),
                                  "member_count": int(len(member_ids)),
                                  "population_known_people_mean_030m": primary["population_exposed_known_people"]["mean"],
                                  "affected_road_length_m_mean_030m": primary["affected_road_length_m"]["mean"],
                                  "facilities_exposed_mean_030m": primary["mapped_facilities_exposed_count"]["mean"],
                                  "hazard_coverage_fraction": coverage["hazard_grid"]["fraction_assessed"]})

    pq.write_table(pa.Table.from_pandas(pd.DataFrame(member_records), preserve_index=False),
                   OUTPUT / "member_impact_metrics.parquet", compression="zstd", version="2.6")
    pq.write_table(pa.Table.from_pandas(pd.concat(cell_tables, ignore_index=True), preserve_index=False),
                   OUTPUT / "cell_impact.parquet", compression="zstd", version="2.6")
    (OUTPUT / "impact_results.jsonl").write_text("".join(json.dumps(x, allow_nan=False) + "\n" for x in event_lines), encoding="utf-8")
    input_files = [SUMMARY, CELL_TABLE, GPKG, ROOT / "data/features/simulation/batch2_v1/simulation_summary.json"]
    input_hashes = {str(p.relative_to(ROOT)): sha256(p) for p in input_files if p.exists()}
    run_summary = {
        "task": "A07 Phase 13 ensemble impact analysis", "status": "DERIVED_SIMULATED_IMPACT_NOT_LIVE",
        "output_revision": "batch2_v4_contract; batch2_v1 preserved; batch2_v2 partial and batch2_v3 complete-but-superseded attempts preserved after contract validation fixes",
        "schema_id": SCHEMA_ID, "schema_version": SCHEMA_VERSION,
        "schema_status": "Lane A proposal only; G0 not ready; no shared contract freeze or API integration",
        "generated_at_utc": generated_at, "run_time_seconds": time.perf_counter() - start,
        "device": "CPU NumPy/Pandas/PyArrow; no GPU computation used",
        "grid": {"shape": [height, width], "eligible_cells": int(eligible.sum()), "resolution_m": int(summary["grid_cell_size_m"]), "crs": str(summary["crs"])},
        "event_scenario_horizon_combinations": len(per_combo), "member_time_records": len(member_records),
        "sensitivity_thresholds_m": list(THRESHOLDS_M), "default_threshold_m": DEFAULT_THRESHOLD_M,
        "worldpop": {k: v for k, v in pop_meta_all.items() if k != "valid_count"},
        "roads": road_meta_all, "facilities": facility_meta,
        "baseline_core_cell_count": int(len(baseline_cells)), "baseline_core_anchor_cell_id": baseline_anchor,
        "combo_summary": per_combo,
        "outputs": {"results": "impact_results.jsonl", "edge_cell_index": "road_edge_grid_index.parquet",
                    "cell_metrics": "cell_impact.parquet", "member_metrics": "member_impact_metrics.parquet"},
        "input_sha256": input_hashes,
        "limitations": ["A05 records are hindcasts/scenario contrasts, not operational forecasts.",
                        "The 600 m grid is much coarser than roads. Edge depth is sampled at the segment midpoint.",
                        "The access cascade collapses the OSM graph to 600 m cells and compares to the largest baseline component; it is not OD routing, travel-time reachability, facility operational status, or safe-access validation.",
                        "NoData in population or depth is kept as unassessed; reported exposed population is the known-data portion only.",
                        "Facility/population exposure depth threshold equals the road sensitivity threshold only as an explicit screening assumption.",
                        "The current G0 C7 proposal is not approved or frozen; API/UI compatibility remains for integrator review."],
    }
    (OUTPUT / "run_summary.json").write_text(json.dumps(_json_safe(run_summary), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    report = make_report(run_summary, event_lines)
    REPORT.write_text(report, encoding="utf-8")
    return run_summary


def make_report(summary: dict, results: list[dict]) -> str:
    lines = [
        "# Phase 13 Batch 2 impact analysis",
        "",
        "**Status:** DERIVED simulated impact scenarios; not live impact estimates, hydraulic truth, or emergency guidance. The C7 JSON shape is the Lane A `impact-result-v0.1-draft` proposal only; G0 is not ready, so this is not an approved/frozen API or database contract.",
        "",
        "## Method",
        "",
        f"- Input ensemble: {summary['event_scenario_horizon_combinations']} event × scenario × horizon cases; {summary['member_time_records']} member-threshold rows; {summary['grid']['eligible_cells']} eligible cells on a {summary['grid']['resolution_m']} m {summary['grid']['crs']} grid.",
        "- This run aligns `run_id` to the C7 proposal's integer type and carries complete per-category cascade fields; earlier v1-v3 outputs are preserved unchanged.",
        f"- Edge depth is the simulated depth at each road segment midpoint on the 600 m grid. Each edge can join to its cell probability in `data/features/impact/batch2_v1/road_edge_grid_index.parquet` → `cell_impact.parquet`.",
        "- Blocked when depth is at or above 0.30 m; sensitivity screens are 0.15 and 0.50 m. These are assumptions, not locally validated closure/exposure thresholds.",
        "- Each horizon is an instantaneous simulated state at event-window UTC start plus lead hours. No temporal aggregation interval is claimed.",
        "- WorldPop is summed from CMA-limited 30 m static cells into the 600 m solver cells. The known-data sum is reported separately from NoData; unknown cells are not zero.",
        "- Facilities are mapped OSM points. Hospital and shelter categories are reported separately; OSM schools and colleges form an assumed candidate-shelter group.",
        "- Access cascade uses road endpoints collapsed to 600 m cells. A mapped facility counts connected when its cell remains in a component intersecting the largest pre-event road component. This is not origin-destination routing or a measure of facility operation.",
        "",
        "## Coverage and source inventory",
        "",
        f"- Road source features: {summary['roads']['source_feature_count']:,}; midpoint-assessed edges: {summary['roads']['midpoint_assessed_edge_count']:,} ({summary['roads']['midpoint_assessed_road_length_m']/1000:,.1f} km); outside/unassessed on this model grid: {summary['roads']['midpoint_unassessed_edge_count']:,}.",
        f"- Target facilities mapped: {summary['facilities']['mapped_target_facility_count']:,}; by group: {summary['facilities']['mapped_counts_by_cascade_group']}.",
        f"- WorldPop known CMA cell-table sum within eligible model cells: {summary['worldpop']['known_population_sum_people_model_domain']:,.1f}; source NoData 30 m cells mapped there: {summary['worldpop']['population_nodata_source_cells']:,}. Values are model estimates, not census counts.",
        "",
        "## Selected 0.30 m ensemble summaries",
        "",
        f"Full result distributions and all three threshold screens are in `{OUTPUT.relative_to(ROOT).as_posix()}/impact_results.jsonl`; per-member metrics are in Parquet.",
        "",
        "| Event | Scenario | Lead (h) | Known population in depth-screened cells, mean people | Screened road length, mean km | Mapped facilities screened, mean | Hazard coverage |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in summary.get("combo_summary", []):
        vals = [r.get("event_key"), r.get("scenario_key"), str(r.get("horizon_hours")),
                f"{r['population_known_people_mean_030m']:,.1f}" if r.get("population_known_people_mean_030m") is not None else "not computed",
                f"{r['affected_road_length_m_mean_030m']/1000:,.2f}" if r.get("affected_road_length_m_mean_030m") is not None else "not computed",
                f"{r['facilities_exposed_mean_030m']:,.1f}" if r.get("facilities_exposed_mean_030m") is not None else "not computed",
                f"{r['hazard_coverage_fraction']:.3f}" if r.get("hazard_coverage_fraction") is not None else "not computed"]
        lines.append("| " + " | ".join(vals) + " |")
    lines += [
        "",
        "## Interpretation and limits",
        "",
        "- Percentiles are descriptive spread over the 20 fixed simulation members; they are not calibrated confidence intervals.",
        "- A05 hindcasts are not operational forecast skill. The source contains no archived numerical weather prediction forecast for these dates.",
        "- Coarse midpoint sampling can miss local road flooding, bridges, tunnels, drainage, and sub-cell variation. Facility cascades are only a coarse graph-connectivity proxy.",
        "- Exposed population is the known WorldPop estimate in screened cells. If any contributing population pixels are NoData, known-data totals are incomplete and the result is flagged PARTIAL.",
        "- No capacity allocation, shelter demand assignment, route travel time, or safe evacuation path is computed here.",
        "- This local output proposal needs integrator approval and API/UI reconciliation before any shared contract or endpoint consumes it.",
        "",
        "## Reproduction",
        "",
        "`.venv/Scripts/python.exe -m pipelines.phase13.impact` (writes `batch2_v4_contract`; the script refuses to overwrite existing outputs).",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    result = run()
    result["combo_summary"] = []
    print(json.dumps({"status": result["status"], "runtime_seconds": result["run_time_seconds"],
                      "cases": result["event_scenario_horizon_combinations"],
                      "member_threshold_rows": result["member_time_records"],
                      "outputs": result["outputs"]}, indent=2))


if __name__ == "__main__":
    main()
