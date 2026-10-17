# Routing profile — Phase 4 Part 1

This is a planning and baseline profile. The graph uses assumed default speeds when maxspeed is absent; it does not include flood closures.

## Graph definition

Included highway classes: living_street, motorway, motorway_link, primary, primary_link, residential, road, secondary, secondary_link, service, tertiary, tertiary_link, trunk, trunk_link, unclassified.
Excluded highway classes present in the source: cycleway, footway, path, pedestrian, steps and track. No other excluded highway value occurred in the source. `access=no` and `access=private` were excluded (84,784 source segments); `bridleway` was not present.
Default speed assumptions (km/h): {"living_street": 15, "motorway": 100, "motorway_link": 50, "primary": 50, "primary_link": 40, "residential": 25, "road": 25, "secondary": 40, "secondary_link": 30, "service": 15, "tertiary": 30, "tertiary_link": 25, "trunk": 80, "trunk_link": 40, "unclassified": 25}. Missing or unparsable maxspeed uses these assumptions.

Per edge fields include length, travel time, bridge/tunnel flags and cleaned-DEM minimum/mean/maximum sampled at vertices and <=30 m intervals.

## Facilities and routing

Snapped facilities: {"hospital": 848, "shelter": 174, "candidate_shelter": 909}. Facilities within 500 m of a road node: {"hospital": 848, "shelter": 174, "candidate_shelter": 909}.
Snap distance summaries (m): {"candidate_shelter": {"max": 143.54826240738464, "median": 33.77466958941277, "min": 0.6459785858814651, "p90": 65.26386188224099}, "hospital": {"max": 114.04204072932721, "median": 23.00116392423215, "min": 1.2360228213434297, "p90": 43.12544515145951}, "shelter": {"max": 136.56362632387427, "median": 10.202590833156048, "min": 2.1448485107250232, "p90": 47.35329123890754}}.
200-origin hospital routes: median **3.16 min**, 90th percentile **7.15 min** among 159 reachable origins; 41 had no directed path to a snapped hospital. **79.5%** of all sampled origins reached a hospital within 30 minutes.
200-origin shelter routes: median **6.36 min**, 90th percentile **11.28 min** among 159 reachable origins; 41 had no directed path to a snapped OSM shelter.
Schools and colleges are reported separately as 909 candidate shelters, an assumption; they are not counted as actual shelters. For both hospitals and shelters, of the same 41 unreachable origins, **40** were in a weakly connected component with no destination, and **1** shared a weak component with a destination but had no directed path (one-way/topology). The 200 origin node IDs and reason lists are in `data/processed/routing/routing_unreachable_audit.json`.
Flood passability function is defined but not run on observed or predicted flood data. It marks an edge blocked at predicted depth >=0.3 m; that threshold is an assumption to confirm from literature.

Outputs: `data/processed/routing/vehicle_edges.gpkg`, `routing_metrics.json`, and `routing_unreachable_audit.json`.

## Unreachable-origin cause audit

The exact 200-origin node IDs and cause categories are saved in `data/processed/routing/routing_unreachable_audit.json`.

## Largest-SCC and population-weighted origin addendum

A fixed seed (42) selected 200 nodes uniformly from the largest strongly connected component (402,683 of 508,854 graph nodes; 79.14%). A second 200-draw sample weighted node selection by the existing 30 m WorldPop value within the CMA, dividing a cell's value among eligible nodes in that cell; weighted draws are with replacement. The detailed per-origin IDs, route summaries and limitations are in `data/processed/routing/routing_origin_coverage.json`. WorldPop is an alpha model estimate, not census demand, and the route times use assumed speeds without flood closures.

For these two largest-SCC-only samples, all 200 origins in each sample reached both a hospital and a shelter in the graph. Uniform sample hospital travel time median/p90 was 2.95/6.92 minutes; shelter was 6.71/12.06 minutes. Population-weighted sample hospital median/p90 was 2.03/5.90 minutes; shelter was 6.00/10.30 minutes. All 200 in each set were within 30 minutes under the assumed-speed graph. These figures are conditional on starting inside the largest SCC; they do not contradict the earlier all-graph sample, where 41 of 200 origins were unreachable. The population weights sum to 1,687,592.02 across 363,747 positive-population eligible nodes; this is a node-selection weight total over the accessible graph, not total CMA population or evacuation demand.
