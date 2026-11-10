"""Gridded Open-Meteo precipitation forcing for the A06 600 m domain (A23 / CR-015 / CR-018).

Semantics kept explicit:
- Open-Meteo hourly ``precipitation`` is the sum over the *preceding* hour (mm), labelled by its end time (UTC here).
- Values are numerical-weather-model output, never rain-gauge observations.
- A model's native cell is identified by the grid coordinate the API returns; the A06 cell takes the value of the
  nearest sampled native cell (piecewise-constant, no smoothing or invented sub-grid variability).
- Missing values stay missing: a model with any missing hour over the domain is excluded, never zero-filled.
"""
from __future__ import annotations

import hashlib
import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import numpy as np

ENDPOINT = "https://api.open-meteo.com/v1/forecast"
ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0); upstream national weather services."
# Primary model first. Native spacing is the provider-documented nominal value.
MODELS: tuple[tuple[str, str, float], ...] = (
    ("ecmwf_ifs", "ECMWF IFS HRES", 9.0),
    ("ukmo_global_deterministic_10km", "UK Met Office Global 10 km", 10.0),
    ("icon_global", "DWD ICON Global", 13.0),
)
PAST_HOURS = 24
FORECAST_HOURS = 72
LATTICE_DEG = 0.05  # ~5.5 km: finer than every native grid (>= 9 km), so each native cell over the domain is sampled
# Open-Meteo free tier counts each location as a call (600/min, 5,000/h, 10,000/day). 3 models x 80 points
# = ~240 calls per run, so even a 2-hour cycle would use ~2,900/day.
MARGIN_DEG = 0.03
USER_AGENT = "TwinGuard-educational-prototype/1.0"


class ForcingError(RuntimeError):
    pass


@dataclass
class ModelForcing:
    model: str
    label: str
    nominal_km: float
    url: str
    response_sha256: str
    times_utc: list[str]
    point_lat: np.ndarray
    point_lon: np.ndarray
    native_lat: np.ndarray
    native_lon: np.ndarray
    values_mm: np.ndarray  # [points, hours]
    native_cells: int = 0
    status: str = "ok"
    reason: str | None = None


@dataclass
class ForcingSnapshot:
    fetched_at: str
    lattice_deg: float
    models: list[ModelForcing] = field(default_factory=list)
    raw: dict[str, bytes] = field(default_factory=dict)

    @property
    def usable(self) -> list[ModelForcing]:
        return [m for m in self.models if m.status == "ok"]

    def combined_sha256(self) -> str:
        digest = hashlib.sha256()
        for item in sorted(self.usable, key=lambda m: m.model):
            digest.update(item.model.encode())
            digest.update(item.values_mm.astype("<f8").tobytes())
            digest.update("|".join(item.times_utc).encode())
        return digest.hexdigest()


def lattice(bounds_lonlat: list[float], spacing: float = LATTICE_DEG, margin: float = MARGIN_DEG) -> tuple[np.ndarray, np.ndarray]:
    west, south, east, north = bounds_lonlat
    lats = np.round(np.arange(south - margin, north + margin + 1e-9, spacing), 4)
    lons = np.round(np.arange(west - margin, east + margin + 1e-9, spacing), 4)
    grid_lat, grid_lon = np.meshgrid(lats, lons, indexing="ij")
    return grid_lat.ravel(), grid_lon.ravel()


def request_url(model: str, lat: np.ndarray, lon: np.ndarray) -> str:
    query = {
        "latitude": ",".join(f"{v:.4f}" for v in lat),
        "longitude": ",".join(f"{v:.4f}" for v in lon),
        "hourly": "precipitation",
        "models": model,
        "past_hours": str(PAST_HOURS),
        "forecast_hours": str(FORECAST_HOURS),
        "timezone": "GMT",
        "timeformat": "iso8601",
        "precipitation_unit": "mm",
        "cell_selection": "nearest",
    }
    return f"{ENDPOINT}?{urllib.parse.urlencode(query)}"


def _http_get(url: str, timeout: float, retry_after_429: float = 65.0) -> bytes:
    import time
    import urllib.error
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed https endpoint
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt == 1 and retry_after_429 > 0:
                time.sleep(retry_after_429)  # one polite retry after the per-minute window
                continue
            raise ForcingError(f"HTTP {error.code}") from None
    raise ForcingError("request failed")


