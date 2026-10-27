# Phase 13 Batch 2 impact analysis

> **Superseded first-run record:** these `batch2_v1` figures were kept for provenance but are not the final A07 result. Use [the corrected `batch2_v4_contract` report](PHASE13_IMPACT_BATCH2_V4.md) and its matching output folder. The intervening v2 partial and v3 outputs were also preserved; v4 is the report of record.

**Status:** DERIVED simulated impact scenarios; not live impact estimates, hydraulic truth, or emergency guidance. The C7 JSON shape is the Lane A `impact-result-v0.1-draft` proposal only; G0 is not ready, so this is not an approved/frozen API or database contract.

## Method

- Input ensemble: 75 event × scenario × horizon cases; 4500 member-threshold rows; 2430 eligible cells on a 600 m EPSG:32644 grid.
- Edge depth is the simulated depth at each road segment midpoint on the 600 m grid. Each edge can join to its cell probability in `data/features/impact/batch2_v1/road_edge_grid_index.parquet` → `cell_impact.parquet`.
- Blocked when depth is at or above 0.30 m; sensitivity screens are 0.15 and 0.50 m. These are assumptions, not locally validated closure/exposure thresholds.
- Each horizon is an instantaneous simulated state at event-window UTC start plus lead hours. No temporal aggregation interval is claimed.
- WorldPop is summed from CMA-limited 30 m static cells into the 600 m solver cells. The known-data sum is reported separately from NoData; unknown cells are not zero.
- Facilities are mapped OSM points. Hospital and shelter categories are reported separately; OSM schools and colleges form an assumed candidate-shelter group.
- Access cascade uses road endpoints collapsed to 600 m cells. A mapped facility counts connected when its cell remains in a component intersecting the largest pre-event road component. This is not origin-destination routing or a measure of facility operation.

## Coverage and source inventory

- Road source features: 566,307; midpoint-assessed edges: 405,601 (13,614.0 km); outside/unassessed on this model grid: 160,706.
- Target facilities mapped: 1,492; by group: {'hospital': 697, 'shelter': 102, 'candidate_shelter': 693}.
- WorldPop known CMA cell-table sum within eligible model cells: 4,836,739.3; source NoData 30 m cells mapped there: 96,254. Values are model estimates, not census counts.

## Selected 0.30 m ensemble summaries

Full result distributions and all three threshold screens are in `data/features/impact/batch2_v1/impact_results.jsonl`; per-member metrics are in Parquet.

