# B32 — High-fidelity TwinGuard product UI

**Owner:** Lane B. **Status:** ready/unclaimed at registration. **Classification:** local DEMO/SIMULATED interface refinement.

## Goal

Raise the seven-section frontend to a cohesive, high-fidelity control-room product experience. This is a substantial visual and interaction refinement beyond B30/B31, focused on the scenario workspace, map/twin stage, information hierarchy, and task-specific screen layouts.

## Inputs

- B29/B30 product experience and captures.
- B31 shared scenario context and A21-pending UI states.
- Existing local demo adapter and fixture semantics.
- The project-owner reference images in conversation (layout inspiration only; do not copy their fabricated map or values).

## Owned outputs

- `frontend/src/ui/product/ProductExperience.tsx`
- `frontend/src/ui/product/product.css`
- `tests/ui/product/evidence/b32/`
- `docs/ui/HIGH_FIDELITY_UI.md`

## Scope

Refine the application shell, navigation, scenario/time context, overview, 3D/2D scene, Reservoirs, Impacts, Emergency Response, What-if Lab, and Data & System views. Make the center of gravity the scenario and its spatial context, with supporting evidence and controls grouped by the task the user is performing. Improve the vector scene with a legible, attractive, schematic city/river/road composition and subtle motion that remains visibly illustrative.

Use a restrained professional visual system: consistent type scale, spacing, iconography, surfaces, colors, data labels, and compact states. Avoid a wall of equal-weight cards, oversized decorative typography, tiny all-caps text, or neon-heavy styling. Give controls clear focus, hover, selected, disabled, loading, unavailable, and unknown states. Keep dense content scannable and responsive.

## Acceptance criteria

1. Preserve the seven sections, local adapter, DEMO/SIMULATED boundary, existing controls, and B31 context bar; no new network/service calls, package, or geographic/flood-data claims.
2. Deliver a materially stronger visual hierarchy and more refined spatial view. The map/twin should be the primary surface where relevant, with compact supporting context and task-specific controls.
3. Improve the schematic city scene using authored vector/CSS graphics only. Clearly label that it is illustrative and has no geographic coordinates, measured depth, or hydraulic meaning. Keep the 2D fallback coherent.
4. Preserve unknown, unavailable, zero, dry, and NoData as distinct states. A21 values and decision comparisons remain explicitly pending until completed owner evidence is available; do not invent conditional routes or stability results.
5. Preserve keyboard navigation, visible focus, semantic labels/headings, reduced-motion support, and readable layouts for desktop, tablet, and mobile.
6. Capture the overview, 3D Twin, Emergency Response, What-if Lab, and mobile overview using an available local rendering workflow. Record actual viewport dimensions and any inaccessible manual checks; do not claim visual review without captured evidence.
7. Run the production build. Do not install packages or alter lockfiles. Preserve B29–B31 evidence and unrelated concurrent work.
8. Finish through the official Lane B protocol. Commit only B32-owned paths; do not edit A21 outputs, contracts, gates, services, databases, or Docker configuration.

## Dependencies and boundaries

Dependencies: B29, B30, and B31 (`done_with_caveats`). A21 is running on disjoint Lane A outputs and is not a dependency. Until its report is complete and reviewed, all A21-driven UI remains pending. Keep G0/G5/G6 and C1–C9 unchanged.
