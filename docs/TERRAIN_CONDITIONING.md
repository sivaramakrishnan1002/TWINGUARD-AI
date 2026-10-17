# Terrain conditioning — Phase 4 Part 1

New outputs are under `data/processed/terrain_cleaned/`. Existing terrain layers and raw inputs were not altered.

## Masks and conditioning

Masked CMA elevation cells below −5 m: **255** (0.2295 km²).
WorldCover class-80 cells: 536,536 across the full master-grid context; rasterized OSM water polygons/lines: 181,305 across that context. Their combined context-grid footprint is 586.874 km²; after preserving named target channels for burn-in, 583.509 km² is masked. Within the CMA specifically, **143,465 water-masked cells** remain after separating the 255 below−5 m cells, equal to about **129.1185 km²** at 30 m per cell.
Water area is a 30 m cell-footprint estimate, not a surveyed shoreline area. The local OSM extract provides mapped waterways and closed water-tagged ways; incomplete relation multipolygons or unnamed/unmapped water are not guaranteed represented. Target channel centerlines are explicitly restored from the water mask so they can be burned.
Priority-Flood depression filling modified 339,532 cells; maximum fill depth 12.901 m; mean positive fill depth 0.515 m.
The exact-match channel lines were burned by **2.0 m** below the filled surface. This is a modeling assumption, not a locally calibrated channel depth. Named channels: Adyar River: 5 segments, 49.824 km; Cooum: 1 segments, 43.920 km; Kosasthalaiyar River: 4 segments, 38.617 km; Buckingham Canal: 7 segments, 56.210 km.

GLO-30 is a digital surface model (DSM): it includes returns from buildings and trees, not just bare earth. The source terrain was horizontally reprojected to the master grid; no vertical datum conversion was applied in this conditioning step. The fill and burn assumptions cannot remove DSM surface artifacts.

## Differences from existing terrain layers

Comparisons use cells valid in both old and new rasters; the largest-difference coordinates are in EPSG:32644 metres.

| Layer | Difference summary | Largest difference location (E, N) m |
|---|---|---|
| slope_deg | n=1,762,770; mean Δ=3.214; MAE=3.577; RMSE=17.24; P95 |Δ|=2.19; max |Δ|=89.76 | 390315.0, 1448355.0 |
| flow_direction_d8 | n=1,762,770; changed=519,182 (29.45%) | 390975.0, 1471545.0 |
| flow_accumulation_cells_d8 | n=1,762,770; mean Δ=-0.586; MAE=1.433; RMSE=6.267; P95 |Δ|=7; max |Δ|=707 | 401115.0, 1458465.0 |
| twi_d8_proxy | n=1,762,770; mean Δ=-0.1876; MAE=0.6428; RMSE=1.853; P95 |Δ|=2.53; max |Δ|=15.5 | 410925.0, 1431915.0 |

Slope is in degrees, D8 direction codes use the same eight-neighbor ordering as the Phase 3 implementation, accumulation is upstream-cell count, and TWI uses the existing project proxy equation. D8 ties remain sinks; masked water creates hydrologic outlets. The TWI is a proxy, not a calibrated wetness product.

## Mask-edge derivative safeguard

The initial slope/TWI calculation used finite values immediately beside masked cells, where a gradient can be contaminated by the NODATA sentinel. To preserve the first outputs and obey the no-overwrite rule, three additional rasters were written under new names: `slope_deg_edge_safe.tif`, `twi_d8_proxy_edge_safe.tif`, and `depression_fill_depth_m_valid_only.tif`. The edge-safe slope/TWI set a one-cell neighborhood next to NODATA to NODATA (97,902 valid-context cells excluded); this leaves 1,664,868 context cells and 1,103,993 CMA cells with safe derivatives. The valid-only fill-depth copy marks the same masked cells as NODATA instead of zero. Against the original Phase 3 layers on common CMA-valid cells, edge-safe slope has mean Δ −0.228°, MAE 0.247°, RMSE 0.585°, P95 |Δ| 1.299°, max |Δ| 11.818° at (420135, 1443705) m; edge-safe TWI has mean Δ 0.181, MAE 0.341, RMSE 0.686, P95 |Δ| 1.671, max |Δ| 7.514 at (418515, 1466715) m. Use these edge-safe products when derivatives are needed near masked water boundaries; the original newly written files remain as provenance and are not overwritten.

## Assumptions and validation notes

The less-than −5 m mask applies only within the CMA; the DSM outside the CMA remains available for context and routing. WorldCover class 80 is used as the 30 m permanent-water proxy. OSM water polygons and lines are rasterized by all-touched 30 m cells, which can over/understate true water width. The four exact-match target channels are restored from the combined water mask and burned by 2 m. This explicit exception is needed to meet both water masking and stream burning objectives.
No terrain values were corrected manually. The previously found source minimum (about −64.51 m) was masked inside the CMA by the requested cutoff. Depressions were filled from the perimeter and valid-mask boundaries with Priority-Flood; this treats mask boundaries as outlets. No existing terrain file was overwritten.
