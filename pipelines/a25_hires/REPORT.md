# A25 — High-resolution flood simulation for 3D

**Status:** done with caveats (2026-11-08). **Engine:** `twinguard-flood-engine/2.0.0` (`services/flood_engine/hires.py`, `scenario.py`, `products.py`). **Static assets:** `data/features/live/a25_static_v1/`. **Runs:** `data/features/simulation/a25_runs_v1/`.

## Resolutions achieved

| Grid | Cell | Rows × cols | Active cells | Sea / nested boundary cells |
|---|---:|---|---:|---:|
| `citywide_120m` (default citywide) | 120 m | 440 × 343 | 77,296 | 1,039 |
| `citywide_90m` | 90 m | 587 × 457 | 136,096 | 1,248 |
| `focus_30m_VELACHERY` | 30 m | 200 × 200 (6 × 6 km) | 36,124 | 736 |
| `focus_30m_ADYAR` | 30 m | 200 × 200 | 30,702 | 859 |
| `focus_30m_T_NAGAR` | 30 m | 200 × 200 | 37,966 | 751 |
| `focus_30m_PORUR` | 30 m | 200 × 200 | 37,802 | 761 |

All grids are EPSG:32644 with the origin at the upper-left corner and row 0 north. `meta.json` → `grid` is exactly the C4 v3 GridSpec. The terrain is the conditioned Copernicus GLO-30 DEM (`data/processed/terrain_cleaned/cleaned_elevation_m.tif`, derived from `data/raw/dem/`) aggregated by mean. The 600 m A06/A23 path (`solver.py`, `engine.py`) is unchanged and still tested.

## Runtime (16-core Windows machine, 8 solver threads, NumPy only)

| Run | Cell | Duration | Frames | Solver steps | Engine s | Max mass-balance error | Max depth m | Flooded km² (≥0.10 m) | Buildings ≥0.10 m | People exposed | Wards ≥ moderate | run_id |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| event 2015-12-01 citywide 120 m | 120 m | 48 h | 97 × 30 min | 11,827 | 250 | 1.0e-06 | 7.84 | 406.7 | 94,034 | 1,793,134 | 197 | `evt-20261107T120140Z-b0df587c` |
| event 2021-11-11 citywide 120 m | 120 m | 48 h | 97 × 30 min | 12,416 | 231 | 2.0e-06 | 11.01 | 241.6 | 52,261 | 1,068,723 | 197 | `evt-20261107T120550Z-acee1c29` |
| event 2023-12-03 citywide 120 m | 120 m | 48 h | 97 × 30 min | 9,680 | 194 | 0.0e+00 | 3.73 | 233.5 | 52,870 | 1,067,561 | 197 | `evt-20261107T172118Z-1f3e8383` |
| event 2015-12-01 citywide 120 m, 3 members | 120 m | 24 h | 49 × 30 min | 14,208 | 144 | 0.0e+00 | 2.29 | 119.8 | 33,093 | 654,587 | 197 | `evt-20261107T172432Z-06dd0e43` |
| event 2015-12-01 focus 30 m VELACHERY | 30 m | 48 h | 97 × 30 min | 51,801 | 354 | 8.1e-05 | 9.77 | 15.3 | 11,210 | 132,830 | 23 | `evt-20261107T172655Z-b8175ee2` |
| event 2015-12-01 focus 30 m ADYAR | 30 m | 48 h | 97 × 30 min | 61,125 | 531 | 9.4e-05 | 7.35 | 11.2 | 5,368 | 96,355 | 18 | `evt-20261107T173249Z-6419fd66` |
| event 2015-12-01 focus 30 m T_NAGAR | 30 m | 48 h | 97 × 30 min | 58,773 | 1574 | 2.9e-05 | 15.2 | 15.8 | 17,447 | 195,541 | 38 | `evt-20261108T041721Z-52a22060` |
| event 2015-12-01 focus 30 m PORUR | 30 m | 48 h | 97 × 30 min | 52,808 | 390 | 1.5e-05 | 16.88 | 16.8 | 9,998 | 156,880 | 15 | `evt-20261108T044335Z-b11d2025` |
| what-if: 2015 base, rain 130%, Chembarambakkam 850 m3/s, tide +0.5 m | 120 m | 48 h | 97 × 30 min | 21,242 | 334 | 1.8e-05 | 13.54 | 481.0 | 113,535 | 2,130,253 | 197 | `whatif-20261108T045006Z-3e52ff0a` |
| custom: 6 h burst 5/20/45/60/30/10 mm, 15-min frames | 120 m | 24 h | 97 × 15 min | 7,884 | 127 | 1.0e-06 | 11.13 | 396.2 | 89,426 | 1,720,586 | 198 | `sim-20261108T045540Z-76171aa4` |
| event 2015-12-01 citywide 90 m | 90 m | 24 h | 49 × 30 min | 6,101 | 176 | 1.0e-06 | 2.17 | 129.7 | 37,209 | 739,816 | 200 | `evt-20261108T090210Z-24c676fd` |

