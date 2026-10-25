# Track B runbook

## Verified local prerequisites

Checked 2026-10-25: all four required image references are present locally; no image pull was performed. Existing `.venv` client pins are redis 8.1.0, confluent-kafka 2.16.0, and prometheus-client 0.26.0. No package installation is needed.

Use these exact local image assignments if overriding the overlay defaults:

```powershell
$env:TRACKB_REDIS_IMAGE = 'redis:8.10.2-alpine'
$env:TRACKB_KAFKA_IMAGE = 'apache/kafka:4.3.2'
$env:TRACKB_PROMETHEUS_IMAGE = 'prom/prometheus:v3.13.2'
$env:TRACKB_GRAFANA_IMAGE = 'grafana/grafana:13.2.2-ubuntu'
```

## Validate and start only Track B

The validation command suppresses all output and prints only its exit result. Never print rendered Compose configuration.

```powershell
docker compose -f docker-compose.yml -f docker-compose.trackb.yml --profile trackb config --quiet
```

Start only the four named Track B services (do not omit the service list, which could start unprofiled services from the base file):

```powershell
docker compose -f docker-compose.yml -f docker-compose.trackb.yml --profile trackb up -d trackb-redis trackb-kafka trackb-prometheus trackb-grafana
docker compose -f docker-compose.yml -f docker-compose.trackb.yml --profile trackb ps
```

Ports published by the overlay are loopback-only: Redis 6380, Kafka 9092, Prometheus 9090, Grafana 3001. Track B consumer metrics bind to `127.0.0.1:8000`; the Prometheus target is `host.docker.internal:8000`. Scrape reachability must be checked at runtime and is not implied by configuration.

## Run the consumer and REPLAY

In a separate terminal, use a fresh replay consumer group and an isolated Redis logical database for the B9 run. `latest` starts this new group at the current topic end, avoiding pre-existing retained records. The consumer still reads generated alerts produced after the replay begins.

```powershell
$env:TRACKB_CONSUMER_GROUP = 'trackb-b9-replay'
$env:TRACKB_AUTO_OFFSET_RESET = 'latest'
$env:TRACKB_REDIS_URL = 'redis://127.0.0.1:6380/1'
.\.venv\Scripts\python.exe -m pipelines.trackb.streaming consume
```

In another terminal, produce the historical replay window at full speed; records are marked `source: replay`:

```powershell
.\.venv\Scripts\python.exe -m pipelines.trackb.streaming replay --start 2015-11-20 --end 2015-12-04
```

Inspect local metrics at `http://127.0.0.1:8000/metrics`, Prometheus at `http://127.0.0.1:9090`, and Grafana at `http://127.0.0.1:3001`. Record actual topic counts, consumed messages, alert counts, errors, latency and Prometheus target health. These are REPLAY results, never live data.

## Database boundary

Do not apply migration 100 or write to the shared project database. The default consumer has no database connection. DB persistence remains blocked unless an already-approved isolated Track B test database is available and migration 100 is applied there under that approval.

## Runtime attempt — 2026-10-25

- Quiet Compose validation passed. Redis, Kafka, Prometheus and Grafana all reached healthy after the Grafana healthcheck was changed to use the image's existing `curl` executable.
- The replay producer reported 120 events for 2015-11-20–2015-12-04. A fresh `trackb-b9-replay` consumer group processed 31 before being stopped. Metrics showed zero alerts and zero rule errors; observed topic lag remained 4,079. Redis DB 1 contained processed markers but no reservoir-state or current-alert keys. B9 is incomplete and blocked pending consumer/topic assignment and throughput diagnosis.
- Prometheus target was `up` while the consumer's loopback metrics endpoint ran. It became `down` after consumer shutdown. The sampled latency mean of 65.8237 seconds across 31 observations is delayed/stale backlog timing, not accepted as representative replay latency.
- Migration 100 remained unapplied; no DB writes were attempted.
- B10 stop-only returned success. All four Track B services are exited; all four named volumes remain present.

## Stop and preserve volumes

After runtime checks, stop only Track B services. Never run `down`, `down -v`, prune, or a volume deletion command.

```powershell
docker compose -f docker-compose.yml -f docker-compose.trackb.yml --profile trackb stop trackb-redis trackb-kafka trackb-prometheus trackb-grafana
docker compose -f docker-compose.yml -f docker-compose.trackb.yml --profile trackb ps
docker volume ls --filter label=com.docker.compose.volume=trackb-redis-data --format '{{.Name}}'
docker volume ls --filter label=com.docker.compose.volume=trackb-kafka-data --format '{{.Name}}'
docker volume ls --filter label=com.docker.compose.volume=trackb-prometheus-data --format '{{.Name}}'
docker volume ls --filter label=com.docker.compose.volume=trackb-grafana-data --format '{{.Name}}'
```

The previous credential exposure risk is accepted by the user for this run. Do not copy, display, or log any credential; keep Compose output suppressed.
