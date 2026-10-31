"""FastAPI scaffold for TwinGuard AI."""

import json
import hashlib
import math
import re
from datetime import date, datetime, timezone
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Path as ApiPath, Request
from fastapi.responses import JSONResponse
from pydantic import AnyUrl, BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator
from fastapi.middleware.cors import CORSMiddleware

from app.database import get_layer_records
from app.scenario_visualization.router import router as scenario_visualization_router
from app.scenario_visualization.raster_router import router as scenario_raster_router


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MAX_IMPACT_ROWS = 500
MAX_ROUTE_RESULT_ROWS = 500


class _ExactAcceptCORSMiddleware(CORSMiddleware):
    """Apply CR-010's one explicit request-header allowance."""

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        # Starlette automatically includes browser safelisted headers. This
        # package policy intentionally allows only the explicitly approved
        # Accept header, including in the preflight response.
        self.allow_headers = ["accept"]
        self.preflight_headers["Access-Control-Allow-Headers"] = "Accept"


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


class ImpactArtifactRequest(UTCRequestModel):
    """Exact C4 v1 selector for one saved A07 V4 result."""

    model_config = ConfigDict(extra="forbid")

    run_id: int
    valid_at: datetime
    scenario_key: str = Field(min_length=1)


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


class ReplayLookupError(BaseModel):
    status: Literal[400, 404, 409, 503]
    code: Literal["invalid_selector", "not_found", "ambiguous_identity", "asset_unavailable"]
    detail: str = Field(min_length=1)


class ReplaySourceProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: Literal["Kaggle Chennai Water Management"]
    archive_path: Literal["data/raw/reservoirs/kaggle_chennai_water_management/archive.zip"]
    archive_sha256: Literal["7645febde7ccc21871200487139d1c8a84ea90a6dd2eccc93b7d1f06faf69197"]
    member: Literal["chennai_reservoir_levels.csv"]
    member_sha256: Literal["3b4b6f2f53b5db20513d2829c2dba265c5738a55bf0c8eade51e0e2d5cfeaef7"]
    csv_physical_line: Literal[4354]
    raw_date_field: Literal["Date"]
    raw_storage_field: Literal["POONDI"]
    raw_storage_value: Literal["2745.00"]
    timezone_status: Literal["unknown; source provides date only"]
    rainfall_unit_status: Literal["INFERRED; original unit unspecified"]


class ReplayRawSourceRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Date: Literal["01-12-2015"]
    POONDI: Literal["2745.00"]


class ReplaySourceObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    schema_: Literal["trackb.reservoir_update.v1"] = Field(alias="schema")
    event_id: Literal["replay:POONDI:date:2015-12-01"]
    source: Literal["replay"]
    source_mode: Literal["REPLAY"]
    time_precision: Literal["date"]
    source_date: Literal["2015-12-01"]
    observed_at: None
    observation_timezone: Literal["unknown"]
    received_at: datetime
    reservoir_key: Literal["POONDI"]
    raw_source_row: ReplayRawSourceRow
    storage_value: Literal[2745]
    storage_unit: Literal["mcft"]
    provenance: ReplaySourceProvenance


class ReplayContextInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_date: date
    reservoir_key: str
    role: str
    source_member_sha256: Literal["3b4b6f2f53b5db20513d2829c2dba265c5738a55bf0c8eade51e0e2d5cfeaef7"]


class ReplayRunIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    identity_version: Literal["b13-replay-identity-v1"]
    replay_run_id: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")
    algorithm_id: Literal["trackb-rule-v1"]
    configuration_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    normalized_input_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    context_inputs: list[ReplayContextInput]


class ReplayTriggerInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    storage_pct: float
    rise_1d_pct: float | None
    rise_3d_pct: float | None
    rain_3d_mm: float | None


class ReplayTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    horizon_days: Literal[7]
    capacity_fraction: Literal[0.8]
    status: Literal["DEFAULT, to confirm"]


