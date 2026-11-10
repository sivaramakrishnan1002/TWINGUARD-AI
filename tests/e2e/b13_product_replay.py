"""B13 / G5 (CR-020) packaged product-pipeline replay: event 2015-12-01 -> /v3 -> outputs, through nginx /api/ai/v3/.

Run against the packaged B11 stack (docker compose -f docker-compose.b11.yml up --build):

    .venv\\Scripts\\python.exe tests\\e2e\\b13_product_replay.py --base http://127.0.0.1:8081/api/ai

Writes docs/trackb/B13_PRODUCT_REPLAY_EVIDENCE.json (hashes, statuses, timings). Not collected by pytest.
Every /v3 body is validated against docs/api/ai-service.yaml (C4 v3) with tests/ai_service/v3_support.validate.
"""
from __future__ import annotations

import argparse
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

EVENTS = ROOT / "data/features/live/a25_static_v1/shared/events.json"
MANIFEST = ROOT / "data/features/live/a25_static_v1/manifest.json"
A06_EVENTS = ROOT / "services/ai-service/app/v3/events.json"
OUT = ROOT / "docs/trackb/B13_PRODUCT_REPLAY_EVIDENCE.json"
UI_RUN = "evt-20261108T141229Z-fb36a1cd"           # B48 screenshots (Tabs 2 and 7)
PRE_FLOW_RUN = "evt-20261108T090744Z-b0d2d2bc"     # engine 2.0.0, no A27 flow sidecar
ROUTE = {"origin": {"lon": 80.2209, "lat": 12.9815}, "destination": {"lon": 80.2707, "lat": 13.0827}}
FORBIDDEN = ("AIza", "VITE_GOOGLE", "GOOGLE_MAPS")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Client:
    def __init__(self, base: str):
        self.base = base.rstrip("/")
        self.http = httpx.Client(timeout=300.0)
        self.log: list[dict] = []
        self.scanned: list[bytes] = []

    def call(self, method: str, path: str, spec_path: str | None, json_body=None, params=None, expect=None) -> dict:
        t0 = time.perf_counter()
        r = self.http.request(method, f"{self.base}{path}", json=json_body, params=params)
        seconds = round(time.perf_counter() - t0, 3)
        body = r.content
        self.scanned += [body, json.dumps(json_body or {}).encode(), json.dumps(params or {}).encode()]
        doc = r.json() if r.headers.get("content-type", "").startswith("application/json") else None
        errors = None
        if spec_path:
            try:
                errors = validate(doc, response_schema(spec_path, method, r.status_code))[:10]
            except KeyError:
                errors = [f"status {r.status_code} not in contract for {method} {spec_path}"]
        entry = {"method": method, "path": path, "params": params, "request": json_body, "status": r.status_code,
                 "seconds": seconds, "bytes": len(body), "sha256": sha(body), "schema_errors": errors,
                 "content_encoding": r.headers.get("content-encoding")}
        if expect is not None:
            entry["expected_status"] = expect
            entry["pass"] = r.status_code == expect and not errors
        self.log.append(entry)
        return {"entry": entry, "doc": doc, "body": body}


def content_hash(doc: dict, run_id: str) -> str:
    """Body hash with the run_id normalised, so outputs of two run_ids over the same engine run compare equal."""
    text = json.dumps(doc, sort_keys=True, separators=(",", ":")).replace(run_id, "RUN_ID")
    return sha(text.encode())


def outputs(c: Client, run_id: str, frame: int) -> dict:
    base = f"/v3/simulations/{run_id}"
    spec = "/v3/simulations/{run_id}"
    calls = {
        "depth": c.call("GET", f"{base}/depth", spec + "/depth", params={"frame_index": frame}),
        "flow": c.call("GET", f"{base}/flow", spec + "/flow", params={"frame_index": frame}),
        "wards": c.call("GET", f"{base}/wards", spec + "/wards"),
        "roads": c.call("GET", f"{base}/roads", spec + "/roads", params={"bbox": "80.20,12.96,80.24,13.00"}),
        "routes": c.call("POST", "/v3/routes", "/v3/routes", json_body={"run_id": run_id, **ROUTE}),
        "shelters": c.call("GET", f"{base}/shelters", spec + "/shelters"),
        "incidents": c.call("GET", f"{base}/incidents", spec + "/incidents"),
    }
    return {name: {**v["entry"], "content_sha256": content_hash(v["doc"], run_id) if v["doc"] else None} for name, v in calls.items()}


