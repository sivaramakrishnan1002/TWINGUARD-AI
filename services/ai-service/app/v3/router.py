"""C4 v3 product simulation and decision API (OD-2026-11-07 / CR-019), mounted at /v3.

Folds the CR-018 /live draft into /v3: no scheduler, no background polling; Open-Meteo is fetched only for
user-triggered requests with caching and a 600 s minimum interval. Every result carries source_mode.
"""
from __future__ import annotations

import math
import re
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Literal

import numpy as np
from fastapi import APIRouter, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import analysis, config, device, resources, static, weather
from .runs import MANAGER, QueueFull, TooSoon, public

router = APIRouter(prefix="/v3", tags=["v3"])
BBOX = r"^-?[0-9.]+,-?[0-9.]+,-?[0-9.]+,-?[0-9.]+$"
MAX_ROAD_FEATURES = 20000
RESERVOIR_NAMES = ("CHEMBARAMBAKKAM", "POONDI", "PUZHAL", "CHOLAVARAM")


# ------------------------------------------------------------------------------------------------ errors
class V3Error(Exception):
    CODES = {400: "bad_request", 404: "not_found", 409: "conflict", 422: "invalid", 429: "rate_limited", 503: "unavailable"}

    def __init__(self, status: int, detail: str, retry_after_s: int | None = None):
        super().__init__(detail)
        self.status, self.detail, self.retry_after_s = status, detail, retry_after_s


def error_response(status: int, detail: str, retry_after_s: int | None = None) -> JSONResponse:
    headers = {"Cache-Control": "no-store"}
    if retry_after_s is not None:
        headers["Retry-After"] = str(int(retry_after_s))
    return JSONResponse(status_code=status, headers=headers,
                        content={"detail": detail, "code": V3Error.CODES[status], "retry_after_s": retry_after_s})


def handle_v3_error(_request: Request, exc: V3Error) -> JSONResponse:
    return error_response(exc.status, exc.detail, exc.retry_after_s)


def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    if any(e.get("type") == "json_invalid" for e in errors):
        return error_response(400, "Request body is not valid JSON.")
    first = errors[0] if errors else {}
    loc = ".".join(str(p) for p in first.get("loc", []) if p not in ("body", "query", "path"))
    return error_response(422, f"{loc or 'request'}: {first.get('msg', 'invalid value')}"[:300])


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


class ApiError(BaseModel):
    """C4 v3 ApiError body."""
    model_config = ConfigDict(extra="forbid")
    detail: str
    code: Literal["bad_request", "not_found", "conflict", "invalid", "rate_limited", "unavailable"]
    retry_after_s: int | None = Field(default=None, ge=0)


ERROR_TEXT = {
    400: "Malformed request or invalid selector.",
    404: "Run, ward, building, shelter or resource not found.",
    409: "Conflict: another run is in progress or the resource version changed.",
    422: "Request failed validation (field ranges, units or enums).",
    429: "Rate limited: the Open-Meteo minimum fetch interval or the run-start interval has not elapsed. Retry-After header is set.",
    503: "Engine, static assets, cache or upstream source unavailable; no partial body.",
}


def errors(*codes: int) -> dict:
    return {code: {"model": ApiError, "description": ERROR_TEXT[code]} for code in codes}


# ------------------------------------------------------------------------------------------------ request models
class LonLat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lon: float = Field(ge=79.9, le=80.5)
    lat: float = Field(ge=12.7, le=13.4)


class CustomRainfall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start_time_utc: datetime
    interval_minutes: Literal[15, 30, 60]
    values_mm: list[float] = Field(min_length=1, max_length=288)

    @model_validator(mode="after")
    def check(self):
        if any((not math.isfinite(v)) or v < 0 or v > 200 for v in self.values_mm):
            raise ValueError("values_mm must be 0..200 mm per interval")
        if self.start_time_utc.tzinfo is None:
            raise ValueError("start_time_utc must include a UTC offset")
        return self


