# TwinGuard: an integrated rainfall–reservoir flood digital twin with three-state routing and shelter decisions for Chennai

*Bachelor's final-year project paper · Round 4 (A29), November 2026*

## Abstract

Urban flood response needs more than a hazard map. Decision makers need to see how forecast rain and reservoir state become street-level water, which buildings and people are affected, which roads remain usable, and where shelters can be reached, and they need to test "what if" before it happens. We present TwinGuard, an integrated rainfall + reservoir → flood simulation → 3D digital twin → impact, three-state routing and shelter decision pipeline with what-if scenarios for Chennai, India.

The pipeline works as follows:
- **Inputs:** historical, user-defined or live three-model numerical weather forecasts (Open-Meteo), plus public reservoir storage (CFM-DSS) through a documented assumption rule.
- **Engine:** a local-inertial shallow-water solver at 120 m citywide and 30 m in four focus areas, on CPU or a 4 GB laptop GPU (a 72 h live forecast in 18.3 s on GPU against 154.6 s on CPU).
- **Outputs:** depth and velocity fields; per-building impact for 382,294 footprints and per-ward summaries for 200 wards; roads classified as passable, blocked or unknown; and shelter reachability.
- **Delivery:** a versioned 36-operation API and a seven-tab 3D control room, with an automatic 3-hour live-forecast cycle.

On 108,000 simulated origin–destination cases, three-state routing raised route availability from 8–18% (fail-closed) to 98–99.7%, while flagging 86% of cases as needing verification. The contribution is the integrated, provenance-labelled system. Component accuracy is not validated against independent observations.

## 1. Introduction

Chennai floods repeatedly from intense north-east-monsoon rain and from releases of its upstream reservoirs, as in December 2015, November 2021 and Cyclone Michaung in December 2023. Existing tools tend to address one link of the chain: flood mapping, inundation modelling, evacuation routing, or shelter planning (Li et al., 2025). Our aim was to build a single, reproducible chain that a student project can run on one laptop, and that:

1. accepts historical, user-defined and live forecast rainfall, and couples reservoir state;
2. simulates citywide and neighbourhood-scale inundation fast enough for interactive use;
3. turns water depth and flow into impacts on buildings, people, roads and wards;
4. keeps uncertainty about road state explicit rather than hidden; and
5. presents everything in a 3D digital twin with what-if scenarios and a live mode, with every value labelled by its provenance.

## 2. Related work

- **Flood modelling:** the local-inertial approximation of the shallow-water equations (Bates et al., 2010) is a standard way to simulate urban inundation efficiently. We use it with Bates face depths, a donor-volume limiter, and a fixed-stage sea boundary.
- **Road impact:** depth–disruption functions relate water depth to vehicle speed (Pregnolato et al., 2017).
- **Evacuation and logistics:** flood evacuation planning, covering hazard modelling, shelter choice and routing, is reviewed by Li et al. (2025). Coupled flood–road network evacuation for dam-failure flooding is shown by An et al. (2025).
- **Uncertain road states:** recent work treats road accessibility under flooding as uncertain and values verification or sensing, through Bayesian active verification of lifeline roads (Li, Song & Li, 2026) and Bayesian-network flood sensing (Pan, Mohammadi & Taylor, 2026).

Our three-state road ledger (passable, blocked, unknown) is closest to this last line of work. A preregistered literature review ([A21 review](literature/ROUTING_UNKNOWN_EVIDENCE_2025_2026.md)) found no basis for claiming it as a new method on its own. Our contribution is therefore the integration of these components into one Chennai-specific, provenance-labelled pipeline with a 3D digital twin and live operation.

## 3. Data

| Layer | Source | Use |
|---|---|---|
| Terrain | Copernicus GLO-30, conditioned with burned river channels | Bed elevation (EPSG:32644) |
| Land cover | ESA WorldCover 2021 | Manning roughness, infiltration |
| Population | WorldPop 2021 | Exposure |
| Buildings, roads, facilities | OpenStreetMap (382,294 buildings; 566,307 road segments) | Impact, routing, shelters |
| Wards | GCC 200-ward boundaries (DataMeet/Transparent Chennai, CC BY-SA 2.5 IN) | Ward summaries |
| Event rainfall | GPM IMERG daily with ERA5 hourly shape | Historical replay (2015, 2021, 2023) |
| Forecast rainfall | Open-Meteo: ECMWF IFS, UKMO 10 km, ICON | Live and forecast runs |
| Reservoirs | CFM-DSS public dashboard (daily level and storage) | Outlet inflow by assumption rule |
| Flood labels | UNOSAT November 2015 (accepted); NRSC Dec 2023 (preliminary) | Training and cross-check |

