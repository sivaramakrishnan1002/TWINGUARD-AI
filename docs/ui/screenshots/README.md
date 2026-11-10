# B48 UI screenshots

Captured 2026-11-08 with headless Chrome (RTX 3050 via ANGLE) against the live C4 v3 API
(`/api/ai/v3`), run `evt-20261108T141229Z-fb36a1cd` (Dec 2015 event, 48 h, citywide 120 m, CUDA),
frame 72 (T+36 h) unless noted. Tools: `tools/ui/capture_screens.mjs`, `tools/ui/capture_photoreal.mjs`.

| File | Shows |
|---|---|
| 01–07 | The seven tabs (Situation Overview … Digital Twin 3D City) |
| 08, 09 | Citywide oblique and Velachery close-up (earlier capture, saved results) |
| 11–13 | End-to-end check: Run Simulation, What-if and Find Routes calling the API |
| 14 | Water animated by modelled `/flow` velocities (legend: "modelled velocity") |
| 15 | Experimental "Photoreal roofs" toggle, before/after, Velachery and T. Nagar |
| 16 | G5 evidence: tabs 2 and 7 with run_id, REPLAY input, SIMULATED, CUDA, `/flow`, DEMO badge, Google attribution |

## Load size (production build)

| | Main JS chunk | gzip | 3D engine |
|---|---|---|---|
| Before (704faa8) | 4,525 kB | 1,233 kB | bundled in main chunk |
| After | 270 kB | 87 kB | lazy `Twin3D` chunk, 4,268 kB / 1,151 kB gzip |

First contentful paint measured with `tools/ui/measure_load.mjs` (SwiftShader, 2 cold runs) is about
the same (2.6–3.0 s before, 2.8 s after); the UI shell no longer waits for the 3D engine. The "after" build
reaches the viewer in 0.5–0.65 s, and globe and citywide buildings in about 20 s under software rendering.

## B50: packaged UI (G5 criterion 4)

`17_g5_packaged_flood_simulation.webp` and `17_g5_packaged_digital_twin.webp` were captured on 2026-11-10 from the
**B11 nginx package at http://127.0.0.1:8081/** (not the Vite dev server) with `tools/ui/capture_g5_packaged.mjs`.
Run `evt-20261108T152128Z-59eba744` (B13 packaged run), frame 72 (T+36 h), camera at Velachery via area search.

- Stack: `docker compose -p twinguard-b11 -f docker-compose.b11.yml up -d --build --wait`, with a local override that only
  dropped ai-service's host port 8000 (Lane B's GPU service held it); nginx reaches ai-service on the compose network.
- Frontend image `local/twinguard-b11-frontend:0.1.0` = `3c815aa8cc7b` (rebuilt 2026-11-10 09:44 IST from the current UI);
  served entry bundle `assets/index-DpsSUc_K.js`, sha256 `5ce4a2d38fe62924…`; Cesium assets served from `/cesium/` (200).
- Visible: run_id, rainfall input REPLAY, results SIMULATED, compute CUDA (run provenance), water motion
  "MODELLED /flow" (`/flow?frame_index=72&stride=4` → 200), generated-incident markers (Tab 2 with the incident layer on;
  Tab 7 "Generated incidents" layer), DEMO / SIMULATION badge (header and map), Google Maps logo and credit.
- Browser console errors: **0** on both tabs. The ion token appeared in **no** `/api/ai` request (URL, headers or body);
  the bundle contains no Google `AIza` key (the 3D uses the Cesium ion token, read from git-ignored `frontend/.env.local`
  at build time and present only in the lazy Twin3D chunk; the image is local, never pushed).
- API calls seen (all GET, same origin): `/api/ai/v3/status`, `/events`, `/simulations?limit=50`, `/static/wards`,
  `/weather`, and for the run `/depth`, `/flow`, `/wards`, `/incidents`, `/shelters`, `/roads`.
- Packaged-build fix: added `frontend/.dockerignore`, so the build context no longer copies the host's Windows
  `node_modules` (and `dist`) over the Linux `npm ci` install.

## B54: packaged live UI (18_live_*)

Captured on 2026-11-10 from the **packaged stack at http://127.0.0.1:8081/** (nginx, Lane B's B53 build; frontend
rebuilt from the B52 UI). Served entry bundle `assets/index-Dg3YnI3f.js`, sha256
`898dffdeafc771c0de4ff913395f6c5d1fbdc305631eb0d34236a21463ed63e8` (no Google `AIza` key in it).

| File | What it shows |
| --- | --- |
| `18_live_overview.webp` | Situation Overview on live run `sim-20261110T153456Z-b1a4b11c` (LIVE_FORECAST, CPU, issued 15:34:50Z) |
| `18_live_flood_simulation_3d.webp` | Flood Simulation, 3D Digital Twin, same run; Run Details: CPU, MODELLED /flow |
| `18_live_flood_simulation_2d.webp` | Flood Simulation after switching to 2D Map (Google roadmap, dark-styled) |
| `18_live_digital_twin.webp` | Digital Twin (3D City) tab, same run |
| `18_live_last_error_fallback.webp` | Error-handling evidence: after B53's simulated Open-Meteo failure (12:21Z) the `last_error` banner shows, the Open-Meteo dot is red and the last good run `sim-20261110T121126Z-979f9524` stays on screen |

- Visible in the clean shots: header badge **LIVE FORECAST · 21:04 IST** and map badge LIVE FORECAST; live strip
  "Updated 21:09 IST · next 00:04" with Open-Meteo and CFM-DSS health dots (both ok, green) and the Refresh button;
  disclaimer "Model forecast — not an official warning" on every tab; reservoir outlet inflow tagged ASSUMPTION
  (SCENARIO_INPUT); Google Maps logo and credit with Cesium ion and OpenStreetMap attribution.
- The clean state came from one manual Refresh at 12:31:42Z (202 started, run `sim-20261110T123148Z-eac60710`, cleared
  `last_error`); the scheduled 15:34Z cycle then published the run shown.
- Browser console errors: **0** on all five captures. The ion token appeared in **no** `/api/ai` request.
- API calls (same origin): `GET /api/ai/v3/live/status` (polled), `/status`, `/simulations?limit=50`, `/static/wards`,
  `/weather`, and per run `/depth`, `/flow` (200), `/wards`, `/incidents`, `/shelters`, `/roads`; one
  `POST /api/ai/v3/live/refresh` (manual, before capture).
