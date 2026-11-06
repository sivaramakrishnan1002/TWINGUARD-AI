"""Low-volume, on-demand reads from the public CFM-DSS reservoir dashboard.

The dashboard's daily and monthly values are published snapshots. Their
``T00:00:00`` suffix is a chart-category serialization, not an observation
instant. The connector therefore preserves calendar labels and never emits an
observation timestamp or inferred timezone.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from http.cookiejar import CookieJar
from typing import Any, Callable, Mapping, Protocol


BASE_URL = "https://chennaifloodmonitor.tn.gov.in"
DASHBOARD_PATH = "/HomePage/Dashboard"
DAILY_PATH = "/Master/GetLast15daysWaterLevel"
MONTHLY_PATH = "/Master/GetMonthlyWaterLevelOfReservoir"
SOURCE_ID = "tn_cfm_dss_public_lakes_dashboard"

# IDs were checked against the five names displayed in the public dashboard.
RESERVOIR_NAMES = {
    "Po001": "Poondi",
    "TNCH-07-T0726": "Chembarambakkam",
    "RD001": "Red Hills",
    "Cho001": "Cholavaram",
    "TK-001": "Thervoy Kandigai",
}

_TOKEN_RE = re.compile(r"\btoken\s*=\s*'([^']+)'", re.IGNORECASE)
_DATE_LABEL_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:T00:00:00)?$")


class CfmSourceError(RuntimeError):
    """The public dashboard could not provide a validated snapshot."""


class ResponseLike(Protocol):
    status: int
    body: bytes


class SessionLike(Protocol):
    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float,
    ) -> ResponseLike: ...


class _Response:
    def __init__(self, status: int, body: bytes):
        self.status = status
        self.body = body


class _PublicSession:
    """Cookie-aware anonymous GET client; it has no login or credential flow."""

    def __init__(self) -> None:
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(CookieJar())
        )

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float,
    ) -> _Response:
        request = urllib.request.Request(url, headers=dict(headers or {}), method="GET")
        try:
            with self._opener.open(request, timeout=timeout) as response:
                return _Response(response.status, response.read())
        except urllib.error.HTTPError as exc:
            return _Response(exc.code, exc.read())
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise CfmSourceError("CFM-DSS dashboard request failed") from exc


@dataclass(frozen=True)
class DailyReservoirSnapshot:
    reservoir_id: str
    reservoir_name: str
    source_date: str
    observed_at: None
    observation_timezone: str
    time_precision: str
    water_level_m: float
    average_storage_mcm: float
    received_at: str
    source_mode: str
    availability: str
    freshness: str
    freshness_note: str
    provenance: Mapping[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReservoirHistory:
    history_kind: str
    source_id: str
    received_at: str
    availability: str
    freshness: str
    records: tuple[DailyReservoirSnapshot, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "history_kind": self.history_kind,
            "source_id": self.source_id,
            "received_at": self.received_at,
            "availability": self.availability,
            "freshness": self.freshness,
            "records": [record.to_dict() for record in self.records],
        }


def _parse_json_payload(body: bytes) -> list[object]:
    try:
        value: object = json.loads(body.decode("utf-8-sig"))
        # The dashboard currently returns JSON encoded inside a JSON string.
        if isinstance(value, str):
            value = json.loads(value)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CfmSourceError("CFM-DSS returned an invalid JSON payload") from exc
    if not isinstance(value, list):
        raise CfmSourceError("CFM-DSS payload must be a JSON array")
    return value


def _parse_label(value: object, *, monthly: bool) -> str:
    if not isinstance(value, str):
        raise CfmSourceError("CFM-DSS date label is missing or not text")
    match = _DATE_LABEL_RE.fullmatch(value)
    if not match:
        raise CfmSourceError("CFM-DSS date label changed; refusing to infer timestamp semantics")
    label = match.group(1)
    try:
        parsed = date.fromisoformat(label)
    except ValueError as exc:
        raise CfmSourceError("CFM-DSS date label is invalid") from exc
    if monthly and parsed.day != 1:
        raise CfmSourceError("CFM-DSS monthly label is not the first calendar day")
    return label


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CfmSourceError(f"CFM-DSS {name} must be numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise CfmSourceError(f"CFM-DSS {name} must be a finite non-negative value")
    return number


class CfmDashboardClient:
    """Fetch daily/monthly reservoir histories from public dashboard GET routes.

    One invocation makes one dashboard request and one history request. No
    scheduler, persistence, database, service route, or high-frequency polling
    is included. Freshness remains unknown because the source cadence/meaning
    has not been documented.
    """

    def __init__(
        self,
        session: SessionLike | None = None,
        *,
        timeout_seconds: float = 15.0,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if timeout_seconds <= 0 or timeout_seconds > 60:
            raise ValueError("timeout_seconds must be in (0, 60]")
        self._session = session or _PublicSession()
        self._timeout = timeout_seconds
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _get(self, path: str, headers: Mapping[str, str] | None = None) -> bytes:
        response = self._session.get(
            BASE_URL + path, headers=headers, timeout=self._timeout
        )
        if response.status != 200:
            raise CfmSourceError(f"CFM-DSS GET {path} returned HTTP {response.status}")
        return response.body

    def _public_request_token(self) -> str:
        page = self._get(DASHBOARD_PATH)
        match = _TOKEN_RE.search(page.decode("utf-8", errors="replace"))
        if not match:
            raise CfmSourceError("CFM-DSS dashboard did not provide a request token")
        return match.group(1)

    def fetch_daily_history(self) -> ReservoirHistory:
        return self._fetch_history(DAILY_PATH, date_field="date", kind="daily", monthly=False)

    def fetch_monthly_history(self) -> ReservoirHistory:
        return self._fetch_history(
            MONTHLY_PATH, date_field="monthly", kind="monthly", monthly=True
        )

    def _fetch_history(
        self, path: str, *, date_field: str, kind: str, monthly: bool
    ) -> ReservoirHistory:
        token = self._public_request_token()
        raw = self._get(path, headers={"RequestVerificationToken": token})
        payload_hash = hashlib.sha256(raw).hexdigest()
        rows = _parse_json_payload(raw)
        received = self._clock()
        if received.tzinfo is None or received.utcoffset() is None:
            raise ValueError("clock must return a timezone-aware datetime")
        received_at = received.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

        records: list[DailyReservoirSnapshot] = []
        identities: set[tuple[str, str]] = set()
        required = {"tankid", date_field, "average_waterlevel", "average_storage"}
        for row in rows:
            if not isinstance(row, dict) or not required.issubset(row):
                raise CfmSourceError("CFM-DSS row does not match the observed reservoir schema")
            reservoir_id = row.get("tankid")
            if not isinstance(reservoir_id, str) or reservoir_id not in RESERVOIR_NAMES:
                raise CfmSourceError("CFM-DSS returned an unknown reservoir identifier")
            source_date = _parse_label(row.get(date_field), monthly=monthly)
            identity = (reservoir_id, source_date)
            if identity in identities:
                raise CfmSourceError("CFM-DSS returned duplicate reservoir/date rows")
            identities.add(identity)
            records.append(
                DailyReservoirSnapshot(
                    reservoir_id=reservoir_id,
                    reservoir_name=RESERVOIR_NAMES[reservoir_id],
                    source_date=source_date,
                    observed_at=None,
                    observation_timezone="unknown",
                    time_precision="date",
                    water_level_m=_finite_number(row.get("average_waterlevel"), "water level"),
                    average_storage_mcm=_finite_number(row.get("average_storage"), "storage"),
                    received_at=received_at,
                    source_mode="LIVE",
                    availability="available",
                    freshness="unknown",
                    freshness_note="Dashboard publication cadence and observation-time semantics are unverified.",
                    provenance={
                        "source_id": SOURCE_ID,
                        "endpoint": path,
                        "response_sha256": payload_hash,
                    },
                )
            )
        if not records:
            raise CfmSourceError("CFM-DSS returned no reservoir rows")
        records.sort(key=lambda item: (item.source_date, item.reservoir_id), reverse=True)
        return ReservoirHistory(
            history_kind=kind,
            source_id=SOURCE_ID,
            received_at=received_at,
            availability="available",
            freshness="unknown",
            records=tuple(records),
        )


def main() -> None:
    """On-demand CLI: ``python -m services.trackb.connectors.tn_reservoir``."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--period", choices=("daily", "monthly"), default="daily")
    args = parser.parse_args()
    try:
        client = CfmDashboardClient()
        result = client.fetch_daily_history() if args.period == "daily" else client.fetch_monthly_history()
        json.dump(result.to_dict(), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    except CfmSourceError as exc:
        print(f"CFM-DSS fetch unavailable: {exc}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
