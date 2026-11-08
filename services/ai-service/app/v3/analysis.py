"""Derived C4 v3 products from a run's depth frames: summary, buildings, roads, routes, shelters, incidents, plans."""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree

from . import config
from .static import Grid, Product

STATE_PASSABLE, STATE_BLOCKED, STATE_UNKNOWN = 0, 1, 2
STATE_NAMES = ("ASSESSED_PASSABLE", "ASSESSED_BLOCKED", "UNKNOWN")
SPEED_FLOOR, SPEED_REDUCTION_AT_THRESHOLD = 0.20, 0.80  # A08 assumptions
NON_VEHICLE = {"footway", "path", "pedestrian", "steps", "cycleway", "track"}
WALK_SPEED_KMH = 5.0
EMERGENCY_SPEED_FACTOR = 1.25
SNAP_LIMIT_M = 1500.0
DEPTH_CLASSES = ((0.0, "dry"), (0.15, "lt_0_15"), (0.5, "0_15_to_0_5"), (1.0, "0_5_to_1_0"))
HEIGHT_SOURCES = ("osm_height", "osm_levels", "estimated")
SEVERITY_ORDER = ("info", "watch", "warning", "critical")


def r2(value) -> float | None:
    if value is None:
        return None
    value = float(value)
    return None if not math.isfinite(value) else round(value, 2)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def depth_class(depth: float | None) -> str:
    if depth is None or not math.isfinite(depth):
        return "unknown"
    if depth <= 0:
        return "dry"
    if depth < 0.15:
        return "lt_0_15"
    if depth < 0.5:
        return "0_15_to_0_5"
    if depth <= 1.0:
        return "0_5_to_1_0"
    return "gt_1_0"


def risk_level(max_depth: float | None, fraction: float | None) -> str:
    d, f = max_depth or 0.0, fraction or 0.0
    if d >= 1.0 or f >= 0.5:
        return "severe"
    if d >= 0.5 or f >= 0.25:
        return "high"
    if d >= 0.15 or f >= 0.05:
        return "moderate"
    return "low"


# --------------------------------------------------------------------------------------------------- depth access
def frame_depth(frames: dict, frame_index: int | None, layer: str = "depth_mean") -> np.ndarray:
    stack = frames[layer]
    if frame_index is None:
        with np.errstate(all="ignore"):
            return np.nanmax(stack, axis=0) if np.isfinite(stack).any() else stack[0]
    return stack[frame_index]


def peak_until(frames: dict, frame_index: int | None) -> tuple[np.ndarray, np.ndarray]:
    """Per-cell max of depth_mean over frames 0..frame_index (all frames if None) and its frame index."""
    stack = frames["depth_mean"] if frame_index is None else frames["depth_mean"][: frame_index + 1]
    filled = np.where(np.isfinite(stack), stack, -1.0)
    return np.where(np.isfinite(stack[0]), filled.max(axis=0), np.nan), filled.argmax(axis=0)


# --------------------------------------------------------------------------------------------------- roads
def segment_states(product: Product, depth: np.ndarray, threshold_m: float, seg_cell: np.ndarray | None = None):
    """A21/A08 three-state rule per road segment: ordinary blocked at threshold, tunnels at half, bridges UNKNOWN.
    ``seg_cell`` maps segments onto the depth grid (Grid.seg_cell); defaults to the 600 m A06 mapping."""
    roads = product.roads
    cells = roads["seg_cell"] if seg_cell is None else seg_cell
    flat = depth.ravel()
    d = np.where(cells >= 0, flat[np.clip(cells, 0, None)], np.nan)
    structure = roads["seg_structure"]
    thr = np.where(structure == 1, threshold_m / 2.0, threshold_m)
    finite = np.isfinite(d)
    state = np.full(len(cells), STATE_UNKNOWN, np.uint8)
    state[finite & (d < thr)] = STATE_PASSABLE
    state[finite & (d >= thr)] = STATE_BLOCKED
    speed = np.full(len(cells), np.nan, np.float32)
    speed[finite & (d <= 0)] = 1.0
    reduced = finite & (d > 0) & (d < thr)
    speed[reduced] = np.maximum(SPEED_FLOOR, 1.0 - SPEED_REDUCTION_AT_THRESHOLD * d[reduced] / thr[reduced])
    speed[state == STATE_BLOCKED] = 0.0
    reason = np.full(len(cells), None, dtype=object)
    reason[cells < 0] = "NO_MODEL_CELL"
    reason[(cells >= 0) & ~finite] = "UNKNOWN_NODATA"
    special = np.isin(structure, [2, 3, 4])
    state[special] = STATE_UNKNOWN
    speed[special] = np.nan
    reason[special] = "UNASSESSED_STRUCTURE"
    return state, speed, d, reason