class WhatIfModifiers(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_run_id: str
    rainfall_scale_pct: float = Field(default=100, ge=0, le=300)
    reservoir_release_m3s: dict[str, float] = Field(default_factory=dict)
    tide_offset_m: float = Field(default=0.0, ge=-1.0, le=2.0)

    @model_validator(mode="after")
    def check(self):
        for name, value in self.reservoir_release_m3s.items():
            if name not in RESERVOIR_NAMES:
                raise ValueError(f"reservoir_release_m3s keys must be one of {', '.join(RESERVOIR_NAMES)}")
            if not (0 <= value <= 3000):
                raise ValueError("reservoir_release_m3s values must be 0..3000 m3/s")
        return self


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["event", "custom", "forecast", "what_if"]
    event_key: str | None = None
    custom_rainfall: CustomRainfall | None = None
    what_if: WhatIfModifiers | None = None
    duration_hours: int = Field(default=24, ge=6, le=72)
    resolution: Literal["citywide", "focus"] = "citywide"
    focus_area: Literal["VELACHERY", "ADYAR", "T_NAGAR", "PORUR"] | None = None
    frame_interval_minutes: Literal[15, 30] = 30

    @model_validator(mode="after")
    def check(self):
        if self.mode == "event" and not self.event_key:
            raise ValueError("event_key is required when mode=event")
        if self.mode == "custom" and self.custom_rainfall is None:
            raise ValueError("custom_rainfall is required when mode=custom")
        if self.mode == "what_if" and self.what_if is None:
            raise ValueError("what_if is required when mode=what_if")
        if self.resolution == "focus" and self.focus_area is None:
            raise ValueError("focus_area is required when resolution=focus")
        return self


class RouteSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    frame_index: int | None = Field(default=None, ge=0)
    origin: LonLat
    destination: LonLat
    policy: Literal["avoid_blocked", "avoid_blocked_and_unknown", "shortest_dry"] = "avoid_blocked"
    profile: Literal["car", "emergency_vehicle", "walk"] = "car"
    blocked_depth_threshold_m: float = Field(default=0.3, ge=0.1, le=1.0)


class ResourceBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    location: LonLat


class Resource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resource_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$")
    type: Literal["boat", "rescue_team", "vehicle", "ambulance", "pump"]
    count: int = Field(ge=0, le=500)
    base: ResourceBase
    source_mode: Literal["SCENARIO_INPUT"] | None = None


class ResourceSet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int | None = Field(default=None, ge=0)
    updated_at: datetime | None = None
    resources: list[Resource] = Field(max_length=200)

    @model_validator(mode="after")
    def unique(self):
        ids = [r.resource_id for r in self.resources]
        if len(ids) != len(set(ids)):
            raise ValueError("resource_id values must be unique")
        return self


# ------------------------------------------------------------------------------------------------ helpers
def _grid(request: dict | None = None) -> static.Grid:
    request = request or {"resolution": "citywide"}
    resolution = request.get("resolution", "citywide")
    try:
        return static.grid(resolution, request.get("focus_area"))
    except static.StaticUnavailable:
        if resolution == "focus":
            raise V3Error(503, "Focus-area 30 m grids are not installed yet (A25 pending).") from None
        raise V3Error(503, "Model grid is not installed.") from None


def _product() -> static.Product:
    try:
        return static.product()
    except static.StaticUnavailable:
        raise V3Error(503, "Product static bundle (roads, buildings, shelters) is not installed.") from None


def _run(run_id: str, completed: bool = True) -> dict:
    if not re.match(config.RUN_ID_PATTERN, run_id or ""):
        raise V3Error(404, "Run not found.")
    doc = MANAGER.get(run_id)
    if doc is None:
        raise V3Error(404, "Run not found.")
    if completed and doc["state"] != "completed":
        if doc["state"] == "failed":
            raise V3Error(503, f"Run failed: {doc.get('error') or 'no results'}")
        raise V3Error(503, f"Run is {doc['state']}; results are not ready.", retry_after_s=5)
    return doc


def _frames(doc: dict) -> dict:
    try:
        return MANAGER.frames(doc["run_id"])
    except (OSError, KeyError, ValueError):
        raise V3Error(503, "Run results are unreadable.") from None


def _frame_index(doc: dict, frame_index: int | None) -> int | None:
    if frame_index is not None and frame_index >= len(doc["frames"]):
        raise V3Error(422, f"frame_index must be 0..{len(doc['frames']) - 1}")
    return frame_index


def _times(doc: dict) -> list[str]:
    return [f["valid_time_utc"] for f in doc["frames"]]


def _bbox(text: str | None):
    if text is None:
        return None
    w, s, e, n = (float(v) for v in text.split(","))
    if not (w < e and s < n):
        raise V3Error(422, "bbox must be west,south,east,north with west<east and south<north")
    return w, s, e, n


def _cursor(text: str | None) -> int:
    if text is None:
        return 0
    if not text.isdigit():
        raise V3Error(400, "Invalid cursor.")
    return int(text)


class _Lru:
    def __init__(self, size: int):
        self.size, self.data, self.lock = size, OrderedDict(), threading.Lock()

    def get(self, key, factory):
        with self.lock:
            if key in self.data:
                self.data.move_to_end(key)
                return self.data[key]
        value = factory()
        with self.lock:
            self.data[key] = value
            while len(self.data) > self.size:
                self.data.popitem(last=False)
        return value


ROUTERS = _Lru(6)
DERIVED = _Lru(32)


def _depth(doc: dict, frame_index: int | None) -> np.ndarray:
    return analysis.frame_depth(_frames(doc), frame_index)


def _router(doc: dict, frame_index: int | None, profile: str, threshold: float = config.DEFAULT_BLOCK_THRESHOLD_M):
    product, grid = _product(), _grid(doc["request"])
    return ROUTERS.get(("flood", doc["run_id"], frame_index, threshold, profile),
                       lambda: analysis.Router(product, _depth(doc, frame_index), threshold, profile, grid.seg_cell(product)))


def _shelters(doc: dict, frame_index: int | None, capacity_factor: float = 1.0):
    grid, product = _grid(doc["request"]), _product()
    return DERIVED.get(("shelters", doc["run_id"], frame_index, capacity_factor),
                       lambda: analysis.shelter_report(grid, product, _depth(doc, frame_index), capacity_factor,
                                                       _router(doc, frame_index, "walk")))


def _incidents(doc: dict, frame_index: int | None) -> list[dict]:
    grid, product = _grid(doc["request"]), _product()

    def build():
        shelters, _ = _shelters(doc, frame_index)
        return analysis.incidents(grid, product, _frames(doc), _times(doc), frame_index, doc["request"].get("what_if"), shelters)
    return DERIVED.get(("incidents", doc["run_id"], frame_index), build)


# ------------------------------------------------------------------------------------------------ status / overview / weather / events
def _device_status() -> dict:
    """EngineStatus.device (OD-2026-11-08): requested setting, resolved device, GPU name, one GPU job at most."""
    try:
        dev = device.status()
    except Exception:  # noqa: BLE001 - device reporting never breaks status
        return {"requested": device.requested(), "resolved": "cpu", "name": None, "cuda_available": False, "gpu_jobs_max": 1}
    return {k: dev[k] for k in ("requested", "resolved", "name", "cuda_available", "gpu_jobs_max")}


@router.get("/status", operation_id="v3GetEngineStatus")
def get_status(response: Response) -> dict:
    _no_store(response)
    queue = MANAGER.status()
    allowed = weather.next_allowed("point")
    return {
        "engine_version": config.ENGINE_VERSION_A25 if config.a25_enabled() else config.ENGINE_VERSION,
        "device": _device_status(),
        "static_available": static.grid_available("citywide") and static.product_available(),
        **queue,
        "weather_min_refresh_interval_s": config.weather_min_interval_s(),
        "weather_next_fetch_allowed_at": weather._iso(allowed) if allowed and allowed > weather._now() else None,
    }


@router.get("/overview", operation_id="v3GetOverview", responses=errors(503))
def get_overview(response: Response) -> dict:
    _no_store(response)
    _grid()
    _product()
    latest = MANAGER.latest_completed()
    counts = {s: 0 for s in analysis.SEVERITY_ORDER}
    if latest:
        for incident in _incidents(latest, None):
            counts[incident["severity"]] += 1
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "badge": config.BADGE,
        "latest_run": public(latest) if latest else None,
        "weather": weather.cached_point(),
        "reservoirs": None,
        "incident_counts": counts,
        "top_wards": _ward_rows(latest, None)[:10] if latest and static.wards_available() else [],
    }


