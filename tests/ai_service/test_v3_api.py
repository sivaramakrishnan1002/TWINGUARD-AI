"""B47 focused tests for the C4 v3 product API (docs/api/ai-service.yaml x-c4-v3-product-api).

Uses a synthetic 10x12 grid and road lattice so the suite runs without the git-ignored project data.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "ai-service"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v3_support import assert_contract, build_fixture, custom_request, v3_section, validate  # noqa: E402

from app import main  # noqa: E402
from app.v3 import config, static, weather  # noqa: E402
from app.v3.runs import MANAGER  # noqa: E402

RUN = "/v3/simulations/{run_id}"


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    root = tmp_path_factory.mktemp("v3")
    grid_dir, product_dir = build_fixture(root)
    mp = pytest.MonkeyPatch()
    mp.setenv("TWINGUARD_LIVE_STATIC", str(grid_dir))
    mp.setenv("TWINGUARD_V3_PRODUCT_STATIC", str(product_dir))
    mp.setenv("TWINGUARD_V3_RUNS", str(root / "runs"))
    mp.setenv("TWINGUARD_V3_INLINE_WORKER", "1")
    mp.setenv("TWINGUARD_V3_MEMBERS", "1")
    mp.setenv("TWINGUARD_V3_RUN_MIN_INTERVAL_S", "0")
    calls = []

    def fake_fetch(url, timeout=30.0):
        calls.append(url)
        hours = [f"2026-11-07T{h:02d}:00" for h in range(48)]
        return json.dumps({"utc_offset_seconds": 0,
                           "current": {"temperature_2m": 27.5, "precipitation": 1.2, "relative_humidity_2m": 88, "wind_speed_10m": 14.0},
                           "hourly": {"time": hours, "precipitation": [0.5] * 48, "precipitation_probability": [60] * 48}}).encode()

    mp.setattr(weather, "FETCHER", fake_fetch)
    static.clear_cache()
    client = TestClient(main.app)
    yield {"client": client, "root": root, "calls": calls, "mp": mp, "grid_dir": grid_dir}
    MANAGER.wait_idle(60)
    mp.undo()
    static.clear_cache()


def run_and_wait(client, body) -> str:
    response = client.post("/v3/simulations", json=body)
    assert response.status_code == 202, response.text
    accepted = assert_contract(response, "/v3/simulations", "post")
    assert MANAGER.wait_idle(120)
    return accepted["run_id"]


@pytest.fixture(scope="module")
def base_run(env):
    return run_and_wait(env["client"], custom_request())


# ------------------------------------------------------------------------------------------------- coverage
def test_every_contract_operation_is_mounted():
    mounted = {(m.upper(), p) for p, item in main.app.openapi()["paths"].items() if p.startswith("/v3/") for m in item}
    for path, item in v3_section()["paths"].items():
        for method in item:
            if method in ("get", "post", "put", "delete", "patch"):
                assert (method.upper(), path) in mounted, f"{method.upper()} {path} is not mounted"


def test_no_operation_accepts_or_returns_a_maps_key(env, base_run):
    schema = main.app.openapi()
    for path, item in schema["paths"].items():
        if path.startswith("/v3/"):
            for op in item.values():
                for param in op.get("parameters", []):
                    assert "key" not in param["name"].lower() or param["name"] == "event_key"
    body = json.dumps([env["client"].get(p).json() for p in ("/v3/status", "/v3/overview", f"/v3/simulations/{base_run}")])
    assert "VITE_GOOGLE" not in body and "AIza" not in body


# ------------------------------------------------------------------------------------------------- status/events
def test_status_and_events(env):
    client = env["client"]
    body = assert_contract(client.get("/v3/status"), "/v3/status")
    assert body["static_available"] is True and body["weather_min_refresh_interval_s"] >= 600
    assert body["device"]["resolved"] == "cpu" and body["device"]["gpu_jobs_max"] == 1  # A06 pilot is CPU-only
    events = assert_contract(client.get("/v3/events"), "/v3/events")["events"]
    assert {"2015-12-01", "2023-12-04"} <= {e["event_key"] for e in events}
    assert all(e["source_mode"] == "REPLAY" for e in events)


def test_no_background_open_meteo_fetch(env):
    before = len(env["calls"])
    env["client"].get("/v3/status")
    env["client"].get("/v3/overview")
    assert len(env["calls"]) == before


# ------------------------------------------------------------------------------------------------- simulations
@pytest.mark.parametrize("body,status", [
    ({"mode": "event"}, 422),
    ({"mode": "custom"}, 422),
    ({"mode": "what_if"}, 422),
    ({"mode": "event", "event_key": "1999-01-01"}, 400),
    ({"mode": "event", "event_key": "2015-12-01", "duration_hours": 5}, 422),
    ({"mode": "event", "event_key": "2015-12-01", "resolution": "focus"}, 422),
    ({"mode": "event", "event_key": "2015-12-01", "resolution": "focus", "focus_area": "ADYAR"}, 503),
    ({"mode": "event", "event_key": "2015-12-01", "google_maps_api_key": "x"}, 422),
    ({**custom_request([250.0])}, 422),
    ({"mode": "what_if", "what_if": {"base_run_id": "whatif-20260101T000000Z-deadbeef"}}, 404),
    ({"mode": "what_if", "what_if": {"base_run_id": "x", "reservoir_release_m3s": {"VEERANAM": 10}}}, 422),
])
def test_create_simulation_errors(env, body, status):
    response = env["client"].post("/v3/simulations", json=body)
    assert response.status_code == status, response.text
    assert_contract(response, "/v3/simulations", "post")


def test_malformed_json_is_400(env):
    response = env["client"].post("/v3/simulations", content=b"{bad", headers={"content-type": "application/json"})
    assert response.status_code == 400 and response.json()["code"] == "bad_request"


def test_completed_run_and_cache(env, base_run):
    client = env["client"]
    run = assert_contract(client.get(RUN.format(run_id=base_run)), RUN)
    assert run["state"] == "completed" and run["source_mode"] == "SIMULATED" and len(run["frames"]) == 12
    assert run["summary"]["max_depth_m"] > 0.3 and run["summary"]["roads_blocked_km"] > 0
    assert any(i["source_mode"] == "SCENARIO_INPUT" for i in run["provenance"]["inputs"])
    assert run["provenance"]["device"] == {"used": "cpu", "name": None, "fallback_reason": None}
    assert len(run["limitations"]) <= 5
    again = client.post("/v3/simulations", json=custom_request())
    assert again.status_code == 202 and again.json() == {**again.json(), "run_id": base_run, "state": "cached"}
    listing = assert_contract(client.get("/v3/simulations?limit=1"), "/v3/simulations")
    assert listing["runs"][0]["run_id"] == base_run
    assert client.get("/v3/simulations?cursor=abc").status_code == 400


def test_unknown_and_malformed_run_ids_are_404(env):
    for rid in ("evt-20260101T000000Z-deadbeef", "evt-..-etc", "live-20260101T000000Z-deadbeef"):
        response = env["client"].get(RUN.format(run_id=rid))
        assert response.status_code == 404
        assert_contract(response, RUN)


def test_results_of_unfinished_run_are_503(env, base_run, monkeypatch):
    doc = dict(MANAGER.get(base_run), state="running")
    monkeypatch.setitem(MANAGER.docs, base_run, doc)
    response = env["client"].get(RUN.format(run_id=base_run) + "/depth")
    assert response.status_code == 503 and response.headers["retry-after"]
    assert_contract(response, RUN + "/depth")


def test_queue_full_is_409_and_start_interval_is_429(env, monkeypatch):
    monkeypatch.setattr(config, "MAX_QUEUE", 0)
    response = env["client"].post("/v3/simulations", json=custom_request([1.0, 2.0]))
    assert response.status_code == 409
    assert_contract(response, "/v3/simulations", "post")
    monkeypatch.setattr(config, "MAX_QUEUE", 4)
    monkeypatch.setenv("TWINGUARD_V3_RUN_MIN_INTERVAL_S", "3600")
    response = env["client"].post("/v3/simulations", json=custom_request([3.0]))
    assert response.status_code == 429 and int(response.headers["retry-after"]) > 0
    assert_contract(response, "/v3/simulations", "post")


def test_child_process_worker(env, monkeypatch):
    monkeypatch.setenv("TWINGUARD_V3_INLINE_WORKER", "0")
    run_id = run_and_wait(env["client"], {**custom_request([10.0, 10.0]), "duration_hours": 6})
    run = env["client"].get(RUN.format(run_id=run_id)).json()
    assert run["state"] == "completed", run.get("error")


# ------------------------------------------------------------------------------------------------- results
def test_depth(env, base_run):
    client, url = env["client"], RUN.format(run_id=base_run) + "/depth"
    peak = assert_contract(client.get(url), RUN + "/depth")
    assert peak["frame_index"] is None and peak["rows"] == 10 and peak["cols"] == 12 and peak["unit"] == "m"
    assert all(row[-1] is None for row in peak["values"])  # drain column: unknown, never 0
    assert all(v is None or round(v, 2) == v for row in peak["values"] for v in row)
    frame = assert_contract(client.get(url + "?frame_index=3&layer=depth_p95"), RUN + "/depth")
    assert frame["valid_time_utc"].endswith("Z")
    assert_contract(client.get(url + "?layer=velocity_mps"), RUN + "/depth")
    for query in ("?frame_index=99", "?resolution=focus&focus_area=ADYAR", "?layer=secret"):
        response = client.get(url + query)
        assert response.status_code == 422, query
        assert_contract(response, RUN + "/depth")


def test_buildings_paging_and_filters(env, base_run):
    client, url = env["client"], RUN.format(run_id=base_run) + "/buildings"
    first = assert_contract(client.get(url + "?limit=50"), RUN + "/buildings")
    assert first["count"] == 50 and first["total"] == 120 and first["next_cursor"] == "50"
    second = assert_contract(client.get(url + f"?limit=100&cursor={first['next_cursor']}"), RUN + "/buildings")
    assert second["count"] == 70 and second["next_cursor"] is None
    deep = assert_contract(client.get(url + "?min_depth_m=0.3"), RUN + "/buildings")
    assert deep["total"] > 0 and all(b["max_depth_m"] >= 0.3 for b in deep["buildings"])
    assert {b["height_source"] for b in first["buildings"]} == {"osm_levels", "estimated"}
    boxed = client.get(url + "?bbox=80.199,13.0,80.21,13.06").json()
    assert 0 < boxed["total"] < 120
    assert client.get(url + "?bbox=1,2,3").status_code == 422
    assert client.get(url + "?cursor=x").status_code == 400


def test_wards_unavailable_until_a25(env, base_run):
    response = env["client"].get(RUN.format(run_id=base_run) + "/wards")
    assert response.status_code == 503
    assert_contract(response, RUN + "/wards")
    assert env["client"].get("/v3/static/wards").status_code == 503


def test_roads_three_state(env, base_run):
    body = assert_contract(env["client"].get(RUN.format(run_id=base_run) + "/roads"), RUN + "/roads")
    states = {f["properties"]["state"] for f in body["features"]}
    assert states == {"ASSESSED_PASSABLE", "ASSESSED_BLOCKED", "UNKNOWN"}
    bridge = next(f for f in body["features"] if f["properties"]["edge_id"] == "e:0")
    assert bridge["properties"]["state"] == "UNKNOWN" and bridge["properties"]["unknown_reason"] == "UNASSESSED_STRUCTURE"
    blocked = [f for f in body["features"] if f["properties"]["state"] == "ASSESSED_BLOCKED"]
    assert all(f["properties"]["depth_m"] >= 0.3 and f["properties"]["speed_factor"] == 0 for f in blocked)
    higher = env["client"].get(RUN.format(run_id=base_run) + "/roads?blocked_depth_threshold_m=1.0").json()
    assert sum(f["properties"]["state"] == "ASSESSED_BLOCKED" for f in higher["features"]) < len(blocked)
    assert env["client"].get(RUN.format(run_id=base_run) + "/roads?blocked_depth_threshold_m=2").status_code == 422


def test_routes(env, base_run):
    client = env["client"]
    west, east = {"lon": 80.2005, "lat": 13.0445}, {"lon": 80.2551, "lat": 13.0445}
    body = assert_contract(client.post("/v3/routes", json={"run_id": base_run, "origin": west, "destination": east}), "/v3/routes", "post")
    assert body["status"] == "found" and body["routes"][0]["policy"] == "avoid_blocked"
    assert {r["policy"] for r in body["routes"]} == {"avoid_blocked", "avoid_blocked_and_unknown", "shortest_dry"}
    assert body["dry_baseline"]["route_status"] == "ASSESSED_PASSABLE"
    for route in body["routes"]:
        if route["route_status"] != "NO_ROUTE":
            assert route["length_by_state_m"]["ASSESSED_BLOCKED"] == 0
    strict = next(r for r in body["routes"] if r["policy"] == "avoid_blocked_and_unknown")
    assert strict["route_status"] in ("ASSESSED_PASSABLE", "NO_ROUTE")
    far = client.post("/v3/routes", json={"run_id": base_run, "origin": {"lon": 80.45, "lat": 12.75}, "destination": east}).json()
    assert far["status"] == "origin_unreachable" and far["routes"] == []
    for bad, status in (({"run_id": base_run, "origin": {"lon": 81, "lat": 13}, "destination": east}, 422),
                        ({"run_id": "evt-20260101T000000Z-deadbeef", "origin": west, "destination": east}, 404),
                        ({"run_id": base_run, "origin": west, "destination": east, "frame_index": 99}, 422)):
        response = client.post("/v3/routes", json=bad)
        assert response.status_code == status
        assert_contract(response, "/v3/routes", "post")


def test_shelters_incidents_and_plan(env, base_run):
    client, base = env["client"], RUN.format(run_id=base_run)
    report = assert_contract(client.get(base + "/shelters?capacity_factor=2.0"), RUN + "/shelters")
    valley = next(s for s in report["shelters"] if s["shelter_id"] == "osm:2")
    assert valley["reachable"] is False and valley["site_max_depth_m"] >= 0.3
    assert report["totals"]["demand_people"] > 0 and report["capacity_factor"] == 2.0
    assert client.get(base + "/shelters?capacity_factor=3").status_code == 422
    incidents = assert_contract(client.get(base + "/incidents?min_severity=info"), RUN + "/incidents")["incidents"]
    assert incidents and all(i["generated"] is True and i["generated_from"] == "simulation" for i in incidents)
    assert {"building_flooding", "road_blocked", "population_cut_off", "shelter_unreachable"} <= {i["type"] for i in incidents}
    critical = client.get(base + "/incidents?min_severity=critical").json()["incidents"]
    assert all(i["severity"] == "critical" for i in critical)
    plan = assert_contract(client.get(base + "/emergency-plan"), RUN + "/emergency-plan")
    assert plan["assignments"] and plan["resource_set_version"] == 0


def test_scenario_resources(env):
    client = env["client"]
    current = assert_contract(client.get("/v3/scenario-resources"), "/v3/scenario-resources")
    assert all(r["source_mode"] == "SCENARIO_INPUT" for r in current["resources"])
    new = {"version": current["version"], "resources": [
        {"resource_id": "boats-1", "type": "boat", "count": 3, "base": {"name": "Base A", "location": {"lon": 80.21, "lat": 13.04}}}]}
    saved = assert_contract(client.put("/v3/scenario-resources", json=new), "/v3/scenario-resources", "put")
    assert saved["version"] == current["version"] + 1 and saved["resources"][0]["source_mode"] == "SCENARIO_INPUT"
    stale = client.put("/v3/scenario-resources", json=new)
    assert stale.status_code == 409
    assert_contract(stale, "/v3/scenario-resources", "put")
    bad = client.put("/v3/scenario-resources", json={"version": saved["version"], "resources": [{**new["resources"][0], "type": "helicopter"}]})
    assert bad.status_code == 422
    dup = client.put("/v3/scenario-resources", json={"version": saved["version"], "resources": new["resources"] * 2})
    assert dup.status_code == 422


def test_what_if_and_comparison(env, base_run):
    client = env["client"]
    whatif = run_and_wait(client, {"mode": "what_if", "what_if": {"base_run_id": base_run, "rainfall_scale_pct": 200, "tide_offset_m": 1.0}})
    assert whatif.startswith("whatif-")
    run = client.get(RUN.format(run_id=whatif)).json()
    assert run["request"]["duration_hours"] == 6 and run["request"]["what_if"]["rainfall_scale_pct"] == 200
    comparison = client.get(RUN.format(run_id=whatif) + "/comparison").json()
    assert comparison["baseline_run_id"] == base_run and comparison["delta"]["max_depth_m"] > 0
    assert comparison["modifiers"]["base_run_id"] == base_run
    response = client.get(RUN.format(run_id=base_run) + "/comparison")
    assert response.status_code == 400
    assert_contract(response, RUN + "/comparison")
    assert client.get(RUN.format(run_id=base_run) + f"/comparison?baseline_run_id={whatif}").status_code == 200


def test_comparison_schema_for_increases(env, base_run):
    """Increases validate against Comparison; negative deltas await the Integrator's SimulationSummary/delta change."""
    whatif = run_and_wait(env["client"], {"mode": "what_if", "what_if": {"base_run_id": base_run, "rainfall_scale_pct": 150}})
    assert_contract(env["client"].get(RUN.format(run_id=whatif) + "/comparison"), RUN + "/comparison")