def roads_blocked_km(product: Product, depth: np.ndarray, threshold_m: float = config.DEFAULT_BLOCK_THRESHOLD_M,
                     seg_cell: np.ndarray | None = None) -> float:
    state, *_ = segment_states(product, depth, threshold_m, seg_cell)
    return float(product.roads["seg_length_m"][state == STATE_BLOCKED].sum() / 1000.0)


def segment_coords(product: Product, i: int) -> list[list[float]]:
    roads = product.roads
    a, b = roads["seg_coord_offsets"][i], roads["seg_coord_offsets"][i + 1]
    return [[round(float(x), 6), round(float(y), 6)] for x, y in zip(roads["seg_coord_lon"][a:b], roads["seg_coord_lat"][a:b])]


def bbox_filter(lon, lat, bbox):
    if bbox is None:
        return np.ones(len(lon), bool)
    w, s, e, n = bbox
    return (lon >= w) & (lon <= e) & (lat >= s) & (lat <= n)


# --------------------------------------------------------------------------------------------------- routing
class Router:
    """Directed road graph with per-arc state for one depth field."""

    def __init__(self, product: Product, depth: np.ndarray | None, threshold_m: float, profile: str,
                 seg_cell: np.ndarray | None = None):
        roads = product.roads
        self.product = product
        n_seg = len(roads["seg_cell"])
        if depth is None:
            seg_state = np.zeros(n_seg, np.uint8)
            seg_speed = np.ones(n_seg, np.float32)
            seg_depth = np.zeros(n_seg)
        else:
            seg_state, seg_speed, seg_depth, _ = segment_states(product, depth, threshold_m, seg_cell)
        hw_names = roads["highway_names"]
        seg = roads["arc_segment"]
        frm, to = roads["arc_from"], roads["arc_to"]
        length = roads["arc_length_m"].astype(np.float64)
        speed = roads["arc_speed_kmh"].astype(np.float64)
        keep = np.ones(len(seg), bool)
        if profile == "walk":
            frm, to = np.concatenate([frm, to]), np.concatenate([to, frm])
            seg, length = np.concatenate([seg, seg]), np.concatenate([length, length])
            speed = np.full(len(seg), WALK_SPEED_KMH)
            keep = np.ones(len(seg), bool)
        else:
            highway = hw_names[roads["seg_highway"][seg]]
            keep = ~np.isin(highway, list(NON_VEHICLE))
            if profile == "emergency_vehicle":
                speed = speed * EMERGENCY_SPEED_FACTOR
        self.frm, self.to, self.seg, self.length = frm[keep], to[keep], seg[keep], length[keep]
        self.speed_kmh = speed[keep]
        self.state = seg_state[self.seg]
        factor = seg_speed[self.seg]
        self.factor = np.where(np.isfinite(factor), factor, 1.0)
        self.depth = seg_depth[self.seg]
        self.base_time = self.length * 3.6 / np.maximum(self.speed_kmh, 0.1)
        self.n = len(roads["node_lon"])
        self._matrices: dict[str, tuple] = {}
        used = np.zeros(self.n, bool)
        used[self.frm] = True
        used[self.to] = True
        self.nodes = np.flatnonzero(used)
        mx, my = _metric(roads["node_lon"][self.nodes], roads["node_lat"][self.nodes])
        self.tree = cKDTree(np.column_stack([mx, my]))

    def snap(self, lon: float, lat: float) -> tuple[int, float]:
        dist, idx = self.tree.query(list(_metric(lon, lat)))
        return int(self.nodes[idx]), float(dist)

    def snap_many(self, lon, lat) -> tuple[np.ndarray, np.ndarray]:
        mx, my = _metric(lon, lat)
        dist, idx = self.tree.query(np.column_stack([mx, my]))
        return self.nodes[idx], dist

    def weights(self, policy: str) -> np.ndarray:
        passable = self.state == STATE_PASSABLE
        unknown = self.state == STATE_UNKNOWN
        time = self.base_time / np.maximum(self.factor, SPEED_FLOOR)
        if policy == "avoid_blocked_and_unknown":
            return np.where(passable, time, np.inf)
        if policy == "avoid_blocked":
            return np.where(passable, time, np.where(unknown, self.base_time * 1.5, np.inf))
        if policy == "shortest_dry":
            return np.where(passable, self.base_time / np.maximum(self.factor, SPEED_FLOOR) ** 2, np.inf)
        if policy == "dry_baseline":
            return self.base_time
        raise ValueError(policy)

    def _matrix(self, policy: str):
        if policy in self._matrices:
            return self._matrices[policy]
        w = self.weights(policy)
        ok = np.isfinite(w)
        f, t, ww, arcs = self.frm[ok], self.to[ok], w[ok], np.flatnonzero(ok)
        order = np.lexsort((ww, t, f))
        f, t, ww, arcs = f[order], t[order], ww[order], arcs[order]
        first = np.ones(len(f), bool)
        first[1:] = (f[1:] != f[:-1]) | (t[1:] != t[:-1])
        f, t, ww, arcs = f[first], t[first], np.maximum(ww[first], 1e-6), arcs[first]
        matrix = csr_matrix((ww, (f, t)), shape=(self.n, self.n))
        keys = f.astype(np.int64) * self.n + t  # already sorted by (f, t)
        self._matrices[policy] = (matrix, keys, arcs)
        return self._matrices[policy]

    def shortest(self, policy: str, source: int, target: int):
        matrix, keys, arcs = self._matrix(policy)
        dist, pred = dijkstra(matrix, directed=True, indices=source, return_predecessors=True)
        if not np.isfinite(dist[target]):
            return None
        nodes = [target]
        while nodes[-1] != source:
            nodes.append(int(pred[nodes[-1]]))
        nodes.reverse()
        pairs = np.asarray(nodes[:-1], np.int64) * self.n + np.asarray(nodes[1:], np.int64)
        return [int(a) for a in arcs[np.searchsorted(keys, pairs)]]

    def times_from(self, policy: str, source: int) -> np.ndarray:
        matrix, _, _ = self._matrix(policy)
        return dijkstra(matrix, directed=True, indices=source)

    def option(self, policy: str, path: list[int] | None, status_override: str | None = None) -> dict:
        if path is None:
            return {"policy": policy, "route_status": "NO_ROUTE", "distance_m": None, "travel_time_s": None, "geometry": None,
                    "length_by_state_m": {"ASSESSED_PASSABLE": 0.0, "ASSESSED_BLOCKED": 0.0, "UNKNOWN": 0.0},
                    "max_depth_on_route_m": None}
        idx = np.asarray(path, dtype=np.int64)
        by_state = {name: round(float(self.length[idx][self.state[idx] == code].sum()), 1) for code, name in enumerate(STATE_NAMES)}
        if status_override:
            status = status_override
        elif by_state["ASSESSED_BLOCKED"] > 0 or by_state["UNKNOWN"] > 0:
            status = "CONDITIONAL"
        else:
            status = "ASSESSED_PASSABLE"
        t = self.base_time[idx] / (1.0 if policy == "dry_baseline" else np.maximum(self.factor[idx], SPEED_FLOOR))
        roads = self.product.roads
        coords = [[round(float(roads["node_lon"][self.frm[idx[0]]]), 6), round(float(roads["node_lat"][self.frm[idx[0]]]), 6)]]
        for arc in idx:
            node = self.to[arc]
            coords.append([round(float(roads["node_lon"][node]), 6), round(float(roads["node_lat"][node]), 6)])
        depths = self.depth[idx]
        finite = depths[np.isfinite(depths)]
        return {"policy": policy, "route_status": status, "distance_m": round(float(self.length[idx].sum()), 1),
                "travel_time_s": round(float(t.sum()), 1), "geometry": {"type": "LineString", "coordinates": coords},
                "length_by_state_m": by_state, "max_depth_on_route_m": r2(max(finite.max(), 0.0)) if finite.size else None}

    @property
    def open_nodes(self) -> np.ndarray:
        if not hasattr(self, "_open"):
            ok = self.state != STATE_BLOCKED
            self._open = (np.bincount(self.frm[ok], minlength=self.n) + np.bincount(self.to[ok], minlength=self.n)) > 0
        return self._open

    def node_has_open_arc(self, node: int) -> bool:
        return bool(self.open_nodes[node])

    @property
    def components(self) -> np.ndarray:
        if not hasattr(self, "_components"):
            passable = self.state == STATE_PASSABLE
            graph = csr_matrix((np.ones(int(passable.sum())), (self.frm[passable], self.to[passable])), shape=(self.n, self.n))
            self._components = connected_components(graph, directed=False)[1]
        return self._components


