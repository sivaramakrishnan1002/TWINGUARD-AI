"""Fail-closed gate prerequisite and G0 checklist validation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from state import ROOT, read_state


COMMON_CRITERIA = (
    "version",
    "owner",
    "consumers",
    "data_format",
    "units",
    "timestamps",
    "provenance",
    "null_nodata",
    "compatibility",
)
SPECIAL_CRITERIA = {
    "C1": ("scientific_semantics",),
    "C2": ("accepted_label_serialization",),
    "C3": ("timezone_status",),
    "C4": ("api_projection_agreement",),
    "C5": ("catalogue_and_tile_availability",),
    "C6": ("twin_serialization", "b9_runtime"),
    "C7": ("implementable_result_schema",),
    "C8": ("implementable_result_schema",),
}
C3_DATE_ONLY_DECISION = "docs/master/C3_DATE_ONLY_DECISION.json"
C3_DATE_ONLY_TESTS = (
    "tests/trackb/test_date_only_timestamps.py",
    "tests/trackb/test_router.py",
)
C3_APPROVED_SEMANTICS = (
    "Preserve historical source calendar values exactly as source_date (YYYY-MM-DD).",
    "Historical observation instant and timezone are unknown/null unless authoritative source-owner evidence is later obtained.",
    "Never synthesize midnight, assume Asia/Kolkata or another timezone, or claim sub-day ordering or exact validity intervals for date-only records.",
    "Keep received_at as the actual ingestion timestamp, separate from source_date.",
    "For sources that provide genuine timestamps, retain the supplied offset and instant.",
    "Any schema migration needed to store date-only records remains unapplied until separately authorized for an isolated database."
)


def c3_approved_date_only_blockers(item: dict, root: Path = ROOT) -> list[str]:
    """A C3 PASS means the unknown-time policy was explicitly approved and tested, not discovered."""
    criterion = item.get("criteria", {}).get("timezone_status", {})
    if criterion.get("status") != "PASS":
        return []
    blockers: list[str] = []
    evidence = criterion.get("evidence")
    if not isinstance(evidence, list) or C3_DATE_ONLY_DECISION not in evidence:
        blockers.append("C3.timezone_status: approved date-only decision evidence is required")
    for path in C3_DATE_ONLY_TESTS:
        if not isinstance(evidence, list) or path not in evidence or not (root / path).is_file():
            blockers.append(f"C3.timezone_status: required date-only test evidence missing: {path}")
    decision_path = root / C3_DATE_ONLY_DECISION
    if not decision_path.is_file():
        blockers.append("C3.timezone_status: project-owner decision record is missing")
        return blockers
    try:
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        blockers.append("C3.timezone_status: project-owner decision record is unreadable")
        return blockers
    if decision.get("decision_status") != "approved":
        blockers.append("C3.timezone_status: project-owner decision is not approved")
    if tuple(decision.get("semantics", ())) != C3_APPROVED_SEMANTICS:
        blockers.append("C3.timezone_status: approved semantics do not match the six bounded terms")
    if decision.get("historical_measurement_time_meaning") != "unknown" or decision.get("historical_timezone") != "unknown":
        blockers.append("C3.timezone_status: historical source-time facts must remain unknown")
    for flag in ("migration_101_authorized", "shared_database_write_authorized", "live_operation_claim_authorized"):
        if decision.get(flag) is not False:
            blockers.append(f"C3.timezone_status: {flag} must remain false")
    return blockers


def g0_checklist_blockers(state: dict, checklist: dict, root: Path = ROOT) -> list[str]:
    """Return every missing or failed G0 criterion; no implicit pass defaults."""
    blockers: list[str] = []
    running = sorted(
        task.get("id", "unknown")
        for task in state.get("tasks", [])
        if task.get("status") == "running"
    )
    if running:
        blockers.append(f"lane work still running: {', '.join(running)}")
    if checklist.get("gate") != "G0":
        blockers.append("checklist gate must be G0")
    if checklist.get("decision") != "PASS":
        blockers.append("checklist decision is not PASS")
    report_path = checklist.get("report_path")
    if report_path != "docs/master/GATE_G0_REPORT.md":
        blockers.append("checklist must reference docs/master/GATE_G0_REPORT.md")
    elif not (root / report_path).is_file():
        blockers.append("G0 gate report is missing")
    else:
        report = (root / report_path).read_text(encoding="utf-8")
        marker = f"**Current gate decision: {checklist.get('decision', 'MISSING')}**"
        if marker not in report:
            blockers.append("gate report current-decision marker does not match checklist")

    registry = {item.get("id"): item for item in state.get("contracts", [])}
    recorded = checklist.get("contracts")
    if not isinstance(recorded, list):
        return blockers + ["checklist contracts must be a list"]
    by_id = {item.get("id"): item for item in recorded if isinstance(item, dict)}
    expected_ids = set(SPECIAL_CRITERIA)
    if set(by_id) != expected_ids:
        blockers.append("checklist must contain exactly C1-C8")

    for cid in sorted(expected_ids):
        item = by_id.get(cid)
        reg = registry.get(cid)
        if item is None:
            blockers.append(f"{cid}: checklist entry missing")
            continue
        if reg is None:
            blockers.append(f"{cid}: STATE.json registry entry missing")
            continue
        for field in ("version", "owner", "consumers", "path"):
            if item.get(field) != reg.get(field):
                blockers.append(f"{cid}.{field}: checklist does not match STATE.json registry")
        draft = item.get("path")
        if not isinstance(draft, str) or not (root / draft).is_file():
            blockers.append(f"{cid}.path: contract draft missing")

        criteria = item.get("criteria")
        required = set(COMMON_CRITERIA) | set(SPECIAL_CRITERIA[cid])
        if not isinstance(criteria, dict):
            blockers.append(f"{cid}: criteria object missing")
            continue
        if set(criteria) != required:
            missing = sorted(required - set(criteria))
            extra = sorted(set(criteria) - required)
            if missing:
                blockers.append(f"{cid}: missing criteria {','.join(missing)}")
            if extra:
                blockers.append(f"{cid}: unexpected criteria {','.join(extra)}")
        for name in sorted(required & set(criteria)):
            criterion = criteria[name]
            if not isinstance(criterion, dict):
                blockers.append(f"{cid}.{name}: criterion record missing")
                continue
            evidence = criterion.get("evidence")
            if criterion.get("status") != "PASS":
                blockers.append(f"{cid}.{name}={criterion.get('status', 'MISSING')}")
            if not isinstance(evidence, list) or not evidence:
                blockers.append(f"{cid}.{name}: evidence path(s) required")
                continue
            for evidence_path in evidence:
                if not isinstance(evidence_path, str) or not (root / evidence_path).exists():
                    blockers.append(f"{cid}.{name}: evidence missing: {evidence_path}")
        if cid == "C3":
            blockers.extend(c3_approved_date_only_blockers(item, root))
    return blockers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("gate")
    args = parser.parse_args()
    state = read_state()
    gate = next((item for item in state["gates"] if item["id"] == args.gate), None)
    if gate is None:
        parser.error(f"unknown gate {args.gate}")

    if args.gate == "G0":
        checklist_path = ROOT / "docs/master/G0_CHECKLIST.json"
        if not checklist_path.is_file():
            print("G0 NOT READY: checklist missing: docs/master/G0_CHECKLIST.json")
            return 1
        try:
            checklist = json.loads(checklist_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"G0 NOT READY: checklist unreadable ({type(exc).__name__})")
            return 1
        blockers = g0_checklist_blockers(state, checklist)
        if gate.get("status") != "ready":
            blockers.append(f"STATE.json gate status is {gate.get('status', 'MISSING')}")
        if blockers:
            print("G0 NOT READY: " + "; ".join(blockers))
            return 1
        print("G0 READY: all C1-C8 checklist criteria and evidence paths pass")
        return 0

    tasks = {task["id"]: task for task in state["tasks"]}
    missing = [
        required
        for required in gate["requires"]
        if required in tasks and tasks[required]["status"] not in ("done", "done_with_caveats")
    ]
    if missing:
        print(f"{args.gate} CLOSED: tasks incomplete: {', '.join(missing)}")
        return 1
    unknown = [required for required in gate["requires"] if required not in tasks]
    if unknown:
        print(f"{args.gate} NOT READY: criterion evidence needs explicit gate checklist review")
        return 1
    print(f"{args.gate} READY for integrator gate checklist; all listed task prerequisites are complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