class ReplayDerivedAlert(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    schema_: Literal["trackb.alert.v1"] = Field(alias="schema")
    event_id: Literal["replay:POONDI:date:2015-12-01"]
    source_date: Literal["2015-12-01"]
    time_precision: Literal["date"]
    observation_timezone: Literal["unknown"]
    observed_at: None
    received_at: datetime
    source: Literal["replay"]
    reservoir_key: Literal["POONDI"]
    level: Literal["Normal", "Watch", "Warning", "Critical"]
    confidence: float = Field(ge=0, le=1)
    valid_from: None
    valid_to: None
    rule_version: Literal["trackb-rule-v1"]
    trigger_inputs: ReplayTriggerInputs
    target: ReplayTarget
    provenance: ReplaySourceProvenance


class ReplayDerivedOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["produced", "not_produced"]
    alert: ReplayDerivedAlert | None
    output_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def status_matches_payload(self):
        if self.status == "produced" and (self.alert is None or self.output_sha256 is None):
            raise ValueError("produced output requires an alert and hash")
        if self.status == "not_produced" and (self.alert is not None or self.output_sha256 is not None):
            raise ValueError("not_produced output must be null")
        return self


class ReplayObservationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: Literal["C4-v2"]
    source_observation: ReplaySourceObservation
    replay: ReplayRunIdentity
    derived_output: ReplayDerivedOutput
    limitations: list[str] = Field(min_length=1)


class ReplayLookupFailure(Exception):
    def __init__(self, status: int, code: str, detail: str):
        self.status, self.code, self.detail = status, code, detail


REPLAY_EVENT_ID = "replay:POONDI:date:2015-12-01"
REPLAY_FIXTURE = Path(__file__).resolve().parent / "replay_results" / "b13_source_observation.json"
REPLAY_FIXTURE_SHA256 = "dd5ea17cdf63853ffd1cdc3036b8c8282490daafd3e19715cd82445cb27ff2a8"
REPLAY_CONFIG_SHA256 = "b2d4f49c2961a5f20d55302786230a3029c6f4863ffa785241d288f4e21f65fb"
REPLAY_IDENTITY_VERSION = "b13-replay-identity-v1"
REPLAY_ALGORITHM_ID = "trackb-rule-v1"
REPLAY_SELECTOR_PATTERN = re.compile(r"^replay:[A-Z]+:date:[0-9]{4}-[0-9]{2}-[0-9]{2}$")


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _load_b13_fixture() -> tuple[dict[str, Any], ...]:
    """Load only the canonical packaged source fixture and verify its pinned bytes."""
    try:
        raw = REPLAY_FIXTURE.read_bytes()
        if hashlib.sha256(raw).hexdigest() != REPLAY_FIXTURE_SHA256:
            raise ValueError("fixture hash mismatch")
        document = json.loads(raw)
        if document["fixture_schema"] != "b13.source_observation.v1":
            raise ValueError("fixture schema mismatch")
        if document["selector"]["event_id"] != REPLAY_EVENT_ID:
            raise ValueError("fixture selector mismatch")
        if document["selector"]["archive_sha256"] != "7645febde7ccc21871200487139d1c8a84ea90a6dd2eccc93b7d1f06faf69197":
            raise ValueError("archive hash mismatch")
        if document["selector"]["member_sha256"] != "3b4b6f2f53b5db20513d2829c2dba265c5738a55bf0c8eade51e0e2d5cfeaef7":
            raise ValueError("member hash mismatch")
        if _canonical_sha256(document["effective_configuration"]) != REPLAY_CONFIG_SHA256:
            raise ValueError("configuration canonicalization mismatch")
        return (document,)
    except Exception:
        raise ReplayLookupFailure(503, "asset_unavailable", "The approved replay input is unavailable or failed integrity verification.") from None


def _finite_number(value: Any) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite replay input")
    return number


def _evaluate_b13(document: dict[str, Any]) -> ReplayObservationResult:
    """Run the registered B19 storage rule against the exact packaged observation/context."""
    try:
        selected = document["source_observation"]
        context = document["context_inputs"]
        config = document["effective_configuration"]
        selector = document["selector"]
        if len(context) != 3:
            raise ValueError("unexpected context count")
        previous = sorted(context, key=lambda row: row["raw_source_rows"]["levels"]["Date"])
        expected_dates = ["28-11-2015", "29-11-2015", "30-11-2015"]
        if [row["raw_source_rows"]["levels"]["Date"] for row in previous] != expected_dates:
            raise ValueError("context identity mismatch")
        if selected["raw_source_row"] != {"Date": "01-12-2015", "POONDI": "2745.00"}:
            raise ValueError("selected source values mismatch")
        storage = [_finite_number(row["raw_source_rows"]["levels"]["POONDI"]) for row in previous]
        storage.append(_finite_number(selected["storage_value"]))
        rainfall = [_finite_number(row["raw_source_rows"]["rainfall"]["POONDI"]) for row in previous]
        rainfall.append(_finite_number(document["selected_rainfall_raw"]["POONDI"]))
        capacity = _finite_number(config["capacity_mcft"])
        storage_pct = [100.0 * value / capacity for value in storage]
        rise_1d = storage_pct[-1] - storage_pct[-2]
        rise_3d = storage_pct[-1] - storage_pct[-4]
        rain_3d = sum(rainfall[-3:])
        thresholds = config["rule_thresholds"]
        rise_1_threshold = _finite_number(thresholds["rise_1d_pct"])
        rise_3_threshold = _finite_number(thresholds["rise_3d_pct"])
        rain_p75 = _finite_number(thresholds["rain_3d_p75_mm"])
        rain_p90 = _finite_number(thresholds["rain_3d_p90_mm"])
        critical = storage_pct[-1] >= 90
        warning = storage_pct[-1] >= 80 and (rise_3d >= rise_3_threshold or rain_3d >= rain_p90)
        watch = storage_pct[-1] >= 70 or (rise_1d >= rise_1_threshold and rain_3d >= rain_p75)
        level = 3 if critical else 2 if warning else 1 if watch else 0
        confidence = min(4.0, max(0.0, float(storage_pct[-1] >= 70) + float(rise_1d >= rise_1_threshold) + float(rise_3d >= rise_3_threshold) + float(rain_3d >= rain_p75))) / 4.0
        feature_payload = {
            "source_row": selected["raw_source_row"],
            "selected_rainfall_feature_row": document["selected_rainfall_raw"],
            "source_date": selected["source_date"],
            "context_rows": [row["raw_source_rows"] for row in previous],
            "normalized_features": {"storage_pct": storage_pct[-1], "rise_1d_pct": rise_1d, "rise_3d_pct": rise_3d, "rain_3d_source_units_unverified": rain_3d},
        }
        normalized_hash = _canonical_sha256(feature_payload)
        config_hash = _canonical_sha256(config)
        context_inputs = [
            {"source_date": datetime.strptime(row["raw_source_rows"]["levels"]["Date"], "%d-%m-%Y").date(), "reservoir_key": "POONDI", "role": "rolling_feature_window_preceding_selected_source_row", "source_member_sha256": selector["member_sha256"]}
            for row in previous
        ]
        run_identity = {
            "identity_version": REPLAY_IDENTITY_VERSION,
            "source_archive_sha256": selector["archive_sha256"],
            "source_member_sha256": selector["member_sha256"],
            "event_id": selector["event_id"],
            "csv_physical_line": selector["csv_physical_line"],
            "algorithm_id": REPLAY_ALGORITHM_ID,
            "configuration_sha256": config_hash,
            "normalized_input_sha256": normalized_hash,
        }
        replay_run_id = "sha256:" + _canonical_sha256(run_identity)
        received_at = datetime.now(timezone.utc)
        provenance = selected["provenance"]
        source_observation = {**selected, "event_id": selector["event_id"], "received_at": received_at, "provenance": provenance}
        if level:
            alert = {
                "schema": "trackb.alert.v1", "event_id": REPLAY_EVENT_ID, "source_date": "2015-12-01",
                "time_precision": "date", "observation_timezone": "unknown", "observed_at": None,
                "received_at": received_at, "source": "replay", "reservoir_key": "POONDI",
                "level": ("Normal", "Watch", "Warning", "Critical")[level], "confidence": confidence,
                "valid_from": None, "valid_to": None, "rule_version": "trackb-rule-v1",
                "trigger_inputs": {"storage_pct": storage_pct[-1], "rise_1d_pct": rise_1d, "rise_3d_pct": rise_3d, "rain_3d_mm": rain_3d},
                "target": config["target"], "provenance": provenance,
            }
            output_sha = _canonical_sha256(ReplayDerivedAlert.model_validate(alert).model_dump(mode="json", by_alias=True))
            derived = {"status": "produced", "alert": alert, "output_sha256": output_sha}
        else:
            derived = {"status": "not_produced", "alert": None, "output_sha256": None}
        return ReplayObservationResult.model_validate({
            "contract_version": "C4-v2", "source_observation": source_observation,
            "replay": {"identity_version": REPLAY_IDENTITY_VERSION, "replay_run_id": replay_run_id,
                       "algorithm_id": REPLAY_ALGORITHM_ID, "configuration_sha256": config_hash,
                       "normalized_input_sha256": normalized_hash, "context_inputs": context_inputs},
            "derived_output": derived,
            "limitations": [
                "Historical observation time and timezone are unknown; source_date is date-only.",
                "Any alert is derived replay output, not a historically observed event.",
                "This is a storage-target rule only; no flood-depth result is produced.",
                "Rainfall source units are undocumented and inferred; the legacy rule field is not verified millimetres.",
                "Rule confidence is not calibrated probability; capacity and target settings require confirmation.",
                "Research-only; not live, a validated forecast, warning, route, or safety guidance.",
            ],
        })
    except ReplayLookupFailure:
        raise
    except Exception:
        raise ReplayLookupFailure(503, "asset_unavailable", "The approved replay input, context, or configuration is unavailable or invalid.") from None


def _b13_replay_projection(event_id: str) -> ReplayObservationResult:
    if not REPLAY_SELECTOR_PATTERN.fullmatch(event_id):
        raise ReplayLookupFailure(400, "invalid_selector", "event_id must be a date-only replay selector.")
    try:
        date.fromisoformat(event_id.rsplit(":", 1)[1])
    except ValueError:
        raise ReplayLookupFailure(400, "invalid_selector", "event_id must contain a valid calendar date.") from None
    if event_id != REPLAY_EVENT_ID:
        raise ReplayLookupFailure(404, "not_found", "No exact approved replay observation exists.")
    rows = _load_b13_fixture()
    matches = [row for row in rows if row.get("selector", {}).get("event_id") == event_id]
    if not matches:
        raise ReplayLookupFailure(404, "not_found", "No exact approved replay observation exists.")
    if len(matches) != 1:
        raise ReplayLookupFailure(409, "ambiguous_identity", "More than one source observation matches this selector.")
    return _evaluate_b13(matches[0])


app = FastAPI(
    title="TwinGuard AI Service",
    version="0.1.0",
    description=(
        "Bounded C4 v1 artifact projections and the local test-scoped CR-012 date-only replay observation route are enabled. "
        "The replay route separates the archived REPLAY input from optional derived rule output; no live operation is enabled."
    ),
)
app.include_router(scenario_visualization_router)
app.include_router(scenario_raster_router)
app.add_middleware(
    _ExactAcceptCORSMiddleware,
    allow_origins=["http://127.0.0.1:8081"],
    allow_methods=["GET"],
    allow_headers=["Accept"],
    allow_credentials=False,
)


@app.exception_handler(ReplayLookupFailure)
async def replay_lookup_error_handler(request: Request, exc: ReplayLookupFailure) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        content=ReplayLookupError(status=exc.status, code=exc.code, detail=exc.detail).model_dump(mode="json"),
    )


