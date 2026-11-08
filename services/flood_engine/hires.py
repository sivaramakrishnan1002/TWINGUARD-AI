"""A25 high-resolution local-inertial solver (NumPy only): 30-120 m grids, fixed-stage sea boundary,
point inflows (reservoir releases), per-cell rainfall, sub-hourly frames and per-cell peak tracking.

Differences from the 600 m A06 pilot (``solver.py``, unchanged):
- Flow depth at a face uses the Bates et al. (2010) form ``max(eta_i, eta_j) - max(z_i, z_j)``.
- Rivers and inland water are active cells (the DEM has burned channels), so releases are conveyed to the sea;
  the sea is a fixed-stage boundary (stage = tide offset, m above MSL) instead of every water cell draining.
- Cells outside the domain are no-flow, as in A06. The A06 donor-volume limiter is kept.

Each time step is split into row strips processed by a thread pool (NumPy releases the GIL for large array
operations). Rows are independent within each phase, so results do not depend on the thread count.
"""
from __future__ import annotations

import math
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import numpy as np

G = 9.80665
NODATA_CM = 65535
# A27 flow sidecar encoding: int16 centi-units (0.01 m/s, 0.01 m); -32768 = NoData.
FLOW_NODATA = -32768
FLOW_SCALE = 0.01
WET_THRESHOLD_M = 0.01
WSE_VERTICAL_DATUM = "EGM2008 (Copernicus GLO-30 heights)"
F32 = np.float32


@dataclass
class HiresGrid:
    z: np.ndarray            # bed elevation (m, EGM2008 per GLO-30)
    active: np.ndarray       # computed cells
    boundary: np.ndarray     # fixed-stage (sea) cells
    mann: np.ndarray         # Manning n
    porosity: np.ndarray     # plan-area porosity (building coverage)
    infiltration_mm_h: np.ndarray
    cell_m: float


@dataclass
class HiresResult:
    frames_cm: np.ndarray            # [frames, rows, cols] uint16 depth in cm (65535 = NoData)
    frame_minutes: list[int]
    peak_m: np.ndarray               # float32, NaN outside domain
    peak_frame: np.ndarray           # int16 frame index of peak (-1 = never wet)
    peak_speed_mps: np.ndarray       # float32, sampled at frame times
    diagnostics: dict = field(default_factory=dict)
    # A27 (record_flow=True): per-frame cell-centred depth-averaged velocity and water-surface elevation,
    # int16 in units of FLOW_SCALE. u eastward (+x), v northward (+y); FLOW_NODATA outside the domain (u, v, wse)
    # and for dry cells (wse only; dry u = v = 0).
    flow_u: np.ndarray | None = None
    flow_v: np.ndarray | None = None
    flow_wse: np.ndarray | None = None


def _face_flux(q, eta_a, eta_b, z_a, z_b, n2, ok, dt, dx, hf, tmp):
    """In-place Bates local-inertial face update (n2 = Manning n squared, ok = float face mask)."""
    np.maximum(eta_a, eta_b, out=hf)
    np.maximum(z_a, z_b, out=tmp)
    hf -= tmp
    wet = hf > 1e-4
    np.maximum(hf, F32(1e-4), out=hf)
    np.abs(q, out=tmp)
    tmp *= n2
    tmp *= F32(G * dt)
    tmp /= hf ** F32(7.0 / 3.0)
    tmp += F32(1.0)
    slope = eta_b - eta_a
    slope *= hf
    slope *= F32(G * dt / dx)
    q -= slope
    q /= tmp
    q *= ok
    q *= wet


def _strips(n_rows: int, n_parts: int) -> list[tuple[int, int]]:
    edges = np.linspace(0, n_rows, n_parts + 1).astype(int)
    return [(int(a), int(b)) for a, b in zip(edges[:-1], edges[1:]) if b > a]


