"""On-demand Open-Meteo access for C4 v3 (OD-2026-11-07): user-triggered only, cached, >= 600 s between fetches.

There is no scheduler or background polling anywhere in v3. Two independent caches are kept under the run store:
``point.json`` (Chennai current + hourly, for GET /v3/weather) and ``forecast_grid.npz`` (gridded precipitation for
mode=forecast runs, fetched by the simulation worker through services.flood_engine.forcing).
"""
from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import config

ENDPOINT = "https://api.open-meteo.com/v1/forecast"
ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"
USER_AGENT = "TwinGuard-educational-prototype/1.0"
_LOCK = threading.Lock()


class RateLimited(Exception):
    def __init__(self, retry_after_s: int):
        super().__init__("minimum Open-Meteo fetch interval has not elapsed")
        self.retry_after_s = max(1, int(retry_after_s))


class Unavailable(Exception):
    pass


def _dir() -> Path:
    path = config.runs_dir() / "_weather"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _now() -> float:
    return time.time()


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _attempts() -> dict:
    return _read(_dir() / "attempts.json") or {}


def _mark_attempt(kind: str, ts: float) -> None:
    data = _attempts()
    data[kind] = ts
    (_dir() / "attempts.json").write_text(json.dumps(data), encoding="utf-8")


def next_allowed(kind: str) -> float | None:
    last = _attempts().get(kind)
    return None if last is None else last + config.weather_min_interval_s()


def _http_get(url: str, timeout: float = 30.0) -> bytes:
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed https endpoint
        return response.read()


FETCHER = _http_get  # tests replace this


def point_url() -> str:
    query = {
        "latitude": f"{config.CHENNAI['lat']:.4f}", "longitude": f"{config.CHENNAI['lon']:.4f}",
        "current": "temperature_2m,precipitation,relative_humidity_2m,wind_speed_10m",
        "hourly": "precipitation,precipitation_probability", "forecast_hours": "48",
        "timezone": "GMT", "timeformat": "iso8601", "wind_speed_unit": "kmh", "precipitation_unit": "mm",
    }
    return f"{ENDPOINT}?{urllib.parse.urlencode(query)}"


def _parse_point(body: bytes, fetched_at: float) -> dict:
    payload = json.loads(body)
    if payload.get("error") or payload.get("utc_offset_seconds") != 0:
        raise Unavailable("unexpected Open-Meteo response")
    current = payload.get("current") or {}
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    precip = hourly.get("precipitation") or [None] * len(times)
    prob = hourly.get("precipitation_probability") or [None] * len(times)
    if not (len(times) == len(precip) == len(prob)):
        raise Unavailable("misaligned Open-Meteo hourly series")

    def num(value):
        return None if value is None else float(value)

    return {
        "provider": "open-meteo", "model": "best_match", "fetched_at": _iso(fetched_at),
        "min_refresh_interval_s": config.weather_min_interval_s(),
        "location": dict(config.CHENNAI),
        "current": {"temperature_c": num(current.get("temperature_2m")), "precipitation_mm": num(current.get("precipitation")),
                    "relative_humidity_pct": num(current.get("relative_humidity_2m")),
                    "wind_speed_kmh": num(current.get("wind_speed_10m"))},
        "hourly": [{"time_utc": f"{t}:00Z" if len(t) == 16 else t,
                    "precipitation_mm": None if p is None else max(0.0, float(p)),
                    "precipitation_probability_pct": None if q is None else min(100.0, max(0.0, float(q)))}
                   for t, p, q in zip(times, precip, prob)],
        "source_mode": "MODEL_FORECAST", "attribution": ATTRIBUTION,
    }


def cached_point() -> dict | None:
    doc = _read(_dir() / "point.json")
    if doc:
        fetched = datetime.fromisoformat(doc["fetched_at"].replace("Z", "+00:00")).timestamp()
        doc["cache_age_s"] = max(0, int(_now() - fetched))
        doc["min_refresh_interval_s"] = config.weather_min_interval_s()
    return doc


def get_point(refresh: bool) -> dict:
    with _LOCK:
        cached = cached_point()
        if cached and not refresh:
            return cached
        allowed = next_allowed("point")
        now = _now()
        if allowed is not None and now < allowed:
            raise RateLimited(allowed - now)
        _mark_attempt("point", now)
        try:
            doc = _parse_point(FETCHER(point_url()), now)
        except Unavailable:
            raise
        except Exception as error:  # never leak provider bodies or transport details
            raise Unavailable(type(error).__name__) from None
        (_dir() / "point.json").write_text(json.dumps(doc), encoding="utf-8")
        doc["cache_age_s"] = 0
        return doc


