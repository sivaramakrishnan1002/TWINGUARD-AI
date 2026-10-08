"""Verify manually downloaded Sentinel-1 ZIPs against a shortlist.

The verifier never extracts, edits, or deletes products. It appends a report to
the Sentinel folder's DOWNLOAD_LOG.txt when ZIP files are present.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import zipfile
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_products(path: Path) -> dict[str, float]:
    result: dict[str, float] = {}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            name = (row.get("product_name") or row.get("product_id") or "").strip()
            size = row.get("product_size_MB") or row.get("size_MB") or ""
            if name and size:
                result[name.removesuffix(".zip")] = float(size)
    return result


def verify(folder: Path, shortlist: Path, append_log: bool = True) -> int:
    zips = sorted(folder.rglob("*.zip"))
    if not zips:
        print(f"No .zip files found in {folder}")
        return 0
    products = load_products(shortlist)
    records = []
    failures = 0
    for path in zips:
        actual = path.stat().st_size
        digest = sha256(path)
        product = path.stem.removesuffix(".SAFE")
        match = product in products
        size_ok = False
        archive_ok = False
        contents_ok = False
        error = ""
        if match:
            expected = products[product] * 1_000_000
            size_ok = abs(actual - expected) / expected <= 0.01 if expected else False
        try:
            with zipfile.ZipFile(path) as archive:
                archive_ok = archive.testzip() is None
                names = archive.namelist()
                contents_ok = any(Path(n).name.lower() == "manifest.safe" for n in names) or any(
                    "/measurement/" in ("/" + n.lower()) and n.lower().endswith((".tif", ".tiff"))
                    for n in names
                )
        except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
            error = f"{type(exc).__name__}: {exc}"
        passed = match and size_ok and archive_ok and contents_ok
        failures += not passed
        records.append(
            f"Filename: {path.name}\nSize bytes: {actual}\nSHA-256: {digest}\n"
            f"Product name match: {match}\nSize within 1% of catalogue: {size_ok}\n"
            f"ZIP testzip: {'PASS' if archive_ok else 'FAIL'}\n"
            f"manifest.safe or measurement files present: {contents_ok}\n"
            f"Overall: {'PASS' if passed else 'FAIL'}\n"
            f"Downloaded manually by user from Copernicus Data Space Browser\n"
            f"Error: {error or 'None'}\n"
        )
        print(records[-1])
    if append_log:
        with (folder / "DOWNLOAD_LOG.txt").open("a", encoding="utf-8") as log:
            log.write("\n" + "\n".join(records))
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, default=Path("data/raw/satellite/sentinel1"))
    parser.add_argument("--shortlist", type=Path, default=Path("data/raw/satellite/sentinel1_shortlist.csv"))
    parser.add_argument("--no-log", action="store_true", help="Print results without appending a log")
    args = parser.parse_args()
    if not args.folder.is_dir():
        print(f"Folder does not exist: {args.folder}", file=sys.stderr)
        return 2
    if list(args.folder.glob("*.zip")) and not args.shortlist.is_file():
        print(f"Shortlist does not exist: {args.shortlist}", file=sys.stderr)
        return 2
    return verify(args.folder, args.shortlist, not args.no_log)


if __name__ == "__main__":
    raise SystemExit(main())
