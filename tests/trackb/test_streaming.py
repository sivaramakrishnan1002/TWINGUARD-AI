import json
from concurrent.futures import Future
from types import SimpleNamespace
from urllib.request import urlopen

import pytest

from pipelines.trackb.metrics import TrackBMetrics
from pipelines.trackb.streaming import (
    DEAD_LETTER_TOPIC,
    TOPIC_SPECS,
    InvalidEvent,
    KafkaJSONProducer,
    TrackBEventProcessor,
    consumer_config,
    ensure_topics,
    process_message,
    topic_for_event,
    update_consumer_lag,
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

    def delete(self, key):
        return self.values.pop(key, None) is not None


class FakeKafkaProducer:
    def __init__(self, order=None, fail_delivery=False):
        self.records = []
        self.callbacks = []
        self.order = order if order is not None else []
        self.fail_delivery = fail_delivery

    def produce(self, topic, key, value, on_delivery=None):
        self.records.append((topic, key, value))
        if on_delivery:
            self.callbacks.append(on_delivery)

    def poll(self, timeout):
        return 0

    def flush(self, timeout):
        while self.callbacks:
            self.callbacks.pop(0)(RuntimeError('fixture delivery failure') if self.fail_delivery else None, None)
        self.order.append('flush')
        return 0


class FakeMessage:
    def __init__(self, topic, value, key=b'POONDI'):
        self._topic, self._value, self._key = topic, value, key

    def error(self):
        return None

    def topic(self):
        return self._topic

    def value(self):
        return self._value

    def key(self):
        return self._key


class FakeConsumer:
    def __init__(self, order=None):
        self.commits = []
        self.order = order if order is not None else []

    def commit(self, message, asynchronous):
        self.commits.append((message, asynchronous))
        self.order.append('commit')


def reservoir_event(**overrides):
    event = {
        'schema': 'trackb.reservoir_update.v1',
        'event_id': 'replay:POONDI:storage:2015-12-01',
        'observed_at': '2015-12-01T00:00:00+05:30',
        'received_at': '2026-10-25T00:00:00+05:30',
        'source': 'replay',
        'provenance': {'source_id': 'fixture'},
        'reservoir_key': 'POONDI',
        'storage_value': 3200.0,
        'storage_unit': 'mcft',
        'capacity_value': 3231.0,
        'capacity_unit': 'mcft',
        'release_value': None,
        'release_unit': 'cusecs',
        'rainfall_mm': 30.0,
        'rain_3d_mm': 60.0,
        'rise_1d_pct': 3.0,
        'rise_3d_pct': 5.0,
        'qc_flags': [],
    }
    event.update(overrides)
    return event


def test_event_validation_routes_schema_and_rejects_nonfinite_values():
    event = reservoir_event()
    validate_event(event)
    assert topic_for_event(event) == 'trackb.reservoir.v1'
    with pytest.raises(InvalidEvent, match='finite'):
        validate_event(reservoir_event(storage_value=float('nan')))
    with pytest.raises(InvalidEvent, match='timezone'):
        validate_event(reservoir_event(observed_at='2015-12-01T00:00:00'))


def test_consumer_can_isolate_a_fresh_replay_group_without_changing_defaults():
    default = consumer_config('localhost:9092')
    assert default['group.id'] == 'trackb-rule-engine'
    assert default['auto.offset.reset'] == 'earliest'
    assert default['enable.auto.commit'] is False
    isolated = consumer_config('localhost:9092', 'trackb-b9-replay', 'latest')
    assert isolated['group.id'] == 'trackb-b9-replay'
    assert isolated['auto.offset.reset'] == 'latest'
    with pytest.raises(ValueError, match='auto_offset_reset'):
        consumer_config('localhost:9092', 'trackb-b9-replay', 'unsafe')


def test_lag_probe_uses_cached_watermarks_and_skips_invalid_uninitialized_positions():
    metrics = TrackBMetrics()

    class Consumer:
        def __init__(self, offset):
            self.offset = offset
            self.cached_flags = []

        def assignment(self):
            return [SimpleNamespace(topic='trackb.rain.v1', partition=0)]

        def get_watermark_offsets(self, assignment, cached=False, timeout=None):
            self.cached_flags.append(cached)
            return (0, 12)

        def position(self, assignments):
            return [SimpleNamespace(offset=self.offset)]

    invalid = Consumer(-1001)
    update_consumer_lag(invalid, metrics)
    assert invalid.cached_flags == [True]
    assert 'trackb_consumer_lag{' not in metrics.exposition().decode()
    valid = Consumer(9)
    update_consumer_lag(valid, metrics)
    exposition = metrics.exposition().decode()
    assert valid.cached_flags == [True]
    assert 'trackb_consumer_lag{group="trackb-rule-engine",topic="trackb.rain.v1"} 3.0' in exposition


def test_failed_alert_delivery_clears_dedupe_marker_and_never_commits_offset():
    raw = json.dumps(reservoir_event()).encode()
    redis = FakeRedis()
    fake_producer = FakeKafkaProducer(fail_delivery=True)
    producer = KafkaJSONProducer(fake_producer)
    metrics = TrackBMetrics()
    processor = TrackBEventProcessor(
        redis, producer, {'POONDI': {'rise_1d_pct': 1, 'rise_3d_pct': 2,
                                    'rain_3d_p75_mm': 10, 'rain_3d_p90_mm': 20}}, metrics,
    )
    consumer = FakeConsumer()
    message = FakeMessage('trackb.reservoir.v1', raw)
    with pytest.raises(RuntimeError, match='delivery'):
        process_message(message, consumer, producer, processor, metrics)
    assert not consumer.commits
    assert not redis.exists('trackb:processed:' + reservoir_event()['event_id'])
    assert 'trackb_rule_engine_errors_total{kind="delivery"} 1.0' in metrics.exposition().decode()


def test_topic_setup_is_idempotent_and_checks_partition_retention():
    class Admin:
        def __init__(self):
            self.topics = {}
            self.creates = 0

        def list_topics(self, timeout):
            return SimpleNamespace(topics=self.topics)

        def create_topics(self, specs, operation_timeout):
            self.creates += 1
            for spec in specs:
                self.topics[spec.topic] = SimpleNamespace(
                    partitions={i: object() for i in range(spec.num_partitions)}
                )
            futures = {}
            for spec in specs:
                future = Future()
                future.set_result(None)
                futures[spec.topic] = future
            return futures

        def describe_configs(self, resources, request_timeout):
            futures = {}
            retention = {spec.name: str(spec.retention_days * 86400 * 1000) for spec in TOPIC_SPECS}
            for resource in resources:
                future = Future()
                future.set_result({'retention.ms': SimpleNamespace(value=retention[resource.name])})
                futures[resource] = future
            return futures

    admin = Admin()
    ensure_topics(admin)
    ensure_topics(admin)
    assert admin.creates == 1
    assert len(admin.topics) == len(TOPIC_SPECS)


def test_consumer_updates_redis_and_commits_after_alert_delivery():
    order = []
    fake_producer = FakeKafkaProducer(order)
    producer = KafkaJSONProducer(fake_producer)
    redis = FakeRedis()
    metrics = TrackBMetrics()
    persisted_alerts, persisted_states = {}, []
    processor = TrackBEventProcessor(
        redis, producer, {'POONDI': {'rise_1d_pct': 1, 'rise_3d_pct': 2,
                                    'rain_3d_p75_mm': 10, 'rain_3d_p90_mm': 20}},
        metrics, alert_writer=lambda event: persisted_alerts.setdefault(event['event_id'], event),
        state_writer=persisted_states.append,
    )
    consumer = FakeConsumer(order)
    raw = json.dumps(reservoir_event()).encode()
    message = FakeMessage('trackb.reservoir.v1', raw)

    assert process_message(message, consumer, producer, processor, metrics)
    assert len(consumer.commits) == 1
    assert order.index('flush') < order.index('commit')
    assert redis.values['trackb:alert:POONDI:current']
    assert json.loads(redis.values['trackb:alert:POONDI:current'])['level'] == 'Critical'
    assert redis.values['trackb:reservoir:POONDI:state']
    assert persisted_states == [json.loads(raw)]
    assert len(persisted_alerts) == 1
    assert fake_producer.records[0][0] == 'trackb.alerts.v1'
    emitted = json.loads(fake_producer.records[0][2])
    assert emitted['source'] == 'replay' and emitted['schema'] == 'trackb.alert.v1'
    assert process_message(FakeMessage('trackb.alerts.v1', fake_producer.records[0][2]),
                           consumer, producer, processor, metrics)
    exposition = metrics.exposition().decode()
    assert 'trackb_messages_processed_total{source="replay",topic="trackb.reservoir.v1"} 1.0' in exposition
    assert 'trackb_alerts_total{level="Critical",source="replay"} 1.0' in exposition

    # Redelivery after restart is suppressed by the durable Redis idempotency key.
    assert not process_message(message, consumer, producer, processor, metrics)
    assert len(persisted_alerts) == 1


def test_invalid_record_is_metadata_only_dlq_and_committed_after_flush():
    order = []
    fake_producer = FakeKafkaProducer(order)
    producer = KafkaJSONProducer(fake_producer)
    consumer = FakeConsumer(order)
    metrics = TrackBMetrics()
    processor = TrackBEventProcessor(FakeRedis(), producer, {}, metrics)
    raw = b'{"private_payload":"must-not-be-copied"'

    assert not process_message(FakeMessage('trackb.rain.v1', raw), consumer, producer, processor, metrics)
    assert fake_producer.records[0][0] == DEAD_LETTER_TOPIC
    dlq = fake_producer.records[0][2]
    assert b'must-not-be-copied' not in dlq
    decoded = json.loads(dlq)
    assert decoded['error_kind'] == 'invalid_json'
    assert decoded['payload_sha256']
    assert 'trackb_rule_engine_errors_total{kind="invalid_json"} 1.0' in metrics.exposition().decode()
    assert order.index('flush') < order.index('commit')
    assert len(consumer.commits) == 1


def test_prometheus_metrics_exposition_covers_all_required_series():
    metrics = TrackBMetrics()
    metrics.record_message('trackb.rain.v1', 'replay')
    metrics.record_message('trackb.rain.v1', 'replay')
    metrics.record_alert('Warning', 'replay')
    metrics.observe_latency('replay', 0.125)
    metrics.set_consumer_lag('trackb-rule-engine', 'trackb.rain.v1', 3)
    metrics.record_rule_error('invalid_json')

    exposition = metrics.exposition().decode('utf-8')
    assert 'trackb_messages_processed_total{source="replay",topic="trackb.rain.v1"} 2.0' in exposition
    assert 'trackb_alerts_total{level="Warning",source="replay"} 1.0' in exposition
    assert 'trackb_e2e_latency_seconds_bucket' in exposition
    assert 'trackb_consumer_lag{group="trackb-rule-engine",topic="trackb.rain.v1"} 3.0' in exposition
    assert 'trackb_rule_engine_errors_total{kind="invalid_json"} 1.0' in exposition


def test_metrics_labels_are_bounded_and_unknown_errors_are_collapsed():
    metrics = TrackBMetrics()
    with pytest.raises(ValueError, match='topic'):
        metrics.record_message('reservoir:' + 'x' * 1000, 'replay')
    with pytest.raises(ValueError, match='source'):
        metrics.record_alert('Warning', 'run-id-with-unbounded-values')
    with pytest.raises(ValueError, match='latency'):
        metrics.observe_latency('replay', float('nan'))
    with pytest.raises(ValueError, match='group'):
        metrics.set_consumer_lag('group-' + 'x' * 500, 'trackb.rain.v1', 1)
    metrics.record_rule_error('exception-instance-123456')
    assert 'trackb_rule_engine_errors_total{kind="other"} 1.0' in metrics.exposition().decode()
    assert 'exception-instance-123456' not in metrics.exposition().decode()


def test_replay_run_id_is_embedded_in_event_identity_and_provenance(tmp_path, monkeypatch):
    import pandas as pd
    import pipelines.trackb.streaming as streaming

    archive = tmp_path / 'data/raw/reservoirs/kaggle_chennai_water_management/archive.zip'
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b'fixture source fingerprint')
    frame = pd.DataFrame([{
        'date': pd.Timestamp('2015-12-01'), 'reservoir': 'POONDI',
        'rain_kaggle_raw': 1.0, 'storage_mcft': 100.0, 'capacity_mcft': 3231.0,
        'rain_3d_mm': 3.0, 'rise_1d_pct': 1.0, 'rise_3d_pct': 2.0,
    }])
    monkeypatch.setattr(streaming, 'load_observations', lambda _root: (frame, None, None))
    events = list(streaming.make_replay_events(tmp_path, '2015-12-01', '2015-12-01', 'run-abc'))
    assert len(events) == 2
    assert all(e['source'] == 'replay' for e in events)
    assert all(e['provenance']['replay_run_id'] == 'run-abc' for e in events)
    assert all(':run:run-abc' in e['event_id'] for e in events)


def test_producer_counts_delivery_acknowledgements_and_raises_on_failed_ack():
    fake = FakeKafkaProducer()
    producer = KafkaJSONProducer(fake)
    event = reservoir_event()
    producer.send(event)
    producer.flush()
    assert producer.delivered_count == 1

    failed = FakeKafkaProducer(fail_delivery=True)
    failed_producer = KafkaJSONProducer(failed)
    failed_producer.send(event)
    with pytest.raises(RuntimeError, match='delivery'):
        failed_producer.flush()
    assert failed_producer.delivered_count == 0


def test_metrics_endpoint_serves_prometheus_format_on_loopback():
    metrics = TrackBMetrics()
    metrics.record_message('trackb.twin.v1', 'simulated')
    with pytest.raises(ValueError, match='loopback'):
        metrics.serve(port=0, address='0.0.0.0')
    server, thread = metrics.serve(port=0)
    try:
        assert server.server_address[0] == '127.0.0.1'
        with urlopen(f'http://127.0.0.1:{server.server_port}/metrics', timeout=3) as response:
            body = response.read().decode('utf-8')
            assert response.status == 200
            assert metrics.content_type.split(';')[0] in response.headers.get('Content-Type', '')
            assert 'trackb_messages_processed_total' in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
