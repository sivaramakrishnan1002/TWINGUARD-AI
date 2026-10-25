"""Read-only GeoPDF inspection and native embedded-image extraction."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
from typing import Any

from pypdf import PdfReader


DEFAULT_PDFS = [
    Path("data/raw/historical_floods/2021/ChennaiCity-ChennaiCorporationTaluk-4.pdf"),
    Path("data/raw/historical_floods/2023/tncyclone50dsc07122023_0600hrs_map.pdf"),
]


def _resolve(value: Any) -> Any:
    try:
        return value.get_object()
    except AttributeError:
        return value


def _viewport(vp: Any) -> dict[str, Any]:
    obj = _resolve(vp)
    measure = _resolve(obj.get("/Measure", {}))
    gcs = _resolve(measure.get("/GCS", {}))
    return {
        "name": str(obj.get("/Name", "")),
        "bbox_pdf_points": [float(x) for x in obj.get("/BBox", [])],
        "measure_subtype": str(measure.get("/Subtype", "")),
        "gpts_lat_lon": [float(x) for x in measure.get("/GPTS", [])],
        "lpts": [float(x) for x in measure.get("/LPTS", [])],
        "gcs_type": str(gcs.get("/Type", "")),
        "gcs_wkt_prefix": str(gcs.get("/WKT", ""))[:180],
    }


def inspect_pdf(root: Path, relative: Path, image_root: Path) -> dict[str, Any]:
    src = root / relative
    if not src.is_file():
        return {"source": relative.as_posix(), "status": "absent"}
    reader = PdfReader(src, strict=True)
    pages = []
    for page_no, page in enumerate(reader.pages, 1):
        vps = [_viewport(vp) for vp in (_resolve(page.get("/VP", [])) or [])]
        images = []
        for img in page.images:
            image = img.image
            name = Path(img.name).name
            out_dir = image_root / src.stem
            out_dir.mkdir(parents=True, exist_ok=True)
            target = out_dir / f"page{page_no:03d}_{name}"
            # PNG keeps the extracted decoded native pixels losslessly, even where the PDF
            # embedded object uses JPEG compression. Preserve the original dimensions.
            if target.suffix.lower() not in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
                target = target.with_suffix(".png")
            buffer = io.BytesIO()
            if target.suffix.lower() == ".png":
                image.save(buffer, format="PNG")
            elif target.suffix.lower() in {".jpg", ".jpeg"}:
                image.save(buffer, format="JPEG", quality=100, subsampling=0)
            else:
                image.save(buffer, format="TIFF")
            encoded = buffer.getvalue()
            if target.exists():
                if hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(encoded).digest():
                    raise FileExistsError(f"refusing to overwrite non-matching extracted image: {target}")
            else:
                target.write_bytes(encoded)
            images.append({"name": img.name, "path": target.relative_to(root).as_posix(), "width_px": image.width, "height_px": image.height, "mode": image.mode, "size_bytes": target.stat().st_size, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
        text = page.extract_text() or ""
        # Report possible graticule labels from selectable vector text, not OCR guesses.
        tokens = [line.strip() for line in text.splitlines() if any(ch in line.upper() for ch in ("LAT", "LON", "°", "N", "E")) and any(ch.isdigit() for ch in line)]
        pages.append({"page": page_no, "media_box_points": [float(x) for x in page.mediabox], "geospatial_viewports": vps, "embedded_images": images, "selectable_text_lines_with_coordinate_hints": tokens[:50], "legend_text_excerpt": [line.strip() for line in text.splitlines() if any(w in line.lower() for w in ("flood", "water", "inundat", "affected", "legend"))][:30], "text_excerpt": text[:2500]})
    return {"source": relative.as_posix(), "file_size_bytes": src.stat().st_size, "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest(), "pdf_metadata": {str(k): str(v) for k, v in (reader.metadata or {}).items()}, "page_count": len(reader.pages), "pages": pages, "geopdf_embedded_georeferencing": any(p["geospatial_viewports"] and any(v["measure_subtype"] == "/GEO" and len(v["gpts_lat_lon"]) >= 8 for v in p["geospatial_viewports"]) for p in pages)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    root = args.root.resolve()
    out_dir = root / "data/processed/pdf_maps/extracted_images"
    results = [inspect_pdf(root, p, out_dir) for p in DEFAULT_PDFS]
    dec = root / "data/raw/historical_floods/2015/december_maps"
    if dec.is_dir():
        present = sorted(p for p in dec.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")
        results.extend(inspect_pdf(root, p.relative_to(root), out_dir) for p in present)
    else:
        results.append({"source": "data/raw/historical_floods/2015/december_maps", "status": "folder absent; December maps not provided"})
    out_path = root / "docs/PDF_MAP_INSPECTION.json"
    encoded_json = json.dumps(results, indent=2, ensure_ascii=False)
    if out_path.exists():
        if out_path.read_text(encoding="utf-8") != encoded_json:
            raise FileExistsError(f"refusing to overwrite non-matching inspection report: {out_path}")
    else:
        out_path.write_text(encoded_json, encoding="utf-8")
    summary = [{"source": x["source"], "status": x.get("status", "inspected"), "pages": x.get("page_count"), "embedded_georeferencing": x.get("geopdf_embedded_georeferencing"), "image_count": sum(len(p["embedded_images"]) for p in x.get("pages", []))} for x in results]
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
