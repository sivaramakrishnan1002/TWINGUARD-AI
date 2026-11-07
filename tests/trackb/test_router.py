from fastapi import FastAPI
from fastapi.testclient import TestClient
from services.trackb.router import configure_reader, router

class Reader:
    def current_reservoir_states(self): return [{"name": "Poondi", "source": "replay"}]
    def recent_alerts(self, limit): return [{"limit": limit, "source": "replay"}]
    def alert_timeline(self, start, end): return [{"start": start, "end": end, "source": "replay"}]
    def backtest_summary(self): return {"status": "exploratory"}
    def rule_parameters(self): return {"horizon_days": 7}

def test_read_only_routes_and_validation():
    configure_reader(Reader())
    app = FastAPI(); app.include_router(router); client = TestClient(app)
    assert client.get('/trackb/reservoirs/current').json()['states'][0]['source'] == 'replay'
    assert client.get('/trackb/alerts/recent?limit=3').json()['alerts'][0]['limit'] == 3
    assert client.get('/trackb/alerts/timeline?start=2020-02-01&end=2020-01-01').status_code == 422
    assert client.get('/trackb/alerts/timeline?start=bad&end=2020-01-01').status_code == 422
    assert client.get('/trackb/backtest/summary').json()['status'] == 'exploratory'
    assert client.get('/trackb/rules/parameters').status_code == 200


def test_date_only_api_rows_preserve_null_time_and_reject_synthetic_instants():
    class DateOnlyReader(Reader):
        def current_reservoir_states(self):
            return [{"source": "replay", "source_date": "2015-12-01", "time_precision": "date",
                     "observation_timezone": "unknown", "observed_at": None,
                     "received_at": "2026-10-28T12:00:00+05:30", "storage_mcft": 100.0}]

    configure_reader(DateOnlyReader())
    app = FastAPI(); app.include_router(router); client = TestClient(app)
    row = client.get('/trackb/reservoirs/current').json()['states'][0]
    assert row['source_date'] == '2015-12-01' and row['observed_at'] is None
    assert row['received_at'] == '2026-10-28T12:00:00+05:30'

    class InvalidDateOnlyReader(DateOnlyReader):
        def current_reservoir_states(self):
            return [{"source": "replay", "source_date": "2015-12-01", "time_precision": "date",
                     "observation_timezone": "unknown", "observed_at": "2015-12-01T00:00:00+05:30"}]

    configure_reader(InvalidDateOnlyReader())
    assert client.get('/trackb/reservoirs/current').status_code == 502
