# Phase 10 risk-map lineage (CR-003 / A03)

## Inputs read

| Input | Use |
|---|---|
| `data/processed/grid/cma_mask.tif` | EPSG:32644, 30 m master grid and CMA mask |
| `data/processed/alignment/spatial_blocks.tif` | 3 km block ids for block-wise summaries |
| `data/features/population/worldpop_2021_sum_resampled_30m.tif` | Model-estimated exposure; NoData counted separately |
| `data/features/predictions/phase9b_v2/probability_mean_apparent.tif` | Phase 9B apparent full-data scores |
| `data/features/predictions/phase9b_v2/interval_lower90_apparent.tif`, `interval_upper90_apparent.tif` | Phase 9B apparent uncertainty bounds; copied unchanged |
| `data/features/predictions/phase9c/radar_probability_mean_apparent.tif` | Phase 9C apparent scores inside radar observability only |
| `data/features/predictions/phase9c/radar_mondrian_p05_apparent.tif`, `radar_mondrian_p95_apparent.tif` | Phase 9C apparent spatial Mondrian bounds; copied unchanged |
| `data/features/predictions/phase9c/radar_observability_mask.tif`, `urban_confidence.tif`, `physical_susceptibility_outside_radar.tif` | Coverage/urban caveat and separate ordinal physical complement |
| `docs/PHASE9C_METRICS.json` | Existing independent OpenCity point cross-check, not used for fitting |
| Read-only PostGIS `twinguard.facilities`, `twinguard.road_edges` (`in_cma=true`) | Point facility counts and representative-point road-length allocation |

## Outputs

The authoritative risk-class GeoTIFFs, copied uncertainty/coverage layers and class-by-3 km block CSV are under `data/features/predictions/phase10_cr003_v3/`. The PNG is `docs/figures/phase10_risk_map_cr003_v3.png`. A generalized 120 m MVT tile set is `data/processed/tiles/phase10_cr003_v3/phase10_apparent_risk.mbtiles`.

Risk classes are produced from apparent probability scores using fixed cut-points `<0.05`, `0.05–<0.10`, `0.10–<0.25` and `>=0.25`. Class 255 is not assessed and remains NoData in the risk GeoTIFF. The physical complement is kept separate from model probabilities. Facilities are assigned to the grid cell containing each point. For road totals, each entire edge length is assigned to the cell containing `ST_PointOnSurface`; this is an approximation and does not split edges at class or block boundaries.

The main JSON summary is `docs/PHASE10_RISK_MAP_CR003_V3.json`. Database queries use `.env` via a custom parser and a read-only transaction; credentials and connection details were not emitted. No database writes or raw-data changes were made. Earlier same-session draft outputs under `data/features/predictions/phase10/` and `phase10_cr003_v2/` and their matching tile folders are superseded; use only the v3 outputs.
