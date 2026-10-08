# TwinGuard AI

An exploratory geospatial project for assembling and evaluating flood-risk data for Chennai and its surrounding metropolitan area.

## Study area decision

Use the existing `data/raw/boundary/chennai_cma_boundary.geojson` as the provisional analysis boundary. It represents an older, pre-2022 Chennai Metropolitan Area boundary with an area of approximately 1,187.46 km². Confirm whether the project requires the expanded post-2022 CMA boundary before treating this study area as final.

## Data layout

- `data/raw/` — immutable source downloads and acquisition logs; excluded from Git.
- `data/processed/` — planned intermediate datasets; excluded from Git.
- `data/features/` — planned model-ready features; excluded from Git.
- `docs/` — plans, data inventory, quality notes, and project status.
- `services/backend/` — planned API/backend service.
- `services/ai-service/` — planned model/inference service.
- `frontend/` — planned user interface.
- `notebooks/` — planned exploratory analysis.
- `experiments/` — planned controlled model experiments.

## Project phases

1. Study definition and project setup.
2. Data acquisition, inventory, and quality audit — completed for the current collected sources; several important sources remain manual or unavailable.
3. Feature engineering and label preparation — planned; not started.
4. Model development and validation — planned.
5. Application integration, evaluation, and final documentation — planned.

See `docs/PROJECT_STATUS.md` and `docs/PHASE3_PLAN.md` for current status and the planning decisions needed before Phase 3.
