"""A27: per-frame u, v and water-surface elevation sidecar and FlowFrame readers."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, Path(__file__).resolve().parent):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from services.flood_engine import hires, products, scenario  # noqa: E402
from test_a25 import NX, NY, _grid, static_root  # noqa: E402,F401  (fixture re-export)


def _decode(a):
    return np.where(a == hires.FLOW_NODATA, np.nan, a.astype(np.float64) * hires.FLOW_SCALE)


def _plane(slope_x=0.0, slope_y=0.0, n=16):
    rows, cols = np.indices((n, n))
    z = (10.0 - slope_x * cols * 30.0 - slope_y * rows * 30.0).astype(np.float32)
    act = np.ones((n, n), bool)
    act[0, 0] = False
    return hires.HiresGrid(z, act, np.zeros((n, n), bool), np.full((n, n), 0.03), np.ones((n, n)), np.zeros((n, n)), 30.0)


def test_existing_outputs_bit_identical_with_and_without_flow():
    g = _grid()
    a = hires.run(g, [40.0, 60.0, 5.0], 3600, 4 * 3600, 1800, record_flow=False)
    b = hires.run(g, [40.0, 60.0, 5.0], 3600, 4 * 3600, 1800, record_flow=True)
    assert a.flow_u is None and b.flow_u.shape == b.frames_cm.shape and b.flow_u.dtype == np.int16
    np.testing.assert_array_equal(a.frames_cm, b.frames_cm)
    np.testing.assert_array_equal(a.peak_m, b.peak_m)
    np.testing.assert_array_equal(a.peak_frame, b.peak_frame)
    np.testing.assert_array_equal(a.peak_speed_mps, b.peak_speed_mps)
    assert a.diagnostics == b.diagnostics


def test_sign_convention_east_and_north():
    east = hires.run(_plane(slope_x=0.01), [80.0], 3600, 3600, 1800)
    u, v = _decode(east.flow_u[-1]), _decode(east.flow_v[-1])
    wet = np.isfinite(u) & (np.abs(u) > 0)
    assert np.nanmean(u[wet]) > 0.01 and abs(np.nanmean(v[wet])) < 0.2 * np.nanmean(u[wet])  # downhill to +x (east)
    south = hires.run(_plane(slope_y=0.01), [80.0], 3600, 3600, 1800)  # bed falls with row index = to the south
    v = _decode(south.flow_v[-1])
    assert np.nanmean(v[np.isfinite(v) & (v != 0)]) < -0.01  # southward flow is negative v (v is northward +y)


def test_round_trip_wse_speed_dry_and_nodata():
    g = _grid()
    r = hires.run(g, [40.0, 60.0, 5.0], 3600, 4 * 3600, 1800)
    depth = np.where(r.frames_cm == hires.NODATA_CM, np.nan, r.frames_cm / 100.0)
    wse = _decode(r.flow_wse)
    u, v = _decode(r.flow_u), _decode(r.flow_v)
    wet = np.isfinite(depth) & (depth >= hires.WET_THRESHOLD_M + 0.005)  # cm rounding of the depth frame
    expected = g.z[None].astype(np.float64) + depth
    assert np.nanmax(np.abs(wse[wet] - expected[wet])) <= 0.011  # 0.01 m encoding + cm depth rounding
    dry = np.isfinite(depth) & (depth < 0.005)
    assert np.isnan(wse[dry]).all() and (u[dry] == 0).all() and (v[dry] == 0).all()
    outside = ~g.active
    assert np.isnan(u[:, outside]).all() and np.isnan(v[:, outside]).all() and np.isnan(wse[:, outside]).all()
    assert np.isnan(u[0][g.active]).sum() == 0 and (u[0][g.active] == 0).all()  # frame 0: still water
    # speed from the sidecar equals the solver's |q|/h peak speed (same cell-centred discharge) within encoding
    speed = np.nanmax(np.hypot(u, v), axis=0)
    ok = g.active & (np.nanmax(depth, axis=0) > 0.05)
    assert np.allclose(speed[ok], r.peak_speed_mps[ok], atol=0.015)


def test_products_flow_frame_stride_and_unavailable(static_root, tmp_path):
    runs = tmp_path / "runs"
    doc = scenario.run_scenario(static_root, runs, mode="event", event_key="2015-12-01", duration_hours=6)
    assert doc["flow"]["file"] == "flow.npz" and doc["flow"]["wet_threshold_m"] == 0.01 and "EGM2008" in doc["flow"]["wse_vertical_datum"]
    rid = doc["run_id"]
    f = products.flow_frame(runs, rid, 6)
    assert f["source_mode"] == "SIMULATED" and f["units"] == {"u": "m/s", "v": "m/s", "wse": "m"}
    assert f["rows"] == NY and f["cols"] == NX and f["grid"] == doc["grid"] and f["valid_time_utc"] == doc["frames"][6]["valid_time_utc"]
    assert f["u"][0][-1] is None and f["wse"][0][-1] is None  # sea boundary column is outside the computed domain
    assert all(x is None or abs(x) < 50 for row in f["u"] for x in row)
    assert f["speed_max_mps"] is None or f["speed_max_mps"] >= 0
    s2 = products.flow_frame(runs, rid, 6, stride=2)
    assert s2["rows"] == (NY + 1) // 2 and s2["cols"] == (NX + 1) // 2 and s2["stride"] == 2
    assert s2["grid"]["cell_size_m"] == 2 * doc["grid"]["cell_size_m"] and s2["grid"]["rows"] == s2["rows"]
    # centre of subsampled cell (0,0) coincides with the centre of original cell (0,0)
    g, g2 = doc["grid"], s2["grid"]
    assert g2["origin_x_m"] + g2["cell_size_m"] / 2 == pytest.approx(g["origin_x_m"] + g["cell_size_m"] / 2)
    assert g2["origin_y_m"] - g2["cell_size_m"] / 2 == pytest.approx(g["origin_y_m"] - g["cell_size_m"] / 2)
    assert s2["u"][1][1] == f["u"][2][2] and s2["wse"][1][1] == f["wse"][2][2]
    assert products.velocity_frame(runs, rid, 6)["u"] == f["u"] and products.wse_frame(runs, rid, 6)["wse"] == f["wse"]
    with pytest.raises(ValueError):
        products.flow_frame(runs, rid, 999)
    with pytest.raises(ValueError):
        products.flow_frame(runs, rid, 1, stride=9)
    # a run computed before A27 (no sidecar) stays readable for depth but reports flow as unavailable
    old = runs / "evt-20000101T000000Z-00000000"
    shutil.copytree(runs / rid, old)
    (old / "flow.npz").unlink()
    run_json = (old / "run.json").read_text(encoding="utf-8").replace(rid, old.name)
    (old / "run.json").write_text(run_json, encoding="utf-8")
    assert products.depth_frame(runs, old.name, 3)["rows"] == NY
    with pytest.raises(products.FlowUnavailable):
        products.flow_frame(runs, old.name, 3)


def test_sidecar_wse_offset_decodes_to_bed_plus_depth(static_root, tmp_path):
    runs = tmp_path / "runs"
    doc = scenario.run_scenario(static_root, runs, mode="event", event_key="2015-12-01", duration_hours=6)
    rid = doc["run_id"]
    bundle = scenario.StaticBundle(static_root, doc["provenance"]["static_bundle"])
    with np.load(runs / rid / "frames.npz") as b:
        depth = np.where(b["depth_cm"][6] == hires.NODATA_CM, np.nan, b["depth_cm"][6] / 100.0)
    w = np.array([[np.nan if x is None else x for x in row] for row in products.wse_frame(runs, rid, 6)["wse"]])
    wet = np.isfinite(depth) & (depth >= 0.015)
    assert np.nanmax(np.abs(w[wet] - (bundle.a["z"][wet] + depth[wet]))) <= 0.021
    assert np.isnan(w[np.isfinite(depth) & (depth < 0.005)]).all()
    assert doc["provenance"]["engine_version"] == "twinguard-flood-engine/2.1.0"