# --------------------------------------------------------------------------------------------------- buildings
def building_depths(grid: Grid, product: Product, frames: dict, frame_index: int | None):
    peak, argmax = peak_until(frames, frame_index)
    cells = grid.building_cell(product)
    ok = cells >= 0
    depth = np.full(len(cells), np.nan)
    depth[ok] = peak.ravel()[cells[ok]]
    when = np.full(len(cells), -1)
    when[ok] = argmax.ravel()[cells[ok]]
    return depth, when


def buildings_affected(grid: Grid, product: Product, peak: np.ndarray) -> int:
    cells = grid.building_cell(product)
    d = np.where(cells >= 0, peak.ravel()[np.clip(cells, 0, None)], np.nan)
    return int(np.sum(d >= config.FLOOD_THRESHOLD_M))


# --------------------------------------------------------------------------------------------------- summary
def summary(grid: Grid, product: Product | None, frames: dict, frame_times: list[str], frame_index: int | None = None) -> dict:
    peak, _ = peak_until(frames, frame_index)
    active = grid.active
    land = active & (grid.arrays["landcover"] != 80)  # permanent water is not "flooded" (as A25)
    cell_km2 = (grid.cell_size_m / 1000.0) ** 2
    flooded = land & (np.nan_to_num(peak, nan=0.0) >= config.FLOOD_THRESHOLD_M)
    pop = np.where(active, grid.arrays["population"], 0.0)
    stack = frames["depth_mean"] if frame_index is None else frames["depth_mean"][: frame_index + 1]
    areas = [(np.nan_to_num(f, nan=0.0)[land] >= config.FLOOD_THRESHOLD_M).sum() for f in stack]
    wards = grid.arrays.get("ward_id")
    peak_idx = int(np.argmax(areas)) if len(areas) else 0
    return {
        "max_depth_m": r2(np.nanmax(peak[active])) if active.any() else None,
        "flooded_area_km2": r2(flooded.sum() * cell_km2),
        "buildings_affected": buildings_affected(grid, product, peak) if product else None,
        "population_exposed": int(round(float(np.nansum(pop[flooded])))),
        "roads_blocked_km": r2(roads_blocked_km(product, peak, seg_cell=grid.seg_cell(product))) if product else None,
        "wards_affected": int(np.unique(wards[flooded & (wards > 0)]).size) if wards is not None else None,
        "peak_time_utc": frame_times[peak_idx] if frame_times else None,
    }


