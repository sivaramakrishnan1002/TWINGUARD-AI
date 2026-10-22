"""Read-only audit of files under data/raw against DOWNLOAD_LOG.txt records."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
HEX = re.compile(r"^[0-9a-fA-F]{64}$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parse_log_text(text: str, log: Path) -> list[dict]:
    entries = []
    chunks = re.split(r"(?=File(?: name)?:\s*)", text)
    for chunk in chunks:
        m = re.search(r"^File(?: name)?:\s*(.+?)\s*$", chunk, re.M)
        if not m:
            continue
        name = m.group(1).strip()
        sm = re.search(
            r"^(?:File size \(bytes\)|Size \(bytes\)|Size bytes):\s*(\d+)",
            chunk, re.M | re.I,
        )
        hm = re.search(r"^SHA-256:\s*(\S+)", chunk, re.M | re.I)
        if sm or hm:
            entries.append({"log": log, "name": name, "size": int(sm.group(1)) if sm else None,
                            "sha": hm.group(1).lower() if hm else ""})
    return entries


def log_entries() -> list[dict]:
    entries = []
    for log in RAW.rglob("DOWNLOAD_LOG.txt"):
        text = log.read_text(encoding="utf-8", errors="replace")
        entries.extend(parse_log_text(text, log))
    return entries


def possible_paths(entry: dict) -> set[Path]:
    rawname = Path(entry["name"].replace("/", "\\"))
    candidates = {entry["log"].parent / rawname, RAW / rawname}
    return {p.resolve() for p in candidates}


def main() -> None:
    entries = log_entries()
    by_path: dict[Path, list[dict]] = {}
    for e in entries:
        for p in possible_paths(e):
            by_path.setdefault(p, []).append(e)
    files = [p for p in RAW.rglob("*") if p.is_file() and p.name.lower() != "download_log.txt"]
    entries_by_basename: dict[str, list[dict]] = {}
    for e in entries:
        entries_by_basename.setdefault(Path(e["name"].replace("/", "\\")).name.lower(), []).append(e)
    no_hash, mismatches, okay = [], [], []
    total = 0
    for path in sorted(files):
        size = path.stat().st_size
        total += size
        matched_entries = by_path.get(path.resolve(), [])
        if not matched_entries:
            # Some existing logs store just the original filename while the
            # actual download lives one resource folder deeper.
            matched_entries = entries_by_basename.get(path.name.lower(), [])
        records = [e for e in matched_entries if e["size"] and e["sha"] and HEX.match(e["sha"])]
        if not records:
            no_hash.append((path.relative_to(RAW).as_posix(), size))
            continue
        actual = sha256(path)
        good = [e for e in records if e["size"] == size and e["sha"] == actual]
        if good:
            okay.append(path)
        else:
            mismatches.append((path.relative_to(RAW).as_posix(), size, actual,
                               [(e["name"], e["size"], e["sha"]) for e in records]))
    print(f"DATA_FILES={len(files)}; DATA_BYTES={total}; HASH_MATCH={len(okay)}; NO_COMPARABLE_HASH={len(no_hash)}; MISMATCH={len(mismatches)}")
    print("NO_HASH")
    for p, s in no_hash:
        print(f"{p}\t{s}")
    print("MISMATCH")
    for item in mismatches:
        print(item)


if __name__ == "__main__":
    main()
