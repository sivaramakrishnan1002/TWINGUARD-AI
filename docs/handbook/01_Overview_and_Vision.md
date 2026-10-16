# Overview and vision

## The problem

Chennai faces urban flood emergencies in which rainfall, drainage, rivers, reservoirs, roads, people and public services interact. A map of predicted water alone does not answer whether a route will stay passable, which shelter may be reachable, or how confident the forecast is. The project context and problem framing come from the user's planning brief. [user]

The system is intended for research and decision support. It is not an official warning service, a replacement for emergency authorities, or a guarantee that a route or shelter is safe. [user]

## Vision: decision continuity

The proposed loop is: collect observations and forecasts → estimate current and future flood conditions → quantify uncertainty → update the city representation (“twin state”) → estimate effects on roads, people and facilities → compare actions → show a recommendation with evidence → update when new information arrives. “Digital Twin” here means a data-linked digital representation of a real place that can be updated and used to test scenarios. The loop is a target design, not an implemented product. [user]

## Example of a future operator experience

> “Flooding may intensify in Zone X in 90 minutes. Road A has a high chance of becoming impassable. Shelter B may approach capacity. Route C is expected to remain safer over the journey. Consider evacuation now; confidence is moderate.”

This is an illustrative sentence only. Zone X, roads, shelter status, timing and confidence are not measured results and must not be presented as actual Chennai alerts. [user]

## What TwinGuard is

- A research platform for testing a connected flood-to-decision workflow. [user]
- A proposed two-track system: a slower, richer event forecast and a faster rain/reservoir alert. [user]
- A way to compare baseline models, uncertainty methods, routes and counterfactual actions under documented data limits. [user]

## What it is not

- Not a CRUD application (a basic create/read/update/delete database interface), static GIS map, dataset dashboard, or collection of disconnected models. [user]
- Not a validated public warning system, dispatch tool, or substitute for local authorities. [user]
- Not currently a trained flood predictor, working routing service or operational digital twin. The repository records feature preparation but no model training. [repo: `docs/PROJECT_STATUS.md`]

## Users and intended decisions

The intended decision-maker is an emergency planning or response operator. Candidate decisions include prioritising an area, selecting a departure time, choosing a route that is likely to remain passable, assigning a shelter, and comparing what-if cases such as a bridge closure. User roles and institution are not yet named. [user]

## Geographic scope

The working boundary is the older, smaller CMA, with a measured area of **1,187.460287 km²** in the coverage analysis. It remains provisional; the expanded post-2022 metropolitan area is not the current analysis boundary. The planning brief explains the choice as a denser urban core with better event and map-data fit, but this rationale must be checked against the final project requirements. [repo: `docs/COVERAGE_2015.md`, `docs/GRID_DECISION.md`; user]