# --------------------------------------------------------------------------------------------------- shelters
def shelter_report(grid: Grid, product: Product, depth: np.ndarray, capacity_factor: float, router: "Router",
                   threshold_m: float = config.DEFAULT_BLOCK_THRESHOLD_M) -> tuple[list[dict], dict]:
    """B-lane method: demand = population of cells at >= threshold; greedy nearest assignment within components of
    passable arcs (walk graph). Capacities are assumed (100/250/500 people) times capacity_factor."""
    component = router.components
    flat = depth.ravel()
    shelters = []
    s_nodes, s_dist = router.snap_many([s["lon"] for s in product.shelters], [s["lat"] for s in product.shelters])
    for s, cell, node, dist in zip(product.shelters, grid.shelter_cells(product), s_nodes, s_dist):
        node = int(node)
        site = flat[cell] if cell >= 0 else np.nan
        reachable = bool(np.isfinite(site) and site < threshold_m and dist <= SNAP_LIMIT_M and router.node_has_open_arc(node))
        shelters.append({**s, "node": node, "site": site, "reachable": reachable,
                         "capacity": int(round(s["capacity_people"] * capacity_factor)), "assigned": 0})
    pop = grid.arrays["population"]
    demand_cells = np.flatnonzero((grid.active & (np.nan_to_num(depth, nan=0.0) >= threshold_m)).ravel())
    demand_total, unreachable = 0, 0
    open_by_comp: dict[int, list[dict]] = {}
    for s in shelters:
        if s["reachable"]:
            open_by_comp.setdefault(int(component[s["node"]]), []).append(s)
    lon, lat = grid.arrays["cell_lon"].ravel(), grid.arrays["cell_lat"].ravel()
    served = 0
    ordered = demand_cells[np.argsort(-flat[demand_cells])]
    cell_nodes = dict(zip(ordered.tolist(), router.snap_many(lon[ordered], lat[ordered])[0].tolist())) if ordered.size else {}
    for cell in ordered:
        people = int(round(float(pop.ravel()[cell]))) if np.isfinite(pop.ravel()[cell]) else 0
        if people <= 0:
            continue
        demand_total += people
        node = cell_nodes[int(cell)]
        candidates = open_by_comp.get(int(component[node]), [])
        if not candidates:
            unreachable += people
            continue
        remaining = people
        for s in sorted(candidates, key=lambda x: (x["lon"] - lon[cell]) ** 2 + (x["lat"] - lat[cell]) ** 2):
            take = min(remaining, s["capacity"] - s["assigned"])
            if take > 0:
                s["assigned"] += take
                remaining -= take
            if remaining == 0:
                break
        served += people - remaining
    out = []
    wards = grid.ward_at(grid.shelter_cells(product))
    for s, ward in zip(shelters, wards):
        out.append({"shelter_id": s["shelter_id"], "name": s["name"], "category": s["category"],
                    "location": {"lon": s["lon"], "lat": s["lat"]}, "ward_id": ward,
                    "capacity_people": s["capacity"], "capacity_source": s["capacity_source"],
                    "site_max_depth_m": r2(max(s["site"], 0.0)) if np.isfinite(s["site"]) else None,
                    "reachable": s["reachable"], "assigned_population": s["assigned"] if s["reachable"] else 0,
                    "utilisation_pct": r2(100.0 * s["assigned"] / s["capacity"]) if s["capacity"] else None})
    totals = {"demand_people": demand_total, "served_people": served, "unserved_people": demand_total - served,
              "unreachable_people": unreachable, "reachable_shelters": sum(1 for s in shelters if s["reachable"])}
    return out, totals


