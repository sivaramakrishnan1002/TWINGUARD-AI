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
        return {"run_id": run_id, "grid": json.loads((Path(static_root) / "citywide_120m/meta.json").read_text())["grid"],
                "frames": [{"index": k, "valid_time_utc": f"2026-11-07T{(k + 1) // 2:02d}:{30 * ((k + 1) % 2):02d}:00Z",
                            "elapsed_minutes": (k + 1) * frame_interval_minutes} for k in range(frames)],
                "provenance": {"engine_version": "twinguard-flood-engine/2.0.0", "forcing_sha256": "c" * 64,
                               "inputs": [{"name": "rainfall", "source": "user", "source_mode": "SCENARIO_INPUT", "fetched_at": None, "sha256": None}]}}
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
