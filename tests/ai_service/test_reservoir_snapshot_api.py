import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT / "services" / "ai-service", ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from app.main import app  # noqa: E402
from app.reservoir_snapshot import router as reservoir_router  # noqa: E402
from services.trackb.connectors.tn_reservoir.client import (  # noqa: E402
    CfmSourceError,
    DailyReservoirSnapshot,
    ReservoirHistory,
)


def _history(kind="daily"):
    rows = [
        DailyReservoirSnapshot(
            reservoir_id="Po001",
            reservoir_name="Poondi",
            source_date="2026-11-06" if kind == "daily" else "2026-11-01",
            observed_at=None,
            observation_timezone="unknown",
            time_precision="date",
            water_level_m=38.6894,
            average_storage_mcm=16.5085,
            received_at="2026-11-06T09:00:00Z",
            source_mode="LIVE",
            availability="available",
            freshness="unknown",
            freshness_note="Cadence unknown.",
            provenance={
                "source_id": "tn_cfm_dss_public_lakes_dashboard",
                "endpoint": "/Master/GetLast15daysWaterLevel"
                if kind == "daily"
                else "/Master/GetMonthlyWaterLevelOfReservoir",
                "response_sha256": "a" * 64,
            },
        )
    ]
    return ReservoirHistory(
        history_kind=kind,
        source_id="tn_cfm_dss_public_lakes_dashboard",
        received_at=datetime(2026, 11, 6, 9, tzinfo=timezone.utc).isoformat(),
        availability="available",
        freshness="unknown",
        records=tuple(rows),
    )


def test_daily_snapshot_is_explicit_date_only_and_not_cached(monkeypatch):
    class FakeClient:
        calls = 0

        def __init__(self, **kwargs):
            assert kwargs["timeout_seconds"] == 15.0

        def fetch_daily_history(self):
            self.calls += 1
            return _history()

        def fetch_monthly_history(self):
            raise AssertionError("monthly endpoint should not be called")

    fake = FakeClient(timeout_seconds=15.0)
    monkeypatch.setattr(reservoir_router, "CfmDashboardClient", lambda **kw: fake)
    response = TestClient(app).get("/reservoirs/history")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["source_mode"] == "LIVE"
    assert body["freshness"] == "unknown"
    assert body["records"][0]["source_date"] == "2026-11-06"
    assert body["records"][0]["observed_at"] is None
    assert body["records"][0]["observation_timezone"] == "unknown"
    assert body["records"][0]["provenance"]["response_sha256"] == "a" * 64
    assert fake.calls == 1


def test_monthly_snapshot_selects_monthly_connector_method(monkeypatch):
    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["timeout_seconds"] == 15.0

        def fetch_daily_history(self):
            raise AssertionError("daily endpoint should not be called")

        def fetch_monthly_history(self):
            return _history("monthly")

    monkeypatch.setattr(reservoir_router, "CfmDashboardClient", FakeClient)
    response = TestClient(app).get("/reservoirs/history?period=monthly")
    assert response.status_code == 200
    assert response.json()["history_kind"] == "monthly"
    assert response.json()["records"][0]["source_date"] == "2026-11-01"


def test_upstream_failure_is_generic_and_never_exposes_exception(monkeypatch):
    class FakeClient:
        def fetch_daily_history(self):
            raise CfmSourceError("token=secret raw body leak")

    monkeypatch.setattr(reservoir_router, "CfmDashboardClient", FakeClient)
    response = TestClient(app).get("/reservoirs/history")
    assert response.status_code == 503
    assert response.json() == {
        "detail": "Reservoir source is unavailable or returned invalid data."
    }
    assert "secret" not in response.text
    assert "raw body" not in response.text


def test_invalid_period_is_rejected_before_source_access(monkeypatch):
    def fail_if_called(**kwargs):
        raise AssertionError("invalid query must not access upstream")

    monkeypatch.setattr(reservoir_router, "CfmDashboardClient", fail_if_called)
    response = TestClient(app).get("/reservoirs/history?period=hourly")
    assert response.status_code == 422


def test_origin_cors_is_narrow_and_credentials_are_disabled():
    client = TestClient(app)
    allowed = client.options(
        "/reservoirs/history",
        headers={
            "Origin": "http://127.0.0.1:8081",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "accept",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:8081"
    assert "access-control-allow-credentials" not in allowed.headers
    denied = client.options(
        "/reservoirs/history",
        headers={
            "Origin": "https://example.invalid",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "accept",
        },
    )
    assert denied.status_code == 400