def _metric(lon, lat):
    """Local equirectangular metres (adequate for nearest-node snapping over the CMA extent)."""
    k = 111320.0
    return np.asarray(lon) * k * math.cos(math.radians(13.0)), np.asarray(lat) * k


# --------------------------------------------------------------------------------------------------- incidents
def incidents(grid: Grid, product: Product, frames: dict, frame_times: list[str], frame_index: int | None,
              whatif: dict | None, shelters: list[dict] | None) -> list[dict]:
    depth = frame_depth(frames, frame_index)
    when = frame_times[frame_index] if frame_index is not None else (frame_times[-1] if frame_times else iso(datetime.now(timezone.utc)))
    flat = np.nan_to_num(depth, nan=-1.0).ravel()
    lon, lat = grid.arrays["cell_lon"].ravel(), grid.arrays["cell_lat"].ravel()
    pop = np.nan_to_num(grid.arrays["population"], nan=0.0).ravel()
    bcells = grid.building_cell(product)
    bcount = np.bincount(bcells[bcells >= 0], minlength=flat.size)
    cells = grid.seg_cell(product)
    state, _, _, _ = segment_states(product, depth, config.DEFAULT_BLOCK_THRESHOLD_M, cells)
    roads = product.roads
    blocked = state == STATE_BLOCKED
    blocked_km = np.bincount(cells[blocked & (cells >= 0)], weights=roads["seg_length_m"][blocked & (cells >= 0)], minlength=flat.size) / 1000
    out = []

    def add(kind, severity, cell, title, metrics, location=None):
        loc = location or {"lon": round(float(lon[cell]), 6), "lat": round(float(lat[cell]), 6)}
        out.append({"incident_id": f"inc-{kind}-{cell}", "generated": True, "generated_from": "simulation", "type": kind,
                    "severity": severity, "ward_id": grid.ward_at([cell])[0], "location": loc, "valid_time_utc": when, "title": title,
                    "metrics": metrics})

    for cell in np.flatnonzero((flat >= config.FLOOD_THRESHOLD_M) & (bcount > 0)):
        d = flat[cell]
        severity = "critical" if d >= 1.0 else "warning" if d >= 0.5 else "watch"
        add("building_flooding", severity, int(cell), f"{int(bcount[cell])} buildings in a cell at {d:.2f} m",
            {"depth_m": r2(d), "buildings": float(bcount[cell])})
    for cell in np.flatnonzero(blocked_km >= 0.5):
        km = blocked_km[cell]
        add("road_blocked", "critical" if km >= 3 else "warning" if km >= 1 else "watch", int(cell),
            f"{km:.1f} km of road blocked", {"blocked_km": r2(km), "depth_m": r2(flat[cell])})
    for cell in np.flatnonzero((flat >= config.DEFAULT_BLOCK_THRESHOLD_M) & (pop >= 500)):
        p = pop[cell]
        add("population_cut_off", "critical" if p >= 5000 else "warning" if p >= 2000 else "watch", int(cell),
            f"~{int(p):,} people in a cell at {flat[cell]:.2f} m", {"population": float(round(p)), "depth_m": r2(flat[cell])})
    for s in shelters or []:
        if not s["reachable"]:
            site = s.get("site_max_depth_m")
            add("shelter_unreachable", "warning" if (site or 0) >= config.DEFAULT_BLOCK_THRESHOLD_M else "watch",
                grid.cells_near(s["location"]["lon"], s["location"]["lat"]), f"Shelter unreachable: {s['name']}"[:120],
                {"site_depth_m": site, "capacity_people": float(s["capacity_people"])}, s["location"])
            out[-1]["incident_id"] = f"inc-shelter_unreachable-{s['shelter_id'].replace(':', '_')}"
    for name, release in ((whatif or {}).get("reservoir_release_m3s") or {}).items():
        from .simulate import RESERVOIRS
        (rlon, rlat), *_rest, capacity = RESERVOIRS[name]
        if release > 0:
            add("reservoir_release", "warning" if release > capacity else "info", grid.cells_near(rlon, rlat),
                f"{name.title()} release {release:g} m3/s (scenario)", {"release_m3s": float(release), "assumed_bankfull_m3s": capacity},
                {"lon": rlon, "lat": rlat})
            out[-1]["incident_id"] = f"inc-reservoir_release-{name.lower()}"
    out.sort(key=lambda i: (-SEVERITY_ORDER.index(i["severity"]), i["incident_id"]))
    return out