def parse_model(model: str, label: str, nominal_km: float, url: str, body: bytes, lat: np.ndarray, lon: np.ndarray) -> ModelForcing:
    payload = json.loads(body)
    items = payload if isinstance(payload, list) else [payload]
    if len(items) != len(lat):
        raise ForcingError(f"{model}: expected {len(lat)} locations, received {len(items)}")
    times: list[str] | None = None
    values = np.full((len(items), PAST_HOURS + FORECAST_HOURS), np.nan)
    nlat = np.empty(len(items))
    nlon = np.empty(len(items))
    for i, item in enumerate(items):
        if item.get("error"):
            raise ForcingError(f"{model}: provider error {item.get('reason', '')[:120]}")
        if item.get("utc_offset_seconds") != 0:
            raise ForcingError(f"{model}: response is not UTC")
        if (item.get("hourly_units") or {}).get("precipitation") != "mm":
            raise ForcingError(f"{model}: precipitation unit is not mm")
        hourly = item.get("hourly") or {}
        t = hourly.get("time")
        v = hourly.get("precipitation")
        if not isinstance(t, list) or not isinstance(v, list) or len(t) != len(v):
            raise ForcingError(f"{model}: hourly series missing or misaligned")
        if times is None:
            times = t
            _check_hourly(times, model)
        elif t != times:
            raise ForcingError(f"{model}: locations returned different valid times")
        if len(v) != values.shape[1]:
            raise ForcingError(f"{model}: expected {values.shape[1]} hours, received {len(v)}")
        values[i] = [np.nan if x is None else float(x) for x in v]
        nlat[i] = float(item["latitude"])
        nlon[i] = float(item["longitude"])
    if np.any(values[np.isfinite(values)] < 0):
        raise ForcingError(f"{model}: negative precipitation")
    native = len({(round(a, 4), round(b, 4)) for a, b in zip(nlat, nlon)})
    forcing = ModelForcing(model, label, nominal_km, url, hashlib.sha256(body).hexdigest(), times or [], lat, lon, nlat, nlon, values, native)
    if np.isnan(values).any():
        forcing.status, forcing.reason = "excluded", f"{int(np.isnan(values).sum())} missing point-hours; not zero-filled"
    return forcing


def _check_hourly(times: list[str], model: str) -> None:
    parsed = [datetime.fromisoformat(t).replace(tzinfo=timezone.utc) for t in times]
    for a, b in zip(parsed, parsed[1:]):
        if b - a != timedelta(hours=1):
            raise ForcingError(f"{model}: valid times are not consecutive hours")


def fetch_snapshot(bounds_lonlat: list[float], models=MODELS, timeout: float = 60.0, getter=_http_get, now=None) -> ForcingSnapshot:
    lat, lon = lattice(bounds_lonlat)
    fetched_at = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    snapshot = ForcingSnapshot(fetched_at=fetched_at, lattice_deg=LATTICE_DEG)
    for model, label, km in models:
        url = request_url(model, lat, lon)
        try:
            body = getter(url, timeout)
            snapshot.raw[model] = body
            snapshot.models.append(parse_model(model, label, km, url, body, lat, lon))
        except Exception as error:  # one model failing must not fabricate or block the others
            empty = np.empty(0)
            snapshot.models.append(ModelForcing(model, label, km, url, "", [], lat, lon, empty, empty, np.empty((0, 0)), 0, "excluded", f"{type(error).__name__}: {str(error)[:160]}"))
    usable = snapshot.usable
    if not usable:
        raise ForcingError("no weather model returned complete domain precipitation")
    reference = usable[0].times_utc
    for item in usable[1:]:
        if item.times_utc != reference:
            item.status, item.reason = "excluded", "valid times differ from primary model"
    return snapshot


def map_to_grid(forcing: ModelForcing, cell_lat: np.ndarray, cell_lon: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Return [hours, rows, cols] mm. Cells outside ``mask`` are NaN (not dry)."""
    lat0 = math.radians(float(np.nanmean(cell_lat[mask])))
    px = forcing.point_lon * math.cos(lat0)
    py = forcing.point_lat
    cx = cell_lon[mask] * math.cos(lat0)
    cy = cell_lat[mask]
    nearest = np.empty(len(cx), dtype=np.int64)
    for i in range(0, len(cx), 20000):  # chunked: bounded memory on 30-120 m grids
        sl = slice(i, i + 20000)
        nearest[sl] = np.argmin((cx[sl, None] - px[None, :]) ** 2 + (cy[sl, None] - py[None, :]) ** 2, axis=1)
    hours = forcing.values_mm.shape[1]
    field_mm = np.full((hours,) + mask.shape, np.nan)
    field_mm[:, mask] = forcing.values_mm[nearest].T
    return field_mm


def manifest(snapshot: ForcingSnapshot) -> dict:
    return {
        "provider": "Open-Meteo Forecast API",
        "endpoint": ENDPOINT,
        "attribution": ATTRIBUTION,
        "fetched_at": snapshot.fetched_at,
        "lattice_deg": snapshot.lattice_deg,
        "past_hours": PAST_HOURS,
        "forecast_hours": FORECAST_HOURS,
        "time_semantics": "hourly precipitation is the sum over the preceding hour; labels are interval end times in UTC",
        "source_class": "numerical weather model output; not rain-gauge observation",
        "combined_forcing_sha256": snapshot.combined_sha256(),
        "models": [
            {"model": m.model, "label": m.label, "nominal_native_km": m.nominal_km, "status": m.status, "reason": m.reason,
             "response_sha256": m.response_sha256, "sampled_points": int(len(m.point_lat)), "distinct_native_cells": m.native_cells,
             "first_valid_time_utc": m.times_utc[0] if m.times_utc else None, "last_valid_time_utc": m.times_utc[-1] if m.times_utc else None}
            for m in snapshot.models
        ],
    }
