import json
from datetime import datetime

import pandas as pd
import pytest

from pipelines.trackb.metrics import TrackBMetrics
from pipelines.trackb.persistence import write_alert, write_reservoir_state
from pipelines.trackb.replay import replay_rows
from pipelines.trackb.streaming import (
    InvalidEvent,
    TrackBEventProcessor,
    make_replay_events,
    validate_event,
)


class FakeRedis:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, ex=None):
        self.values[key] = value

    def exists(self, key):
        return key in self.values


class FakeProducer:
    def __init__(self):
        self.events = []

    def send(self, event):
        validate_event(event)
        self.events.append(event)


class Cursor:
    def __init__(self, results=None):
        self.sql = []
        self.results = list(results or [])

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        self.sql.append((sql, params))

    def fetchone(self):
        return self.results.pop(0) if self.results else None


class Connection:
    def __init__(self, results=None):
        self.cur = Cursor(results)

    class Transaction:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def transaction(self):
        return self.Transaction()

    def cursor(self):
        return self.cur


def date_only_reservoir(**overrides):
    event = {
        'schema': 'trackb.reservoir_update.v1',
        'event_id': 'replay:POONDI:storage:2015-12-01:run:r1',
        'source_date': '2015-12-01',
        'time_precision': 'date',
        'observation_timezone': 'unknown',
        'observed_at': None,
        'received_at': '2026-10-28T12:00:00+05:30',
        'source': 'replay',
        'provenance': {'source_id': 'fixture', 'source_file': 'archive.zip', 'source_sha256': 'a' * 64,
                       'timezone_status': 'unknown; source provides date only', 'replay_run_id': 'r1'},
        'reservoir_key': 'POONDI',
        'storage_value': 3200.0,
        'storage_unit': 'mcft',
        'capacity_value': 3231.0,
        'capacity_unit': 'mcft',
        'release_value': None,
        'release_unit': 'cusecs',
        'rainfall_mm': None,
        'rain_3d_mm': None,
        'rise_1d_pct': None,
        'rise_3d_pct': None,
        'qc_flags': ['fixture-qc'],
    }
    event.update(overrides)
    return event


def test_source_replay_producer_emits_date_only_with_separate_received_at(tmp_path, monkeypatch):
    import pipelines.trackb.streaming as streaming

    archive = tmp_path / 'data/raw/reservoirs/kaggle_chennai_water_management/archive.zip'
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b'fixture archive digest input')
    frame = pd.DataFrame([{
        'date': pd.Timestamp('2015-12-01'), 'reservoir': 'POONDI',
        'rain_kaggle_raw': 2.5, 'storage_mcft': 3200.0, 'capacity_mcft': 3231.0,
        'rain_3d_mm': None, 'rise_1d_pct': None, 'rise_3d_pct': None,
    }])
    monkeypatch.setattr(streaming, 'load_observations', lambda _root: (frame, None, None))

    rain, reservoir = list(make_replay_events(tmp_path, '2015-12-01', '2015-12-01', 'r1'))
    for event in (rain, reservoir):
        validate_event(event)
        assert event['source_date'] == '2015-12-01'
        assert event['observed_at'] is None
        assert event['time_precision'] == 'date'
        assert event['observation_timezone'] == 'unknown'
        assert event['received_at'] != event['source_date']
        assert event['provenance']['timezone_status'].startswith('unknown')
        assert 'date_timezone' not in event['provenance']
    assert reservoir['rise_1d_pct'] is None and reservoir['rise_3d_pct'] is None


def test_date_only_flows_through_consumer_state_alert_and_idempotency():
    event = date_only_reservoir()
    producer = FakeProducer()
    redis = FakeRedis()
    state_calls = []
    processor = TrackBEventProcessor(
        redis, producer, {'POONDI': {'rise_1d_pct': 1, 'rise_3d_pct': 2,
                                     'rain_3d_p75_mm': 10, 'rain_3d_p90_mm': 20}},
        TrackBMetrics(), state_writer=state_calls.append,
    )

    assert processor.process(event) is True
    assert processor.process(event) is False
    state = json.loads(redis.values['trackb:reservoir:POONDI:state'])
    assert state['source_date'] == '2015-12-01'
    assert state['observed_at'] is None
    assert state['received_at'] == event['received_at']
    assert state['source'] == 'replay' and state['provenance'] == event['provenance']
    assert state['rise_1d_pct'] is None and state['rise_3d_pct'] is None and state['rain_3d_mm'] is None
    assert state['release_value'] is None and state['qc_flags'] == ['fixture-qc']
    assert len(state_calls) == 1

    assert len(producer.events) == 1
    alert = producer.events[0]
    assert alert['source_date'] == '2015-12-01'
    assert alert['time_precision'] == 'date'
    assert alert['observed_at'] is None
    assert alert['valid_from'] is None and alert['valid_to'] is None
    assert alert['received_at'] != event['received_at']
    assert alert['provenance'] == event['provenance']


