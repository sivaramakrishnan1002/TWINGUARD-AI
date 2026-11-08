"""C4 v3 simulation driver: builds forcing and steps the A06/A23 solver (services.flood_engine, read-only).

The solver's own ``simulate`` keeps hourly snapshots only, so this driver uses the same ``step``/``stable_dt``
functions with sub-hourly frame and forcing boundaries. Physics and limits are the engine's.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from services.flood_engine import solver

from . import config
from .static import Grid

# Assumption-based what-if proxies (documented in limitations; not routed hydraulics).
RESERVOIRS = {
    # name: (reservoir lon, lat), downstream corridor lat band, lon band, assumed bank-full channel capacity m3/s
    "CHEMBARAMBAKKAM": ((80.06, 13.01), (12.99, 13.035), (80.08, 80.29), 900.0),
    "POONDI": ((79.86, 13.19), (13.16, 13.25), (80.05, 80.33), 700.0),
    "PUZHAL": ((80.17, 13.16), (13.13, 13.20), (80.18, 80.33), 300.0),
    "CHOLAVARAM": ((80.15, 13.22), (13.17, 13.25), (80.15, 80.33), 200.0),
}
COASTAL_BAND_CELLS = 8  # ~4.8 km at 600 m

ALL_MEMBERS = [(m.manning_multiplier, m.infiltration_multiplier) for m in solver.parameter_members()]
DEFAULT_MEMBERS = [(1.0, 1.0), (0.75, 0.5), (2.0, 1.5), (1.5, 0.5), (0.75, 1.5)]


def members() -> list[tuple[float, float]]:
    setting = config.members_setting()
    if setting == "all":
        return ALL_MEMBERS
    n = max(1, min(len(DEFAULT_MEMBERS), int(setting) if setting.isdigit() else 5))
    return DEFAULT_MEMBERS[:n]


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def sha_array(*arrays) -> str:
    digest = hashlib.sha256()
    for a in arrays:
        digest.update(np.ascontiguousarray(np.asarray(a, dtype="<f8")).tobytes())
    return digest.hexdigest()


class Forcing:
    """Rainfall in mm per interval, uniform ([n]) or gridded ([n, rows, cols]); time 0 = spin-up start."""

    def __init__(self, values_mm, interval_minutes: int, start: datetime, spinup_minutes: int, inputs: list[dict]):
        self.values = np.nan_to_num(np.asarray(values_mm, dtype=np.float64), nan=0.0)
        self.interval_s = int(interval_minutes) * 60
        self.start = start
        self.spinup_s = int(spinup_minutes) * 60
        self.inputs = inputs

    def rate_m_s(self, t: float):
        i = int(t // self.interval_s)
        if i >= len(self.values):
            return 0.0
        return np.maximum(self.values[i], 0.0) / 1000.0 / self.interval_s

    def next_boundary(self, t: float) -> float:
        return (math.floor(t / self.interval_s + 1e-9) + 1) * self.interval_s

    def sha256(self) -> str:
        return sha_array(self.values, [self.interval_s, self.spinup_s, self.start.timestamp()])

    def save(self, path: Path) -> None:
        np.savez_compressed(path, values=self.values.astype(np.float32), interval_minutes=self.interval_s // 60,
                            start_utc=np.asarray(iso(self.start)), spinup_minutes=self.spinup_s // 60,
                            inputs=np.asarray(json.dumps(self.inputs)))

    @classmethod
    def load(cls, path: Path) -> "Forcing":
        with np.load(path, allow_pickle=False) as z:
            return cls(z["values"], int(z["interval_minutes"]), parse_iso(str(z["start_utc"])), int(z["spinup_minutes"]),
                       json.loads(str(z["inputs"])))


def event_forcing(event: dict, duration_hours: int) -> Forcing:
    hourly = np.asarray(event["hourly_mm"], dtype=np.float64)
    if duration_hours > len(hourly):
        raise ValueError("duration exceeds the saved event window")
    window = np.convolve(hourly, np.ones(duration_hours), mode="valid")
    start_idx = int(np.argmax(window))
    spin = min(24, start_idx)
    start = parse_iso(event["start_utc"]) + timedelta(hours=start_idx - spin)
    values = hourly[start_idx - spin:start_idx + duration_hours]
    inputs = [{"name": f"event rainfall {event['event_key']}", "source": event["rainfall_source"], "source_mode": "REPLAY",
               "fetched_at": None, "sha256": sha_array(hourly)}]
    return Forcing(values, 60, start, spin * 60, inputs)


def custom_forcing(custom: dict) -> Forcing:
    values = np.asarray(custom["values_mm"], dtype=np.float64)
    inputs = [{"name": "custom rainfall", "source": "user-entered uniform rainfall (mm per interval)",
               "source_mode": "SCENARIO_INPUT", "fetched_at": None, "sha256": sha_array(values)}]
    return Forcing(values, int(custom["interval_minutes"]), parse_iso(custom["start_time_utc"]), 0, inputs)


def forecast_forcing(grid: Grid, snapshot) -> Forcing:
    """Open-Meteo lattice snapshot (forcing.ForcingSnapshot) mapped onto this grid: 24 h spin-up then forecast hours."""
    from services.flood_engine import forcing as fm

    model = snapshot.usable[0]
    values = fm.map_to_grid(model, grid.arrays["cell_lat"].astype(float), grid.arrays["cell_lon"].astype(float), grid.active | grid.drain)
    first_valid = datetime.fromisoformat(model.times_utc[0]).replace(tzinfo=timezone.utc)
    start = first_valid - timedelta(hours=1)  # hourly values are sums over the preceding hour
    inputs = [{"name": "Open-Meteo gridded precipitation", "source": f"Open-Meteo Forecast API ({model.model})",
               "source_mode": "MODEL_FORECAST", "fetched_at": snapshot.fetched_at, "sha256": snapshot.combined_sha256()}]
    values = np.where(grid.active | grid.drain, np.nan_to_num(values, nan=0.0), 0.0)
    return Forcing(values, 60, start, fm.PAST_HOURS * 60, inputs)


def whatif_forcing(base: Forcing, scale_pct: float) -> Forcing:
    inputs = list(base.inputs) + [{"name": "rainfall scale", "source": f"what-if {scale_pct:g}% of base rainfall",
                                   "source_mode": "SCENARIO_INPUT", "fetched_at": None, "sha256": None}]
    return Forcing(base.values * (scale_pct / 100.0), base.interval_s // 60, base.start, base.spinup_s // 60, inputs)


def reservoir_inflow(grid: Grid, releases: dict[str, float]) -> tuple[np.ndarray, dict]:
    """Excess release above an assumed bank-full capacity, spread over land cells next to the downstream channel (m/s)."""
    rate = np.zeros(grid.shape)
    detail = {}
    lon, lat = grid.arrays["cell_lon"], grid.arrays["cell_lat"]
    near_drain = np.zeros(grid.shape, bool)
    d = grid.drain
    near_drain[1:, :] |= d[:-1, :]
    near_drain[:-1, :] |= d[1:, :]
    near_drain[:, 1:] |= d[:, :-1]
    near_drain[:, :-1] |= d[:, 1:]
    area = grid.cell_size_m ** 2
    for name, release in (releases or {}).items():
        _, (la0, la1), (lo0, lo1), capacity = RESERVOIRS[name]
        excess = max(0.0, float(release) - capacity)
        corridor = grid.active & near_drain & (lat >= la0) & (lat <= la1) & (lon >= lo0) & (lon <= lo1)
        n = int(corridor.sum())
        detail[name] = {"release_m3s": float(release), "assumed_bankfull_m3s": capacity, "excess_m3s": excess, "cells": n}
        if excess > 0 and n:
            rate[corridor] += excess / (n * area)
    return rate, detail


def coastal_drains(grid: Grid) -> np.ndarray:
    """Channel/open-water (drain) cells within a few km of the eastern coastline in each row (tidal outfalls)."""
    valid = grid.active | grid.drain
    mask = np.zeros(grid.shape, bool)
    for r in range(grid.shape[0]):
        cols = np.flatnonzero(valid[r])
        if cols.size:
            east = cols.max()
            band = np.arange(max(0, east - COASTAL_BAND_CELLS + 1), east + 1)
            mask[r, band] = grid.drain[r, band]
    return mask


def run(grid: Grid, forcing: Forcing, duration_hours: int, frame_minutes: int, extra_inflow_m_s=None,
        tide_offset_m: float = 0.0, progress=None) -> dict:
    """Run all members; return frame stacks and diagnostics. Depth is NaN outside active cells (unknown, not dry)."""
    a = grid.arrays
    z, active, drain, porosity = a["z"], grid.active, grid.drain, a["porosity"]
    dx = grid.cell_size_m
    frame_s = frame_minutes * 60
    n_frames = duration_hours * 60 // frame_minutes
    end = forcing.spinup_s + n_frames * frame_s
    member_set = members()
    # Tide proxy: raised outfall water level in coastal drain cells (the solver resets drains to 0 after each step, and
    # never lets drains push water onto land, so a higher outfall level only blocks land drainage; no volume is added).
    tidal = coastal_drains(grid) if tide_offset_m > 0 else None
    tide_level = np.where(tidal, np.maximum(0.0, tide_offset_m - z), 0.0) if tidal is not None else None
    stacks = np.zeros((len(member_set), n_frames) + grid.shape, np.float32)
    velocity = np.zeros((n_frames,) + grid.shape, np.float32)
    diag_rows = []
    started = time.perf_counter()
    for mi, (n_mult, f_mult) in enumerate(member_set):
        h = np.zeros(grid.shape)
        qx = np.zeros((grid.shape[0], grid.shape[1] - 1))
        qy = np.zeros((grid.shape[0] - 1, grid.shape[1]))
        mann = a["mann"] * n_mult
        infil = np.maximum(0, solver.infiltration_rate(a["landcover"], f_mult))
        t, steps, frame = 0.0, 0, 0
        totals = {"rain_m3": 0.0, "infiltration_m3": 0.0, "outflow_m3": 0.0}
        next_frame = forcing.spinup_s + frame_s
        while t < end - 1e-6:
            stable = solver.stable_dt(h, active, dx)
            if stable < 0.1:
                raise RuntimeError(f"local-inertial stability step below 0.1 s: {stable:.4g}")
            dt = min(stable, forcing.next_boundary(t) - t, next_frame - t)
            rain = forcing.rate_m_s(t)
            if extra_inflow_m_s is not None:
                rain = rain + extra_inflow_m_s  # the solver books this volume as rain_m3
            h, qx, qy, d = solver.step(z, h, qx, qy, active, drain, mann, porosity, infil, rain, dx, dt)
            if tide_level is not None:
                h = np.where(tidal, tide_level, h)
            for key in ("rain_m3", "infiltration_m3", "outflow_m3"):
                totals[key] += d[key]
            t += dt
            steps += 1
            if steps > 2_000_000:
                raise RuntimeError("simulation exceeded 2,000,000 time steps")
            if t >= next_frame - 1e-6 and frame < n_frames:
                stacks[mi, frame] = h
                if mi == 0:
                    velocity[frame] = _velocity(h, qx, qy)
                frame += 1
                next_frame += frame_s
                if progress:
                    progress(100.0 * (mi + frame / n_frames) / len(member_set))
        if not np.isfinite(stacks[mi]).all():
            raise RuntimeError("non-finite depth")
        storage = float(np.sum(h[active] * porosity[active]) * dx * dx)
        supplied = totals["rain_m3"]
        error = abs(supplied - totals["infiltration_m3"] - totals["outflow_m3"] - storage) / max(supplied, 1e-9)
        diag_rows.append({"manning_multiplier": n_mult, "infiltration_multiplier": f_mult, "steps": steps,
                          "mass_balance_relative_error": round(error, 6)})
    nan_out = np.where(active, 0.0, np.nan).astype(np.float32)
    if len(member_set) > 1:
        p05, p95 = np.percentile(stacks, 5, axis=0), np.percentile(stacks, 95, axis=0)
    else:
        p05 = p95 = stacks[0]
    return {
        "depth_mean": (stacks.mean(axis=0) + nan_out).astype(np.float32),
        "depth_p05": (p05 + nan_out).astype(np.float32),
        "depth_p95": (p95 + nan_out).astype(np.float32),
        "velocity_mps": (velocity + nan_out).astype(np.float32),
        "members": diag_rows,
        "runtime_seconds": round(time.perf_counter() - started, 2),
        "frame_start": forcing.start + timedelta(seconds=forcing.spinup_s),
    }


def _velocity(h, qx, qy) -> np.ndarray:
    """Cell speed (m/s) from mean face unit discharges; zero where depth < 1 cm."""
    ux = np.zeros_like(h)
    uy = np.zeros_like(h)
    ux[:, :-1] += 0.5 * qx
    ux[:, 1:] += 0.5 * qx
    uy[:-1, :] += 0.5 * qy
    uy[1:, :] += 0.5 * qy
    speed = np.hypot(ux, uy) / np.maximum(h, 1e-2)
    return np.where(h >= 0.01, np.minimum(speed, 10.0), 0.0)
