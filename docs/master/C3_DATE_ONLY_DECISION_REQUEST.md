# C3 date-only contract decision request

**Status: approved by the project owner on 2026-10-28.** The approval authorizes the bounded date-only contract policy described below and recorded in [C3_DATE_ONLY_DECISION.json](C3_DATE_ONLY_DECISION.json). It does not establish historical measurement-time meaning or timezone as discovered facts, authorize applying migration 101, authorize shared-database writes, claim live operation, freeze C3, or make G0 ready.

## Evidence and boundary

B19 implementation and regression tests support preservation of date-only historical reservoir records. The source archive contains dates but no authoritative source-owner record specifying what those dates mean or their timezone. B19's focused tests passed locally on 2026-10-28: `tests/trackb/test_date_only_timestamps.py` and `tests/trackb/test_router.py` (7 passed, one existing Starlette/httpx deprecation warning). I09 remains done_with_caveats; its review records C3 compatibility and timezone status as FAIL. `database/migrations/101_trackb_date_only_reservoir_observations.sql` is a proposal and has not been applied; B19 reports no database was accessed or changed.

The earlier project-owner decision for proxy-free A11 scope (CR-007) is unrelated and is not approval for this C3 decision.

## Exact decision requested

Project owner: please explicitly approve or reject the following bounded C3 contract semantics for historical date-only reservoir records. Approval would accept an honest unknown-time representation as the contract for these source rows; it would **not** establish the historical measurement-time meaning or timezone as discovered facts.

1. Preserve the source calendar value exactly as `source_date` (`YYYY-MM-DD`).
2. Represent the historical observation instant and timezone as unknown/null unless authoritative source-owner evidence is later obtained.
3. Never synthesize midnight, assume `Asia/Kolkata` or another timezone, or claim sub-day ordering or exact validity intervals for date-only records.
4. Keep `received_at` as the actual ingestion timestamp, separate from `source_date`.
5. For sources that provide genuine timestamps, retain the supplied offset and instant.
6. Any schema migration needed to store date-only records remains unapplied until separately authorized for an isolated database.

**Approval recorded:** The project owner replied “approve it” to the request above on 2026-10-28. The reply is bound to the six enumerated semantics and the stated limitations in this request. The Integrator decision record preserves the exact approval context.

## Effect if approved

After approval is recorded, the Integrator may revise the C3 draft/checklist/report so the C3 temporal criterion tests faithful date-only preservation and honest unknown-time handling, while explicitly retaining the unresolved historical facts. Checker logic and negative tests may be updated only if needed to enforce the approved criterion. The approval alone does not prove persistence compatibility: migration 101 remains a proposal, and C3 compatibility must remain failed unless required compatibility evidence is independently satisfied. C3 remains v0/unfrozen and G0 remains `not_ready` until every G0 criterion, task stop condition, and required gate check passes.

## Current disposition

The date-only policy is approved. The Integrator may update C3 draft/checklist semantics under a registered task. Historical date meaning and timezone remain unknown, persistence compatibility remains unproven while migration 101 is unapplied, and G0 must remain `not_ready` unless every independent criterion and stop condition passes.
