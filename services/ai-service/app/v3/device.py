"""Compute-device selection for /v3 engine runs (OD-2026-11-08): GPU when it helps, CPU always supported.

TWINGUARD_V3_DEVICE = auto (default) | cuda | cpu. ``auto`` picks CUDA when it is available and the engine accepts a
device. Only one simulation runs at a time (runs.RunManager), so at most one GPU job uses the 4 GB card. A CUDA failure
is retried once on CPU and recorded as ``fallback_reason``. CUDA is probed in a short child process so the API process
never imports torch.
"""
from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
import threading

_LOCK = threading.Lock()
_PROBE: dict | None = None
PROBE_CODE = (
    "import json\n"
    "out={'cuda_available':False,'name':None,'backend':None}\n"
    "try:\n"
    " from services.flood_engine import gpu\n"
    " ok,name=gpu.available(); out.update(cuda_available=bool(ok),name=name,backend='flood_engine.gpu')\n"
    "except Exception:\n"
    " try:\n"
    "  import torch\n"
    "  if torch.cuda.is_available(): out.update(cuda_available=True,name=torch.cuda.get_device_name(0),backend='torch')\n"
    " except Exception: pass\n"
    "print(json.dumps(out))\n"
)


def requested() -> str:
    value = os.environ.get("TWINGUARD_V3_DEVICE", "auto").strip().lower()
    return value if value in ("auto", "cuda", "cpu") else "auto"


def probe(refresh: bool = False) -> dict:
    """{'cuda_available': bool, 'name': str|None, 'backend': str|None}; cached for the process lifetime."""
    global _PROBE
    with _LOCK:
        if _PROBE is not None and not refresh:
            return dict(_PROBE)
        result = {"cuda_available": False, "name": None, "backend": None}
        if requested() != "cpu" and os.environ.get("TWINGUARD_V3_DEVICE_PROBE", "1") == "1":
            try:
                proc = subprocess.run([sys.executable, "-c", PROBE_CODE], capture_output=True, text=True, timeout=60,  # noqa: S603
                                      env=_child_env())
                line = (proc.stdout.strip().splitlines() or ["{}"])[-1]
                result.update(json.loads(line) if line.startswith("{") else {})
            except Exception:  # noqa: BLE001 - no CUDA information means CPU
                pass
        _PROBE = result
        return dict(result)


def _child_env() -> dict:
    from pathlib import Path
    service = Path(__file__).resolve().parents[2]
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(service), str(service.parents[1]), env.get("PYTHONPATH", "")])
    return env


def engine_accepts_device(func) -> bool:
    try:
        return "device" in inspect.signature(func).parameters
    except (TypeError, ValueError):
        return False


def resolve(engine_supports_gpu: bool) -> dict:
    """Return {'requested', 'used', 'name', 'reason'} for the next run (before any CUDA failure)."""
    want = requested()
    info = probe() if want != "cpu" else {"cuda_available": False, "name": None}
    if want == "cpu":
        return {"requested": want, "used": "cpu", "name": None, "reason": None}
    if not engine_supports_gpu:
        return {"requested": want, "used": "cpu", "name": None, "reason": "engine has no GPU backend"}
    if not info["cuda_available"]:
        return {"requested": want, "used": "cpu", "name": None, "reason": "CUDA not available" if want == "cuda" else None}
    return {"requested": want, "used": "cuda", "name": info["name"], "reason": None}


def engine_supports_gpu() -> bool:
    """Only Lane A's A25 runner can take a device; the A06 pilot driver is NumPy-only."""
    from . import config
    if not config.a25_enabled():
        return False
    from services.flood_engine import scenario  # noqa: PLC0415 - optional engine
    return engine_accepts_device(scenario.run_scenario)


def status() -> dict:
    """Device summary for GET /v3/status (reported in engine_version until the contract adds a field)."""
    supports = engine_supports_gpu()
    plan = resolve(supports)
    info = probe() if requested() != "cpu" else {"cuda_available": False, "name": None}
    return {"requested": plan["requested"], "resolved": plan["used"], "name": plan["name"] or info.get("name"),
            "cuda_available": bool(info.get("cuda_available")), "engine_gpu_backend": supports, "gpu_jobs_max": 1}


def label(device: dict) -> str:
    if device.get("used") == "cuda":
        return f"cuda: {device.get('name') or 'GPU'}"
    return "cpu" + (f"; fallback: {device['reason']}" if device.get("reason") else "")