@router.get("/weather", operation_id="v3GetWeather", responses=errors(429, 503))
def get_weather(response: Response, refresh: bool = Query(default=False)) -> dict:
    _no_store(response)
    try:
        return weather.get_point(refresh)
    except weather.RateLimited as error:
        raise V3Error(429, "Open-Meteo minimum fetch interval (600 s) has not elapsed.", error.retry_after_s) from None
    except weather.Unavailable:
        raise V3Error(503, "Open-Meteo is unavailable or returned invalid data.") from None


@router.get("/events", operation_id="v3ListEvents")
def list_events(response: Response) -> dict:
    _no_store(response)
    return {"events": [{k: e[k] for k in ("event_key", "label", "start_utc", "end_utc", "rainfall_source", "source_mode")}
                       for e in static.events()]}


# ------------------------------------------------------------------------------------------------ simulations
@router.post("/simulations", status_code=202, operation_id="v3CreateSimulation", responses=errors(400, 404, 409, 422, 429, 503))
def create_simulation(body: SimulationRequest, response: Response) -> dict:
    _no_store(response)
    request = body.model_dump(mode="json", exclude_none=True)
    engine = "a25" if config.a25_enabled() else "a06"
    identity: dict = {}
    job_extra: dict = {}
    if body.mode == "event":
        event = next((e for e in static.events() if e["event_key"] == body.event_key), None)
        if event is None:
            raise V3Error(400, "Unknown event_key; see GET /v3/events.")
        identity = {"event": event["event_key"], "label": event["label"]}
    elif body.mode == "custom":
        total = sum(body.custom_rainfall.values_mm)
        identity = {"label": f"Custom rainfall {total:g} mm"}
        request["custom_rainfall"]["start_time_utc"] = body.custom_rainfall.start_time_utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    elif body.mode == "what_if":
        base = _run(body.what_if.base_run_id, completed=False) if re.match(config.RUN_ID_PATTERN, body.what_if.base_run_id) else None
        if base is None:
            raise V3Error(404, "Base run not found.")
        if base["state"] != "completed":
            raise V3Error(409, "Base run is not completed yet.")
        if base.get("_engine", "a06") != engine:
            raise V3Error(409, "Base run was computed by a different engine version; run a new base first.")
        for key in ("duration_hours", "resolution", "frame_interval_minutes", "focus_area"):
            if key in base["request"]:
                request[key] = base["request"][key]
            else:
                request.pop(key, None)
        request["what_if"] = {"rainfall_scale_pct": 100.0, "tide_offset_m": 0.0, "reservoir_release_m3s": {}, **request["what_if"]}
        identity = {"label": f"What-if on {base.get('label', base['run_id'])}"}
        job_extra = {"base_run_dir": str(MANAGER.run_dir(base["run_id"])), "base_engine_run_id": base.get("_engine_run_id")}
    _grid(request)
    if body.mode == "forecast":
        try:
            plan = weather.plan_forecast_fetch()
        except weather.RateLimited as error:
            raise V3Error(429, "Open-Meteo minimum fetch interval (600 s) has not elapsed.", error.retry_after_s) from None
        if not plan["fetch"]:
            cached = _cached_forecast(request, plan["forcing_sha256"])
            if cached:
                return {"run_id": cached["run_id"], "state": "cached", "status_url": f"/v3/simulations/{cached['run_id']}",
                        "estimated_seconds": 0}
        identity = {"label": "Open-Meteo forecast", "forcing": plan["forcing_sha256"] or f"fetch-{datetime.now(timezone.utc).timestamp()}"}
        job_extra = {"fetch_forecast": plan["fetch"]}
    identity["engine"] = engine
    if engine == "a25":  # engine upgrades (e.g. 2.1.0 adds A27 flow) must not be served from older cached runs
        from services.flood_engine import scenario as _scenario
        identity["engine_version"] = getattr(_scenario, "ENGINE_VERSION", "unknown")
    # GPU results would match CPU only within tolerance, so the compute device is part of the cache identity.
    identity["device"] = device.resolve(device.engine_supports_gpu())["used"] if engine == "a25" else "cpu"
    job_extra["engine"] = engine
    try:
        doc, state = MANAGER.submit(request, identity, job_extra)
    except QueueFull:
        raise V3Error(409, "A run is in progress and the queue is full (max 4 queued).") from None
    except TooSoon as error:
        raise V3Error(429, "Run-start interval has not elapsed.", error.retry_after_s) from None
    return {"run_id": doc["run_id"], "state": state, "status_url": f"/v3/simulations/{doc['run_id']}",
            "estimated_seconds": 0 if state == "cached" else MANAGER.estimate_s(request)}


