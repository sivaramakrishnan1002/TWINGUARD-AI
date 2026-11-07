"""Explicitly enabled B20 PostgreSQL integration test for the isolated DB only."""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get('TRACKB_B20_PG_TEST') != '1',
    reason='set TRACKB_B20_PG_TEST=1 and TRACKB_B20_DATABASE=twinguard_trackb_test to enable isolated PostgreSQL writes',
)

EXPECTED_DATABASE = 'twinguard_trackb_test'
EXPECTED_OWNER = 'twinguard_app'
MIGRATIONS = (
    '001_core_schema.sql',
    '005_stage5_complementary_tables.sql',
    '010_create_twin_schema.sql',
    '100_trackb_twin_link.sql',
    '101_trackb_date_only_reservoir_observations.sql',
)


def _connect_verified():
    if os.environ.get('TRACKB_B20_DATABASE') != EXPECTED_DATABASE:
        pytest.fail('B20 requires an explicit allowlisted TRACKB_B20_DATABASE target')

    from pipelines.stage5.db_common import read_env
    import psycopg

    values = read_env()
    # POSTGRES_DB is deliberately ignored; only the explicit B20 allowlist is used.
    conn = psycopg.connect(
        host=values.get('POSTGRES_HOST') or 'localhost',
        port=int(values.get('POSTGRES_PORT') or '5432'),
        dbname=EXPECTED_DATABASE,
        user=values['POSTGRES_USER'],
        password=values['POSTGRES_PASSWORD'],
        connect_timeout=5,
        application_name='trackb-b20-isolated-test',
    )
    try:
        conn.execute('SET TRANSACTION READ ONLY')
        identity = conn.execute(
            """SELECT current_database(), current_user, pg_get_userbyid(d.datdba), d.datistemplate
               FROM pg_database d WHERE d.datname=current_database()"""
        ).fetchone()
        if identity != (EXPECTED_DATABASE, EXPECTED_OWNER, EXPECTED_OWNER, False):
            pytest.fail('B20 PostgreSQL identity is not the allowlisted isolated test database/owner')

        ledger = dict(conn.execute(
            'SELECT version,checksum_sha256 FROM twinguard.schema_migrations'
        ).fetchall())
        for filename in MIGRATIONS:
            source = Path('database/migrations') / filename
            digest = hashlib.sha256(source.read_text(encoding='utf-8').encode('utf-8')).hexdigest()
            if ledger.get(filename) != digest:
                pytest.fail(f'B20 migration ledger mismatch or missing entry: {filename}')

        required_relations = (
            'twin.reservoir_state', 'twin.alerts', 'twin.trackb_recompute_markers',
            'twin.trackb_reservoir_daily_observations', 'twin.trackb_date_only_recompute_markers',
            'trackb.alert_events', 'trackb.date_only_alert_events',
        )
        for relation in required_relations:
            if conn.execute('SELECT to_regclass(%s) IS NOT NULL', (relation,)).fetchone()[0] is not True:
                pytest.fail('B20 required persistence relation is absent')

        replay_run = conn.execute(
            "SELECT run_id FROM twin.state_runs WHERE run_kind='REPLAY' ORDER BY run_id LIMIT 1"
        ).fetchone()
        if replay_run is None:
            pytest.fail('B20 isolated test database has no existing replay run for the FK fixture')
        existing_timestamped = conn.execute(
            """SELECT run_id,valid_at,reservoir_key,rainfall_mm,storage_mcft,capacity_mcft,
                      release_cusecs,qc_flags,provenance
               FROM twin.reservoir_state
               WHERE provenance->>'event_id' NOT LIKE 'b20-test:%'
               ORDER BY run_id,valid_at,reservoir_key LIMIT 1"""
        ).fetchone()
        if existing_timestamped is None:
            pytest.fail('B20 test database has no pre-existing timestamped state row for compatibility readback')

        # Migration 010/100 timestamp semantics must still be required on their
        # original tables after the additive date-keyed migration.
        not_null_checks = {
            ('twin', 'reservoir_state', 'valid_at'),
            ('twin', 'alerts', 'valid_from'),
            ('twin', 'alerts', 'valid_to_exclusive'),
            ('trackb', 'alert_events', 'observed_at'),
            ('twin', 'trackb_recompute_markers', 'valid_at'),
        }
        nullable = conn.execute(
            """SELECT table_schema,table_name,column_name,is_nullable
               FROM information_schema.columns
               WHERE (table_schema,table_name,column_name) IN (
                 ('twin','reservoir_state','valid_at'),('twin','alerts','valid_from'),
                 ('twin','alerts','valid_to_exclusive'),('trackb','alert_events','observed_at'),
                 ('twin','trackb_recompute_markers','valid_at'))"""
        ).fetchall()
        if {(s, t, c) for s, t, c, null in nullable if null == 'NO'} != not_null_checks:
            pytest.fail('B20 existing timestamp columns changed nullability')

        conn.commit()  # End the read-only identity/schema preflight transaction.
        return conn, int(replay_run[0]), existing_timestamped
    except Exception:
        conn.close()
        raise