def test_replay_alerts_keep_date_only_and_supplied_timestamp_offset(tmp_path):
    destination = tmp_path / 'alerts.jsonl'
    thresholds = {'POONDI': {'rise_1d_pct': 1, 'rise_3d_pct': 2,
                             'rain_3d_p75_mm': 10, 'rain_3d_p90_mm': 20}}
    rows = [
        {'source_date': '2015-12-01', 'time_precision': 'date', 'observation_timezone': 'unknown',
         'observed_at': None, 'reservoir_key': 'POONDI', 'storage_pct': 95,
         'rise_1d_pct': None, 'rise_3d_pct': None, 'rain_3d_mm': None,
         'provenance': {'source_id': 'date-fixture', 'timezone_status': 'unknown'}},
        {'source_date': '2015-12-01', 'time_precision': 'instant', 'observed_at': '2015-12-01T07:45:00+05:45',
         'reservoir_key': 'POONDI', 'storage_pct': 95, 'rise_1d_pct': None,
         'rise_3d_pct': None, 'rain_3d_mm': None,
         'provenance': {'source_id': 'timestamp-fixture'}},
    ]
    assert replay_rows(rows, destination, '2015-12-01', '2015-12-01', thresholds) == 2
    date_alert, instant_alert = [json.loads(line) for line in destination.read_text(encoding='utf-8').splitlines()]
    validate_event(date_alert)
    validate_event(instant_alert)
    assert date_alert['source_date'] == '2015-12-01' and date_alert['observed_at'] is None
    assert date_alert['valid_from'] is None and date_alert['valid_to'] is None
    assert date_alert['trigger_inputs']['rise_1d_pct'] is None
    assert instant_alert['observed_at'] == '2015-12-01T07:45:00+05:45'
    assert instant_alert['valid_from'] == '2015-12-01T07:45:00+05:45'
    assert instant_alert['valid_to'].endswith('+05:45')
    assert datetime.fromisoformat(instant_alert['valid_to']) - datetime.fromisoformat(instant_alert['valid_from']) == pd.Timedelta(days=1)


def test_persistence_uses_additive_date_keyed_tables_and_is_idempotent():
    event = date_only_reservoir()
    conn = Connection([('alert:POONDI:date:2015-12-01:rule:v1',), None])
    alert = {
        'event_id': 'alert:POONDI:date:2015-12-01:rule:v1', 'source_date': event['source_date'],
        'time_precision': 'date', 'observation_timezone': 'unknown', 'observed_at': None,
        'received_at': event['received_at'], 'valid_from': None, 'valid_to': None, 'source': 'replay',
        'provenance': event['provenance'], 'reservoir_key': 'POONDI', 'level': 'Critical',
    }
    assert write_alert(conn, alert) == alert['event_id']
    assert write_alert(conn, alert) is None
    assert 'trackb.date_only_alert_events' in conn.cur.sql[0][0]
    assert 'twin.alerts' not in conn.cur.sql[0][0]
    assert conn.cur.sql[0][1][1] == '2015-12-01'

    state_conn = Connection()
    write_reservoir_state(state_conn, 7, event)
    state_sql, state_params = state_conn.cur.sql[0]
    marker_sql, marker_params = state_conn.cur.sql[1]
    assert 'twin.trackb_reservoir_daily_observations' in state_sql
    assert 'ON CONFLICT(run_id,source_date,reservoir_key)' in state_sql
    assert 'observed_at' not in state_sql and state_params[1] == '2015-12-01'
    assert state_params[5] == event['received_at']
    assert state_params[6] is None
    assert 'twin.trackb_date_only_recompute_markers' in marker_sql
    assert marker_params[2] == '2015-12-01'


def test_date_only_validator_rejects_synthetic_midnight_and_bad_timezone():
    with pytest.raises(InvalidEvent, match='must not contain observed_at'):
        validate_event(date_only_reservoir(observed_at='2015-12-01T00:00:00+05:30'))
    with pytest.raises(InvalidEvent, match='timezone must be unknown'):
        validate_event(date_only_reservoir(observation_timezone='Asia/Kolkata'))
