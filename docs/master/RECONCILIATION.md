# Initial reconciliation — 2026-10-25

## Sources inspected

Git HEAD `54ebad0`; dirty worktree includes concurrent Lane A and Lane B changes. Read both batch specifications and progress boards, project status, handbook, phase 8/9 reports, migrations, tools/requirements, and recursive feature/processed file listings. PostgreSQL was queried through `.env` using a read-only transaction; credentials were not printed. Initial reconciliation suite: 44 passed; after master-control tests, 46 passed. Latest full suite (with concurrent Lane A acceptance test) reports 47 passed, 1 failed, and one Starlette/httpx deprecation warning. The failure is `tests/phase8/test_rule_v2_acceptance.py::test_confusion_metrics_and_iou`: its expected IoU 0.5 conflicts with the standard formula TP/(TP+FP+FN)=1/3 for TP=FP=FN=1. This lane-owned test was not changed. Raw audit completed: 157 files, 30,544,672,450 bytes; 157 hash matches, zero missing comparable hashes, zero mismatches.

## Verified database snapshot

Database `twinguard`, PostgreSQL 18.6. 26 non-system base tables; `twinguard.schema_migrations` has 14 records (001–014); `twinguard.grid_cells` 1,319,380; `labels.derived_flood_polygons` 45,096; `twinguard.flood_labels` 21,927; manifest 130. `labels.v_usable_flood_labels` exists. Migration 100 is on disk but unapplied; `twin.alerts` and `twin.reservoir_state` exist and each has zero rows. The separate `twin` clone/24-table historical parity is documented but not re-run here.

## Claims versus evidence

| Item | Evidence/status | Conflict or caveat |
|---|---|---|
| F1–F6 | Phase docs, migrations and data files exist; DB counts support F4/F5/F6. | Historical phase claims have not each been replayed. |
| F7 | Migration 010, API specs, AI service and design docs exist. | API contracts/design do not prove deployed endpoints; services contain 501 stubs. |
| F8 | Clone acceptance reported in Stage 5/6 report. | Historical test was before migrations 004–008 extension; no current parity rerun. |
| F9 | Handbook v1 exists. | Refresh is explicitly pending in project status. |
| F10 | SETUP_TOOLS documents setup. | Maven missing per user claim/project status; not independently probed this pass. |
| F11 | Phase 8 docs, metrics and labels exist. | 45,096 DB derived polygons; weak pilot metrics. Classification as tier D is a board/spec claim; inspect registry before reuse. |
| F12 | Phase 9 report and metric artifacts exist. | PR-AUC 0.3415 and prevalence 5.11% are single-event spatial CV, not generalization. |
| A01 | Batch board T1/T2 done; T3 doing. T3 rasters and run-specific JSON exist. | T4/T5 not completed per board; no approved labels/depth should be inferred. Concurrent dirty files are preserved. |
| B01 | Track B board marks B1–B6 and B10 done. | B3 and B5 claims mean authored artifacts, not runtime validation. Board says calibrated comparator unavailable. |
| B02/B13 | Board says B7–B9 blocked and B13 blocked. | No streaming images/runtime E2E evidence observed. |
| B03 | Migration 100, router and tests present; board marks B11/B12 done. | Migration 100 unapplied and tables empty, so runtime twin linkage is not complete. |
| Raw audit | Process started as command session 12946. | Final count/hash status pending. |
| pytest | Process started as session 69450. | Final result pending. |

The Lane A board advanced during this work: T3 is now done at commit a092c31; T4 is doing after preregistration recorded at 2026-10-25 09:42:35 Asia/Kolkata. The combined catalogue task A01 remains running until T5 completes. This is a live lane-owned change, not an integrator edit.

## Initial running work

Batch 1 A01 is running through T5; T3 is done and T4 is doing. Track B is treated as running documentation/integration activity per its board; the B7–B9 runtime subtask is blocked. Re-run `verify_state.py` and reread both boards at each session start.



## Track B streaming prerequisite reconciliation — 2026-10-25

Read PROTOCOL.md, GATES.md, STATE.json, NEXT.md, the Track B progress board, and Track B final report. Local Docker inventory was queried by exact image reference; all four required tags are present: `redis:8.10.2-alpine`, `apache/kafka:4.3.2`, `prom/prometheus:v3.13.2`, and `grafana/grafana:13.2.2-ubuntu`. No image pull, Compose validation, or service start was performed.

M1 is recorded complete with local image-inventory evidence. B01 is `done_with_caveats`; B02 depends only on B01 and M1, has no recorded prerequisites, and has no exact-path running-task output conflict. B02 is therefore `ready`, not running or complete. The task catalogue does not list G0 as a B02 dependency: G3 requires B02 and B03. G0 remains `not_ready`; its contracts-freeze checklist was not bypassed. Migration 100 remains unapplied and DB integration remains gated. Track B paths were read-only in this reconciliation.