# ------------------------------------------------------------------------------------------------- weather/forecast
def test_weather_cache_and_min_interval(env):
    client, calls = env["client"], env["calls"]
    before = len(calls)
    first = assert_contract(client.get("/v3/weather"), "/v3/weather")
    assert first["source_mode"] == "MODEL_FORECAST" and "Open-Meteo" in first["attribution"] and len(calls) == before + 1
    cached = assert_contract(client.get("/v3/weather"), "/v3/weather")
    assert len(calls) == before + 1 and cached["fetched_at"] == first["fetched_at"]
    limited = client.get("/v3/weather?refresh=true")
    assert limited.status_code == 429 and 0 < int(limited.headers["retry-after"]) <= 600
    assert_contract(limited, "/v3/weather")
    assert len(calls) == before + 1
    status = client.get("/v3/status").json()
    assert status["weather_next_fetch_allowed_at"].endswith("Z")


def test_weather_upstream_failure_is_503(env, monkeypatch, tmp_path):
    monkeypatch.setenv("TWINGUARD_V3_RUNS", str(tmp_path / "other"))

    def broken(url, timeout=30.0):
        raise OSError("connection refused with secret details")

    monkeypatch.setattr(weather, "FETCHER", broken)
    response = env["client"].get("/v3/weather")
    assert response.status_code == 503 and "secret" not in response.text
    assert_contract(response, "/v3/weather")
    again = env["client"].get("/v3/weather")
    assert again.status_code == 429  # a failed attempt still counts against the 600 s interval


