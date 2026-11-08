"""A26 optional CUDA backend: device selection, CPU fallback, and CPU/GPU parity (GPU tests skip without CUDA)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, Path(__file__).resolve().parent):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from services.flood_engine import hires, hires_torch, products, scenario  # noqa: E402
from test_a25 import _grid, static_root  # noqa: E402,F401

CUDA, CUDA_INFO = hires_torch.available()
needs_cuda = pytest.mark.skipif(not CUDA, reason=f"CUDA unavailable: {CUDA_INFO}")
DEPTH_TOL_M = 0.01      # max abs depth difference per saved frame (frames are stored in cm)
PEAK_TOL_M = 0.005


def _depth(frames):
    return np.where(frames == hires.NODATA_CM, np.nan, frames / 100.0)


def test_resolve_device_and_unsupported_values():
    assert scenario.resolve_device("cpu") == ("cpu", None, None)
    assert scenario.resolve_device(None) == ("cpu", None, None)
    used, _, reason = scenario.resolve_device("tpu")
    assert used == "cpu" and "unsupported" in reason


def test_cuda_unavailable_falls_back_to_cpu(static_root, tmp_path, monkeypatch):
    monkeypatch.setattr(hires_torch, "available", lambda: (False, "torch.cuda.is_available() is False"))
    doc = scenario.run_scenario(static_root, tmp_path / "runs", mode="event", event_key="2015-12-01", duration_hours=6, device="cuda")
    dev = doc["provenance"]["device"]
    assert dev["requested"] == "cuda" and dev["used"] == "cpu" and "is_available" in dev["fallback_reason"]


def test_cuda_error_falls_back_and_matches_cpu(static_root, tmp_path, monkeypatch):
    cpu = scenario.run_scenario(static_root, tmp_path / "a", mode="event", event_key="2015-12-01", duration_hours=6)
    monkeypatch.setattr(hires_torch, "available", lambda: (True, "Fake GPU"))

    def boom(*a, **k):
        raise RuntimeError("CUDA out of memory. Tried to allocate 2.00 GiB")
    monkeypatch.setattr(hires_torch, "run", boom)
    doc = scenario.run_scenario(static_root, tmp_path / "b", mode="event", event_key="2015-12-01", duration_hours=6, device="cuda")
    dev = doc["provenance"]["device"]
    assert dev["used"] == "cpu" and "out of memory" in dev["fallback_reason"] and dev["name"] == "cpu (NumPy)"
    assert doc["summary"] == cpu["summary"]
    with np.load(tmp_path / "a" / cpu["run_id"] / "frames.npz") as x, np.load(tmp_path / "b" / doc["run_id"] / "frames.npz") as y:
        np.testing.assert_array_equal(x["depth_cm"], y["depth_cm"])


@needs_cuda
def test_gpu_solver_parity_and_mass_balance():
    g = _grid()
    a = hires.run(g, [40.0, 60.0, 5.0], 3600, 4 * 3600, 1800, inflows=[(6, 1, 20.0)], stage_m=0.3)
    b = hires_torch.run(g, [40.0, 60.0, 5.0], 3600, 4 * 3600, 1800, inflows=[(6, 1, 20.0)], stage_m=0.3)
    assert np.nanmax(np.abs(_depth(a.frames_cm) - _depth(b.frames_cm))) <= DEPTH_TOL_M
    assert np.nanmax(np.abs(a.peak_m - b.peak_m)) <= PEAK_TOL_M
    assert a.diagnostics["mass_balance_relative_error"] <= 0.01 and b.diagnostics["mass_balance_relative_error"] <= 0.01
    assert abs(a.diagnostics["steps"] - b.diagnostics["steps"]) <= max(2, 0.01 * a.diagnostics["steps"])
    assert np.abs(a.flow_u.astype(int) - b.flow_u.astype(int)).max() <= 5  # 0.05 m/s
    assert b.diagnostics["device"].startswith("cuda") and b.diagnostics["peak_vram_mb"] is not None
    spatial = np.broadcast_to(np.array([40.0, 60.0, 5.0])[:, None, None], (3,) + g.z.shape)
    c = hires_torch.run(g, spatial, 3600, 3 * 3600, 1800)
    d = hires.run(g, spatial, 3600, 3 * 3600, 1800)
    assert np.nanmax(np.abs(c.peak_m - d.peak_m)) <= PEAK_TOL_M


@needs_cuda
def test_gpu_scenario_parity_including_nested_focus(static_root, tmp_path):
    cpu = scenario.run_scenario(static_root, tmp_path / "cpu", mode="event", event_key="2015-12-01", duration_hours=6, members=3)
    gpu = scenario.run_scenario(static_root, tmp_path / "gpu", mode="event", event_key="2015-12-01", duration_hours=6, members=3, device="cuda")
    dev = gpu["provenance"]["device"]
    assert dev["used"].startswith("cuda") and dev["fallback_reason"] is None and dev["peak_vram_mb"] is not None
    assert all(m["mass_balance_relative_error"] <= 0.01 for m in gpu["diagnostics"].values())
    for layer in ("depth_mean", "depth_p05", "depth_p95"):
        a = np.array(products.depth_frame(tmp_path / "cpu", cpu["run_id"], layer=layer)["values"], dtype=float)
        b = np.array(products.depth_frame(tmp_path / "gpu", gpu["run_id"], layer=layer)["values"], dtype=float)
        assert np.nanmax(np.abs(a - b)) <= PEAK_TOL_M + 0.01  # values rounded to 0.01 m
    fc = scenario.run_scenario(static_root, tmp_path / "cpu", mode="event", event_key="2015-12-01", duration_hours=6, resolution="focus", focus_area="VELACHERY")
    fg = scenario.run_scenario(static_root, tmp_path / "gpu", mode="event", event_key="2015-12-01", duration_hours=6, resolution="focus", focus_area="VELACHERY", device="cuda")
    a = np.array(products.depth_frame(tmp_path / "cpu", fc["run_id"])["values"], dtype=float)
    b = np.array(products.depth_frame(tmp_path / "gpu", fg["run_id"])["values"], dtype=float)
    assert np.nanmax(np.abs(a - b)) <= PEAK_TOL_M + 0.01
    assert products.flow_frame(tmp_path / "gpu", fg["run_id"], 6)["rows"] == 24


def test_savez_fast_round_trip_and_timing_block(static_root, tmp_path):
    arrays = {"a": np.arange(1000, dtype=np.uint16).reshape(10, 100), "b": np.full((3, 4), -32768, np.int16), "c": np.float32(0.01)}
    scenario.savez_fast(tmp_path / "x.npz", **arrays)
    with np.load(tmp_path / "x.npz", allow_pickle=False) as z:
        for k, v in arrays.items():
            np.testing.assert_array_equal(z[k], v)
            assert z[k].dtype == np.asarray(v).dtype
    doc = scenario.run_scenario(static_root, tmp_path / "runs", mode="event", event_key="2015-12-01", duration_hours=6)
    t = doc["timing"]
    assert {"forcing_and_setup_s", "device_init_s", "solve_s", "post_processing_s"} <= set(t) and t["solve_s"] >= 0


@needs_cuda
def test_warmup_is_paid_once():
    hires_torch.warmup("cuda:0")
    again = hires_torch.warmup("cuda:0")
    assert again == {"torch_import_s": 0.0, "cuda_context_s": 0.0}
