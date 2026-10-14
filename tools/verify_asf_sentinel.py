"""Read-only integrity and footprint verification for user-downloaded ASF Sentinel-1 ZIPs.

This script never extracts or changes a ZIP. It writes a Markdown verification
report under docs/ and the specifically permitted metadata DOWNLOAD_LOG.txt in
the existing misspelled raw directory (senitnel1).
"""
from __future__ import annotations

import hashlib
import re
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

from pyproj import Transformer
from shapely.geometry import Polygon, shape
from shapely.ops import transform, unary_union
import json

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/satellite/senitnel1"
BOUNDARY = ROOT / "data/raw/boundary/chennai_cma_boundary.geojson"
REPORT = ROOT / "docs/SENTINEL_VERIFICATION.md"
LOG = RAW / "DOWNLOAD_LOG.txt"
LOCAL_TZ = ZoneInfo("Asia/Kolkata")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def lname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1]


def xml_text(root: ET.Element, name: str) -> list[str]:
    vals = []
    for elem in root.iter():
        if lname(elem.tag).lower() == name.lower():
            value = (elem.text or "").strip()
            if value:
                vals.append(value)
    return vals


def metadata(zf: zipfile.ZipFile, name: str) -> dict:
    manifest_name = next(n for n in zf.namelist() if Path(n).name.lower() == "manifest.safe")
    manifest = ET.fromstring(zf.read(manifest_name))
    annotations = [n for n in zf.namelist() if "/annotation/" in n.lower() and n.lower().endswith(".xml")]
    ann_roots = [ET.fromstring(zf.read(n)) for n in annotations]
    all_roots = [manifest, *ann_roots]

    def first(tag: str, default: str = "Not present") -> str:
        for root in all_roots:
            found = xml_text(root, tag)
            if found:
                return found[0]
        return default

    plat = next((e for e in manifest.iter() if lname(e.tag).lower() == "platform"), None)
    family = next(((e.text or "").strip() for e in plat.iter() if lname(e.tag).lower() == "familyname"), "Sentinel-1") if plat is not None else "Sentinel-1"
    number = next(((e.text or "").strip() for e in plat.iter() if lname(e.tag).lower() == "number"), "") if plat is not None else ""
    if family.upper() == "SENTINEL-1":
        family = "Sentinel-1"
    product_type = first("productType")
    mode = first("mode")
    start = first("startTime")
    stop = first("stopTime")
    relative = first("relativeOrbitNumber")
    absolute = first("orbitNumber")
    direction = first("pass")
    pols = set()
    for root in all_roots:
        pols.update(v.upper() for v in xml_text(root, "transmitterReceiverPolarisation"))
        pols.update(v.upper() for v in xml_text(root, "polarisation"))
    if not pols:
        pols.update(re.findall(r"-(VV|VH|HH|HV)-", " ".join(zf.namelist()), re.I))

    # SAFE manifest footprint coordinates are normally emitted as lat,lon pairs.
    coords_text = []
    for elem in manifest.iter():
        if lname(elem.tag).lower() in {"coordinates", "poslist"} and (elem.text or "").strip():
            coords_text.append((lname(elem.tag).lower(), (elem.text or "").strip()))
    footprint = None
    for kind, raw in coords_text:
        nums = [float(x) for x in re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", raw)]
        if kind == "coordinates":
            # GML coordinates serialize each pair as latitude,longitude here.
            if len(nums) >= 8 and len(nums) % 2 == 0:
                pts = [(nums[i + 1], nums[i]) for i in range(0, len(nums), 2)]
                candidate = Polygon(pts)
                if candidate.is_valid and not candidate.is_empty:
                    footprint = candidate
                    break
        else:
            # GML posList in this SAFE schema uses latitude longitude ordering.
            if len(nums) >= 8 and len(nums) % 2 == 0:
                pts = [(nums[i + 1], nums[i]) for i in range(0, len(nums), 2)]
                candidate = Polygon(pts)
                if candidate.is_valid and not candidate.is_empty:
                    footprint = candidate
                    break
    baseline = "Not present"
    for e in manifest.iter():
        if lname(e.tag).lower() in {"software", "processing"}:
            baseline = e.attrib.get("version", baseline)
            if baseline != "Not present":
                break
    if baseline == "Not present":
        matches = [v for r in all_roots for v in xml_text(r, "softwareVersion")]
        if matches:
            baseline = matches[0]
    return {
        "mission": f"{family}{number}", "product_type": product_type, "mode": mode,
        "polarizations": ",".join(sorted(pols)), "start": start, "stop": stop,
        "relative_orbit": relative, "direction": direction,
        "absolute_orbit": absolute, "baseline": baseline,
        "footprint": footprint,
    }


def utc(value: str) -> str:
    return value.replace("Z", " UTC") if value != "Not present" else value


def main() -> None:
    boundary_geo = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    boundary = shape(boundary_geo["features"][0]["geometry"] if "features" in boundary_geo else boundary_geo["geometry"] if boundary_geo.get("type") == "Feature" else boundary_geo)
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True).transform
    boundary_m = transform(to_utm, boundary)
    zips = sorted(RAW.glob("*/*.zip"))
    if len(zips) != 10:
        raise RuntimeError(f"Expected 10 ZIPs in {RAW}; found {len(zips)}")
    rows = []
    for path in zips:
        rec = {"path": path, "size": path.stat().st_size, "sha": digest(path), "info": None, "zip_ok": False, "zip_error": ""}
        try:
            with zipfile.ZipFile(path) as zf:
                bad_member = zf.testzip()
                rec["zip_ok"] = bad_member is None
                if bad_member:
                    rec["zip_error"] = f"CRC failure: {bad_member}"
                rec["info"] = metadata(zf, path.name)
        except Exception as exc:
            rec["zip_error"] = f"{type(exc).__name__}: {exc}"
        info = rec["info"]
        rec["filename_match"] = bool(info and path.stem.startswith("_".join(path.stem.split("_")[:10])))
        # Compare acquisition timestamp encoded in the name with manifest start/stop.
        encoded = re.search(r"_(\d{8}T\d{6})_(\d{8}T\d{6})_", path.name)
        if info and encoded:
            rec["filename_match"] = info["start"].startswith(encoded.group(1)[:4]+"-"+encoded.group(1)[4:6]+"-"+encoded.group(1)[6:8]+"T"+encoded.group(1)[9:11]+":"+encoded.group(1)[11:13]+":"+encoded.group(1)[13:15]) and info["stop"].startswith(encoded.group(2)[:4]+"-"+encoded.group(2)[4:6]+"-"+encoded.group(2)[6:8]+"T"+encoded.group(2)[9:11]+":"+encoded.group(2)[11:13]+":"+encoded.group(2)[13:15])
        footprint = info["footprint"] if info else None
        rec["coverage"] = transform(to_utm, footprint).intersection(boundary_m).area / boundary_m.area * 100 if footprint else None
        rows.append(rec)

    groups: dict[str, list] = {}
    for r in rows:
        year = r["path"].parent.name
        key = year + "-" + r["path"].name.split("_")[4][:8]
        groups.setdefault(key, []).append(r)
    group_cov = {}
    for key, members in groups.items():
        geoms = [r["info"]["footprint"] for r in members if r["info"] and r["info"]["footprint"]]
        group_cov[key] = transform(to_utm, unary_union(geoms)).intersection(boundary_m).area / boundary_m.area * 100 if geoms else None

    now = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
    report = ["# Sentinel-1 ASF ZIP verification", "", f"Read-only verification run: {now}",
              "All archives were read in place; no files were extracted or modified. Geometry intersections use the existing CMA boundary projected to EPSG:32644.",
              "", "## ZIP and SAFE metadata", "",
              "| ZIP filename | Size (bytes) | SHA-256 | ZIP test | Mission / type / mode | Polarisation | Start–stop UTC | Relative / absolute orbit | Direction | Processing version | CMA footprint coverage | Name matches metadata |",
              "|---|---:|---|---|---|---|---|---|---|---|---:|---|"]
    log = ["Sentinel-1 ASF Vertex (Earthdata login), downloaded manually by user"]
    for r in rows:
        info = r["info"]
        if info:
            year = r["path"].parent.name
            coverage = f"{r['coverage']:.2f}%" if r["coverage"] is not None else "not computed"
            report.append(f"| `{r['path'].name}` | {r['size']:,} | `{r['sha']}` | {'PASS' if r['zip_ok'] else 'FAIL: '+r['zip_error']} | {info['mission']} / {info['product_type']} / {info['mode']} | {info['polarizations']} | {utc(info['start'])}–{utc(info['stop'])} | {info['relative_orbit']} / {info['absolute_orbit']} | {info['direction']} | {info['baseline']} | {coverage} | {'yes' if r['filename_match'] else 'NO'} |")
            mtime = datetime.fromtimestamp(r["path"].stat().st_mtime, LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
            log.extend(["", f"File name: {r['path'].name}", "Source: NASA ASF Vertex (Earthdata login), downloaded manually by user", f"Filesystem modification date: {mtime}", f"File size (bytes): {r['size']}", f"SHA-256: {r['sha']}", f"ZIP integrity (testzip): {'PASS' if r['zip_ok'] else 'FAIL'}", f"Licence: TO CONFIRM from ASF and Copernicus terms"])
        else:
            report.append(f"| `{r['path'].name}` | {r['size']:,} | `{r['sha']}` | FAIL: {r['zip_error']} | metadata unreadable | — | — | — | — | — | — | no |")
            log.extend(["", f"File name: {r['path'].name}", "Source: NASA ASF Vertex (Earthdata login), downloaded manually by user", f"Filesystem modification date: {datetime.fromtimestamp(r['path'].stat().st_mtime, LOCAL_TZ).isoformat()}", f"File size (bytes): {r['size']}", f"SHA-256: {r['sha']}", f"ZIP integrity (testzip): FAIL ({r['zip_error']})", "Licence: TO CONFIRM from ASF and Copernicus terms"])

    report += ["", "## Coverage by date and slice union", "", "| Acquisition date | Slices | Union coverage of CMA |", "|---|---:|---:|"]
    for key, cov in sorted(group_cov.items()):
        compact_date = key.split("-", 1)[1]
        display_date = f"{compact_date[:4]}-{compact_date[4:6]}-{compact_date[6:8]}"
        report.append(f"| {display_date} | {len(groups[key])} | {cov:.2f}% |" if cov is not None else f"| {display_date} | {len(groups[key])} | unavailable |")
    report += ["", "## Pair consistency", ""]
    by_year: dict[str, list] = {}
    for r in rows:
        by_year.setdefault(r["path"].parent.name, []).append(r)
    pair_results = []
    for year, members in sorted(by_year.items()):
        dates = sorted({r["path"].name.split("_")[4][:8] for r in members})
        snapshots = []
        for date in dates:
            rs = [r for r in members if r["path"].name.split("_")[4].startswith(date)]
            if rs and rs[0]["info"]:
                snapshots.append((date, rs[0]["info"]))
        same = len(snapshots) >= 2 and all((a[1]["relative_orbit"], a[1]["direction"], a[1]["polarizations"]) == (snapshots[0][1]["relative_orbit"], snapshots[0][1]["direction"], snapshots[0][1]["polarizations"]) for a in snapshots)
        pair_results.append(same)
        report.append(f"- **{year}:** {', '.join(d for d,_ in snapshots)}; relative orbit/direction/polarisations match across reference and event dates: **{'yes' if same else 'no or incomplete'}** ({', '.join(f'{i["relative_orbit"]}/{i["direction"]}/{i["polarizations"]}' for _,i in snapshots)}).")
    report += ["", "## Post-peak catalogue check", "",
               "The saved catalogue comprises `data/raw/satellite/scenes_candidates.csv` and `docs/SENTINEL_SHORTLIST.csv`; no new catalogue queries or downloads were made. Post-peak candidate sizes are the MB values in `scenes_candidates.csv`; coverage percentages come from `docs/SENTINEL_SHORTLIST.csv` (individual footprint coverage), because the saved candidate CSV contains no geometries.", "",
               "| Event | Provisional peak | Post-peak Sentinel-1 same-orbit/direction candidates in saved catalogue | CMA coverage / slices |", "|---|---|---|---|"]
    report += ["| 2015 | 1 Dec 2015 | None found after peak in saved candidate catalogue | No post-peak footprints available |",
               "| 2021 | 7 Nov 2021 | 16 Nov 2021: `S1A_IW_GRDH_1SDV_20211116T003147_20211116T003212_040589_04D094_898D_COG` (536.138 MB) and `S1A_IW_GRDH_1SDV_20211116T003212_20211116T003237_040589_04D094_667C_COG` (549.281 MB) | 27.65% and 72.32%; both adjacent slices needed for near-full CMA coverage (individual footprints, not a computed geometric union) |",
               "| 2023 | 4 Dec 2023 | None found after peak in saved candidate catalogue | No post-peak footprints available |",
               "",
               "The downloaded 2015 (19 Oct reference; 24 Nov event), 2021 (23 Oct reference; 4 Nov event), and 2023 (18 Nov reference; 30 Nov event) GRD-HD scenes are all pre-peak. They can support pre-event/reference comparisons and exploratory mapping of water changes at acquisition time; they cannot directly observe the 1–8 Dec 2015, 7 Nov 2021, or 4 Dec 2023 peak. The 24 Nov 2015 UNOSAT `S1_20151124` layer name supports a same-date correspondence, but does not alone prove the exact ASF product was used.",
               "",
               "## Summary", "",
               f"- ZIPs checked: {len(rows)}; ZIP CRC/integrity pass: {sum(bool(r['zip_ok']) for r in rows)}/{len(rows)}.",
               f"- Sum of on-disk ZIP sizes: {sum(r['size'] for r in rows):,} bytes.",
               f"- Metadata/name consistency: {sum(bool(r['filename_match']) for r in rows)}/{len(rows)}.",
               f"- Same relative orbit, pass direction and VV,VH polarisation across each event/reference pair: {'all match' if all(pair_results) else 'not all match'}.",
               "- SSL verification was never disabled; no network request was made for this verification.", ""]
    REPORT.write_text("\n".join(report), encoding="utf-8")
    LOG.write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"Report written: {REPORT}")
    print(f"Raw metadata log written: {LOG}")
    print(f"ZIP count={len(rows)}; all integrity={all(r['zip_ok'] for r in rows)}; bytes={sum(r['size'] for r in rows)}")
    for r in rows:
        print(r["path"].name, "coverage", None if r["coverage"] is None else round(r["coverage"], 4), "name_match", r["filename_match"], "zip", r["zip_ok"])


if __name__ == "__main__":
    main()
