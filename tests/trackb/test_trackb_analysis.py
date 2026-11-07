import numpy as np
import pandas as pd

from pipelines.trackb.analysis import confusion, future_target, bootstrap_ci
from pipelines.trackb.persistence import write_alert, write_reservoir_state
from pipelines.trackb.replay import replay_rows


def test_future_storage_target_excludes_current_day_and_censors_tail():
    frame = pd.DataFrame({'storage_pct': [69., 70., 80., 69., 70., 69., 90.]})
    target = future_target(frame, horizon=2, fraction=.8)
    assert target.iloc[0] == True
    assert target.iloc[1] == True
    assert target.iloc[2] == False
    assert target.iloc[3] == False
    assert target.iloc[4] == True
    assert pd.isna(target.iloc[5])
    assert pd.isna(target.iloc[6])


def test_confusion_metrics_use_standard_definitions_and_empty_denominators():
    result = confusion(np.array([True, True, False]), np.array([True, False, True]))
    assert result == {'tp': 1, 'fp': 1, 'fn': 1, 'tn': 0,
                      'pod': 0.5, 'false_alarm_ratio': 0.5, 'csi': 1/3}
    empty = confusion(np.array([False, False]), np.array([False, False]))
    assert empty['pod'] is None and empty['false_alarm_ratio'] is None and empty['csi'] is None


def test_year_block_bootstrap_is_seeded_and_bounded():
    y = np.array([True, False, True, False])
    pred = np.array([True, True, False, False])
    dates = pd.Series(pd.to_datetime(['2018-01-01','2018-01-02','2019-01-01','2019-01-02']))
    a = bootstrap_ci(y, pred, dates, bootstrap_reps=20, seed=7)
    b = bootstrap_ci(y, pred, dates, bootstrap_reps=20, seed=7)
    assert a == b
    assert all(0 <= x <= 1 for bounds in a.values() for x in bounds)


class Cursor:
    def __init__(self):
        self.sql = []
        self.fetchone_values = [("event-1",), (91,)]
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, params): self.sql.append((sql, params))
    def fetchone(self): return self.fetchone_values.pop(0) if self.fetchone_values else None


class Connection:
    def __init__(self): self.cur = Cursor(); self.tx = 0
    class Transaction:
        def __init__(self, owner): self.owner=owner
        def __enter__(self): self.owner.tx += 1
        def __exit__(self, *args): return False
    def transaction(self): return self.Transaction(self)
    def cursor(self): return self.cur


def test_alert_persistence_is_idempotent_and_maps_critical_to_emergency():
    conn=Connection()
    event={'event_id':'event-1','source':'replay','observed_at':'2015-12-01T00:00:00+00:00',
           'received_at':'2026-10-25T00:00:00+05:30','valid_from':'2015-12-01T00:00:00+00:00',
           'valid_to':'2015-12-02T00:00:00+00:00','level':'Critical','provenance':{}}
    assert write_alert(conn,event)==91
    assert 'ON CONFLICT(event_id) DO NOTHING' in conn.cur.sql[0][0]
    assert conn.cur.sql[1][1][1]=='EMERGENCY'
    assert write_alert(conn,event) is None


def test_state_persistence_keeps_missing_release_null_and_queues_marker():
    conn=Connection()
    event={'event_id':'res-1','source':'replay','observed_at':'2015-12-01T00:00:00+00:00',
           'reservoir_key':'POONDI','storage_value':100.,'capacity_value':3231.,'release_value':None}
    write_reservoir_state(conn,7,event)
    state_sql, state_params=conn.cur.sql[0]
    assert 'ON CONFLICT(run_id,valid_at,reservoir_key) DO UPDATE' in state_sql
    assert state_params[6] is None
    assert state_params[2]=='poondi'
    assert 'ON CONFLICT(marker_key) DO NOTHING' in conn.cur.sql[1][0]


def test_offline_replay_emits_versioned_source_labeled_alert(tmp_path):
    source=tmp_path/'input.jsonl'; destination=tmp_path/'alerts.jsonl'
    source.write_text('{"observed_at":"2015-12-01T00:00:00+00:00","reservoir_key":"POONDI",'
                      '"storage_pct":95,"rise_1d_pct":1,"rise_3d_pct":2,"rain_3d_mm":40}\n',encoding='utf8')
    thresholds={'POONDI':{'rise_1d_pct':.1,'rise_3d_pct':.2,'rain_3d_p75_mm':10,'rain_3d_p90_mm':20}}
    assert replay_rows([__import__('json').loads(source.read_text(encoding='utf8'))],destination,'2015-12-01','2015-12-02',thresholds)==1
    event=__import__('json').loads(destination.read_text(encoding='utf8'))
    assert event['schema']=='trackb.alert.v1' and event['source']=='replay'
    assert event['level']=='Critical' and event['valid_to']>'2015-12-01T00:00:00'
