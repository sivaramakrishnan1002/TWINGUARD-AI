"""Read-only PostgreSQL access for the AI service."""

from __future__ import annotations

from pathlib import Path

import psycopg


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _read_env_file(path: Path) -> dict[str, str]:
    """Parse simple KEY=value entries without loading or displaying secrets."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def _connect_read_only() -> psycopg.Connection:
    values = _read_env_file(PROJECT_ROOT / ".env")
    required = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
    if any(not values.get(key) for key in required):
        raise RuntimeError("Database settings are missing from the project .env file.")
    return psycopg.connect(
        dbname=values["POSTGRES_DB"],
        user=values["POSTGRES_USER"],
        password=values["POSTGRES_PASSWORD"],
        host=values.get("POSTGRES_HOST", "localhost"),
        port=int(values.get("POSTGRES_PORT", "5432")),
        connect_timeout=2,
        options="-c default_transaction_read_only=on -c statement_timeout=2000",
    )


def get_layer_records() -> list[dict[str, object]]:
    """Return registered layer metadata and its recorded loaded row count."""
    with _connect_read_only() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """SELECT layer_key, source_layer, target_srid, loaded_row_count
                   FROM twinguard.dataset_catalog
                   ORDER BY layer_key"""
            )
            return [
                {
                    "layer_key": row[0],
                    "source_layer": row[1],
                    "target_srid": row[2],
                    "loaded_row_count": row[3],
                }
                for row in cursor.fetchall()
            ]
