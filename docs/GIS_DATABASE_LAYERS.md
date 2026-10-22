# Stage 6 — queryable GIS layers

The loader reads source files only; it does not rewrite them. It uses the existing provisional older-CMA boundary and imports selected vector layers into schema `twinguard`, reprojection to EPSG:32644 where needed. Layer counts are after source-layer selection; the four UNOSAT layers are spatially filtered to features intersecting the provisional CMA boundary, while geometries themselves are preserved and may extend beyond it.

| PostGIS table | Source | Rows | Geometry / CRS | Notes |
|---|---|---:|---|---|
| `study_area` | `data/raw/boundary/chennai_cma_boundary.geojson` | 1 | MultiPolygon / 32644 | Older CMA boundary; vintage remains unconfirmed. |
| `road_edges` | `data/processed/routing/vehicle_edges.gpkg`, `vehicle_edges` | 455,285 | LineString / 32644 | Filtered vehicle graph; speeds/assumptions documented in `ROUTING_PROFILE.md`. |
| `facilities` | `data/features/facilities/chennai_facilities.gpkg`, `facilities` | 15,413 | Point / 32644 | OSM-derived facilities; 15,162 fall inside the boundary. |
| `waterways` | `data/features/hydrology/chennai_waterways.gpkg`, `waterways` | 759 | LineString / 32644 | 687 intersect the boundary. |
| `flood_references` | `FL20151123IND_shp.zip`: four named UNOSAT vector layers | 10,419 | Geometry / 32644 | 1 Sep (1,360) and 14 Oct (645) are baseline-water references; 12 Nov (4,704) and 24 Nov (3,710) are event layers. These do not label the 1–8 Dec 2015 peak. |

The original flood geometries include **235 invalid geometries**. They were retained without automatic repair so their imported geometry remains faithful to the vector source. The other four tables have zero invalid geometries. The vector-tile functions succeeded for a Chennai z=12 test tile even with these source geometries; a map client should still treat the invalid-feature count as a data-quality warning.

### Read-only invalid-geometry reason review — 2026-10-22

The reasons were grouped from PostGIS `ST_IsValidReason` on the imported features; no geometry was altered:

| Source layer | Count | Reported reason |
|---|---:|---|
| `LS8_20151014_PreFlood` | 50 | Ring Self-intersection |
| `S1_20150901_PreFlood` | 31 | Ring Self-intersection |
| `S1_20151112_Flood` | 34 | Ring Self-intersection |
| `S1_20151124_Flood` | 119 | Ring Self-intersection |
| `S1_20151124_Flood` | 1 | Interior is disconnected |

Thus 234 invalid features report ring self-intersections and one reports a disconnected interior. These reasons identify geometry validity problems, not their cause or the correct scientific repair. Preserve the raw source; if valid geometries are required later, test a documented repair or exclusion on a new derived copy and compare area/feature counts.

## Views and vector tiles

The migration provides `v_study_area`, `v_roads`, `v_facilities`, `v_waterways` and `v_flood_references`. The corresponding callable functions are `mvt_study_area(z,x,y)`, `mvt_roads(z,x,y)`, `mvt_facilities(z,x,y)`, `mvt_waterways(z,x,y)` and `mvt_flood_references(z,x,y)`. Each returns an MVT payload as `bytea` in Web Mercator. A smoke check at z=12, x=2960, y=1898 returned respectively 173, 2,175,224, 146,030, 5,162 and 20,668 bytes.

The tile functions are database primitives, not an HTTP tile endpoint. There is no frontend/viewer in this stage. Roads/features outside the CMA that are in the source context remain in tables; spatial query results are available through the views and indexes.

## Provenance and limits

- OSM-derived data retain an ODbL attribution/share-alike note in `dataset_catalog`; the project’s existing attribution records remain authoritative.
- UNOSAT terms were not independently confirmed, so catalog entries say so rather than asserting a licence.
- The older CMA boundary is provisional. The layer catalog preserves each source file hash to identify the imported version.
- NRSC/NDEM PDF maps were not digitized or loaded; no Sentinel scenes or rasters were loaded. See `LABEL_STRATEGY.md` for label timing and scope.
- Run `python pipelines/stage6/load_gis_layers.py` to load. Matching source hashes are skipped; changed sources or uncatalogued pre-existing target rows are refused. Run `python pipelines/stage6/verify_gis.py` for read-only row, CRS, geometry, provenance, view and tile checks.
