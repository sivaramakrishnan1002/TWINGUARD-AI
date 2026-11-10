"""B53 (CR-021) packaged live-cycle verification through nginx /api/ai/v3/live/*.

Phases (run in order against the packaged B11 stack; each phase appends to docs/trackb/B53_LIVE_CYCLE_EVIDENCE.json):

    python tests/e2e/b53_live_cycle.py catchup   # fresh run store: start-up catch-up + already_running during it
    python tests/e2e/b53_live_cycle.py refresh   # manual refresh 202 + second refresh within 600 s -> 429
    python tests/e2e/b53_live_cycle.py failure   # with HTTPS_PROXY pointed at a closed port: last-good + last_error
    python tests/e2e/b53_live_cycle.py final     # disclaimer bytes/charset, retention, key scan

Not collected by pytest. Bodies are validated against C4 v3 (tests/ai_service/v3_support.validate).
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "ai_service"))
from v3_support import response_schema, validate  # noqa: E402

BASE = "http://127.0.0.1:8081/api/ai"
OUT = ROOT / "docs/trackb/B53_LIVE_CYCLE_EVIDENCE.json"
RUN_STORE = ROOT / "data/features/v3/runs_b53"
DISCLAIMER = "Model forecast — not an official warning"
FORBIDDEN = (b"AIza", b"VITE_GOOGLE", b"GOOGLE_MAPS")
http = httpx.Client(timeout=120.0)
scanned: list[bytes] = []


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def call(method: str, path: str, spec: str | None = None, **kw) -> dict:
    t0 = time.perf_counter()
    r = http.request(method, BASE + path, **kw)
    scanned.append(r.content)
    doc = None
    try:
        doc = r.json()
    except ValueError:
        pass
    errors = None
    if spec:
        try:
            errors = validate(doc, response_schema(spec, method, r.status_code))[:10]
        except KeyError:
            errors = [f"status {r.status_code} not in contract"]
    return {"status": r.status_code, "seconds": round(time.perf_counter() - t0, 3), "bytes": len(r.content),
            "sha256": sha(r.content), "schema_errors": errors, "content_type": r.headers.get("content-type"),
            "retry_after": r.headers.get("retry-after"), "doc": doc}


def strip(entry: dict) -> dict:
    return {k: v for k, v in entry.items() if k != "doc"}


def status() -> dict:
    return call("GET", "/v3/live/status", "/v3/live/status")


def wait_idle(limit_s: float = 900) -> dict:
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < limit_s:
        s = status()
        if s["doc"] and s["doc"]["state"] == "idle":
            return s
        time.sleep(3)
    raise TimeoutError("live cycle did not finish")


def run_record(run_id: str) -> dict:
    run = call("GET", f"/v3/simulations/{run_id}", "/v3/simulations/{run_id}")
    doc = run["doc"]
    frame = len(doc["frames"]) // 2
    depth = call("GET", f"/v3/simulations/{run_id}/depth", "/v3/simulations/{run_id}/depth", params={"frame_index": frame})
    flow = call("GET", f"/v3/simulations/{run_id}/flow", "/v3/simulations/{run_id}/flow", params={"frame_index": frame})
    result = json.loads((RUN_STORE / run_id / "result.json").read_text(encoding="utf-8"))
    created = datetime.fromisoformat(doc["created_at"].replace("Z", "+00:00"))
    done = datetime.fromisoformat(doc["completed_at"].replace("Z", "+00:00"))
    diag = result.get("diagnostics") or {}
    return {
        "run_id": run_id, "run_kind": doc.get("run_kind"), "mode": doc.get("mode"), "source_mode": doc.get("source_mode"),
        "engine_version": doc["provenance"]["engine_version"], "device": doc["provenance"].get("device"),
        "live": doc.get("live"), "frames": len(doc["frames"]), "grid": doc.get("grid"),
        "run_wall_seconds": (done - created).total_seconds(), "engine_runtime_s": diag.get("engine_runtime_s"),
        "engine_kernel_mode": diag.get("engine_kernel_mode"), "reservoir_coupling": diag.get("reservoir_coupling"),
        "forecast_check": {k: (diag.get("forecast_check") or {}).get(k) for k in ("fetched_at", "horizon_hours", "forcing_used", "excluded_models")},
        "summary": doc.get("summary"), "summary_sha256": sha(json.dumps(doc.get("summary"), sort_keys=True).encode()),
        "detail": strip(run), "depth": {**strip(depth), "frame_index": frame}, "flow": {**strip(flow), "frame_index": frame},
    }


def load() -> dict:
    return json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"task": "B53", "cr": "CR-021", "base": BASE}


def save(ev: dict) -> None:
    OUT.write_text(json.dumps(ev, indent=1, ensure_ascii=False), encoding="utf-8")


def phase_catchup(ev: dict) -> None:
    t0 = time.perf_counter()
    first = status()
    during = None
    for _ in range(60):  # the container starts its catch-up cycle at start-up
        s = status()
        if s["doc"]["state"] == "running":
            during = call("POST", "/v3/live/refresh", "/v3/live/refresh")
            break
        if s["doc"]["last_good_run_id"]:
            break
        time.sleep(1)
    done = wait_idle()
    st = done["doc"]
    latest = call("GET", "/v3/live/latest", "/v3/live/latest")
    ev["catchup"] = {"observed_at": now(), "seconds_to_publish": round(time.perf_counter() - t0, 1),
                     "first_status_state": first["doc"]["state"],
                     "refresh_during_cycle": strip(during) | {"body": during["doc"]} if during else None,
                     "status": strip(done) | {"body": st}, "latest": strip(latest) | {"body": latest["doc"]},
                     "run": run_record(st["last_good_run_id"])}


def phase_refresh(ev: dict) -> None:
    started = call("POST", "/v3/live/refresh", "/v3/live/refresh")
    second = call("POST", "/v3/live/refresh", "/v3/live/refresh")
    t0 = time.perf_counter()
    time.sleep(3)
    done = wait_idle()
    latest = call("GET", "/v3/live/latest", "/v3/live/latest")
    ev["refresh"] = {"observed_at": now(), "first": strip(started) | {"body": started["doc"]},
                     "second_within_600s": strip(second) | {"body": second["doc"]},
                     "cycle_seconds": round(time.perf_counter() - t0, 1), "status": strip(done) | {"body": done["doc"]},
                     "latest": strip(latest) | {"body": latest["doc"]}, "run": run_record(done["doc"]["last_good_run_id"])}


def phase_failure(ev: dict) -> None:
    before = status()["doc"]
    started = call("POST", "/v3/live/refresh", "/v3/live/refresh")
    time.sleep(3)
    done = wait_idle()
    latest = call("GET", "/v3/live/latest", "/v3/live/latest")
    ev["failure"] = {"observed_at": now(), "method": "ai-service recreated with HTTPS_PROXY=http://127.0.0.1:9 (closed port)",
                     "last_good_before": before["last_good_run_id"], "refresh": strip(started) | {"body": started["doc"]},
                     "status": strip(done) | {"body": done["doc"]}, "latest_after": strip(latest) | {"body": latest["doc"]},
                     "last_good_kept": done["doc"]["last_good_run_id"] == before["last_good_run_id"],
                     "last_error": done["doc"]["last_error"]}


def phase_final(ev: dict) -> None:
    checks = {}
    for path in ("/v3/live/status", "/v3/live/latest"):
        r = http.get(BASE + path)
        raw = r.content
        checks[path] = {"content_type": r.headers.get("content-type"), "em_dash_utf8_bytes": b"\xe2\x80\x94" in raw,
                        "mojibake_bytes": "â€".encode() in raw,
                        "decoded_disclaimer_exact": r.json().get("disclaimer") == DISCLAIMER,
                        "disclaimer_utf8_hex": DISCLAIMER.encode("utf-8").hex()}
    st = status()
    blob = b"\n".join(scanned)
    ev["final"] = {"observed_at": now(), "disclaimer": checks, "status": strip(st) | {"body": st["doc"]},
                   "retention": st["doc"]["retention"], "google_key_markers_in_api": [m.decode() for m in FORBIDDEN if m in blob],
                   "api_calls_scanned": len(scanned)}


def main() -> int:
    phase = sys.argv[1]
    ev = load()
    {"catchup": phase_catchup, "refresh": phase_refresh, "failure": phase_failure, "final": phase_final}[phase](ev)
    blob = b"\n".join(scanned)
    ev[phase]["google_key_markers_found"] = [m.decode() for m in FORBIDDEN if m in blob]
    ev[phase]["responses_scanned"] = len(scanned)
    save(ev)
    print(json.dumps(ev[phase], ensure_ascii=False, default=str)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
