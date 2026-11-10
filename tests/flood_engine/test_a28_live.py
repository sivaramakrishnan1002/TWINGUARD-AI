"""A28: reservoir coupling rule, run_scenario wiring, forecast forcing checks and a no-rain control (no network)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, Path(__file__).resolve().parent):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from services.flood_engine import forcing, reservoir_coupling as rc, scenario  # noqa: E402
from test_a25 import static_root  # noqa: E402,F401

RUN = datetime(2026, 11, 10, 6, 0, tzinfo=timezone.utc)


def snapshot(pcts=None, day="2026-11-10", received="2026-11-10T04:00:00Z"):
    pcts = pcts or {"Chembarambakkam": 95.0, "Poondi": 50.0, "Red Hills": 101.0, "Cholavaram": 89.9}
    recs = []
    for name, pct in pcts.items():
        key = rc._key(name)
        cap = rc.RESERVOIRS[key]["capacity_mcm"] if key else 10.0
        for back in (1, 0):  # an older and a newer row; the newest date wins
            d = (datetime.fromisoformat(day) - timedelta(days=back)).date().isoformat()
            recs.append({"reservoir_name": name, "source_date": d, "observed_at": None, "time_precision": "date",
                         "water_level_m": 20.0, "average_storage_mcm": cap * (pct - 5 * back) / 100.0})
    recs.append({"reservoir_name": "Thervoy Kandigai", "source_date": day, "average_storage_mcm": 5.0})
    return {"history_kind": "daily", "source_mode": "LIVE", "received_at": received, "records": recs}


def test_rule_thresholds_and_versioning():
    assert rc.RULE_ID == "A28-RES-STORAGE-v1"
    q = 100.0
    assert rc.release_for(89.99, q) == 0.0 and rc.release_for(90.0, q) == 0.0
    assert rc.release_for(95.0, q) == 50.0 and rc.release_for(99.0, q) == pytest.approx(90.0)
    assert rc.release_for(100.0, q) == 200.0 and rc.release_for(130.0, q) == 200.0
    p = rc.parameters()
    assert p["threshold_pct"] == 90.0 and p["reservoirs"]["CHEMBARAMBAKKAM"]["capacity_mcm"] == pytest.approx(103.22, abs=0.01)
    assert "ASSUMPTION" in p["basis"]


def test_couple_maps_snapshot_with_aliases_units_and_labels():
    out = rc.couple(snapshot(), RUN)
    assert out["status"] == "applied" and out["snapshot_source_date"] == "2026-11-10" and out["basis"] == "ASSUMPTION"
    rel = out["releases_m3s"]
    assert rel["CHEMBARAMBAKKAM"] == pytest.approx(85.0)   # 95 % -> half of Q_ctrl 170
    assert rel["POONDI"] == 0.0 and rel["CHOLAVARAM"] == 0.0
    assert rel["PUZHAL"] == pytest.approx(120.0)            # "Red Hills" alias, >= 100 % -> spill 2 x 60
    rows = {r["reservoir"]: r for r in out["reservoirs"]}
    assert rows["CHEMBARAMBAKKAM"]["storage_pct"] == pytest.approx(95.0, abs=0.01)
    assert rows["CHEMBARAMBAKKAM"]["time_precision"] == "date" and "T" not in rows["CHEMBARAMBAKKAM"]["source_date"]
    assert all(r["release_basis"] == "ASSUMPTION" for r in rows.values() if r["status"] == "applied")
    assert "THERVOY" not in json.dumps(rows).upper()        # no outlet in the A25 grid
    explicit = rc.couple([{"reservoir_name": "Poondi", "source_date": "2026-11-10", "storage_pct": 100.0}], RUN)
    assert explicit["releases_m3s"]["POONDI"] == 280.0 and explicit["snapshot_received_at"] is None


@pytest.mark.parametrize("snap,reason", [
    (None, "missing"), ({}, "missing"), ({"records": [{"reservoir_name": "Unknown", "source_date": "x"}]}, "unparseable"),
    (snapshot(day="2026-11-07"), "stale"), (snapshot(received="2026-11-07T12:00:00Z"), "stale"),
])
def test_missing_stale_or_bad_snapshot_gives_zero_inflow(snap, reason):
    out = rc.couple(snap, RUN)
    assert reason in out["status"] and not any(out["releases_m3s"].values())


def test_run_scenario_applies_rule_and_labels_inputs(static_root, tmp_path):
    runs = tmp_path / "runs"
    base = scenario.run_scenario(static_root, runs, mode="event", event_key="2015-12-01", duration_hours=6)
    doc = scenario.run_scenario(static_root, runs, mode="event", event_key="2015-12-01", duration_hours=6,
                                reservoir_snapshot=snapshot(), run_time=RUN)
    assert doc["run_id"] != base["run_id"] and doc["reservoir_coupling"]["status"] == "applied"
    assert doc["forcing"]["reservoir_release_m3s"]["CHEMBARAMBAKKAM"] == pytest.approx(85.0) and doc["forcing"]["inflow_cells_used"] == 1
    srcs = {i["name"]: i for i in doc["provenance"]["inputs"]}
    assert srcs["reservoir_snapshot"]["source_mode"] == "PUBLISHED_SNAPSHOT"
    assert srcs["reservoir_outlet_inflow"]["source_mode"] == "SCENARIO_INPUT" and "not an observed release" in srcs["reservoir_outlet_inflow"]["source"]
    assert doc["diagnostics"]["central"]["inflow_m3"] > 0 and doc["diagnostics"]["central"]["mass_balance_relative_error"] <= 0.01
    stale = scenario.run_scenario(static_root, runs, mode="event", event_key="2015-12-01", duration_hours=6,
                                  reservoir_snapshot=snapshot(day="2026-11-01"), run_time=RUN)
    assert "stale" in stale["reservoir_coupling"]["status"] and stale["forcing"]["inflow_cells_used"] == 0
    assert stale["summary"] == base["summary"]  # zero inflow == no coupling
    # existing calls without the new arguments are unchanged (same cached run)
    again = scenario.run_scenario(static_root, runs, mode="event", event_key="2015-12-01", duration_hours=6)
    assert again["cached"] and again["run_id"] == base["run_id"] and again.get("reservoir_coupling") is None


def _fake_forecast(rain_mm=2.0, fetched="2026-11-10T05:12:00Z", first_valid="2026-11-09T06:00"):
    def getter(url, timeout):
        from urllib.parse import parse_qs, urlparse
        q = parse_qs(urlparse(url).query)
        lat = [float(v) for v in q["latitude"][0].split(",")]
        lon = [float(v) for v in q["longitude"][0].split(",")]
        n = forcing.PAST_HOURS + forcing.FORECAST_HOURS
        t0 = datetime.fromisoformat(first_valid)
        times = [(t0 + timedelta(hours=k)).strftime("%Y-%m-%dT%H:%M") for k in range(n)]
        scale = 1.0 if "ecmwf" in url else 0.5
        return json.dumps([{"latitude": round(a, 2), "longitude": round(b, 2), "utc_offset_seconds": 0, "hourly_units": {"precipitation": "mm"},
                            "hourly": {"time": times, "precipitation": [0.0] * forcing.PAST_HOURS + [rain_mm * scale] * forcing.FORECAST_HOURS}}
                           for a, b in zip(lat, lon)]).encode()
    return lambda bounds: forcing.fetch_snapshot(bounds, getter=getter, now=datetime.fromisoformat(fetched.replace("Z", "+00:00")))


def test_forecast_forcing_alignment_units_horizon_coverage(static_root, tmp_path):
    runs = tmp_path / "runs"
    doc = scenario.run_scenario(static_root, runs, mode="forecast", duration_hours=72, fetch_forecast=_fake_forecast(), use_cache=False)
    chk = doc["forecast_check"]
    assert chk["horizon_hours"] == 72 and chk["units"].startswith("mm per 1-hour") and chk["fetched_at"] == "2026-11-10T05:12:00Z"
    assert chk["valid_times_utc"] == ["2026-11-10T06:00:00Z", "2026-11-13T05:00:00Z"]
    assert chk["simulation_start_utc"] == "2026-11-10T05:00:00Z" and doc["frames"][0]["valid_time_utc"] == "2026-11-10T05:00:00Z"
    assert len(doc["frames"]) == 145 and doc["frames"][-1]["valid_time_utc"] == "2026-11-13T05:00:00Z"
    assert {m["model"] for m in chk["models"]} == {m for m, _, _ in forcing.MODELS}
    assert all(m["active_cell_coverage"] == 1.0 for m in chk["models"])
    assert doc["forcing"]["total_mm_domain_mean"] == pytest.approx(144.0, abs=0.01)  # 2 mm/h x 72 h (ECMWF)
    assert doc["diagnostics"]["central"]["mass_balance_relative_error"] <= 0.01
    rain_in = next(i for i in doc["provenance"]["inputs"] if i["name"] == "rainfall")
    assert rain_in["source_mode"] == "MODEL_FORECAST" and rain_in["fetched_at"] == "2026-11-10T05:12:00Z"
    ens = scenario.run_scenario(static_root, runs, mode="forecast", duration_hours=24, fetch_forecast=_fake_forecast(), forecast_model="ensemble_mean", use_cache=False)
    assert ens["forecast_check"]["forcing_used"].startswith("open-meteo:ensemble_mean(")
    assert ens["forcing"]["total_mm_domain_mean"] == pytest.approx(24 * 2.0 * (1 + 0.5 + 0.5) / 3, abs=0.01)
    with pytest.raises(scenario.ScenarioError):
        scenario.run_scenario(static_root, runs, mode="forecast", duration_hours=24, fetch_forecast=_fake_forecast(), forecast_model="gfs", use_cache=False)


def test_no_rain_no_inflow_control_stays_dry(static_root, tmp_path):
    doc = scenario.run_scenario(static_root, tmp_path / "runs", mode="forecast", duration_hours=24, fetch_forecast=_fake_forecast(rain_mm=0.0),
                                reservoir_snapshot=None, use_cache=False)
    assert doc["reservoir_coupling"]["status"] == "zero_inflow_missing_snapshot" and doc["forcing"]["inflow_cells_used"] == 0
    s = doc["summary"]
    assert s["flooded_area_km2"] == 0.0 and s["buildings_affected"] == 0 and s["max_depth_m"] < 0.01
