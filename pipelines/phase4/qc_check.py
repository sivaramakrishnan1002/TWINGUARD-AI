#!/usr/bin/env python
"""Create row-level QC flags and variable summaries without altering inputs."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data/features/events"
OUT = OUT_DIR / "qc_flags_v2.csv"
SUMMARY = OUT_DIR / "qc_summary_v2.json"
DOC = ROOT / "docs/QC_POLICY.md"
INPUTS = {
    "ERA5 hourly": ROOT / "data/features/weather/era5_event_hourly_features.csv",
    "ERA5 and NASA POWER daily": ROOT / "data/features/weather/daily_era5_nasa_power_comparison.csv",
    "Kaggle reservoir daily": ROOT / "data/features/reservoirs/kaggle_daily_storage_features.csv",
    "OpenCity lake monthly": ROOT / "data/features/reservoirs/opencity_monthly_storage_tidy.csv",
}
RANGES = {
    "precipitation": (0, None, "mm per source hour"),
    "temperature_2m": (-50, 60, "degrees C; broad screening interval, assumption"),
    "relative_humidity_2m": (0, 100, "%"),
    "wind_speed_10m": (0, 200, "km/h; broad screening interval, assumption; source metadata unit"),
    "pressure_msl": (800, 1100, "hPa; broad screening interval, assumption"),
    "storage_mcft": (0, None, "mcft; historical capacity not assumed"),
    "capacity_percent": (0, None, "percent of stated denominator; no historical upper bound assumed"),
}


def _frame(name: str, path: Path) -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(path)
    date_col = next((c for c in ("timestamp_utc", "date", "date_local") if c in df.columns), None)
    id_col = next((c for c in ("point_id", "reservoir", "lake", "source_file") if c in df.columns), None)
    value_columns = [c for c in df.select_dtypes(include=["number"]).columns]
    rows, summary = [], {"source": name, "path": path.relative_to(ROOT).as_posix(), "input_rows": len(df), "variables": {}}
    for col in value_columns:
        values = pd.to_numeric(df[col], errors="coerce")
        low, high, range_note = RANGES.get(col, (None, None, "no automatic numeric range assigned"))
        if col in {"era5_mean_mm", "nasa_power_mean_mm"}:
            low, high, range_note = 0, None, "mm/day; nonnegative screen, no upper cutoff"
        elif col.startswith("rain_mm_"):
            low, high, range_note = 0, None, "mm; nonnegative screen, no upper cutoff"
        missing = values.isna()
        nonfinite = values.notna() & ~np.isfinite(values)
        below = values.notna() & np.isfinite(values) & (values < low) if low is not None else pd.Series(False, index=df.index)
        above = values.notna() & np.isfinite(values) & (values > high) if high is not None else pd.Series(False, index=df.index)
        bad = nonfinite | below | above
        summary["variables"][col] = {
            "count": int(values.notna().sum()), "missing": int(missing.sum()),
            "nonfinite": int(nonfinite.sum()), "outside_screened_range": int(bad.sum()),
            "min": float(values[values.notna() & np.isfinite(values)].min()) if (values.notna() & np.isfinite(values)).any() else None,
            "max": float(values[values.notna() & np.isfinite(values)].max()) if (values.notna() & np.isfinite(values)).any() else None,
            "screen": range_note,
        }
        for idx in df.index:
            val = values.at[idx]
            rows.append({
                "source": name, "source_row": int(idx), "timestamp_or_date": str(df.at[idx, date_col]) if date_col else None,
                "source_id": str(df.at[idx, id_col]) if id_col else None, "variable": col,
                "value": float(val) if pd.notna(val) and np.isfinite(val) else None,
                "flag_missing": bool(missing.at[idx]), "flag_nonfinite": bool(nonfinite.at[idx]),
                "flag_outside_screened_range": bool(bad.at[idx]), "screen": range_note,
            })
    return pd.DataFrame(rows), summary


def main() -> int:
    existing = [str(p) for p in (OUT, SUMMARY) if p.exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite existing QC output(s): " + ", ".join(existing))
    missing = [p for p in INPUTS.values() if not p.is_file()]
    if missing:
        raise FileNotFoundError("Missing QC inputs: " + ", ".join(str(p) for p in missing))
    frames, summaries = [], []
    for name, path in INPUTS.items():
        frame, summary = _frame(name, path)
        frames.append(frame)
        summaries.append(summary)
    flags = pd.concat(frames, ignore_index=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    flags.to_csv(OUT, index=False)
    SUMMARY.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    report = """# Missing-data and outlier QC policy — Phase 4

This is a DERIVED screening report. Raw files and existing feature files were read only. Row-level flags are in `data/features/events/qc_flags.csv`; per-variable counts and ranges are in `data/features/events/qc_summary.json`.

## Rules

- Missing values stay missing. No variable was filled, interpolated, deleted, or clipped. A missingness flag is emitted for every numeric observation.
- Non-finite numbers are flagged separately. Broad physical screening intervals are applied only to ERA5 variables with known units: temperature −50 to 60 °C and wind speed 0 to 200 m/s are deliberately broad assumptions; relative humidity is screened at 0–100%; sea-level pressure at 800–1,100 hPa. Hourly precipitation must be nonnegative; no upper cut-off is imposed because extreme precipitation should not be silently rejected.
- Reservoir storage must be nonnegative, but no historical capacity upper bound is imposed. The recorded percent-of-capacity field is screened only for negative values because the denominator is a present-day capacity and historical capacity is not verified.
- Unmapped numeric variables are summarized but receive no invented range. Screened values are warnings for review, not automatic errors.
- IMERG units/daily support are described in `RAIN_SOURCES_COMPARISON.md`; the existing report records `mm/day` from product metadata. ERA5 is hourly precipitation in mm; NASA POWER is `mm/day`. All are estimates, not gauge observations.

## Outputs and limitations

The QC sidecar covers numeric columns in existing event ERA5, daily ERA5/POWER, Kaggle reservoir and OpenCity monthly feature tables. The aligned Parquet tables and their in-table QC columns are pending because the required Parquet engine is absent from `.venv` and network access is prohibited by this task. No values were filled. See the summary JSON for actual counts and observed ranges.
"""
    # QC_POLICY.md was created by the first pass; append a correction without
    # replacing it or hiding the preserved preliminary output.
    with DOC.open("a", encoding="utf-8") as stream:
        stream.write("\n\n## Corrected screening pass (v2)\n\n"
                     "The first QC pass is preserved as `qc_flags.csv` and `qc_summary.json`. "
                     "Use `qc_flags_v2.csv` and `qc_summary_v2.json` for this corrected pass. "
                     "ERA5 `wind_speed_10m` is reported in km/h by the source metadata, not m/s; "
                     "the v2 broad screen is 0–200 km/h (an assumption). Daily ERA5/POWER rainfall "
                     "and rainfall columns named `rain_mm_*` also receive a nonnegative-only screen; "
                     "there is no upper cutoff. The v1 outputs remain unchanged.\n")
    print(f"QC_ROWS={len(flags)}; VARIABLES={sum(len(x['variables']) for x in summaries)}; "
          f"OUT={OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
