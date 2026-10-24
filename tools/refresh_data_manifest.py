"""Refresh only the database snapshot of docs/DATA_MANIFEST.csv.

No raw or derived data files are modified. Database credentials are read through
the project's .env parser and are never printed.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipelines.stage5.db_common import make_engine  # noqa: E402

SOURCE_ID = "stage5_data_manifest"
LOADER = "tools.refresh_data_manifest"


def refresh() -> tuple[int, str]:
    source = ROOT / "docs" / "DATA_MANIFEST.csv"
    payload = source.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    rows = list(csv.DictReader(payload.decode("utf-8-sig").splitlines()))
    if not rows:
        raise RuntimeError("Current project manifest is empty; refusing to replace the database snapshot")

    engine = make_engine()
    raw = engine.raw_connection()
    try:
        cur = raw.cursor()
        cur.execute("BEGIN")
        cur.execute(
            "SELECT source_sha256, loaded_row_count FROM twinguard.dataset_catalog "
            "WHERE layer_key=%s FOR UPDATE",
            (SOURCE_ID,),
        )
        catalogue = cur.fetchone()
        if catalogue is None:
            raise RuntimeError("Manifest catalogue row is missing; refusing to create a new source load")
        cur.execute("SELECT count(*) FROM twinguard.data_manifest WHERE source_id=%s", (SOURCE_ID,))
        old_count = cur.fetchone()[0]
        if old_count != catalogue[1]:
            raise RuntimeError(
                f"Existing manifest snapshot is inconsistent: table rows={old_count}, catalogue rows={catalogue[1]}"
            )
        if catalogue[0] == digest and old_count == len(rows):
            raw.rollback()
            return len(rows), digest

        cur.execute("DELETE FROM twinguard.data_manifest WHERE source_id=%s", (SOURCE_ID,))
        loaded_at = datetime.now(timezone.utc)
        with cur.copy(
            "COPY twinguard.data_manifest "
            "(manifest_key,row_data,source_id,source_sha256,loader,load_time) FROM STDIN"
        ) as copy:
            for index, row in enumerate(rows):
                key = "|".join(str(row.get(column, "")) for column in ("dataset", "filename", "sha256")) or str(index)
                copy.write_row((key, json.dumps(row, ensure_ascii=False), SOURCE_ID, digest, LOADER, loaded_at))
        cur.execute(
            "UPDATE twinguard.dataset_catalog SET source_path=%s, source_layer=%s, "
            "source_sha256=%s, loaded_row_count=%s, loaded_at=%s, caveat=%s "
            "WHERE layer_key=%s",
            (
                source.relative_to(ROOT).as_posix(), "DATA_MANIFEST.csv", digest,
                len(rows), loaded_at, "Current snapshot of docs/DATA_MANIFEST.csv; refreshed transactionally.",
                SOURCE_ID,
            ),
        )
        raw.commit()
        return len(rows), digest
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()
        engine.dispose()


if __name__ == "__main__":
    try:
        count, sha256 = refresh()
        print(f"manifest_rows={count}")
        print(f"source_sha256={sha256}")
        print("result=current docs/DATA_MANIFEST.csv snapshot verified")
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
