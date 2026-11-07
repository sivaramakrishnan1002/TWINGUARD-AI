# Phase 3 — Flood event explorer

## Implemented controls

- Added a documented-window selector for the three planned event-input periods in `docs/TWIN_MODEL.md` / `docs/TIME_ALIGNMENT.md` and the Track B offline alert-candidate replay dates in `docs/trackb/RUNBOOK.md`.
- Planned windows are explicitly marked `PLANNED` and described as historical input periods, not flood-onset dates. The Track B item is marked `REPLAY` and says its candidate messages are not validated flood outcomes.
- Selecting a window updates its status, date range, time basis, source-document provenance, and limitations. It does not load data or fabricate a current valid time, run ID, or version.
- Added event-layer controls and legend slots for flood extent, depth (metres per the documented 2015 output convention), risk class, uncertainty, and NoData. Every layer is visibly `UNAVAILABLE` and disabled.
- Added distinct text-and-style definitions for `REPLAY`, `LIVE`, `SIMULATED`, `DERIVED`, `ASSUMPTION`, and `PLACEHOLDER`.
- Timeline previous/next/play controls remain disabled. Selecting a window shows its documented dates, but no progress marker or timestamp because there is no time-indexed UI feed.
- The NoData legend says coverage is transparent and missing coverage means unknown, not dry. No depth values, risk scores, uncertainty bands, or raster layers are displayed.
- MapLibre shows a brief local-renderer initialization state before its empty-style map is ready; this does not imply data is loading.
- The Phase 2 neutral MapLibre style and 2D fallback remain unchanged.

## Source availability

- The documented event calendar in `docs/TWIN_MODEL.md` has planned windows: 1 Nov–15 Dec 2015, 1–20 Nov 2021, and 25 Nov–15 Dec 2023 (Asia/Kolkata). They are planned input-replay windows, not verified flood-onset dates.
- `docs/trackb/RUNBOOK.md` documents an offline 20 Nov–4 Dec 2015 replay with 50 alert candidates. It is not a UI feed, and its candidates are not validated flood outcomes.
- `docs/T6_DEPTH_OUTPUTS.json` documents DERIVED, assumption-based 2015 depth products for 12 and 24 Nov, in metres on the 30 m EPSG:32644 grid. The depth contract reports only about 30–32% coverage of the mapped extents and an uncalibrated ±4 m assumption. These rasters are not rendered or read by the UI.
- API contracts remain design-only. No verified event catalogue, time-series, flood-layer, or HTTP map-tile endpoint is documented. PostgreSQL MVT functions are not browser-accessible HTTP endpoints.

## Checks and limits

- No dependencies were installed or changed in this phase; no network access was used.
- `npm run build` passes. Vite retains the documented advisory: the main JavaScript bundle is about 1.23 MB (about 345 KB gzip), above its 500 kB warning threshold.
- The production preview was manually checked: the 2015 Track B replay and a planned 2023 window were selected; labels, date windows, provenance, unavailable layer controls, NoData messaging, and disabled timeline controls were verified. The 2D/3D toggle and return to 2D were also checked.
- The map remains an empty style. No event-data rendering, playback, or flood interpretation has been verified.
- No event/layer API request is made while sources are absent. Event-data loading will belong to a future adapter request lifecycle; the current unavailable-source and no-data states stay visible without implying a request is in progress.
- Existing three moderate Tailwind 3/PostCSS dependency advisories remain documented in `PHASE2_STATUS.md`; no forced fix or Tailwind upgrade was performed.
