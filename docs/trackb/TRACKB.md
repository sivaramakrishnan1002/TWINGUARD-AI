# Track B: reservoir/rainfall early warning

## Data classes

**REAL source observations:** historical daily reservoir storage and rainfall products as collected in the project; none are a live feed. **REPLAY:** historical source observations processed in event-time order. **SIMULATED:** no simulation results included in this delivery. Every message declares its source class. Alerts from the existing derived rule are exploratory replay candidates.

## Limits

No actual release-decision series is observed; CAG's reported 1–2 Dec 2015 Chembarambakkam values are annotations only. Daily storage ends 3 Dec 2020. Published capacity values changed over time and the available current figures are not verified historical denominators. OpenCity is monthly. The local IMERG, ERA5 and NASA POWER holdings are not a complete daily rainfall history for the storage period. The held-out B1–B4 metrics in `BACKTEST_REPORT.md` evaluate only a DERIVED future-storage threshold target under current published capacity assumptions; they are not flood or release-decision performance.

## Interface and operations

Read-only router is in `services/trackb/router.py`; it is separate and must be mounted by the host application. Streaming B7–B10 are blocked by missing local images. See `RUNBOOK.md` for exact variable setup, pull/start commands and stop command.

## Lineage and validation

Source inventory and limitations: `AUDIT_AND_BACKTEST.md`; derived evaluation: `BACKTEST_REPORT.md`, `BACKTEST_RESULTS.json`, and `SENSITIVITY.csv`; underlying project lineage: `../DATA_LINEAGE.md`, `../RAIN_SOURCES_COMPARISON.md`, and `../handbook/07_Reservoirs_and_Track_B.md`. Schema extension is migration `../../database/migrations/100_trackb_twin_link.sql` and is idempotent. API tests: `../../tests/trackb/test_router.py`. Database migration has not been applied to the local database. No end-to-end, metric, replay or latency claim is made.


## Current quantitative evidence

The source-coverage inventory, unit caveats and capacity provenance are in `AUDIT_AND_BACKTEST.md`. The held-out storage-target evaluation, model calibration/reliability metrics, per-reservoir and combined POD/FAR/CSI, year-block intervals and the complete N/fraction sensitivity grid are in `BACKTEST_REPORT.md`, `BACKTEST_RESULTS.json` and `SENSITIVITY.csv`. An accelerated 2015 replay artifact is `replay_2015_alerts.jsonl`; every row is explicitly marked `source: replay` and none was written to the database.