@lru_cache(maxsize=1)
def _load_a07_impact_results() -> tuple[ImpactResult, ...]:
    """Load only the registered, versioned A07 artifact; never query a database."""
    path = (PROJECT_ROOT / "data/features/impact/batch2_v4_contract/impact_results.jsonl").resolve()
    if not path.is_relative_to(PROJECT_ROOT) or not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
        raise RuntimeError("registered impact artifact is unavailable")
    results: list[ImpactResult] = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if len(results) >= MAX_IMPACT_ROWS:
                raise RuntimeError("registered impact artifact exceeds its row bound")
            if not line.strip():
                continue
            results.append(ImpactResult.model_validate_json(line))
    if not results:
        raise RuntimeError("registered impact artifact is empty")
    return tuple(results)


@lru_cache(maxsize=1)
def _load_a09_route_results() -> tuple[RouteResponse, ...]:
    """Load only A09 revision 3; result IDs are scoped to this fixed artifact."""
    path = (PROJECT_ROOT / "data/features/routing/results/batch2_v1/revision_3/route_results.jsonl").resolve()
    if not path.is_relative_to(PROJECT_ROOT) or not path.is_file() or path.stat().st_size > 32 * 1024 * 1024:
        raise RuntimeError("registered route artifact is unavailable")
    results: list[RouteResponse] = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if len(results) >= MAX_ROUTE_RESULT_ROWS:
                raise RuntimeError("registered route artifact exceeds its row bound")
            if not line.strip():
                continue
            results.append(RouteResponse.model_validate_json(line))
    if not results:
        raise RuntimeError("registered route artifact is empty")
    return tuple(results)


