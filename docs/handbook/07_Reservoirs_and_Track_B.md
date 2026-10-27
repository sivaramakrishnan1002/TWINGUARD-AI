# Reservoir data and Track B

## Purpose and operating boundary

Track B is the project's reservoir-and-rainfall early-warning research stream. It evaluates historical storage and rainfall observations, produces explicitly labelled REPLAY events, and tests a bounded rule engine and streaming path. It is not a live reservoir feed, flood warning service, release model, or operational decision system. Replay and simulated results must remain visibly distinct from observed source data and from live operation. [repo: `docs/trackb/TRACKB.md`, `docs/trackb/PROGRESS_BOARD.md`]

## Available evidence and limits

- The Kaggle Chennai Water Management archive contains daily storage and a rainfall table for Poondi, Cholavaram, Red Hills/Puzhal and Chembarambakkam. The daily series ends **3 December 2020**. The archive describes storage in mcft; its rainfall unit is not documented and remains **INFERRED** in Track B processing. The date-only source does not establish the historical observation timezone. [repo: `docs/trackb/AUDIT_AND_BACKTEST.md`, `docs/trackb/MESSAGES.md`]
- OpenCity provides monthly lake storage, which cannot establish event-day release timing. Published capacities changed over time; current published capacity figures are not validated historical denominators. [repo: `docs/trackb/AUDIT_AND_BACKTEST.md`]
- No complete historical release/outflow or gate-operation series was collected for these reservoirs. A storage change is not a release measurement. The CAG executive-summary figures for 1–2 December 2015 are limited annotations, not a continuous series or a release model. [repo: `docs/trackb/AUDIT_AND_BACKTEST.md`, `docs/MANUAL_TODO.md`]
- Track B's B1–B4 evaluation targets whether daily storage reaches a future threshold under stated capacity assumptions. Its backtest/model metrics evaluate that **DERIVED storage target**, not flood occurrence, release decisions, or operational warning skill. Capacity, rainfall-unit and coverage caveats remain attached to the results. [repo: `docs/trackb/BACKTEST_REPORT.md`, `docs/trackb/AUDIT_AND_BACKTEST.md`]

## Streaming and verified REPLAY behavior

Track B defines versioned UTF-8 JSON Lines messages for rainfall, reservoir state, twin references and alerts. Events carry `source` (`replay`, `live` or `simulated`), event and receipt timestamps, provenance, unit-bearing fields and explicit nulls for unavailable measurements. The source timezone remains **unconfirmed**: replay assigns Asia/Kolkata midnight only as a provisional encoding default and retains `timezone_status: "DEFAULT, to confirm"`. Consumers preserve the encoded offset and source-calendar date; this does not confirm the source's historical timezone. [repo: `docs/trackb/MESSAGES.md`, `docs/trackb/REALTIME_DESIGN.md`]

A fresh accelerated 2015 REPLAY was verified on 27 October 2026: two producer passes acknowledged 120 events each; Kafka contained 60 unique rainfall IDs, 60 unique reservoir IDs, and 50 alert IDs; the consumer processed 170 unique messages. The isolated test database `twinguard_trackb_test` recorded 60 reservoir states, 60 recompute markers and 50 alert events/links/twin alerts; the duplicate pass did not increase persisted counts. Redis state, offsets/lag and the Prometheus scrape were checked, then Track B services were stopped with named volumes retained. These are **historical REPLAY integration results only**; they do not demonstrate a live source, live ingestion, live warning or live operational service. [repo: `docs/trackb/RUNBOOK.md`, `docs/trackb/TRACKB_REPORT.md`]

Migration 100 and Track B persistence are verified only against the isolated test database. The shared project database `twinguard` was checked read-only; it remains without migration 100 or Track B migration tables. Never run Track B writes or migrations against the shared database. [repo: `docs/trackb/G0_REPAIR_EVIDENCE.md`, `docs/trackb/RUNBOOK.md`]

## Interfaces and current availability

The Track B FastAPI router contains separate read-only reservoir, alert, backtest and rule-parameter endpoints; the host application has not mounted this router. AI forecasting, impact and route operations remain unimplemented stubs. The backend's Track B adapter reports not-configured until integration is implemented. The AI layer catalogue can report recorded metadata and explicit unavailable fields, but no HTTP tile-serving endpoint is implemented. The frontend redesign uses deterministic local mock/demo data and keeps real API/database integration disabled; demo values are not live measurements. G0 remains not ready, so no contract freeze or operational decision use is implied. [repo: `services/trackb/router.py`, `services/ai-service/app/main.py`, `services/backend/src/main/java/org/twinguard/backend/adapter/notconfigured/NotConfiguredTrackBAdapter.java`, `docs/trackb/G0_REPAIR_EVIDENCE.md`, `docs/ui/PROFESSIONAL_UI_REDESIGN.md`]

## Work still requiring evidence or review

Obtain authoritative documentation for the reservoir date/time convention before treating event instants as historically confirmed. Verify rainfall units and historical capacity series. Continue seeking dated release/outflow and gate records; until obtained, preserve release as unavailable. Integrator review is required for proposed API contract changes and G0 evidence; do not claim G0 ready or contracts frozen. [repo: `docs/trackb/G0_REPAIR_EVIDENCE.md`, `docs/MANUAL_TODO.md`, `docs/master/GATE_G0_REPORT.md`]