def test_isolated_postgres_date_only_and_timestamped_persistence_roundtrip():
    from pipelines.trackb.persistence import write_alert, write_reservoir_state

    conn, run_id, existing_timestamped = _connect_verified()
    try:
        fixture_id = uuid4().hex
        received = datetime.now(timezone.utc).isoformat()
        date_event_id = f'b20-test:{fixture_id}:date-only:poondi:1900-01-01'
        date_marker = 'trackb:' + date_event_id
        date_source = {
            'source_id': 'B20 isolated fixture',
            'source_file': 'B20 fixture; not historical source evidence',
            'source_sha256': 'b' * 64,
            'timezone_status': 'unknown; fixture is date-only',
        }
        date_event = {
            'event_id': date_event_id, 'source': 'replay', 'time_precision': 'date',
            'source_date': '1900-01-01', 'observed_at': None, 'observation_timezone': 'unknown',
            'received_at': received, 'reservoir_key': 'POONDI', 'rainfall_mm': None,
            'storage_value': 123.5, 'capacity_value': None, 'release_value': None,
            'qc_flags': ['b20-fixture'], 'provenance': date_source,
        }
        date_alert = {
            'event_id': f'b20-test:{fixture_id}:date-alert:poondi:1900-01-01', 'source': 'replay',
            'time_precision': 'date', 'source_date': '1900-01-01', 'observed_at': None,
            'observation_timezone': 'unknown', 'received_at': received, 'valid_from': None,
            'valid_to': None, 'reservoir_key': 'POONDI', 'level': 'Watch',
            'provenance': date_source,
        }

        write_reservoir_state(conn, run_id, date_event)
        write_reservoir_state(conn, run_id, date_event)  # intentional idempotency replay
        state = conn.execute(
            """SELECT source_date::text,observed_at,observation_timezone,received_at,source,
                      rainfall_mm,storage_mcft,capacity_mcft,release_cusecs,qc_flags,provenance
               FROM twin.trackb_reservoir_daily_observations
               WHERE run_id=%s AND source_date=DATE '1900-01-01' AND reservoir_key='poondi'""",
            (run_id,),
        ).fetchone()
        assert state is not None
        (source_date_read, observed_at, observation_timezone, received_at, source,
         rainfall, storage, capacity, release, qc_flags, provenance) = state
        assert source_date_read == '1900-01-01'
        assert observed_at is None and observation_timezone == 'unknown'
        assert received_at == datetime.fromisoformat(received)
        assert received_at.tzinfo is not None
        assert source == 'replay'
        assert rainfall is None and capacity is None and release is None and storage == 123.5
        assert qc_flags == ['b20-fixture']
        assert provenance['source_date'] == '1900-01-01'
        assert provenance['observed_at'] is None and provenance['observation_timezone'] == 'unknown'
        assert provenance['received_at'] == received
        assert provenance['source'] == 'replay' and provenance['provenance'] == date_source

        write_alert(conn, date_alert)
        assert write_alert(conn, date_alert) is None
        alert_count = conn.execute(
            "SELECT count(*) FROM trackb.date_only_alert_events WHERE event_id=%s",
            (date_alert['event_id'],),
        ).fetchone()[0]
        alert = conn.execute(
            """SELECT source_date::text,received_at,source,payload,provenance
               FROM trackb.date_only_alert_events WHERE event_id=%s""",
            (date_alert['event_id'],),
        ).fetchone()
        assert alert_count == 1 and alert is not None
        alert_date, alert_received, alert_source, payload, alert_provenance = alert
        assert alert_date == '1900-01-01' and alert_received == datetime.fromisoformat(received)
        assert alert_source == 'replay'
        assert payload['source_date'] == '1900-01-01' and payload['observed_at'] is None
        assert payload['valid_from'] is None and payload['valid_to'] is None
        assert payload['received_at'] == received
        assert alert_provenance['source'] == 'replay' and alert_provenance['provenance'] == date_source

        marker_count = conn.execute(
            "SELECT count(*) FROM twin.trackb_date_only_recompute_markers WHERE marker_key=%s",
            (date_marker,),
        ).fetchone()[0]
        state_count = conn.execute(
            """SELECT count(*) FROM twin.trackb_reservoir_daily_observations
               WHERE run_id=%s AND source_date=DATE '1900-01-01' AND reservoir_key='poondi'""",
            (run_id,),
        ).fetchone()[0]
        assert marker_count == 1 and state_count == 1

        # A real offset-bearing timestamp still follows the pre-existing tables.
        instant = datetime.now(timezone(timedelta(hours=5, minutes=45))).replace(microsecond=0).isoformat()
        instant_received = datetime.now(timezone.utc).isoformat()
        instant_id = f'b20-test:{fixture_id}:instant:poondi:{instant}'
        instant_event = {
            'event_id': instant_id, 'source': 'replay', 'time_precision': 'instant',
            'source_date': instant[:10], 'observed_at': instant, 'received_at': instant_received,
            'reservoir_key': 'POONDI', 'rainfall_mm': 1.25, 'storage_value': 456.0,
            'capacity_value': None, 'release_value': None, 'qc_flags': ['b20-instant-fixture'],
            'provenance': {'source_id': 'B20 timestamped fixture', 'supplied_offset': '+05:45'},
        }
        write_reservoir_state(conn, run_id, instant_event)
        write_reservoir_state(conn, run_id, instant_event)
        instant_row = conn.execute(
            """SELECT valid_at,storage_mcft,qc_flags,provenance
               FROM twin.reservoir_state
               WHERE run_id=%s AND valid_at=%s AND reservoir_key='poondi'""",
            (run_id, instant),
        ).fetchone()
        assert instant_row is not None
        valid_at, instant_storage, instant_qc, instant_provenance = instant_row
        assert valid_at == datetime.fromisoformat(instant).astimezone(timezone.utc)
        assert instant_provenance['source_date'] == instant[:10]
        assert instant_storage == 456.0 and instant_qc == ['b20-instant-fixture']
        assert instant_provenance['observed_at'] == instant  # original offset retained in JSONB
        assert instant_provenance['received_at'] == instant_received
        assert instant_provenance['source'] == 'replay'

        existing_key = existing_timestamped[:3]
        unchanged_existing = conn.execute(
            """SELECT run_id,valid_at,reservoir_key,rainfall_mm,storage_mcft,capacity_mcft,
                      release_cusecs,qc_flags,provenance
               FROM twin.reservoir_state
               WHERE run_id=%s AND valid_at=%s AND reservoir_key=%s""",
            existing_key,
        ).fetchone()
        assert unchanged_existing == existing_timestamped

        instant_marker_count = conn.execute(
            "SELECT count(*) FROM twin.trackb_recompute_markers WHERE marker_key=%s",
            ('trackb:' + instant_id,),
        ).fetchone()[0]
        assert instant_marker_count == 1
        conn.commit()
    finally:
        conn.close()
