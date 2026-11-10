# User guide — the 7 tabs

*Added 10 Nov 2026 (B55). The UI opens on the latest **live forecast**. Screenshots are linked, not copied: [`docs/ui/screenshots/`](../ui/screenshots/README.md).* [repo: B48/B52 commits]

## Before you start

- **The badge (header and map)** shows what you are looking at:

  | Badge | Meaning |
  |---|---|
  | **LIVE FORECAST · HH:MM IST** | The automatic 3-hourly forecast run (`run_kind` LIVE_FORECAST), with its Open-Meteo issue time |
  | **REPLAY** | An archived event (Dec 2015, Nov 2021, Dec 2023) re-simulated from saved rainfall |
  | **WHAT-IF** | A what-if run built on a base run |
  | **CUSTOM / FORECAST** | User rainfall, or an on-demand forecast run |
  | **DEMO / SIMULATION** | Shown only before any run is known |

- **The permanent note** "Model forecast — not an official warning" appears on every tab.
- **The live bar** shows "Updated HH:MM IST · next HH:MM", health dots for Open-Meteo and CFM-DSS, and a **Refresh** button (at most once per 10 min). If a cycle fails, a `last_error` banner appears and the last good run stays on screen.
- **Following live:** picking a replay or what-if run *pins* it. "Back to live forecast" follows live again.

Screenshots: [20_live_overview](../ui/screenshots/20_live_overview.webp), [21_live_badge_status](../ui/screenshots/21_live_badge_status.webp), [21_switch_to_replay](../ui/screenshots/21_switch_to_replay.webp), [21_back_to_live](../ui/screenshots/21_back_to_live.webp).

## 1 Situation Overview

The latest run's headline numbers: maximum depth, flooded area, buildings affected, population exposed, roads blocked and wards affected. It also shows Chennai weather (Open-Meteo, cached at most every 10 min), reservoir context, incident counts by severity, and the most affected wards.
Screenshot: [01_situation_overview](../ui/screenshots/01_situation_overview.webp), [20_live_overview](../ui/screenshots/20_live_overview.webp).

## 2 Flood Simulation

Run a simulation and play it back. Choose an archived event, enter custom rainfall (15/30/60 min intervals), or start a forecast run; then use the timeline to play the depth frames. Per-ward summaries are shown. Runs are queued, and an identical request returns the cached run.
Screenshots: [02_flood_simulation](../ui/screenshots/02_flood_simulation.webp), [17_g5_packaged_flood_simulation](../ui/screenshots/17_g5_packaged_flood_simulation.webp), [20_live_flood_simulation](../ui/screenshots/20_live_flood_simulation.webp).

## 3 Emergency Support

- **Shelters:** reachability and allocation. Capacities are *assumed*; the capacity factor can be 0.5, 1 or 2.
- **Incidents:** generated from the run's results and labelled as generated.
- **Resources:** boats, teams and vehicles are owner-set scenario inputs (`SCENARIO_INPUT`), and a greedy assignment plan pairs them with incidents. This is decision support, not dispatch.

Screenshot: [03_emergency_support](../ui/screenshots/03_emergency_support.webp).

## 4 Road Routing

Roads are shown in three states: passable, blocked (at 0.30 m or more; tunnels at half that) and unknown (for example bridges). Route search compares three policies — *avoid blocked*, *avoid blocked and unknown* and *shortest dry* — against a dry baseline. A route through unknown roads is **CONDITIONAL**.
Screenshots: [04_road_routing](../ui/screenshots/04_road_routing.webp), [13_e2e_road_routing](../ui/screenshots/13_e2e_road_routing.webp).

## 5 What-if Simulation

Modify a base run: rainfall from 0–300 %, reservoir releases of 0–3,000 m³/s per reservoir (assumed scenario inputs), and a tide offset from −1 to 2 m. The comparison shows the changes against the base, overall and by ward.
Screenshots: [05_what_if_simulation](../ui/screenshots/05_what_if_simulation.webp), [12_e2e_what_if](../ui/screenshots/12_e2e_what_if.webp).

## 6 Reservoir Monitoring

The CFM-DSS public dashboard snapshot (`PUBLISHED_SNAPSHOT`, date-only `source_date`). In live runs, the A28 outlet inflow is labelled **ASSUMPTION**, never as a release.
Screenshot: [06_reservoir_monitoring](../ui/screenshots/06_reservoir_monitoring.webp).

## 7 Digital Twin 3D City

CesiumJS with Google Photorealistic 3D Tiles. Water is draped or extruded from the depth grid and animated by the modelled `/flow` velocities. Layers cover buildings by depth class, roads, shelters, incidents and wards. You can switch between 2D, 3D and satellite views. The Google logo and attribution always stay visible.
Screenshots: [07_digital_twin_3d_city](../ui/screenshots/07_digital_twin_3d_city.webp), [14_flow_modelled_velocity](../ui/screenshots/14_flow_modelled_velocity.webp), [17_g5_packaged_digital_twin](../ui/screenshots/17_g5_packaged_digital_twin.webp), [20_live_digital_twin](../ui/screenshots/20_live_digital_twin.webp).
