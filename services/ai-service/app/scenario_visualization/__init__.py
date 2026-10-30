"""Internal, read-only access to the A20 scenario visualization manifest.

This package deliberately is not mounted by the AI FastAPI application. C9 is
still a proposal; an API router can be added only after explicit contract
approval and integration conformance review.
"""

from .repository import (
    InvalidScenarioSelector,
    ScenarioAssetNotFound,
    ScenarioAssetRepository,
    ScenarioAssetsUnavailable,
)

__all__ = [
    "InvalidScenarioSelector",
    "ScenarioAssetNotFound",
    "ScenarioAssetRepository",
    "ScenarioAssetsUnavailable",
]
