# Phase 10 risk display — CR-004

The final Phase 10 composite is data/features/predictions/phase10_cr004_v9/radar_visible_plus_physical_composite.tif (three bands):

1. Apparent radar-visible risk class, values 1–4, only where the radar observability mask is true. Display cut-points are probability 0.10, 0.25 and 0.50.
2. A separate physical susceptibility score outside radar observability, formed from available percentile-rank values for HAND, local depression depth, TWI and named-waterway distance (distance inverted). It is not fitted to flood labels and is not a probability.
3. unreliable_from_labels: 1 outside radar observability and 0 inside; NoData outside the CMA.

The data-driven score is never extrapolated into masked urban, steep, missing-slope, or invalid radar areas. The PHYSICAL score appears there with the unreliable flag. Probability mean and apparent p05/p95 rasters are separate in data/features/predictions/phase9c_addendum_cr004_v6/. No out-of-event or field validation is claimed; out-of-event validation is pending digitised maps.
