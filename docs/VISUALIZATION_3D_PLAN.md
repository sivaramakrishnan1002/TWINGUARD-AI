# 3D command-centre visualization plan

## Principle

Flood calculation, validation and uncertainty stay in 2D or 2.5D raster/network space. A 3D view is a rendering of those results; it does not add physical accuracy or replace the model grid.

## Layers and data flow

1. Use the existing cleaned DEM as the elevation source. Build local terrain tiles from `data/processed/terrain_cleaned/` after confirming the exact cleaned output and vertical datum. The tile recipe and MapLibre terrain-source compatibility are **not yet verified**. Keep source rasters unchanged; tiles are derived outputs under a later approved generated-data folder.
2. Render buildings from the existing OSM footprints. Prefer a valid OSM `height` tag; otherwise estimate from `building:levels × 3 m`. If neither tag is present or valid, use a provisional **9 m default** (three assumed 3 m floors). All fallback values are visual assumptions, not surveyed heights; expose the fallback in feature properties and the legend.
3. Render event/run depth as a semi-transparent 2D raster draped over terrain, with a fixed colour scale and a separate uncertainty/confidence view. Preserve NoData transparency and distinguish unobserved areas from dry cells.
4. Draw routes as lines draped to terrain. Style edges by accessibility probability and time; do not claim a route is safe solely because its line is visible.
5. Use OSM bridge/tunnel tags to style known bridges and underpasses. These tags are incomplete; DEM sampling and line draping do not establish bridge deck or underpass clearance. Do not infer passability from terrain elevation alone.

MapLibre GL JS terrain/extrusion behaviour, local DEM tile format/encoding, browser GPU support and compatibility with the proposed data all remain **to be verified** before implementation.

## Performance budget (targets, not measurements)

- Target 30 frames/second on a named mid-range student laptop; measure on actual hardware before accepting the budget.
- Keep the viewport to a manageable zoom-dependent building set; start with simplified building polygons and level of detail, and avoid loading all 382k footprints as fully detailed extrusions at once.
- Target under 100 MB of decoded visible vector data and under 250 MB total browser memory for the minimum demo; measure and revise after a prototype.
- Use terrain tiles and flood raster tiles rather than transferring whole rasters. Request only visible tile ranges and limit concurrent tile fetches.
- Keep route/state updates separate from geometry redraw; cap update rate to the selected display interval.

## Minimum demo

Show one historical replay window with a terrain basemap, a small visible set of extruded buildings, one depth-overlay time, its uncertainty or NoData legend, and one example route styled by accessibility. Add a clear banner: **historical replay / research prototype / not an operational warning**. Include a 3D on/off control and a 2D fallback. Do not simulate live data unless every synthetic value is visibly labelled simulated.

## Main risks and decisions

- Tile creation, MapLibre terrain configuration and its performance footprint are unverified.
- OSM building heights are sparse and defaults can distort skyline/exposure impressions.
- The DEM is a surface model and contains a known extreme negative artefact; it must not be presented as surveyed ground height.
- 30 m hydrology/flood inputs cannot support building-scale inundation claims.
- Bridge/underpass geometry, road closures and vertical clearance are incomplete.
- The display must show uncertainty, source date, run/version and NoData; 3D appearance can otherwise imply unsupported precision.