# --------------------------------------------------------------------------------------------------- emergency plan
RESOURCE_FOR = {
    "building_flooding": ("boat", "rescue_team"),
    "population_cut_off": ("boat", "rescue_team", "ambulance"),
    "road_blocked": ("pump", "vehicle"),
    "shelter_unreachable": ("vehicle", "rescue_team"),
}
SPEED_KMH = {"boat": 10.0, "rescue_team": 20.0, "vehicle": 30.0, "ambulance": 35.0, "pump": 25.0}


def emergency_plan(router: "Router", incident_list: list[dict], resources: list[dict]) -> tuple[list, list]:
    """Greedy: incidents by severity; each takes one unit of the nearest suitable resource with units left.
    ``router`` is the emergency_vehicle graph for the run's depth field."""
    remaining = {r["resource_id"]: int(r["count"]) for r in resources}
    times: dict[tuple, np.ndarray] = {}

    def road_eta(resource, node, policy):
        key = (resource["resource_id"], policy)
        if key not in times:
            base, _ = router.snap(resource["base"]["location"]["lon"], resource["base"]["location"]["lat"])
            times[key] = router.times_from(policy, base)
        return times[key][node]

    assignments, unassigned = [], []
    for inc in incident_list:
        kinds = RESOURCE_FOR.get(inc["type"])
        if not kinds:
            continue
        loc = inc["location"]
        options = [r for r in resources if r["type"] in kinds and remaining[r["resource_id"]] > 0]
        if not options:
            unassigned.append(inc["incident_id"])
            continue
        best = min(options, key=lambda r: (kinds.index(r["type"]), _km(r["base"]["location"], loc)))
        remaining[best["resource_id"]] -= 1
        if best["type"] == "boat":
            eta, status = _km(best["base"]["location"], loc) * 1.3 / SPEED_KMH["boat"] * 3600, None
        else:
            node, _ = router.snap(loc["lon"], loc["lat"])
            t_pass = road_eta(best, node, "avoid_blocked_and_unknown")
            if np.isfinite(t_pass):
                eta, status = t_pass, "ASSESSED_PASSABLE"
            else:
                t_cond = road_eta(best, node, "avoid_blocked")
                eta, status = (t_cond, "CONDITIONAL") if np.isfinite(t_cond) else (None, "NO_ROUTE")
            if eta is not None:
                eta *= SPEED_KMH["vehicle"] * EMERGENCY_SPEED_FACTOR / SPEED_KMH[best["type"]] if best["type"] != "vehicle" else 1.0
        assignments.append({"incident_id": inc["incident_id"], "resource_id": best["resource_id"], "units": 1,
                            "eta_s": r2(eta) if eta is not None else None, "route_status": status})
    return assignments, unassigned


def _km(a: dict, b: dict) -> float:
    dx = (a["lon"] - b["lon"]) * 111.32 * math.cos(math.radians(13.0))
    dy = (a["lat"] - b["lat"]) * 111.32
    return math.hypot(dx, dy)


def frame_times(start: datetime, n: int, minutes: int) -> list[str]:
    return [iso(start + timedelta(minutes=minutes * (k + 1))) for k in range(n)]
