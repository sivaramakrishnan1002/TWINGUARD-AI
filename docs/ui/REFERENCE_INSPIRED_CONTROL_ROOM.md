# B33 — Reference-inspired TwinGuard control room

## Delivered

The interface now follows the reference images' broad layout: branded status header, seven horizontal product sections, a map-led scenario workspace, compact simulation/source controls, and quick links to reservoirs, response, and what-if work. The selected scenario and synthetic step remain visible, and all seven sections retain their own controls and content.

The Situation Overview uses a bundled fictional city-flood concept image to create the cinematic 3D-building atmosphere requested. It is prominently labeled as static concept art, fictional, and not georeferenced. The 2D option remains a schematic interface illustration. The selected fixture step changes the displayed demo state and labels; it does not animate or modify the concept image.

The header explicitly says live input is not connected. The source panel distinguishes active local demo fixtures, separate saved research outputs, and unavailable live feeds. Existing synthetic fixture values remain the only numbers shown in demo panels. Route safety, operational alerts, real weather values, and A21 results are not fabricated.

## Real-time boundary

This UI pass does not make TwinGuard a live flood system. The repository's verified flood products are saved research/simulation outputs; Track B's documented runtime evidence is historical REPLAY; and the forecast/uncertainty business endpoints remain unavailable. No approved live rainfall/reservoir feed or operational forecast output is wired to this UI. The screen is structured to show source state honestly and can be connected after the project has an approved live-source contract, operational model service, time/provenance semantics, and end-to-end evidence.

The generated city art is not a scientific result and must not be presented as one. The saved A20 rasters and B18 viewer remain distinct from that image and are not loaded in this product screen.

## Validation

- `npm run build` — passed (`tsc --noEmit && vite build`).
- Production bundle contains the local WebP concept asset (278.34 kB); CSS 194.33 kB (34.66 kB gzip); JS 206.25 kB (62.16 kB gzip).
- No package or lockfile changes.
- Local browser screenshot and interactive visual review were unavailable in Work settings. No browser visual pass is claimed.
- No API/service calls, Docker actions, database access, migration, or live source connection was performed.

## Preservation

The existing seven sections, local adapter, reduced-motion support, keyboard-operable navigation and controls, A21-pending copy, B29–B32 evidence, APIs/contracts/gates, and science outputs remain unchanged. A21 is still separate and running; no A21 result is consumed or implied.
