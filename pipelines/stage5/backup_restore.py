"""Create a temporary logical backup and verify archive plus restore capability.

The app role may lack CREATEDB. In that case this script records that the
requested temporary-database restore could not be run, and performs a separate
schema-only restore smoke test into a temporary schema in the configured DB.
The temporary schema is always dropped; no database other than twinguard is
used unless this script itself successfully creates its named temporary DB.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import psycopg

from db_common import ROOT, read_env

BIN = Path(r"C:\Program Files\PostgreSQL\18\bin")


def find_tool(name: str) -> str:
    return shutil.which(name) or str(BIN / f"{name}.exe")


def _run(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, env=env, capture_output=True, text=True, check=False)


def run_backup_restore_test() -> dict[str, str | int | bool]:
    values = read_env()
    child_env = os.environ.copy()
    child_env["PGPASSWORD"] = values["POSTGRES_PASSWORD"]
    host = values.get("POSTGRES_HOST") or "localhost"
    port = values.get("POSTGRES_PORT") or "5432"
    db = values["POSTGRES_DB"]
    user = values["POSTGRES_USER"]
    createdb = False
    report: dict[str, str | int | bool] = {}
    temp_db = "twinguard_restore_test_" + uuid.uuid4().hex[:8]
    temp_schema = "twinguard_restore_test_" + uuid.uuid4().hex[:8]
    with tempfile.TemporaryDirectory(prefix="twinguard_stage56_") as work:
        archive = Path(work) / "twinguard.dump"
        dump_args = [find_tool("pg_dump"), "--host", host, "--port", port,
                     "--username", user, "--dbname", db, "--format=custom",
                     "--no-owner", "--no-privileges", "--schema=twinguard",
                     "--file", str(archive)]
        result = _run(dump_args, child_env)
        if result.returncode:
            err = (result.stderr or result.stdout).strip().replace(values["POSTGRES_PASSWORD"], "[REDACTED]")
            raise RuntimeError("pg_dump failed: " + err)
        report["backup_bytes"] = archive.stat().st_size
        report["backup_sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
        listing = _run([find_tool("pg_restore"), "--list", str(archive)], child_env)
        if listing.returncode:
            raise RuntimeError("pg_restore --list failed: " + listing.stderr.strip())
        report["archive_toc_entries"] = sum(1 for line in listing.stdout.splitlines() if line.strip() and not line.startswith(";") )
        report["archive_verified"] = True

        try:
            control = psycopg.connect(host=host, port=int(port), dbname="postgres",
                                      user=user, password=values["POSTGRES_PASSWORD"],
                                      connect_timeout=5, autocommit=True)
            try:
                # Clone the configured DB so the temporary DB has the same PostGIS
                # extension installed. The project schema is removed before restore.
                control.execute(f'CREATE DATABASE "{temp_db}" TEMPLATE "{db}"')
                createdb = True
                report["temporary_database_created"] = True
            finally:
                control.close()
        except Exception as exc:
            report["temporary_database_created"] = False
            report["temporary_database_error"] = type(exc).__name__ + ": " + str(exc).splitlines()[0]
        if createdb:
            try:
                temp_conn = psycopg.connect(
                    host=host, port=int(port), dbname=temp_db, user=user,
                    password=values["POSTGRES_PASSWORD"], connect_timeout=5,
                    autocommit=True,
                )
                try:
                    temp_conn.execute('DROP SCHEMA IF EXISTS "twinguard" CASCADE')
                finally:
                    temp_conn.close()
                restore = _run([find_tool("pg_restore"), "--exit-on-error", "--host", host,
                                "--port", port, "--username", user, "--dbname", temp_db,
                                "--no-owner", "--no-privileges", str(archive)], child_env)
                if restore.returncode:
                    err = (restore.stderr or restore.stdout).strip().replace(values["POSTGRES_PASSWORD"], "[REDACTED]")
                    report["database_restore_error"] = err.splitlines()[0] if err else "pg_restore returned a nonzero exit code"
                else:
                    report["database_restore_succeeded"] = True
                    tables = (
                        "study_area", "road_edges", "facilities", "waterways",
                        "flood_references", "dataset_catalog", "schema_migrations",
                    )
                    source_conn = psycopg.connect(
                        host=host, port=int(port), dbname=db, user=user,
                        password=values["POSTGRES_PASSWORD"], connect_timeout=5,
                    )
                    restored_conn = psycopg.connect(
                        host=host, port=int(port), dbname=temp_db, user=user,
                        password=values["POSTGRES_PASSWORD"], connect_timeout=5,
                    )
                    try:
                        counts = {}
                        for table in tables:
                            source_count = source_conn.execute(
                                f'SELECT count(*) FROM twinguard."{table}"'
                            ).fetchone()[0]
                            restored_count = restored_conn.execute(
                                f'SELECT count(*) FROM twinguard."{table}"'
                            ).fetchone()[0]
                            counts[table] = {"source": source_count, "restored": restored_count}
                        report["restored_table_counts"] = counts
                        report["restore_row_counts_verified"] = all(
                            pair["source"] == pair["restored"] for pair in counts.values()
                        )
                    finally:
                        restored_conn.close()
                        source_conn.close()
            finally:
                drop_conn = psycopg.connect(host=host, port=int(port), dbname="postgres", user=user,
                                            password=values["POSTGRES_PASSWORD"], autocommit=True)
                try:
                    drop_conn.execute(f'DROP DATABASE IF EXISTS "{temp_db}" WITH (FORCE)')
                finally:
                    drop_conn.close()
                report["temporary_database_dropped"] = True
        if not createdb:
            schema_dump = Path(work) / "twinguard_schema.sql"
            result = _run([find_tool("pg_dump"), "--host", host, "--port", port,
                           "--username", user, "--dbname", db, "--format=plain",
                           "--schema-only", "--no-owner", "--no-privileges",
                           "--schema=twinguard", "--file", str(schema_dump)], child_env)
            if result.returncode:
                err = (result.stderr or result.stdout).strip().replace(values["POSTGRES_PASSWORD"], "[REDACTED]")
                raise RuntimeError("schema-only pg_dump failed: " + err)
            sql = schema_dump.read_text(encoding="utf-8")
            sql = re.sub(r"(?<![A-Za-z0-9_])twinguard(?![A-Za-z0-9_])", temp_schema, sql)
            schema_dump.write_text(sql, encoding="utf-8")
            try:
                restored = _run([find_tool("psql"), "--host", host, "--port", port,
                                 "--username", user, "--dbname", db, "-X", "-v",
                                 "ON_ERROR_STOP=1", "--file", str(schema_dump)], child_env)
                if restored.returncode:
                    err = (restored.stderr or restored.stdout).strip().replace(values["POSTGRES_PASSWORD"], "[REDACTED]")
                    report["schema_restore_error"] = err
                else:
                    report["temporary_schema_restore_succeeded"] = True
                    count_conn = psycopg.connect(host=host, port=int(port), dbname=db, user=user,
                                                 password=values["POSTGRES_PASSWORD"], connect_timeout=5)
                    try:
                        count = count_conn.execute(
                            "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                            "WHERE n.nspname=%s AND c.relkind IN ('r','p','v','m','f')",
                            (temp_schema,),
                        ).fetchone()[0]
                        report["restored_schema_relation_count"] = count
                    finally:
                        count_conn.close()
            finally:
                drop = psycopg.connect(host=host, port=int(port), dbname=db, user=user,
                                       password=values["POSTGRES_PASSWORD"], autocommit=True)
                try:
                    drop.execute(f'DROP SCHEMA IF EXISTS "{temp_schema}" CASCADE')
                finally:
                    drop.close()
                report["temporary_schema_dropped"] = True
    return report


if __name__ == "__main__":
    import json
    print(json.dumps(run_backup_restore_test(), indent=2))