def _cached_forecast(request: dict, forcing_sha: str | None) -> dict | None:
    """A completed forecast run with the same request and the same Open-Meteo forcing (identical forcing -> cached)."""
    for doc in MANAGER.list():
        if doc["state"] == "completed" and doc["mode"] == "forecast" and doc["request"] == request:
            if any(i.get("source_mode") == "MODEL_FORECAST" and i.get("sha256") == forcing_sha for i in doc["provenance"]["inputs"]):
                return doc
    return None


@router.get("/simulations", operation_id="v3ListSimulations", responses=errors(400, 422))
def list_simulations(response: Response, cursor: str | None = Query(default=None),
                     limit: int = Query(default=12, ge=1, le=50)) -> dict:
    _no_store(response)
    start = _cursor(cursor)
    runs = MANAGER.list()
    page = runs[start:start + limit]
    return {"runs": [public(d) for d in page], "next_cursor": str(start + limit) if start + limit < len(runs) else None}


@router.get("/simulations/{run_id}", operation_id="v3GetSimulation", responses=errors(404, 503))
def get_simulation(run_id: str, response: Response) -> dict:
    _no_store(response)
    return public(_run(run_id, completed=False))


@router.get("/simulations/{run_id}/depth", operation_id="v3GetDepthFrame", responses=errors(404, 422, 503))
def get_depth(run_id: str, response: Response, frame_index: int | None = Query(default=None, ge=0),
              layer: Literal["depth_mean", "depth_p05", "depth_p95", "velocity_mps"] = Query(default="depth_mean"),
              resolution: Literal["citywide", "focus"] = Query(default="citywide"),
              focus_area: Literal["VELACHERY", "ADYAR", "T_NAGAR", "PORUR"] | None = Query(default=None)) -> dict:
    _no_store(response)
    doc = _run(run_id)
    if resolution != doc["request"]["resolution"] or (resolution == "focus" and focus_area != doc["request"].get("focus_area")):
        raise V3Error(422, f"Run was computed at resolution={doc['request']['resolution']}.")
    frame_index = _frame_index(doc, frame_index)
    frames = _frames(doc)
    if layer not in frames:
        raise V3Error(422, f"layer {layer} is not available for this run (A25 p05/p95 need 3 members).")
    if frames[layer].shape[0] == 1 and len(doc["frames"]) > 1 and frame_index is not None:
        raise V3Error(422, f"layer {layer} is peak-only for this run; omit frame_index.")
    array = analysis.frame_depth(frames, frame_index, layer) if frames[layer].shape[0] > 1 else frames[layer][0]
    values = [[None if not math.isfinite(v) else round(max(float(v), 0.0), 2) for v in row] for row in array]
    finite = array[np.isfinite(array)]
    return {"run_id": run_id, "frame_index": frame_index,
            "valid_time_utc": doc["frames"][frame_index]["valid_time_utc"] if frame_index is not None else None,
            "unit": "m", "layer": layer, "rows": len(values), "cols": len(values[0]) if values else 0, "grid": doc["grid"],
            "values": values, "max_value": analysis.r2(max(float(finite.max()), 0.0)) if finite.size else None}


