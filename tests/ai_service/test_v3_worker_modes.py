"""B47 follow-up: persistent engine worker vs per-run child processes (runs on CPU-only machines)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "ai-service"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v3_support import assert_contract, build_fixture, custom_request  # noqa: E402

from app import main  # noqa: E402
from app.v3 import config, static  # noqa: E402
from app.v3.gpu_worker import WORKER  # noqa: E402
from app.v3.runs import MANAGER  # noqa: E402

RUN = "/v3/simulations/{run_id}"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    grid_dir, product_dir = build_fixture(tmp_path)
    for key, value in {"TWINGUARD_LIVE_STATIC": str(grid_dir), "TWINGUARD_V3_PRODUCT_STATIC": str(product_dir),
                       "TWINGUARD_V3_RUNS": str(tmp_path / "runs"), "TWINGUARD_V3_INLINE_WORKER": "0",
                       "TWINGUARD_V3_MEMBERS": "1", "TWINGUARD_V3_RUN_MIN_INTERVAL_S": "0",
                       "TWINGUARD_V3_ENGINE": "a06", "TWINGUARD_V3_DEVICE_PROBE": "0"}.items():
        monkeypatch.setenv(key, value)
    static.clear_cache()
    yield TestClient(main.app)
    MANAGER.wait_idle(120)
    WORKER.stop()
    static.clear_cache()


def _run(client, values) -> dict:
    accepted = client.post("/v3/simulations", json=custom_request(values, hours=6))
    assert accepted.status_code == 202, accepted.text
    assert MANAGER.wait_idle(120)
    return client.get(RUN.format(run_id=accepted.json()["run_id"])).json()


def test_default_mode_is_per_run_without_cuda(env, monkeypatch):
    monkeypatch.delenv("TWINGUARD_V3_WORKER", raising=False)
    assert config.worker_mode() == "per_run"  # A06 engine / no CUDA
    status = assert_contract(env.get("/v3/status"), "/v3/status")
    assert status["worker"]["mode"] == "per_run"
    run = _run(env, [5.0, 5.0])
    assert run["state"] == "completed" and run["provenance"]["device"]["used"] == "cpu"


def test_persistent_worker_reuses_one_process(env, monkeypatch):
    monkeypatch.setenv("TWINGUARD_V3_WORKER", "persistent")
    first = _run(env, [6.0, 6.0])
    pid = WORKER.status()["pid"]
    second = _run(env, [7.0, 7.0])
    assert first["state"] == second["state"] == "completed", (first.get("error"), second.get("error"))
    status = env.get("/v3/status").json()["worker"]
    assert status["mode"] == "persistent" and status["pid"] == pid and status["jobs_done"] == 2
    assert status["state"] == "cold" and status["device"] == "cpu"  # no CUDA warm-up for the CPU engine


def test_persistent_worker_restarts_after_it_dies(env, monkeypatch):
    monkeypatch.setenv("TWINGUARD_V3_WORKER", "persistent")
    assert _run(env, [3.0])["state"] == "completed"
    WORKER.proc.kill()  # simulate a crash between jobs
    WORKER.proc.wait(timeout=10)
    run = _run(env, [4.0])
    assert run["state"] == "completed" and run["provenance"]["device"]["fallback_reason"] is None
    assert WORKER.status()["pid"] is not None


def test_worker_failure_reruns_job_once_on_cpu(env, monkeypatch):
    monkeypatch.setenv("TWINGUARD_V3_WORKER", "persistent")
    monkeypatch.setattr(WORKER, "run", lambda path, timeout: (False, "RuntimeError: CUDA error: out of memory", True))
    run = _run(env, [8.0, 1.0])
    assert run["state"] == "completed"
    assert run["provenance"]["device"] == {"used": "cpu", "name": None,
                                           "fallback_reason": "RuntimeError: CUDA error: out of memory; rerun on CPU"}
