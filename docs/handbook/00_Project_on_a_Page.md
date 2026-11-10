# TwinGuard AI — project on a page

*Refreshed 10 Nov 2026 (B55). TwinGuard is a bachelor's final-year project (OD-2026-11-07), not an operational or research-grade service.* [repo: `docs/master/FINAL_YEAR_OWNER_DECISIONS.md`]

## What it is

A flood digital twin for Chennai:
- **Simulation:** it simulates flooding from rainfall and reservoirs.
- **3D city:** it shows the water on a 3D city (CesiumJS with Google Photorealistic 3D Tiles).
- **Decision support:** it turns depth into decision support: affected buildings and wards, three-state road access, routes, shelter reachability, generated incidents and a resource plan.
- **Live mode:** a 72 h forecast is refreshed automatically every 3 h. Archived events can be replayed, and what-if scenarios compared.

## Contribution (owner's wording, OD-2026-11-07 §6)

> "an integrated rainfall + reservoir → flood simulation → 3D digital twin → impact, three-state routing and shelter decision pipeline with what-if scenarios for Chennai" is the project's contribution.

The individual methods (local-inertial flood modelling, graph routing, shelter allocation) are established. The contribution is their integration into one labelled, end-to-end pipeline for Chennai.

## Status (10 Nov 2026)

| Area | State |
|---|---|
| Engine | A25 high-resolution engine: 120/90 m citywide, 30 m focus areas. It has a CUDA backend (A26), flow export (A27) and the A28 reservoir coupling. |
| API | C4 v3 `/v3`: 31 paths / 33 operations, including live endpoints (B47, B49, B51) |
| UI | 7-tab live-first UI with badges and the live bar (B48, B52) |
| Gates | G1–G5 passed with caveats. The Round 2 live stage passed with caveats (I27). G6 (final) is pending owner checklist items. |
| Packaging | B11 Docker stack verified for the replay (B13) and live cycle (B53) |

## Labels you will see

- **Results:** every result is `SIMULATED`.
- **Inputs:** these keep their own class — `REPLAY` (archived event), `MODEL_FORECAST` (Open-Meteo), `PUBLISHED_SNAPSHOT` (CFM-DSS) or `SCENARIO_INPUT` (owner-set resources, what-if values, A28 assumed inflow).
- **Incidents:** generated from the results and labelled as such.
- **Live runs:** every live run carries "Model forecast — not an official warning".

## Where to start

- [Architecture](03_Architecture_and_Tech_Stack.md) → [User Guide](18_User_Guide.md) → [Runbook](19_Runbook.md) → [Risks and Limitations](13_Risks_and_Limitations.md) → [Decision Log](04_Decision_Log.md) → [References and Attribution](16_References_and_Attribution.md).
- Chapters 05–11 record the earlier research phases (data, labels, Track B, Phases 2–3) and are kept as history.