@router.get("/simulations/{run_id}/flow", operation_id="v3GetFlowFrame", responses=errors(404, 422, 503))
def get_flow(run_id: str, request: Request, frame_index: int = Query(ge=0),
             stride: int = Query(default=1, ge=1, le=8)):
    """B49: per-frame depth-averaged u/v and water-surface elevation from the A27 flow sidecar (FlowFrame).

    Served gzip-compressed when the client accepts it (a citywide frame is ~1 MB of JSON before compression).
    """
    doc = _run(run_id)  # focus-area runs have their own run_id, so no resolution selector is needed
    frame_index = _frame_index(doc, frame_index)
    engine_run = doc.get("_engine_run_id")
    if doc.get("_engine", "a06") != "a25" or not engine_run:
        raise V3Error(503, "This run has no flow output (A06 pilot engine); run a new A25 simulation.")
    from services.flood_engine import products
    try:
        body = products.flow_frame(config.runs_dir() / "_a25", engine_run, frame_index, stride)
    except products.FlowUnavailable:
        raise V3Error(503, "This run has no flow output (computed before engine 2.1.0 / A27); run a new simulation.") from None
    except products.NotFound:
        raise V3Error(404, "Engine output for this run was not found.") from None
    except ValueError as error:
        raise V3Error(422, str(error)[:200]) from None
    body["run_id"] = run_id
    body["wet_threshold_m"] = round(float(body["wet_threshold_m"]), 6)  # float32 sidecar value (0.0099999998 -> 0.01)
    return _json_maybe_gzip(request, body)


def _json_maybe_gzip(request: Request, body: dict) -> Response:
    import gzip
    import json as _json

    raw = _json.dumps(body, separators=(",", ":"), allow_nan=False).encode("utf-8")
    headers = {"Cache-Control": "no-store", "Vary": "Accept-Encoding"}
    if "gzip" in request.headers.get("accept-encoding", "").lower() and len(raw) > 1024:
        headers["Content-Encoding"] = "gzip"
        raw = gzip.compress(raw, compresslevel=5)
    return Response(content=raw, media_type="application/json", headers=headers)


@router.get("/simulations/{run_id}/buildings", operation_id="v3GetBuildingDepths", responses=errors(400, 404, 422, 503))
def get_buildings(run_id: str, response: Response, frame_index: int | None = Query(default=None, ge=0),
                  bbox: str | None = Query(default=None, pattern=BBOX), cursor: str | None = Query(default=None),
                  limit: int = Query(default=1000, ge=1, le=5000), min_depth_m: float | None = Query(default=None, ge=0)) -> dict:
    _no_store(response)
    doc = _run(run_id)
    frame_index = _frame_index(doc, frame_index)
    box, start = _bbox(bbox), _cursor(cursor)
    grid, product = _grid(doc["request"]), _product()
    depth, when = DERIVED.get(("bdepth", run_id, frame_index), lambda: analysis.building_depths(grid, product, _frames(doc), frame_index))
    b = product.buildings
    mask = analysis.bbox_filter(b["lon"], b["lat"], box)
    if min_depth_m is not None:
        mask &= np.nan_to_num(depth, nan=-1.0) >= min_depth_m
    idx = np.flatnonzero(mask)
    page = idx[start:start + limit]
    times = _times(doc)
    ward_ids = grid.ward_at(grid.building_cell(product)[page]) if page.size else []
    rows = []
    for i, ward in zip(page, ward_ids):
        d = depth[i]
        known = bool(np.isfinite(d))
        rows.append({
            "building_id": f"b:{int(b['fid'][i])}",
            "centroid": {"lon": round(float(b["lon"][i]), 6), "lat": round(float(b["lat"][i]), 6)},
            "ward_id": ward, "height_m": round(float(b["height_m"][i]), 1),
            "height_source": analysis.HEIGHT_SOURCES[int(b["height_source"][i])],
            "max_depth_m": round(max(float(d), 0.0), 2) if known else None,
            "time_of_max_utc": times[int(when[i])] if known and when[i] >= 0 and d > 0 else None,
            "depth_class": analysis.depth_class(float(d) if known else None),
        })
    return {"run_id": run_id, "frame_index": frame_index, "count": len(rows), "total": int(idx.size), "buildings": rows,
            "next_cursor": str(start + limit) if start + limit < idx.size else None}


