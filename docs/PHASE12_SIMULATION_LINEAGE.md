# Phase 12 simulation lineage

All source items below were read only. Input SHA-256 hashes are recorded in `data/features/simulation/batch2_v1/simulation_summary.json`.

| Source | Use | Derived output |
|---|---|---|
| `data/processed/terrain_cleaned/cleaned_elevation_m.tif` | 600 m valid-cell mean terrain and local-inertial bed elevation | Six mean/p05/p95 peak and selected-hour GeoTIFFs per event |
| `data/features/landcover/worldcover_2021_class.tif` | Manning class defaults, built-up porosity and open-water boundary | Model arrays held in memory; assumptions recorded in summary |
| `data/features/hydrology/chennai_waterways.gpkg` | Rasterized mapped channel drain boundaries | Model arrays held in memory |
| `data/features/static/cell_table.parquet` | CMA row/column membership | Coarse CMA mask and output coverage mask |
| `data/features/predictions/labels_nov2015.parquet` | 12 Nov and 24 Nov mapped labels and eligibility | Spatial-block training-fold calibration and label prevalence |
| `data/processed/alignment/spatial_blocks.tif` | Fixed 3 km spatial blocks | Fold assignment and 3 km train/test buffer |
| `docs/RAIN_SOURCES_COMPARISON.md` | Daily CMA mean IMERG totals | 72 UTC-hour event rainfall sequences |
| `data/features/weather/era5_event_hourly_features.csv` | Nine-point hourly temporal shape, grouped in UTC | Hourly rainfall shape scaled to IMERG daily totals |
| `data/raw/historical_floods/2015/global_flood_database/DFO_4309_From_20151110_to_20151204.zip` | Read-only coarse event cross-check | `validation_summary_selected_model.json` |
| `data/raw/historical_floods/2015/opencity_flood_points/*.kml` | Approximate, undated spatial point cross-check | `validation_summary_selected_model.json` |

The process writes only below `data/features/simulation/batch2_v1/` and does not create or alter raw data. Per-member arrays are in the matching `member_peak_depth_...DERIVED.npz`; aggregate depth rasters are tagged `DERIVED_ASSUMPTION_BASED_PILOT` and use −9999 for unassessed cells.
