# TwinGuard AI — project on a page

**A decision-support research project for urban flooding in Chennai.** TwinGuard is intended to combine weather, satellite, terrain, reservoir, map and population information to estimate where flooding may occur, show uncertainty, and help compare emergency actions. [user]

## Why it exists

Flood response is a chain of decisions. A predicted flood can affect roads, people, facilities and shelters. A useful system should carry uncertainty through that chain and help an operator compare choices, rather than show a flood map alone. This is the project's research direction; the operational system does not exist yet. [user]

## What is new (carefully stated)

The project proposes to test an integrated **uncertainty-to-decision** workflow: forecasts update a digital representation of the city, and likely future road access, exposure, shelter availability and decisions are compared. It also proposes time-aware routes and “what if” scenarios. The individual methods are established ideas. The team has not completed a literature review sufficient to claim priority or novelty. [user]

## Status

`Phase 1: foundation — reported complete` → `Phase 2: collection and audit — close-out complete, with gaps` → `Phase 3: feature preparation — Part B complete` → `Phase 4: not started`. No flood model has been trained. [repo: `docs/PROJECT_STATUS.md`, `docs/PHASE3_LOG.md`]

## What exists now

Raw sources are locally collected and logged; a common 30 m analysis grid and exploratory weather, terrain, land-cover, OSM, population, reservoir and flood-inspection outputs exist. They are research inputs, not a deployed twin or final validation set. The grid uses the older, pre-2022 CMA boundary provisionally. [repo: `docs/PHASE3_LOG.md`, `docs/GRID_DECISION.md`]

## The immediate next work

Resolve the old-versus-expanded CMA boundary, review coastal terrain and drainage, reconcile OSM counts and test network connectivity, settle the flood-label strategy, and verify product units and reuse terms. Then follow the reviewed roadmap and get explicit approval before Phase 4. [repo: `docs/MANUAL_TODO.md`, `docs/PHASE3_PLAN.md`]

## Where a new teammate should start

Read this page, [Progress and Chronicle](09_Progress_and_Chronicle.md), [Data Inventory](05_Data_Inventory.md), [Flood Events and Labels](06_Flood_Events_and_Labels.md), and [Document Control](17_Document_Control.md). Use the [Coverage Matrix](COVERAGE_MATRIX.md) to locate evidence. Unknown personal details remain marked `[TO BE FILLED]`.
