# Initial reconciliation — 2026-10-25

## Sources inspected

Git HEAD `54ebad0`; dirty worktree includes concurrent Lane A and Lane B changes. Read both batch specifications and progress boards, project status, handbook, phase 8/9 reports, migrations, tools/requirements, and recursive feature/processed file listings. PostgreSQL was queried through `.env` using a read-only transaction; credentials were not printed. Full pytest completed: 44 passed, one Starlette/httpx deprecation warning. Raw audit completed: 157 files, 30,544,672,450 bytes; 157 hash matches, zero missing comparable hashes, zero mismatches.

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

The Lane A board has since advanced: T3 remains doing and T4 is now registered as todo with the acceptance preregistration recorded at 2026-10-25 09:42:35 Asia/Kolkata. This is a live lane-owned change, not an integrator edit.

## Initial running work

Batch 1 is treated as running at T3 per its board. Track B is treated as running documentation/integration activity per its board; the B7–B9 runtime subtask is blocked. Re-run `verify_state.py` and reread both boards at each session start.

