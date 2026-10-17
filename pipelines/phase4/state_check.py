#!/usr/bin/env python
"""Read-only size/SHA-256 audit of data/raw against its download logs."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
SHA_RE = re.compile(r"^[0-9a-f]{64}$", re.I)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def log_records() -> list[dict]:
    records = []
    for log in RAW.rglob("DOWNLOAD_LOG.txt"):
        text = log.read_text(encoding="utf-8", errors="replace")
        parts = re.split(r"(?=^(?:File name|File):\s*)", text, flags=re.M)
        for part in parts:
            name = re.search(r"^(?:File name|File):\s*(.+?)\s*$", part, re.M | re.I)
            size = re.search(r"^(?:File size\s*\(bytes\)|Size(?:\s*\(bytes\)|\s+bytes)):\s*(\d+)",
                             part, re.M | re.I)
            digest = re.search(r"^SHA-256:\s*(\S+)", part, re.M | re.I)
            if name and (size or digest):
                records.append({"log": log, "name": name.group(1).strip(),
                                "size": int(size.group(1)) if size else None,
                                "sha256": digest.group(1).lower() if digest else ""})
    return records


def main() -> int:
    records = log_records()
    by_name: dict[str, list[dict]] = {}
    for record in records:
        by_name.setdefault(Path(record["name"].replace("/", "\\")).name.casefold(), []).append(record)
    files = [p for p in RAW.rglob("*") if p.is_file() and p.name.casefold() != "download_log.txt"]
    matched, absent, mismatch = [], [], []
    total = 0
    for path in sorted(files):
        size = path.stat().st_size
        total += size
        candidates = [r for r in by_name.get(path.name.casefold(), [])
                      if r["size"] is not None and SHA_RE.fullmatch(r["sha256"])]
        if not candidates:
            absent.append((path.relative_to(RAW).as_posix(), size))
            continue
        actual = sha256(path)
        if any(r["size"] == size and r["sha256"] == actual for r in candidates):
            matched.append(path)
        else:
            mismatch.append((path.relative_to(RAW).as_posix(), size, actual,
                             [(r["name"], r["size"], r["sha256"]) for r in candidates]))
    print(f"DATA_FILES={len(files)}; DATA_BYTES={total}; HASH_MATCH={len(matched)}; "
          f"NO_COMPARABLE_HASH={len(absent)}; MISMATCH={len(mismatch)}")
    for path, size in absent:
        print(f"NO_COMPARABLE_HASH\t{path}\t{size}")
    for row in mismatch:
        print(f"MISMATCH\t{row}")
    return 1 if mismatch else 0


if __name__ == "__main__":
    raise SystemExit(main())