The 157 raw files are hash-audited (157/157 matches). Flood labels passed through a pre-registered acceptance rule. SAR-derived labels failed it, so only the UNOSAT references are used ([G1 report](master/GATE_G1_REPORT.md)).

## 4. Methods

### 4.1 Flood engine

The engine (`services/flood_engine/hires.py`) solves the local-inertial equations on a regular grid:
- **Physics:** Manning friction from land cover; plan-area porosity from building coverage; land-cover infiltration rates; per-cell rainfall; point inflows at river cells for reservoir releases; a sea boundary at a fixed stage (tide offset).
- **Time stepping:** CFL-limited, with depth frames saved every 15 or 30 minutes.
- **Grids:** citywide 120 m (440 × 343 cells, 77,296 active) and 30 m focus grids for Velachery, Adyar, T. Nagar and Porur (200 × 200 each). Focus grids take their boundary water surface from the matching citywide run.
- **Ensemble:** an optional 3-member set (Manning × {1, 0.75, 2}, infiltration × {1, 1.5, 0.5}) gives p05/p95 bracket members.
- **Outputs:** per-frame depth, depth-averaged velocity (u, v) and water-surface elevation ([A27](../pipelines/a25_hires/A27_FLOW.md)).

**GPU backend.** A torch float32 implementation records each time step once as a CUDA graph and replays it, with NumPy as default and automatic fallback ([GPU benchmark](FLOOD_ENGINE_GPU_BENCHMARK.md)).

### 4.2 Forcing and reservoir coupling

- **Forecast rain:** sampled on a 0.05° lattice for three weather models, mapped to grid cells by nearest native model cell, and aligned on interval-end hourly labels. A 24 h past window is discarded as spin-up.
- **Reservoir coupling** (rule `A28-RES-STORAGE-v1`, an explicit assumption because CFM-DSS publishes no release data):
  - below 90% storage, no release;
  - from 90% to 100%, a linear ramp to Q_ctrl;
  - at 100% or more, spill at 2 × Q_ctrl;
  - Q_ctrl is Chembarambakkam 170, Poondi 140, Puzhal 60 and Cholavaram 30 m³/s;
  - missing or stale (> 48 h) snapshots give zero inflow ([A28](../pipelines/a25_hires/A28_RESERVOIR_COUPLING.md)).

### 4.3 Impact, three-state routing and shelters

- **Buildings:** each building takes the peak depth and time of peak of its centroid cell.
- **Ward risk:** each ward's class combines its 95th-percentile land depth and its flooded fraction (≥ 0.10 m).
- **Road states:** each road segment is `ASSESSED_PASSABLE` (midpoint depth < 0.30 m), `ASSESSED_BLOCKED` (≥ 0.30 m) or `UNKNOWN` (no depth coverage, or a bridge or tunnel). The speed factor follows Pregnolato et al. (2017).
- **Routing:** first uses passable edges only. If no route exists, it searches passable plus unknown edges, minimising unknown distance, and labels the result `CONDITIONAL / NEEDS VERIFICATION` ([A21](ROUTING_THREE_STATE_BATCH3.md)).
- **Shelters:** a shelter is reachable when its site is dry (< 0.15 m) and it connects to the main passable network. Capacities (shelter 100, school 250, college 500, community hall 150 people) are assumptions.

### 4.4 Susceptibility model

Phase 9B/9C random-forest ensembles were trained on the November 2015 UNOSAT labels. They were evaluated by spatially blocked 5-fold cross-validation (3 km blocks plus buffer) at true prevalence, against eight calibrated baselines ([G2 report](master/GATE_G2_REPORT.md)).

### 4.5 Software system

- **API:** a FastAPI service exposes the C4 v3 contract, 36 operations covering simulations, depth, flow, wards, buildings, roads, routes, shelters, incidents, the emergency plan, what-if comparison, static layers and live mode ([contract](master/contracts/c4_openapi_v3.md)).
- **UI:** a React/CesiumJS interface with seven tabs (Situation Overview, Flood Simulation, Emergency Support, Road Routing, What-if Simulation, Reservoir Monitoring, Digital Twin 3D City) over Google Photorealistic 3D Tiles.
- **Live mode:** a scheduler runs a 72 h forecast every 3 hours, with a 600 s manual-refresh limit, a daily Open-Meteo budget, and last-good fallback (CR-021).
- **Packaging:** nginx, the AI service and the backend are packaged with Docker Compose (B11).

## 5. Results