| Event | Scenario | Lead (h) | Known population in depth-screened cells, mean people | Screened road length, mean km | Mapped facilities screened, mean | Hazard coverage |
|---|---|---:|---:|---:|---:|---:|
| 2015-12-02 | perfect_foresight_imerg | 6 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2015-12-02 | perfect_foresight_imerg | 12 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2015-12-02 | perfect_foresight_imerg | 24 | 34,055.4 | 96.93 | 5.8 | 1.000 |
| 2015-12-02 | perfect_foresight_imerg | 48 | 221,131.2 | 734.00 | 39.2 | 1.000 |
| 2015-12-02 | perfect_foresight_imerg | 72 | 110,090.2 | 341.05 | 18.1 | 1.000 |
| 2015-12-02 | rain_error_q10 | 6 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2015-12-02 | rain_error_q10 | 12 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2015-12-02 | rain_error_q10 | 24 | 1,152.8 | 2.21 | 0.0 | 1.000 |
| 2015-12-02 | rain_error_q10 | 48 | 201,214.4 | 657.93 | 37.3 | 1.000 |
| 2015-12-02 | rain_error_q10 | 72 | 103,134.2 | 317.10 | 15.8 | 1.000 |
| 2015-12-02 | rain_error_q50 | 6 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2015-12-02 | rain_error_q50 | 12 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2015-12-02 | rain_error_q50 | 24 | 34,555.7 | 100.66 | 5.9 | 1.000 |
| 2015-12-02 | rain_error_q50 | 48 | 221,113.9 | 734.68 | 39.2 | 1.000 |
| 2015-12-02 | rain_error_q50 | 72 | 110,090.5 | 341.28 | 18.1 | 1.000 |
| 2015-12-02 | rain_error_q90 | 6 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2015-12-02 | rain_error_q90 | 12 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2015-12-02 | rain_error_q90 | 24 | 65,451.2 | 170.93 | 13.2 | 1.000 |
| 2015-12-02 | rain_error_q90 | 48 | 229,071.0 | 767.56 | 40.2 | 1.000 |
| 2015-12-02 | rain_error_q90 | 72 | 112,126.5 | 351.61 | 18.9 | 1.000 |
| 2015-12-02 | persistence_previous_day | 6 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2015-12-02 | persistence_previous_day | 12 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2015-12-02 | persistence_previous_day | 24 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2015-12-02 | persistence_previous_day | 48 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2015-12-02 | persistence_previous_day | 72 | 1,441.0 | 2.76 | 0.0 | 1.000 |
| 2021-11-13 | perfect_foresight_imerg | 6 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2021-11-13 | perfect_foresight_imerg | 12 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2021-11-13 | perfect_foresight_imerg | 24 | 1,152.8 | 2.21 | 0.0 | 1.000 |
| 2021-11-13 | perfect_foresight_imerg | 48 | 1,152.8 | 2.21 | 0.0 | 1.000 |
| 2021-11-13 | perfect_foresight_imerg | 72 | 864.6 | 1.65 | 0.0 | 1.000 |
| 2021-11-13 | rain_error_q10 | 6 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2021-11-13 | rain_error_q10 | 12 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2021-11-13 | rain_error_q10 | 24 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2021-11-13 | rain_error_q10 | 48 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2021-11-13 | rain_error_q10 | 72 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2021-11-13 | rain_error_q50 | 6 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2021-11-13 | rain_error_q50 | 12 | 576.4 | 1.10 | 0.0 | 1.000 |
| 2021-11-13 | rain_error_q50 | 24 | 1,441.0 | 2.76 | 0.0 | 1.000 |
| 2021-11-13 | rain_error_q50 | 48 | 1,441.0 | 2.76 | 0.0 | 1.000 |
| 2021-11-13 | rain_error_q50 | 72 | 1,441.0 | 2.76 | 0.0 | 1.000 |
| 2021-11-13 | rain_error_q90 | 6 | 2,655.3 | 7.01 | 0.0 | 1.000 |
| 2021-11-13 | rain_error_q90 | 12 | 7,248.7 | 26.11 | 0.0 | 1.000 |
| 2021-11-13 | rain_error_q90 | 24 | 9,574.5 | 33.75 | 0.0 | 1.000 |
| 2021-11-13 | rain_error_q90 | 48 | 25,442.2 | 75.62 | 3.1 | 1.000 |
| 2021-11-13 | rain_error_q90 | 72 | 46,812.3 | 124.61 | 9.5 | 1.000 |
| 2021-11-13 | persistence_previous_day | 6 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2021-11-13 | persistence_previous_day | 12 | 2,947.9 | 6.94 | 0.0 | 1.000 |
| 2021-11-13 | persistence_previous_day | 24 | 106,334.1 | 291.42 | 22.6 | 1.000 |
| 2021-11-13 | persistence_previous_day | 48 | 131,754.4 | 406.10 | 24.2 | 1.000 |
| 2021-11-13 | persistence_previous_day | 72 | 135,098.3 | 421.71 | 24.3 | 1.000 |
| 2023-12-04 | perfect_foresight_imerg | 6 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2023-12-04 | perfect_foresight_imerg | 12 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2023-12-04 | perfect_foresight_imerg | 24 | 720.5 | 1.38 | 0.0 | 1.000 |
| 2023-12-04 | perfect_foresight_imerg | 48 | 116,434.2 | 316.01 | 23.6 | 1.000 |
| 2023-12-04 | perfect_foresight_imerg | 72 | 122,985.7 | 389.98 | 20.0 | 1.000 |
| 2023-12-04 | rain_error_q10 | 6 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2023-12-04 | rain_error_q10 | 12 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2023-12-04 | rain_error_q10 | 24 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2023-12-04 | rain_error_q10 | 48 | 90,277.6 | 226.58 | 20.0 | 1.000 |
| 2023-12-04 | rain_error_q10 | 72 | 115,998.9 | 364.27 | 19.0 | 1.000 |
| 2023-12-04 | rain_error_q50 | 6 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2023-12-04 | rain_error_q50 | 12 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2023-12-04 | rain_error_q50 | 24 | 1,008.7 | 1.93 | 0.0 | 1.000 |
| 2023-12-04 | rain_error_q50 | 48 | 117,138.6 | 318.85 | 23.6 | 1.000 |
| 2023-12-04 | rain_error_q50 | 72 | 123,001.1 | 390.22 | 20.0 | 1.000 |
| 2023-12-04 | rain_error_q90 | 6 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2023-12-04 | rain_error_q90 | 12 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2023-12-04 | rain_error_q90 | 24 | 9,785.2 | 28.25 | 0.8 | 1.000 |
| 2023-12-04 | rain_error_q90 | 48 | 127,516.9 | 373.18 | 24.5 | 1.000 |
| 2023-12-04 | rain_error_q90 | 72 | 125,532.2 | 402.88 | 20.0 | 1.000 |
| 2023-12-04 | persistence_previous_day | 6 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2023-12-04 | persistence_previous_day | 12 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2023-12-04 | persistence_previous_day | 24 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2023-12-04 | persistence_previous_day | 48 | 0.0 | 0.00 | 0.0 | 1.000 |
| 2023-12-04 | persistence_previous_day | 72 | 0.0 | 0.00 | 0.0 | 1.000 |

## Interpretation and limits

- Percentiles are descriptive spread over the 20 fixed simulation members; they are not calibrated confidence intervals.
- A05 hindcasts are not operational forecast skill. The source contains no archived numerical weather prediction forecast for these dates.
- Coarse midpoint sampling can miss local road flooding, bridges, tunnels, drainage, and sub-cell variation. Facility cascades are only a coarse graph-connectivity proxy.
- Exposed population is the known WorldPop estimate in screened cells. If any contributing population pixels are NoData, known-data totals are incomplete and the result is flagged PARTIAL.
- No capacity allocation, shelter demand assignment, route travel time, or safe evacuation path is computed here.
- This local output proposal needs integrator approval and API/UI reconciliation before any shared contract or endpoint consumes it.

## Reproduction

`.venv/Scripts/python.exe -m pipelines.phase13.impact` (the script refuses to overwrite existing outputs).
