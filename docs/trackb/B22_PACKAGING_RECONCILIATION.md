# B22 — B11 packaging mount reconciliation

Date: 2026-10-30

The original packaging assertion required the AI service to mount exactly two artifact directories: the registered A07 impact results and A09 revision-3 route results. B21 added three approved A20 manifest-linked scenario asset directories so both the AI service and Spring backend can serve the read-only C9 catalog/detail projections. These mounts are part of the approved B21 package boundary and were verified `RW=false` in the packaged runtime; the earlier two-entry expectation became stale.

The test now asserts exact source/target allowlists, bind type, and `read_only: true`, rejecting missing or additional mounts. The AI service must receive exactly the A07/A09 mounts plus A20 visualization, forecast, and simulation assets. The backend must receive exactly those three A20 mounts. It also checks the backend environment allowlist. Existing checks still require only the three app-tier services, loopback ports, health checks, no Compose named volumes/database service, no mounted secrets, and a static frontend without a proxy.

## Checks

- Focused packaging suite: `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib tests\packaging\test_b11_packaging.py` — **6 passed**.
- Quiet Compose validation: `docker compose -p twinguard-b11 -f docker-compose.b11.yml config --quiet` — passed with no configuration output.

The B21 runtime smoke and actual read-only mount inspection are recorded in [C9_ROUTE_MOUNT_REPORT.md](C9_ROUTE_MOUNT_REPORT.md). B22 performs no runtime startup, service implementation change, database operation, or volume action.
