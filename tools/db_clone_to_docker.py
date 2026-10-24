"""Clone the local TwinGuard schema into the project's Docker PostGIS database.

The backup is a timestamped custom-format archive under the git-ignored
``backups/`` directory. The target must not already contain the twinguard
schema, so repeated runs cannot silently overwrite a prior Docker database.
Credentials are read with the project's simple .env parser and never emitted.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipelines.stage5.db_common import read_env  # noqa: E402

PG_BIN = Path(r"C:\Program Files\PostgreSQL\18\bin")


def find_tool(name: str) -> str:
    return shutil.which(name) or str(PG_BIN / f"{name}.exe")


def run_tool(name: str, args: list[str], env: dict[str, str]) -> float:
    start = time.perf_counter()
    result = subprocess.run(
        [find_tool(name), *args], env=env, capture_output=True, text=True,
        check=False,
    )
    elapsed = time.perf_counter() - start
    if result.returncode:
        # Avoid exposing endpoint details, usernames, or passwords from client
        # diagnostics. The command and exit status are enough to locate failure.
        raise RuntimeError(
            f"{name} failed with exit code {result.returncode} after {elapsed:.3f}s; "
            "client diagnostics withheld"
        )
    return elapsed


def connect(host: str, port: int, db: str, user: str, password: str):
    return psycopg.connect(
        host=host, port=port, dbname=db, user=user, password=password,
        connect_timeout=10,
    )


def table_counts(conn) -> dict[str, int]:
    names = conn.execute(
        "SELECT c.relname FROM pg_class c "
        "JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname='twinguard' AND c.relkind IN ('r','p') "
        "ORDER BY c.relname"
    ).fetchall()
    counts: dict[str, int] = {}
    for (name,) in names:
        stmt = sql.SQL("SELECT count(*) FROM {}.{}").format(
            sql.Identifier("twinguard"), sql.Identifier(name)
        )
        counts[name] = conn.execute(stmt).fetchone()[0]
    return counts


def geometry_checks(conn) -> dict[str, dict[str, int]]:
    cols = conn.execute(
        "SELECT f_table_name, f_geometry_column, srid FROM geometry_columns "
        "WHERE f_table_schema='twinguard' ORDER BY f_table_name, f_geometry_column"
    ).fetchall()
    result: dict[str, dict[str, int]] = {}
    for table, column, expected_srid in cols:
        q = sql.SQL(
            "SELECT count(*) FILTER (WHERE {g} IS NOT NULL), "
            "count(*) FILTER (WHERE {g} IS NOT NULL AND NOT ST_IsValid({g})), "
            "count(*) FILTER (WHERE {g} IS NOT NULL AND ST_SRID({g}) <> %s) "
            "FROM {schema}.{table}"
        ).format(
            g=sql.Identifier(column), schema=sql.Identifier("twinguard"),
            table=sql.Identifier(table),
        )
        nonnull, invalid, srid_mismatch = conn.execute(q, (expected_srid,)).fetchone()
        result[f"{table}.{column}"] = {
            "non_null": nonnull,
            "invalid": invalid,
            "srid_mismatch": srid_mismatch,
        }
    return result


def main() -> int:
    started = time.perf_counter()
    cfg = read_env()
    local_host = cfg.get("POSTGRES_HOST") or "localhost"
    local_port = int(cfg.get("POSTGRES_PORT") or "5432")
    docker_port = int(cfg.get("DOCKER_POSTGRES_HOST_PORT") or "5433")
    database = cfg["POSTGRES_DB"]
    user = cfg["POSTGRES_USER"]
    password = cfg["POSTGRES_PASSWORD"]

    backups = ROOT / "backups"
    backups.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = backups / f"twinguard_{stamp}.dump"
    if archive.exists():
        raise RuntimeError("Refusing to overwrite an existing backup archive")

    child_env = os.environ.copy()
    child_env["PGPASSWORD"] = password
    dump_seconds = run_tool(
        "pg_dump",
        ["--host", local_host, "--port", str(local_port), "--username", user,
         "--dbname", database, "--format=custom", "--no-owner",
         "--no-privileges", "--schema=twinguard", "--file", str(archive)],
        child_env,
    )

    # The target database is project-owned, but never replace existing tables.
    with connect("127.0.0.1", docker_port, database, user, password) as target:
        present = target.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname='twinguard')"
        ).fetchone()[0]
        if present:
            raise RuntimeError(
                "Docker target already has the twinguard schema; refusing to overwrite it"
            )

    try:
        restore_seconds = run_tool(
            "pg_restore",
            ["--exit-on-error", "--host", "127.0.0.1", "--port", str(docker_port),
             "--username", user, "--dbname", database, "--no-owner",
             "--no-privileges", str(archive)],
            child_env,
        )
    except RuntimeError as exc:
        # Restore may fail after creating some objects. Because the target schema
        # was confirmed absent immediately beforehand, remove only this partial
        # restore when the Docker database is reachable; leave the dump intact.
        try:
            with connect("127.0.0.1", docker_port, database, user, password) as target:
                target.execute('DROP SCHEMA IF EXISTS "twinguard" CASCADE')
        except Exception:
            pass
        raise RuntimeError(f"{exc}; dump_seconds={dump_seconds:.3f}") from None

    with connect(local_host, local_port, database, user, password) as source, \
            connect("127.0.0.1", docker_port, database, user, password) as target:
        source_counts = table_counts(source)
        target_counts = table_counts(target)
        if source_counts != target_counts:
            missing = sorted(set(source_counts) - set(target_counts))
            extra = sorted(set(target_counts) - set(source_counts))
            mismatched = {
                name: {"local": source_counts[name], "docker": target_counts[name]}
                for name in sorted(set(source_counts) & set(target_counts))
                if source_counts[name] != target_counts[name]
            }
            raise RuntimeError(
                f"Table-count comparison failed; missing={missing}, extra={extra}, mismatched={mismatched}"
            )
        source_geometry = geometry_checks(source)
        target_geometry = geometry_checks(target)
        if source_geometry != target_geometry:
            raise RuntimeError("PostGIS validity/SRID checks differ between local and Docker databases")

    if any(item["invalid"] or item["srid_mismatch"] for item in target_geometry.values()):
        raise RuntimeError("PostGIS check found invalid geometries or SRID mismatches")

    print(f"backup_file={archive.relative_to(ROOT)}")
    print(f"backup_bytes={archive.stat().st_size}")
    print(f"dump_seconds={dump_seconds:.3f}")
    print(f"restore_seconds={restore_seconds:.3f}")
    print("table_counts (all local counts matched Docker):")
    for name, count in source_counts.items():
        print(f"  {name}: {count}")
    print(f"geometry_columns_checked={len(target_geometry)}")
    print("postgis_validity_srid_checks=all matched; invalid=0; srid_mismatch=0")
    print(f"total_seconds={time.perf_counter() - started:.3f}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Do not echo database exceptions; they may contain endpoint details.
        msg = (
            "database client details withheld"
            if isinstance(exc, psycopg.Error)
            else str(exc)
        )
        print(f"ERROR: {type(exc).__name__}: {msg}", file=sys.stderr)
        raise SystemExit(1)