def _fake_snapshot(calls):
    """A tiny Open-Meteo lattice snapshot built with the engine's own dataclasses (no network)."""
    from services.flood_engine import forcing as fm

    def fetch(bounds, models=fm.MODELS, **_kw):
        calls.append(bounds)
        hours = fm.PAST_HOURS + fm.FORECAST_HOURS
        lat, lon = fm.lattice(bounds)
        times = [f"2026-11-{6 + (h // 24):02d}T{h % 24:02d}:00" for h in range(hours)]
        model = fm.ModelForcing("ecmwf_ifs", "ECMWF IFS HRES", 9.0, "https://api.open-meteo.com/v1/forecast", "b" * 64, times,
                                lat, lon, lat, lon, np.full((lat.size, hours), 2.0))
        return fm.ForcingSnapshot(fetched_at="2026-11-07T00:00:00Z", lattice_deg=fm.LATTICE_DEG, models=[model])
    return fetch


def test_forecast_runs_use_cached_snapshot(env, monkeypatch):
    from services.flood_engine import forcing as fm

    calls = []
    monkeypatch.setattr(fm, "fetch_snapshot", _fake_snapshot(calls))
    monkeypatch.setattr(weather, "_now", lambda: 1_794_009_600.0)  # 2026-11-07T00:00:00Z
    run_id = run_and_wait(env["client"], {"mode": "forecast", "duration_hours": 6})
    run = env["client"].get(RUN.format(run_id=run_id)).json()
    assert run["state"] == "completed", run.get("error")
    assert any(i["source_mode"] == "MODEL_FORECAST" for i in run["provenance"]["inputs"])
    assert len(calls) == 1
    again = env["client"].post("/v3/simulations", json={"mode": "forecast", "duration_hours": 6})
    assert again.json()["state"] == "cached" and again.json()["run_id"] == run_id
    longer = run_and_wait(env["client"], {"mode": "forecast", "duration_hours": 12})
    assert longer != run_id and len(calls) == 1  # a different request reuses the cached snapshot: no second fetch


