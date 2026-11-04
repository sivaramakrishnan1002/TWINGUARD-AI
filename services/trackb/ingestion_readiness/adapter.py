"""Typed, in-memory fixture adapter for offline ingestion behavior tests.

The adapter accepts an injected transport and clock. It has no configured endpoint,
credentials, persistence, route, or default transport. Tests should inject fixtures
and fake clocks/transports; this code does not establish production/live readiness.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Mapping, Protocol, TypeAlias


JsonValue: TypeAlias = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


class TemporalPrecision(str, Enum):
    DATE = "date"
    INSTANT = "instant"


class SourceMode(str, Enum):
    REPLAY = "REPLAY"
    SIMULATED = "SIMULATED"


class Missingness(str, Enum):
    PRESENT = "present"
    MISSING = "missing"
    NODATA = "nodata"
    UNAVAILABLE = "unavailable"


class AvailabilityState(str, Enum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"
    STALE = "stale"
    DELAYED = "delayed"
    MISSING = "missing"
    MALFORMED = "malformed"
    UNAVAILABLE = "unavailable"


class FreshnessState(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    DELAYED = "delayed"
    UNKNOWN = "unknown"


class MalformedEnvelope(ValueError):
    """An injected fixture does not meet the offline envelope contract."""


class TransientSourceError(Exception):
    """A fake/injected transport can raise this to exercise bounded retries."""


class SourceUnavailableError(Exception):
    """The injected source cannot provide the requested fixture."""


@dataclass(frozen=True)
class Provenance:
    source_id: str
    evidence_path: str
    sha256: str


@dataclass(frozen=True)
class ObservationEnvelope:
    schema: str
    event_id: str
    source_id: str
    source_mode: SourceMode
    time_precision: TemporalPrecision
    source_date: str | None
    observed_at: str | None
    observation_timezone: str | None
    received_at: str
    value: float | None
    unit: str | None
    spatial_coverage: Mapping[str, JsonValue] | None
    provenance: Provenance
    quality: tuple[str, ...]
    missingness: Missingness

    @classmethod
    def parse(cls, raw: Mapping[str, object]) -> "ObservationEnvelope":
        required = {
            "schema", "event_id", "source_id", "source_mode", "time_precision",
            "source_date", "observed_at", "observation_timezone", "received_at",
            "value", "unit", "spatial_coverage", "provenance", "quality", "missingness",
        }
        if set(raw) != required:
            raise MalformedEnvelope("envelope fields do not match the registered boundary")
        try:
            if raw["schema"] != "trackb.observation_envelope.v1":
                raise ValueError("unsupported schema")
            event_id = _nonempty(raw["event_id"], "event_id")
            source_id = _nonempty(raw["source_id"], "source_id")
            mode = SourceMode(raw["source_mode"])
            precision = TemporalPrecision(raw["time_precision"])
            source_date = raw["source_date"]
            observed_at = raw["observed_at"]
            observation_timezone = raw["observation_timezone"]
            received_at = _aware_timestamp(raw["received_at"], "received_at")
            if precision is TemporalPrecision.DATE:
                if not isinstance(source_date, str) or not _is_iso_date(source_date):
                    raise ValueError("date precision requires ISO source_date")
                if observed_at is not None or observation_timezone != "unknown":
                    raise ValueError("date-only source time and timezone must remain unknown")
            else:
                if source_date is not None and (not isinstance(source_date, str) or not _is_iso_date(source_date)):
                    raise ValueError("source_date must be an ISO calendar date when supplied")
                observed_at = _aware_timestamp(observed_at, "observed_at")
                if source_date is not None and datetime.fromisoformat(observed_at.replace("Z", "+00:00")).date().isoformat() != source_date:
                    raise ValueError("source_date must match the calendar date in observed_at's supplied offset")
                if observation_timezone is not None and not isinstance(observation_timezone, str):
                    raise ValueError("observation_timezone must be a source-supplied string or null")
            if not isinstance(raw["value"], (int, float)) and raw["value"] is not None:
                raise ValueError("value must be numeric or null")
            value = None if raw["value"] is None else float(raw["value"])
            if value is not None and not math.isfinite(value):
                raise ValueError("value must be finite")
            unit = raw["unit"]
            if unit is not None and (not isinstance(unit, str) or not unit.strip()):
                raise ValueError("unit must be a non-empty string or null")
            coverage = raw["spatial_coverage"]
            if coverage is not None and not isinstance(coverage, dict):
                raise ValueError("spatial_coverage must be an object or null")
            provenance_raw = raw["provenance"]
            if not isinstance(provenance_raw, dict) or set(provenance_raw) != {"source_id", "evidence_path", "sha256"}:
                raise ValueError("provenance must include source_id, evidence_path, and sha256")
            provenance = Provenance(
                source_id=_nonempty(provenance_raw["source_id"], "provenance.source_id"),
                evidence_path=_nonempty(provenance_raw["evidence_path"], "provenance.evidence_path"),
                sha256=_sha256(provenance_raw["sha256"]),
            )
            if provenance.source_id != source_id:
                raise ValueError("provenance source_id must match envelope source_id")
            quality_raw = raw["quality"]
            if not isinstance(quality_raw, list) or any(not isinstance(flag, str) or not flag for flag in quality_raw):
                raise ValueError("quality must be an array of non-empty strings")
            missingness = Missingness(raw["missingness"])
            if missingness is Missingness.PRESENT and value is None:
                raise ValueError("present value cannot be null")
            if missingness is not Missingness.PRESENT and value is not None:
                raise ValueError("missing, NoData, and unavailable values must remain null")
            return cls(
                schema="trackb.observation_envelope.v1", event_id=event_id, source_id=source_id,
                source_mode=mode, time_precision=precision, source_date=source_date,
                observed_at=observed_at, observation_timezone=observation_timezone,
                received_at=received_at, value=value, unit=unit, spatial_coverage=coverage,
                provenance=provenance, quality=tuple(quality_raw), missingness=missingness,
            )
        except MalformedEnvelope:
            raise
        except Exception as exc:
            raise MalformedEnvelope(str(exc)) from None

    def idempotency_hash(self) -> str:
        """Hash source event identity/content; received_at is processing metadata."""
        identity = {
            "schema": self.schema,
            "event_id": self.event_id,
            "source_id": self.source_id,
            "source_mode": self.source_mode.value,
            "time_precision": self.time_precision.value,
            "source_date": self.source_date,
            "observed_at": self.observed_at,
            "observation_timezone": self.observation_timezone,
            "value": self.value,
            "unit": self.unit,
            "spatial_coverage": self.spatial_coverage,
            "provenance": {
                "source_id": self.provenance.source_id,
                "evidence_path": self.provenance.evidence_path,
                "sha256": self.provenance.sha256,
            },
            "quality": list(self.quality),
            "missingness": self.missingness.value,
        }
        encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class AdapterResult:
    state: AvailabilityState
    freshness: FreshnessState
    attempts: int
    envelope: ObservationEnvelope | None = None
    detail: str | None = None


class FixtureTransport(Protocol):
    """Injection boundary. Production network clients are intentionally absent."""

    def fetch(self, event_id: str) -> Mapping[str, object] | None: ...


class FixtureOnlyIngestionAdapter:
    """Classify and deduplicate injected fixture observations in process memory."""

    def __init__(self, clock: Callable[[], datetime]):
        self._clock = clock
        self._accepted: dict[str, str] = {}

    @property
    def accepted_event_count(self) -> int:
        return len(self._accepted)

    def ingest(
        self,
        event_id: str,
        transport: FixtureTransport,
        *,
        stale_after_seconds: float,
        delayed_after_seconds: float | None = None,
        max_attempts: int = 3,
    ) -> AdapterResult:
        if stale_after_seconds < 0 or (delayed_after_seconds is not None and delayed_after_seconds < 0):
            raise ValueError("freshness thresholds must be non-negative")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least one")
        raw: Mapping[str, object] | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                raw = transport.fetch(event_id)
                break
            except TransientSourceError:
                if attempt == max_attempts:
                    return AdapterResult(AvailabilityState.UNAVAILABLE, FreshnessState.UNKNOWN, attempt, detail="retry limit exhausted")
            except SourceUnavailableError:
                return AdapterResult(AvailabilityState.UNAVAILABLE, FreshnessState.UNKNOWN, attempt, detail="fixture unavailable")
            except Exception:
                return AdapterResult(AvailabilityState.UNAVAILABLE, FreshnessState.UNKNOWN, attempt, detail="injected transport failed")
        attempts = attempt
        if raw is None:
            return AdapterResult(AvailabilityState.MISSING, FreshnessState.UNKNOWN, attempts, detail="no fixture record")
        try:
            envelope = ObservationEnvelope.parse(raw)
            if envelope.event_id != event_id:
                raise MalformedEnvelope("fixture event_id does not match requested identity")
        except MalformedEnvelope:
            return AdapterResult(AvailabilityState.MALFORMED, FreshnessState.UNKNOWN, attempts, detail="fixture envelope is invalid")
        freshness = self._freshness(envelope, stale_after_seconds, delayed_after_seconds)
        if freshness is FreshnessState.STALE:
            return AdapterResult(AvailabilityState.STALE, freshness, attempts, envelope, "source observation exceeded the caller-supplied freshness threshold")
        if freshness is FreshnessState.DELAYED:
            return AdapterResult(AvailabilityState.DELAYED, freshness, attempts, envelope, "receipt exceeded the caller-supplied delay threshold")
        fingerprint = envelope.idempotency_hash()
        previous = self._accepted.get(event_id)
        if previous is not None:
            if previous == fingerprint:
                return AdapterResult(AvailabilityState.DUPLICATE, freshness, attempts, envelope, "identical event already accepted")
            return AdapterResult(AvailabilityState.CONFLICT, freshness, attempts, envelope, "event_id already accepted with different source content")
        self._accepted[event_id] = fingerprint
        return AdapterResult(AvailabilityState.ACCEPTED, freshness, attempts, envelope)

    def _freshness(
        self,
        envelope: ObservationEnvelope,
        stale_after_seconds: float,
        delayed_after_seconds: float | None,
    ) -> FreshnessState:
        if envelope.time_precision is TemporalPrecision.DATE:
            # received_at is never substituted for the unknown source observation time.
            return FreshnessState.UNKNOWN
        try:
            observed = datetime.fromisoformat(envelope.observed_at.replace("Z", "+00:00"))
            received = datetime.fromisoformat(envelope.received_at.replace("Z", "+00:00"))
            now = self._clock()
            if now.tzinfo is None:
                return FreshnessState.UNKNOWN
            age_seconds = (now.astimezone(timezone.utc) - observed.astimezone(timezone.utc)).total_seconds()
            if age_seconds < 0:
                return FreshnessState.UNKNOWN
            if age_seconds > stale_after_seconds:
                return FreshnessState.STALE
            if delayed_after_seconds is not None:
                delay_seconds = (received.astimezone(timezone.utc) - observed.astimezone(timezone.utc)).total_seconds()
                if delay_seconds > delayed_after_seconds:
                    return FreshnessState.DELAYED
            return FreshnessState.FRESH
        except Exception:
            return FreshnessState.UNKNOWN


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _aware_timestamp(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must retain its supplied ISO-8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must contain an explicit UTC offset")
    return value


def _is_iso_date(value: str) -> bool:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat() == value
    except ValueError:
        return False


def _sha256(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[a-f0-9]{64}", value) is None:
        raise ValueError("provenance.sha256 must be a lowercase SHA-256 digest")
    return value
