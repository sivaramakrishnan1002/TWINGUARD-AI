"""Apply checksum-tracked SQL migrations to the configured twinguard database."""
from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy import text

from db_common import ROOT, make_engine

MIGRATIONS = ROOT / "database" / "migrations"


def apply_migrations() -> list[str]:
    engine = make_engine()
    applied: list[str] = []
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS twinguard")
            conn.exec_driver_sql(
                """CREATE TABLE IF NOT EXISTS twinguard.schema_migrations (
                    version text PRIMARY KEY,
                    applied_at timestamptz NOT NULL DEFAULT now(),
                    checksum_sha256 text NOT NULL
                )"""
            )
        for path in sorted(MIGRATIONS.glob("*.sql")):
            sql = path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
            with engine.begin() as conn:
                previous = conn.execute(
                    text("SELECT checksum_sha256 FROM twinguard.schema_migrations WHERE version=:v"),
                    {"v": path.name},
                ).scalar_one_or_none()
                if previous:
                    if previous != checksum:
                        raise RuntimeError(f"Applied migration checksum changed: {path.name}")
                    continue
                conn.exec_driver_sql(sql)
                conn.execute(
                    text("INSERT INTO twinguard.schema_migrations(version, checksum_sha256) VALUES (:v,:h)"),
                    {"v": path.name, "h": checksum},
                )
                applied.append(path.name)
    finally:
        engine.dispose()
    return applied


if __name__ == "__main__":
    versions = apply_migrations()
    print("Applied migrations:", ", ".join(versions) if versions else "none; schema is current")
