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
        # B47 / C4 v3: model grids and the product static bundle.
        ("./data/features/live", "/app/data/features/live"),
        ("./data/features/v3/product_static_v1", "/app/data/features/v3/product_static_v1"),
    ) + [
        # The only writable mount: the git-ignored C4 v3 run store.
        {"type": "bind", "source": "./data/features/v3/runs", "target": "/app/data/v3/runs", "read_only": False,
         "bind": {"create_host_path": True}},
    ]
    assert set(ai["environment"]) == {
        "PYTHONDONTWRITEBYTECODE", "PYTHONPATH", "TWINGUARD_LIVE_SCHEDULE_MIN", "TWINGUARD_V3_RUNS",
        "TWINGUARD_V3_PRODUCT_STATIC", "TWINGUARD_LIVE_STATIC", "TWINGUARD_V3_WEATHER_MIN_INTERVAL_S", "TWINGUARD_V3_LIVE",
    }
    # CR-021: live forecast mode is on in the packaged stack and switchable; the old CR-018 draft scheduler stays off.
    assert ai["environment"]["TWINGUARD_V3_LIVE"] in ("0", "1")
    # OD-2026-11-07: no background polling; the draft scheduler stays disabled.
    assert ai["environment"]["TWINGUARD_LIVE_SCHEDULE_MIN"] == "0"
    assert int(ai["environment"]["TWINGUARD_V3_WEATHER_MIN_INTERVAL_S"]) >= 600


def test_backend_mounts_only_a20_scenario_assets_read_only() -> None:
    backend = _compose()["services"]["backend"]
    assert backend["volumes"] == _expected_binds(
        ("./data/features/visualization3d/batch2_v1", "/app/data/features/visualization3d/batch2_v1"),
        ("./data/features/forecast/batch2_v1", "/app/data/features/forecast/batch2_v1"),
        ("./data/features/simulation/batch2_v1", "/app/data/features/simulation/batch2_v1"),
    )
    assert set(backend["environment"]) == {
        "SERVER_PORT",
        "TWINGUARD_SCENARIO_PROJECT_ROOT",
        "TWINGUARD_B13_ENABLED",
        "TWINGUARD_B13_AI_BASE_URL",
    }


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
    # CR-018: the same-origin /api/ai/ route to the packaged AI service stays GET-only; C4 v3 (B47) adds one
    # /api/ai/v3/ route that also allows the POST/PUT operations of the contract. No other proxy exists.
    assert nginx.count("proxy_pass") == 2
    assert "location /api/ai/ {" in nginx
    assert "proxy_pass http://ai-service:8000/;" in nginx
    assert "limit_except get { deny all; }" in nginx
    assert "location /api/ai/v3/ {" in nginx
    assert "proxy_pass http://ai-service:8000/v3/;" in nginx
    assert "limit_except get post put { deny all; }" in nginx
    assert "proxy_pass" not in COMPOSE.read_text(encoding="utf-8").lower()



def test_gpu_is_opt_in_and_cpu_stays_default() -> None:
    """OD-2026-11-08: the base stack needs no GPU; docker-compose.gpu.yml opts in with gpus: all."""
    ai = _compose()["services"]["ai-service"]
    assert "gpus" not in ai and "deploy" not in ai
    assert "TWINGUARD_GPU" not in str(ai.get("build", {}).get("args", {}))
    dockerfile = (ROOT / "services/ai-service/Dockerfile").read_text(encoding="utf-8")
    assert "ARG TWINGUARD_GPU=0" in dockerfile and "torch==2.14.1" in dockerfile
    gpu = yaml.safe_load((ROOT / "docker-compose.gpu.yml").read_text(encoding="utf-8"))["services"]["ai-service"]
    assert gpu["gpus"] == "all" and gpu["build"]["args"]["TWINGUARD_GPU"] == "1"
    assert gpu["environment"]["TWINGUARD_V3_DEVICE"] == "auto"
    result = subprocess.run(
        ["docker", "compose", "-p", "twinguard-b11", "-f", str(COMPOSE), "-f", str(ROOT / "docker-compose.gpu.yml"), "config", "--quiet"],
        cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_gpu_image_pins_match_requirements_gpu() -> None:
    """The optional GPU image installs exactly the torch pin and index recorded in requirements-gpu.txt."""
    import re

    lines = [line.strip() for line in (ROOT / "requirements-gpu.txt").read_text(encoding="utf-8").splitlines()
             if line.strip() and not line.strip().startswith("#")]
    index = next(line.split(None, 1)[1] for line in lines if line.startswith("--index-url"))
    pins = sorted(line for line in lines if not line.startswith("--"))
    dockerfile = (ROOT / "services/ai-service/Dockerfile").read_text(encoding="utf-8")
    gpu_lines = dockerfile.split('if [ "$TWINGUARD_GPU" = "1" ]; then', 1)[1].splitlines()
    gpu_install = next(line for line in gpu_lines if "pip install" in line).split(";")[0]
    assert sorted(re.findall(r"\b[\w.-]+==[\w.+-]+", gpu_install)) == pins
    assert f"--index-url {index}" in gpu_install


def test_always_on_override_restarts_containers_and_keeps_base_unchanged() -> None:
    """CR-021 live mode 'always on' option: restart: unless-stopped only via the override file."""
    base = _compose()["services"]
    assert all("restart" not in svc for svc in base.values())
    override = yaml.safe_load((ROOT / "docker-compose.always-on.yml").read_text(encoding="utf-8"))["services"]
    assert {name: svc["restart"] for name, svc in override.items()} == {
        "ai-service": "unless-stopped", "backend": "unless-stopped", "frontend": "unless-stopped"}
    assert override["ai-service"]["environment"]["TWINGUARD_V3_LIVE"] == "1"
    result = subprocess.run(
        ["docker", "compose", "-p", "twinguard-b11", "-f", str(COMPOSE), "-f", str(ROOT / "docker-compose.always-on.yml"),
         "config", "--quiet"], cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_local_live_launcher_sets_live_and_gpu_worker() -> None:
    script = (ROOT / "services/ai-service/start_live.ps1").read_text(encoding="utf-8")
    for needle in ('$env:TWINGUARD_V3_LIVE', '$env:TWINGUARD_V3_DEVICE = "auto"', '$env:TWINGUARD_V3_WORKER = "auto"',
                   "run_local.py", "-WindowStyle Hidden", r"data\features\v3\logs"):
        assert needle in script
    assert "start_live.ps1" in (ROOT / "services/ai-service/start_live.bat").read_text(encoding="utf-8")
