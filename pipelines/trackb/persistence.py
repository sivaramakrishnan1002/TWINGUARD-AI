"""Idempotent persistence helpers for Track B, using an injected psycopg connection."""
from __future__ import annotations
import json

SEVERITY = {'Normal':'INFO','Watch':'WATCH','Warning':'WARNING','Critical':'EMERGENCY'}

def write_alert(conn,event:dict) -> int | None:
    """Persist an alert to trackb.alert_events and twin.alerts exactly once.

    Caller owns the connection lifecycle. Migration 100 must already be applied.
    Returns twin.alerts.alert_id, or None when this event_id was already stored.
    """
    if event.get('source') not in {'replay','live','simulated'}:
        raise ValueError('source must be replay, live, or simulated')
    if event.get('level') not in SEVERITY:
        raise ValueError('unknown Track B alert level')
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO trackb.alert_events(event_id,source,observed_at,payload)
                   VALUES (%s,%s,%s,%s::jsonb) ON CONFLICT(event_id) DO NOTHING
                   RETURNING event_id""",
                (event['event_id'],event['source'],event['observed_at'],json.dumps(event)),
            )
            if cur.fetchone() is None:
                return None
            cur.execute(
                """INSERT INTO twin.alerts(alert_type,severity,issued_at,valid_from,valid_to_exclusive,payload,provenance)
                   VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb) RETURNING alert_id""",
                ('TRACKB_STORAGE_EARLY_WARNING',SEVERITY[event['level']],event['received_at'],
                 event['valid_from'],event['valid_to'],json.dumps(event),
                 json.dumps({'source':event['source'],'provenance':event.get('provenance',{})})),
            )
            alert_id=cur.fetchone()[0]
            cur.execute(
                """INSERT INTO twin.trackb_alert_links(event_key,alert_id,source)
                   VALUES (%s,%s,%s) ON CONFLICT(event_key) DO NOTHING""",
                (event['event_id'],alert_id,event['source']),
            )
            return int(alert_id)


def write_reservoir_state(conn,run_id:int,event:dict) -> None:
    """Upsert one accepted reservoir observation and queue its twin recompute marker."""
    if event.get('source') not in {'replay','live','simulated'}:
        raise ValueError('source must be replay, live, or simulated')
    key=event['reservoir_key']; valid_at=event['observed_at']
    state={'event_id':event['event_id'],'source':event['source'],'provenance':event.get('provenance',{})}
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO twin.reservoir_state
                   (run_id,valid_at,reservoir_key,rainfall_mm,storage_mcft,capacity_mcft,release_cusecs,qc_flags,provenance)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
                   ON CONFLICT(run_id,valid_at,reservoir_key) DO UPDATE SET
                   rainfall_mm=EXCLUDED.rainfall_mm,storage_mcft=EXCLUDED.storage_mcft,
                   capacity_mcft=EXCLUDED.capacity_mcft,release_cusecs=EXCLUDED.release_cusecs,
                   qc_flags=EXCLUDED.qc_flags,provenance=EXCLUDED.provenance""",
                (run_id,valid_at,key,event.get('rainfall_mm'),event.get('storage_value'),
                 event.get('capacity_value'),event.get('release_value'),json.dumps(event.get('qc_flags',[])),json.dumps(state)),
            )
            cur.execute(
                """INSERT INTO twin.trackb_recompute_markers(marker_key,reservoir_key,valid_at,source,payload)
                   VALUES (%s,%s,%s,%s,%s::jsonb) ON CONFLICT(marker_key) DO NOTHING""",
                ('trackb:'+event['event_id'],key,valid_at,event['source'],json.dumps(state)),
            )
