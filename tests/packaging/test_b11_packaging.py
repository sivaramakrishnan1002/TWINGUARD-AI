"""Structural safety checks for the isolated B11 app-tier package."""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "docker-compose.b11.yml"


def _compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


def test_b11_compose_config_validates_without_rendering_configuration() -> None:
    result = subprocess.run(
        ["docker", "compose", "-p", "twinguard-b11", "-f", str(COMPOSE), "config", "--quiet"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_b11_contains_only_loopback_app_tier_services_without_named_volumes() -> None:
    config = _compose()
    assert set(config["services"]) == {"frontend", "ai-service", "backend"}
    assert "volumes" not in config
    assert "db" not in config["services"]
    assert "POSTGRES" not in COMPOSE.read_text(encoding="utf-8").upper()

    expected_ports = {
        "frontend": ["127.0.0.1:8081:80"],
        "ai-service": ["127.0.0.1:8000:8000"],
        "backend": ["127.0.0.1:8080:8080"],
    }
    for name, ports in expected_ports.items():
        assert config["services"][name]["ports"] == ports
        assert config["services"][name]["healthcheck"]["test"]


def _expected_binds(*pairs: tuple[str, str]) -> list[dict[str, object]]:
    """Build a strict, ordered allowlist of bind sources and container targets."""
    return [
        {"type": "bind", "source": source, "target": target, "read_only": True}
        for source, target in pairs
    ]


def test_ai_mounts_only_registered_artifacts_read_only() -> None:
    ai = _compose()["services"]["ai-service"]
    assert ai["volumes"] == _expected_binds(
        ("./data/features/impact/batch2_v4_contract", "/app/data/features/impact/batch2_v4_contract"),
        ("./data/features/routing/results/batch2_v1/revision_3", "/app/data/features/routing/results/batch2_v1/revision_3"),
        ("./data/features/visualization3d/batch2_v1", "/app/data/features/visualization3d/batch2_v1"),
        ("./data/features/forecast/batch2_v1", "/app/data/features/forecast/batch2_v1"),
        ("./data/features/simulation/batch2_v1", "/app/data/features/simulation/batch2_v1"),
    )
    assert set(ai["environment"]) == {"PYTHONDONTWRITEBYTECODE", "PYTHONPATH"}


def test_backend_mounts_only_a20_scenario_assets_read_only() -> None:
    backend = _compose()["services"]["backend"]
    assert backend["volumes"] == _expected_binds(
        ("./data/features/visualization3d/batch2_v1", "/app/data/features/visualization3d/batch2_v1"),
        ("./data/features/forecast/batch2_v1", "/app/data/features/forecast/batch2_v1"),
        ("./data/features/simulation/batch2_v1", "/app/data/features/simulation/batch2_v1"),
    )
    assert set(backend["environment"]) == {"SERVER_PORT", "TWINGUARD_SCENARIO_PROJECT_ROOT"}


def test_build_inputs_are_version_pinned_and_do_not_mount_secrets() -> None:
    dockerfiles = {
        ROOT / "frontend/Dockerfile": {"node:22.14.0-alpine3.21", "nginx:1.27.5-alpine"},
        ROOT / "services/ai-service/Dockerfile": {"python:3.12.8-slim-bookworm"},
        ROOT / "services/backend/Dockerfile": {
            "maven:3.9.9-eclipse-temurin-21",
            "eclipse-temurin:21.0.6_7-jre-jammy",
        },
    }
    for path, expected_images in dockerfiles.items():
        lines = [line.split()[1] for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("FROM ")]
        assert set(lines) == expected_images
        assert all(":" in image for image in lines)

    compose_text = COMPOSE.read_text(encoding="utf-8").lower()
    assert "postgres_password" not in compose_text
    assert ".env" not in compose_text
    assert "live_feed" not in compose_text


def test_frontend_is_static_only_and_ai_route_computation_stays_separate() -> None:
    nginx = (ROOT / "frontend/nginx.conf").read_text(encoding="utf-8").lower()
    assert "try_files" in nginx
    assert "proxy_pass" not in nginx
    assert "proxy_pass" not in COMPOSE.read_text(encoding="utf-8").lower()