### 5.1 Susceptibility

| Metric | Value | Source |
|---|---|---|
| Phase 9B ensemble vs terrain-logistic baseline | PR-AUC +0.183 ± 0.054 (5/5 folds) | [Phase 9B v2](PHASE9B_MODEL_UPGRADE_V2.md) |
| Phase 9C exposure-free model | PR-AUC 0.219 (elevation 0.069; waterway distance 0.074; random 0.063) | [Phase 9C final](PHASE9C_ADDENDUM_CR004_FINAL.md) |
| Out-of-event, Dec 2023 NRSC (preliminary map) | PR-AUC 0.121 (lift 2.76), ROC-AUC 0.778, n = 574,018 cells | [2023 check](PHASE9C_OUT_OF_EVENT_2023.md) |

### 5.2 Citywide and focus simulations

| Scenario | Grid | Flooded ≥ 0.10 m | Buildings affected | People exposed | Mass balance | run_id |
|---|---|---:|---:|---:|---:|---|
| Dec 2015, 48 h | 120 m | 406.7 km² | 94,034 | 1,793,134 | 1e-6 | `evt-20261107T120140Z-b0df587c` |
| Nov 2021, 48 h | 120 m | 241.6 km² | 52,261 | 1,068,723 | 2e-6 | `evt-20261107T120550Z-acee1c29` |
| Dec 2023, 48 h | 120 m | 233.5 km² | 52,870 | 1,067,561 | 0 | `evt-20261107T172118Z-1f3e8383` |
| Dec 2015, 48 h, Velachery | 30 m | 15.3 km² | 11,210 | 132,830 | 8.1e-5 | `evt-20261107T172655Z-b8175ee2` |
| What-if: rain 130%, Chembarambakkam 850 m³/s, tide +0.5 m | 120 m | 481.0 km² | 113,535 | 2,130,253 | 1.8e-5 | `whatif-20261108T045006Z-3e52ff0a` |

Source: [A25 report](../pipelines/a25_hires/REPORT.md). These magnitudes are upper-end, because the model has no storm drains (§7). In Dec 2015, Ward 189 (Perungudi, the Pallikaranai marsh area) comes out in the highest risk class, with 69% of its area flooded and 2.8 m maximum depth (same run).

### 5.3 Engine performance

| Case (citywide 120 m unless noted) | CPU (NumPy) | GPU (CUDA graph, RTX 3050 4 GB) | Agreement |
|---|---:|---:|---|
| 24 h event | 62.8 s | 17.1 s | Identical steps; mean depth difference < 1 mm |
| 48 h event (2021) | 230.9 s total (A25 batch) | 12.8 s solve (1.0 ms per step); 62.4 s with eager kernels before CUDA graphs | Mass balance ≤ 2e-6 |
| 72 h live forecast | 154.6 s | 18.3 s | Identical peak grids at 0.01 m |
| 24 h focus 30 m (nested) | 104.9 s | 46.6 s | Flooded IoU 1.0 |

Peak VRAM is 4–30 MB. Sources: [GPU benchmark](FLOOD_ENGINE_GPU_BENCHMARK.md), [A28 live check](../pipelines/a25_hires/A28_RESERVOIR_COUPLING.md).

### 5.4 Three-state routing

| Measure (108,000 primary simulated OD cases) | Fail-closed | Three-state |
|---|---:|---:|
| Route available (95% cluster-bootstrap interval) | 8.1–18.3% | 98.0–99.7% |
| Routes needing verification | — | 85.88% (92,750) |
| Arcs to verify to cover every conditional case | — | 50 (greedy queue) |

Source: [three-state routing](ROUTING_THREE_STATE_BATCH3.md), commit f33797b. On the fully assessed held-out simulated member, both methods had zero simulated blocked outcomes. These are simulation outcomes, not observed road outcomes.

### 5.5 End-to-end system

- **Packaged historical replay:** the 2015 event flows through nginx, the API, the engine and the UI (`evt-20261108T152128Z-59eba744`). All seven API outputs were schema-valid and byte-identical on repeat. An in-container CPU computation took 161 s. Packaged UI screenshots: [flood simulation](ui/screenshots/17_g5_packaged_flood_simulation.webp), [digital twin](ui/screenshots/17_g5_packaged_digital_twin.webp) ([G5](master/GATE_G5_REPORT.md)).
- **Packaged live cycle:** `sim-20261110T120422Z-1a781dbd` and `sim-20261110T121126Z-979f9524`, with A28 coupling applied, refresh limits enforced, and last-good fallback under a simulated upstream failure ([B53](trackb/B53_LIVE_CYCLE_REPORT.md)).
- **UI views:** [overview](ui/screenshots/01_situation_overview.webp), [modelled flow](ui/screenshots/14_flow_modelled_velocity.webp), [30 m focus run](ui/screenshots/18_focus_run_after_t24.webp), [live mode](ui/screenshots/20_live_overview.webp).