def _ward_rows(doc: dict, frame_index: int | None) -> list[dict]:
    """Per-ward summary from an installed A25 ward_id grid (cells -> ward)."""
    grid, product = _grid(doc["request"]), _product()
    ward_grid = grid.arrays["ward_id"].astype(np.int64)
    names = static.ward_names(grid)
    peak, _ = analysis.peak_until(_frames(doc), frame_index)
    cell_km2 = (grid.cell_size_m / 1000.0) ** 2
    pop = np.nan_to_num(grid.arrays["population"], nan=0.0)
    seg_cell = grid.seg_cell(product)
    seg_state, *_ = analysis.segment_states(product, peak, config.DEFAULT_BLOCK_THRESHOLD_M, seg_cell)
    roads = product.roads
    seg_ward = np.where(seg_cell >= 0, ward_grid.ravel()[np.clip(seg_cell, 0, None)], 0)
    bcells = grid.building_cell(product)
    bward = np.where(bcells >= 0, ward_grid.ravel()[np.clip(bcells, 0, None)], 0)
    bdepth = np.where(bcells >= 0, peak.ravel()[np.clip(bcells, 0, None)], np.nan)
    rows = []
    for ward_id, (name, zone) in sorted(names.items()):
        cells = (ward_grid == ward_id) & grid.active
        d = peak[cells]
        d = d[np.isfinite(d)]
        flooded = d >= config.FLOOD_THRESHOLD_M
        frac = float(flooded.mean()) if d.size else None
        mx = float(d.max()) if d.size else None
        blocked = (seg_ward == ward_id) & (seg_state == analysis.STATE_BLOCKED)
        rows.append({"ward_id": ward_id, "ward_name": name, "zone": zone, "max_depth_m": analysis.r2(max(mx, 0.0)) if mx is not None else None,
                     "mean_flooded_depth_m": analysis.r2(d[flooded].mean()) if flooded.any() else (0.0 if d.size else None),
                     "flooded_area_km2": analysis.r2(flooded.sum() * cell_km2) if d.size else None, "flooded_fraction": analysis.r2(frac),
                     "buildings_affected": int(np.sum((bward == ward_id) & (bdepth >= config.FLOOD_THRESHOLD_M))),
                     "population_exposed": int(round(float(pop[cells][np.nan_to_num(peak[cells], nan=0) >= config.FLOOD_THRESHOLD_M].sum()))),
                     "roads_blocked_km": analysis.r2(roads["seg_length_m"][blocked].sum() / 1000), "shelters_reachable": None,
                     "risk_level": analysis.risk_level(mx, frac)})
    rows.sort(key=lambda r: (-["low", "moderate", "high", "severe"].index(r["risk_level"]), -(r["max_depth_m"] or 0)))
    return rows


@router.get("/simulations/{run_id}/wards", operation_id="v3GetWardSummaries", responses=errors(404, 422, 503))
def get_wards(run_id: str, response: Response, frame_index: int | None = Query(default=None, ge=0)) -> dict:
    _no_store(response)
    doc = _run(run_id)
    frame_index = _frame_index(doc, frame_index)
    if not static.wards_available():
        raise V3Error(503, "GCC ward boundaries are not installed yet (A25 pending).")
    return {"run_id": run_id, "frame_index": frame_index, "source_mode": "SIMULATED", "wards": _ward_rows(doc, frame_index)}


@router.get("/simulations/{run_id}/roads", operation_id="v3GetRoadStates", responses=errors(404, 422, 503))
def get_roads(run_id: str, response: Response, frame_index: int | None = Query(default=None, ge=0),
              bbox: str | None = Query(default=None, pattern=BBOX),
              blocked_depth_threshold_m: float = Query(default=0.3, ge=0.1, le=1.0)) -> dict:
    _no_store(response)
    doc = _run(run_id)
    frame_index = _frame_index(doc, frame_index)
    box = _bbox(bbox)
    product, grid = _product(), _grid(doc["request"])
    roads = product.roads
    state, speed, depth, reason = analysis.segment_states(product, _depth(doc, frame_index), blocked_depth_threshold_m,
                                                          grid.seg_cell(product))
    idx = np.flatnonzero(analysis.bbox_filter(roads["seg_mid_lon"], roads["seg_mid_lat"], box))
    priority = np.array([2, 0, 1])[state[idx]]  # blocked first, then unknown, then passable
    idx = idx[np.argsort(priority, kind="stable")][:MAX_ROAD_FEATURES]
    names = roads["highway_names"]
    features = []
    for i in idx:
        d = depth[i]
        features.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": analysis.segment_coords(product, int(i))},
                         "properties": {"edge_id": f"e:{int(i)}", "state": analysis.STATE_NAMES[int(state[i])],
                                        "unknown_reason": reason[i] if state[i] == analysis.STATE_UNKNOWN else None,
                                        "depth_m": round(max(float(d), 0.0), 2) if math.isfinite(d) else None,
                                        "speed_factor": round(float(speed[i]), 2) if math.isfinite(speed[i]) else None,
                                        "road_class": str(names[roads["seg_highway"][i]])}})
    return {"type": "FeatureCollection", "run_id": run_id, "frame_index": frame_index, "features": features}


