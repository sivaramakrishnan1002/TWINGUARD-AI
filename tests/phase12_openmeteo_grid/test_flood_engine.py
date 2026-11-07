"""A23 flood engine (live API is an unmounted draft handed over for change control): solver equivalence, forcing semantics, ensemble outputs, idempotency, API."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "services" / "ai-service"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from services.flood_engine import engine, forcing, solver  # noqa: E402

NY, NX = 8, 9


def _grid():
    rng = np.random.default_rng(7)
    z = 10 + rng.normal(0, 1.5, (NY, NX))
    z[3:5, 3:6] -= 4  # depression that ponds
    active = np.ones((NY, NX), bool)
    active[0, 0] = False
    drain = np.zeros((NY, NX), bool)
    drain[:, -1] = True
    active &= ~drain
    return z, active, drain


def _write_static(directory: Path) -> engine.StaticGrid:
    z, active, drain = _grid()
    lat = np.linspace(13.2, 12.9, NY)[:, None] * np.ones((1, NX))
    lon = np.linspace(80.05, 80.30, NX)[None, :] * np.ones((NY, 1))
    directory.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        directory / "static.npz", z=z, active=active, drain=drain, mann=np.full((NY, NX), 0.05), porosity=np.ones((NY, NX)),
        landcover=np.full((NY, NX), 50, np.int16), population=np.where(active, 100.0, np.nan), population_nodata_cells=np.zeros((NY, NX), np.int32),
        road_length_m=np.full((NY, NX), 1000.0), cell_lon=lon, cell_lat=lat,
        facility_cell=np.array([3 * NX + 4, 1 * NX + 1]), facility_group=np.array(["hospital", "candidate_shelter"]),
        facility_category=np.array(["hospital", "school"]), facility_name=np.array(["Low Hospital", "High School"]),
        facility_lon=np.array([80.17, 80.08]), facility_lat=np.array([13.03, 13.16]),
    )
    meta = {"grid": {"crs": "EPSG:32644", "corners_lonlat": [[80.0, 13.2], [80.3, 13.2], [80.3, 12.9], [80.0, 12.9]],
                     "bounds_lonlat": [80.05, 12.9, 80.30, 13.2], "transform": [600, 0, 0, 0, -600, 0]},
            "bundle_sha256": "0" * 64}
    (directory / "static_meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return engine.StaticGrid(directory)


def _payload(lat, lon, amounts, start="2026-11-06T06:00"):
    from datetime import datetime, timedelta
    t0 = datetime.fromisoformat(start)
    hours = forcing.PAST_HOURS + forcing.FORECAST_HOURS
    times = [(t0 + timedelta(hours=k)).strftime("%Y-%m-%dT%H:%M") for k in range(hours)]
    return [{"latitude": round(float(a), 2), "longitude": round(float(b), 2), "utc_offset_seconds": 0,
             "hourly_units": {"time": "iso8601", "precipitation": "mm"},
             "hourly": {"time": times, "precipitation": list(amounts(i, hours))}} for i, (a, b) in enumerate(zip(lat, lon))]


def _getter(amounts):
    def get(url, timeout):
        from urllib.parse import parse_qs, urlparse
        q = parse_qs(urlparse(url).query)
        lat = [float(v) for v in q["latitude"][0].split(",")]
        lon = [float(v) for v in q["longitude"][0].split(",")]
        return json.dumps(_payload(lat, lon, amounts)).encode()
    return get


def heavy(i, hours):
    return [0.0] * forcing.PAST_HOURS + [40.0 if 2 <= k < 8 else 0.0 for k in range(hours - forcing.PAST_HOURS)]


def test_solver_matches_a06_step_for_uniform_rain():
    a06 = pytest.importorskip("pipelines.phase12.simulate")
    z, active, drain = _grid()
    mann = np.full((NY, NX), 0.05)
    por = np.where(np.arange(NX)[None, :] % 2 == 0, 0.7, 1.0) * np.ones((NY, 1))
    inf = solver.infiltration_rate(np.full((NY, NX), 50, np.int16), 1.0)
    rain = np.array([0, 20, 35, 5, 0, 0])
    s1, d1, n1 = a06.simulate(z, active, drain, mann, por, inf, rain, 600)
    s2, d2, n2 = solver.simulate(z, active, drain, mann, por, inf, rain, 600)
    s3, d3, _ = solver.simulate(z, active, drain, mann, por, inf, np.broadcast_to(rain[:, None, None], (6, NY, NX)), 600)
    assert n1 == n2
    np.testing.assert_array_equal(s1, s2)
    np.testing.assert_array_equal(s1, s3)
    assert d2["mass_balance_relative_error"] == pytest.approx(d1["mass_balance_relative_error"], rel=1e-6) and d1["mass_balance_relative_error"] < 0.01
    assert abs(d3["mass_balance_relative_error"] - d1["mass_balance_relative_error"]) < 1e-12


def test_spatial_rain_only_wets_where_it_rains_and_conserves_mass():
    z, active, drain = _grid()
    rain = np.zeros((4, NY, NX))
    rain[:, :, :3] = 30.0
    states, diag, _ = solver.simulate(z, active, drain, np.full((NY, NX), 0.05), np.ones((NY, NX)), np.zeros((NY, NX)), rain)
    assert diag["mass_balance_relative_error"] < 0.01
    assert states[0][:, :3][active[:, :3]].mean() > states[0][:, 6:8][active[:, 6:8]].mean()
    bad = rain.copy()
    bad[1, 2, 2] = np.nan
    with pytest.raises(ValueError, match="missing"):
        solver.simulate(z, active, drain, np.full((NY, NX), 0.05), np.ones((NY, NX)), np.zeros((NY, NX)), bad)


def test_forcing_parser_fails_closed_and_maps_nearest_native_cell():
    lat = np.array([13.0, 13.0, 13.1])
    lon = np.array([80.1, 80.2, 80.1])
    ok = forcing.parse_model("m", "M", 9, "u", json.dumps(_payload(lat, lon, lambda i, h: [float(i)] * h)).encode(), lat, lon)
    assert ok.status == "ok" and ok.native_cells == 3
    mask = np.ones((2, 2), bool)
    grid = forcing.map_to_grid(ok, np.array([[13.09, 13.09], [13.01, 13.01]]), np.array([[80.11, 80.19], [80.11, 80.19]]), mask)
    assert grid.shape == (96, 2, 2)
    assert grid[0, 0, 0] == 2.0 and grid[0, 1, 0] == 0.0 and grid[0, 1, 1] == 1.0
    missing = _payload(lat, lon, lambda i, h: [None if (i == 1 and k == 5) else 1.0 for k in range(h)])
    excluded = forcing.parse_model("m", "M", 9, "u", json.dumps(missing).encode(), lat, lon)
    assert excluded.status == "excluded" and "not zero-filled" in excluded.reason
    gap = _payload(lat, lon, lambda i, h: [1.0] * h)
    for item in gap:
        item["hourly"]["time"][3] = item["hourly"]["time"][4]
    with pytest.raises(forcing.ForcingError, match="consecutive"):
        forcing.parse_model("m", "M", 9, "u", json.dumps(gap).encode(), lat, lon)
    wrong_unit = _payload(lat, lon, lambda i, h: [1.0] * h)
    wrong_unit[0]["hourly_units"]["precipitation"] = "inch"
    with pytest.raises(forcing.ForcingError, match="mm"):
        forcing.parse_model("m", "M", 9, "u", json.dumps(wrong_unit).encode(), lat, lon)


def test_one_failing_model_is_excluded_not_fabricated():
    def get(url, timeout):
        if "models=icon_global" in url:
            raise forcing.ForcingError("HTTP 500")
        return _getter(heavy)(url, timeout)
    snap = forcing.fetch_snapshot([80.05, 12.9, 80.3, 13.2], getter=get)
    status = {m.model: m.status for m in snap.models}
    assert status["icon_global"] == "excluded" and status["ecmwf_ifs"] == "ok"
    assert all(m.model != "icon_global" for m in snap.usable)


def test_live_engine_creates_versioned_run_and_is_idempotent(tmp_path):
    static = _write_static(tmp_path / "static")
    members = solver.parameter_members()[:2]
    fetch = lambda bounds: forcing.fetch_snapshot(bounds, getter=_getter(heavy))  # noqa: E731
    live = engine.LiveEngine(tmp_path / "static", tmp_path / "runs", fetcher=fetch, min_interval_s=0)
    original = engine.compute_run
    engine.compute_run = lambda s, snap: original(s, snap, members=members)
    try:
        first = live.run_once()
        second = live.run_once()
    finally:
        engine.compute_run = original
    assert first["outcome"] == "created"
    assert second["outcome"] == "unchanged" and second["run"]["run_id"] == first["run"]["run_id"]
    run = first["run"]
    assert run["source_mode"] == "LIVE" and run["status"] == "DERIVED_RESEARCH_OUTPUT"
    assert run["horizon"]["hours"] == forcing.FORECAST_HOURS and run["horizon"]["spin_up_hours"] == forcing.PAST_HOURS
    assert run["ensemble"]["members"] == 2 * len(forcing.MODELS)
    assert run["ensemble"]["max_mass_balance_relative_error"] <= 0.01
    assert run["exposure"]["0.15"]["population_people"]["p50"] > 0
    assert run["outlook"]["level"] in {"MINIMAL", "LOW", "MODERATE", "HIGH"}
    assert run["forcing"]["source_class"].startswith("numerical weather model")
    assert len(run["timeline"]) == forcing.FORECAST_HOURS
    run_dir = tmp_path / "runs" / run["run_id"]
    assert (run_dir / "grids.npz").exists() and len(list((run_dir / "forcing").iterdir())) == len(forcing.MODELS)
    with np.load(run_dir / "grids.npz") as grids:
        assert np.isnan(grids["peak_mean"][0, 0])  # outside assessed cells stays NoData, never dry
        assert grids["hourly_mean"].shape == (forcing.FORECAST_HOURS, NY, NX)
    assert not list((tmp_path / "runs").glob(".tmp-*"))


def test_live_engine_rate_limits_untriggered_reruns(tmp_path):
    _write_static(tmp_path / "static")
    calls = []
    def fetch(bounds):
        calls.append(1)
        return forcing.fetch_snapshot(bounds, getter=_getter(heavy))
    live = engine.LiveEngine(tmp_path / "static", tmp_path / "runs", fetcher=fetch, min_interval_s=3600)
    original = engine.compute_run
    engine.compute_run = lambda s, snap: original(s, snap, members=solver.parameter_members()[:1])
    try:
        assert live.run_once()["outcome"] == "created"
        assert live.run_once()["outcome"] == "rate_limited"
    finally:
        engine.compute_run = original
    assert len(calls) == 1


def test_live_api_serves_runs_grids_and_fails_closed(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    _write_static(tmp_path / "static")
    live = engine.LiveEngine(tmp_path / "static", tmp_path / "runs", fetcher=lambda b: forcing.fetch_snapshot(b, getter=_getter(heavy)), min_interval_s=0)
    original = engine.compute_run
    engine.compute_run = lambda s, snap: original(s, snap, members=solver.parameter_members()[:1])
    try:
        run_id = live.run_once()["run"]["run_id"]
    finally:
        engine.compute_run = original
    monkeypatch.setenv("TWINGUARD_LIVE_STATIC", str(tmp_path / "static"))
    monkeypatch.setenv("TWINGUARD_LIVE_RUNS", str(tmp_path / "runs"))
    monkeypatch.setenv("TWINGUARD_LIVE_SCHEDULE_MIN", "0")
    from fastapi import FastAPI
    from app.live.router import router  # draft router; intentionally not mounted in app.main
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    status = client.get("/live/status").json()
    assert status["run_count"] == 1 and status["latest"]["run_id"] == run_id and status["static_available"]
    latest = client.get("/live/runs/latest")
    assert latest.status_code == 200 and latest.headers["cache-control"] == "no-store"
    assert client.get(f"/live/runs/{run_id}").json()["run_id"] == run_id
    grid = client.get(f"/live/runs/{run_id}/grid/peak_mean").json()
    assert grid["rows"] == NY and grid["cols"] == NX and grid["values"][0][0] is None
    hourly = client.get(f"/live/runs/{run_id}/grid/hourly_mean?hour=4").json()
    assert hourly["valid_time_utc"].endswith("Z")
    assert client.get(f"/live/runs/{run_id}/grid/hourly_mean").status_code == 422
    assert client.get(f"/live/runs/{run_id}/grid/secret").status_code == 422
    assert client.get("/live/runs/..%2F..%2Fetc").status_code in (404, 422)
    assert client.get("/live/runs/live-20260101T000000Z-deadbeef").status_code == 404
    assert len(client.get("/live/runs").json()["runs"]) == 1
