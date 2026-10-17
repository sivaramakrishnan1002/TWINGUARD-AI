#!/usr/bin/env python
"""Create event time-series Parquet files without changing source data."""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TZ = ZoneInfo("Asia/Kolkata")
EVENTS = {
    "2015": ("2015-11-01", "2015-12-15"),
    "2021": ("2021-11-01", "2021-11-20"),
    "2023": ("2023-11-25", "2023-12-15"),
}
ERA_CSV = ROOT / "data/features/weather/era5_event_hourly_features.csv"
POWER_CSV = ROOT / "data/features/weather/daily_era5_nasa_power_comparison.csv"
RES_CSV = ROOT / "data/features/reservoirs/kaggle_daily_storage_features.csv"
OUT = ROOT / "data/features/events"


def local_window_utc(start_local: str, end_local: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Return inclusive-start/exclusive-end UTC bounds for full IST calendar days."""
    start = pd.Timestamp(start_local).tz_localize(TZ).tz_convert("UTC")
    end = (pd.Timestamp(end_local) + pd.Timedelta(days=1)).tz_localize(TZ).tz_convert("UTC")
    return start, end


def imerg_bucket_date(timestamp_utc: pd.Timestamp) -> date:
    """The IMERG daily value is labelled by its UTC day, not its IST day."""
    return pd.Timestamp(timestamp_utc).tz_convert("UTC").date()


def _source_timezone(year: str) -> str:
    source = ROOT / f"data/raw/weather/open_meteo_era5_{year}_hourly.json"
    obj = json.loads(source.read_text(encoding="utf-8"))
    entries = obj if isinstance(obj, list) else [obj]
    values = {str(item.get("timezone")) for item in entries if item.get("timezone")}
    if len(values) != 1:
        raise ValueError(f"No timezone in ERA5 source metadata: {source.relative_to(ROOT)}")
    return next(iter(values))


def _power_time_standard() -> str:
    sources = sorted((ROOT / "data/raw/weather").glob("nasa_power_daily_point_*.json"))
    standards = set()
    for source in sources:
        obj = json.loads(source.read_text(encoding="utf-8"))
        value = obj.get("header", {}).get("time_standard")
        if value:
            standards.add(str(value))
    if len(standards) != 1:
        raise ValueError(f"NASA POWER time standard is missing or inconsistent: {sorted(standards)}")
    return next(iter(standards))


def _imerg_daily() -> pd.DataFrame:
    """Read only the existing per-day CMA summaries via the project's local reader."""
    raw = ROOT / "data/raw/weather/imerg"
    files = sorted(raw.glob("3B-DAY.MS.MRG.3IMERG.*.V07B.nc4"))
    if not files:
        return pd.DataFrame(columns=["date_utc", "imerg_cma_mean_mm_day"])
    # Reuse the existing read-only NetCDF/window implementation; no granule is written.
    sys.path.insert(0, str(ROOT / "pipelines/phase4"))
    from ingest_imerg import NetCDF  # noqa: PLC0415
    import geopandas as gpd  # noqa: PLC0415
    from shapely.geometry import Point  # noqa: PLC0415

    boundary_path = ROOT / "data/raw/boundary/chennai_cma_boundary.geojson"
    boundary = gpd.read_file(boundary_path).to_crs("EPSG:4326").geometry.union_all()
    minx, miny, maxx, maxy = boundary.bounds
    rows = []
    pattern = re.compile(r"\.([0-9]{8})-S000000-E235959\.V07B\.nc4$")
    for path in files:
        match = pattern.search(path.name)
        if not match:
            continue
        reader = NetCDF(path)
        try:
            values, _, _ = reader.cma_values(boundary, (minx, maxx), (miny, maxy))
        finally:
            try:
                reader.lib.nc_close(reader.ncid)
                reader.dll_dir.close()
            except Exception:
                pass
        rows.append({"date_utc": pd.Timestamp(match.group(1)).date(),
                     "imerg_cma_mean_mm_day": float(sum(values) / len(values)) if values else None})
    return pd.DataFrame(rows)


def build_event(year: str, era: pd.DataFrame, power: pd.DataFrame,
                reservoir: pd.DataFrame, imerg: pd.DataFrame) -> pd.DataFrame:
    start_local, end_local = EVENTS[year]
    start_utc, end_utc = local_window_utc(start_local, end_local)
    axis = pd.DataFrame({"timestamp_utc": pd.date_range(start_utc, end_utc,
                                                        inclusive="left", freq="h", tz="UTC")})
    axis["timestamp_ist"] = axis["timestamp_utc"].dt.tz_convert(TZ)
    axis["event_year"] = int(year)

    e = era.copy()
    e["timestamp_utc"] = pd.to_datetime(e["timestamp_utc"], utc=True, errors="raise")
    e = e[e["timestamp_utc"].between(start_utc, end_utc, inclusive="left")]
    keep = [c for c in ["timestamp_utc", "point_id", "precipitation", "temperature_2m",
                        "relative_humidity_2m", "wind_speed_10m", "pressure_msl"] if c in e]
    value_cols = [c for c in keep if c not in {"timestamp_utc", "point_id"}]
    if "point_id" not in keep:
        raise ValueError("ERA5 features lack point_id")
    wide = e[keep].pivot(index="timestamp_utc", columns="point_id", values=value_cols)
    wide.columns = [f"era5_{var}_{point}" for var, point in wide.columns]
    wide = wide.reset_index()
    axis = axis.merge(wide, how="left", on="timestamp_utc", validate="one_to_one")
    era_cols = [c for c in axis if c.startswith("era5_")]
    axis["era5_record_available"] = axis[era_cols].notna().any(axis=1) if era_cols else False
    for col in era_cols:
        axis[f"missing_{col}"] = axis[col].isna()

    axis["date_utc"] = axis["timestamp_utc"].dt.date
    p = power.copy()
    p["date_utc"] = pd.to_datetime(p["date"], errors="raise").dt.date
    p = p[["date_utc", "era5_mean_mm", "nasa_power_mean_mm"]]
    p = p.drop_duplicates("date_utc")
    axis = axis.merge(p, how="left", on="date_utc", validate="many_to_one")
    axis["daily_bucket_boundary_utc"] = axis["timestamp_utc"].dt.hour.eq(0)
    # Daily estimates are retained only on their UTC bucket boundary; no hourly values are fabricated.
    for col in ["era5_mean_mm", "nasa_power_mean_mm"]:
        axis.loc[~axis["daily_bucket_boundary_utc"], col] = pd.NA
    axis["nasa_power_daily_present"] = axis["daily_bucket_boundary_utc"] & axis["nasa_power_mean_mm"].notna()
    axis["nasa_power_daily_missing"] = axis["daily_bucket_boundary_utc"] & axis["nasa_power_mean_mm"].isna()
    axis["era5_daily_present"] = axis["daily_bucket_boundary_utc"] & axis["era5_mean_mm"].notna()
    axis["era5_daily_missing"] = axis["daily_bucket_boundary_utc"] & axis["era5_mean_mm"].isna()

    if not imerg.empty:
        axis = axis.merge(imerg, how="left", left_on="date_utc", right_on="date_utc", validate="many_to_one")
    else:
        axis["imerg_cma_mean_mm_day"] = pd.NA
    axis.loc[~axis["daily_bucket_boundary_utc"], "imerg_cma_mean_mm_day"] = pd.NA
    axis["imerg_daily_present"] = axis["daily_bucket_boundary_utc"] & axis["imerg_cma_mean_mm_day"].notna()
    axis["imerg_daily_missing"] = axis["daily_bucket_boundary_utc"] & axis["imerg_cma_mean_mm_day"].isna()
    axis["daily_time_semantics"] = "UTC calendar-day bucket; value only at 00:00 UTC"
    axis["era5_source_timezone"] = _source_timezone(year)
    axis["reservoir_time_semantics"] = "date-only; reading time of day unknown; see appended daily records"

    # Preserve reservoir observations as date-only records, never assign them an invented hour.
    r = reservoir.copy()
    r["date_local"] = pd.to_datetime(r["date"], errors="raise").dt.date
    first, last = date.fromisoformat(start_local), date.fromisoformat(end_local)
    r = r[(r["date_local"] >= first) & (r["date_local"] <= last)]
    rrows = pd.DataFrame({
        "timestamp_utc": pd.NaT, "timestamp_ist": pd.NaT, "event_year": int(year),
        "date_utc": pd.NaT, "record_type": "reservoir_daily_date_only",
        "date_local": r["date_local"], "reservoir": r["reservoir"],
        "reservoir_storage_mcft": r["storage_mcft"], "reservoir_time_of_day_known": False,
        "reservoir_record_available": r["storage_mcft"].notna(),
        "reservoir_record_missing": r["storage_mcft"].isna(),
    })
    axis["record_type"] = "hourly_master_axis"
    axis["date_local"] = axis["timestamp_ist"].dt.date
    axis["reservoir_time_of_day_known"] = pd.NA
    axis["reservoir_record_available"] = pd.NA
    axis["reservoir_record_missing"] = pd.NA
    return pd.concat([axis, rrows], ignore_index=True, sort=False)


def main() -> int:
    required = [ERA_CSV, POWER_CSV, RES_CSV]
    missing = [p for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError("Required existing feature input missing: " + ", ".join(str(p) for p in missing))
    if not (Path(__import__("pyarrow").__file__).is_file()):  # fail before creating outputs
        raise RuntimeError("Parquet output requires pyarrow in the project .venv")
    power_time_standard = _power_time_standard()
    if power_time_standard.upper() != "UTC":
        raise ValueError(f"Expected NASA POWER UTC metadata, found: {power_time_standard}")
    OUT.mkdir(parents=True, exist_ok=True)
    targets = [OUT / f"aligned_{year}.parquet" for year in EVENTS]
    dictionary = OUT / "aligned_data_dictionary.json"
    existing = [str(p) for p in [*targets, dictionary] if p.exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite existing output(s): " + ", ".join(existing))
    era = pd.read_csv(ERA_CSV)
    power = pd.read_csv(POWER_CSV)
    reservoir = pd.read_csv(RES_CSV)
    imerg = _imerg_daily()
    for year, target in zip(EVENTS, targets):
        frame = build_event(year, era, power, reservoir, imerg)
        temp = target.with_suffix(".parquet.tmp")
        frame.to_parquet(temp, index=False, engine="pyarrow")
        temp.replace(target)
    metadata = {
        "time_zone_source": "Open-Meteo hourly JSON request metadata; verified per year by the script",
        "local_event_windows_inclusive": EVENTS,
        "hourly_axis": "IST local-day limits converted to UTC; timestamps include timezone offsets",
        "daily_sources": "IMERG and NASA POWER are UTC-day buckets, retained only at 00:00 UTC; no hourly interpolation",
        "reservoirs": "date-only daily rows with unknown time of day; timestamp_utc remains null",
        "nodata": "missing remains null and is accompanied by availability/missing flags",
        "outputs": [p.name for p in targets],
        "status": "DERIVED",
    }
    dictionary.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"WROTE {len(targets)} Parquet event files and {dictionary.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
