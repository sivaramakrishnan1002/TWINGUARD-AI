# CR-009 — C9 read-only route activation decision

**Decision:** Approved by the project owner on 2026-10-30.

## Approved scope

Authorize the two existing proposed C9 operations in both the FastAPI AI service and the Spring backend:

- `GET /scenario-visualization-assets` — read the A20 manifest-backed catalog.
- `GET /scenario-visualization-assets/{event_id}/{scenario_id}` — retrieve one exact saved scenario detail.

The operations are limited to bounded, read-only projections of saved A20 research assets. Preserve manifest provenance and hashes, exact saved UTC timestamps, explicit null valid times, grid/CRS, units basis, parameter-member spread, coverage and NoData-as-unknown semantics. They must return no partial result when a manifest or referenced asset cannot be completely validated.

## Approved HTTP mappings

- Invalid selector/input: `400`.
- No exact matching scenario: `404`.
- Duplicate or ambiguous identity: `409` for both catalog and exact-detail operations; a catalog with duplicate identities is not returned.
- Missing, unreadable, or unavailable asset: `503`, with no partial result.

The current runtime remains unavailable until the Lane B implementation task completes its conformance tests. OpenAPI entries remain projections and do not claim routes are mounted.

## Boundaries

C9 is a separate additive proposed contract, approved for implementation but **not frozen** and not added to the C1–C8 registry. C1–C8 versions/statuses and G0 remain unchanged. This decision does not authorize live feeds, generated predictions, operational alerts or routing, database writes, migrations, or scientific-output regeneration. A20 outputs remain read-only and research-only; no street-level hydraulic accuracy, live prediction, warning, safety, or emergency-guidance claim is authorized.

## Review and sequence

Integrator change-control review is recorded in I16 and the C9 draft/OpenAPI projections. Lane B task B21 owns the route mounting and runtime tests. B18 remains blocked until B21 is complete and verified; I08 remains blocked until B18 evidence is complete.
