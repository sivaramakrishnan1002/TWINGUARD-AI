"""Read-only Track B API; inject a project-specific read adapter."""
from typing import Any, Protocol
from datetime import date
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
