# Batch 2 Lane A progress

| Task | Status | Commit | Notes |
|---|---|---|---|
| S0 Spec loading and dependency reconciliation | done | — | Specs/dependencies registered; protocol checks pending. |
| A04c / S1 Urban physical layer | done_with_caveats | e357478 | 1,175,660 CMA cells scored; 927 points scored; OpenCity points are undated/approximate. |
| A03d / S2 GeoPDF labels and 2023 out-of-event evaluation | done_with_caveats | b55ccb3 | 2023 WGS84 GeoPDF red class extracted/polygonised; preliminary only because exact OSM control-point RMS is not available. 2021 UTM45/GPTS CRS conflict is manual-needed; Dec 2015 maps absent. |
| A04d / S3 Calibrated SAR labels | done_with_caveats | ee3f631 | Pooled buffered OOF IoU 0.5977 permits a Tier C map-reproduction candidate only. VV-only slightly outperforms full features. The same-scene UNOSAT comparison may be circular; applied outputs are Tier D. v2 enforces eligibility; v1 preserved but superseded. |
| A06 / S4 2D simulation | done_with_caveats | 64e20cc | 600 m NumPy local-inertial pilot; 20 members × 2 events, 68.03 s; maximum mass error 0.264%. Selected-member buffered block CV and calibrated metrics are in `PHASE12_SIMULATION.md`. GFD overlap is weak; OpenCity dates unclear; no hydraulic-accuracy claim. |
| A05 / Forecast and hindcast wrapper | done_with_caveats | 5001ab4 | 15 event/scenario combinations × 20 A06 members; 225 600 m horizon rasters and member ensembles. Perfect-foresight, ERA5–IMERG difference and persistence are scenario contrasts only; no archived NWP or observed lead-time depth validation. CPU, 687.71 s; max mass error 0.591%; 5 focused tests passed. See `PHASE11_FORECAST_BATCH2.md`. |
| A07 / Impact | done_with_caveats | eaa484c | Versioned impact output `data/features/impact/batch2_v4_contract/`: 75 event/scenario/horizon records; 4,500 member-threshold records; 405,601/566,307 road segments midpoint-assessed; population NoData retained. Default 0.30 m with 0.15/0.50 m sensitivity. Facility cascade is a coarse 600 m component proxy. Hindcasts/simulations only, not live impact or routing truth. Lane A C7 shape is task-approved only; API/UI mismatch remains for integrator. See `PHASE13_IMPACT_BATCH2_V4.md`. |
| A08 / Time-dependent graph | done_with_caveats | 5966dee | 1,500 compact 600 m member/time snapshots across 15 event/scenario cases; 508,854 nodes, 566,307 segments, 1,071,656 directed arcs. 768,688 arcs mapped to A07 cells; 302,968 unassessed/ambiguous. Ordinary 0.30 m, tunnel-proxy 0.15 m, bridges unassessed; speed factors are assumptions. 105 Lane A tests passed; raw audit 157/157. Simulated overlay only, no safe/operational routes. See `ROUTING_GRAPH_BATCH2.md`. |
| A09 / Routing | done_with_caveats | b9b6ea4 | 216 versioned route results across 3 event windows, 3 snapshots and 6 graph-node OD probes; 19 forecast members vs hidden simulated member 20. Only 18/54 current and horizon paths and 15/54 uncertainty paths exist on assessed arcs; all 54 static paths have incomplete hazard coverage. Not live or validated guidance. See `ROUTING_BATCH2.md`. |
| A10 / Shelter allocation | done_with_caveats | d0f4343 | 540 simulated cases; 293,374 allocation rows. Final corrected output is batch2_v3; v1/v2 preserved. 3 focused and 113 Lane A tests passed; raw audit 157/157. Candidate capacities are assumptions; weak components are not routing. |
| A11 / Priority zones | blocked | — | Depends on A07 and A10. |
| A12 / Explainability | done_with_caveats | 46d325d | Grouped permutation importance and marginal PDP on a held-out spatial fold for the Phase 9C default RF; single-event SAR label is not independent validation. Summarized existing 20-member simulation sensitivity per event; no simulation rerun. See `EXPLAINABILITY_BATCH2.md`; CPU only because CUDA was unavailable. |
| A13 / Decision lab | blocked | — | Depends on A05, A09, A10, A11 and A12. |
| A14 / Phases 19-21 experiments | done_with_caveats | 6cd52f9 | H1 not testable: accepted flood labels cover only the Nov 2015 episode; no independent held-out event labels. Feasibility/config only, no model fit or metrics; 3 focused tests passed and raw audit 157/157. |
| A15 / Phase 25 validation | done_with_caveats | 6212004 | A05/A06/A09 outputs and limitations rechecked; 116 Lane A tests, route verifier and raw audit pass. No external flood-depth or route truth; TIFF unit metadata gap documented. |
| A18 / C1 T6 metadata conformance | done_with_caveats | 2ed3abc | Six tagged copies preserve original pixel arrays and masks; acquisition time remains unknown/null. Four focused tests and 21 Phase 8 tests passed; raw audit 157/157. Does not freeze C1 or authorize routing. See `DEPTH_METADATA_REPAIR.md`. |
| A19 / C2 accepted-label GeoJSON export | done_with_caveats | e4b6024 | Read-only export of the 10,419-row accepted view; 8,414 event-flood and 2,005 baseline-water features, zero rejected rows. 16 label tests passed; raw audit 157/157. Exact hashes/counts in `LABEL_GEOJSON_EXPORT.md`; no DB writes. |
| A20 / 3D scenario data readiness | done_with_caveats | f0124f8 | Indexed 45 saved A05 raster references and four A06 context groups; exact saved times, 600 m grid and NoData preserved. Regional presentation only; no street-scale, hydraulic-validation, operational-forecast, or safety claim. 121 Lane A tests passed; raw audit 157/157. See `FLOOD_3D_SCENARIO_READINESS.md`. |
| A17 / Paper and project report | done_with_caveats | e57847d | Wrote cited internal drafts `PAPER_DRAFT.md` and `FINAL_REPORT.md`; source evidence through A15, A20 described only as raster indexing. Drafts preserve blockers, unknowns, and model limits; 121 Lane A tests passed and raw audit 157/157. Awaiting authorized review. |

## Defaults and scope notes

- WorldPop NoData remains a missing-exposure flag; never use it to censor hazard eligibility.
- The urban physical layer is not fitted to flood labels.
- Physical simulation output is a calibration proxy, not hydraulic truth.
- New work preserves all previous model, label and map artifacts.