def _saved_artifact_unavailable() -> HTTPException:
    # Keep parser/duplicate details private and do not accidentally return a partial result.
    return HTTPException(status_code=503, detail="Registered saved-result evidence is unavailable.")


def _impact_projection(request: ImpactArtifactRequest) -> ImpactResult:
    """Resolve the exact C4 v1 A07 tuple; duplicates fail closed."""
    try:
        rows = _load_a07_impact_results()
    except Exception:
        raise _saved_artifact_unavailable() from None
    matches = [
        row for row in rows
        if row.run_id == request.run_id
        and row.valid_at_utc == request.valid_at
        and row.scenario_key == request.scenario_key
    ]
    if not matches:
        raise HTTPException(status_code=404, detail="No exact saved impact result was found.")
    if len(matches) != 1:
        raise _saved_artifact_unavailable()
    return matches[0]


def _route_result_projection(result_id: str) -> RouteResponse:
    """Resolve an identifier only within the registered A09 revision-3 artifact."""
    try:
        rows = _load_a09_route_results()
    except Exception:
        raise _saved_artifact_unavailable() from None
    matches = [row for row in rows if row.result_id == result_id]
    if not matches:
        raise HTTPException(status_code=404, detail="No saved route result exists in A09 revision 3.")
    if len(matches) != 1:
        raise _saved_artifact_unavailable()
    return matches[0]


