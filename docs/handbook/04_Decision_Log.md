# Decision log

<!-- B55 refresh -->
## Final-year decisions (November 2026)

These are the binding owner decisions for the final product. They are recorded by the Integrator in `docs/master/FINAL_YEAR_OWNER_DECISIONS.md` and implemented under the change requests below. The October entries further down are kept as history; where they conflict, the decisions below win. [repo]

| ID | Decision | Implemented by |
|---|---|---|
| **OD-2026-11-07** | A bachelor's final-year product rebaseline. 7 tabs in a dark control-room style. 3D city with CesiumJS and Google Photorealistic 3D Tiles; the key stays in git-ignored `.env.local` and the API never returns or accepts it. Relaxed caveat policy (one DEMO/SIMULATION badge; `done_with_caveats` counts as done). Still binding: no fabricated value shown as observed, a `source_mode` on every result, resources as `SCENARIO_INPUT`, incidents labelled generated. On-demand Open-Meteo with caching and a 600 s minimum interval. **Novelty claim in the owner's wording** (see [Project on a Page](00_Project_on_a_Page.md)). | CR-019; A25, B47, B48 |
| **OD-2026-11-08** | Use the GPU whenever it helps (RTX 3050 Laptop, 4 GB). CPU must remain a supported fallback, and every GPU path falls back cleanly. One GPU job at a time. | A26 (CUDA backend); B47 device option |
| **OD-2026-11-08b** | Revised G5: the product-pipeline end-to-end check (archived input → engine → `/v3` → packaged UI). The CR-012 POONDI replay is kept as an optional secondary check. | CR-020; B13, B50 |
| **OD-2026-11-08c** | Keep a persistent engine worker warm (`TWINGUARD_V3_WORKER`), with CPU fallback. Measured 17 s warm against 31 s cold for a 48 h citywide run. | B47 (dec0abe, df96bf2) |
| **OD-2026-11-10** | Live forecast mode: a 3 h cycle with start-up catch-up, manual refresh at most once per 600 s, the last 16 live runs kept, a 5,000 calls/day Open-Meteo budget, the CFM-DSS snapshot at most daily, and reservoir coupling only through A28's labelled assumption rule. A run-dependent badge, and the permanent note "Model forecast — not an official warning". It amends the earlier no-polling rules **for live mode only**. | CR-021; A28, B51, B52, B53 |

| Change request | Subject |
|---|---|
| **CR-019** | Product rebaseline of the UI and API: C4 v3 `/v3` contract, ownership and task split (A25, B47, B48) |
| **CR-020** | G5 as the product-pipeline replay (B13 acceptance, packaged UI evidence) |
| **CR-021** | Live forecast mode (`/v3/live/*`, `run_kind`, `live` block, Overview badge, CR-016/017/018 amendments) |

---

This table separates recorded repository decisions from the user's planning-chat decisions. Dates are stated only where a repository record supports them. “Options” are included only when recorded; otherwise the entry says they were not recorded. [repo: sources in table; user]