# ------------------------------------------------------------------------------------------- gridded forcing
# The cache holds the raw Open-Meteo lattice snapshot (primary model), so each engine maps it onto its own grid.
def grid_snapshot_path() -> Path:
    return _dir() / "forecast_snapshot.npz"


def grid_snapshot_info() -> dict | None:
    path = grid_snapshot_path()
    if not path.exists():
        return None
    with np.load(path, allow_pickle=False) as z:
        return json.loads(str(z["meta"]))


def plan_forecast_fetch() -> dict:
    """Decide (in the API process) whether a forecast run may reuse the cached snapshot or must fetch now."""
    with _LOCK:
        info = grid_snapshot_info()
        now = _now()
        if info:
            age = now - datetime.fromisoformat(info["fetched_at"].replace("Z", "+00:00")).timestamp()
            if age < config.weather_min_interval_s():
                return {"fetch": False, "forcing_sha256": info["forcing_sha256"], "fetched_at": info["fetched_at"]}
        allowed = next_allowed("grid")
        if allowed is not None and now < allowed:
            if info:  # stale but the interval since the last attempt has not elapsed: reuse what exists
                return {"fetch": False, "forcing_sha256": info["forcing_sha256"], "fetched_at": info["fetched_at"]}
            raise RateLimited(allowed - now)
        _mark_attempt("grid", now)
        return {"fetch": True, "forcing_sha256": None, "fetched_at": None}


def fetch_forecast_snapshot(bounds_lonlat: list[float]):
    """Worker side: one gridded Open-Meteo fetch (primary ECMWF IFS model) saved as the cached snapshot."""
    from services.flood_engine import forcing as fm

    snapshot = fm.fetch_snapshot(bounds_lonlat, models=fm.MODELS[:1])
    save_snapshot(snapshot, grid_snapshot_path())
    return load_forecast_snapshot()


def save_snapshot(snapshot, path: Path) -> dict:
    """Persist the primary usable model of a ForcingSnapshot (atomic); returns its meta."""
    from services.flood_engine import forcing as fm

    model = snapshot.usable[0]
    meta = {"fetched_at": snapshot.fetched_at, "model": model.model, "label": model.label, "nominal_km": model.nominal_km,
            "url": model.url, "response_sha256": model.response_sha256, "lattice_deg": snapshot.lattice_deg,
            "forcing_sha256": snapshot.combined_sha256(), "attribution": fm.ATTRIBUTION, "endpoint": fm.ENDPOINT}
    meta["models_usable"] = [m.model for m in snapshot.usable]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + ".tmp.npz")
    np.savez_compressed(tmp, times_utc=np.asarray(model.times_utc), point_lat=model.point_lat, point_lon=model.point_lon,
                        native_lat=model.native_lat, native_lon=model.native_lon, values_mm=model.values_mm,
                        meta=np.asarray(json.dumps(meta)))
    tmp.replace(path)
    return meta


def load_forecast_snapshot(path: Path | None = None):
    """Rebuild a services.flood_engine.forcing.ForcingSnapshot from a saved snapshot (default: the cache; no network)."""
    from services.flood_engine import forcing as fm

    path = Path(path) if path else grid_snapshot_path()
    if not path.exists():
        raise Unavailable("no cached Open-Meteo snapshot")
    with np.load(path, allow_pickle=False) as z:
        meta = json.loads(str(z["meta"]))
        model = fm.ModelForcing(meta["model"], meta.get("label", meta["model"]), float(meta.get("nominal_km", 9.0)),
                                meta.get("url", fm.ENDPOINT), meta.get("response_sha256", ""), [str(t) for t in z["times_utc"]],
                                z["point_lat"], z["point_lon"], z["native_lat"], z["native_lon"], z["values_mm"])
    return fm.ForcingSnapshot(fetched_at=meta["fetched_at"], lattice_deg=float(meta.get("lattice_deg", fm.LATTICE_DEG)), models=[model])


def forecast_snapshot(fetch: bool, bounds_lonlat: list[float]):
    return fetch_forecast_snapshot(bounds_lonlat) if fetch else load_forecast_snapshot()
