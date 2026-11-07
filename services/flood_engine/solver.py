"""A06 local-inertial shallow-water solver with spatially varying rainfall (NumPy only).

Physics, limits and boundary handling are identical to ``pipelines/phase12/simulate.step``; the only change is
that rainfall may be a per-cell field. ``tests/phase12_openmeteo_grid`` asserts equivalence with A06 for uniform rain.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

G = 9.80665
CELL_M = 600.0


@dataclass(frozen=True)
class Member:
    member_id: int
    manning_multiplier: float
    infiltration_multiplier: float


def parameter_members() -> list[Member]:
    """The same 20 A06 Manning × infiltration multipliers."""
    combos = [(n, f) for f in (0.5, 0.75, 1.0, 1.5) for n in (0.75, 1.0, 1.25, 1.5, 2.0)]
    return [Member(i + 1, n, f) for i, (n, f) in enumerate(combos)]


INFILTRATION_MM_H = {10: 1.4, 20: 1.2, 30: 1.0, 40: 1.4, 50: 0.25, 60: 0.4, 70: 0.5, 80: 0.0, 90: 0.8, 95: 0.8, 100: 0.5}


def infiltration_rate(landcover: np.ndarray, multiplier: float) -> np.ndarray:
    mm = np.full(landcover.shape, 0.8)
    for cls, value in INFILTRATION_MM_H.items():
        mm[landcover == cls] = value
    return mm * multiplier / 1000 / 3600


def step(z, h, qx, qy, active, drain, mann, porosity, infiltration_m_s, rain_m_s, dx, dt):
    if dx <= 0 or dt <= 0:
        raise ValueError("dx and dt must be positive")
    valid = active | drain
    eta = z + h
    hx = np.maximum(h[:, :-1], h[:, 1:])
    hy = np.maximum(h[:-1, :], h[1:, :])
    nx = 0.5 * (mann[:, :-1] + mann[:, 1:])
    ny = 0.5 * (mann[:-1, :] + mann[1:, :])
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        ax = (qx - G * hx * dt * (eta[:, 1:] - eta[:, :-1]) / dx) / (1 + G * nx**2 * np.abs(qx) * dt / np.maximum(hx, 1e-5) ** (7 / 3))
        ay = (qy - G * hy * dt * (eta[1:, :] - eta[:-1, :]) / dx) / (1 + G * ny**2 * np.abs(qy) * dt / np.maximum(hy, 1e-5) ** (7 / 3))
    ax[~(valid[:, :-1] & valid[:, 1:])] = 0
    ay[~(valid[:-1, :] & valid[1:, :])] = 0
    ax[(drain[:, :-1] & active[:, 1:]) & (ax > 0)] = 0
    ax[(active[:, :-1] & drain[:, 1:]) & (ax < 0)] = 0
    ay[(drain[:-1, :] & active[1:, :]) & (ay > 0)] = 0
    ay[(active[:-1, :] & drain[1:, :]) & (ay < 0)] = 0
    capx_l = np.maximum(h[:, :-1], 0) * porosity[:, :-1] * dx / (4 * dt)
    capx_r = np.maximum(h[:, 1:], 0) * porosity[:, 1:] * dx / (4 * dt)
    ax = np.where(ax > 0, np.minimum(ax, capx_l), np.maximum(ax, -capx_r))
    capy_u = np.maximum(h[:-1, :], 0) * porosity[:-1, :] * dx / (4 * dt)
    capy_d = np.maximum(h[1:, :], 0) * porosity[1:, :] * dx / (4 * dt)
    ay = np.where(ay > 0, np.minimum(ay, capy_u), np.maximum(ay, -capy_d))
    div = np.zeros_like(h)
    div[:, :-1] += ax / dx
    div[:, 1:] -= ax / dx
    div[:-1, :] += ay / dx
    div[1:, :] -= ay / dx
    p = np.maximum(porosity, 1e-6)
    rain_depth = np.broadcast_to(np.asarray(rain_m_s, dtype=np.float64) * dt, h.shape)
    infil_depth = np.minimum(h + rain_depth, infiltration_m_s * dt / p)
    hn = h.copy()
    hn[active] = np.maximum(0, h[active] + rain_depth[active] / p[active] - infil_depth[active] - dt * div[active] / p[active])
    hn[drain | ~valid] = 0
    area = dx * dx
    rain_volume = float(np.sum(rain_depth[active]) * area)
    infiltration_volume = float(np.sum(infil_depth[active] * p[active]) * area)
    out = 0.0
    for q, aa, bb in ((ax, active[:, :-1], drain[:, 1:]), (-ax, drain[:, :-1], active[:, 1:]), (ay, active[:-1, :], drain[1:, :]), (-ay, drain[:-1, :], active[1:, :])):
        out += float(np.sum(np.maximum(q[aa & bb], 0)) * dx * dt)
    return hn, ax, ay, {"rain_m3": rain_volume, "infiltration_m3": infiltration_volume, "outflow_m3": out}


def stable_dt(h, active, dx):
    maxh = float(np.max(h[active])) if active.any() else 0.0
    return min(300.0, 0.45 * dx / max(math.sqrt(G * max(maxh, 1e-4)), 0.01))


def simulate(z, active, drain, mann, porosity, infiltration, rain_mm, dx=CELL_M, keep_from: int = 0):
    """Run hourly forcing ``rain_mm`` ([hours] or [hours, rows, cols] mm per preceding hour).

    Returns (hourly depth snapshots from ``keep_from`` onward as float32, diagnostics, steps).
    """
    rain_mm = np.asarray(rain_mm, dtype=np.float64)
    if not np.isfinite(rain_mm[(slice(None),) + ((active,) if rain_mm.ndim == 3 else ())]).all():
        raise ValueError("rainfall forcing contains missing values over active cells")
    h = np.zeros_like(z, dtype=np.float64)
    qx = np.zeros((z.shape[0], z.shape[1] - 1))
    qy = np.zeros((z.shape[0] - 1, z.shape[1]))
    total = {"rain_m3": 0.0, "infiltration_m3": 0.0, "outflow_m3": 0.0}
    snaps = []
    steps = 0
    for hour, mm in enumerate(rain_mm):
        rate = np.where(np.isfinite(mm), np.maximum(0, mm), 0) / 1000 / 3600 if np.ndim(mm) else max(0.0, float(mm)) / 1000 / 3600
        remaining = 3600.0
        while remaining > 1e-6:
            stable = stable_dt(h, active, dx)
            if stable < 0.1:
                raise RuntimeError(f"local-inertial stability step below 0.1 s: {stable:.6g}")
            dt = min(remaining, stable)
            h, qx, qy, d = step(z, h, qx, qy, active, drain, mann, porosity, np.maximum(0, infiltration), rate, dx, dt)
            for key in total:
                total[key] += d[key]
            remaining -= dt
            steps += 1
            if steps > 1_000_000:
                raise RuntimeError("simulation exceeded 1,000,000 time steps")
        if hour >= keep_from:
            snaps.append(h.astype(np.float32, copy=True))
    total["final_storage_m3"] = float(np.sum(h[active] * porosity[active]) * dx * dx)
    total["mass_balance_relative_error"] = abs(total["rain_m3"] - total["infiltration_m3"] - total["outflow_m3"] - total["final_storage_m3"]) / max(total["rain_m3"], 1e-9)
    return np.stack(snaps) if snaps else np.zeros((0,) + z.shape, np.float32), total, steps