def test_forecast_rate_limited_without_cache(env, monkeypatch, tmp_path):
    monkeypatch.setenv("TWINGUARD_V3_RUNS", str(tmp_path / "fresh"))
    from services.flood_engine import forcing as fm

    monkeypatch.setattr(fm, "fetch_snapshot", lambda *a, **k: (_ for _ in ()).throw(OSError("offline")))
    first = env["client"].post("/v3/simulations", json={"mode": "forecast", "duration_hours": 6})
    assert first.status_code == 202
    MANAGER.wait_idle(60)
    assert env["client"].get(RUN.format(run_id=first.json()["run_id"])).json()["state"] == "failed"
    second = env["client"].post("/v3/simulations", json={"mode": "forecast", "duration_hours": 6})
    assert second.status_code == 429 and second.headers["retry-after"]
    assert_contract(second, "/v3/simulations", "post")


# ------------------------------------------------------------------------------------------------- overview/static
def test_overview(env, base_run):
    body = assert_contract(env["client"].get("/v3/overview"), "/v3/overview")
    assert body["badge"] == "DEMO / SIMULATION" and body["latest_run"]["state"] == "completed"
    assert sum(body["incident_counts"].values()) > 0 and body["top_wards"] == []


def test_static_layers(env):
    client = env["client"]
    shelters = assert_contract(client.get("/v3/static/shelters"), "/v3/static/{layer}")
    assert len(shelters["features"]) == 3 and shelters["source_mode"] == "STATIC_REFERENCE"
    buildings = assert_contract(client.get("/v3/static/buildings?limit=10"), "/v3/static/{layer}")
    assert buildings["features"][0]["geometry"]["type"] == "Polygon" and buildings["next_cursor"] == "10"
    assert client.get("/v3/static/roads").status_code == 422
    response = client.get("/v3/static/focus_areas")
    assert response.status_code == 503
    assert_contract(response, "/v3/static/{layer}")


def test_validator_rejects_bad_bodies():
    from v3_support import v3_section as section
    schema = section()["schemas"]["Incident"]
    assert validate({"incident_id": "x", "generated": False, "type": "building_flooding", "severity": "watch",
                     "location": {"lon": 80.2, "lat": 13.0}, "valid_time_utc": "2026-01-01T00:00:00Z"}, schema)


def test_trial_promotion_matches_contract_operations():
    """Same checks as test_api.py applies to top-level paths, run against the v3 section before promotion."""
    generated = main.app.openapi()
    for path, item in v3_section()["paths"].items():
        for method, contract_op in item.items():
            if method not in ("get", "post", "put"):
                continue
            runtime = generated["paths"][path][method]
            assert runtime["operationId"] == contract_op["operationId"]
            missing = set(contract_op["responses"]) - set(runtime["responses"])
            assert not missing, (method, path, missing)
            if "requestBody" in contract_op:
                want = contract_op["requestBody"]["content"]["application/json"]["schema"]["$ref"].split("/")[-1]
                got = runtime["requestBody"]["content"]["application/json"]["schema"]["$ref"].split("/")[-1]
                assert got == want, (path, want, got)
    v1 = generated["paths"]["/route"]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    assert v1.endswith("/RouteRequest")
