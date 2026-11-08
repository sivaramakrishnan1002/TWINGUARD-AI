# CR-020 — G5 revised to the product pipeline (replay -> engine -> /v3 -> packaged UI)

**Decision:** approved by the project owner on 2026-11-08 ("B", relayed by the coordinator session), choosing option B in [G5_REASSESSMENT_2026-11-08.md](G5_REASSESSMENT_2026-11-08.md). Recorded by the Integrator. Owner decision: OD-2026-11-08b in `FINAL_YEAR_OWNER_DECISIONS.md`.

## Change

- **New G5 scope:** an end-to-end replay of one source-identified archived input. The saved 2015-12-01 event rainfall (REPLAY), optionally plus a cached Open-Meteo snapshot (MODEL_FORECAST), goes through a flood-engine run, the C4 v3 `/v3` API, and the packaged UI. Source input stays distinct from simulated output.
- **Superseded:** CR-012's G5 scope (the POONDI date-only reservoir observation as the gate path). The CR-012 route, `GET /replay-alerts/{event_id}`, stays mounted and is kept as an **optional secondary check** with no UI requirement. CR-012's C3 date-only rules still bind that route.
- **Kept from the old G5:** deterministic, hash-recorded selection; separation of source and derived; fail-closed behaviour; read-only data boundaries; no observed, live-warning or safety claim (OD-2026-11-07 badge policy).

## Task

B13 keeps its ID, with acceptance revised to the 8 criteria in `STATE.json` (from the reassessment).

**Owners:**
- **Lane B:** execution and packaging evidence.
- **UI session (B48):** run view and labels in Tabs 2 and 7, with flow animation.
- **Integrator:** review, the item-8 contract tidy-up, and `gate_check G5`.

**Start:** B13 starts once B48 confirms the run view and labels are in place. Until then it is `blocked_prerequisite` with that prerequisite recorded. The Integrator moves it to `ready` on B48's confirmation.

## Unchanged

C1-C8 stay frozen. C4 v3 is unchanged by this CR. G6 still requires I04, the owner's release decision.
