"""FastAPI scaffold for TwinGuard AI."""

from datetime import datetime
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.database import get_layer_records


class Health(BaseModel):
    status: Literal["ok"]
    service: str
    database: Literal["ok", "unavailable", "not_checked"]


class Layer(BaseModel):
    layer_key: str
    source_layer: str
    target_srid: int
    loaded_row_count: int = Field(ge=0)


class ForecastRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    event_key: str
    issued_at: datetime
    horizon_hours: int = Field(ge=1)
    step_minutes: int = Field(ge=1)
    input_source_ids: list[str] | None = None


class RunTimeRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    run_id: int
    valid_at: datetime
    zone_ids: list[str] | None = None


class RouteRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    run_id: int
    departure_at: datetime
    origin: str
    destination: str
    mode: Literal["vehicle", "walking"] | None = None
    minimum_accessibility_probability: float | None = Field(default=None, ge=0, le=1)


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    scenario_key: str
    base_run_id: int
    parameters: dict[str, Any]


app = FastAPI(
    title="TwinGuard AI Service",
    version="0.1.0",
    description="Scaffold following the TwinGuard AI service contract.",
)


@app.get("/health", operation_id="health", response_model=Health)
def health() -> Health:
    return Health(status="ok", service="twinguard-ai-service", database="not_checked")


@app.get(
    "/layers",
    operation_id="listLayers",
    response_model=list[Layer],
    responses={503: {"description": "Required read-only data service unavailable"}},
)
def layers() -> list[dict[str, object]]:
    # Do not return driver messages: they can contain connection information.
    try:
        return get_layer_records()
    except Exception:
        raise HTTPException(status_code=503, detail="Layer catalogue is unavailable.") from None


def _not_implemented(feature: str) -> None:
    raise HTTPException(status_code=501, detail=f"Not implemented yet: {feature}.")


@app.post("/forecast", operation_id="createForecast", status_code=202, response_model=None)
def forecast(request: ForecastRequest) -> None:
    _not_implemented("forecast")


@app.post(
    "/uncertainty",
    operation_id="summarizeUncertainty",
    response_model=None,
    responses={404: {"description": "Run or requested time not found"}},
)
def uncertainty(request: RunTimeRequest) -> None:
    _not_implemented("uncertainty")


@app.post("/impact", operation_id="estimateImpact", response_model=None)
def impact(request: RunTimeRequest) -> None:
    _not_implemented("impact")


@app.post("/route", operation_id="planRoute", response_model=None)
def route(request: RouteRequest) -> None:
    _not_implemented("route")


@app.post("/scenario", operation_id="createScenario", status_code=202, response_model=None)
def scenario(request: ScenarioRequest) -> None:
    _not_implemented("scenario")


_default_openapi = app.openapi


def _openapi_schema():
    schema = _default_openapi()
    for path in ("/forecast", "/uncertainty", "/impact", "/route", "/scenario"):
        schema["paths"][path]["post"].setdefault("responses", {})["501"] = {
            "description": "Feature not implemented yet",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"detail": {"type": "string"}},
                    }
                }
            },
        }
    return schema


app.openapi = _openapi_schema
