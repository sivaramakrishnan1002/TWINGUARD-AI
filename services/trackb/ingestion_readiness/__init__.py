"""Fixture-only ingestion boundary; this package has no live connector."""

from .adapter import (
    AdapterResult,
    AvailabilityState,
    FixtureOnlyIngestionAdapter,
    FreshnessState,
    Missingness,
    SourceMode,
    TemporalPrecision,
)

__all__ = [
    "AdapterResult",
    "AvailabilityState",
    "FixtureOnlyIngestionAdapter",
    "FreshnessState",
    "Missingness",
    "SourceMode",
    "TemporalPrecision",
]
