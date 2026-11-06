"""Read-only connector for the public Chennai Flood Monitoring reservoir dashboard."""

from .client import (
    CfmDashboardClient,
    CfmSourceError,
    DailyReservoirSnapshot,
    ReservoirHistory,
)

__all__ = [
    "CfmDashboardClient",
    "CfmSourceError",
    "DailyReservoirSnapshot",
    "ReservoirHistory",
]
