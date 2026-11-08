"""A26 optional CUDA backend for ``hires.run`` (torch float32). Same equations, limiter, boundary handling,
frames, peaks and A27 flow output as the NumPy reference; NumPy stays the default and the fallback.

The whole grid lives on the GPU (the largest A25 grid, 90 m citywide, needs ~25 MB); frames are copied to host
memory as they are recorded, so VRAM does not grow with run length. Volume totals accumulate on the device in
float64, so the only per-step host sync is the max depth needed for the CFL time step.
"""
from __future__ import annotations

import math

import numpy as np

from .hires import (FLOW_NODATA, FLOW_SCALE, G, NODATA_CM, WET_THRESHOLD_M, HiresGrid, HiresResult)


def available() -> tuple[bool, str | None]:
    """(True, device name) when torch with CUDA is usable; otherwise (False, reason)."""
    try:
        import torch
    except Exception as error:  # noqa: BLE001 - torch is an optional extra
        return False, f"torch not importable: {type(error).__name__}"
    try:
        if not torch.cuda.is_available():
            return False, "torch.cuda.is_available() is False"
        return True, torch.cuda.get_device_name(0)
    except Exception as error:  # noqa: BLE001
        return False, f"CUDA query failed: {type(error).__name__}: {str(error)[:120]}"


_WARM: dict = {}


def warmup(device: str = "cuda") -> dict:
    """Import torch and create the CUDA context once per process; returns the seconds spent (0 when already warm).
    A long-lived worker can call this at start-up so the first simulation does not pay ~5-20 s of cold init."""
    import time
    if device in _WARM:
        return {"torch_import_s": 0.0, "cuda_context_s": 0.0}
    t = time.perf_counter()
    import torch
    t_import = time.perf_counter() - t
    t = time.perf_counter()
    torch.zeros(1, device=device)
    torch.cuda.synchronize(device)
    _WARM[device] = True
    return {"torch_import_s": t_import, "cuda_context_s": time.perf_counter() - t}


