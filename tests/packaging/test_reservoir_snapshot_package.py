from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_ai_image_context_contains_only_services_and_reservoir_connector():
    compose = (ROOT / "docker-compose.b11.yml").read_text(encoding="utf-8")
    dockerfile = (ROOT / "services/ai-service/Dockerfile").read_text(encoding="utf-8")
    assert "context: ./services" in compose
    assert "dockerfile: ai-service/Dockerfile" in compose
    assert "COPY trackb/connectors/tn_reservoir /app/services/trackb/connectors/tn_reservoir" in dockerfile
    assert "PYTHONPATH=/app/services/ai-service:/app" in dockerfile
    compose_env = __import__("yaml").safe_load(compose)["services"]["ai-service"]["environment"]
    assert compose_env["PYTHONPATH"] == "/app/services/ai-service:/app"
    assert "COPY data/" not in dockerfile
