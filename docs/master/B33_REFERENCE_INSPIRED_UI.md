# B33 — Reference-inspired flood control-room UI

**Owner:** Lane B. **Status:** ready/unclaimed at registration. **Classification:** product UI refinement with local DEMO/SIMULATED fixtures.

## Goal

Use the project-owner's two generated interface images as visual direction for a premium flood operations workspace: compact branded header, seven clear product sections, a dominant city-twin canvas, and focused supporting panels. Preserve the current product behavior while making the overview and 3D Twin feel like a polished application rather than a prototype wireframe.

## Inputs

- B29–B32 product UI and evidence.
- Existing local adapter and synthetic fixture semantics.
- B18 exact saved-raster explorer and A20 evidence limits, as source context only. Do not imply the generated scene is the raster result.
- The two user-provided reference images for composition and visual tone only.

## Owned outputs

- `frontend/src/ui/product/ProductExperience.tsx`
- `frontend/src/ui/product/product.css`
- `frontend/src/ui/product/assets/flood-city-concept-v1.webp`
- `docs/ui/REFERENCE_INSPIRED_CONTROL_ROOM.md`

## Product direction

Use a refined horizontal navigation/header inspired by the reference, with scenario/source/time and demo status kept clear. The Situation Overview should feel like a control-room dashboard: compact synthetic snapshot and event context, a large spatial/3D centerpiece, a focused simulation-control panel, and concise lower panels for reservoirs, impact, response, and what-if. The 3D Flood Twin should make the city scene the main focus and keep its time/view controls immediately accessible. Keep the remaining sections task-specific rather than duplicating dashboard cards.

Use locally authored UI plus one bundled fictional city-flood concept image to achieve a cinematic 3D-building atmosphere. The image is concept art only: no real Chennai location, observed water extent, building footprint, depth, or model output. Label it visibly as illustrative/demo. Show only existing fixture values elsewhere, each with demo labels. Do not copy generated screenshots or use their invented live readings, alerts, routes, safety states, exact locations, or service-health claims.

## Acceptance criteria

1. Preserve the seven sections, local adapter, existing user interactions, scenario context, and demo-only boundary. No network/API/service calls or new packages.
2. Deliver a visual layout recognizably guided by the references: compact header, clear horizontal section navigation, large spatial workspace, and task-focused supporting panels.
3. Use the bundled fictional city concept artwork only as a static illustrative visual. Clearly distinguish it from saved A20 rasters and any measured/model result. Do not present AI art as a flood simulation output.
4. Preserve existing unknown/unavailable/zero/dry/NoData semantics. Do not show invented live weather, real reservoir readings, route safety, operational risk, system health, or A21 decision-stability results.
5. Keep controls accessible, keyboard operable, reduced-motion aware, and responsive for desktop/tablet/mobile. No state is indicated by color alone.
6. Run the production build. Provide actual visual captures if the local rendering tools are available; otherwise record the exact limitation and make no visual-review claim.
7. Do not modify A21 outputs, A20 assets, B18 APIs, contracts, gates, services, package manifests, databases, or Docker configuration. Finish through the Lane B task protocol and commit only registered outputs.

## Dependencies and boundaries

Dependencies: B29, B30, B31, and B32 (`done_with_caveats`). A21 is running on disjoint science paths and is not a dependency; its results remain pending until completed and reviewed. G0/G5/G6 and contracts C1–C9 remain unchanged.