Engine seconds include writing all products. ADYAR was re-timed (531 s; identical 61,125 steps) because its batch wall time spanned a machine sleep. T_NAGAR ran while the machine was heavily loaded (≈27 ms/step vs ≈7 ms/step for the other focus areas). Per-step cost on an idle machine: ≈9 ms at 120 m (77k cells), ≈23 ms under load; ≈7 ms at 30 m (≈37k cells). A 24 h citywide 120 m run takes 45-105 s, 48 h 190-250 s; a 48 h 30 m focus run 350-530 s (plus its cached citywide parent).

The solver is the A06 local-inertial scheme with Bates (2010) face depths, a fixed-stage sea boundary (stage = tide offset), active river channels for reservoir releases, and the A06 donor-volume limiter. Each step is split into row strips on a thread pool, and results are bit-identical for any thread count (tested). Optimisation from 61 to about 23 ms per step at 120 m came from float32 fields, in-place updates and mask multiplication instead of boolean indexing.

## Outputs per run (`a25_runs_v1/<run_id>/`)

| File | Content |
|---|---|
| `run.json` | C4 v3 SimulationRun: request, `frames` (index, valid_time_utc, elapsed_minutes), GridSpec, summary, provenance (forcing SHA-256, static bundle hash), diagnostics (mass balance, steps, min dt), ≤ 5 limitations |
| `frames.npz` | `depth_cm` uint16 [frames, rows, cols] every 15 or 30 min (65535 = NoData; 0 = dry) |
| `peak.npz` | `depth_mean` peak, `depth_p05` / `depth_p95` (3-member runs: low/high bracket members), `velocity_mps` (peak, sampled at frames), `peak_frame` |
| `buildings.npz` | Per building in the grid: max depth, frame of max (→ `time_of_max_utc`), depth class |
| `wards.json` | C4 v3 WardSummary per GCC ward, plus the documented risk rule |
| `road_states.npz` | A21 three-state per road segment per frame (0 passable, 1 blocked ≥ 0.30 m, 2 unknown) |
| `shelters.npz` | Per-frame shelter reachability, site peak depth, nearest road node |

The batch summary is in `a25_runs_v1/batch_summary.json`.

## Static bundle (`a25_static_v1/`)

- **Per grid** (`static.npz`): `z`, `active`, `boundary` (alias `drain`), `mann`, `porosity`, `infiltration_mm_h`, `landcover`, `population` (WorldPop 2021, summed), `ward_id`, `cell_lon/lat`, `road_length_m`, and the index arrays `building_cell`, `road_cell`, `arc_cell` (per `directed_arcs.parquet` arc), `shelter_cell`. `meta.json` holds GridSpec, `inflow_cells` and the bundle hash.
- **`shared/buildings.npz`:** 382,294 OSM footprints with centroid, ward, footprint ring (WGS84), `height_m` and `height_source`. Of these, 61 use `osm_height` (PBF `height` tag), 8,348 use `osm_levels` (`building:levels` × 3.2 m) and 373,885 are `estimated`.
- **`shared/wards.geojson`:** GCC wards 1–200 from DataMeet `Chennai/Wards.geojson` (Transparent Chennai), CC BY-SA 2.5 India, commit `313d8feb`, SHA-256 `2dff80b6…1ab2`. The source's ward-0 cantonment polygon is excluded. Ward names are not in the source; they display as "Ward N" with the zone.
- **Other shared files:** `roads.npz` (566,307 segments with geometry and structure flag), `road_topology.npz`, `shelters.npz` (shelter 100, school 250, college 500, community hall 150 people, all assumed; A10 values plus halls), `focus_areas.geojson`, `reservoirs` in `meta.inflow_cells`, `events.json`.
- **Events:** `2015-12-01`, `2021-11-11` and `2023-12-03`, each a 72 h UTC window from event day −1, using A06's IMERG daily CMA mean with the ERA5 hourly shape.

