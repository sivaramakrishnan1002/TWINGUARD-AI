"""A25 scenario runner: one entry point for event / custom / forecast / what-if flood runs at 30-120 m.

Lane B (B47) calls ``run_scenario(...)`` (or ``python -m services.flood_engine.scenario_cli``) and serves the run
directory with ``services.flood_engine.products``. Outputs follow C4 v3 (GridSpec, Frame, DepthFrame, BuildingDepth,
WardSummary, RoadFeatureCollection, ShelterReport). NumPy only; SciPy is used for road connectivity if installed.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from . import hires

ENGINE_VERSION = "twinguard-flood-engine/2.0.0"
STATIC_VERSION = "a25_static_v1"
FLOOD_M = 0.10            # SimulationSummary "flooded" / "affected" threshold (C4 v3)
BLOCKED_M = 0.30          # A08/A21 road threshold (ASSESSED_BLOCKED at or above)
SHELTER_DRY_M = 0.15      # C4 v3 Shelter.reachable: site depth below this
MAIN_NETWORK_NODES = 1000 # shelter is reachable if its road node sits in a passable component at least this large
DEPTH_CLASSES = ("dry", "lt_0_15", "0_15_to_0_5", "0_5_to_1_0", "gt_1_0", "unknown")
# Ensemble members: (label, manning multiplier, infiltration multiplier); low/high bracket central.
MEMBERS = {1: [("central", 1.0, 1.0)],
           3: [("central", 1.0, 1.0), ("low", 0.75, 1.5), ("high", 2.0, 0.5)]}
LIMITATIONS = [
    "Simulated with a simplified local-inertial model on the GLO-30 surface DEM; no storm-drain network.",
    "Event rainfall is spatially uniform (IMERG daily, ERA5 hourly shape); forecast rainfall is Open-Meteo model output.",
    "Reservoir releases enter at one river cell per reservoir; tide is a constant sea-level offset.",
    "Building heights are mostly estimated; ward risk levels and road states are model-derived display classes.",
    "Not validated against observed depths; for research and demonstration only.",
]


class ScenarioError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


class StaticBundle:
    def __init__(self, root: Path, name: str):
        self.root = Path(root)
        self.dir = self.root / name
        if not (self.dir / "static.npz").exists():
            raise ScenarioError(f"static grid {name} is not installed under {self.root}")
        with np.load(self.dir / "static.npz", allow_pickle=False) as b:
            self.a = {k: b[k] for k in b.files}
        self.meta = json.loads((self.dir / "meta.json").read_text(encoding="utf-8"))
        self.grid = self.meta["grid"]
        self.name = name

    @property
    def shape(self):
        return self.a["z"].shape

    def hires_grid(self, manning_mult=1.0, infil_mult=1.0) -> hires.HiresGrid:
        a = self.a
        return hires.HiresGrid(a["z"], a["active"], a["boundary"], a["mann"] * manning_mult, a["porosity"],
                               a["infiltration_mm_h"] * infil_mult, float(self.grid["cell_size_m"]))


def grid_name(resolution: str, focus_area: str | None, cell_m: int = 120) -> str:
    if resolution == "citywide":
        return f"citywide_{cell_m}m"
    if resolution == "focus":
        if focus_area not in {"VELACHERY", "ADYAR", "T_NAGAR", "PORUR"}:
            raise ScenarioError("focus_area must be one of VELACHERY, ADYAR, T_NAGAR, PORUR")
        return f"focus_30m_{focus_area}"
    raise ScenarioError("resolution must be citywide or focus")


def load_events(static_root: Path) -> dict:
    doc = json.loads((Path(static_root) / "shared/events.json").read_text(encoding="utf-8"))
    return {e["event_key"]: e for e in doc["events"]}


# ----------------------------------------------------------------------------------------------- forcing
def build_forcing(request: dict, static_root: Path, bundle: StaticBundle, runs_root: Path, fetch_forecast=None) -> dict:
    """Return {start, interval_s, rain_mm ([n] or [n,rows,cols]), inputs[], stage_m, releases{}}."""
    mode = request["mode"]
    inputs = []
    if mode == "what_if":
        wi = request.get("what_if") or {}
        base = load_run(runs_root, wi.get("base_run_id", ""))
        if base is None:
            raise ScenarioError("what_if.base_run_id not found")
        base_req = dict(base["request"])
        base_req["duration_hours"] = request.get("duration_hours", base_req.get("duration_hours", 24))
        f = build_forcing(base_req, static_root, bundle, runs_root, fetch_forecast)
        scale = float(wi.get("rainfall_scale_pct", 100.0)) / 100.0
        if not 0 <= scale <= 3:
            raise ScenarioError("rainfall_scale_pct must be 0-300")
        f["rain_mm"] = f["rain_mm"] * scale
        f["stage_m"] = float(f.get("stage_m", 0.0)) + float(wi.get("tide_offset_m", 0.0))
        rel = dict(f.get("releases", {}))
        for k, v in (wi.get("reservoir_release_m3s") or {}).items():
            if k not in {"CHEMBARAMBAKKAM", "POONDI", "PUZHAL", "CHOLAVARAM"} or not 0 <= float(v) <= 3000:
                raise ScenarioError(f"invalid reservoir release {k}={v}")
            rel[k] = float(v)
        f["releases"] = rel
        f["inputs"] = f["inputs"] + [{"name": "what_if", "source": f"base {wi['base_run_id']}; rain x{scale:.2f}; tide {wi.get('tide_offset_m', 0.0)} m; releases {rel}", "source_mode": "SCENARIO_INPUT", "fetched_at": None, "sha256": None}]
        return f
    if mode == "event":
        events = load_events(static_root)
        ev = events.get(request.get("event_key"))
        if ev is None:
            raise ScenarioError(f"unknown event_key; available: {sorted(events)}")
        rain = np.asarray(ev["values_mm"], float)
        inputs.append({"name": "rainfall", "source": ev["rainfall_source"], "source_mode": "REPLAY", "fetched_at": None,
                       "sha256": hashlib.sha256(json.dumps(ev["values_mm"]).encode()).hexdigest()})
        return {"start": _parse(ev["start_utc"]), "interval_s": 3600.0, "rain_mm": rain, "inputs": inputs, "stage_m": 0.0, "releases": {}}
    if mode == "custom":
        cr = request.get("custom_rainfall") or {}
        vals = np.asarray(cr.get("values_mm", []), float)
        interval = int(cr.get("interval_minutes", 60))
        if interval not in (15, 30, 60) or not 1 <= len(vals) <= 288 or (vals < 0).any() or (vals > 200).any():
            raise ScenarioError("custom_rainfall needs interval_minutes 15/30/60 and 1-288 values in 0-200 mm")
        inputs.append({"name": "rainfall", "source": "user custom rainfall (uniform areal)", "source_mode": "SCENARIO_INPUT", "fetched_at": None,
                       "sha256": hashlib.sha256(vals.tobytes()).hexdigest()})
        return {"start": _parse(cr["start_time_utc"]), "interval_s": interval * 60.0, "rain_mm": vals, "inputs": inputs, "stage_m": 0.0, "releases": {}}
    if mode == "forecast":
        from . import forcing as fm
        snap = (fetch_forecast or fm.fetch_snapshot)(_bounds(bundle))
        model = snap.usable[0]
        a = bundle.a
        field = fm.map_to_grid(model, a["cell_lat"].astype(float), a["cell_lon"].astype(float), a["active"] | a["boundary"])
        field = np.nan_to_num(field[fm.PAST_HOURS:], nan=0.0)
        start = _parse(model.times_utc[fm.PAST_HOURS] + ":00Z") - timedelta(hours=1)
        inputs.append({"name": "rainfall", "source": f"open-meteo:{model.model}", "source_mode": "MODEL_FORECAST", "fetched_at": snap.fetched_at,
                       "sha256": model.response_sha256})
        return {"start": start, "interval_s": 3600.0, "rain_mm": field.astype(np.float32), "inputs": inputs, "stage_m": 0.0, "releases": {}}
    raise ScenarioError("mode must be event, custom, forecast or what_if")


def _bounds(bundle: StaticBundle):
    return bundle.grid["bbox_wgs84"]


# ----------------------------------------------------------------------------------------------- nesting
def nested_boundary_fn(child: StaticBundle, parent_dir: Path, parent: StaticBundle, frame_s: float, stage_sea: float):
    """Stage for child boundary cells from the parent run's water surface, linearly interpolated in time."""
    with np.load(parent_dir / "frames.npz", allow_pickle=False) as b:
        pframes = b["depth_cm"]
    pg = parent.grid
    a = child.a
    bidx = np.flatnonzero(a["boundary"] & ~a["active"])
    rows, cols = np.divmod(bidx, child.grid["cols"])
    x = child.grid["origin_x_m"] + (cols + 0.5) * child.grid["cell_size_m"]
    y = child.grid["origin_y_m"] - (rows + 0.5) * child.grid["cell_size_m"]
    pc = np.floor((x - pg["origin_x_m"]) / pg["cell_size_m"]).astype(int)
    pr = np.floor((pg["origin_y_m"] - y) / pg["cell_size_m"]).astype(int)
    ok = (pr >= 0) & (pr < pg["rows"]) & (pc >= 0) & (pc < pg["cols"])
    pidx = np.where(ok, pr * pg["cols"] + pc, 0)
    pz = parent.a["z"].ravel()[pidx].astype(np.float32)
    seaf = parent.a["boundary"].ravel()[pidx] & ~parent.a["active"].ravel()[pidx]
    flat = pframes.reshape(pframes.shape[0], -1)

    def stage(t):
        k = min(t / frame_s, pframes.shape[0] - 1)
        k0 = int(np.floor(k))
        k1 = min(k0 + 1, pframes.shape[0] - 1)
        w = k - k0
        d0 = flat[k0, pidx].astype(np.float32)
        d1 = flat[k1, pidx].astype(np.float32)
        nod = (d0 == hires.NODATA_CM) | (d1 == hires.NODATA_CM) | ~ok
        depth = ((1 - w) * d0 + w * d1) / 100.0
        eta = np.where(depth > 0.01, pz + depth, -1e3)  # dry parent cell -> no imposed water (acts as outflow)
        eta = np.where(nod, -1e3, eta)
        return np.where(seaf, stage_sea, eta).astype(np.float32)

    return stage


