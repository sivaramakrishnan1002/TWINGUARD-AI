# Phase 9C out-of-event check: 2023 map

This is a **preliminary map cross-check**, not independent validated event accuracy. The Phase 9C model was trained on a November 2015 SAR-derived label; the Dec 2023 NRSC GeoPDF is a different event, but the legend includes both flooding and standing/rain water and the map says no ground verification. GeoPDF provides a WGS84 viewport, but no OSM control-point RMS was available; therefore no tier B/C label was loaded.

| Comparison domain | n cells | map-positive cells | prevalence | PR-AUC (lift) | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| 2015 Phase 9C radar-observable cells | 574018 | 25160 | 0.043831 | 0.121055 (lift 2.76) | 0.778127 |
| New A04c physical score, full covered CMA | 1175660 | 30312 | 0.025783 | 0.028158 (lift 1.09) | 0.574700 |

Map-positive area in CMA after nearest-neighbour resampling to the 30 m analysis grid is about **28.81 km²**; this number is map-scale approximate, not a precise inundation area. The comparisons are documented as descriptive cross-checks only. The map class is not accepted as validation truth because it can include standing paddy/rain water, has no field verification, and lacks independently measured control-point residuals.
