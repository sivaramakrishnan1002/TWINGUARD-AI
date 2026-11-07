# I04 — Release and backup decision request

**Status: pending project-owner decisions.** This request records decisions needed to scope G6/I04. No tag, publication, database access, dump, or volume action is authorized by this document.

## Release scope decision

Please record:

1. Target release version and exact Git ref/commit. G6 currently names `v1.0`; confirm whether that is the tag to create or provide the intended version.
2. Release contents and evidence required in the release: validation report, final report/paper status, G0/G5 evidence, I08/B18 saved-replay evidence, service/package evidence, and known limitations. A17's current outputs are internal drafts; state whether Lane A and academic/supervisor review are required before release.
3. Whether a local tag only is authorized, or whether remote push/publication is in scope. If remote publication is requested, identify the approved destination and release owner. No remote will be contacted until this is explicit.
4. Tag ownership/signing requirements and the person authorized to approve the final tag and release report.

## Database backup decision

Please choose one:

- **No database dump required for G6.** Record this decision; I04 will not create a dump.
- **A dump is required.** Identify the exact database name and owner, confirm it is an isolated fresh/test target, and separately authorize a read-only preflight and dump task. The task must positively verify the configured target, database ownership and test status, available disk, and ignored `backups/` destination immediately before writing. Do not use shared `twinguard` by default. A shared database requires a separate explicit decision and safety review; no credentials should be placed in this request.

The project gate protocol requires confirming the target and available disk before any dump and prohibits Docker volume deletion. This request does not itself authorize a database connection, backup, tag, or publication.

## Current blockers and evidence

- `I04` is blocked: release scope, tag/ref, publication scope, and backup requirement/target have not been decided.
- `docs/VALIDATION_REPORT.md` (A15) records internal/reproducibility checks and states that independent date-matched flood-depth and real route truth are unavailable; it does not establish scientific validation.
- `docs/PAPER_DRAFT.md` and `docs/FINAL_REPORT.md` (A17) remain internal drafts pending authorized Lane A and academic/supervisor review. They predate I08's saved A20 UI acceptance and must be checked for release currency before G6 closure.
- `docs/master/FLOOD_3D_SCENARIO_ACCEPTANCE.md` records I08's exact saved-asset replay evidence and caveats. It does not establish live operation, validated hydraulics, or safety.

G6 remains closed until the project-owner decisions are recorded, I04 is completed under the resulting scope, and the complete G6 protocol and evidence pass.
