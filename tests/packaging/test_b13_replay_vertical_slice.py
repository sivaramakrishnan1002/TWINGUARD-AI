"""Static package boundary checks for the B11 B13 test-scoped route."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_packaged_fixture_and_b11_route_enablement_are_bounded() -> None:
    fixture_path = ROOT / "services/ai-service/app/replay_results/b13_source_observation.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert hashlib.sha256(fixture_path.read_bytes()).hexdigest() == "dd5ea17cdf63853ffd1cdc3036b8c8282490daafd3e19715cd82445cb27ff2a8"
    assert fixture["selector"]["event_id"] == "replay:POONDI:date:2015-12-01"
    assert fixture["source_observation"]["observed_at"] is None
    assert fixture["source_observation"]["observation_timezone"] == "unknown"
    assert len(fixture["context_inputs"]) == 3

    compose = yaml.safe_load((ROOT / "docker-compose.b11.yml").read_text(encoding="utf-8"))
    assert set(compose["services"]) == {"frontend", "ai-service", "backend"}
    backend_env = compose["services"]["backend"]["environment"]
    assert backend_env["TWINGUARD_B13_ENABLED"] == "true"
    assert backend_env["TWINGUARD_B13_AI_BASE_URL"] == "http://ai-service:8000"
    # The bounded services/ build context packages the shared, dependency-free
    # public reservoir connector without including raw data or the repository.
    assert compose["services"]["ai-service"]["build"]["context"] == "./services"
    assert compose["services"]["ai-service"]["build"]["dockerfile"] == "ai-service/Dockerfile"
    dockerfile = (ROOT / "services/ai-service/Dockerfile").read_text(encoding="utf-8")
    assert "COPY ai-service/app /app/services/ai-service/app" in dockerfile
    assert "COPY trackb/connectors/tn_reservoir /app/services/trackb/connectors/tn_reservoir" in dockerfile
    assert fixture_path.is_relative_to(ROOT / "services/ai-service/app")

    # Packaging contains only the app tier; the B13 path has no database service or writable data mount.
    assert all("db" not in name.lower() and "postgres" not in name.lower() for name in compose["services"])
    assert all(mount.get("read_only") is True for mount in compose["services"]["ai-service"].get("volumes", []))
