"""Shared safe configuration and database helpers for Stage 5/6."""
from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine

ROOT = Path(__file__).resolve().parents[2]


def read_env(path: Path | None = None) -> dict[str, str]:
    """Read simple KEY=VALUE .env lines without echoing values or using dotenv."""
    source = path or ROOT / ".env"
    result: dict[str, str] = {}
    for raw in source.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        result[key.strip()] = value
    missing = [k for k in ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD") if not result.get(k)]
    if missing:
        raise RuntimeError("Missing required .env keys: " + ", ".join(missing))
    return result


def make_engine(values: dict[str, str] | None = None) -> Engine:
    v = values or read_env()
    url = URL.create(
        "postgresql+psycopg",
        username=v["POSTGRES_USER"],
        password=v["POSTGRES_PASSWORD"],
        host=v.get("POSTGRES_HOST") or "localhost",
        port=int(v.get("POSTGRES_PORT") or "5432"),
        database=v["POSTGRES_DB"],
    )
    return create_engine(url, pool_pre_ping=True, echo=False)
