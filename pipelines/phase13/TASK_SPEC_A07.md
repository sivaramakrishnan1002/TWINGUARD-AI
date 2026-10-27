# A07 task notes — Phase 13 ensemble impact analysis

**Task:** A07, claimed through `tools/master/claim.py` on 2026-10-27.

## Acceptance

- Estimate road-edge passability from each saved A05 event/scenario/horizon ensemble, using 0.30 m as the default assumed blocking threshold and sensitivity at 0.15–0.50 m.
- Keep population NoData unknown and report exposure distributions, mapped facility exposure, and hospital/shelter access cascades.
- Write only new, versioned products under `data/features/impact/`; retain prior products.
- The first run wrote `batch2_v1`. Review found its coverage status did not carry all source geometry outside the solver footprint; preserve it unchanged, and write the corrected coverage version to `batch2_v2_coverage/`.

## Inputs and interpretation

- A05 `depth_members_by_horizon_DERIVED.npz` files, their summary, and the A06 grid returned by `pipelines.phase12.simulate.load_static()` (600 m, EPSG:32644).
- Existing static `cell_table.parquet` for CMA-limited WorldPop values and its explicit NoData flag; this avoids summing whole 600 m cells outside the CMA.
- Existing OSM road segments and facilities from `data/features/osm/chennai_osm_features.gpkg`.
- Use road segment midpoint depth as the 600 m grid exposure sample. The resulting edge passability is a coarse proxy; it cannot resolve street-scale water or the entire length of a road segment.
- For access cascades, collapse road endpoint connectivity onto 600 m cells. A facility is connected if its coarse-cell component remains connected to the largest pre-event road component. This is a network-connectivity proxy, not OD travel routing, facility operation, shelter allocation, or safe access.
- Use 0.15, 0.30, and 0.50 m as three fixed sensitivity points spanning the requested range. Apply each as a modeled flood-depth screen to roads and mapped facilities; these are assumptions, not empirically validated impact thresholds.
- Write local JSON/Parquet using the Lane A C7 proposal (`impact-result-v0.1-draft`) only. G0 is not ready, so this proposal is not approved or frozen and no API/database contract is changed.

## Reproducibility and limits

- Fixed inputs and file hashes are recorded in the run summary. No random sampling is used.
- NoData in depth, population, or graph coverage remains explicitly unassessed; it is never treated as dry, zero population, or passable.
- All A05 states are DERIVED hindcast/scenario simulations, not live forecasts or validated hydraulic truth. Facility “access” is only the coarse connected-component cascade described above.
- Run with `.venv/Scripts/python.exe -m pipelines.phase13.impact`; the program refuses to overwrite a nonempty output directory or an existing report.
