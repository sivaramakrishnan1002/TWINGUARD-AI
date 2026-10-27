"""FastAPI scaffold for TwinGuard AI."""

from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import AnyUrl, BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from app.database import get_layer_records


class Health(BaseModel):
    status: Literal["ok"]
    service: str
    database: Literal["ok", "unavailable", "not_checked"]


class ZoomRange(BaseModel):
    min: int = Field(ge=0, le=22)
    max: int = Field(ge=0, le=22)

    @model_validator(mode="after")
    def validate_order(self):
        if self.min > self.max:
            raise ValueError("zoom minimum cannot exceed maximum")
        return self


class LayerProvenance(BaseModel):
    source_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    source_url: AnyUrl | None = None


class RouteProvenance(BaseModel):
    source: Literal["replay", "live", "simulated"]
    source_id: str = Field(min_length=1, max_length=128)
    schema_version: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    source_file: str | None = Field(default=None, max_length=512)
    source_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    run_id: str | None = Field(default=None, max_length=128)


class Layer(BaseModel):
    layer_key: str
    source_layer: str
    source_crs: str | None
    target_srid: int
    loaded_row_count: int = Field(ge=0)
    units: dict[str, str]
    zoom: ZoomRange | None
    attribution: str | None
    vintage: str | None
    provenance: LayerProvenance
    nodata: str
    tile_endpoint_available: Literal[False]


class UTCRequestModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    @field_validator("*", mode="after")
    @classmethod
    def require_aware_datetimes(cls, value):
        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("timestamp must include an explicit UTC offset")
            return value.astimezone(timezone.utc)
        return value

    @field_serializer("*", when_used="json")
    @classmethod
    def serialize_datetimes_as_utc(cls, value):
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return value


class RouteResponse(BaseModel):
    # `reachable` means a topological path exists; probability is the separate
    # flood-accessibility assessment and may be unknown.
    reachable: bool
    edge_ids: list[int]
    travel_time_minutes: float | None = Field(default=None, ge=0)
    route_accessibility_probability: float | None = Field(default=None, ge=0, le=1)
    provenance: RouteProvenance


class ForecastRequest(UTCRequestModel):
    event_key: str
    issued_at: datetime
    horizon_hours: int = Field(ge=1)
    step_minutes: int = Field(ge=1)
    input_source_ids: list[str] | None = None


class RunTimeRequest(UTCRequestModel):
    run_id: int
    valid_at: datetime
    zone_ids: list[str] | None = None


class RouteRequest(UTCRequestModel):
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


@app.post("/route", operation_id="planRoute", response_model=RouteResponse)
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
