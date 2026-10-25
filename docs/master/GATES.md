# Gate protocol

| Gate | Target day | Required evidence |
|---|---:|---|
| G0 | 2 | C1–C8 frozen, versions, compatible stubs and ownership confirmed. |
| G1 | 6–10 | Label acceptance and depth contract. |
| G2 | 10–12 | Risk map, fair baselines and out-of-event evaluation. |
| G3 | 12–15 | Replay connected to twin and integration evidence. |
| G4 | 22–25 | Forecast through shelter API. |
| G5 | 28–32 | End-to-end replay scenario. |
| G6 | 34–38 | Validation, documentation, release tag v1.0. |

At each gate both lanes stop. Integrator checks prerequisites and ownership, runs `python tools/master/gate_check.py Gn`, merges requirements, reconciles migration numbering, runs the complete test suite, raw audit and end-to-end checks, and records `GATE_Gn_REPORT.md`. Create database dumps under ignored `backups/` only after confirming the configured target and available disk. Never delete Docker volumes. Replace stubs only with real evidence-backed outputs. Any failure keeps the gate closed and creates owning-lane repair tasks.

