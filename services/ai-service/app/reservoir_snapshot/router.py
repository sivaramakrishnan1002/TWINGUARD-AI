from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from services.trackb.connectors.tn_reservoir.client import (
    CfmDashboardClient,
    CfmSourceError,
    ReservoirHistory,
)


router = APIRouter()


class ReservoirProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: Literal["tn_cfm_dss_public_lakes_dashboard"]
    endpoint: Literal[
        "/Master/GetLast15daysWaterLevel",
        "/Master/GetMonthlyWaterLevelOfReservoir",
    ]
    response_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class ReservoirRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reservoir_id: str = Field(min_length=1)
    reservoir_name: str = Field(min_length=1)
    source_date: str = Field(
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        json_schema_extra={"format": "date"},
    )
    time_precision: Literal["date"]
    observed_at: None
    observation_timezone: Literal["unknown"]
    water_level_m: float = Field(ge=0, allow_inf_nan=False)
    average_storage_mcm: float = Field(ge=0, allow_inf_nan=False)
    received_at: datetime
    source_mode: Literal["LIVE"]
    availability: Literal["available"]
    freshness: Literal["unknown"]
    freshness_note: str
    provenance: ReservoirProvenance


class ReservoirHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    history_kind: Literal["daily", "monthly"]
    source_id: Literal["tn_cfm_dss_public_lakes_dashboard"]
    source_mode: Literal["LIVE"]
    received_at: datetime
    availability: Literal["available"]
    freshness: Literal["unknown"]
    records: list[ReservoirRecord] = Field(min_length=1, max_length=75)
    limitations: list[str] = Field(min_length=1)


class ReservoirUnavailable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: Literal["Reservoir source is unavailable or returned invalid data."]


LIMITATIONS = [
    "Latest published CFM-DSS dashboard history; publication cadence and freshness are unknown.",
    "Calendar date/month labels are not exact observation times; timezone is unknown.",
    "This source provides no rainfall, release, inflow/outflow, flood depth, forecast, route-safety, or shelter decision result.",
    "Research and educational display only; this endpoint does not trigger model recomputation.",
]
SOURCE_ID = "tn_cfm_dss_public_lakes_dashboard"


def _response(history: ReservoirHistory, expected_kind: str) -> ReservoirHistoryResponse:
    if history.history_kind != expected_kind:
        raise ValueError("source history kind does not match request")
    max_rows = 75 if expected_kind == "daily" else 65
    if not 0 < len(history.records) <= max_rows:
        raise ValueError("source history exceeds its row bound")
    return ReservoirHistoryResponse.model_validate(
        {
            **history.to_dict(),
            "source_mode": "LIVE",
            "limitations": LIMITATIONS,
        }
    )


@router.get(
    "/reservoirs/history",
    operation_id="getCfmReservoirHistory",
    response_model=ReservoirHistoryResponse,
    responses={503: {"model": ReservoirUnavailable}},
)
def get_reservoir_history(
    response: Response,
    period: Literal["daily", "monthly"] = Query(default="daily"),
) -> ReservoirHistoryResponse:
    """Fetch one latest-published public dashboard snapshot on demand."""
    response.headers["Cache-Control"] = "no-store"
    try:
        client = CfmDashboardClient(timeout_seconds=15.0)
        history = (
            client.fetch_daily_history()
            if period == "daily"
            else client.fetch_monthly_history()
        )
        return _response(history, period)
    except (CfmSourceError, ValueError, TypeError):
        raise HTTPException(
            status_code=503,
            detail="Reservoir source is unavailable or returned invalid data.",
        ) from None
    except Exception:
        # Never leak upstream response/token details or transport exception text.
        raise HTTPException(
            status_code=503,
            detail="Reservoir source is unavailable or returned invalid data.",
        ) from None
