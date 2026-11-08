"""Run the AI service locally with the project data (C4 v3 /v3 on A25 when installed).

From D:\\TIWNGUARD:

    .venv\\Scripts\\python.exe services\\ai-service\\run_local.py

Serves http://127.0.0.1:8000 (loopback only), the same app the packaged /api/ai/ proxy targets. The Vite dev proxy
forwards /api/ai/* here (override its target with TWINGUARD_AI_URL). Every setting below can be overridden by an
environment variable of the same name. Open-Meteo is fetched only on user requests (cached, >= 600 s apart).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "ai-service"
DEFAULTS = {
    "TWINGUARD_V3_RUNS": ROOT / "data/features/v3/runs",
    "TWINGUARD_V3_PRODUCT_STATIC": ROOT / "data/features/v3/product_static_v1",
    "TWINGUARD_LIVE_STATIC": ROOT / "data/features/live/a06_live_static_v1",
    "TWINGUARD_V3_A25_STATIC": ROOT / "data/features/live/a25_static_v1",
    "TWINGUARD_V3_DEVICE": "auto",
    "TWINGUARD_LIVE_SCHEDULE_MIN": "0",
}


def main() -> int:
    for key, value in DEFAULTS.items():
        os.environ.setdefault(key, str(value))
    Path(os.environ["TWINGUARD_V3_RUNS"]).mkdir(parents=True, exist_ok=True)
    os.environ["PYTHONPATH"] = os.pathsep.join([str(SERVICE), str(ROOT), os.environ.get("PYTHONPATH", "")])
    sys.path[:0] = [str(SERVICE), str(ROOT)]
    os.chdir(ROOT)
    import uvicorn

    host = os.environ.get("TWINGUARD_AI_HOST", "127.0.0.1")
    port = int(os.environ.get("TWINGUARD_AI_PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