def run(grid: HiresGrid, rain_mm, rain_interval_s: float, duration_s: float, frame_interval_s: float,
        stage_m: float = 0.0, inflows=None, max_dt: float = 60.0, cfl: float = 0.7,
        boundary_stage_fn=None, progress=None, threads: int | None = None, record_flow: bool = True,
        device: str = "cuda") -> HiresResult:
    import torch

    dev = torch.device(device)
    f32 = torch.float32
    T = lambda a, dt=f32: torch.as_tensor(np.ascontiguousarray(a), dtype=dt, device=dev)  # noqa: E731
    if dev.type == "cuda":
        torch.cuda.reset_peak_memory_stats(dev)

    z_np = np.ascontiguousarray(grid.z, dtype=np.float32)
    ny, nx = z_np.shape
    act_np = np.asarray(grid.active, bool)
    bnd_np = np.asarray(grid.boundary, bool) & ~act_np
    wet_ok = act_np | bnd_np
    dx = float(grid.cell_m)
    area = dx * dx
    p_np = np.where(act_np, np.maximum(np.asarray(grid.porosity, np.float32), np.float32(0.05)), np.float32(1.0)).astype(np.float32)
    n = np.asarray(grid.mann, np.float32)
    z = T(z_np)
    act = T(act_np, torch.bool)
    actf = act.to(f32)
    p = T(p_np)
    n2x = T(((n[:, :-1] + n[:, 1:]) * np.float32(0.5)) ** 2)
    n2y = T(((n[:-1, :] + n[1:, :]) * np.float32(0.5)) ** 2)
    okx = T((wet_ok[:, :-1] & wet_ok[:, 1:]).astype(np.float32))
    oky = T((wet_ok[:-1, :] & wet_ok[1:, :]).astype(np.float32))
    infil = T((np.where(act_np, np.asarray(grid.infiltration_mm_h, np.float64), 0.0) / 1000.0 / 3600.0).astype(np.float32))
    rain_np = np.asarray(rain_mm, dtype=np.float64 if np.ndim(rain_mm) == 1 else np.float32)
    spatial = rain_np.ndim == 3
    src_np = np.zeros_like(z_np)
    inflow_m3s = 0.0
    for r, c, q in inflows or []:
        if act_np[r, c] and q > 0:
            src_np[r, c] += np.float32(q / area)
            inflow_m3s += float(q)
    has_src = inflow_m3s > 0
    src = T(src_np)
    bidx_np = np.flatnonzero(bnd_np)
    bidx = torch.as_tensor(bidx_np, dtype=torch.long, device=dev)
    bmask = T(bnd_np, torch.bool)
    zb_np = z_np.ravel()[bidx_np]
    zb = z.reshape(-1)[bidx]
    h = torch.zeros((ny, nx), dtype=f32, device=dev)
    hb = torch.zeros(len(bidx_np), dtype=f32, device=dev)

    def set_boundary(tt):
        stage = boundary_stage_fn(tt) if boundary_stage_fn is not None else float(stage_m)
        if np.ndim(stage):
            hb.copy_(torch.as_tensor(np.maximum(np.asarray(stage, np.float32) - zb_np, np.float32(0.0)), device=dev))
        else:
            hb.copy_(torch.clamp(torch.tensor(float(stage), dtype=f32, device=dev) - zb, min=0.0))
        h.view(-1)[bidx] = hb

    set_boundary(0.0)
    qx = torch.zeros((ny, nx - 1), dtype=f32, device=dev)
    qy = torch.zeros((ny - 1, nx), dtype=f32, device=dev)
    nframes = int(round(duration_s / frame_interval_s)) + 1
    frames = np.full((nframes, ny, nx), NODATA_CM, dtype=np.uint16)
    peak = torch.zeros_like(h)
    peak_frame = torch.full((ny, nx), -1, dtype=torch.int16, device=dev)
    peak_speed = torch.zeros_like(h)
    tot = torch.zeros(3, dtype=torch.float64, device=dev)  # rain, infiltration, boundary_out (depth-equivalent sums)
    rain_m3 = 0.0
    if record_flow:
        flow_u = np.full((nframes, ny, nx), FLOW_NODATA, dtype=np.int16)
        flow_v = np.full((nframes, ny, nx), FLOW_NODATA, dtype=np.int16)
        flow_wse = np.full((nframes, ny, nx), FLOW_NODATA, dtype=np.int16)
    else:
        flow_u = flow_v = flow_wse = None
    n_act = float(act_np.sum())
    G32 = float(G)
    rain_cache = {}

    def face_flux(q, eta_a, eta_b, z_a, z_b, n2, ok, dt):
        hf = torch.maximum(eta_a, eta_b) - torch.maximum(z_a, z_b)
        wet = hf > 1e-4
        hf = torch.clamp(hf, min=1e-4)
        den = torch.abs(q) * n2 * (G32 * dt) / hf.pow(7.0 / 3.0) + 1.0
        q = (q - (eta_b - eta_a) * hf * (G32 * dt / dx)) / den
        return q * ok * wet

    def record(k):
        cm = torch.clamp(torch.round(h * 100.0), max=NODATA_CM - 1).to(torch.int32).cpu().numpy().astype(np.uint16)
        cm[~act_np] = NODATA_CM
        frames[k] = cm

    def cell_discharge():
        ux = torch.zeros_like(h)
        uy = torch.zeros_like(h)
        ux[:, :-1] += 0.5 * qx
        ux[:, 1:] += 0.5 * qx
        uy[:-1, :] += 0.5 * qy
        uy[1:, :] += 0.5 * qy
        return ux, uy

    def record_flow_frame(k, ux, uy):
        hn = h.cpu().numpy()
        uxn, uyn = ux.cpu().numpy(), uy.cpu().numpy()
        wet = act_np & (hn >= WET_THRESHOLD_M)
        hs = np.maximum(hn, np.float32(WET_THRESHOLD_M))
        u = np.where(wet, uxn / hs, np.float32(0.0))
        v = np.where(wet, -uyn / hs, np.float32(0.0))
        enc = lambda a: np.clip(np.round(a / FLOW_SCALE), -32767, 32767).astype(np.int16)  # noqa: E731
        fu, fv, fw = enc(u), enc(v), enc(z_np + hn)
        fu[~act_np] = FLOW_NODATA
        fv[~act_np] = FLOW_NODATA
        fw[~wet] = FLOW_NODATA
        flow_u[k], flow_v[k], flow_wse[k] = fu, fv, fw

    def update_peak(frame_index):
        nonlocal peak
        hn = h * actf
        changed = hn > peak
        peak_frame[changed] = frame_index
        peak = torch.maximum(peak, hn)

    record(0)
    if record_flow:
        record_flow_frame(0, torch.zeros_like(h), torch.zeros_like(h))
    t = 0.0
    next_frame = 1
    steps = 0
    min_dt = max_dt
    hmax = 0.0
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
        eta = z + h
        cap = h * p * (dx / (4.0 * dt))
        cap.view(-1)[bidx] = float("inf")
        qx = face_flux(qx, eta[:, :-1], eta[:, 1:], z[:, :-1], z[:, 1:], n2x, okx, dt)
        qx = torch.minimum(qx, cap[:, :-1])
        qx = torch.maximum(qx, -cap[:, 1:])
        qy = face_flux(qy, eta[:-1, :], eta[1:, :], z[:-1, :], z[1:, :], n2y, oky, dt)
        qy = torch.minimum(qy, cap[:-1, :])
        qy = torch.maximum(qy, -cap[1:, :])
        d = torch.zeros_like(h)
        d[:, :-1] += qx
        d[:, 1:] -= qx
        d[:-1, :] += qy
        d[1:, :] -= qy
        d = d * (dt / dx)
        vol = h * p
        k = int(t // rain_interval_s)
        if k < len(rain_np):
            if spatial:
                rf = rain_cache.get(k)
                if rf is None:
                    rain_cache.clear()
                    rf = rain_cache[k] = torch.as_tensor(rain_np[k] * np.float32(1.0 / 1000.0 / rain_interval_s), dtype=f32, device=dev)
                rd = rf * dt * actf
                vol = vol + rd
                tot[0] += rd.sum(dtype=torch.float64)
            else:
                rs = float(rain_np[k]) / 1000.0 / rain_interval_s
                if rs:
                    vol = vol + float(np.float32(rs * dt)) * actf
                    rain_m3 += rs * dt * n_act * area
        if has_src:
            vol = vol + src * dt
        infil_d = torch.minimum(vol, infil * dt)
        vol = vol - infil_d - d
        tot[1] += infil_d.sum(dtype=torch.float64)
        tot[2] += d[bmask].sum(dtype=torch.float64)
        h = torch.clamp(vol, min=0.0) / p * actf
        h.view(-1)[bidx] = hb
        hmax = float((h * actf).max())  # CFL depth over active cells only, as in the NumPy reference
        t += dt
        steps += 1
        if steps % 10 == 0:
            update_peak(min(next_frame, nframes - 1))
        if next_frame < nframes and t >= next_frame * frame_interval_s - 1e-6:
            update_peak(next_frame)
            ux, uy = cell_discharge()
            speed = torch.hypot(ux, uy) / torch.clamp(h, min=0.01)
            speed = torch.where(h <= 0.01, torch.zeros_like(speed), speed)
            peak_speed = torch.maximum(peak_speed, speed * actf)
            record(next_frame)
            if record_flow:
                record_flow_frame(next_frame, ux, uy)
            next_frame += 1
            if progress:
                progress(t / duration_s)
        if steps > 5_000_000:
            raise RuntimeError("exceeded 5,000,000 steps")
    update_peak(nframes - 1)
    tot_np = tot.cpu().numpy()
    totals = {"rain_m3": (rain_m3 + float(tot_np[0]) * area), "inflow_m3": inflow_m3s * duration_s if has_src else 0.0,
              "infiltration_m3": float(tot_np[1]) * area, "boundary_net_out_m3": -float(tot_np[2]) * area}
    hn = h.cpu().numpy()
    storage = float(np.sum(hn[act_np].astype(np.float64) * p_np[act_np]) * area)
    inputs = totals["rain_m3"] + totals["inflow_m3"]
    residual = inputs - totals["infiltration_m3"] - totals["boundary_net_out_m3"] - storage
    peak_np = peak.cpu().numpy()
    pf = peak_frame.cpu().numpy()
    pf[peak_np <= 0] = -1
    diag = {**totals, "final_storage_m3": storage, "steps": steps, "min_dt_s": min_dt, "threads": 0,
            "mass_balance_relative_error": abs(residual) / max(inputs, 1e-9), "inflow_m3s": inflow_m3s,
            "device": str(dev), "peak_vram_mb": round(torch.cuda.max_memory_allocated(dev) / 2**20, 1) if dev.type == "cuda" else None}
    return HiresResult(frames, [int(round(k * frame_interval_s / 60)) for k in range(nframes)],
                       np.where(act_np, peak_np, np.nan).astype(np.float32), pf,
                       np.where(act_np, peak_speed.cpu().numpy(), np.nan).astype(np.float32), diag, flow_u, flow_v, flow_wse)
