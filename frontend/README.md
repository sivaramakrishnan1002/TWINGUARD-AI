# TwinGuard UI

Map-first React, TypeScript, Tailwind, and MapLibre foundation for the Chennai flood research interface.

## Setup status

M3 npm/network setup was approved for Phase 2. Install with `npm ci` from this directory using the checked-in `package-lock.json`, then run `npm run dev` or `npm run build`.

## Phase 1 behavior

The shell starts with no event, run, map source, or flood layer selected. MapLibre uses an empty style with no remote basemap. Its camera is centered on the midpoint of the provisional study-boundary bounding box, but no boundary geometry is rendered. The 3D control changes camera perspective only; terrain tiles are not available. UI view-model interfaces live in `src/ui/types.ts`; service integration belongs behind adapters after verified HTTP endpoints and data catalogues are ready. The current OpenAPI files are design-only contracts, not operational endpoints.
