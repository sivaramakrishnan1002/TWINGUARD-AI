# B31 — Flood operations control-room UI refinement

**Owner:** Lane B. **Status:** scoped for an isolated UI implementation. **Classification:** local DEMO/SIMULATED frontend refinement.

## Goal

Improve the existing B29/B30 seven-section product experience into a more coherent, high-quality flood operations control-room interface. This is a focused product refinement, not a new data integration or change to the underlying service architecture. The design must remain honest about demo fixtures and current evidence limits.

## Inputs

- B29 local demo adapter, fixtures, and product behavior.
- B30 refined product screen and visual evidence.
- Current frontend implementation and the A21 task specification (for future terminology only; A21 results are not yet available).

## Owned outputs

- `frontend/src/ui/product/ProductExperience.tsx`
- `frontend/src/ui/product/product.css`
- `tests/ui/product/product-experience.test.mjs` (only if behavior changes require coverage; preserve existing assertions)
- New B31 visual evidence under `tests/ui/product/evidence/b31/`
- `docs/ui/CONTROL_ROOM_UI_REFINEMENT.md`

## Product direction

Create a calm, legible operations workspace that makes four things immediately clear: selected scenario and time, what the display is showing, what evidence is available, and which values or decisions remain uncertain. Use a strong map/workspace hierarchy, a consistent scenario/time control, restrained color, readable typography, and fewer repetitive bordered cards. Maintain the seven existing sections and their local demo behaviors.

The overview should establish the scenario, frame/time, source mode, and evidence limitations at a glance. The 3D Twin should use a clear visual stage with well-organized layer and playback controls. Reservoirs, Impacts, Emergency Response, What-if Lab, and Data & System should retain their distinct tasks and share the same selected scenario/time context.

## Acceptance criteria

1. Preserve all seven B29 sections and the local typed demo adapter. No network/API call, backend dependency, new package, or real-data connection is introduced.
2. Add a coherent shared scenario/time control usable across sections. Scenario changes reset the frame and keep the current source/demo labels synchronized. Playback respects reduced-motion preferences and can be stopped by keyboard-accessible controls.
3. Refine layout, spacing, typography, contrast, card treatment, navigation, and responsive behavior so the interface reads as one professional application rather than a collection of generic dashboard cards. Do not rely on color alone for state.
4. Keep DEMO/SIMULATED labeling visible and accurate. Preserve distinctions among unknown, unavailable, zero, dry, and NoData. Do not invent A21 decision-stability results; until A21 is complete, show an explicit pending/illustrative state where relevant.
5. Keep all current limits visible: schematic water is illustrative, demo values are synthetic, no safe-route or operational guidance is offered, and service health is not inferred from the static demo.
6. Preserve keyboard focus visibility, semantic headings/labels, skip navigation, and responsive layouts at desktop, tablet, and mobile widths.
7. Provide visual captures for the overview, 3D Twin, Emergency Response, and What-if Lab at desktop and a mobile overview. Record viewport sizes and known limitations in the report.
8. Run the production build and the existing focused UI/product and demo-only packaging checks. Record exact results and update the UI progress evidence.
9. Do not change A21, science outputs, API/OpenAPI contracts, gates, databases, or Docker behavior. Finish through the official Lane B protocol and commit only registered outputs.

## Dependencies and boundaries

Dependencies: B29 and B30 (`done_with_caveats`). A21 is **not** a dependency for the design refinement; use pending/illustrative states until its evidence is complete. A21's registered outputs do not overlap these frontend paths. Keep G0/G5/G6 and all frozen contracts unchanged.
