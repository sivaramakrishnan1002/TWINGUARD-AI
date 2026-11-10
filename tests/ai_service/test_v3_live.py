"""B51 (CR-021 / OD-2026-11-10): live forecast scheduler and /v3/live endpoints, with a fake clock and fake transports."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "ai-service"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v3_support import assert_contract, build_fixture, custom_request  # noqa: E402

from app import main  # noqa: E402
from app.v3 import live, static  # noqa: E402
from app.v3.runs import MANAGER  # noqa: E402

DISCLAIMER = "Model forecast — not an official warning"
T0 = datetime(2026, 11, 10, 6, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, **kw):
        self.t += timedelta(**kw)


class FakeOpenMeteo:
    """A23-shaped lattice snapshot; rain changes per call so each cycle has distinct forcing."""

    def __init__(self, clock):
        self.clock, self.calls, self.fail = clock, 0, False

    def __call__(self, bounds):
        from services.flood_engine import forcing as fm
        self.calls += 1
        if self.fail:
            raise OSError("HTTP 429 after one back-off, secret=abc")
        hours = fm.PAST_HOURS + fm.FORECAST_HOURS
        lat, lon = fm.lattice(bounds)
        start = self.clock().replace(minute=0) - timedelta(hours=fm.PAST_HOURS - 1)
        times = [(start + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(hours)]
        rain = np.full((lat.size, hours), 1.0 + 0.5 * self.calls)
        models = [fm.ModelForcing(m, label, km, "https://api.open-meteo.com/v1/forecast", f"{self.calls:064x}", times,
                                  lat, lon, lat, lon, rain) for m, label, km in fm.MODELS]
        return fm.ForcingSnapshot(fetched_at=self.clock().strftime("%Y-%m-%dT%H:%M:%SZ"), lattice_deg=fm.LATTICE_DEG, models=models)


class FakeReservoir:
    def __init__(self, clock):
        self.clock, self.calls = clock, 0

    def __call__(self):
        self.calls += 1
        day = (self.clock() - timedelta(days=1)).strftime("%Y-%m-%d")
        return {"received_at": self.clock().strftime("%Y-%m-%dT%H:%M:%SZ"), "source_date": day,
                "records": [{"reservoir_id": "POONDI", "source_date": day, "water_level_m": 10.5}]}


@pytest.fixture()
def env(tmp_path, monkeypatch):
    grid_dir, product_dir = build_fixture(tmp_path)
    for key, value in {"TWINGUARD_LIVE_STATIC": str(grid_dir), "TWINGUARD_V3_PRODUCT_STATIC": str(product_dir),
                       "TWINGUARD_V3_RUNS": str(tmp_path / "runs"), "TWINGUARD_V3_INLINE_WORKER": "1",
                       "TWINGUARD_V3_MEMBERS": "1", "TWINGUARD_V3_RUN_MIN_INTERVAL_S": "0", "TWINGUARD_V3_ENGINE": "a06",
                       "TWINGUARD_V3_DEVICE_PROBE": "0", "TWINGUARD_V3_LIVE": "1"}.items():
        monkeypatch.setenv(key, value)
    static.clear_cache()
    clock = Clock(T0)
    om, cfm = FakeOpenMeteo(clock), FakeReservoir(clock)
    sched = live.LiveScheduler(clock=clock, fetch_forecast=om, fetch_reservoir=cfm, forecast_calls=lambda b: 240)
    monkeypatch.setattr(live, "SCHEDULER", sched)
    yield {"client": TestClient(main.app), "clock": clock, "om": om, "cfm": cfm, "sched": sched, "mp": monkeypatch}
    MANAGER.wait_idle(60)
    static.clear_cache()


def test_disabled_switch(env, monkeypatch):
    monkeypatch.setenv("TWINGUARD_V3_LIVE", "0")
    client = env["client"]
    status = assert_contract(client.get("/v3/live/status"), "/v3/live/status")
    assert status["enabled"] is False and status["state"] == "disabled" and status["disclaimer"] == DISCLAIMER
    assert status["sources"]["open_meteo"]["state"] == "disabled" and status["next_scheduled_at"] is None
    for method, path in (("get", "/v3/live/latest"), ("post", "/v3/live/refresh")):
        response = getattr(client, method)(path)
        assert response.status_code == 503 and DISCLAIMER in response.json()["detail"]
        assert_contract(response, path, method)
    assert env["om"].calls == 0


def test_catch_up_cycle_publishes_live_run(env):
    client, sched = env["client"], env["sched"]
    assert sched.due() == "catch_up"
    assert client.get("/v3/live/latest").status_code == 404  # before the first run
    run_id = sched.run_cycle("catch_up")
    assert run_id and run_id.startswith("sim-")
    latest = assert_contract(client.get("/v3/live/latest"), "/v3/live/latest")
    assert latest["run_id"] == run_id and latest["run_kind"] == "LIVE_FORECAST" and latest["disclaimer"] == DISCLAIMER
    assert latest["horizon_hours"] == 72 and latest["issued_at"] == "2026-11-10T06:00:00Z" and latest["device"] == "cpu"
    assert {"MODEL_FORECAST", "PUBLISHED_SNAPSHOT"} <= {i["source_mode"] for i in latest["inputs"]}
    run = assert_contract(client.get(f"/v3/simulations/{run_id}"), "/v3/simulations/{run_id}")
    assert run["mode"] == "live" and run["run_kind"] == "LIVE_FORECAST" and run["source_mode"] == "SIMULATED"
    assert run["live"]["cycle"] == "catch_up" and run["live"]["disclaimer"] == DISCLAIMER
    assert run["live"]["reservoir_source_date"] == "2026-11-09" and "zero reservoir inflow" in run["live"]["reservoir_coupling_rule"]
    status = assert_contract(client.get("/v3/live/status"), "/v3/live/status")
    assert status["state"] == "idle" and status["last_good_run_id"] == run_id and status["last_error"] is None
    assert status["sources"]["open_meteo"]["state"] == "ok" and status["sources"]["open_meteo"]["calls_today"] == 240
    assert status["sources"]["cfm_dss"]["calls_today"] == 2 and status["retention"] == {"keep_last": 16, "stored": 1}
    assert status["next_scheduled_at"] == "2026-11-10T09:00:00Z"
    overview = assert_contract(client.get("/v3/overview"), "/v3/overview")
    assert overview["badge"] == "LIVE FORECAST" and overview["live"]["run_id"] == run_id
    assert client.post("/v3/simulations", json={"mode": "live"}).status_code == 422  # live runs only from the cycle


def test_schedule_and_catch_up(env):
    sched, clock = env["sched"], env["clock"]
    sched.run_cycle("catch_up")
    clock.advance(hours=1)
    assert sched.due() is None
    clock.advance(hours=2)
    assert sched.due() == "scheduled"
    clock.advance(hours=4)  # service was down across a whole cycle
    assert sched.due() == "catch_up"


def test_overlap_lock_and_manual_refresh_window(env):
    client, sched, clock = env["client"], env["sched"], env["clock"]
    sched.lock.acquire()
    try:
        busy = assert_contract(client.post("/v3/live/refresh"), "/v3/live/refresh", "post")
        assert busy["state"] == "already_running" and busy["accepted"] is False
        with pytest.raises(live.LiveBusy):
            sched.run_cycle("scheduled")
        assert assert_contract(client.get("/v3/live/status"), "/v3/live/status")["state"] == "running"
    finally:
        sched.lock.release()
    started = sched.refresh(background=False)
    assert started["state"] == "started" and started["disclaimer"] == DISCLAIMER
    clock.advance(seconds=300)
    limited = client.post("/v3/live/refresh")
    assert limited.status_code == 429 and 0 < int(limited.headers["retry-after"]) <= 300
    assert_contract(limited, "/v3/live/refresh", "post")
    clock.advance(seconds=301)
    assert sched.refresh(background=False)["state"] == "started"
    assert env["om"].calls == 2


def test_retention_prunes_only_live_runs(env, monkeypatch):
    client, sched, clock = env["client"], env["sched"], env["clock"]
    monkeypatch.setattr(live, "KEEP_LAST", 3)
    custom = client.post("/v3/simulations", json=custom_request([5.0, 5.0])).json()["run_id"]
    assert MANAGER.wait_idle(60)
    ids = []
    for _ in range(5):
        ids.append(sched.run_cycle("scheduled"))
        clock.advance(hours=3)
    assert len(set(ids)) == 5
    for old in ids[:2]:
        assert client.get(f"/v3/simulations/{old}").status_code == 404
    for kept in ids[2:]:
        assert client.get(f"/v3/simulations/{kept}").json()["state"] == "completed"
    assert client.get(f"/v3/simulations/{custom}").json()["state"] == "completed"  # non-live runs are never pruned
    assert sched.status()["retention"] == {"keep_last": 3, "stored": 3}
    assert len(list((Path(sched._dir())).glob("forecast_*.npz"))) == 3


def test_failure_keeps_last_good_run(env):
    client, sched, clock = env["client"], env["sched"], env["clock"]
    good = sched.run_cycle("catch_up")
    clock.advance(hours=3)
    env["om"].fail = True
    assert sched.run_cycle("scheduled") is None
    status = assert_contract(client.get("/v3/live/status"), "/v3/live/status")
    assert status["last_error"]["stage"] == "fetch_forecast" and status["last_good_run_id"] == good
    assert status["sources"]["open_meteo"]["state"] == "error"
    assert "secret" not in json.dumps(status)  # credential-free messages only
    assert client.get("/v3/live/latest").json()["run_id"] == good


def test_daily_budget_stops_before_5000(env, monkeypatch):
    client, sched, clock = env["client"], env["sched"], env["clock"]
    sched.forecast_calls = lambda b: 2600
    first = sched.run_cycle("catch_up")
    clock.advance(hours=3)
    assert sched.run_cycle("scheduled") is None  # 2600 + 2600 >= 5000
    status = client.get("/v3/live/status").json()
    assert "budget" in status["last_error"]["message"] and status["sources"]["open_meteo"]["calls_today"] == 2600
    assert env["om"].calls == 1 and status["last_good_run_id"] == first
    clock.advance(minutes=30)
    refused = client.post("/v3/live/refresh")
    assert refused.status_code == 503 and "budget" in refused.json()["detail"]
    clock.t = datetime(2026, 11, 11, 0, 30, tzinfo=timezone.utc)  # new UTC day resets the count
    assert sched.run_cycle("scheduled")


def test_reservoir_snapshot_at_most_daily(env):
    sched, clock = env["sched"], env["clock"]
    sched.run_cycle("catch_up")
    for _ in range(3):
        clock.advance(hours=3)
        sched.run_cycle("scheduled")
    assert env["cfm"].calls == 1  # reused while under 24 h old
    clock.advance(hours=16)
    sched.run_cycle("scheduled")
    assert env["cfm"].calls == 2


def test_no_google_key_in_live_responses(env):
    client, sched = env["client"], env["sched"]
    sched.run_cycle("catch_up")
    blob = json.dumps([client.get(p).json() for p in ("/v3/live/status", "/v3/live/latest", "/v3/overview")])
    assert "AIza" not in blob and "VITE_GOOGLE" not in blob and "token" not in blob.lower()


def test_what_if_on_live_run_makes_no_upstream_fetch(env):
    client, sched = env["client"], env["sched"]
    base = sched.run_cycle("catch_up")
    calls = env["om"].calls
    accepted = client.post("/v3/simulations", json={"mode": "what_if", "what_if": {"base_run_id": base, "rainfall_scale_pct": 150}})
    assert accepted.status_code == 202, accepted.text
    assert MANAGER.wait_idle(60)
    run = client.get(f"/v3/simulations/{accepted.json()['run_id']}").json()
    assert run["state"] == "completed" and run["run_kind"] == "WHAT_IF" and env["om"].calls == calls
    job = json.loads((MANAGER.run_dir(run["run_id"]) / "job.json").read_text(encoding="utf-8"))
    assert job["base_snapshot"].endswith(".npz")