@router.get("/simulations/{run_id}/shelters", operation_id="v3GetShelterReport", responses=errors(404, 422, 503))
def get_shelters(run_id: str, response: Response, frame_index: int | None = Query(default=None, ge=0),
                 capacity_factor: float = Query(default=1.0)) -> dict:
    _no_store(response)
    if capacity_factor not in (0.5, 1.0, 2.0):
        raise V3Error(422, "capacity_factor must be one of 0.5, 1.0, 2.0")
    doc = _run(run_id)
    frame_index = _frame_index(doc, frame_index)
    shelters, totals = _shelters(doc, frame_index, float(capacity_factor))
    return {"run_id": run_id, "frame_index": frame_index, "source_mode": "SIMULATED", "capacity_factor": float(capacity_factor),
            "shelters": shelters, "totals": totals}


@router.get("/simulations/{run_id}/incidents", operation_id="v3GetIncidents", responses=errors(404, 422, 503))
def get_incidents(run_id: str, response: Response, frame_index: int | None = Query(default=None, ge=0),
                  min_severity: Literal["info", "watch", "warning", "critical"] = Query(default="watch")) -> dict:
    _no_store(response)
    doc = _run(run_id)
    frame_index = _frame_index(doc, frame_index)
    floor = analysis.SEVERITY_ORDER.index(min_severity)
    items = [i for i in _incidents(doc, frame_index) if analysis.SEVERITY_ORDER.index(i["severity"]) >= floor]
    return {"run_id": run_id, "source_mode": "SIMULATED", "incidents": items}


@router.get("/simulations/{run_id}/emergency-plan", operation_id="v3GetEmergencyPlan", responses=errors(404, 422, 503))
def get_emergency_plan(run_id: str, response: Response, frame_index: int | None = Query(default=None, ge=0)) -> dict:
    _no_store(response)
    doc = _run(run_id)
    frame_index = _frame_index(doc, frame_index)
    resource_set = resources.get()
    items = [i for i in _incidents(doc, frame_index) if i["severity"] in ("warning", "critical")]
    assignments, unassigned = DERIVED.get(
        ("plan", run_id, frame_index, resource_set["version"]),
        lambda: analysis.emergency_plan(_router(doc, frame_index, "emergency_vehicle"), items, resource_set["resources"]))
    return {"run_id": run_id, "frame_index": frame_index, "source_mode": "SIMULATED",
            "resource_set_version": resource_set["version"], "assignments": assignments, "unassigned_incidents": unassigned}


@router.get("/simulations/{run_id}/comparison", operation_id="v3GetComparison", responses=errors(400, 404, 503))
def get_comparison(run_id: str, response: Response, baseline_run_id: str | None = Query(default=None)) -> dict:
    _no_store(response)
    doc = _run(run_id)
    modifiers = doc["request"].get("what_if")
    base_id = baseline_run_id or (modifiers or {}).get("base_run_id")
    if not base_id:
        raise V3Error(400, "baseline_run_id is required for a run that is not a what-if run.")
    base = _run(base_id)
    if base["grid"] != doc["grid"]:
        raise V3Error(400, "Runs use different grids and cannot be compared.")
    delta = {}
    for key in ("max_depth_m", "flooded_area_km2", "buildings_affected", "population_exposed", "roads_blocked_km", "wards_affected"):
        a, b = doc["summary"].get(key), base["summary"].get(key)
        delta[key] = None if a is None or b is None else (a - b if isinstance(a, int) and isinstance(b, int) else analysis.r2(a - b))
    delta["peak_time_utc"] = doc["summary"].get("peak_time_utc")
    ward_changes = []
    if static.wards_available():
        before = {w["ward_id"]: w for w in _ward_rows(base, None)}
        for w in _ward_rows(doc, None):
            b = before.get(w["ward_id"])
            if b:
                change = None if w["max_depth_m"] is None or b["max_depth_m"] is None else analysis.r2(w["max_depth_m"] - b["max_depth_m"])
                ward_changes.append({"ward_id": w["ward_id"], "max_depth_change_m": change,
                                     "risk_level_before": b["risk_level"], "risk_level_after": w["risk_level"]})
    out = {"run_id": run_id, "baseline_run_id": base_id, "delta": delta, "ward_changes": ward_changes}
    if modifiers:
        out["modifiers"] = modifiers
    return out


