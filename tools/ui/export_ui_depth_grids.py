"""Export saved A05 depth rasters into compact JSON files for the product UI.

Read-only on project data. Writes only to frontend/src/ui/evidence/generated/
(git-ignored): one file per A05 event window, holding every saved
scenario x lead x band (p05/p50/p95) grid as base64 little-endian uint16
millimetres, with 65535 for NoData (outside the assessed CMA; not dry).

The values are the saved DERIVED hindcast scenarios exactly as stored
(rounded to 1 mm). Nothing is interpolated, resampled or re-modelled.

Run from the repository root:
    .venv\\Scripts\\python.exe tools\\ui\\export_ui_depth_grids.py
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/features/forecast/batch2_v1"
SUMMARY = SOURCE / "forecast_summary.json"
OUT = ROOT / "frontend/src/ui/evidence/generated"

EVENTS = {
    "2015-12-02": "2015-11-30T00:00:00Z",
    "2021-11-13": "2021-11-11T00:00:00Z",
    "2023-12-04": "2023-12-02T00:00:00Z",
}
SCENARIOS = ["perfect_foresight_imerg", "rain_error_q10", "rain_error_q50", "rain_error_q90", "persistence_previous_day"]
LEADS = [6, 12, 24, 48, 72]
BANDS = ["p05", "p50", "p95"]
NODATA = -9999.0
NODATA_CODE = 65535
CELL_KM2 = 0.36  # 600 m x 600 m


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode(values: np.ndarray, valid: np.ndarray) -> str:
    mm = np.full(values.shape, NODATA_CODE, dtype="<u2")
    mm[valid] = np.clip(np.rint(values[valid] * 1000.0), 0, NODATA_CODE - 1).astype("<u2")
    return base64.b64encode(mm.tobytes()).decode("ascii")


def main() -> None:
    if not SOURCE.is_dir():
        raise SystemExit(f"Saved A05 rasters not found at {SOURCE}; nothing exported.")
    OUT.mkdir(parents=True, exist_ok=True)
    summary_sha = sha256(SUMMARY) if SUMMARY.exists() else None
    for event_id, window_start in EVENTS.items():
        start = datetime.fromisoformat(window_start.replace("Z", "+00:00"))
        scenarios: dict[str, object] = {}
        grid_meta = None
        for scenario in SCENARIOS:
            leads: dict[str, object] = {}
            for lead in LEADS:
                entry: dict[str, object] = {
                    "valid_time_utc": (start + timedelta(hours=lead)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
                for band in BANDS:
                    path = SOURCE / event_id / scenario / f"depth_lead{lead:02d}h_{band}_DERIVED.tif"
                    with rasterio.open(path) as raster:
                        values = raster.read(1)
                        if raster.nodata != NODATA:
                            raise SystemExit(f"Unexpected NoData value in {path}")
                        if grid_meta is None:
                            grid_meta = {
                                "width": raster.width,
                                "height": raster.height,
                                "cell_size_m": 600,
                                "crs": str(raster.crs),
                                "transform": list(raster.transform)[:6],
                            }
                    valid = values != NODATA
                    entry[band] = encode(values, valid)
                    entry[f"{band}_sha256"] = sha256(path)
                    if band == "p50":
                        v = values[valid]
                        entry["stats_p50"] = {
                            "valid_cells": int(valid.sum()),
                            "nodata_cells": int((~valid).sum()),
                            "max_m": round(float(v.max()), 3),
                            "mean_m": round(float(v.mean()), 4),
                            "area_ge_0_10_km2": round(float((v >= 0.10).sum() * CELL_KM2), 2),
                            "area_ge_0_30_km2": round(float((v >= 0.30).sum() * CELL_KM2), 2),
                        }
                leads[str(lead)] = entry
            scenarios[scenario] = {"leads": leads}
        payload = {
            "schema": "twinguard.ui.a05_depth_grids.v1",
            "status": "DERIVED_HINDCAST_SCENARIOS_NOT_FORECAST_SKILL",
            "event_id": event_id,
            "window_start_utc": window_start,
            "grid": grid_meta,
            "encoding": "base64 little-endian uint16 depth in millimetres; 65535 = NoData (outside assessed CMA; not dry)",
            "band_semantics": "per-cell p05/p50/p95 across 20 A06 parameter members; parameter spread, not calibrated confidence",
            "source": {"path": "data/features/forecast/batch2_v1/", "forecast_summary_sha256": summary_sha, "report": "docs/PHASE11_FORECAST_BATCH2.md"},
            "scenarios": scenarios,
        }
        target = OUT / f"a05_{event_id}.json"
        target.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        print(f"wrote {target.relative_to(ROOT)} ({target.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