# ----------------------------------------------------------------------------------------------- products
def depth_class(d: np.ndarray) -> np.ndarray:
    out = np.full(d.shape, 5, np.int8)
    fin = np.isfinite(d)
    out[fin & (d < 0.01)] = 0
    out[fin & (d >= 0.01) & (d < 0.15)] = 1
    out[fin & (d >= 0.15) & (d < 0.5)] = 2
    out[fin & (d >= 0.5) & (d < 1.0)] = 3
    out[fin & (d >= 1.0)] = 4
    return out


def risk_level(depth_p95: float | None, flooded_fraction: float | None) -> str:
    """Ward display class from the ward's 95th-percentile peak depth on land cells and its flooded fraction
    (peak >= 0.10 m): severe if p95 >= 1.0 m and >= 10% flooded, or >= 25% flooded; high if p95 >= 0.5 m and
    >= 5% flooded; moderate if p95 >= 0.15 m or >= 5% flooded; otherwise low. A percentile, not the maximum, so a
    single DEM pit does not classify a whole ward."""
    m = depth_p95 or 0.0
    f = flooded_fraction or 0.0
    if (m >= 1.0 and f >= 0.10) or f >= 0.25:
        return "severe"
    if m >= 0.5 and f >= 0.05:
        return "high"
    if m >= 0.15 or f >= 0.05:
        return "moderate"
    return "low"


