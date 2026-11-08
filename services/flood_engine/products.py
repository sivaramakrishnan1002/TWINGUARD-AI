"""Read-side helpers that turn an A25 run directory into C4 v3 response bodies (NumPy only).

Lane B maps each /v3 operation to one function here; every function returns plain JSON-serialisable dicts.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import hires
from .scenario import BLOCKED_M, DEPTH_CLASSES, FLOOD_M, StaticBundle, load_events, load_run, road_states, shelter_reachability, speed_factor, _road_topology

HEIGHT_SOURCES = ("osm_height", "osm_levels", "estimated")
ROAD_STATES = ("ASSESSED_PASSABLE", "ASSESSED_BLOCKED", "UNKNOWN")


class NotFound(LookupError):
    pass


def _run(runs_root, run_id) -> dict:
    doc = load_run(Path(runs_root), run_id)
    if doc is None:
        raise NotFound(run_id)
    return doc


def _bundle(static_root, doc) -> StaticBundle:
    return StaticBundle(Path(static_root), doc["provenance"]["static_bundle"])


def _bbox(bbox):
    if bbox is None:
        return None
    if isinstance(bbox, str):
        bbox = [float(v) for v in bbox.split(",")]
    w, s, e, n = bbox
    if not (w < e and s < n):
        raise ValueError("bbox must be west,south,east,north")
    return w, s, e, n


def _cursor(cursor) -> int:
    return int(cursor) if cursor not in (None, "") else 0


def list_runs(runs_root, limit: int = 20) -> dict:
    root = Path(runs_root)
    docs = []
    if root.exists():
        for d in sorted((x for x in root.iterdir() if x.is_dir() and not x.name.startswith(".")), reverse=True):
            if (d / "run.json").exists():
                docs.append(json.loads((d / "run.json").read_text(encoding="utf-8")))
            if len(docs) >= limit:
                break
    return {"runs": docs, "next_cursor": None}


def get_run(runs_root, run_id) -> dict:
    return _run(runs_root, run_id)


def events(static_root) -> dict:
    return {"events": [{k: e[k] for k in ("event_key", "label", "start_utc", "end_utc", "rainfall_source", "source_mode")}
                       for e in load_events(Path(static_root)).values()]}


def depth_frame(runs_root, run_id, frame_index: int | None = None, layer: str = "depth_mean") -> dict:
    """C4 v3 DepthFrame. frame_index None = peak. Values rounded to 0.01 m; null outside the domain."""
    doc = _run(runs_root, run_id)
    d = Path(runs_root) / run_id
    if layer not in ("depth_mean", "depth_p05", "depth_p95", "velocity_mps"):
        raise ValueError("unknown layer")
    if frame_index is None:
        with np.load(d / "peak.npz", allow_pickle=False) as b:
            if layer not in b.files:
                raise NotFound(f"layer {layer} not in this run (members={doc.get('members')})")
            arr = b[layer].astype(np.float64)
        valid_time = doc["summary"].get("peak_time_utc")
    else:
        if layer != "depth_mean":
            raise ValueError("per-frame grids are depth_mean only; use frame_index=null for p05/p95/velocity peaks")
        with np.load(d / "frames.npz", allow_pickle=False) as b:
            frames = b["depth_cm"]
        if not 0 <= frame_index < frames.shape[0]:
            raise ValueError(f"frame_index must be 0..{frames.shape[0] - 1}")
        f = frames[frame_index]
        arr = np.where(f == hires.NODATA_CM, np.nan, f / 100.0)
        valid_time = doc["frames"][frame_index]["valid_time_utc"]
    values = [[None if not np.isfinite(v) else round(float(v), 2) for v in row] for row in arr]
    fin = arr[np.isfinite(arr)]
    return {"run_id": run_id, "frame_index": frame_index, "valid_time_utc": valid_time, "unit": "m/s" if layer == "velocity_mps" else "m",
            "layer": layer, "rows": arr.shape[0], "cols": arr.shape[1], "grid": doc["grid"], "values": values,
            "max_value": round(float(fin.max()), 2) if fin.size else None}


def depth_frames_binary(runs_root, run_id) -> tuple[np.ndarray, dict]:
    """All frames as uint16 centimetres [frames, rows, cols] (65535 = NoData) for an additive binary variant."""
    doc = _run(runs_root, run_id)
    with np.load(Path(runs_root) / run_id / "frames.npz", allow_pickle=False) as b:
        return b["depth_cm"], {"grid": doc["grid"], "frames": doc["frames"], "nodata": hires.NODATA_CM, "scale_m": 0.01}


def buildings_page(static_root, runs_root, run_id, bbox=None, cursor=None, limit: int = 1000, min_depth_m: float | None = None,
                   frame_index: int | None = None) -> dict:
    doc = _run(runs_root, run_id)
    d = Path(runs_root) / run_id
    limit = max(1, min(int(limit), 5000))
    with np.load(d / "buildings.npz", allow_pickle=False) as b:
        idx, depth, pframe, cls = b["index"], b["max_depth_m"], b["peak_frame"], b["depth_class"]
    if frame_index is not None:
        bundle = _bundle(static_root, doc)
        with np.load(d / "frames.npz", allow_pickle=False) as fb:
            fr = fb["depth_cm"][frame_index].ravel()
        raw = fr[bundle.a["building_cell"][idx]]
        depth = np.where(raw == hires.NODATA_CM, np.nan, raw / 100.0).astype(np.float32)
        from .scenario import depth_class
        cls = depth_class(depth)
    with np.load(Path(static_root) / "shared/buildings.npz", allow_pickle=False) as s:
        osmid, lon, lat, height, hsrc, ward = s["osmid"], s["lon"], s["lat"], s["height_m"], s["height_source"], s["ward_id"]
    sel = np.ones(len(idx), bool)
    box = _bbox(bbox)
    if box:
        w, so, e, n = box
        sel &= (lon[idx] >= w) & (lon[idx] <= e) & (lat[idx] >= so) & (lat[idx] <= n)
    if min_depth_m is not None:
        sel &= np.nan_to_num(depth, nan=-1) >= float(min_depth_m)
    pos = np.flatnonzero(sel)
    start = _cursor(cursor)
    page = pos[start:start + limit]
    frames = doc["frames"]
    items = []
    for j in page:
        i = int(idx[j])
        dm = float(depth[j])
        pf = int(pframe[j])
        items.append({"building_id": f"way/{int(osmid[i])}", "centroid": {"lon": round(float(lon[i]), 6), "lat": round(float(lat[i]), 6)},
                      "ward_id": int(ward[i]) or None, "height_m": round(float(height[i]), 1), "height_source": HEIGHT_SOURCES[int(hsrc[i])],
                      "max_depth_m": None if not np.isfinite(dm) else round(dm, 2),
                      "time_of_max_utc": frames[pf]["valid_time_utc"] if (frame_index is None and pf >= 0 and np.isfinite(dm) and dm > 0) else None,
                      "depth_class": DEPTH_CLASSES[int(cls[j])]})
    nxt = start + limit
    return {"run_id": run_id, "frame_index": frame_index, "count": len(items), "total": int(len(pos)), "buildings": items,
            "next_cursor": str(nxt) if nxt < len(pos) else None}


def wards(runs_root, run_id) -> dict:
    _run(runs_root, run_id)
    doc = json.loads((Path(runs_root) / run_id / "wards.json").read_text(encoding="utf-8"))
    keep = ("ward_id", "ward_name", "zone", "max_depth_m", "mean_flooded_depth_m", "flooded_area_km2", "flooded_fraction",
            "buildings_affected", "population_exposed", "roads_blocked_km", "shelters_reachable", "risk_level")
    rows = [{k: w.get(k) for k in keep} for w in doc["wards"]]  # exactly the C4 v3 WardSummary fields
    return {"run_id": run_id, "frame_index": None, "source_mode": "SIMULATED", "wards": rows}


def roads(static_root, runs_root, run_id, frame_index: int | None = None, bbox=None, blocked_depth_threshold_m: float = BLOCKED_M,
          limit: int = 20000) -> dict:
    """RoadFeatureCollection (A21 three-state). frame_index None = peak frame. Geometry is WGS84."""
    doc = _run(runs_root, run_id)
    d = Path(runs_root) / run_id
    bundle = _bundle(static_root, doc)
    k = frame_index if frame_index is not None else next(f["index"] for f in doc["frames"] if f["valid_time_utc"] == doc["summary"]["peak_time_utc"])
    with np.load(d / "frames.npz", allow_pickle=False) as fb:
        frame = fb["depth_cm"][k]
    with np.load(Path(static_root) / "shared/roads.npz", allow_pickle=False) as r:
        rz = {key: r[key] for key in ("osmid", "highway", "structure", "line_offsets", "line_lonlat")}
    rcell = bundle.a["road_cell"]
    state, depth = road_states(frame, rcell, rz["structure"])
    thr = float(blocked_depth_threshold_m)
    known = state != 2
    state[known & (depth >= thr)] = 1
    state[known & (depth < thr)] = 0
    sel = np.flatnonzero(rcell >= 0)
    box = _bbox(bbox)
    off, ll = rz["line_offsets"], rz["line_lonlat"]
    if box:
        w, so, e, n = box
        first = ll[off[sel]]
        sel = sel[(first[:, 0] >= w) & (first[:, 0] <= e) & (first[:, 1] >= so) & (first[:, 1] <= n)]
    sel = sel[:limit]
    sf = speed_factor(depth)
    feats = []
    for i in sel:
        coords = ll[off[i]:off[i + 1]].round(6).tolist()
        st = int(state[i])
        reason = None
        if st == 2:
            reason = "bridge_or_structure_unassessed" if rz["structure"][i] else "no_depth_coverage"
        feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": coords},
                      "properties": {"edge_id": f"e:{int(i)}", "state": ROAD_STATES[st], "unknown_reason": reason,
                                     "depth_m": None if st == 2 else round(float(depth[i]), 2),
                                     "speed_factor": None if st == 2 else round(float(sf[i]), 3), "road_class": str(rz["highway"][i])}})
    return {"type": "FeatureCollection", "run_id": run_id, "frame_index": k, "features": feats}


def shelters(static_root, runs_root, run_id, frame_index: int | None = None, capacity_factor: float = 1.0) -> dict:
    """ShelterReport: reachability from the saved per-frame three-state roads; demand = people in cells >= 0.10 m."""
    doc = _run(runs_root, run_id)
    d = Path(runs_root) / run_id
    with np.load(d / "shelters.npz", allow_pickle=False) as b:
        reach_all, sidx, site_peak = b["reachable"], b["shelter_index"], b["site_peak_m"]
    k = frame_index if frame_index is not None else next(f["index"] for f in doc["frames"] if f["valid_time_utc"] == doc["summary"]["peak_time_utc"])
    reach = reach_all[k]
    with np.load(Path(static_root) / "shared/shelters.npz", allow_pickle=False) as s:
        sh = {key: s[key] for key in s.files}
    wards_doc = json.loads((d / "wards.json").read_text(encoding="utf-8"))
    demand_by_ward = {w["ward_id"]: w["population_exposed"] or 0 for w in wards_doc["wards"]}
    cap = (sh["capacity_people"][sidx] * float(capacity_factor)).astype(int)
    assigned = np.zeros(len(sidx), int)
    unserved = 0
    unreachable = 0
    for ward, demand in demand_by_ward.items():
        m = np.flatnonzero((sh["ward_id"][sidx] == ward) & reach)
        if not len(m):
            unreachable += demand
            continue
        left = demand
        for j in m[np.argsort(-cap[m])]:
            take = min(left, cap[j] - assigned[j])
            assigned[j] += take
            left -= take
            if left <= 0:
                break
        unserved += left
    demand_total = int(sum(demand_by_ward.values()))
    items = []
    for j, i in enumerate(sidx):
        items.append({"shelter_id": str(sh["shelter_id"][i]), "name": str(sh["name"][i]) or "Unnamed", "category": str(sh["category"][i]),
                      "location": {"lon": round(float(sh["lon"][i]), 6), "lat": round(float(sh["lat"][i]), 6)},
                      "ward_id": int(sh["ward_id"][i]) or None, "capacity_people": int(cap[j]), "capacity_source": "assumed",
                      "site_max_depth_m": None if not np.isfinite(site_peak[j]) else round(float(site_peak[j]), 2),
                      "reachable": bool(reach[j]), "assigned_population": int(assigned[j]),
                      "utilisation_pct": round(100.0 * assigned[j] / cap[j], 1) if cap[j] else None})
    served = int(assigned.sum())
    return {"run_id": run_id, "frame_index": k, "source_mode": "SIMULATED", "capacity_factor": float(capacity_factor), "shelters": items,
            "totals": {"demand_people": demand_total, "served_people": served, "unserved_people": int(unserved),
                       "unreachable_people": int(unreachable), "reachable_shelters": int(reach.sum())}}


def static_layer(static_root, layer: str, bbox=None, cursor=None, limit: int = 1000) -> dict:
    root = Path(static_root) / "shared"
    box = _bbox(bbox)
    start = _cursor(cursor)
    limit = max(1, min(int(limit), 5000))
    base = {"type": "FeatureCollection", "layer": layer, "source_mode": "STATIC_REFERENCE", "next_cursor": None}
    if layer in ("wards", "focus_areas"):
        doc = json.loads((root / f"{layer}.geojson").read_text(encoding="utf-8"))
        feats = doc["features"]
        src = {"wards": ("GCC 200-ward boundary (DataMeet / Transparent Chennai)", "CC BY-SA 2.5 India; Transparent Chennai via DataMeet"),
               "focus_areas": ("TwinGuard A25 focus areas (6 km boxes)", "TwinGuard")}[layer]
        page = feats[start:start + limit]
        return {**base, "source": src[0], "attribution": src[1], "features": page,
                "next_cursor": str(start + limit) if start + limit < len(feats) else None}
    if layer == "shelters":
        with np.load(root / "shelters.npz", allow_pickle=False) as s:
            sh = {k: s[k] for k in s.files}
        sel = np.arange(len(sh["lon"]))
        if box:
            w, so, e, n = box
            sel = sel[(sh["lon"] >= w) & (sh["lon"] <= e) & (sh["lat"] >= so) & (sh["lat"] <= n)]
        page = sel[start:start + limit]
        feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(float(sh["lon"][i]), 6), round(float(sh["lat"][i]), 6)]},
                  "properties": {"shelter_id": str(sh["shelter_id"][i]), "name": str(sh["name"][i]) or "Unnamed", "category": str(sh["category"][i]),
                                 "capacity_people": int(sh["capacity_people"][i]), "capacity_source": "assumed", "ward_id": int(sh["ward_id"][i]) or None}}
                 for i in page]
        return {**base, "source": "OpenStreetMap facilities (shelter/school/college/community hall)", "attribution": "© OpenStreetMap contributors (ODbL)",
                "features": feats, "next_cursor": str(start + limit) if start + limit < len(sel) else None}
    if layer == "buildings":
        with np.load(root / "buildings.npz", allow_pickle=False) as s:
            osmid, lon, lat, h, hs, ward, off, ring = (s[k] for k in ("osmid", "lon", "lat", "height_m", "height_source", "ward_id", "ring_offsets", "ring_lonlat"))
        sel = np.arange(len(lon))
        if box:
            w, so, e, n = box
            sel = sel[(lon >= w) & (lon <= e) & (lat >= so) & (lat <= n)]
        page = sel[start:start + limit]
        feats = [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring[off[i]:off[i + 1]].round(6).tolist()]},
                  "properties": {"building_id": f"way/{int(osmid[i])}", "height_m": round(float(h[i]), 1),
                                 "height_source": HEIGHT_SOURCES[int(hs[i])], "ward_id": int(ward[i]) or None}} for i in page]
        return {**base, "source": "OpenStreetMap building footprints", "attribution": "© OpenStreetMap contributors (ODbL)",
                "features": feats, "next_cursor": str(start + limit) if start + limit < len(sel) else None}
    raise ValueError("layer must be wards, buildings, shelters or focus_areas")