# ------------------------------------------------------------------------------------------------ routes
@router.post("/routes", operation_id="v3SearchRoute", responses=errors(400, 404, 422, 503))
def search_route(body: RouteSearchRequest, response: Response) -> dict:
    _no_store(response)
    doc = _run(body.run_id)
    frame_index = _frame_index(doc, body.frame_index)
    product = _product()
    flood = _router(doc, frame_index, body.profile, body.blocked_depth_threshold_m)
    dry = ROUTERS.get(("dry", body.profile), lambda: analysis.Router(product, None, body.blocked_depth_threshold_m, body.profile))
    src, d_src = flood.snap(body.origin.lon, body.origin.lat)
    dst, d_dst = flood.snap(body.destination.lon, body.destination.lat)
    base = {"run_id": body.run_id, "frame_index": frame_index, "source_mode": "SIMULATED"}
    if d_src > analysis.SNAP_LIMIT_M or not flood.node_has_open_arc(src):
        return {**base, "status": "origin_unreachable", "routes": [], "dry_baseline": None}
    if d_dst > analysis.SNAP_LIMIT_M or not flood.node_has_open_arc(dst):
        return {**base, "status": "destination_unreachable", "routes": [], "dry_baseline": None}
    policies = [body.policy] + [p for p in ("avoid_blocked", "avoid_blocked_and_unknown", "shortest_dry") if p != body.policy]
    routes = [flood.option(p, flood.shortest(p, src, dst)) for p in policies]
    dry_path = dry.shortest("dry_baseline", src, dst)
    dry_option = None
    if dry_path is not None:
        dry_option = flood.option("dry_baseline", dry_path, status_override="ASSESSED_PASSABLE")  # same arc indexing per profile
    status = "found" if routes[0]["route_status"] != "NO_ROUTE" else "no_route"
    return {**base, "status": status, "routes": routes, "dry_baseline": dry_option}


# ------------------------------------------------------------------------------------------------ resources
@router.get("/scenario-resources", operation_id="v3GetScenarioResources")
def get_resources(response: Response) -> dict:
    _no_store(response)
    return resources.get()


@router.put("/scenario-resources", operation_id="v3PutScenarioResources", responses=errors(400, 409, 422, 503))
def put_resources(body: ResourceSet, response: Response) -> dict:
    _no_store(response)
    try:
        return resources.put(body.version, [r.model_dump(mode="json", exclude_none=True) for r in body.resources])
    except resources.VersionConflict:
        raise V3Error(409, "Resource set version changed; GET the current version and retry.") from None
    except OSError:
        raise V3Error(503, "Resource store is not writable.") from None


# ------------------------------------------------------------------------------------------------ static layers
@router.get("/static/{layer}", operation_id="v3GetStaticLayer", responses=errors(400, 404, 422, 503))
def get_static_layer(layer: Literal["wards", "buildings", "shelters", "focus_areas"], response: Response,
                     bbox: str | None = Query(default=None, pattern=BBOX), cursor: str | None = Query(default=None),
                     limit: int = Query(default=1000, ge=1, le=5000)) -> dict:
    _no_store(response)
    box, start = _bbox(bbox), _cursor(cursor)
    osm = "© OpenStreetMap contributors (ODbL)"
    if layer in ("wards", "focus_areas"):
        collection = static.geojson_layer(layer)
        if collection is None:
            raise V3Error(503, f"{layer} layer is not installed yet (A25 pending).")
        features = collection["features"]
        page = features[start:start + limit]
        return {"type": "FeatureCollection", "layer": layer, "source": collection.get("source", "A25"), "source_mode": "STATIC_REFERENCE",
                "attribution": collection.get("attribution", "Greater Chennai Corporation ward boundaries (A25)" if layer == "wards"
                                              else "TwinGuard focus areas (A25)"), "features": page,
                "next_cursor": str(start + limit) if start + limit < len(features) else None}
    product = _product()
    if layer == "shelters":
        items = [s for s in product.shelters if box is None or (box[0] <= s["lon"] <= box[2] and box[1] <= s["lat"] <= box[3])]
        page = items[start:start + limit]
        features = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
                     "properties": {"shelter_id": s["shelter_id"], "name": s["name"], "category": s["category"],
                                    "capacity_people": s["capacity_people"], "capacity_source": s["capacity_source"]}} for s in page]
        return {"type": "FeatureCollection", "layer": layer, "source": "OSM shelters, schools and colleges (B-lane candidate set)",
                "source_mode": "STATIC_REFERENCE", "attribution": osm, "features": features,
                "next_cursor": str(start + limit) if start + limit < len(items) else None}
    b = product.buildings
    idx = np.flatnonzero(analysis.bbox_filter(b["lon"], b["lat"], box))
    page = idx[start:start + limit]
    features = []
    for i in page:
        a, z = b["ring_offsets"][i], b["ring_offsets"][i + 1]
        ring = [[round(float(x), 6), round(float(y), 6)] for x, y in zip(b["ring_lon"][a:z], b["ring_lat"][a:z])]
        features.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]},
                         "properties": {"building_id": f"b:{int(b['fid'][i])}", "height_m": round(float(b["height_m"][i]), 1),
                                        "height_source": analysis.HEIGHT_SOURCES[int(b["height_source"][i])], "ward_id": None}})
    return {"type": "FeatureCollection", "layer": layer, "source": "OSM building footprints (382,294)", "source_mode": "STATIC_REFERENCE",
            "attribution": osm, "features": features, "next_cursor": str(start + limit) if start + limit < idx.size else None}