### Requested control checks

- `.\.venv\Scripts\python.exe tools\master\verify_state.py`: exit 0. It reported 55 Git status entries, read both lane boards, and completed its migration/database summary; its output reiterates that master-state task claims do not replace lane-board evidence. No state-integrity failure was reported.
- `.\.venv\Scripts\python.exe tools\master\next_task.py --lane B`: exit 0; output `B02	Streaming/monitoring B6-B10`.
- `.\.venv\Scripts\python.exe tools\master\gate_check.py G0`: exit 0; output `G0 NOT READY: criterion evidence needs explicit gate checklist review`. G0 remains not_ready.
- `NEXT.md` was regenerated from the updated task state. No Compose validation, service start, migration application, image pull, or database write was performed.


## B12 Docs ownership reconciliation — 2026-10-25

The master B12 entry was `running`, titled “Docs”, with outputs `docs/trackb/` and `docs/handbook/`, but no acceptance criteria, no task-specific session claim time, no finish time, no commit, and no notes. Its session field only says “Track B”. The Track B progress board marks batch task B13 Docs done, and TRACKB_REPORT.md also marks B13 done; TRACKB.md, DIAGRAM.md, REALTIME_DESIGN.md and the report are present. That is evidence the Track B-owned documentation package was authored, but the operational board/report/runbook still require B02 phase evidence updates.

The handbook chapter `docs/handbook/07_Reservoirs_and_Track_B.md`, compiled `docs/handbook/TwinGuard_Project_Handbook.md`, and `docs/handbook/12_Team_Guide.md` still describe only the older illustrative screen/legacy command. B12 remains running with ownership narrowed to exactly those three handbook files. `docs/trackb/` is released for B02 to update its board, report, and runbook. The master task ID B12 (“Docs”) is distinct from Track B batch B12 (“API”); the latter is marked done in the Track B board/report. No Track B files were edited and no commit was made in this reconciliation.

## B08 stale-claim reconciliation — 2026-10-29

The 2026-10-28 B08 claim (`B08 bounded real endpoint projections`) was not followed by implementation or valid in-progress work. The master task history shows the claim and no B08 finish/implementation record; the worktree has no changes under the registered outputs `services/ai-service/` or `tests/ai_service/`, and no B08 heavy lock exists. All listed dependencies remain `done_with_caveats`; G0 remains `ready`; C4, C7 and C8 remain frozen at v0. No other task is running and the B08 output-conflict check is clear.

B08 is returned to `ready` and unclaimed by the official master-state process. Its registered scope, dependencies and acceptance criteria are unchanged. This does not mark B08 complete or waive its G0/frozen-contract prerequisite; business endpoints remain unavailable until B08 implementation satisfies its existing criteria.

## B08 selector ambiguity and CR-008 — 2026-10-29

Independent inspection of B08's report, AI endpoint tests, Pydantic request/result models, OpenAPI projections, backend DTO/conformance tests, frozen C4/C7/C8 drafts, and the registered owner artifacts confirms that the blocker is a request-selector mismatch:

- A07 V4 has 75 unique results. All use run 7004; there are 15 valid times with five scenario keys at each time. `(run_id, valid_at_utc, scenario_key)` is unique, but frozen C4 `RunTimeRequest` has no `scenario_key`.
- A09 revision 3 has 216 unique `result_id` values and null `run_id` on every row. Four methods share each group matching the current route request's non-run fields. Frozen `RouteRequest` requires an integer `run_id` and has no result ID, scenario, or method selector.
- C7/C8 result schemas already carry `scenario_key`/`result_id`; the evidence supports result-body conformance, not the missing C4 request/lookup semantics. B08 correctly keeps ambiguous and unsupported results unavailable.

No deterministic selector is available under the current request schemas. CR-008 proposes a C4 change-control path: require an A07 `scenario_key` for impact selection and add a distinct saved A09 result lookup by its existing `result_id`, while leaving route computation unavailable absent an evidenced run mapping. Forecast, uncertainty, and C4 `/scenario` remain unavailable pending their own artifact mapping. Lane A confirmed selector evidence in `docs/CR008_LANEA_SELECTOR_EVIDENCE.md`, commit `e3161b5`; the A09 ID is scoped to revision 3 and no run mapping was found. Explicit project-owner approval remains pending. No frozen contract, OpenAPI projection, Lane A artifact, B08 implementation, or G0 status was changed.

I14 is registered as `blocked_manual` pending the project-owner decision; the Lane A evidence prerequisite is satisfied. B08 remains `blocked_prerequisite`; its report/tests and current 501 behavior are preserved. B11, B13, B17, and I08 remain gated by their existing dependencies. See `docs/master/CR-008_B08_ARTIFACT_SELECTORS.md` and `docs/master/CHANGE_REQUESTS.md`.
