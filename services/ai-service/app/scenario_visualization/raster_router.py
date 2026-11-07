"""CR-010 read-only delivery of exact A20 scenario GeoTIFF bytes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse

from .raster_repository import ScenarioRasterRepository
from .repository import (
    InvalidScenarioSelector,
    ScenarioAssetNotFound,
    ScenarioAssetsUnavailable,
    ScenarioIdentityConflict,
)


router = APIRouter()


def get_scenario_raster_repository() -> ScenarioRasterRepository:
    return ScenarioRasterRepository()


def _problem(status: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "detail": detail})


@router.get(
    "/scenario-visualization-assets/{event_id}/{scenario_id}/raster",
    operation_id="getScenarioVisualizationRaster",
    response_class=Response,
    response_model=None,
    responses={
        200: {"description": "Exact original GeoTIFF bytes.", "content": {"image/tiff": {"schema": {"type": "string", "format": "binary"}}}},
        400: {"description": "Invalid selector; no raster bytes are returned."},
        404: {"description": "No exact saved event/scenario/time/band match exists."},
        409: {"description": "Duplicate or ambiguous identity; no raster bytes are returned."},
        503: {"description": "Manifest or asset is unavailable or fails integrity validation; no partial body is returned."},
        501: {"description": "Reserved unavailable response; runtime activation is governed by B23/B24."},
    },
)
def get_scenario_visualization_raster(
    event_id: str,
    scenario_id: str,
    request: Request,
    valid_time_utc: str | None = Query(default=None),
    band: str | None = Query(default=None),
    repository: ScenarioRasterRepository = Depends(get_scenario_raster_repository),
) -> Response | JSONResponse:
    if set(request.query_params.keys()) != {"valid_time_utc", "band"}:
        return _problem(400, "INVALID_SCENARIO_SELECTOR", "Exact valid_time_utc and band selectors are required.")
    if any(len(request.query_params.getlist(name)) != 1 for name in ("valid_time_utc", "band")):
        return _problem(400, "INVALID_SCENARIO_SELECTOR", "Duplicate query selectors are not accepted.")
    content_length = request.headers.get("content-length", "0")
    if (content_length.isdigit() and int(content_length) > 0) or request.headers.get("transfer-encoding"):
        return _problem(400, "INVALID_SCENARIO_SELECTOR", "Request bodies are not accepted.")
    if valid_time_utc is None or band is None:
        return _problem(400, "INVALID_SCENARIO_SELECTOR", "Exact valid_time_utc and band selectors are required.")
    try:
        payload, reference = repository.read(event_id, scenario_id, valid_time_utc, band)
        # The complete bounded file has been read and verified before Response
        # construction; streaming cannot emit a valid-prefix on a later error.
        return Response(
            content=payload,
            media_type="image/tiff",
            headers={"ETag": f'"{reference["sha256"]}"'},
        )
    except InvalidScenarioSelector:
        return _problem(400, "INVALID_SCENARIO_SELECTOR", "The raster selector is invalid.")
    except ScenarioAssetNotFound:
        return _problem(404, "SCENARIO_ASSET_NOT_FOUND", "No exact saved raster was found.")
    except ScenarioIdentityConflict:
        return _problem(409, "SCENARIO_IDENTITY_CONFLICT", "Scenario identity is duplicated or ambiguous.")
    except ScenarioAssetsUnavailable:
        return _problem(503, "SCENARIO_VISUALIZATION_UNAVAILABLE", "The saved raster is unavailable.")
