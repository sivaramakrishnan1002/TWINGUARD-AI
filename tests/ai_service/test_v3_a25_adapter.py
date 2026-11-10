"""B47: C4 v3 switches to Lane A's A25 engine when its bundle is installed (stubbed run_scenario, synthetic bundle)."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "ai-service"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v3_support import COLS, ROWS, assert_contract, build_fixture, custom_request  # noqa: E402

from app import main  # noqa: E402
from app.v3 import config, static  # noqa: E402
from app.v3.runs import MANAGER  # noqa: E402
from services.flood_engine import scenario  # noqa: E402

RUN = "/v3/simulations/{run_id}"


def _a25_bundle(root: Path, grid_dir: Path) -> Path:
    a25 = root / "a25"
    city = a25 / "citywide_120m"
    shared = a25 / "shared"
    city.mkdir(parents=True)
    shared.mkdir()
    with np.load(grid_dir / "static.npz") as z:
        arrays = {k: z[k] for k in z.files}
    n = ROWS * COLS
    ward = np.where(np.arange(n).reshape(ROWS, COLS) % COLS < COLS // 2, 1, 2).astype(np.int16)
    arrays.update(boundary=arrays["drain"], ward_id=ward, infiltration_mm_h=np.ones((ROWS, COLS), np.float32),
                  building_cell=np.where(arrays["active"].ravel(), np.arange(n), -1).astype(np.int32),
                  shelter_cell=np.array([1 * COLS + 1, 5 * COLS + 5, 8 * COLS + 9], np.int32))
    with np.load(root / "product" / "roads.npz") as z:
        arrays["road_cell"] = z["seg_cell"]
    np.savez_compressed(city / "static.npz", **arrays)
    grid = {"crs": "EPSG:32644", "origin_x_m": 390000.0, "origin_y_m": 1471620.0, "cell_size_m": 600, "rows": ROWS, "cols": COLS,
            "bbox_wgs84": [80.2, 12.995, 80.266, 13.05]}
    (city / "meta.json").write_text(json.dumps({"grid": grid, "static_assets_version": "a25_static_v1"}), encoding="utf-8")
    np.savez_compressed(shared / "shelters.npz", shelter_id=np.array(["osm:1", "osm:2", "osm:3"]))
    wards = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": None, "properties": {"ward_id": 1, "ward_name": "Ward 1", "zone": "I Test"}},
        {"type": "Feature", "geometry": None, "properties": {"ward_id": 2, "ward_name": "Ward 2", "zone": "II Test"}}]}
    (shared / "wards.geojson").write_text(json.dumps(wards), encoding="utf-8")
    (shared / "events.json").write_text(json.dumps({"events": [{"event_key": "2015-12-01", "label": "Dec 2015", "start_utc": "2015-11-30T00:00:00Z",
                                                                  "end_utc": "2015-12-03T00:00:00Z", "rainfall_source": "IMERG", "source_mode": "REPLAY",
                                                                  "interval_minutes": 60, "values_mm": [5.0] * 72}]}), encoding="utf-8")
    (a25 / "manifest.json").write_text(json.dumps({"version": "a25_static_v1"}), encoding="utf-8")
    return a25


def fake_run_scenario(calls):
    def run(static_root, runs_root, *, mode, what_if=None, duration_hours=24, frame_interval_minutes=30, progress=None, **kw):
        calls.append({"mode": mode, "what_if": what_if, **kw})
        frames = duration_hours * 60 // frame_interval_minutes
        run_id = f"{'whatif' if mode == 'what_if' else 'sim'}-20261107T000000Z-{len(calls):08x}"
        out = Path(runs_root) / run_id
        out.mkdir(parents=True)
        scale = 2 if what_if else 1
        depth = np.linspace(0, 0.6 * scale, frames)[:, None, None] * np.ones((frames, ROWS, COLS))
        cm = np.round(depth * 100).astype(np.uint16)
        cm[:, :, -1] = 65535
        np.savez_compressed(out / "frames.npz", depth_cm=cm)
        np.savez_compressed(out / "peak.npz", velocity_mps=np.full((ROWS, COLS), 0.4, np.float32))
        if progress:
            progress(100.0)
        doc = {"run_id": run_id, "grid": json.loads((Path(static_root) / "citywide_120m/meta.json").read_text())["grid"],
               "frames": [{"index": k, "valid_time_utc": f"2026-11-07T{(k + 1) // 2:02d}:{30 * ((k + 1) % 2):02d}:00Z",
                           "elapsed_minutes": (k + 1) * frame_interval_minutes} for k in range(frames)],
               "provenance": {"engine_version": "twinguard-flood-engine/2.1.0", "forcing_sha256": "c" * 64,
                              "inputs": [{"name": "rainfall", "source": "user", "source_mode": "SCENARIO_INPUT", "fetched_at": None, "sha256": None}]},
               "flow": {"file": "flow.npz", "wse_vertical_datum": "EGM2008"}}
        # A27 flow sidecar in Lane A's encoding: int16 x 0.01, wse relative to a per-cell offset, -32768 = NoData.
        nodata = -32768
        u = np.full((frames, ROWS, COLS), 25, np.int16)       # 0.25 m/s east
        v = np.full((frames, ROWS, COLS), -10, np.int16)      # 0.10 m/s south
        wse = np.full((frames, ROWS, COLS), 50, np.int16)     # +0.50 m above the offset
        offset = np.full((ROWS, COLS), 600, np.int16)         # 6.00 m
        for arr in (u, v, wse):
            arr[:, :, -1] = nodata                            # drain column: outside the land domain
        wse[0] = nodata                                       # first frame dry: wse null
        u[0] = 0
        v[0] = 0
        u[0, :, -1] = v[0, :, -1] = nodata
        np.savez_compressed(out / "flow.npz", u=u, v=v, wse=wse, wse_offset_cm=offset, scale=np.float32(0.01),
                            nodata=np.int16(nodata), wet_threshold_m=np.float32(0.01))
        (out / "run.json").write_text(json.dumps(doc), encoding="utf-8")
        return doc
    return run


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    root = tmp_path_factory.mktemp("v3a25")
    grid_dir, product_dir = build_fixture(root)
    a25 = _a25_bundle(root, grid_dir)
    mp = pytest.MonkeyPatch()
    for key, value in {"TWINGUARD_LIVE_STATIC": str(grid_dir), "TWINGUARD_V3_PRODUCT_STATIC": str(product_dir),
                       "TWINGUARD_V3_RUNS": str(root / "runs"), "TWINGUARD_V3_INLINE_WORKER": "1",
                       "TWINGUARD_V3_RUN_MIN_INTERVAL_S": "0", "TWINGUARD_V3_A25_STATIC": str(a25)}.items():
        mp.setenv(key, value)
    calls = []
    mp.setattr(scenario, "run_scenario", fake_run_scenario(calls))
    static.clear_cache()
    yield {"client": TestClient(main.app), "calls": calls, "mp": mp, "root": root}
    MANAGER.wait_idle(60)
    mp.undo()
    static.clear_cache()
    shutil.rmtree(root, ignore_errors=True)


def test_a25_engine_is_selected_and_served(env):
    client = env["client"]
    assert config.a25_enabled()
    status = assert_contract(client.get("/v3/status"), "/v3/status")
    assert "A25" in status["engine_version"]
    assert [e["event_key"] for e in client.get("/v3/events").json()["events"]] == ["2015-12-01"]
    accepted = client.post("/v3/simulations", json=custom_request()).json()
    assert MANAGER.wait_idle(60)
    run = assert_contract(client.get(RUN.format(run_id=accepted["run_id"])), RUN)
    assert run["state"] == "completed" and env["calls"][-1]["members"] == 1 and env["calls"][-1]["citywide_cell_m"] == 120
    assert run["summary"]["wards_affected"] == 2 and "A25" in run["provenance"]["engine_version"]
    assert run["limitations"][0].startswith("A25 local-inertial model on a 600 m citywide grid")  # fixture grid is 600 m
    assert not any("A06" in note for note in run["limitations"]) and len(run["limitations"]) <= 5
    depth = assert_contract(client.get(RUN.format(run_id=run["run_id"]) + "/depth?frame_index=11"), RUN + "/depth")
    assert depth["values"][0][0] == 0.6 and depth["values"][0][-1] is None
    assert client.get(RUN.format(run_id=run["run_id"]) + "/depth?layer=velocity_mps").json()["max_value"] == 0.4
    assert client.get(RUN.format(run_id=run["run_id"]) + "/depth?layer=velocity_mps&frame_index=2").status_code == 422
    assert client.get(RUN.format(run_id=run["run_id"]) + "/depth?layer=depth_p95").status_code == 422  # members=1
    wards = assert_contract(client.get(RUN.format(run_id=run["run_id"]) + "/wards"), RUN + "/wards")["wards"]
    assert {w["ward_id"] for w in wards} == {1, 2} and wards[0]["risk_level"] in ("high", "severe")
    buildings = client.get(RUN.format(run_id=run["run_id"]) + "/buildings?limit=3").json()["buildings"]
    assert buildings[0]["ward_id"] == 1
    assert client.get("/v3/static/wards").json()["features"][0]["properties"]["ward_id"] == 1
    overview = assert_contract(client.get("/v3/overview"), "/v3/overview")
    assert overview["top_wards"]
    env["state"] = run["run_id"]


def test_a25_what_if_uses_engine_run_id_and_guard(env, monkeypatch):
    client = env["client"]
    base = env["state"]
    accepted = client.post("/v3/simulations", json={"mode": "what_if", "what_if": {"base_run_id": base, "rainfall_scale_pct": 200}}).json()
    assert MANAGER.wait_idle(60)
    assert env["calls"][-1]["what_if"]["base_run_id"].startswith("sim-20261107T000000Z-")
    comparison = assert_contract(client.get(RUN.format(run_id=accepted["run_id"]) + "/comparison"), RUN + "/comparison")
    assert comparison["delta"]["max_depth_m"] > 0 and comparison["ward_changes"]
    monkeypatch.setenv("TWINGUARD_V3_ENGINE", "a06")  # base computed by A25 cannot seed an A06 what-if
    response = client.post("/v3/simulations", json={"mode": "what_if", "what_if": {"base_run_id": base, "rainfall_scale_pct": 50}})
    assert response.status_code == 409


# ------------------------------------------------------------------------------------------------- OD-2026-11-08 GPU
def test_device_resolution_cpu_default_and_cuda_when_available(monkeypatch):
    from app.v3 import device

    monkeypatch.setenv("TWINGUARD_V3_DEVICE", "cpu")
    assert device.resolve(True)["used"] == "cpu"
    monkeypatch.setenv("TWINGUARD_V3_DEVICE", "auto")
    monkeypatch.setattr(device, "probe", lambda refresh=False: {"cuda_available": True, "name": "Test GPU", "backend": "torch"})
    assert device.resolve(True) == {"requested": "auto", "used": "cuda", "name": "Test GPU", "reason": None}
    assert device.resolve(False)["used"] == "cpu"  # engine without a GPU backend
    monkeypatch.setattr(device, "probe", lambda refresh=False: {"cuda_available": False, "name": None, "backend": None})
    assert device.resolve(True)["used"] == "cpu"
    monkeypatch.setenv("TWINGUARD_V3_DEVICE", "cuda")
    assert device.resolve(True)["reason"] == "CUDA not available"


def test_cuda_failure_falls_back_to_cpu_and_is_reported(env, monkeypatch):
    from app.v3 import device

    devices = []
    inner = fake_run_scenario(env["calls"])

    def gpu_engine(static_root, runs_root, *, device="cpu", **kw):
        devices.append(device)
        if device == "cuda":
            raise RuntimeError("CUDA out of memory")
        return inner(static_root, runs_root, **kw)

    monkeypatch.setattr(scenario, "run_scenario", gpu_engine)
    monkeypatch.setenv("TWINGUARD_V3_DEVICE", "auto")
    monkeypatch.setattr(device, "probe", lambda refresh=False: {"cuda_available": True, "name": "Test GPU", "backend": "torch"})
    client = env["client"]
    status = assert_contract(client.get("/v3/status"), "/v3/status")
    assert status["device"] == {"requested": "auto", "resolved": "cuda", "name": "Test GPU", "cuda_available": True, "gpu_jobs_max": 1}
    accepted = client.post("/v3/simulations", json=custom_request([7.0, 7.0])).json()
    assert MANAGER.wait_idle(60)
    run = assert_contract(client.get(RUN.format(run_id=accepted["run_id"])), RUN)
    assert run["state"] == "completed" and devices == ["cuda", "cpu"]
    assert run["provenance"]["device"] == {"used": "cpu", "name": None, "fallback_reason": "CUDA run failed (RuntimeError); rerun on CPU"}


# ------------------------------------------------------------------------------------------------- B49 flow
def test_flow_frame_from_a27_sidecar(env):
    client = env["client"]
    run_id = run_and_wait_a25(client, custom_request([4.0, 4.0, 4.0]))
    url = RUN.format(run_id=run_id) + "/flow"
    response = client.get(url + "?frame_index=3", headers={"accept-encoding": "gzip"})
    assert response.status_code == 200 and response.headers["content-encoding"] == "gzip"
    body = assert_contract(response, RUN + "/flow")
    assert body["run_id"] == run_id and body["source_mode"] == "SIMULATED" and body["wse_vertical_datum"] == "EGM2008"
    assert body["u"][0][0] == 0.25 and body["v"][0][0] == -0.1 and body["wse"][0][0] == 6.5
    assert body["u"][0][-1] is None and body["wse"][0][-1] is None
    assert body["speed_max_mps"] == 0.27 and body["rows"] == ROWS and body["cols"] == COLS
    dry = client.get(url + "?frame_index=0").json()
    assert dry["u"][0][0] == 0 and dry["wse"][0][0] is None  # dry: u = v = 0, wse null
    for stride in (2, 4, 8):  # strided lattices validate now that GridSpec.cell_size_m is any positive number
        coarse = assert_contract(client.get(url + f"?frame_index=3&stride={stride}"), RUN + "/flow")
        assert coarse["stride"] == stride and coarse["grid"]["cell_size_m"] == 600 * stride
        assert coarse["rows"] == -(-ROWS // stride) and coarse["cols"] == -(-COLS // stride)
    for query in ("", "?frame_index=99", "?frame_index=1&stride=9", "?frame_index=1&stride=0", "?frame_index=-1"):
        bad = client.get(url + query)
        assert bad.status_code == 422, query
        assert_contract(bad, RUN + "/flow")
    missing = client.get(RUN.format(run_id="evt-20260101T000000Z-deadbeef") + "/flow?frame_index=0")
    assert missing.status_code == 404
    assert_contract(missing, RUN + "/flow")
    engine_dir = Path(config.runs_dir()) / "_a25" / MANAGER.get(run_id)["_engine_run_id"]
    renamed = engine_dir.with_name(engine_dir.name + ".moved")
    engine_dir.rename(renamed)  # engine output gone -> products.NotFound -> 404
    try:
        gone = client.get(url + "?frame_index=1")
        assert gone.status_code == 404
        assert_contract(gone, RUN + "/flow")
    finally:
        renamed.rename(engine_dir)


def test_flow_unavailable_for_runs_without_sidecar(env):
    client = env["client"]
    run_id = run_and_wait_a25(client, custom_request([2.0, 2.0]))
    engine_run = MANAGER.get(run_id)["_engine_run_id"]
    (Path(config.runs_dir()) / "_a25" / engine_run / "flow.npz").unlink()  # as a pre-A27 (2.0.0) run
    response = client.get(RUN.format(run_id=run_id) + "/flow?frame_index=0")
    assert response.status_code == 503 and "no flow output" in response.json()["detail"]
    assert_contract(response, RUN + "/flow")


def run_and_wait_a25(client, body) -> str:
    accepted = client.post("/v3/simulations", json=body)
    assert accepted.status_code == 202, accepted.text
    assert MANAGER.wait_idle(60)
    run = client.get(RUN.format(run_id=accepted.json()["run_id"])).json()
    assert run["state"] == "completed", run.get("error")
    return run["run_id"]


def test_engine_device_report_is_normalised(env, monkeypatch):
    """A26 reports "cuda:0" and its own NumPy fallback; /v3 exposes the C4 v3 enum cuda|cpu."""
    from app.v3 import device

    inner = fake_run_scenario(env["calls"])
    reports = iter([{"used": "cuda:0", "name": "Test GPU", "fallback_reason": None},
                    {"used": "cpu", "name": "cpu (NumPy)", "fallback_reason": "CUDA error: out of memory; ran on NumPy"}])

    def a26_engine(static_root, runs_root, *, device="cpu", **kw):
        doc = inner(static_root, runs_root, **kw)
        doc["provenance"]["device"] = {"requested": device, **next(reports)}
        return doc

    monkeypatch.setattr(scenario, "run_scenario", a26_engine)
    monkeypatch.setattr(device, "probe", lambda refresh=False: {"cuda_available": True, "name": "Test GPU", "backend": "torch"})
    client = env["client"]
    gpu = client.get(RUN.format(run_id=run_and_wait_a25(client, custom_request([9.0, 1.0])))).json()
    assert gpu["provenance"]["device"] == {"used": "cuda", "name": "Test GPU", "fallback_reason": None}
    cpu = client.get(RUN.format(run_id=run_and_wait_a25(client, custom_request([9.0, 2.0])))).json()
    assert cpu["provenance"]["device"] == {"used": "cpu", "name": None, "fallback_reason": "CUDA error: out of memory; ran on NumPy"}
    assert_contract(client.get(RUN.format(run_id=cpu["run_id"])), RUN)


# ------------------------------------------------------------------------------------------------- B51 live + A28
def test_live_cycle_passes_reservoir_snapshot_to_a28(env, monkeypatch):
    from datetime import datetime, timezone

    from test_v3_live import Clock, FakeOpenMeteo, FakeReservoir
    from app.v3 import live

    seen = {}
    inner = fake_run_scenario(env["calls"])

    def a28_engine(static_root, runs_root, *, mode, reservoir_snapshot=None, run_time=None, fetch_forecast=None, device="cpu", **kw):
        seen.update(mode=mode, reservoir=reservoir_snapshot, run_time=run_time, snapshot=fetch_forecast(None))
        doc = inner(static_root, runs_root, mode=mode, **kw)
        doc["reservoir_coupling"] = {"rule_id": "A28-RES-STORAGE-v1", "status": "applied", "releases_m3s": {"POONDI": 0.0}}
        doc["provenance"]["inputs"] += [
            {"name": "reservoir_snapshot", "source": "CFM-DSS public dashboard", "source_mode": "PUBLISHED_SNAPSHOT", "fetched_at": None},
            {"name": "reservoir_outlet_inflow", "source": "A28-RES-STORAGE-v1 (ASSUMPTION; not an observed release)",
             "source_mode": "SCENARIO_INPUT", "fetched_at": None}]
        return doc

    monkeypatch.setattr(scenario, "run_scenario", a28_engine)
    clock = Clock(datetime(2026, 11, 10, 6, 0, tzinfo=timezone.utc))
    sched = live.LiveScheduler(clock=clock, fetch_forecast=FakeOpenMeteo(clock), fetch_reservoir=FakeReservoir(clock),
                               forecast_calls=lambda b: 240)
    monkeypatch.setattr(live, "SCHEDULER", sched)
    monkeypatch.setenv("TWINGUARD_V3_LIVE", "1")
    run_id = sched.run_cycle("catch_up")
    assert run_id and seen["mode"] == "forecast" and seen["snapshot"].usable
    assert seen["reservoir"]["records"][0]["reservoir_id"] == "POONDI" and seen["run_time"].isoformat().startswith("2026-11-10T06:00")
    client = env["client"]
    run = assert_contract(client.get(RUN.format(run_id=run_id)), RUN)
    assert run["run_kind"] == "LIVE_FORECAST" and run["live"]["reservoir_coupling_rule"] == "A28-RES-STORAGE-v1 (applied)"
    latest = assert_contract(client.get("/v3/live/latest"), "/v3/live/latest")
    names = [i["name"] for i in latest["inputs"]]
    assert "reservoir_outlet_inflow" in names and "reservoirs" not in names  # engine's own reservoir inputs, no duplicate
    assert next(i for i in latest["inputs"] if i["name"] == "reservoir_outlet_inflow")["source_mode"] == "SCENARIO_INPUT"
