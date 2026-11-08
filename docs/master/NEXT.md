# Next actions

## YOU DO THIS (manual tasks in order)

- **I04 — Release/backups** (blocked_manual)
- **M4 — Create GitHub repo/push** (blocked_manual)
- **M6 — Optional PDF georeferencing** (parked)
- **M7 — Census/licence checks** (blocked_manual)
- **M8 — Mentor review dates** (blocked_manual)

  - Steps: Project owner: answer docs/master/I04_RELEASE_BACKUP_DECISION_REQUEST.md with release/tag/ref and publication scope, required reviews, and whether a database dump is required. If yes, identify an isolated test database and owner for a separately authorized preflight. No tag, dump, or publication is authorized yet.
  - Steps: Create the GitHub repository, confirm its remote and default branch, then push only after reviewing the staged paths.
  - Steps: Optional: georeference the 2021/2023 PDFs and December maps in QGIS; preserve originals and document control points/CRS.
  - Steps: Verify census provenance and dataset licences; record source, terms, date and permitted use in the project catalogue.
  - Steps: Set mentor review dates and record them in the project schedule.

## Ready tasks by lane A

- None.

## Ready tasks by lane B

- None.

## Ready tasks by lane I

- None.

## Blocked tasks

- **B13 — E2E scenario** (blocked_prerequisite)
- **I04 — Release/backups** (blocked_manual)
- **M4 — Create GitHub repo/push** (blocked_manual)
- **M7 — Census/licence checks** (blocked_manual)
- **M8 — Mentor review dates** (blocked_manual)
- **B40 — Implement authorized IMD rainfall/weather connector** (blocked_prerequisite)
- **B42 — Prove observation-triggered recomputation through API and UI** (blocked_prerequisite)
- **A26 — Optional CUDA backend for services/flood_engine (OD-2026-11-08)** (blocked_prerequisite)

## Running tasks

- **A25 — High-resolution flood simulation for 3D (citywide 90-120 m, 30 m focus areas, buildings, wards)** (running)
- **B48 — Reference-design UI with Google Photorealistic 3D Tiles (7 tabs) — ui session** (running)

## Next gate

G5 is next (`not_ready`); review its registered prerequisites and evidence before closure.
