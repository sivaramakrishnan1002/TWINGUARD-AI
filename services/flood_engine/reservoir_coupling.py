"""A28: CFM-DSS reservoir snapshot -> reservoir outlet inflow hydrographs (documented ASSUMPTION rule).

CFM-DSS publishes daily water level and storage, never releases. The inflows produced here are therefore model
assumptions derived from storage, labelled ``ASSUMPTION`` everywhere, and must never be shown as observed or
published releases (CR-016 as amended by CR-021). ``source_date`` stays date-only (C3): no time of day is invented.

Rule ``A28-RES-STORAGE-v1`` (per reservoir, constant over the run):
    pct = storage_mcm / capacity_mcm * 100      (storage % from the snapshot if given, else from nominal capacity)
    pct <  90           -> 0 m3/s                                (reservoir absorbs inflow)
    90 <= pct < 100     -> Q_ctrl * (pct - 90) / 10                (controlled release ramps up)
    pct >= 100          -> Q_spill = 2 * Q_ctrl                   (surplus / spill)
The snapshot is ignored (zero inflow for every reservoir) when it is missing, unparseable, or stale:
``source_date`` more than 2 calendar days before the run date, or received more than 48 h before the run.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone

RULE_ID = "A28-RES-STORAGE-v1"
STALE_HOURS = 48
# Nominal full-reservoir capacity (MCM; 1 TMC = 28.317 MCM) and assumed controlled-release maximum (m3/s).
# Capacities: WRD/CMWSSB published nominal values; Q_ctrl: assumption (order of the 2015/2023 surplus releases
# reported in news/CAG narrative, reduced for a controlled release). Thervoy Kandigai has no outlet in the A25 grid.
RESERVOIRS = {
    "CHEMBARAMBAKKAM": {"capacity_mcm": 3.645 * 28.317, "q_ctrl_m3s": 170.0, "aliases": ("chembarambakkam",)},
    "POONDI": {"capacity_mcm": 3.231 * 28.317, "q_ctrl_m3s": 140.0, "aliases": ("poondi",)},
    "PUZHAL": {"capacity_mcm": 3.300 * 28.317, "q_ctrl_m3s": 60.0, "aliases": ("puzhal", "red hills", "redhills")},
    "CHOLAVARAM": {"capacity_mcm": 1.081 * 28.317, "q_ctrl_m3s": 30.0, "aliases": ("cholavaram",)},
}
THRESHOLD_PCT = 90.0
SPILL_FACTOR = 2.0


def parameters() -> dict:
    return {"rule_id": RULE_ID, "threshold_pct": THRESHOLD_PCT, "spill_factor": SPILL_FACTOR, "stale_hours": STALE_HOURS,
            "reservoirs": {k: {"capacity_mcm": round(v["capacity_mcm"], 2), "q_ctrl_m3s": v["q_ctrl_m3s"]} for k, v in RESERVOIRS.items()},
            "basis": "ASSUMPTION: storage-threshold release; CFM-DSS publishes no release data"}


def release_for(pct: float, q_ctrl: float) -> float:
    if pct < THRESHOLD_PCT:
        return 0.0
    if pct < 100.0:
        return round(q_ctrl * (pct - THRESHOLD_PCT) / (100.0 - THRESHOLD_PCT), 3)
    return round(SPILL_FACTOR * q_ctrl, 3)


def _key(name: str) -> str | None:
    n = (name or "").strip().lower()
    for key, spec in RESERVOIRS.items():
        if n in spec["aliases"] or n == key.lower():
            return key
    return None


def _parse_date(value) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _parse_instant(value) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _records(snapshot) -> tuple[list[dict], str | None]:
    """Accept the B44 /reservoirs/history body ({records:[...], received_at}) or a plain list of records."""
    if isinstance(snapshot, dict):
        return list(snapshot.get("records") or []), snapshot.get("received_at")
    if isinstance(snapshot, list):
        return snapshot, None
    return [], None


def couple(snapshot, run_time: datetime | None = None) -> dict:
    """Return the coupling result: rule id, parameters, per-reservoir rows, releases_m3s and status."""
    run_time = run_time or datetime.now(timezone.utc)
    base = {"rule_id": RULE_ID, "parameters": parameters(), "releases_m3s": {k: 0.0 for k in RESERVOIRS},
            "reservoirs": [], "basis": "ASSUMPTION", "source": "CFM-DSS public dashboard (PUBLISHED_SNAPSHOT; no release data)"}
    if not snapshot:
        return {**base, "status": "zero_inflow_missing_snapshot", "snapshot_sha256": None}
    records, received = _records(snapshot)
    sha = hashlib.sha256(json.dumps(snapshot, sort_keys=True, default=str).encode()).hexdigest()
    latest: dict[str, dict] = {}
    for rec in records:
        key = _key(rec.get("reservoir_name") or rec.get("name") or rec.get("reservoir_id", ""))
        d = _parse_date(rec.get("source_date"))
        if key is None or d is None:
            continue
        if key not in latest or d > latest[key]["_date"]:
            latest[key] = {**rec, "_date": d}
    if not latest:
        return {**base, "status": "zero_inflow_unparseable_snapshot", "snapshot_sha256": sha}
    newest = max(r["_date"] for r in latest.values())
    received_at = _parse_instant(received or next((r.get("received_at") for r in latest.values() if r.get("received_at")), None))
    age_days = (run_time.astimezone(timezone.utc).date() - newest).days
    stale_reason = None
    if age_days > STALE_HOURS // 24:
        stale_reason = f"source_date {newest.isoformat()} is {age_days} days before the run date"
    elif received_at is not None and (run_time - received_at).total_seconds() > STALE_HOURS * 3600:
        stale_reason = f"snapshot received {received_at.isoformat()} is more than {STALE_HOURS} h before the run"
    rows, releases = [], {k: 0.0 for k in RESERVOIRS}
    for key, spec in RESERVOIRS.items():
        rec = latest.get(key)
        if rec is None:
            rows.append({"reservoir": key, "status": "absent_from_snapshot", "release_m3s": 0.0})
            continue
        storage = rec.get("average_storage_mcm", rec.get("storage_mcm"))
        pct = rec.get("storage_pct")
        try:
            storage = None if storage is None else float(storage)
            pct = float(pct) if pct is not None else (None if storage is None else 100.0 * storage / spec["capacity_mcm"])
        except (TypeError, ValueError):
            storage, pct = None, None
        if pct is None or pct < 0:
            rows.append({"reservoir": key, "status": "invalid_storage", "release_m3s": 0.0, "source_date": rec["_date"].isoformat()})
            continue
        q = 0.0 if stale_reason else release_for(pct, spec["q_ctrl_m3s"])
        releases[key] = q
        rows.append({"reservoir": key, "source_date": rec["_date"].isoformat(), "time_precision": "date",
                     "water_level_m": rec.get("water_level_m", rec.get("level_m")), "storage_mcm": storage,
                     "storage_pct": round(pct, 2), "release_m3s": q, "release_basis": "ASSUMPTION",
                     "status": "stale_ignored" if stale_reason else "applied"})
    return {**base, "status": f"zero_inflow_stale_snapshot: {stale_reason}" if stale_reason else "applied",
            "snapshot_sha256": sha, "snapshot_source_date": newest.isoformat(),
            "snapshot_received_at": received_at.isoformat() if received_at else None,
            "reservoirs": rows, "releases_m3s": releases}