| ID | Decision | Alternatives considered / reason | Decision owner and date | Impact |
|---|---|---|---|---|
| D01 | Use the older pre-2022 CMA boundary provisionally. | User context: dense core, existing event fit and data density; expanded area would change scope. Must confirm final jurisdiction. | User; date not recorded. [user; repo: `docs/GRID_DECISION.md`] | Current raster and summaries cover the old boundary. |
| D02 | Use two tracks: slower multimodal Track A and rapid Track B. | Satellite revisit is too slow to serve as the sole fast alert. | User; date not recorded. [user] | Separate forecast and alert hypotheses. |
| D03 | Treat reservoir observations as Tier 1. | Reservoir operations may affect flood decisions; available series are storage-only, not release records. | User; date not recorded. [user; repo: `docs/PHASE3_PLAN.md`] | Keep storage analysis modest; seek missing releases manually. |
| D04 | Tide/surge and estimated soil moisture are stretch items. | Add only if time/data allow. | User; date not recorded. [user] | Do not block core project on them. |
| D05 | Glacial/geological floods are out of scope. | Chennai project concerns urban rainfall and reservoir-linked flooding; Nepal comparison is excluded. | User; date not recorded. [user] | Keep event and hazard framing local. |
| D06 | Local PostgreSQL/PostGIS first; Docker later. | Avoid a port 5432 conflict and keep the database choice aligned with Compose. | User; date not recorded. [user; repo: `docker-compose.yml`] | Compose exists but remains stopped. |
| D07 | Download data manually; Codex verifies and documents. | User performs logins and browser downloads; avoid credential sharing and unattended login. | User; date not recorded. [user] | Manual collection and manual TODOs remain. |
| D08 | Use NASA ASF Vertex after Copernicus Data Space login failed. | Copernicus sign-in was not working in the user’s browser; ASF provided Sentinel search/download. | User; date not recorded; acquisition records dated 2026-10-14. [user; repo: `docs/SENTINEL_VERIFICATION.md`] | ASF licence terms still need checking. |
| D09 | Keep `data/raw` immutable. | Raw originals are source evidence. | User; repeated; audit date 2026-10-14. [user; repo: `docs/PHASE3_LOG.md`] | Derived products go under processed/features; no raw edits. |
| D10 | Preserve the misspelled `senitnel1` path in manifest references. | Correcting a raw path would violate the no-rename rule. The actual on-disk folder is `sentinel1`; manifest uses `senitnel1` in rows, creating a conflict to resolve without moving files. | User; date not recorded. [user; repo: `docs/PHASE3_LOG.md`, `docs/DATA_MANIFEST.csv`] | Verify path discrepancy before any path-dependent automation. |
| D11 | Use Global Flood Database event 4309 only as a broad cross-check. | Coarse MODIS event centroid is outside CMA; event is not local truth. | Assistant-recommended/documented; user approval date not recorded. [repo: `docs/PHASE3_LOG.md`] | Do not use it as a definitive Chennai label. |
| D12 | Use WorldPop for relative patterns, not absolute headcount. | R2025A is alpha and constrained; total appears below believed census figure; nodata meaning is uncertain. | User-approved caveat; date not recorded. [repo: `docs/DATA_QUALITY_REPORT.md`] | Mark population outputs as model estimates. |
| D13 | Do not treat storage change as reservoir release. | No complete release series was collected. | User/project rule; date not recorded. [user; repo: `docs/PHASE3_PLAN.md`] | Track B remains storage/rainfall only. |
| D14 | Defer emails and records requests to the user. | User said they cannot send emails/RTI through Codex and will handle manually. | User; date not recorded. [user] | NRSC December 2015 and TN WRD records remain open. |
| D15 | Work on a 30 m EPSG:32644 common grid. | A 30 m compromise aligns with the terrain source; earlier 10 m was only a plan and would overstate detail from coarse inputs. | Recorded 2026-10-14. [repo: `docs/GRID_DECISION.md`] | All checked outputs align; does not improve native source detail. |
| D16 | Keep Sep/Oct 2015 water layers as a baseline idea, not an automatic subtraction. | PreFlood classes include possible wet soil and static water; verify before use. | Recorded 2026-10-14. [repo: `docs/PHASE3_PLAN.md`] | Subtraction output is test-only. |
| D17 | Exclude invalid polygons individually rather than unioning invalid KMLs. | Union operation failed on invalid geometry; per-feature handling let inventory complete. | Pipeline correction dated 2026-10-14. [repo: `docs/PHASE3_LOG.md`] | OpenCity KML inventory is not a single dissolved flood mask. |
| D18 | Preserve the five existing tiled label GeoTIFFs without rewriting for COG layout. | Validator found no COG layout; no-overwrite rule preserved files. | 2026-10-14. [repo: `docs/PHASE3_VALIDATION.json`, `docs/PHASE3_LOG.md`] | They remain valid aligned rasters with a performance/layout warning. |
| D19 | No model training or Phase 4 in this pass. | Current deliverable was feature preparation and validation. | User-approved status; 2026-10-14. [repo: `docs/PHASE3_LOG.md`] | Model and application work remain future phases. |

## Decisions still needed

Confirm the final boundary, label strategy, hydrological conditioning, release-data plan, and Sentinel reuse terms. These choices affect final model scope and validation. [repo: `docs/MANUAL_TODO.md`]
