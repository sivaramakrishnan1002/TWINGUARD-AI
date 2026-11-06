import hashlib
import json
from datetime import datetime, timezone

import pytest

from services.trackb.connectors.tn_reservoir.client import (
    CfmDashboardClient,
    CfmSourceError,
    DAILY_PATH,
    DASHBOARD_PATH,
    MONTHLY_PATH,
    SOURCE_ID,
)


class FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self.body = body


class FakeSession:
    def __init__(self, bodies):
        self.bodies = bodies
        self.calls = []

    def get(self, url, *, headers=None, timeout):
        self.calls.append((url, dict(headers or {}), timeout))
        route = url.split(".gov.in", 1)[-1]
        body, status = self.bodies[route]
        return FakeResponse(status, body)


def _wire_payload(rows):
    # The dashboard currently double-encodes its JSON array in the response.
    return json.dumps(json.dumps(rows, separators=(",", ":"))).encode()


def _daily_rows():
    rows = []
    names = ["Po001", "TNCH-07-T0726", "RD001", "Cho001", "TK-001"]
    for day in range(6, 0, -1):
        for tank in names:
            rows.append({
                "tankid": tank,
                "date": f"2026-11-0{day}T00:00:00",
                "average_waterlevel": 38.68,
                "average_storage": 16.50,
            })
    return rows


def _client(route=DAILY_PATH, rows=None, *, status=200, token="ephemeral-test-token"):
    page = f"<html><script>token = '{token}';</script></html>".encode()
    payload = _wire_payload(_daily_rows() if rows is None else rows)
    session = FakeSession({
        DASHBOARD_PATH: (page, 200),
        route: (payload, status),
    })
    clock = lambda: datetime(2026, 11, 6, 12, 30, tzinfo=timezone.utc)
    return CfmDashboardClient(session, clock=clock), session, payload


def test_daily_fetch_keeps_calendar_date_unknown_time_and_provenance():
    client, session, payload = _client()
    result = client.fetch_daily_history()

    assert result.history_kind == "daily"
    assert result.source_id == SOURCE_ID
    assert len(result.records) == 30
    poondi = next(r for r in result.records if r.reservoir_id == "Po001")
    assert poondi.source_date == "2026-11-06"
    assert poondi.observed_at is None
    assert poondi.observation_timezone == "unknown"
    assert poondi.time_precision == "date"
    assert poondi.water_level_m == 38.68
    assert poondi.average_storage_mcm == 16.50
    assert poondi.received_at == "2026-11-06T12:30:00Z"
    assert poondi.source_mode == "LIVE"
    assert poondi.freshness == "unknown"
    assert poondi.provenance["response_sha256"] == hashlib.sha256(payload).hexdigest()
    assert len(session.calls) == 2
    assert session.calls[0][0].endswith(DASHBOARD_PATH)
    assert session.calls[1][0].endswith(DAILY_PATH)
    assert session.calls[1][1] == {"RequestVerificationToken": "ephemeral-test-token"}
    assert "ephemeral-test-token" not in json.dumps(result.to_dict())


def test_monthly_route_uses_month_labels_and_no_observation_instant():
    rows = [{
        "tankid": "Po001",
        "monthly": "2026-11-01T00:00:00",
        "average_waterlevel": 38.6868,
        "average_storage": 16.4668,
    }]
    client, _, _ = _client(MONTHLY_PATH, rows)
    result = client.fetch_monthly_history()
    assert result.history_kind == "monthly"
    assert result.records[0].source_date == "2026-11-01"
    assert result.records[0].observed_at is None


@pytest.mark.parametrize("label", ["2026-11-06T06:00:00", "2026-11-06T00:00:00Z", "not-a-date"])
def test_refuses_to_infer_time_semantics_if_source_label_changes(label):
    rows = [{
        "tankid": "Po001", "date": label,
        "average_waterlevel": 38.68, "average_storage": 16.5,
    }]
    client, _, _ = _client(rows=rows)
    with pytest.raises(CfmSourceError, match="date label"):
        client.fetch_daily_history()


def test_missing_public_page_token_fails_closed():
    client, _, _ = _client(token="")
    with pytest.raises(CfmSourceError, match="did not provide a request token"):
        client.fetch_daily_history()


def test_http_forbidden_is_reported_without_retry_or_login():
    client, session, _ = _client(status=403)
    with pytest.raises(CfmSourceError, match="HTTP 403"):
        client.fetch_daily_history()
    assert len(session.calls) == 2


def test_duplicate_identity_unknown_tank_and_nonfinite_values_rejected():
    row = {
        "tankid": "Po001", "date": "2026-11-06T00:00:00",
        "average_waterlevel": 38.68, "average_storage": 16.5,
    }
    duplicate_client, _, _ = _client(rows=[row, row])
    with pytest.raises(CfmSourceError, match="duplicate"):
        duplicate_client.fetch_daily_history()

    unknown_client, _, _ = _client(rows=[{**row, "tankid": "UNKNOWN"}])
    with pytest.raises(CfmSourceError, match="unknown reservoir"):
        unknown_client.fetch_daily_history()

    invalid_client, _, _ = _client(rows=[{**row, "average_storage": float("nan")}])
    with pytest.raises(CfmSourceError, match="finite non-negative"):
        invalid_client.fetch_daily_history()


def test_unexpected_schema_fails_closed():
    rows = [{"tankid": "Po001", "date": "2026-11-06T00:00:00"}]
    client, _, _ = _client(rows=rows)
    with pytest.raises(CfmSourceError, match="schema"):
        client.fetch_daily_history()