## Documented rules

- **Height estimate** (`build_static.estimate_height`): apartments, residential and hotel 12 m; house and detached 6.4 m; hut, shed, roof and garage 3.5 m; commercial, office, retail, school, college, hospital and public 9.6 m; industrial and warehouse 8 m. Otherwise by footprint area: under 60 m² 3.5 m, under 150 m² 6.4 m, under 600 m² 9.6 m, under 2,500 m² 12.8 m, else 16 m.
- **Ward `risk_level`:** based on the ward's 95th-percentile peak depth on land cells (`depth_p95_m` in `wards.json`; a percentile so that one DEM pit cannot classify a ward) and its flooded fraction (peak ≥ 0.10 m, permanent water excluded):
  - severe if p95 ≥ 1.0 m and ≥ 10% flooded, or ≥ 25% flooded;
  - high if p95 ≥ 0.5 m and ≥ 5% flooded;
  - moderate if p95 ≥ 0.15 m or ≥ 5% flooded;
  - otherwise low.
  - `max_depth_m` is still reported as the true maximum. `services.flood_engine.scenario.rebuild_wards` recomputes ward files for existing runs.
- **Roads (A21/A08):** midpoint-cell depth ≥ 0.30 m is ASSESSED_BLOCKED; bridges and tunnels, NoData and unmapped segments are UNKNOWN. The speed factor follows Pregnolato et al. (2017).
- **Shelter reachable:** site depth < 0.15 m and the nearest road node lies in an all-passable component of at least 1,000 nodes.
- **Reservoir release:** injected at the river cell nearest each reservoir (Chembarambakkam → Adyar; Poondi, Puzhal and Cholavaram → Kosasthalaiyar).
- **Focus nesting:** the outer ring takes the time-interpolated water surface of the matching citywide run. Cells that are dry in the parent act as free outflow.

## Engine call for Lane B

```python
from services.flood_engine.scenario import run_scenario
doc = run_scenario(static_root, runs_root, *, mode,              # "event" | "custom" | "forecast" | "what_if"
                   event_key=None, custom_rainfall=None,          # CustomRainfall dict
                   what_if=None,                                  # {base_run_id, rainfall_scale_pct, reservoir_release_m3s, tide_offset_m}
                   duration_hours=24, resolution="citywide",      # or "focus" + focus_area
                   focus_area=None, frame_interval_minutes=30, members=1,   # members 3 adds p05/p95
                   citywide_cell_m=120, threads=None, fetch_forecast=None, progress=None)
# -> SimulationRun dict (run_id evt-/sim-/whatif-...; identical request -> cached copy)
```

The CLI equivalent is `python -m services.flood_engine.scenario_cli --mode event --event-key 2015-12-01 --hours 24 [--resolution focus --focus-area VELACHERY]`. The readers in `services/flood_engine/products.py` return C4 v3 bodies: `depth_frame`, `buildings_page`, `wards`, `roads`, `shelters`, `static_layer`, `events`, `list_runs`, `get_run` and `depth_frames_binary`.

## Rebuild

```
python -m pipelines.a25_hires.build_static --resolutions 120 90     # ~4 min (first run also parses the OSM PBF)
python -m pipelines.a25_hires.run_batch --hours 48
python -m pytest tests/flood_engine tests/phase12_openmeteo_grid
```

## Limitations

1. No storm-drain network; GLO-30 is a surface model. Rain ponds in depressions and DEM pits more than in reality (a few cells reach 7–17 m in excavations or burned channels), so flooded areas and ward risk are upper-end.
2. Event rainfall is spatially uniform (IMERG daily, ERA5 hourly shape). Only forecast mode uses gridded Open-Meteo rainfall.
3. Releases enter at one river cell per reservoir, and the tide is a constant offset with no astronomical cycle.
4. 98% of building heights are estimated. Capacities, risk classes and road states are model-derived display classes.
5. Not validated against observed depths; p05/p95 are bracket members, not statistical quantiles.