def wait(c: Client, run_id: str, limit_s: float = 1800) -> dict:
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < limit_s:
        doc = c.http.get(f"{c.base}/v3/simulations/{run_id}").json()
        if doc["state"] in ("completed", "failed"):
            return doc
        time.sleep(2)
    raise TimeoutError(run_id)


def simulate(c: Client, body: dict) -> dict:
    t0 = time.perf_counter()
    accepted = c.call("POST", "/v3/simulations", "/v3/simulations", json_body=body)
    run = wait(c, accepted["doc"]["run_id"])
    wall = round(time.perf_counter() - t0, 1)
    fetched = c.call("GET", f"/v3/simulations/{run['run_id']}", "/v3/simulations/{run_id}")
    return {"request": body, "accepted": accepted["doc"], "wall_seconds": wall, "run_id": run["run_id"], "state": run["state"],
            "error": run.get("error"), "frames": len(run.get("frames") or []), "grid": run.get("grid"), "summary": run.get("summary"),
            "provenance": run.get("provenance"), "limitations": run.get("limitations"), "detail_sha256": fetched["entry"]["sha256"],
            "detail_schema_errors": fetched["entry"]["schema_errors"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8081/api/ai")
    args = parser.parse_args()
    c = Client(args.base)
    evidence: dict = {"task": "B13", "cr": "CR-020", "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                      "base": args.base}

    # 1 Input
    events = json.loads(EVENTS.read_text(encoding="utf-8"))["events"]
    record = next(e for e in events if e["event_key"] == "2015-12-01")
    evidence["input"] = {
        "events_file": str(EVENTS.relative_to(ROOT)).replace("\\", "/"), "events_sha256": sha(EVENTS.read_bytes()),
        "a25_manifest_sha256": sha(MANIFEST.read_bytes()), "a06_fallback_events_sha256": sha(A06_EVENTS.read_bytes()),
        "record": {k: record[k] for k in ("event_key", "label", "start_utc", "end_utc", "rainfall_source", "source_mode",
                                           "interval_minutes", "total_mm")} | {"values": len(record["values_mm"]),
                                                                               "values_sha256": sha(json.dumps(record["values_mm"]).encode())},
    }
    status = c.call("GET", "/v3/status", "/v3/status")
    events_api = c.call("GET", "/v3/events", "/v3/events")
    evidence["status"] = {"body": status["doc"], "sha256": status["entry"]["sha256"], "schema_errors": status["entry"]["schema_errors"]}
    evidence["events_api"] = {"keys": [e["event_key"] for e in events_api["doc"]["events"]], "sha256": events_api["entry"]["sha256"]}

    # 2 Engine runs (exact acceptance body, and the 48 h request behind the B48 screenshots)
    exact = simulate(c, {"mode": "event", "event_key": "2015-12-01"})
    primary = simulate(c, {"mode": "event", "event_key": "2015-12-01", "duration_hours": 48})
    # A fresh, uncached engine compute inside the packaged CPU image (the two runs above may reuse engine output).
    fresh = simulate(c, {"mode": "event", "event_key": "2015-12-01", "duration_hours": 36})
    evidence["runs"] = {"acceptance_body": exact, "primary_48h": primary, "fresh_compute_36h": fresh}

    # 3 Outputs for the primary run, and the same outputs for the UI screenshot run
    frame = primary["frames"] // 2
    evidence["outputs_frame_index"] = frame
    evidence["outputs"] = outputs(c, primary["run_id"], frame)
    evidence["outputs_acceptance_body_run"] = outputs(c, exact["run_id"], exact["frames"] // 2)
    ui = c.http.get(f"{c.base}/v3/simulations/{UI_RUN}")
    if ui.status_code == 200:
        ui_outputs = outputs(c, UI_RUN, frame)
        evidence["ui_run"] = {"run_id": UI_RUN, "provenance": ui.json().get("provenance"),
                              "content_equal_to_primary": {k: ui_outputs[k]["content_sha256"] == evidence["outputs"][k]["content_sha256"]
                                                           for k in ui_outputs},
                              "outputs": ui_outputs}
    else:
        evidence["ui_run"] = {"run_id": UI_RUN, "status": ui.status_code}

    # 5 Determinism: identical request -> cached, same run_id, identical hashes
    again = c.call("POST", "/v3/simulations", "/v3/simulations", json_body=primary["request"])
    repeat_outputs = outputs(c, primary["run_id"], frame)
    evidence["determinism"] = {"repeat_state": again["doc"]["state"], "same_run_id": again["doc"]["run_id"] == primary["run_id"],
                               "identical_hashes": {k: repeat_outputs[k]["sha256"] == evidence["outputs"][k]["sha256"] for k in repeat_outputs}}

    # 6 Fail-closed
    spec = "/v3/simulations/{run_id}"
    fails = {
        "unknown_run_404": c.call("GET", "/v3/simulations/evt-20200101T000000Z-deadbeef", spec, expect=404)["entry"],
        "flow_pre_2_1_0_503": c.call("GET", f"/v3/simulations/{PRE_FLOW_RUN}/flow", spec + "/flow", params={"frame_index": 0}, expect=503)["entry"],
        "invalid_frame_422": c.call("GET", f"/v3/simulations/{primary['run_id']}/depth", spec + "/depth", params={"frame_index": 9999}, expect=422)["entry"],
        "invalid_flow_frame_422": c.call("GET", f"/v3/simulations/{primary['run_id']}/flow", spec + "/flow", params={"frame_index": 9999}, expect=422)["entry"],
    }
    # Queue over limit: one running + 4 queued, then the next distinct request is refused with 409.
    submitted = []
    for k in range(7):
        body = {"mode": "custom", "duration_hours": 6, "custom_rainfall": {"start_time_utc": "2026-11-08T00:00:00Z", "interval_minutes": 60,
                                                                         "values_mm": [round(1.0 + 0.1 * k, 2)] * 6}}
        r = c.call("POST", "/v3/simulations", "/v3/simulations", json_body=body)
        submitted.append(r["entry"])
        if r["entry"]["status"] == 409:
            break
        time.sleep(2.2)  # respect the 2 s run-start interval (429 otherwise)
    fails["queue_over_limit_409"] = {**submitted[-1], "expected_status": 409, "pass": submitted[-1]["status"] == 409 and not submitted[-1]["schema_errors"],
                                     "accepted_before": [e["status"] for e in submitted[:-1]]}
    evidence["fail_closed"] = fails

    # Optional secondary check: CR-012 date-only replay route (GET /api/ai/ proxy)
    replay = c.http.get(f"{c.base}/replay-alerts/replay:POONDI:date:2015-12-01")
    evidence["replay_alert_poondi"] = {"status": replay.status_code, "sha256": sha(replay.content), "bytes": len(replay.content),
                                       "event_id": (replay.json() or {}).get("selector", {}).get("event_id") if replay.status_code == 200 else None}

    # 7 Boundaries: no Google key anywhere in requests or responses
    blob = b"\n".join(c.scanned)
    evidence["boundaries"] = {"google_key_markers_found": [m for m in FORBIDDEN if m.encode() in blob], "calls_scanned": len(c.log)}
    evidence["calls"] = c.log
    evidence["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUT.write_text(json.dumps(evidence, indent=1), encoding="utf-8")

    checks = {
        "outputs_200_and_valid": all(v["status"] == 200 and not v["schema_errors"] for v in evidence["outputs"].values()),
        "cached_same_run_and_hashes": evidence["determinism"]["repeat_state"] == "cached" and evidence["determinism"]["same_run_id"]
        and all(evidence["determinism"]["identical_hashes"].values()),
        "fail_closed": all(v.get("pass") for v in fails.values()),
        "no_google_key": not evidence["boundaries"]["google_key_markers_found"],
        "primary_completed": primary["state"] == "completed",
    }
    print(json.dumps({"checks": checks, "primary_run": primary["run_id"], "acceptance_body_run": exact["run_id"],
                      "wall_seconds": primary["wall_seconds"], "device": (primary["provenance"] or {}).get("device"),
                      "ui_run_content_equal": evidence["ui_run"].get("content_equal_to_primary")}, indent=1))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
