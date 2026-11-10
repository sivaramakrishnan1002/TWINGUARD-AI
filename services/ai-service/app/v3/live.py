"""Live forecast mode (OD-2026-11-10 / CR-021, B51): a 3 h cycle of Open-Meteo forecast -> engine -> latest live run.

Each cycle, under one live lock (never overlapping):
1. Fetch the A23 multi-model Open-Meteo lattice. Upstream calls are counted per UTC day and the cycle stops before
   5,000; A23's fetcher backs off once on HTTP 429.
2. Reuse the CFM-DSS reservoir snapshot if it is under 24 h old, otherwise read it once (B41 client).
3. Apply the reservoir coupling rule. Until A28 lands this is a labelled stub with zero inflow; the inflows are
   model assumptions and are never shown as observed releases.
4. Run the engine for 72 h citywide (persistent GPU worker when available, CPU fallback) as mode "live",
   run_kind LIVE_FORECAST, and publish it as the latest live run. Keep the last 16 live runs; prune only live runs.
On failure the last good run keeps being served and last_error is set. Every live response carries DISCLAIMER.
Results stay source_mode SIMULATED; inputs keep MODEL_FORECAST / PUBLISHED_SNAPSHOT.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from . import config

log = logging.getLogger("twinguard.v3.live")
DISCLAIMER = "Model forecast — not an official warning"
CYCLE_HOURS = 3
KEEP_LAST = 16
MANUAL_MIN_INTERVAL_S = 600
DAILY_CALL_BUDGET = 5000
RESERVOIR_MAX_AGE_S = 24 * 3600
HORIZON_HOURS = 72
COUPLING_RULE_STUB = "A28-pending: zero reservoir inflow (stub, assumption)"  # engines without A28 (A06 pilot)
LIVE_REQUEST = {"mode": "live", "duration_hours": HORIZON_HOURS, "resolution": "citywide", "frame_interval_minutes": 30}


def enabled() -> bool:
    """TWINGUARD_V3_LIVE=0 disables live mode (endpoints answer 503, no scheduler)."""
    return os.environ.get("TWINGUARD_V3_LIVE", "1") != "0"


def iso(dt: datetime | None) -> str | None:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def parse(text: str | None) -> datetime | None:
    return datetime.fromisoformat(text.replace("Z", "+00:00")) if text else None


class LiveBusy(Exception):
    pass


class LiveRateLimited(Exception):
    def __init__(self, retry_after_s: int):
        super().__init__("manual refresh minimum interval not elapsed")
        self.retry_after_s = max(1, int(retry_after_s))


class LiveUnavailable(Exception):
    pass


def _default_forecast_fetch(bounds):
    from services.flood_engine import forcing as fm
    return fm.fetch_snapshot(bounds)  # A23 multi-model lattice; one polite retry on 429 inside


def _default_reservoir_fetch() -> dict:
    from services.trackb.connectors.tn_reservoir.client import CfmDashboardClient
    history = CfmDashboardClient(timeout_seconds=15.0).fetch_daily_history()
    doc = history.to_dict()
    dates = sorted(r["source_date"] for r in doc["records"])
    return {"received_at": doc["received_at"], "source_date": dates[-1] if dates else None, "records": doc["records"]}


def estimated_forecast_calls(bounds) -> int:
    from services.flood_engine import forcing as fm
    lat, _ = fm.lattice(bounds)
    return int(len(lat)) * len(fm.MODELS)


class LiveScheduler:
    def __init__(self, clock: Callable[[], datetime] | None = None, fetch_forecast=None, fetch_reservoir=None,
                 forecast_calls: Callable[[list], int] | None = None, reservoir_calls: int = 2):
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.fetch_forecast = fetch_forecast or _default_forecast_fetch
        self.fetch_reservoir = fetch_reservoir or _default_reservoir_fetch
        self.forecast_calls = forecast_calls or estimated_forecast_calls
        self.reservoir_calls = reservoir_calls  # dashboard token page + history request
        self.lock = threading.Lock()   # the single live lock: no overlapping cycles
        self.state_lock = threading.Lock()
        self.running_run_id: str | None = None
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    # ------------------------------------------------------------------------------------------ state
    def _dir(self) -> Path:
        path = config.runs_dir() / "_live"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def load(self) -> dict:
        try:
            return json.loads((self._dir() / "state.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"runs": [], "calls": {}, "sources": {"open_meteo": {}, "cfm_dss": {}}}

    def save(self, st: dict) -> None:
        tmp = self._dir() / "state.tmp"
        tmp.write_text(json.dumps(st), encoding="utf-8")
        for attempt in range(20):
            try:
                os.replace(tmp, self._dir() / "state.json")
                return
            except PermissionError:
                time.sleep(0.05 * (attempt + 1))
        os.replace(tmp, self._dir() / "state.json")

    def _calls(self, st: dict, source: str, now: datetime) -> int:
        return int(st.get("calls", {}).get(now.strftime("%Y-%m-%d"), {}).get(source, 0))

    def _add_calls(self, st: dict, source: str, now: datetime, n: int) -> None:
        day = now.strftime("%Y-%m-%d")
        calls = {d: v for d, v in st.get("calls", {}).items() if d >= (now - timedelta(days=2)).strftime("%Y-%m-%d")}
        calls.setdefault(day, {}).setdefault(source, 0)
        calls[day][source] += int(n)
        st["calls"] = calls

    # ------------------------------------------------------------------------------------------ schedule
    def due(self, now: datetime | None = None) -> str | None:
        """Cycle kind that is due now (catch_up / scheduled), or None."""
        now = now or self.clock()
        last = parse(self.load().get("last_cycle_at"))
        if last is None or now - last >= timedelta(hours=2 * CYCLE_HOURS):
            return "catch_up"
        if now - last >= timedelta(hours=CYCLE_HOURS):
            return "scheduled"
        return None

    def next_scheduled_at(self, now: datetime | None = None) -> datetime | None:
        if not enabled():
            return None
        now = now or self.clock()
        last = parse(self.load().get("last_cycle_at"))
        return now if last is None else max(now, last + timedelta(hours=CYCLE_HOURS))

    def start(self) -> None:
        """Background loop for the AI-service process (not started in tests)."""
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._loop, daemon=True, name="v3-live-scheduler")
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                if enabled():
                    kind = self.due()
                    if kind:
                        self.run_cycle(kind)
            except LiveBusy:
                pass
            except Exception:  # noqa: BLE001 - the loop must survive any cycle
                log.exception("live cycle crashed")
            nxt = self.next_scheduled_at()
            wait = 60.0 if nxt is None else min(60.0, max(1.0, (nxt - self.clock()).total_seconds()))
            self.stop_event.wait(wait)

    # ------------------------------------------------------------------------------------------ manual refresh
    def refresh(self, background: bool = True) -> dict:
        if not enabled():
            raise LiveUnavailable("Live mode is disabled (TWINGUARD_V3_LIVE=0).")
        now = self.clock()
        with self.state_lock:
            st = self.load()
            last = parse(st.get("last_manual_at"))
            if last and (now - last).total_seconds() < MANUAL_MIN_INTERVAL_S:
                raise LiveRateLimited(MANUAL_MIN_INTERVAL_S - (now - last).total_seconds())
            if self.lock.locked():
                return {"accepted": False, "state": "already_running", "run_id": self.running_run_id,
                        "next_allowed_at": iso(last + timedelta(seconds=MANUAL_MIN_INTERVAL_S)) if last else None,
                        "disclaimer": DISCLAIMER}
            budget = self._budget_left(st, now)
            if budget is not None:
                raise LiveUnavailable(budget)
            st["last_manual_at"] = iso(now)
            self.save(st)
        if background:
            threading.Thread(target=self._safe_cycle, args=("manual",), daemon=True, name="v3-live-manual").start()
        else:
            self._safe_cycle("manual")
        return {"accepted": True, "state": "started", "run_id": None,
                "next_allowed_at": iso(now + timedelta(seconds=MANUAL_MIN_INTERVAL_S)), "disclaimer": DISCLAIMER}

    def _safe_cycle(self, kind: str) -> None:
        try:
            self.run_cycle(kind)
        except LiveBusy:
            pass
        except Exception:  # noqa: BLE001
            log.exception("live cycle crashed")

    def _budget_left(self, st: dict, now: datetime) -> str | None:
        from . import static
        need = self.forecast_calls(static.grid("citywide").bounds_lonlat)
        used = self._calls(st, "open_meteo", now)
        if used + need >= DAILY_CALL_BUDGET:
            return f"Open-Meteo daily budget reached ({used} calls today; limit {DAILY_CALL_BUDGET}); serving the last good run."
        return None

    # ------------------------------------------------------------------------------------------ cycle
    def run_cycle(self, kind: str) -> str | None:
        """One live cycle; returns the published run_id or None. Raises LiveBusy if a cycle is running."""
        if not self.lock.acquire(blocking=False):
            raise LiveBusy()
        try:
            return self._cycle(kind)
        finally:
            self.running_run_id = None
            self.lock.release()

    def _fail(self, st: dict, now: datetime, stage: str, message: str, run_id: str | None = None) -> None:
        st["last_error"] = {"at": iso(now), "stage": stage, "message": message[:300], "run_id": run_id}
        self.save(st)
        log.warning("live cycle failed at %s: %s", stage, message)

    def _cycle(self, kind: str) -> str | None:
        from . import device, static, weather
        from .runs import MANAGER, QueueFull, TooSoon

        now = self.clock()
        with self.state_lock:
            st = self.load()
            st["last_cycle_at"] = iso(now)  # recorded at start: a failing cycle waits for the next slot
            st["last_cycle_kind"] = kind
            self.save(st)
        grid = static.grid("citywide")
        bounds = grid.bounds_lonlat
        sources = st.setdefault("sources", {"open_meteo": {}, "cfm_dss": {}})

        # 1 forecast grid (budgeted)
        budget = self._budget_left(st, now)
        if budget:
            sources["open_meteo"].update(last_attempt_at=iso(now), last_error="daily budget reached")
            self._fail(st, now, "fetch_forecast", budget)
            return None
        sources["open_meteo"]["last_attempt_at"] = iso(now)
        self._add_calls(st, "open_meteo", now, self.forecast_calls(bounds))
        try:
            snapshot = self.fetch_forecast(bounds)
            if not snapshot.usable:
                raise RuntimeError("no usable weather model")
        except Exception as error:  # noqa: BLE001 - credential-free message only
            sources["open_meteo"]["last_error"] = f"{type(error).__name__}"[:120]
            self._fail(st, now, "fetch_forecast", f"Open-Meteo fetch failed ({type(error).__name__})")
            return None
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        snap_path = self._dir() / f"forecast_{stamp}.npz"
        meta = weather.save_snapshot(snapshot, snap_path)
        model = snapshot.usable[0]
        valid_from = datetime.fromisoformat(model.times_utc[_past_hours()]).replace(tzinfo=timezone.utc) - timedelta(hours=1)
        sources["open_meteo"].update(last_success_at=iso(now), data_time=iso(valid_from), last_error=None)

        # 2 reservoir snapshot (at most daily)
        reservoir = st.get("reservoir")
        age = (now - parse(reservoir["received_at"])).total_seconds() if reservoir and reservoir.get("received_at") else None
        if age is None or age >= RESERVOIR_MAX_AGE_S:
            sources["cfm_dss"]["last_attempt_at"] = iso(now)
            self._add_calls(st, "cfm_dss", now, self.reservoir_calls)
            try:
                fetched = self.fetch_reservoir()
                reservoir = {**fetched, "sha256": hashlib.sha256(json.dumps(fetched.get("records"), sort_keys=True).encode()).hexdigest()}
                st["reservoir"] = reservoir
                sources["cfm_dss"].update(last_success_at=iso(now), data_time=reservoir.get("source_date"), last_error=None)
            except Exception as error:  # noqa: BLE001 - the cycle continues with the older snapshot, if any
                sources["cfm_dss"]["last_error"] = f"{type(error).__name__}"[:120]
        self.save(st)

        # 3 coupling: the engine applies A28 (A28-RES-STORAGE-v1) to the snapshot; the A06 pilot has none (stub label).
        coupling_rule = COUPLING_RULE_STUB
        reservoir_body = {"records": reservoir["records"], "received_at": reservoir.get("received_at")} if reservoir else None

        # 4 engine run
        engine = "a25" if config.a25_enabled() else "a06"
        identity = {"label": f"Live forecast {iso(now)}", "engine": engine, "live_cycle_at": iso(now),
                    "forcing": meta.get("forcing_sha256"),
                    "device": device.resolve(device.engine_supports_gpu())["used"] if engine == "a25" else "cpu"}
        if engine == "a25":
            from services.flood_engine import scenario as _scenario
            identity["engine_version"] = getattr(_scenario, "ENGINE_VERSION", "unknown")
        live_block = {"cycle": kind, "issued_at": snapshot.fetched_at, "forecast_valid_from": iso(valid_from),
                      "forecast_valid_to": iso(valid_from + timedelta(hours=HORIZON_HOURS)),
                      "reservoir_snapshot_received_at": (reservoir or {}).get("received_at"),
                      "reservoir_source_date": (reservoir or {}).get("source_date"),
                      "reservoir_coupling_rule": coupling_rule, "disclaimer": DISCLAIMER}
        extra_inputs = [{"name": "reservoirs", "source": "cfm-dss:GetLast15daysWaterLevel", "source_mode": "PUBLISHED_SNAPSHOT",
                         "fetched_at": (reservoir or {}).get("received_at"), "sha256": (reservoir or {}).get("sha256")}] if reservoir else []
        run_id = None
        for attempt in range(3):
            try:
                doc, _state = MANAGER.submit(dict(LIVE_REQUEST), {**identity, "reservoir": (reservoir or {}).get("sha256")},
                                             {"engine": engine, "live_snapshot": str(snap_path), "live": live_block,
                                              "live_reservoir": reservoir_body, "live_run_time": iso(now)})
                run_id = doc["run_id"]
                break
            except TooSoon as error:
                time.sleep(min(error.retry_after_s, 5))
            except QueueFull:
                self._fail(st, now, "engine", "engine queue is full; serving the last good run")
                return None
        if run_id is None:
            self._fail(st, now, "engine", "could not start the live run")
            return None
        self.running_run_id = run_id
        MANAGER.annotate(run_id, live=live_block, _live_inputs=extra_inputs)
        deadline = time.time() + config.run_timeout_s() + 120
        doc = MANAGER.get(run_id)
        while doc and doc["state"] in ("queued", "running") and time.time() < deadline:
            time.sleep(1.0)
            doc = MANAGER.get(run_id)
        if not doc or doc["state"] != "completed":
            self._fail(st, now, "engine", f"live run {doc['state'] if doc else 'missing'}: {(doc or {}).get('error') or ''}".strip(), run_id)
            return None

        coupling = _engine_coupling(MANAGER.run_dir(run_id))
        if coupling:
            live_block = {**live_block, "reservoir_coupling_rule": f"{coupling.get('rule_id')} ({str(coupling.get('status', '')).split(':')[0]})"}
            MANAGER.annotate(run_id, live=live_block)

        # 5 publish + retention
        with self.state_lock:
            st = self.load()
            runs = [r for r in st.get("runs", []) if r != run_id] + [run_id]
            for old in runs[:-KEEP_LAST]:
                MANAGER.delete_run(old)  # live runs only; event/what-if/custom runs are never touched here
            for stale in sorted(self._dir().glob("forecast_*.npz"))[:-KEEP_LAST]:
                stale.unlink(missing_ok=True)
            st["runs"] = runs[-KEEP_LAST:]
            st["last_good_run_id"] = run_id
            st["last_error"] = None
            self.save(st)
        return run_id

    # ------------------------------------------------------------------------------------------ views
    def latest(self) -> dict | None:
        from .runs import MANAGER
        st = self.load()
        run_id = st.get("last_good_run_id")
        doc = MANAGER.get(run_id) if run_id else None
        if not doc or doc["state"] != "completed":
            return None
        live = doc.get("live") or {}
        prov = doc.get("provenance") or {}
        engine_inputs = [i for i in prov.get("inputs", []) if i.get("source_mode") != "STATIC_REFERENCE"]
        has_reservoir = any(i.get("name") == "reservoir_snapshot" for i in engine_inputs)  # A28 engine reports its own
        extra = [] if has_reservoir else doc.get("_live_inputs", [])
        from .runs import utc_z
        inputs = [{**{k: i.get(k) for k in ("name", "source", "source_mode")}, "fetched_at": utc_z(i.get("fetched_at"))}
                  for i in engine_inputs + extra]
        return {"run_id": run_id, "run_kind": "LIVE_FORECAST", "state": "completed",
                "issued_at": utc_z(live.get("issued_at") or doc["created_at"]), "completed_at": doc.get("completed_at"),
                "forecast_valid_from": live.get("forecast_valid_from"), "forecast_valid_to": live.get("forecast_valid_to"),
                "horizon_hours": HORIZON_HOURS, "summary": doc.get("summary"), "inputs": inputs,
                "device": (prov.get("device") or {}).get("used"), "disclaimer": DISCLAIMER}

    def status(self) -> dict:
        now = self.clock()
        st = self.load()
        on = enabled()
        last_manual = parse(st.get("last_manual_at"))
        manual_next = last_manual + timedelta(seconds=MANUAL_MIN_INTERVAL_S) if last_manual else None
        sources = {}
        for name, policy in (("open_meteo", "every 3 h + manual (min 600 s)"), ("cfm_dss", "at most daily")):
            src = (st.get("sources") or {}).get(name) or {}
            if not on:
                state = "disabled"
            elif src.get("last_error"):
                state = "error"
            elif src.get("last_success_at"):
                limit = RESERVOIR_MAX_AGE_S if name == "cfm_dss" else 2 * CYCLE_HOURS * 3600
                state = "ok" if (now - parse(src["last_success_at"])).total_seconds() < limit else "stale"
            else:
                state = "unknown"
            sources[name] = {"state": state, "refresh_policy": policy, "last_success_at": src.get("last_success_at"),
                             "last_attempt_at": src.get("last_attempt_at"), "data_time": src.get("data_time"),
                             "last_error": src.get("last_error"), "calls_today": self._calls(st, name, now)}
        latest = self.latest() if on else None
        return {"enabled": on, "cycle_hours": CYCLE_HOURS,
                "state": "disabled" if not on else ("running" if self.lock.locked() else "idle"),
                "running_run_id": self.running_run_id, "latest": latest, "last_good_run_id": st.get("last_good_run_id"),
                "next_scheduled_at": iso(self.next_scheduled_at(now)),
                "manual_refresh": {"min_interval_s": MANUAL_MIN_INTERVAL_S,
                                   "next_allowed_at": iso(manual_next) if manual_next and manual_next > now else None},
                "sources": sources, "last_error": st.get("last_error"),
                "retention": {"keep_last": KEEP_LAST, "stored": len(st.get("runs", []))}, "disclaimer": DISCLAIMER}


def _engine_coupling(run_dir: Path) -> dict | None:
    try:
        return (json.loads((run_dir / "result.json").read_text(encoding="utf-8")).get("diagnostics") or {}).get("reservoir_coupling")
    except (OSError, ValueError):
        return None


def _past_hours() -> int:
    from services.flood_engine import forcing as fm
    return fm.PAST_HOURS


SCHEDULER = LiveScheduler()