def ward_summaries(static_root: Path, bundle: "StaticBundle", run_dir: Path, peak_k: int) -> list[dict]:
    """C4 v3 WardSummary rows rebuilt from a run directory's saved files."""
    a = bundle.a
    land = a["active"] & (a["landcover"] != 80)
    cell_km2 = (bundle.grid["cell_size_m"] / 1000.0) ** 2
    with np.load(run_dir / "peak.npz", allow_pickle=False) as b:
        peak = b["depth_mean"].astype(np.float64)
    with np.load(run_dir / "buildings.npz", allow_pickle=False) as b:
        bidx, bdepth = b["index"], b["max_depth_m"]
    with np.load(run_dir / "road_states.npz", allow_pickle=False) as b:
        seg, states = b["segment_index"], b["state"]
    with np.load(run_dir / "shelters.npz", allow_pickle=False) as b:
        sidx, reach = b["shelter_index"], b["reachable"][peak_k]
    with np.load(Path(static_root) / "shared/buildings.npz", allow_pickle=False) as b:
        bward = b["ward_id"][bidx]
    with np.load(Path(static_root) / "shared/roads.npz", allow_pickle=False) as b:
        rlen, road_ward = b["length_m"][seg], b["ward_id"][seg]
    with np.load(Path(static_root) / "shared/shelters.npz", allow_pickle=False) as b:
        shelter_ward = b["ward_id"][sidx]
    blocked = (states == 1).any(axis=0)
    wid = a["ward_id"]
    pop = np.nan_to_num(a["population"], nan=0.0)
    flooded = land & np.isfinite(peak) & (peak >= FLOOD_M)
    wards_doc = json.loads((Path(static_root) / "shared/wards.geojson").read_text(encoding="utf-8"))
    names = {f["properties"]["ward_id"]: (f["properties"]["ward_name"], f["properties"].get("zone")) for f in wards_doc["features"]}
    rows = []
    for w in sorted(n for n in names if 1 <= n <= 200):
        m = land & (wid == w)
        if not m.any():
            continue
        vals = peak[m]
        fm_ = flooded & m
        frac = float(fm_.sum() / m.sum())
        p95 = float(np.nanpercentile(vals, 95))
        rows.append({
            "ward_id": int(w), "ward_name": names[w][0], "zone": names[w][1],
            "max_depth_m": round(float(np.nanmax(vals)), 2), "depth_p95_m": round(p95, 2),
            "mean_flooded_depth_m": round(float(np.nanmean(peak[fm_])), 2) if fm_.any() else 0.0,
            "flooded_area_km2": round(float(fm_.sum() * cell_km2), 3), "flooded_fraction": round(frac, 4),
            "buildings_affected": int(np.count_nonzero((bward == w) & (np.nan_to_num(bdepth, nan=0) >= FLOOD_M))),
            "population_exposed": int(round(float(pop[fm_].sum()))),
            "roads_blocked_km": round(float(rlen[blocked & (road_ward == w)].sum()) / 1000.0, 2),
            "shelters_reachable": int(reach[shelter_ward == w].sum()),
            "risk_level": risk_level(p95, frac), "assessed_area_km2": round(float(m.sum() * cell_km2), 3),
        })
    return rows


