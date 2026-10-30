"""FastAPI scaffold for TwinGuard AI."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import AnyUrl, BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from app.database import get_layer_records
from app.scenario_visualization.router import router as scenario_visualization_router


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


class ResultModel(UTCRequestModel):
    model_config = ConfigDict(extra="allow")


class MetricDistribution(ResultModel):
    status: Literal["AVAILABLE", "PARTIAL", "UNAVAILABLE"]
    unit: str
    mean: float | None
    p05: float | None
    p50: float | None
    p95: float | None
    member_count: int = Field(ge=0)
    interpretation: str


class ImpactEvent(ResultModel):
    event_key: str
    event_start_utc: datetime | None
    event_end_utc: datetime | None
    time_basis: Literal["UTC"]


class ImpactThresholds(ResultModel):
    road_block_depth_m: float = Field(ge=0)
    road_threshold_is_assumption: bool
    sensitivity_depth_thresholds_m: list[float]
    mapped_facility_exposure_threshold_m: float | None
    population_exposure_threshold_m: float | None
    exposure_thresholds_are_assumptions: bool


class ImpactMetrics(ResultModel):
    population_exposed_people: MetricDistribution | None
    affected_road_length_m: MetricDistribution | None
    affected_facilities_count: MetricDistribution | None
    facility_access_loss_fraction: MetricDistribution | None


class CoverageSlice(ResultModel):
    assessed_count: int = Field(ge=0)
    eligible_count: int = Field(ge=0)
    nodata_count: int = Field(ge=0)
    fraction_assessed: float | None = Field(default=None, ge=0, le=1)
    coverage_basis: str | None = None


class ImpactCoverage(ResultModel):
    population: CoverageSlice
    roads: CoverageSlice
    facilities: CoverageSlice
    hazard_grid: CoverageSlice


class ImpactUncertainty(ResultModel):
    method: str
    ensemble_id: str | None
    member_count: int = Field(ge=0)
    interpretation: str


class ImpactSource(ResultModel):
    source_id: str
    source_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    version: str | None
    role: str


class ImpactProvenance(ResultModel):
    sources: list[ImpactSource]
    algorithm: str
    algorithm_version: str | None
    code_commit: str | None
    parameters: dict[str, Any]
    grid: dict[str, Any]


class AggregationInterval(ResultModel):
    start_utc: datetime
    end_utc: datetime
    convention: Literal["[start,end)"]


class FacilityAccess(ResultModel):
    category: Literal["hospital", "shelter", "candidate_shelter"]
    facility_count: int = Field(ge=0)
    reachable_count: int = Field(ge=0)
    unreachable_count: int = Field(ge=0)
    unassessed_count: int = Field(ge=0)
    access_loss_fraction: float | None = Field(default=None, ge=0, le=1)
    coverage_fraction: float | None = Field(default=None, ge=0, le=1)
    coverage_fraction_mean: float | None = Field(default=None, ge=0, le=1)
    interpretation: str


class ImpactSensitivity(ResultModel):
    threshold_m: float = Field(ge=0)
    population_exposed_known_people: MetricDistribution | None
    affected_road_length_m: MetricDistribution | None
    mapped_facilities_exposed_count: MetricDistribution | None
    facility_access_loss_fraction: MetricDistribution | None
    facility_access_by_category: list[FacilityAccess]


class ImpactResult(ResultModel):
    schema_id: Literal["twinguard.impact_result"]
    schema_version: str
    result_id: str
    run_id: int
    run_version: str
    source_mode: Literal["OBSERVED", "DERIVED", "SIMULATED", "ASSUMPTION", "REPLAY"]
    event: ImpactEvent
    valid_at_utc: datetime
    aggregation_interval: AggregationInterval | None
    aggregation_basis: str | None
    generated_at_utc: datetime
    scenario_key: str
    thresholds: ImpactThresholds
    metrics: ImpactMetrics
    facility_access_by_category: list[FacilityAccess]
    sensitivity: list[ImpactSensitivity]
    coverage: ImpactCoverage
    uncertainty: ImpactUncertainty
    provenance: ImpactProvenance
    qc_flags: list[str]
    event_reference_note: str | None


class RouteStatus(str, Enum):
    ROUTE_FOUND = "ROUTE_FOUND"
    NO_TOPOLOGICAL_PATH = "NO_TOPOLOGICAL_PATH"
    INSUFFICIENT_HAZARD_COVERAGE = "INSUFFICIENT_HAZARD_COVERAGE"
    BELOW_ACCESSIBILITY_CONSTRAINT = "BELOW_ACCESSIBILITY_CONSTRAINT"
    INPUT_UNAVAILABLE = "INPUT_UNAVAILABLE"


class RouteEdge(ResultModel):
    edge_id: int
    entry_at_utc: datetime | None
    exit_at_utc: datetime | None
    distance_m: float | None = Field(ge=0)
    travel_time_seconds: float | None = Field(default=None, ge=0)
    depth_max_m: float | None
    passable_probability: float | None = Field(default=None, ge=0, le=1)
    bridge: bool | None
    tunnel: bool | None
    assessment_status: str


class RouteEdgeCoverage(ResultModel):
    route_edge_count: int = Field(ge=0)
    assessed_edge_count: int = Field(ge=0)
    unassessed_edge_count: int = Field(ge=0)
    fraction_assessed: float | None = Field(default=None, ge=0, le=1)


class RouteThresholds(ResultModel):
    ordinary_block_at_or_above_m: float
    tunnel_proxy_block_at_or_above_m: float
    bridge_rule: str
    thresholds_are_assumptions: bool
    uncertainty_route_accessibility_minimum: float | None = Field(default=None, ge=0, le=1)
    sensitivity_m: list[float]


class RouteGraph(ResultModel):
    graph_id: str
    graph_version: str
    graph_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    crs: str
    edge_source_ids: list[str]
    build_algorithm: str
    build_version: str
    assumptions: list[str]


class RouteHazardRun(ResultModel):
    run_id: int | None
    version: str
    issued_at_utc: datetime | None
    valid_start_utc: datetime | None
    valid_end_utc: datetime | None
    depth_source_id: str
    depth_source_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    ensemble_id: str | None


class RouteUncertainty(ResultModel):
    method: str
    ensemble_member_count: int = Field(ge=0)
    travel_time_spread_seconds: float | None = Field(default=None, ge=0)
    failure_probability_constraint: float | None = Field(default=None, ge=0, le=1)
    limitations: list[str]


class RouteResultProvenance(ResultModel):
    algorithm: str
    algorithm_version: str
    code_commit: str
    generated_at_utc: datetime
    parameters: dict[str, Any]


class RouteResponse(ResultModel):
    schema_id: Literal["twinguard.route_result"]
    schema_version: str
    result_id: str
    status: RouteStatus
    run_id: int | None
    scenario_key: str
    source_mode: Literal["OBSERVED", "DERIVED", "SIMULATED", "ASSUMPTION", "REPLAY"]
    method: Literal["static", "current_flood_aware", "horizon_aware", "uncertainty_aware"]
    origin_id: str
    destination_id: str
    travel_mode: Literal["vehicle", "walking"]
    departure_at_utc: datetime
    arrival_at_utc: datetime | None
    requested_horizon_seconds: int | None = Field(default=None, ge=0)
    distance_m: float | None = Field(default=None, ge=0)
    travel_time_seconds: float | None = Field(default=None, ge=0)
    topologically_reachable: bool | None
    route_accessibility_probability: float | None = Field(default=None, ge=0, le=1)
    route_failure_probability: float | None = Field(default=None, ge=0, le=1)
    minimum_accessibility_probability: float | None = Field(default=None, ge=0, le=1)
    route_geometry: dict[str, Any] | None
    node_path: list[int]
    edges: list[RouteEdge]
    depth_thresholds: RouteThresholds
    edge_coverage: RouteEdgeCoverage
    graph: RouteGraph
    hazard_run: RouteHazardRun
    uncertainty: RouteUncertainty
    provenance: RouteResultProvenance
    qc_flags: list[str]

    @model_validator(mode="after")
    def keep_topology_and_accessibility_distinct(self):
        coverage = self.edge_coverage
        if coverage.assessed_edge_count + coverage.unassessed_edge_count != coverage.route_edge_count:
            raise ValueError("edge coverage counts must sum to route edge count")
        if coverage.route_edge_count == 0 and coverage.fraction_assessed is not None:
            raise ValueError("empty route coverage must have a null fraction")
        if coverage.route_edge_count and coverage.fraction_assessed is not None:
            expected = coverage.assessed_edge_count / coverage.route_edge_count
            if abs(coverage.fraction_assessed - expected) > 1e-9:
                raise ValueError("edge coverage fraction must match its counts")
        if self.status == RouteStatus.NO_TOPOLOGICAL_PATH:
            if self.topologically_reachable is not False:
                raise ValueError("NO_TOPOLOGICAL_PATH requires false topological reachability")
            if any(value is not None for value in (
                self.distance_m, self.travel_time_seconds,
                self.route_accessibility_probability, self.route_failure_probability,
            )):
                raise ValueError("no-path measurements and accessibility must remain null")
            if self.arrival_at_utc is not None or self.route_geometry is not None or self.edges:
                raise ValueError("no-path arrival, geometry and edges must remain absent")
        if coverage.unassessed_edge_count and self.route_accessibility_probability is not None:
            raise ValueError("unassessed route edges cannot be treated as passable")
        if (self.route_accessibility_probability is None) != (self.route_failure_probability is None):
            raise ValueError("route accessibility and failure probabilities must both be null or present")
        if self.route_accessibility_probability is not None and self.route_failure_probability is not None:
            if abs(self.route_accessibility_probability + self.route_failure_probability - 1) > 1e-9:
                raise ValueError("route failure probability must complement accessibility")
        return self


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
app.include_router(scenario_visualization_router)


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
