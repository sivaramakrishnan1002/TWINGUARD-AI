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
    """Return catalogued metadata; unavailable fields remain explicitly null/empty."""
    with _connect_read_only() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """SELECT layer_key, source_layer, source_crs, target_srid,
                          loaded_row_count, source_sha256, source_url,
                          source_vintage, licence_note
                   FROM twinguard.dataset_catalog
                   ORDER BY layer_key"""
            )
            return [
                _layer_payload(row)
                for row in cursor.fetchall()
            ]


def _layer_payload(row: tuple) -> dict[str, object]:
    layer_key, source_layer, source_crs, target_srid, row_count, digest, url, vintage, licence = row
    normalized = str(source_layer).lower()
    units: dict[str, str] = {}
    if normalized in {"road_edges", "roads"}:
        units = {"length_m": "m", "speed_kmh": "km/h", "travel_time_min": "min"}
    elif normalized in {"reservoir_observations", "reservoir_levels"}:
        units = {"storage_value": "mcft"}
    # Migration 002 defines MVT functions for these named layer families with
    # z in [0, 22]. It does not expose an HTTP tile endpoint.
    tile_families = {"study_area", "roads", "road_edges", "facilities", "waterways", "flood_references"}
    has_mvt_function = normalized in tile_families
    return {
        "layer_key": layer_key,
        "source_layer": source_layer,
        "source_crs": source_crs,
        "target_srid": target_srid,
        "loaded_row_count": row_count,
        "units": units,
        "zoom": {"min": 0, "max": 22} if has_mvt_function else None,
        "attribution": licence,
        "vintage": vintage,
        "provenance": {
            "source_sha256": digest,
            "source_url": url,
        },
        "nodata": "not_declared_in_catalogue",
        "tile_endpoint_available": False,
    }
