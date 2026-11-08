"""Run store and queue for C4 v3: one simulation at a time in a child process, at most 4 queued, identical requests cached."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import config

log = logging.getLogger("twinguard.v3")
SERVICE_ROOT = Path(__file__).resolve().parents[2]  # services/ai-service
PREFIX = {"event": "evt", "custom": "sim", "forecast": "sim", "what_if": "whatif"}
ESTIMATE_S_PER_MEMBER_HOUR = 0.08


class QueueFull(Exception):
    pass


class TooSoon(Exception):
    def __init__(self, retry_after_s: float):
        super().__init__("run-start interval has not elapsed")
        self.retry_after_s = max(1, int(retry_after_s + 0.999))


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write(path: Path, doc: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, allow_nan=False), encoding="utf-8")
    for attempt in range(20):  # Windows: the target may be open by a reader for a moment
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.05 * (attempt + 1))
    os.replace(tmp, path)


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


class RunManager:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.queue: deque[str] = deque()
        self.running: str | None = None
        self.docs: dict[str, dict] = {}
        self.keys: dict[str, str] = {}
        self.root: Path | None = None
        self.last_submit = 0.0
        self.wakeup = threading.Event()
        self.thread: threading.Thread | None = None
        self.frames_cache: dict[str, dict] = {}

    # ------------------------------------------------------------------------------------------ store
    def _ensure(self) -> Path:
        root = config.runs_dir()
        if self.root != root:
            self.root = root
            self.docs.clear()
            self.keys.clear()
            self.queue.clear()
            self.frames_cache.clear()
            self.running = None
            root.mkdir(parents=True, exist_ok=True)
            for path in root.iterdir():
                doc = _read(path / "run.json") if path.is_dir() else None
                if not doc:
                    continue
                if doc["state"] in ("queued", "running"):
                    doc.update(state="failed", error="interrupted by a service restart", completed_at=now_iso(), progress_pct=None)
                    _write(path / "run.json", doc)
                self.docs[doc["run_id"]] = doc
                if doc["state"] == "completed":
                    self.keys[doc["_key"]] = doc["run_id"]
            if not config.inline_worker() and config.worker_mode() == "persistent":
                from .gpu_worker import WORKER
                WORKER.ensure_started_async()
        return root

    def run_dir(self, run_id: str) -> Path:
        return self._ensure() / run_id

    def get(self, run_id: str) -> dict | None:
        with self.lock:
            self._ensure()
            doc = self.docs.get(run_id)
            if doc and doc["state"] == "running":
                progress = _read(self.run_dir(run_id) / "progress.json")
                if progress:
                    doc["progress_pct"] = progress["progress_pct"]
            return doc

    def list(self) -> list[dict]:
        with self.lock:
            self._ensure()
            return sorted(self.docs.values(), key=lambda d: (d["created_at"], d["run_id"]), reverse=True)

    def latest_completed(self) -> dict | None:
        return next((d for d in self.list() if d["state"] == "completed"), None)

    def frames(self, run_id: str) -> dict:
        with self.lock:
            if run_id not in self.frames_cache:
                with np.load(self.run_dir(run_id) / "frames.npz", allow_pickle=False) as z:
                    self.frames_cache[run_id] = {k: z[k] for k in z.files}
                while len(self.frames_cache) > 6:
                    self.frames_cache.pop(next(iter(self.frames_cache)))
            return self.frames_cache[run_id]

    # ------------------------------------------------------------------------------------------ submit
    def submit(self, request: dict, identity: dict, job_extra: dict | None = None) -> tuple[dict, str]:
        """Return (run doc, state) where state is queued|running|cached."""
        key = hashlib.sha256(json.dumps({"request": request, "identity": identity}, sort_keys=True).encode()).hexdigest()
        with self.lock:
            self._ensure()
            existing = self.keys.get(key)
            if existing and existing in self.docs and self.docs[existing]["state"] in ("completed", "queued", "running"):
                doc = self.docs[existing]
                return doc, ("cached" if doc["state"] == "completed" else doc["state"])
            for rid in list(self.queue) + ([self.running] if self.running else []):
                if self.docs[rid]["_key"] == key:
                    return self.docs[rid], self.docs[rid]["state"]
            if len(self.queue) >= config.MAX_QUEUE:
                raise QueueFull()
            wait = config.run_min_interval_s() - (time.time() - self.last_submit)
            if wait > 0:
                raise TooSoon(wait)
            self.last_submit = time.time()
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            run_id = f"{PREFIX[request['mode']]}-{stamp}-{key[:8]}"
            path = self.run_dir(run_id)
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True)
            doc = {
                "run_id": run_id, "state": "queued", "mode": request["mode"], "request": request, "source_mode": "SIMULATED",
                "label": identity.get("label") or request["mode"], "created_at": now_iso(), "completed_at": None,
                "progress_pct": 0.0, "error": None, "frame_interval_minutes": request["frame_interval_minutes"],
                "frames": [], "provenance": {"engine_version": config.ENGINE_VERSION, "run_id": run_id, "inputs": []},
                "limitations": config.LIMITATIONS, "_key": key, "_engine": identity.get("engine", "a06"),
            }
            _write(path / "job.json", {"run_id": run_id, "request": request, **(job_extra or {})})
            _write(path / "run.json", doc)
            self.docs[run_id] = doc
            self.keys[key] = run_id
            self.queue.append(run_id)
            self._start_thread()
            self.wakeup.set()
            return doc, "queued"

    def estimate_s(self, request: dict) -> int:
        if config.a25_enabled():  # measured by Lane A: ~105 s per 24 h citywide 120 m member incl. products
            citywide = request.get("resolution", "citywide") == "citywide"
            from . import device
            if device.resolve(device.engine_supports_gpu())["used"] == "cuda":
                # Measured via /v3 with A26 943ae77 (CUDA graphs), 48 h citywide 120 m: warm persistent worker 17 s end to end,
                # cold per-run child 31 s. Nested focus ~2-3x citywide.
                warm = config.worker_mode() == "persistent"
                per_hour = (0.3 if warm else 0.45) * (1.0 if citywide else 2.5)
                return int(per_hour * request["duration_hours"] * config.a25_members()) + (3 if warm else 10)
            else:
                per_hour = 4.4 if citywide else 20.0  # CPU; focus: 6-26 min per 48 h
            return int(per_hour * request["duration_hours"] * config.a25_members()) + 10
        from .simulate import members
        hours = request["duration_hours"] + 24
        return int(ESTIMATE_S_PER_MEMBER_HOUR * hours * len(members())) + 2

    # ------------------------------------------------------------------------------------------ worker loop
    def _start_thread(self) -> None:
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._loop, daemon=True, name="v3-runs")
            self.thread.start()

    def _loop(self) -> None:
        while True:
            with self.lock:
                run_id = self.queue.popleft() if self.queue else None
                if run_id:
                    self.running = run_id
                    doc = self.docs[run_id]
                    path = self.run_dir(run_id)  # bound now: the store root may change later (tests)
                    doc.update(state="running", progress_pct=0.0)
                    _write(path / "run.json", doc)
            if not run_id:
                self.wakeup.wait(timeout=30)
                self.wakeup.clear()
                with self.lock:
                    if not self.queue:
                        self.thread = None
                        return
                continue
            try:
                ok, error = self._execute(path)
            except Exception as exc:  # noqa: BLE001 - the queue thread must survive any run
                ok, error = False, type(exc).__name__
            with self.lock:
                try:
                    result = _read(path / "result.json") if ok else None
                    if result:
                        doc.update(state="completed", completed_at=now_iso(), progress_pct=100.0, grid=result["grid"],
                                   frames=result["frames"], summary=result["summary"], provenance=result["provenance"],
                                   _engine_run_id=(result.get("diagnostics") or {}).get("engine_run_id"))
                    else:
                        doc.update(state="failed", completed_at=now_iso(), progress_pct=None, error=error or "simulation failed")
                        if self.keys.get(doc["_key"]) == run_id:
                            self.keys.pop(doc["_key"], None)
                    if path.exists():
                        _write(path / "run.json", doc)
                except OSError as exc:
                    log.warning("v3 run %s could not be finalised: %s", run_id, type(exc).__name__)
                finally:
                    if self.running == run_id:
                        self.running = None

    def _execute(self, path: Path) -> tuple[bool, str | None]:
        run_id = path.name
        if config.inline_worker():
            from . import worker
            try:
                worker.execute(path)
                return True, None
            except Exception as error:  # noqa: BLE001
                return False, f"{type(error).__name__}: {str(error)[:200]}"
        if config.worker_mode() == "persistent":
            from .gpu_worker import WORKER
            ok, error, worker_failed = WORKER.run(path, config.run_timeout_s())
            if ok or not worker_failed:
                return ok, error
            log.warning("v3 run %s: persistent worker failed (%s); rerunning on CPU", run_id, error)
            return self._per_run(path, {"TWINGUARD_V3_DEVICE": "cpu",
                                        "TWINGUARD_V3_FALLBACK_REASON": f"{error}; rerun on CPU"[:200]})
        return self._per_run(path)

    def _per_run(self, path: Path, overrides: dict | None = None) -> tuple[bool, str | None]:
        """One child process per run (the original path; also the CPU fallback for the persistent worker)."""
        run_id = path.name
        env = dict(os.environ)
        env.update(overrides or {})
        env["PYTHONPATH"] = os.pathsep.join([str(SERVICE_ROOT), str(SERVICE_ROOT.parents[1]), env.get("PYTHONPATH", "")])
        try:
            proc = subprocess.run([sys.executable, "-m", "app.v3.worker", str(path)], capture_output=True, text=True,  # noqa: S603
                                  timeout=config.run_timeout_s(), env=env, cwd=str(SERVICE_ROOT))
            line = (proc.stdout.strip().splitlines() or ["{}"])[-1]
            doc = json.loads(line) if line.startswith("{") else {"ok": False, "error": "worker produced no result"}
            if not doc.get("ok"):
                log.warning("v3 run %s failed: %s", run_id, doc.get("error"))
            return bool(doc.get("ok")), doc.get("error")
        except subprocess.TimeoutExpired:
            return False, "simulation timed out"
        except Exception as error:  # noqa: BLE001
            return False, type(error).__name__

    def worker_status(self) -> dict:
        if config.inline_worker():
            return {"mode": "inline", "state": "warm", "device": None, "pid": None, "jobs_done": None, "restarts": 0, "warmup": None}
        if config.worker_mode() == "persistent":
            from .gpu_worker import WORKER
            return WORKER.status()
        return {"mode": "per_run", "state": "cold", "device": None, "pid": None, "jobs_done": None, "restarts": 0, "warmup": None}

    def status(self) -> dict:
        with self.lock:
            self._ensure()
            last = self.latest_completed()
            return {"running": self.running is not None, "running_run_id": self.running, "queue_length": len(self.queue),
                    "last_completed_run_id": last["run_id"] if last else None}

    def wait_idle(self, timeout: float = 120.0) -> bool:
        """Test helper: wait until no run is queued or running."""
        end = time.time() + timeout
        while time.time() < end:
            with self.lock:
                if not self.queue and self.running is None:
                    return True
            time.sleep(0.05)
        return False


MANAGER = RunManager()


def public(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if not k.startswith("_")}
