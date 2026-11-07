"""Read-only Track B API; inject a project-specific read adapter."""
from typing import Any, Protocol
from datetime import date
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query

class TrackBReader(Protocol):
    def current_reservoir_states(self) -> list[dict[str, Any]]: ...
    def recent_alerts(self, limit: int) -> list[dict[str, Any]]: ...
    def alert_timeline(self, start: str, end: str) -> list[dict[str, Any]]: ...
    def backtest_summary(self) -> dict[str, Any]: ...
    def rule_parameters(self) -> dict[str, Any]: ...

router = APIRouter(prefix="/trackb", tags=["trackb"])
_reader: TrackBReader | None = None

def configure_reader(reader: TrackBReader) -> None:
    global _reader
    _reader = reader

def _reader_or_503() -> TrackBReader:
    if _reader is None:
        raise HTTPException(status_code=503, detail="Track B read adapter is not configured")
    return _reader

def _check_sources(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if any(row.get('source') not in {'replay','live','simulated'} for row in rows):
        raise HTTPException(status_code=502, detail="Track B rows must identify replay, live, or simulated source")
    for row in rows:
        if row.get('time_precision')=='date':
            try:
                source_date=date.fromisoformat(row.get('source_date',''))
            except (TypeError,ValueError) as exc:
                raise HTTPException(status_code=502,detail="Date-only Track B rows require an ISO source_date") from exc
            if source_date.isoformat()!=row.get('source_date') or row.get('observed_at') is not None:
                raise HTTPException(status_code=502,detail="Date-only Track B rows cannot advertise an observation instant")
            if row.get('observation_timezone') not in (None,'unknown'):
                raise HTTPException(status_code=502,detail="Date-only Track B timezone must remain unknown")
            if row.get('valid_from') is not None or row.get('valid_to') is not None:
                raise HTTPException(status_code=502,detail="Date-only Track B alerts cannot advertise an exact validity interval")
        elif row.get('time_precision')=='instant':
            try:
                observed=datetime.fromisoformat(str(row.get('observed_at','')).replace('Z','+00:00'))
            except ValueError as exc:
                raise HTTPException(status_code=502,detail="Instant Track B rows require an ISO observed_at") from exc
            if observed.tzinfo is None:
                raise HTTPException(status_code=502,detail="Instant Track B observed_at must include an offset")
    return rows

@router.get("/reservoirs/current")
def current_reservoir_states():
    return {"states": _check_sources(_reader_or_503().current_reservoir_states())}

@router.get("/alerts/recent")
def recent_alerts(limit: int = Query(50, ge=1, le=500)):
    return {"alerts": _check_sources(_reader_or_503().recent_alerts(limit))}

@router.get("/alerts/timeline")
def alert_timeline(start: str, end: str):
    try:
        start_date=date.fromisoformat(start); end_date=date.fromisoformat(end)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="start and end must be ISO calendar dates") from exc
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="end must be on or after start")
    return {"alerts": _check_sources(_reader_or_503().alert_timeline(start, end))}

@router.get("/backtest/summary")
def backtest_summary():
    return {"data_class":"DERIVED", **_reader_or_503().backtest_summary()}

@router.get("/rules/parameters")
def rule_parameters():
    return _reader_or_503().rule_parameters()
