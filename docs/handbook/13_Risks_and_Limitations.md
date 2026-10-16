# Risks and limitations

Likelihood and impact ratings below are qualitative **[estimate, to be agreed]** project judgments, not computed probabilities. Evidence is cited for each underlying issue. [user]

| Risk | Likelihood / impact | Why it matters | Mitigation |
|---|---|---|---|
| Flood labels miss the Dec 2015 peak | High / High [estimate] | UNOSAT ends 24 Nov; GFD ends 4 Dec; PDFs are not spatial vectors. [repo: `docs/PHASE3_LOG.md`] | Seek authoritative layers; document PDF control-point error; otherwise narrow validation and state the gap. |
| PDF-only 2021/2023 flood references | High / High [estimate] | Manual digitising introduces interpretation and georeferencing uncertainty. [repo: `docs/PHASE3_PLAN.md`] | Preserve PDFs; record map legend, control points, residuals, digitiser and confidence. |
| Sparse event count | High / High [estimate] | Only three target event years are in project scope. [user] | Use event-separated evaluation; avoid claims of broad generalisation. |
| Coarse rainfall support and unit issues | Medium / High [estimate] | Nine points and coarse reanalysis may miss local extremes; NASA POWER units need verification. [repo: `docs/FEATURE_DICTIONARY.md`, `docs/MANUAL_TODO.md`] | Compare sources, inspect metadata, add gauge/IMERG/IMD only if available and permitted. |
| Terrain DSM artefacts and unconditioned flow | High / High [estimate] | Buildings/vegetation, coastal negative values, sinks and flats can distort flow/TWI. [repo: `docs/PHASE3_LOG.md`] | Inspect, choose conditioning method, compare paths against drainage references. |
| Population is alpha and NoData uncertain | High / Medium [estimate] | WorldPop estimate is lower than believed census total; NoData is not zero and not proven unsettled. [repo: `docs/DATA_QUALITY_REPORT.md`] | Compare compatible census boundaries/years; show NoData and use relative patterns. |
| Reservoir release series absent | High / High for Track B [estimate] | Storage is not release; current capacities may not represent past capacity. [repo: `docs/PHASE3_PLAN.md`] | Seek operational records; label them unavailable; avoid claiming release-aware validation. |
| OSM incompleteness/count mismatch | Medium / High [estimate] | Tagging/mapping varies; inventory and extracted counts differ; graph connectivity unknown. [repo: `docs/OSM_COUNTS.md`, `docs/PHASE3_LOG.md`] | Reconcile extraction logic; audit components, snapping, access tags and missing assets; cite ODbL. |
| Sentinel timing/processing limits | Medium / High [estimate] | Most scenes are pre-peak; only Dec 6 2015 is within the 2015 peak window and remains raw; no post-peak 2023 scene found. [repo: `docs/SENTINEL_VERIFICATION.md`] | Use date-matched scenes only; approve and document separate processing; check licence. |
| Boundary vintage uncertainty | Medium / High [estimate] | Older CMA may differ from current administrative area. [repo: `docs/GRID_DECISION.md`] | Confirm scope before final features and compare boundary versions if needed. |
| Licence/attribution mismatch | Medium / High [estimate] | Sources have different permissions; some terms are not found; GFD is non-commercial and OSM uses ODbL. [repo: `docs/DATA_MANIFEST.csv`] | Maintain source-specific notices; get permission where needed; review reuse before distribution. |
| Tool availability | Medium / Medium [estimate] | NetworkX, SNAP, pyroSAR, GDAL CLI/bindings and Parquet engines were unavailable in recorded venv. [repo: `docs/PHASE3_LOG.md`] | Re-check environment; install only approved dependencies into project venv; record versions. |
| Time and scope pressure | Unknown / High [estimate] | Team deadlines and staffing are unknown. [unverified: no deadline or role list in repo] | Prioritise reliable labels, baseline, evaluation and documented uncertainty; cut optional models first. |
| Decision-support misuse | Medium / High [estimate] | A prototype could be mistaken for an official safe-route or evacuation command. [user] | Label prototype clearly; show freshness, confidence, limits and human authority; do not deploy without validation and governance. |

## Interpretation limits

WorldCover class 50 is only a built-up proxy; OSM building polygons are incomplete and do not imply occupancy; proximity buffers are not network service areas; GFD overlap is broad regional evidence; UNOSAT inspection rasters are not final training labels; and Track B is not a validated warning model. [repo: `docs/FEATURE_DICTIONARY.md`, `docs/PHASE3_LOG.md`]
