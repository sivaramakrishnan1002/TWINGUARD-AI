"""Approved CR-009 read-only catalog/detail routes for saved A20 assets."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from .repository import (
    InvalidScenarioSelector,
    ScenarioAssetNotFound,
    ScenarioAssetRepository,
    ScenarioAssetsUnavailable,
    ScenarioIdentityConflict,
)


class _C9Response(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0.0"]
    artifact_version: Literal["batch2_v1"]
    status: Literal["DERIVED_ASSUMPTION_BASED_RESEARCH_SCENARIO"]
    grid: dict[str, Any]
    depth_units: dict[str, Any]
    nodata: dict[str, Any]
    provenance: dict[str, Any]
    limitations: list[str]
    presentation_policy: str
    time_basis: dict[str, Any]


class ScenarioVisualizationCatalog(_C9Response):
    scenario_series: list[dict[str, Any]]
    context_layers: list[dict[str, Any]]


class ScenarioVisualizationAsset(_C9Response):
    series: dict[str, Any]


router = APIRouter()


def get_scenario_asset_repository() -> ScenarioAssetRepository:
    # A new repository per request avoids serving stale or partially cached files.
    return ScenarioAssetRepository()


def _problem(status_code: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"code": code, "detail": detail})


def _validate_no_query_input(request: Request) -> JSONResponse | None:
    content_length = request.headers.get("content-length", "0")
    if request.query_params or content_length.isdigit() and int(content_length) > 0:
        return _problem(400, "INVALID_SCENARIO_SELECTOR", "This operation accepts no query or body input.")
    return None


@router.get(
    "/scenario-visualization-assets",
    operation_id="listScenarioVisualizationAssets",
    response_model=ScenarioVisualizationCatalog,
    responses={
        400: {"description": "Unexpected input is not accepted."},
        409: {"description": "A duplicate or ambiguous identity exists; no catalog is returned."},
        503: {"description": "Manifest or referenced asset is unavailable; no partial catalog is returned."},
        501: {"description": "Reserved unavailable response; this approved operation is mounted."},
    },
)
def list_scenario_visualization_assets(
    request: Request,
    repository: ScenarioAssetRepository = Depends(get_scenario_asset_repository),
) -> ScenarioVisualizationCatalog | JSONResponse:
    invalid = _validate_no_query_input(request)
    if invalid:
        return invalid
    try:
        return repository.catalog()
    except ScenarioIdentityConflict:
        return _problem(409, "SCENARIO_IDENTITY_CONFLICT", "Scenario identity is duplicated or ambiguous.")
    except ScenarioAssetsUnavailable:
        return _problem(503, "SCENARIO_VISUALIZATION_UNAVAILABLE", "Scenario assets are unavailable.")


@router.get(
    "/scenario-visualization-assets/{event_id}/{scenario_id}",
    operation_id="getScenarioVisualizationAsset",
    response_model=ScenarioVisualizationAsset,
    responses={
        400: {"description": "Invalid event_id or scenario_id selector."},
        404: {"description": "No exact event/scenario identity exists."},
        409: {"description": "A duplicate or ambiguous identity exists; no detail is returned."},
        503: {"description": "Manifest or referenced asset is unavailable; no partial detail is returned."},
        501: {"description": "Reserved unavailable response; this approved operation is mounted."},
    },
)
def get_scenario_visualization_asset(
    event_id: str,
    scenario_id: str,
    request: Request,
    repository: ScenarioAssetRepository = Depends(get_scenario_asset_repository),
) -> ScenarioVisualizationAsset | JSONResponse:
    invalid = _validate_no_query_input(request)
    if invalid:
        return invalid
    try:
        return repository.asset(event_id, scenario_id)
    except InvalidScenarioSelector:
        return _problem(400, "INVALID_SCENARIO_SELECTOR", "event_id or scenario_id is invalid.")
    except ScenarioAssetNotFound:
        return _problem(404, "SCENARIO_ASSET_NOT_FOUND", "No exact saved scenario asset was found.")
    except ScenarioIdentityConflict:
        return _problem(409, "SCENARIO_IDENTITY_CONFLICT", "Scenario identity is duplicated or ambiguous.")
    except ScenarioAssetsUnavailable:
        return _problem(503, "SCENARIO_VISUALIZATION_UNAVAILABLE", "Scenario assets are unavailable.")