def run(grid: HiresGrid, rain_mm, rain_interval_s: float, duration_s: float, frame_interval_s: float,
        stage_m: float = 0.0, inflows=None, max_dt: float = 60.0, cfl: float = 0.7,
        boundary_stage_fn=None, progress=None, threads: int | None = None, record_flow: bool = True) -> HiresResult:
    """Simulate ``duration_s`` seconds.

    rain_mm: [intervals] (uniform) or [intervals, rows, cols], mm per interval; intervals beyond the array are dry.
    stage_m: sea-boundary water level (m). boundary_stage_fn(t_s) -> stage per boundary cell overrides it (nesting).
    inflows: iterable of (row, col, m3/s) point sources into active cells.
    """
    z = np.ascontiguousarray(grid.z, dtype=F32)
    ny, nx = z.shape
    act = np.asarray(grid.active, bool)
    bnd = np.asarray(grid.boundary, bool) & ~act
    wet_ok = act | bnd
    actf = act.astype(F32)
    dx = float(grid.cell_m)
    area = dx * dx
    p = np.where(act, np.maximum(np.asarray(grid.porosity, F32), F32(0.05)), F32(1.0)).astype(F32)
    n = np.asarray(grid.mann, F32)
    n2x = ((n[:, :-1] + n[:, 1:]) * F32(0.5)) ** 2
    n2y = ((n[:-1, :] + n[1:, :]) * F32(0.5)) ** 2
    okx = (wet_ok[:, :-1] & wet_ok[:, 1:]).astype(F32)
    oky = (wet_ok[:-1, :] & wet_ok[1:, :]).astype(F32)
    infil = (np.where(act, np.asarray(grid.infiltration_mm_h, np.float64), 0.0) / 1000.0 / 3600.0).astype(F32)
    rain_mm = np.asarray(rain_mm, dtype=np.float64 if np.ndim(rain_mm) == 1 else F32)
    spatial = rain_mm.ndim == 3
    src = np.zeros_like(z)
    inflow_m3s = 0.0
    for r, c, q in inflows or []:
        if act[r, c] and q > 0:
            src[r, c] += F32(q / area)
            inflow_m3s += float(q)
    has_src = inflow_m3s > 0

    h = np.zeros_like(z)
    bidx = np.flatnonzero(bnd)
    zb = z.ravel()[bidx]
    hb = np.zeros(len(bidx), dtype=F32)

    def set_boundary(tt):
        stage = boundary_stage_fn(tt) if boundary_stage_fn is not None else float(stage_m)
        hb[:] = np.maximum(np.asarray(stage, F32) - zb, F32(0.0))
        h.ravel()[bidx] = hb

    set_boundary(0.0)
    qx = np.zeros((ny, nx - 1), F32)
    qy = np.zeros((ny - 1, nx), F32)
    hfx, tmpx = np.empty_like(qx), np.empty_like(qx)
    hfy, tmpy = np.empty_like(qy), np.empty_like(qy)
    cap = np.empty_like(z)
    vol = np.empty_like(z)
    eta = np.empty_like(z)
    bnd_rows = np.zeros(ny, bool)
    bnd_rows[np.unique(bidx // nx)] = True

    nframes = int(round(duration_s / frame_interval_s)) + 1
    frames = np.full((nframes, ny, nx), NODATA_CM, dtype=np.uint16)
    peak = np.zeros_like(z)
    peak_frame = np.full((ny, nx), -1, dtype=np.int16)
    peak_speed = np.zeros_like(z)
    if record_flow:
        flow_u = np.full((nframes, ny, nx), FLOW_NODATA, dtype=np.int16)
        flow_v = np.full((nframes, ny, nx), FLOW_NODATA, dtype=np.int16)
        flow_wse = np.full((nframes, ny, nx), FLOW_NODATA, dtype=np.int16)
    else:
        flow_u = flow_v = flow_wse = None
    totals = {"rain_m3": 0.0, "inflow_m3": 0.0, "infiltration_m3": 0.0, "boundary_net_out_m3": 0.0}

    n_threads = max(1, min(threads or min(8, os.cpu_count() or 1), max(1, ny // 16)))
    strips = _strips(ny, n_threads)
    fstrips = _strips(ny - 1, n_threads)
    pool = ThreadPoolExecutor(max_workers=n_threads) if n_threads > 1 else None

    def pmap(fn, parts):
        if pool is None:
            return [fn(a, b) for a, b in parts]
        return list(pool.map(lambda ab: fn(*ab), parts))

    def record(k):
        cm = np.minimum(np.round(h * F32(100.0)), F32(NODATA_CM - 1)).astype(np.uint16)
        cm[~act] = NODATA_CM
        frames[k] = cm

    def record_flow_frame(k, ux, uy):
        """ux, uy: cell-centred discharge per width (m2/s); qy > 0 flows to the next row (south)."""
        wet = act & (h >= WET_THRESHOLD_M)
        hs = np.maximum(h, F32(WET_THRESHOLD_M))
        u = np.where(wet, ux / hs, F32(0.0))
        v = np.where(wet, -uy / hs, F32(0.0))
        enc = lambda a: np.clip(np.round(a / FLOW_SCALE), -32767, 32767).astype(np.int16)  # noqa: E731
        fu, fv = enc(u), enc(v)
        fw = enc(z + h)
        fu[~act] = FLOW_NODATA
        fv[~act] = FLOW_NODATA
        fw[~wet] = FLOW_NODATA
        flow_u[k], flow_v[k], flow_wse[k] = fu, fv, fw

    def update_peak(frame_index):
        hn = h * actf
        changed = hn > peak
        if changed.any():
            peak_frame[changed] = frame_index
            np.maximum(peak, hn, out=peak)

    # ---- per-strip phases -------------------------------------------------------------------------------
    def phase_eta_cap(a, b, dt):
        np.add(z[a:b], h[a:b], out=eta[a:b])
        np.multiply(h[a:b], p[a:b], out=cap[a:b])
        cap[a:b] *= F32(dx / (4.0 * dt))

    def phase_flux(a, b, fa, fb, dt):
        _face_flux(qx[a:b], eta[a:b, :-1], eta[a:b, 1:], z[a:b, :-1], z[a:b, 1:], n2x[a:b], okx[a:b], dt, dx, hfx[a:b], tmpx[a:b])
        np.minimum(qx[a:b], cap[a:b, :-1], out=qx[a:b])
        np.maximum(qx[a:b], -cap[a:b, 1:], out=qx[a:b])
        if fb > fa:
            _face_flux(qy[fa:fb], eta[fa:fb], eta[fa + 1:fb + 1], z[fa:fb], z[fa + 1:fb + 1], n2y[fa:fb], oky[fa:fb], dt, dx, hfy[fa:fb], tmpy[fa:fb])
            np.minimum(qy[fa:fb], cap[fa:fb], out=qy[fa:fb])
            np.maximum(qy[fa:fb], -cap[fa + 1:fb + 1], out=qy[fa:fb])

    def phase_update(a, b, dt, rate_field, rate_scalar):
        d = np.zeros((b - a, nx), F32)
        d[:, :-1] += qx[a:b]
        d[:, 1:] -= qx[a:b]
        lo, hi = a, min(b, ny - 1)
        if hi > lo:
            d[: hi - a] += qy[lo:hi]
        lo2 = max(a, 1)
        if b > lo2:
            d[lo2 - a:] -= qy[lo2 - 1:b - 1]
        d *= F32(dt / dx)
        v = vol[a:b]
        np.multiply(h[a:b], p[a:b], out=v)
        rain_sum = 0.0
        if rate_field is not None:
            rd = rate_field[a:b] * F32(dt) * actf[a:b]
            v += rd
            rain_sum = float(rd.sum(dtype=np.float64))
        elif rate_scalar:
            rd = F32(rate_scalar * dt)
            v += rd * actf[a:b]
            rain_sum = float(rate_scalar * dt) * float(actf[a:b].sum(dtype=np.float64))
        if has_src:
            v += src[a:b] * F32(dt)
        infil_d = np.minimum(v, infil[a:b] * F32(dt))
        v -= infil_d
        v -= d
        boundary_out = 0.0
        if bnd_rows[a:b].any():
            boundary_out = float(d[bnd[a:b]].sum(dtype=np.float64))
        np.maximum(v, F32(0.0), out=v)
        v /= p[a:b]
        np.multiply(v, actf[a:b], out=h[a:b])
        return rain_sum, float(infil_d.sum(dtype=np.float64)), boundary_out, float(h[a:b].max())

    pairs = list(zip(strips, [(fa, fb) for fa, fb in _strips(ny - 1, len(strips))]))
    record(0)
    if record_flow:
        record_flow_frame(0, np.zeros_like(h), np.zeros_like(h))
    t = 0.0
    next_frame = 1
    steps = 0
    min_dt = max_dt
    hmax = 0.0
    try:
        while t < duration_s - 1e-6:
            dt = min(max_dt, cfl * dx / math.sqrt(G * max(hmax, 0.01)), duration_s - t)
            if next_frame < nframes:
                dt = min(dt, next_frame * frame_interval_s - t)
            if dt < 0.05 and next_frame * frame_interval_s - t > 0.05:
                raise RuntimeError(f"time step collapsed to {dt:.4f} s")
            if dt > 1e-3:
                min_dt = min(min_dt, dt)
            if boundary_stage_fn is not None:
                set_boundary(t)
            pmap(lambda a, b: phase_eta_cap(a, b, dt), strips)
            cap.ravel()[bidx] = np.inf
            if pool is None:
                for (a, b), (fa, fb) in pairs:
                    phase_flux(a, b, fa, fb, dt)
            else:
                list(pool.map(lambda pr: phase_flux(pr[0][0], pr[0][1], pr[1][0], pr[1][1], dt), pairs))
            k = int(t // rain_interval_s)
            rate_field, rate_scalar = None, 0.0
            if k < len(rain_mm):
                if spatial:
                    rate_field = rain_mm[k] * F32(1.0 / 1000.0 / rain_interval_s)
                else:
                    rate_scalar = float(rain_mm[k]) / 1000.0 / rain_interval_s
            parts = pmap(lambda a, b: phase_update(a, b, dt, rate_field, rate_scalar), strips)
            h.ravel()[bidx] = hb
            totals["rain_m3"] += sum(x[0] for x in parts) * area
            totals["infiltration_m3"] += sum(x[1] for x in parts) * area
            totals["boundary_net_out_m3"] -= sum(x[2] for x in parts) * area
            totals["inflow_m3"] += inflow_m3s * dt
            hmax = max(x[3] for x in parts)  # CFL depth for the next step
            t += dt
            steps += 1
            if steps % 10 == 0:
                update_peak(min(next_frame, nframes - 1))
            if next_frame < nframes and t >= next_frame * frame_interval_s - 1e-6:
                update_peak(next_frame)
                ux = np.zeros_like(h)
                uy = np.zeros_like(h)
                ux[:, :-1] += F32(0.5) * qx
                ux[:, 1:] += F32(0.5) * qx
                uy[:-1, :] += F32(0.5) * qy
                uy[1:, :] += F32(0.5) * qy
                speed = np.hypot(ux, uy) / np.maximum(h, F32(0.01))
                speed[h <= 0.01] = 0.0
                np.maximum(peak_speed, speed * actf, out=peak_speed)
                record(next_frame)
                if record_flow:
                    record_flow_frame(next_frame, ux, uy)
                next_frame += 1
                if progress:
                    progress(t / duration_s)
            if steps > 5_000_000:
                raise RuntimeError("exceeded 5,000,000 steps")
    finally:
        if pool is not None:
            pool.shutdown(wait=False)
    update_peak(nframes - 1)
    storage = float(np.sum(h[act].astype(np.float64) * p[act]) * area)
    inputs = totals["rain_m3"] + totals["inflow_m3"]
    residual = inputs - totals["infiltration_m3"] - totals["boundary_net_out_m3"] - storage
    diag = {**totals, "final_storage_m3": storage, "steps": steps, "min_dt_s": min_dt, "threads": n_threads,
            "mass_balance_relative_error": abs(residual) / max(inputs, 1e-9), "inflow_m3s": inflow_m3s}
    peak_frame[peak <= 0] = -1
    return HiresResult(frames, [int(round(k * frame_interval_s / 60)) for k in range(nframes)],
                       np.where(act, peak, np.nan).astype(np.float32), peak_frame,
                       np.where(act, peak_speed, np.nan).astype(np.float32), diag, flow_u, flow_v, flow_wse)
