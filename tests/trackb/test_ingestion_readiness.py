"""B35 offline ingestion tests. All transport and time are injected fakes."""

import ast
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pytest

from services.trackb.ingestion_readiness.adapter import (
    AvailabilityState,
    FixtureOnlyIngestionAdapter,
    FreshnessState,
    Missingness,
    SourceUnavailableError,
    TransientSourceError,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "services/trackb/ingestion_readiness/fixtures"
NOW = datetime.fromisoformat("2026-11-04T10:10:00+05:30")


class FakeClock:
    def __init__(self, now=NOW):
        self.now = now

    def __call__(self):
        return self.now


class FakeTransport:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = 0

    def fetch(self, event_id):
        self.calls += 1
        response = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(response, Exception):
            raise response
        return deepcopy(response)


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def adapter(clock=None):
    return FixtureOnlyIngestionAdapter(clock or FakeClock())


def test_timestamped_fixture_retains_original_offset_and_provenance():
    raw = fixture("timestamped_rain_simulated.json")
    result = adapter().ingest(raw["event_id"], FakeTransport(raw), stale_after_seconds=600)
    assert result.state is AvailabilityState.ACCEPTED
    assert result.freshness is FreshnessState.FRESH
    assert result.envelope.observed_at == "2026-11-04T10:00:00+05:30"
    assert result.envelope.received_at == "2026-11-04T10:05:00+05:30"
    assert result.envelope.provenance.sha256 == raw["provenance"]["sha256"]
    assert result.envelope.source_mode.value == "SIMULATED"


def test_date_only_replay_preserves_c3_unknown_time_and_separate_receipt():
    raw = fixture("date_only_poondi_replay.json")
    result = adapter().ingest(raw["event_id"], FakeTransport(raw), stale_after_seconds=1)
    assert result.state is AvailabilityState.ACCEPTED
    assert result.freshness is FreshnessState.UNKNOWN
    assert result.envelope.source_date == "2015-12-01"
    assert result.envelope.observed_at is None
    assert result.envelope.observation_timezone == "unknown"
    assert result.envelope.received_at == raw["received_at"]
    assert result.envelope.received_at != result.envelope.source_date


def test_stale_boundary_uses_caller_threshold_and_is_strictly_greater():
    raw = fixture("timestamped_rain_simulated.json")
    # Observed at 10:00 and fake now 10:10: exactly 600 seconds is fresh.
    at_boundary = adapter().ingest(raw["event_id"], FakeTransport(raw), stale_after_seconds=600)
    assert at_boundary.state is AvailabilityState.ACCEPTED
    assert at_boundary.freshness is FreshnessState.FRESH
    after_boundary = adapter().ingest(raw["event_id"], FakeTransport(raw), stale_after_seconds=599)
    assert after_boundary.state is AvailabilityState.STALE
    assert after_boundary.freshness is FreshnessState.STALE
    assert adapter().accepted_event_count == 0


def test_delayed_input_is_separate_from_staleness():
    raw = fixture("timestamped_rain_simulated.json")
    result = adapter().ingest(raw["event_id"], FakeTransport(raw), stale_after_seconds=900, delayed_after_seconds=240)
    assert result.state is AvailabilityState.DELAYED
    assert result.freshness is FreshnessState.DELAYED
    assert result.attempts == 1


def test_identical_replay_is_idempotent_even_when_received_at_changes():
    raw = fixture("date_only_poondi_replay.json")
    worker = adapter()
    first = worker.ingest(raw["event_id"], FakeTransport(raw), stale_after_seconds=1)
    duplicate_raw = dict(raw, received_at="2026-11-04T10:06:00+05:30")
    duplicate = worker.ingest(raw["event_id"], FakeTransport(duplicate_raw), stale_after_seconds=1)
    assert first.state is AvailabilityState.ACCEPTED
    assert duplicate.state is AvailabilityState.DUPLICATE
    assert worker.accepted_event_count == 1


def test_conflicting_duplicate_fails_closed_without_second_side_effect():
    raw = fixture("timestamped_rain_simulated.json")
    worker = adapter()
    assert worker.ingest(raw["event_id"], FakeTransport(raw), stale_after_seconds=600).state is AvailabilityState.ACCEPTED
    conflict = dict(raw, value=99.0)
    result = worker.ingest(raw["event_id"], FakeTransport(conflict), stale_after_seconds=600)
    assert result.state is AvailabilityState.CONFLICT
    assert worker.accepted_event_count == 1


@pytest.mark.parametrize("missingness", [Missingness.MISSING.value, Missingness.NODATA.value, Missingness.UNAVAILABLE.value])
def test_null_missing_nodata_and_unavailable_values_remain_null(missingness):
    raw = fixture("timestamped_rain_simulated.json")
    raw.update(value=None, missingness=missingness)
    result = adapter().ingest(raw["event_id"], FakeTransport(raw), stale_after_seconds=600)
    assert result.state is AvailabilityState.ACCEPTED
    assert result.envelope.value is None
    assert result.envelope.missingness.value == missingness


def test_malformed_date_only_midnight_or_validity_fields_are_rejected():
    raw = fixture("date_only_poondi_replay.json")
    raw["observed_at"] = "2015-12-01T00:00:00+05:30"
    result = adapter().ingest(raw["event_id"], FakeTransport(raw), stale_after_seconds=600)
    assert result.state is AvailabilityState.MALFORMED
    raw = fixture("date_only_poondi_replay.json")
    raw["valid_from"] = "2015-12-01T00:00:00+05:30"
    assert adapter().ingest(raw["event_id"], FakeTransport(raw), stale_after_seconds=600).state is AvailabilityState.MALFORMED


def test_missing_and_unavailable_inputs_have_distinct_states():
    raw = fixture("timestamped_rain_simulated.json")
    missing = adapter().ingest(raw["event_id"], FakeTransport(None), stale_after_seconds=600)
    unavailable = adapter().ingest(raw["event_id"], FakeTransport(SourceUnavailableError()), stale_after_seconds=600)
    assert missing.state is AvailabilityState.MISSING
    assert unavailable.state is AvailabilityState.UNAVAILABLE
    assert unavailable.attempts == 1


def test_transient_retry_is_bounded_and_accepts_once_after_recovery():
    raw = fixture("timestamped_rain_simulated.json")
    worker = adapter()
    transport = FakeTransport(TransientSourceError(), TransientSourceError(), raw)
    result = worker.ingest(raw["event_id"], transport, stale_after_seconds=600, max_attempts=3)
    assert result.state is AvailabilityState.ACCEPTED
    assert result.attempts == transport.calls == 3
    assert worker.accepted_event_count == 1
    exhausted = worker.ingest(raw["event_id"], FakeTransport(TransientSourceError()), stale_after_seconds=600, max_attempts=2)
    assert exhausted.state is AvailabilityState.UNAVAILABLE
    assert exhausted.attempts == 2


def test_live_mode_is_rejected_and_code_has_no_network_or_persistence_clients():
    raw = fixture("timestamped_rain_simulated.json")
    raw["source_mode"] = "LIVE"
    assert adapter().ingest(raw["event_id"], FakeTransport(raw), stale_after_seconds=600).state is AvailabilityState.MALFORMED
    source = (ROOT / "services/trackb/ingestion_readiness/adapter.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or "").split(".")[0])
    assert not imports.intersection({"requests", "httpx", "urllib", "socket", "psycopg", "redis", "confluent_kafka"})
    assert "https://" not in source and "postgresql://" not in source
