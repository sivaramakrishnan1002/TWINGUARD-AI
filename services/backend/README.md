# TwinGuard backend

This directory contains the Java 21 / Spring Boot 3 application-facing backend foundation. It is independent of the FastAPI AI service, Track B, and the shared database.

## Current behavior

- `GET /health` reports process health without dependency details.
- Errors use generic RFC 9457 problem responses. Request values and exception messages are not included in logs or error bodies.
- Console logs use Spring Boot's structured Logstash JSON format.
- The HTTP port is configurable with `SERVER_PORT` (defaults to `8080`).
- Contract-shaped DTOs, adapter ports, and a service layer define the Phase 2 gateway structure.
- Optional upstream base URLs bind from `TWINGUARD_UPSTREAMS_AI_SERVICE_BASE_URL` and `TWINGUARD_UPSTREAMS_TRACK_B_BASE_URL`; setting them does not enable an adapter or make an upstream call.

No design-contract routes are exposed yet. The default AI-service, Track B, and scenario-store adapters report `UNAVAILABLE / NOT_CONFIGURED`; they do not fabricate state. No real upstream integration or database connection exists. The API design in `docs/api/backend.yaml` remains unfrozen pending G0.

## Phase 3 preflight — 2026-10-25

No upstream adapter was enabled because G0 is still `not_ready` in `docs/master/STATE.json`; the API documents remain design inputs, not approved integration contracts.

- **AI service:** its documented local health URL, `http://127.0.0.1:8000/health`, responded with HTTP 200 during preflight. This establishes process health only. The AI-service README describes forecast, uncertainty, impact, routing, and scenario capabilities as placeholders returning 501; no approved data endpoint contract is available for integration.
- **Track B:** `docs/trackb/TRACKB_REPORT.md` records B9 as blocked after partial replay (31 of 120 events processed, zero alerts, and no reservoir-state/current-alert keys). B10 records all Track B services stopped. B12's read-only router is not mounted in a host application and has no connected read adapter.
- **Configuration:** the AI-service and Track B base-URL environment settings were unset at preflight. Test-only example URLs verify property binding and confirm that configured URLs alone still return `UNAVAILABLE / NOT_CONFIGURED`.
- **Scenarios:** no scenario store or approved persistence contract exists. The backend does not access the shared database.

Before a Phase 3 adapter can be enabled, the integrator must mark G0 ready and confirm the relevant versioned request/response contract, provenance and NoData semantics, ownership, and source modes. The owning service must then be available through an approved endpoint with a documented authentication and timeout policy. Track B additionally needs B9 complete and its router mounted with a connected read adapter. Scenario operations need an approved store contract. Until those conditions are met, design routes stay unexposed and default adapters remain unavailable.

## Build and run

Use Java 21 and Maven 3.10 or later. From this directory:

```powershell
mvn -o test
mvn -o spring-boot:run
```

The offline flag prevents Maven from fetching dependencies. If the required artifacts are not already cached, Maven will fail with a missing-artifact message; resolve that prerequisite separately before building.