## 6. Discussion

The system shows that the full chain, from forecast or reservoir state to routing and shelter decisions, can run on one laptop. The GPU path makes a 72-hour citywide forecast take under 20 seconds, which is what makes the 3-hour live cycle and interactive what-if scenarios practical.

Keeping provenance explicit (SIMULATED, MODEL_FORECAST, PUBLISHED_SNAPSHOT, SCENARIO_INPUT, REPLAY) matters most where inputs are weak: reservoir releases are never published, and road states are often unassessed. The three-state ledger turns that missing evidence into a short, prioritised verification list (50 arcs) instead of silently treating unknown roads as open or closed.

The main open question is accuracy. With one accepted training event and no independent depth or road observations, the magnitudes in §5.2 should be read as relative, scenario-comparison quantities.

## 7. Limitations

1. **Validation:** a single training event (Nov 2015). The out-of-event check uses an unaccepted 2023 map. There are no independent depth or road observations.
2. **Hydraulics:** a simplified 120 m (30 m focus) local-inertial model on a surface DEM with no storm drains, so flood extents are upper-end and DEM pits can show unrealistic local depths.
3. **Assumptions:** reservoir outlet inflows, shelter capacities, road thresholds and 98% of building heights are assumed and labelled as such.
4. **Forecast:** live mode is a numerical-model forecast through this simplified model, not an official warning, and its skill is unmeasured.
5. **Deployment:** the packaged checks ran on CPU (the GPU container image is not built), and the Cesium token is compiled into the local bundle.

## 8. Conclusion

TwinGuard delivers an integrated rainfall + reservoir → flood simulation → 3D digital twin → impact, three-state routing and shelter decision pipeline with what-if scenarios for Chennai. It is reproducible, provenance-labelled and fast enough for live use on modest hardware. The most valuable next step is independent evidence: accepted flood maps for further events, observed depths, and road-closure records, to calibrate the engine and turn its relative scenario outputs into validated estimates.

## Reproducibility

- **Commits:** A25 a4b2cbc; A27 b90c0c6; A26 887d089, a64cc30 and 943ae77; A28 bf50c38; A21 f33797b; B47 d5a45e9; B51 818c7fc; B53 bb6e690; B50 720264b.
- **Run outputs:** `data/features/simulation/a25_runs_v1/`, `a26_benchmark_v1/` and `a28_live_check_v1/`, with manifests and hashes.
- **Gate evidence:** `docs/master/GATE_G1_REPORT.md` to `GATE_G5_REPORT.md` and `ROUND2_LIVE_REVIEW.md`.
- **Report checks:** recorded in the A29 closeout. No new science runs were made for this paper.

## References

- An, G., Wang, Z., Qu, M., Hu, S. (2025). Integrated optimization of emergency evacuation routing for dam failure-induced flooding: a coupled flood–road network modeling approach. *Applied Sciences* 15(8), 4518. doi:10.3390/app15084518
- Bates, P. D., Horritt, M. S., Fewtrell, T. J. (2010). A simple inertial formulation of the shallow water equations for efficient two-dimensional flood inundation modelling. *Journal of Hydrology* 387, 33–45. doi:10.1016/j.jhydrol.2010.03.027
- Li, C., Jiang, C., Chen, J., Lam, M. Y., Xia, J., Ahmadian, R. (2025). An overview of flood evacuation planning: models, methods, and future directions. *Journal of Hydrology* 656, 133026. doi:10.1016/j.jhydrol.2025.133026
- Li, H., Song, X., Li, Y. (2026). Bayesian active verification of lifeline roads for risk aware emergency logistics with trucks and drones. *Discover Artificial Intelligence* 6, 962. doi:10.1007/s44163-026-02033-1
- Pan, X., Mohammadi, N., Taylor, J. E. (2026). Positioning road-level flood sensing for disruption assessment based on uncertainties and Bayesian networks. *Reliability Engineering & System Safety*, 113592. doi:10.1016/j.ress.2026.113592
- Pregnolato, M., Ford, A., Wilkinson, S. M., Dawson, R. J. (2017). The impact of flooding on road transport: a depth-disruption function. *Transportation Research Part D* 55, 67–81. doi:10.1016/j.trd.2017.06.020
