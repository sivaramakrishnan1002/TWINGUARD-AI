# B11 local app-tier runbook

This profile packages only the local static UI, AI artifact projection service, and backend health endpoint. It is separate from the shared project and Track B streaming compositions. The UI is design-only and static; this profile does not enable operational decisions or live flood guidance.

## Prerequisites

- Docker Desktop with Linux containers and Docker Compose v2.
- Repository checkout with the registered A07 V4 and A09 revision-3 artifacts at the read-only mount paths in `docker-compose.b11.yml`.
- Network access during the first image build for pinned build dependencies. No project runtime images, database images, or streaming images are pulled by this workflow. Once the build images exist locally, build with `--pull=false`.

## Validate and build

Run from the repository root. The configuration validation suppresses rendered configuration, which can contain environment data:

```powershell
docker compose -p twinguard-b11 -f docker-compose.b11.yml config --quiet
docker compose -p twinguard-b11 -f docker-compose.b11.yml build --pull=false
```

## Start and verify

```powershell
docker compose -p twinguard-b11 -f docker-compose.b11.yml up -d --no-build --pull never
docker compose -p twinguard-b11 -f docker-compose.b11.yml ps
```

The only published ports bind to loopback: UI `127.0.0.1:8081`, AI service `127.0.0.1:8000`, and backend `127.0.0.1:8080`. Check:

- `GET http://127.0.0.1:8081/` for the static UI.
- `GET http://127.0.0.1:8000/health` for AI service health.
- `GET http://127.0.0.1:8080/health` for backend health.
- The AI service's saved-artifact `POST /impact` selector `(run_id, valid_at, scenario_key)` and `GET /route-results/{result_id}` are read-only projections of the registered simulated A07/A09 artifacts. Unknown selectors return 404 and duplicate evidence fails closed.
- `POST /route`, forecast, uncertainty, and scenario computation remain unavailable (501). The C9 visualization asset/time-slice operation is not mounted. Backend business routes are not exposed.

The AI service has read-only bind mounts for the registered A07 V4 and A09 revision-3 artifact directories. The UI has no API proxy. No database, database credentials, migrations, live feeds, or named volumes are part of this profile. These checks do not demonstrate live ingestion, operational forecast skill, validated impacts, or safe routing.

## Stop and preserve state

Stop only this Compose project's containers:

```powershell
docker compose -p twinguard-b11 -f docker-compose.b11.yml stop
docker compose -p twinguard-b11 -f docker-compose.b11.yml ps -a
```

Do not use `down -v`, prune, or volume cleanup. B11 declares no named volumes. Leave unrelated containers and volumes untouched.

## B11 verification record (2026-10-29)

- Quiet Compose validation passed with no configuration output.
- All three local images built. The AI image required `psycopg[binary]==3.3.6`; the initial image without the binary extra failed import/health, and the corrected pinned image passed health.
- Startup health: frontend, AI service, and backend all `running healthy`.
- Smoke results: UI 200; backend `/health` 200; A07 exact simulated lookup 200 for run `7004`, valid time `2015-11-30T06:00:00+00:00`, scenario `perfect_foresight_imerg`; A09 exact simulated lookup 200 for `A09-2015-12-02-06h-static-od01`; compute operations returned 501; C9 visualization path and backend `/impact` returned 404.
- No database target was configured or contacted; no migrations or database writes occurred.
- The B11 Compose project was stopped after these checks. No volumes were declared or removed; unrelated database service was left running.
