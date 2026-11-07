# Gate protocol

| Gate | Target day | Required evidence |
|---|---:|---|
| G0 | 2 | C1–C8 frozen, versions, compatible stubs and ownership confirmed. |
| G1 | 6–10 | Label acceptance and depth contract. |
| G2 | 10–12 | Risk map, fair baselines and out-of-event evaluation. |
| G3 | 12–15 | Replay connected to twin and integration evidence. |
| G4 | 22–25 | Forecast through shelter API. |
| G5 | 28–32 | End-to-end replay of one source-backed date-only observation through the mounted backend route into the packaged UI, with source input distinguished from derived output. |
| G6 | 34–38 | Validation, documentation, release tag v1.0. |

At each gate both lanes stop. Integrator checks prerequisites and ownership, runs `python tools/master/gate_check.py Gn`, merges requirements, reconciles migration numbering, runs the complete test suite, raw audit and end-to-end checks, and records `GATE_Gn_REPORT.md`. Create database dumps under ignored `backups/` only after confirming the configured target and available disk. Never delete Docker volumes. Replace stubs only with real evidence-backed outputs. Any failure keeps the gate closed and creates owning-lane repair tasks.

For G0, record the C1–C8 criterion-by-criterion status and evidence paths in `docs/master/G0_CHECKLIST.json` and the review in `docs/master/GATE_G0_REPORT.md`. `gate_check.py G0` fails closed unless every required criterion is PASS with existing evidence, checklist metadata matches the contract registry, the report decision marker agrees, all lane tasks have stopped, and `STATE.json` records G0 as `ready`. Checklist completion alone does not freeze contracts; the integrator records the freeze and updates G0 only after all other gate evidence passes.

For G5, B13 must replay one uniquely selected, source-backed archived reservoir observation with date-only C3 semantics through approved processing, a mounted read-only backend route, and the packaged UI. Record the source row identity and hashes, deterministic selector, replay run identity, normalized input/output hashes, actual receipt/processing time separately, and any context inputs used. The UI/API must distinguish the archived REPLAY input from optional derived system output; generated alerts or flood results are derived replay output, never historically observed events. Preserve null/unknown time fields and source provenance. Verify the packaged end-to-end path, fail-closed behavior, read-only boundaries, and research-only limitations. B9's pipeline replay and B18/I08's A20 visualization do not satisfy G5. Keep G5 `not_ready` until every B13 criterion passes; if replay produces no derived result, show no derived result and do not invent one. Current approved scope and evidence are recorded in `docs/master/CR-012_G5_DATE_ONLY_OBSERVATION_REPLAY.md`.