def rebuild_wards(static_root, runs_root, run_id: str) -> dict:
    """Recompute wards.json and summary.wards_affected for an existing run (no re-simulation)."""
    run_dir = Path(runs_root) / run_id
    doc = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    bundle = StaticBundle(Path(static_root), doc["provenance"]["static_bundle"])
    peak_k = next(f["index"] for f in doc["frames"] if f["valid_time_utc"] == doc["summary"]["peak_time_utc"])
    rows = ward_summaries(Path(static_root), bundle, run_dir, peak_k)
    (run_dir / "wards.json").write_text(json.dumps({"run_id": run_id, "wards": rows, "risk_rule": risk_level.__doc__.strip()}, indent=1), encoding="utf-8")
    doc["summary"]["wards_affected"] = int(sum(1 for w in rows if w["risk_level"] != "low"))
    (run_dir / "run.json").write_text(json.dumps(doc, indent=1, allow_nan=False), encoding="utf-8")
    return doc


def road_states(depth_cm_frame: np.ndarray, road_cell: np.ndarray, structure: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """A21 three-state rule per road segment: 0 ASSESSED_PASSABLE, 1 ASSESSED_BLOCKED, 2 UNKNOWN; depth (m, NaN unknown)."""
    flat = depth_cm_frame.ravel()
    inside = road_cell >= 0
    d = np.full(road_cell.shape, np.nan, np.float32)
    raw = flat[np.where(inside, road_cell, 0)]
    good = inside & (raw != hires.NODATA_CM) & ~structure
    d[good] = raw[good] / 100.0
    state = np.full(road_cell.shape, 2, np.uint8)
    state[good & (d < BLOCKED_M)] = 0
    state[good & (d >= BLOCKED_M)] = 1
    return state, d


def speed_factor(depth_m: np.ndarray) -> np.ndarray:
    """Pregnolato et al. (2017) depth-disruption curve, normalised to free flow; 0 at/above 0.30 m."""
    mm = np.clip(np.nan_to_num(depth_m, nan=0.0) * 1000.0, 0, 300)
    v = 0.0009 * mm ** 2 - 0.5529 * mm + 86.9448
    sf = np.clip(v / 86.9448, 0, 1)
    sf[np.nan_to_num(depth_m, nan=0.0) >= BLOCKED_M] = 0.0
    return sf.astype(np.float32)


def _components(n_nodes: int, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    try:
        from scipy.sparse import coo_matrix
        from scipy.sparse.csgraph import connected_components
        m = coo_matrix((np.ones(len(a), np.int8), (a, b)), shape=(n_nodes, n_nodes))
        return connected_components(m, directed=False)[1]
    except ImportError:  # vectorised min-label propagation with pointer jumping
        lab = np.arange(n_nodes)
        while True:
            old = lab.copy()
            m = np.minimum(lab[a], lab[b])
            np.minimum.at(lab, a, m)
            np.minimum.at(lab, b, m)
            lab = lab[lab]
            lab = lab[lab]
            if np.array_equal(lab, old):
                return lab


def shelter_reachability(states: np.ndarray, topo: dict, shelter_node: np.ndarray, site_depth: np.ndarray) -> np.ndarray:
    passable = states[topo["seg_index"]] == 0
    lab = _components(topo["n_nodes"], topo["a"][passable], topo["b"][passable])
    sizes = np.bincount(lab, minlength=topo["n_nodes"])
    ok_node = shelter_node >= 0
    big = np.zeros(len(shelter_node), bool)
    big[ok_node] = sizes[lab[shelter_node[ok_node]]] >= MAIN_NETWORK_NODES
    return big & np.isfinite(site_depth) & (site_depth < SHELTER_DRY_M)


def _road_topology(static_root: Path, road_cell: np.ndarray) -> dict:
    with np.load(Path(static_root) / "shared/road_topology.npz", allow_pickle=False) as t:
        node_a, node_b = t["node_a"], t["node_b"]
    keep = np.flatnonzero((road_cell >= 0) & (node_a >= 0) & (node_b >= 0))
    nodes, inv = np.unique(np.r_[node_a[keep], node_b[keep]], return_inverse=True)
    return {"seg_index": keep, "a": inv[: len(keep)], "b": inv[len(keep):], "n_nodes": len(nodes), "nodes": nodes}


def _shelter_nodes(static_root: Path, topo: dict, shelters: dict) -> np.ndarray:
    with np.load(Path(static_root) / "shared/road_topology.npz", allow_pickle=False) as t:
        nid, nx, ny = t["node_id"], t["node_x"], t["node_y"]
    pos = np.searchsorted(nid, topo["nodes"])
    pos = np.clip(pos, 0, len(nid) - 1)
    gx, gy = nx[pos], ny[pos]
    out = np.full(len(shelters["x"]), -1, np.int64)
    if not len(gx):
        return out
    # nearest graph node within 500 m (grid hash for speed)
    cell = 250.0
    key = (np.floor(gx / cell).astype(np.int64) << 32) + np.floor(gy / cell).astype(np.int64)
    order = np.argsort(key)
    skey = key[order]
    for i, (x, y) in enumerate(zip(shelters["x"], shelters["y"])):
        best, bd = -1, 500.0 ** 2
        cx, cy = int(np.floor(x / cell)), int(np.floor(y / cell))
        for dx in (-2, -1, 0, 1, 2):
            for dy in (-2, -1, 0, 1, 2):
                k = ((cx + dx) << 32) + (cy + dy)
                lo, hi = np.searchsorted(skey, k), np.searchsorted(skey, k, side="right")
                if hi > lo:
                    cand = order[lo:hi]
                    d2 = (gx[cand] - x) ** 2 + (gy[cand] - y) ** 2
                    j = int(np.argmin(d2))
                    if d2[j] < bd:
                        bd, best = float(d2[j]), int(cand[j])
        out[i] = best
    return out


# ----------------------------------------------------------------------------------------------- run
def request_key(request: dict) -> str:
    canon = json.dumps(request, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()


def load_run(runs_root: Path, run_id: str) -> dict | None:
    if not run_id or "/" in run_id or "\\" in run_id or ".." in run_id:
        return None
    p = Path(runs_root) / run_id / "run.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def find_cached(runs_root: Path, key: str) -> dict | None:
    root = Path(runs_root)
    if not root.exists():
        return None
    for d in sorted((x for x in root.iterdir() if x.is_dir() and x.name[:4] in ("sim-", "evt-", "whati")), reverse=True):
        if (d / "run.json").exists():
            doc = json.loads((d / "run.json").read_text(encoding="utf-8"))
            if doc.get("request_key") == key and doc.get("state") == "completed":
                return doc
    return None


def run_scenario(static_root, runs_root, *, mode: str, event_key: str | None = None, custom_rainfall: dict | None = None,
                 what_if: dict | None = None, duration_hours: int = 24, resolution: str = "citywide", focus_area: str | None = None,
                 frame_interval_minutes: int = 30, members: int = 1, citywide_cell_m: int = 120, threads: int | None = None,
                 fetch_forecast=None, progress=None, use_cache: bool = True) -> dict:
    """Run one simulation and write it under ``runs_root/<run_id>/``. Returns the SimulationRun document.

    ``progress`` is called as progress(pct) with 0-100 across all members (simulation phase only).
    Safe to call in a child process; writes are atomic (``.tmp-<run_id>`` then rename).

    Identical requests return the cached run (``state`` stays ``completed`` and ``cached`` is true).
    """
    static_root, runs_root = Path(static_root), Path(runs_root)
    if not 6 <= int(duration_hours) <= 72:
        raise ScenarioError("duration_hours must be 6-72")
    if frame_interval_minutes not in (15, 30):
        raise ScenarioError("frame_interval_minutes must be 15 or 30")
    if members not in MEMBERS:
        raise ScenarioError("members must be 1 or 3")
    request = {"mode": mode, "event_key": event_key, "custom_rainfall": custom_rainfall, "what_if": what_if,
               "duration_hours": int(duration_hours), "resolution": resolution, "focus_area": focus_area,
               "frame_interval_minutes": int(frame_interval_minutes)}
    request = {k: v for k, v in request.items() if v is not None}
    key = request_key({**request, "members": members, "cell": citywide_cell_m, "engine": ENGINE_VERSION})
    if use_cache and mode != "forecast":
        cached = find_cached(runs_root, key)
        if cached:
            return {**cached, "cached": True}
    bundle = StaticBundle(static_root, grid_name(resolution, focus_area, citywide_cell_m))
    t0 = time.perf_counter()
    created = _now()
    forcing = build_forcing(request, static_root, bundle, runs_root, fetch_forecast)
    duration_s = int(duration_hours) * 3600.0
    frame_s = frame_interval_minutes * 60.0
    rain = forcing["rain_mm"]
    forcing_sha = hashlib.sha256(np.ascontiguousarray(rain, np.float32).tobytes() + json.dumps(
        {"stage": forcing["stage_m"], "rel": forcing["releases"]}, sort_keys=True).encode()).hexdigest()
    prefix = {"event": "evt", "what_if": "whatif"}.get(mode, "sim")  # C4 v3 run_id pattern
    run_id = f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{key[:8]}"
    inflows = []
    for name, q in forcing["releases"].items():
        cell = bundle.meta.get("inflow_cells", {}).get(name)
        if cell and q > 0:
            inflows.append((cell["row"], cell["col"], q))
    boundary_fn = None
    parent_run = None
    if resolution == "focus":
        parent_req = {k: v for k, v in request.items() if k not in ("resolution", "focus_area")}
        parent_run = run_scenario(static_root, runs_root, **{**parent_req, "resolution": "citywide"}, members=1,
                                  citywide_cell_m=citywide_cell_m, threads=threads, fetch_forecast=fetch_forecast, use_cache=True)
        parent_bundle = StaticBundle(static_root, grid_name("citywide", None, citywide_cell_m))
        boundary_fn = nested_boundary_fn(bundle, runs_root / parent_run["run_id"], parent_bundle,
                                         parent_run["frame_interval_minutes"] * 60.0, forcing["stage_m"])
    results = []
    n_members = len(MEMBERS[members])
    for i_member, (label, nm, fi) in enumerate(MEMBERS[members]):
        cb = (lambda f, i=i_member: progress(round(100.0 * (i + f) / n_members, 1))) if progress else None
        r = hires.run(bundle.hires_grid(nm, fi), rain, forcing["interval_s"], duration_s, frame_s, stage_m=forcing["stage_m"],
                      inflows=inflows, boundary_stage_fn=boundary_fn, threads=threads, progress=cb)
        if not np.isfinite(r.peak_m[bundle.a["active"]]).all() or np.nanmin(r.peak_m) < 0:
            raise RuntimeError(f"invalid depths in member {label}")
        if boundary_fn is None and r.diagnostics["mass_balance_relative_error"] > 0.01:
            raise RuntimeError(f"mass balance > 1% in member {label}: {r.diagnostics['mass_balance_relative_error']:.4g}")
        results.append((label, r))
    central = results[0][1]
    out = runs_root / f".tmp-{run_id}"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    start = forcing["start"]
    frames = [{"index": k, "valid_time_utc": _iso(start + timedelta(minutes=m)), "elapsed_minutes": m} for k, m in enumerate(central.frame_minutes)]
    peaks = {"depth_mean": central.peak_m}
    if members == 3:
        stack = np.stack([r.peak_m for _, r in results])
        peaks["depth_p05"] = np.where(bundle.a["active"], stack.min(axis=0), np.nan)  # bracket members, not statistical quantiles
        peaks["depth_p95"] = np.where(bundle.a["active"], stack.max(axis=0), np.nan)
    np.savez_compressed(out / "frames.npz", depth_cm=central.frames_cm, frame_minutes=np.asarray(central.frame_minutes, np.int32))
    np.savez_compressed(out / "peak.npz", peak_frame=central.peak_frame, velocity_mps=central.peak_speed_mps,
                        **{k: v.astype(np.float32) for k, v in peaks.items()})

    a = bundle.a
    act = a["active"]
    # Permanent water (WorldCover class 80 at the cell centre) is excluded from "flooded" statistics; its depth stays in the grids.
    land = act & (a["landcover"] != 80)
    cell_km2 = (bundle.grid["cell_size_m"] / 1000.0) ** 2
    peak = central.peak_m
    # Buildings
    with np.load(static_root / "shared/buildings.npz", allow_pickle=False) as bz:
        bward = bz["ward_id"]
        osmid = bz["osmid"]
    bcell = a["building_cell"]
    bin_ = bcell >= 0
    bdepth = np.full(len(bcell), np.nan, np.float32)
    bdepth[bin_] = peak.ravel()[bcell[bin_]]
    bframe = np.full(len(bcell), -1, np.int16)
    bframe[bin_] = central.peak_frame.ravel()[bcell[bin_]]
    np.savez_compressed(out / "buildings.npz", index=np.flatnonzero(bin_).astype(np.int32), max_depth_m=bdepth[bin_],
                        peak_frame=bframe[bin_], depth_class=depth_class(bdepth[bin_]))
    # Roads and shelters per frame
    with np.load(static_root / "shared/roads.npz", allow_pickle=False) as rz:
        rlen, structure = rz["length_m"], rz["structure"]
    rcell = a["road_cell"]
    road_frames = np.zeros((len(frames), len(rcell)), np.uint8)
    for k in range(len(frames)):
        road_frames[k], _ = road_states(central.frames_cm[k], rcell, structure)
    in_grid = rcell >= 0
    np.savez_compressed(out / "road_states.npz", state=road_frames[:, in_grid], segment_index=np.flatnonzero(in_grid).astype(np.int32))
    with np.load(static_root / "shared/shelters.npz", allow_pickle=False) as sz:
        shelters = {k: sz[k] for k in sz.files}
    scell = a["shelter_cell"]
    topo = _road_topology(static_root, rcell)
    snode = _shelter_nodes(static_root, topo, shelters)
    s_in = scell >= 0
    reach = np.zeros((len(frames), len(scell)), bool)
    flat_frames = central.frames_cm.reshape(len(frames), -1)
    for k in range(len(frames)):
        site = np.full(len(scell), np.nan, np.float32)
        raw = flat_frames[k, np.where(s_in, scell, 0)]
        site[s_in & (raw != hires.NODATA_CM)] = raw[s_in & (raw != hires.NODATA_CM)] / 100.0
        reach[k] = shelter_reachability(road_frames[k], topo, snode, site)
    site_peak = np.full(len(scell), np.nan, np.float32)
    site_peak[s_in] = peak.ravel()[scell[s_in]]
    np.savez_compressed(out / "shelters.npz", reachable=reach[:, s_in], shelter_index=np.flatnonzero(s_in).astype(np.int32),
                        site_peak_m=site_peak[s_in], road_node=snode[s_in])
    # Peak frame (max flooded area)
    flooded_by_frame = [(int(np.count_nonzero((f[land] != hires.NODATA_CM) & (f[land] >= FLOOD_M * 100)))) for f in central.frames_cm]
    peak_k = int(np.argmax(flooded_by_frame))
    # Wards
    pop = np.nan_to_num(a["population"], nan=0.0)
    flooded = land & np.isfinite(peak) & (peak >= FLOOD_M)
    blocked_peak = (road_frames == 1).any(axis=0)
    ward_rows = ward_summaries(static_root, bundle, out, peak_k)
    (out / "wards.json").write_text(json.dumps({"run_id": run_id, "wards": ward_rows,
                                                "risk_rule": risk_level.__doc__.strip()}, indent=1), encoding="utf-8")
    summary = {
        "max_depth_m": round(float(np.nanmax(np.where(land, peak, np.nan))), 2),
        "flooded_area_km2": round(float(flooded.sum() * cell_km2), 3),
        "buildings_affected": int(np.count_nonzero(np.nan_to_num(bdepth, nan=0) >= FLOOD_M)),
        "population_exposed": int(round(float(pop[flooded].sum()))),
        "roads_blocked_km": round(float(rlen[blocked_peak].sum()) / 1000.0, 2),
        "wards_affected": int(sum(1 for w in ward_rows if w["risk_level"] != "low")),
        "peak_time_utc": frames[peak_k]["valid_time_utc"],
    }
    diags = {label: {k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.diagnostics.items()} for label, r in results}
    labels = {"event": f"{(load_events(static_root).get(event_key) or {}).get('label', event_key)} (simulated)",
              "custom": "Custom rainfall (simulated)", "forecast": "Open-Meteo forecast (simulated)", "what_if": "What-if scenario (simulated)"}
    doc = {
        "run_id": run_id, "state": "completed", "mode": mode, "request": request, "request_key": key, "source_mode": "SIMULATED",
        "label": labels[mode] + ("" if resolution == "citywide" else f" · {focus_area} 30 m"),
        "created_at": created, "completed_at": _now(), "progress_pct": 100, "error": None, "cached": False,
        "grid": bundle.grid, "frame_interval_minutes": int(frame_interval_minutes), "frames": frames, "summary": summary,
        "members": [m[0] for m in MEMBERS[members]], "layers": sorted(peaks) + ["velocity_mps"],
        "forcing": {"start_utc": _iso(start), "interval_minutes": int(forcing["interval_s"] // 60), "total_mm_domain_mean": round(float(rain.sum() if rain.ndim == 1 else np.nanmean(rain.sum(axis=0)[act])), 2),
                    "tide_offset_m": forcing["stage_m"], "reservoir_release_m3s": forcing["releases"], "inflow_cells_used": len(inflows)},
        "parent_run_id": parent_run["run_id"] if parent_run else None,
        "provenance": {"engine_version": ENGINE_VERSION, "run_id": run_id, "forcing_sha256": forcing_sha, "static_assets_version": STATIC_VERSION,
                       "static_bundle": bundle.name, "static_bundle_sha256": bundle.meta.get("bundle_sha256"), "inputs": forcing["inputs"]},
        "diagnostics": diags, "runtime_seconds": round(time.perf_counter() - t0, 1), "limitations": LIMITATIONS,
        "files": sorted(p.name for p in out.iterdir()) + ["run.json"],
    }
    (out / "run.json").write_text(json.dumps(doc, indent=1, allow_nan=False), encoding="utf-8")
    os.replace(out, runs_root / run_id)
    return doc
