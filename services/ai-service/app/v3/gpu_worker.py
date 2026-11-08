"""Persistent engine worker for /v3 (owner decision 2026-11-08, B47 follow-up).

One long-lived child process (``python -m app.v3.worker --serve``) imports torch and warms the CUDA context once,
then runs queued jobs one at a time, so GPU runs skip the 5-20 s cold start. The run manager already runs a single
job at a time, so the 4 GB card still holds at most one GPU job (gpu_jobs_max = 1).

Protocol: one JSON line per job on stdin ({"run_dir": ..., "env": {...}}); the worker answers with one line prefixed
by MARKER on stdout ({"ok": bool, "error": str|None, "seconds": float}). Anything else on stdout is ignored.
If the worker dies, hangs past the run timeout or reports a CUDA failure, the manager restarts it and reruns that job
once on CPU in a per-run child process with ``fallback_reason`` recorded.
"""
from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

MARKER = "@@V3WORKER "
SERVICE_ROOT = Path(__file__).resolve().parents[2]


def _child_env() -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(SERVICE_ROOT), str(SERVICE_ROOT.parents[1]), env.get("PYTHONPATH", "")])
    return env


def job_env() -> dict:
    """Settings the worker must see for each job (the API process may change them, e.g. in tests)."""
    return {k: v for k, v in os.environ.items() if k.startswith("TWINGUARD_")}


class PersistentWorker:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.proc: subprocess.Popen | None = None
        self.lines: queue.Queue[str] = queue.Queue()
        self.state = "cold"  # cold | starting | warm | down
        self.warmup: dict | None = None
        self.device: str | None = None
        self.jobs_done = 0
        self.restarts = 0
        self.started_at: float | None = None

    # ------------------------------------------------------------------------------------------ lifecycle
    def _reader(self, proc: subprocess.Popen) -> None:
        for raw in proc.stdout:  # type: ignore[union-attr]
            if raw.startswith(MARKER):
                self.lines.put(raw[len(MARKER):].strip())
        self.lines.put("__EOF__")

    def start(self, timeout_s: float = 120.0) -> bool:
        self.stop()
        self.state = "starting"
        self.lines = queue.Queue()
        self.proc = subprocess.Popen(  # noqa: S603 - fixed argv
            [sys.executable, "-m", "app.v3.worker", "--serve"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1, env=_child_env(), cwd=str(SERVICE_ROOT))
        threading.Thread(target=self._reader, args=(self.proc,), daemon=True, name="v3-gpu-worker-reader").start()
        hello = self._next(timeout_s)
        if not hello or hello == "__EOF__":
            self.state = "down"
            self.stop()
            return False
        doc = json.loads(hello)
        self.warmup, self.device = doc.get("warmup"), doc.get("device")
        self.state = "warm" if doc.get("device") == "cuda" and not (doc.get("warmup") or {}).get("error") else "cold"
        self.started_at = time.time()
        return True

    def ensure_started_async(self) -> None:
        """Warm the worker in the background (service start / first request) so the first job is already warm."""
        def _go():
            with self.lock:
                if not self.alive():
                    self.start()
        if not self.alive() and self.state != "starting":
            self.state = "starting"
            threading.Thread(target=_go, daemon=True, name="v3-gpu-worker-start").start()

    def stop(self) -> None:
        proc, self.proc = self.proc, None
        if proc and proc.poll() is None:
            try:
                proc.stdin.close()  # type: ignore[union-attr]
                proc.wait(timeout=5)
            except Exception:  # noqa: BLE001
                proc.kill()
        if self.state != "down":
            self.state = "cold"

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def _next(self, timeout_s: float) -> str | None:
        try:
            return self.lines.get(timeout=timeout_s)
        except queue.Empty:
            return None

    # ------------------------------------------------------------------------------------------ jobs
    def run(self, run_dir: Path, timeout_s: float) -> tuple[bool, str | None, bool]:
        """Run one job. Returns (ok, error, worker_failed); worker_failed means crash/hang -> caller falls back."""
        with self.lock:
            if not self.alive() and not self.start():
                return False, "persistent worker failed to start", True
            try:
                self.proc.stdin.write(json.dumps({"run_dir": str(run_dir), "env": job_env()}) + "\n")  # type: ignore[union-attr]
                self.proc.stdin.flush()  # type: ignore[union-attr]
            except (OSError, ValueError):
                self._crashed()
                return False, "persistent worker pipe closed", True
            reply = self._next(timeout_s)
            if reply is None:
                self._crashed()
                return False, "persistent worker timed out", True
            if reply == "__EOF__":
                self._crashed()
                return False, "persistent worker exited", True
            doc = json.loads(reply)
            self.jobs_done += 1
            error = doc.get("error")
            cuda_failure = bool(error) and any(t in error for t in ("CUDA", "cuda", "OutOfMemory", "out of memory"))
            if cuda_failure:  # a poisoned CUDA context: restart the worker before the next job
                self._crashed()
            return bool(doc.get("ok")), error, cuda_failure

    def _crashed(self) -> None:
        self.restarts += 1
        proc, self.proc = self.proc, None
        if proc and proc.poll() is None:
            proc.kill()
        self.state = "down"

    def status(self) -> dict:
        return {"mode": "persistent", "state": self.state if (self.alive() or self.state == "down") else "cold",
                "device": self.device, "pid": self.proc.pid if self.alive() else None, "jobs_done": self.jobs_done,
                "restarts": self.restarts, "warmup": self.warmup}


WORKER = PersistentWorker()


# ------------------------------------------------------------------------------------------------ child side
def serve() -> int:
    """Worker process main loop (``python -m app.v3.worker --serve``)."""
    from . import device as device_mod
    from . import worker

    plan = device_mod.resolve(device_mod.engine_supports_gpu())
    warm: dict = {}
    if plan["used"] == "cuda":
        try:
            from services.flood_engine import hires_torch
            warm = {k: round(v, 3) for k, v in hires_torch.warmup("cuda:0").items()}
        except Exception as error:  # noqa: BLE001 - cold start then; the engine falls back itself
            warm = {"error": f"{type(error).__name__}: {str(error)[:120]}"}
    print(MARKER + json.dumps({"ready": True, "device": plan["used"], "warmup": warm}), flush=True)
    for line in sys.stdin:
        if not line.strip():
            continue
        started = time.time()
        try:
            job = json.loads(line)
            settings = job.get("env") or {}
            for key in [k for k in os.environ if k.startswith("TWINGUARD_") and k not in settings]:
                del os.environ[key]  # each job sees exactly the API's current settings
            os.environ.update(settings)
            worker.execute(Path(job["run_dir"]))
            out = {"ok": True, "error": None}
        except Exception as error:  # noqa: BLE001 - one safe line per job
            out = {"ok": False, "error": f"{type(error).__name__}: {str(error)[:200]}"}
        finally:
            _free_gpu_cache()
        out["seconds"] = round(time.time() - started, 2)
        print(MARKER + json.dumps(out), flush=True)
    return 0


def _free_gpu_cache() -> None:
    torch = sys.modules.get("torch")
    if torch is not None:
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:  # noqa: BLE001
            pass