@app.get("/health", operation_id="health", response_model=Health)
def health() -> Health:
    return Health(status="ok", service="twinguard-ai-service", database="not_checked")


@app.get(
    "/replay-alerts/{event_id}",
    operation_id="getB13ReplayObservation",
    response_model=ReplayObservationResult,
    responses={
        400: {"model": ReplayLookupError, "description": "Malformed or invalid selector/input."},
        404: {"model": ReplayLookupError, "description": "No exact source observation/replay identity exists."},
        409: {"model": ReplayLookupError, "description": "Duplicate or ambiguous source identity."},
        503: {"model": ReplayLookupError, "description": "Source, context, configuration or result is unavailable or hash-invalid."},
    },
)
def b13_replay_observation(event_id: str) -> ReplayObservationResult:
    return _b13_replay_projection(event_id)


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


@app.post(
    "/impact",
    operation_id="estimateImpact",
    response_model=ImpactResult,
    responses={
        404: {"description": "No exact A07 artifact key exists; duplicate matches fail closed."},
        501: {"description": "Saved-artifact lookup is unavailable until its selector is supported."},
        503: {"description": "Registered read-only evidence is unavailable or ambiguous."},
    },
)
def impact(request: ImpactArtifactRequest) -> ImpactResult:
    return _impact_projection(request)


@app.get(
    "/route-results/{result_id}",
    operation_id="getSavedRouteResult",
    response_model=RouteResponse,
    responses={
        404: {"description": "No exact result_id exists in A09 revision 3; duplicate matches fail closed."},
        501: {"description": "Saved-route retrieval is unavailable until its checks pass."},
        503: {"description": "Registered read-only evidence is unavailable or ambiguous."},
    },
)
def route_result(result_id: str = ApiPath(min_length=1)) -> RouteResponse:
    return _route_result_projection(result_id)


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
