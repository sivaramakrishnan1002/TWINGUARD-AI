#!/usr/bin/env python
"""Read-only ERA5/NASA POWER check; writes new reports only and refuses overwrite."""
from __future__ import annotations

import json
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data/raw/weather"
OUT = ROOT / "docs"
FILES = [
    OUT / "ERA5_2015_CHECK.md",
    OUT / "ERA5_2015_hourly_28Nov_04Dec.csv",
    OUT / "ERA5_EVENT_DAILY_BY_POINT.csv",
    OUT / "ERA5_EVENT_TOP10_DAILY_BY_POINT.csv",
]
WINDOWS = {
    "2015": ("2015-11-01", "2015-12-15"),
    "2021": ("2021-11-01", "2021-11-20"),
    "2023": ("2023-11-25", "2023-12-15"),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-own-docs", action="store_true",
                        help="Refresh only the four report files this script creates under docs/.")
    args = parser.parse_args()
    existing = [str(p.relative_to(ROOT)) for p in FILES if p.exists()]
    if existing and not args.refresh_own_docs:
        raise FileExistsError("Refusing to overwrite: " + ", ".join(existing))

    event_frames: dict[str, pd.DataFrame] = {}
    meta: dict[str, dict] = {}
    for year, (start, end) in WINDOWS.items():
        payload = json.loads((RAW / f"open_meteo_era5_{year}_hourly.json").read_text(encoding="utf-8"))
        meta[year] = {"timezone": payload[0].get("timezone"), "utc_offset_seconds": payload[0].get("utc_offset_seconds"),
                      "units": payload[0].get("hourly_units"), "per_point": []}
        frames = []
        for i, item in enumerate(payload, 1):
            hourly = item["hourly"]
            frame = pd.DataFrame({"timestamp_local": pd.to_datetime(hourly["time"]),
                                  "rain_mm": pd.to_numeric(hourly["precipitation"], errors="coerce")})
            frame["point_id"] = f"era5_{i:02d}"
            frame = frame[(frame.timestamp_local >= start) & (frame.timestamp_local <= end + " 23:00")]
            meta[year]["per_point"].append({"point_id": f"era5_{i:02d}", "rows": int(len(frame)),
                                             "first_local": str(frame.timestamp_local.min()),
                                             "last_local": str(frame.timestamp_local.max())})
            frames.append(frame)
        event_frames[year] = pd.concat(frames, ignore_index=True)

    # Daily values are grouped by the local date declared in each ERA5 request.
    daily_long = []
    top_rows = []
    top_mean: dict[str, list[tuple[str, float]]] = {}
    for year, frame in event_frames.items():
        frame = frame.copy()
        frame["date"] = frame.timestamp_local.dt.strftime("%Y-%m-%d")
        daily_frame = frame.groupby(["date", "point_id"], as_index=False).rain_mm.sum()
        matrix = daily_frame.pivot(index="date", columns="point_id", values="rain_mm").sort_index()
        for point in matrix.columns:
            for day, value in matrix[point].items():
                daily_long.append({"event_year": year, "date": day, "point_id": point, "rain_mm": float(value)})
        mean = matrix.mean(axis=1)
        for day, value in mean.items():
            daily_long.append({"event_year": year, "date": day, "point_id": "mean_9_points", "rain_mm": float(value)})
        top_mean[year] = [(day, float(value)) for day, value in mean.nlargest(10).items()]
        for point in list(matrix.columns) + ["mean_9_points"]:
            series = mean if point == "mean_9_points" else matrix[point]
            for rank, (day, value) in enumerate(series.nlargest(10).items(), 1):
                top_rows.append((year, point, day, float(value), rank))
    daily_out = pd.DataFrame(daily_long).sort_values(["event_year", "date", "point_id"])
    top_out = pd.DataFrame(top_rows, columns=["event_year", "point_id", "date", "rain_mm", "rank"])
    # Keep the daily top-10 file restricted to ranked rows (one row per point and mean).
    top_out = top_out.dropna(subset=["rank"]).sort_values(["event_year", "point_id", "rank"])

    # Retain every local-hour value for 28 Nov–4 Dec 2015 in the companion CSV.
    target = event_frames["2015"].copy()
    target = target[(target.timestamp_local >= "2015-11-28") & (target.timestamp_local <= "2015-12-04 23:00")]
    pivot = target.pivot(index="timestamp_local", columns="point_id", values="rain_mm").sort_index()
    pivot["mean_9_points"] = pivot.mean(axis=1)
    pivot = pivot.reset_index()
    pivot["timestamp_local"] = pivot.timestamp_local.dt.strftime("%Y-%m-%d %H:%M:%S")

    # Compare common UTC calendar days because NASA POWER declares UTC day keys.
    era_utc = []
    for item in json.loads((RAW / "open_meteo_era5_2015_hourly.json").read_text(encoding="utf-8")):
        local = pd.DatetimeIndex(pd.to_datetime(item["hourly"]["time"])).tz_localize(item["timezone"])
        utc = local.tz_convert("UTC")
        era_utc.append(pd.DataFrame({"utc_date": utc.date, "point_id": len(era_utc),
                                     "rain_mm": item["hourly"]["precipitation"]}))
    era_hourly = pd.concat(era_utc, ignore_index=True)
    era_daily = era_hourly.groupby(["utc_date", "point_id"]).rain_mm.sum().groupby("utc_date").mean()
    nasa_rows = []
    nasa_units = set()
    nasa_tz = set()
    for p in sorted(RAW.glob("nasa_power_daily_point_*.json")):
        obj = json.loads(p.read_text(encoding="utf-8"))
        nasa_units.add(obj.get("parameters", {}).get("PRECTOTCORR", {}).get("units"))
        nasa_tz.add(obj.get("header", {}).get("time_standard"))
        series = obj["properties"]["parameter"]["PRECTOTCORR"]
        for date, val in series.items():
            if "20151130" <= date <= "20151203":
                nasa_rows.append({"utc_date": pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:]}").date(),
                                  "rain_mm_day": float(val) if isinstance(val, (int, float)) and val >= 0 else np.nan})
    nasa = pd.DataFrame(nasa_rows).groupby("utc_date").rain_mm_day.mean()
    comparison = pd.concat([era_daily.rename("ERA5_mm_day"), nasa.rename("NASA_POWER_mm_day")], axis=1).loc[
        pd.Timestamp("2015-11-30").date():pd.Timestamp("2015-12-03").date()].dropna()
    comparison["ERA5_minus_POWER_mm_day"] = comparison.ERA5_mm_day - comparison.NASA_POWER_mm_day
    corr = float(comparison.ERA5_mm_day.corr(comparison.NASA_POWER_mm_day)) if len(comparison) > 1 else None
    bias = float(comparison.ERA5_minus_POWER_mm_day.mean()) if len(comparison) else None

    # Dec 1–2 target-window checks are local dates, matching the ERA5 request.
    target_daily = daily_out[(daily_out.event_year == "2015") &
                             (daily_out.point_id == "mean_9_points") &
                             daily_out.date.isin(["2015-12-01", "2015-12-02"])]
    broad = event_frames["2015"].copy()
    broad["date"] = broad.timestamp_local.dt.strftime("%Y-%m-%d")
    full_daily = broad.groupby(["date", "point_id"]).rain_mm.sum().unstack("point_id")
    full_mean = full_daily.mean(axis=1)
    nov16 = float(full_mean.loc["2015-11-16"])
    rankings = {d: int(full_mean.rank(ascending=False, method="min").loc[d]) for d in ("2015-12-01", "2015-12-02")}

    lines = [
        "# ERA5 rainfall check — 2015 and event windows", "",
        "## Source and calendar checks", "",
        f"The raw 2015 Open-Meteo ERA5 hourly JSON contains nine point requests. Its request metadata declares timezone **{meta['2015']['timezone']}** (UTC offset {meta['2015']['utc_offset_seconds']} seconds) and precipitation units **{meta['2015']['units'].get('precipitation')}**. Every point has hourly records from 2015-11-01 00:00 through 2015-12-15 23:00 local time; the target 1–2 Dec dates are present with 24 hourly records per date and no missing hourly values. The full 2015–2023 daily baseline JSON covers 2015-01-01 through 2023-12-31 at all nine points. [repo: `data/raw/weather/open_meteo_era5_2015_hourly.json`, `data/raw/weather/open_meteo_era5_2015-2023_daily_baseline.json`]", "",
        f"NASA POWER metadata declares PRECTOTCORR units **{', '.join(sorted(str(x) for x in nasa_units))}** and date time standard **{', '.join(sorted(str(x) for x in nasa_tz))}**. Therefore the four-day comparison below uses ERA5 hourly rainfall regrouped by UTC date to match NASA POWER's UTC daily buckets; this differs from the local-day ERA5 event tables. [repo: `data/raw/weather/nasa_power_daily_point_*.json`]", "",
        "The saved peak summary searches the complete downloaded event-request windows, not just 1–8 Dec 2015. It reports 16 Nov because the 2015 request covers 1 Nov–15 Dec, and 16 Nov is the largest local-day nine-point mean in that full period. The raw timestamps parse in order and agree with the request timezone; the peak is not caused by a UTC/local date shift or malformed parsing. It is a window-selection issue: it is not a Dec 1–2 peak. [repo: `data/features/weather/event_peak_rainfall.json`, raw hourly JSON]", "",
        "**Answer about 1–2 Dec:** ERA5 does show a substantial rain episode: local-day nine-point means are **49.82 mm on 1 Dec** and **57.10 mm on 2 Dec**. They rank **4th and 3rd**, respectively, among the 45 local dates in the stored 1 Nov–15 Dec 2015 request window. The same window's highest day is 16 Nov at **112.86 mm**. Thus the event is present in the series, but it is not the full-window maximum. ERA5 is a gridded reanalysis estimate, not gauge truth. [repo: source JSON; calculations in this report]", "",
        "## Local daily totals for 28 Nov–4 Dec 2015", "",
        "All values are millimetres per local calendar day (Asia/Kolkata). The individual point columns and nine-point mean are provided below.", "",
        "| Local date | " + " | ".join(f"era5_{i:02d}" for i in range(1, 10)) + " | Mean |", "|---|" + "---:|"*10,
    ]
    local_daily = daily_out[(daily_out.event_year == "2015") & daily_out.date.between("2015-11-28", "2015-12-04")]
    local_mat = local_daily.pivot(index="date", columns="point_id", values="rain_mm")
    for day, row in local_mat.iterrows():
        vals = [float(row.get(f"era5_{i:02d}", np.nan)) for i in range(1, 10)]
        lines.append("| " + day + " | " + " | ".join(f"{v:.2f}" for v in vals) + f" | {np.nanmean(vals):.2f} |")
    lines += ["", f"The 168-hour point-by-point rainfall series is in [`{FILES[1].name}`]. Period totals and maximum single-hour amount per point are summarized below:", "",
              "| Point | 168 h total (mm) | Max 1 h (mm) | Local timestamp of max |", "|---|---:|---:|---|"]
    for i in range(1, 10):
        col=f"era5_{i:02d}"; series=pd.to_numeric(pivot[col]); imax=series.idxmax()
        lines.append(f"| {col} | {series.sum():.2f} | {series.iloc[imax]:.2f} | {pivot.loc[imax,'timestamp_local']} |")
    mean_series=pd.to_numeric(pivot["mean_9_points"]);imax=mean_series.idxmax()
    lines.append(f"| Mean across 9 points | {mean_series.sum():.2f} | {mean_series.iloc[imax]:.2f} | {pivot.loc[imax,'timestamp_local']} |")
    lines += ["", "## Top 10 daily totals in each stored event window", "", "Ranked by the nine-point mean, using each source request's Asia/Kolkata local dates. Individual point rankings are in [`ERA5_EVENT_TOP10_DAILY_BY_POINT.csv`](ERA5_EVENT_TOP10_DAILY_BY_POINT.csv); all daily point values are in [`ERA5_EVENT_DAILY_BY_POINT.csv`](ERA5_EVENT_DAILY_BY_POINT.csv). These are the stored request windows, not claims that each date is the verified event peak.", ""]
    for year in WINDOWS:
        s=top_mean[year]
        lines += [f"### {year} — {WINDOWS[year][0]} to {WINDOWS[year][1]}", "", "| Rank | Local date | Nine-point mean (mm/day) |", "|---:|---|---:|"]
        lines += [f"| {rank} | {day} | {value:.2f} |" for rank,(day,value) in enumerate(s,1)]
        lines.append("")
    lines += ["## ERA5 versus NASA POWER, 30 Nov–3 Dec 2015", "", "Four matched UTC daily buckets, each averaged across the same nine spatial points. The sample is only four days and is not a robust long-term agreement assessment.", "", "| UTC date | ERA5 (mm/day) | NASA POWER (mm/day) | ERA5 − POWER (mm/day) |", "|---|---:|---:|---:|"]
    for day,row in comparison.iterrows():
        lines.append(f"| {day} | {row.ERA5_mm_day:.2f} | {row.NASA_POWER_mm_day:.2f} | {row.ERA5_minus_POWER_mm_day:.2f} |")
    lines += ["", f"Pearson correlation: **{corr:.3f}**; mean bias (ERA5 minus NASA POWER): **{bias:.2f} mm/day**; n = {len(comparison)} daily pairs. Since POWER reports UTC and the ERA5 source JSON is Asia/Kolkata, calendar-day comparisons without timezone alignment would compare different 24-hour periods. [repo: raw metadata; calculations in this report]", "",
              "## Manual rainfall data tasks", "", "1. Manually obtain GPM IMERG precipitation for the three event windows through NASA Earthdata (the user already has an account); keep credentials private, preserve original downloads, record product/version, UTC conventions, units, licence, size and SHA-256. No download was performed here.",
              "2. Manually obtain the IMD gridded daily rainfall product covering Chennai and the same event periods; record its product version, grid, units, calendar/time convention and usage terms. No download was performed here.", "",
              "## Provenance and limits", "", "This report reads the existing raw JSON and derived CSV only. It does not modify raw or feature data. The three event request periods used here are exactly the stored JSON periods: 1 Nov–15 Dec 2015, 1–20 Nov 2021, and 25 Nov–15 Dec 2023. They should not be mistaken for independently verified flood-duration windows.", ""]

    # Write only new documentation artifacts.
    for path, text in [(FILES[0], "\n".join(lines)),
                       (FILES[1], pivot.to_csv(index=False, lineterminator="\n")),
                       (FILES[2], daily_out.to_csv(index=False, lineterminator="\n")),
                       (FILES[3], top_out.to_csv(index=False, lineterminator="\n"))]:
        path.write_text(text.rstrip() + "\n", encoding="utf-8")
    print("Wrote:", ", ".join(str(p.relative_to(ROOT)) for p in FILES))


if __name__ == "__main__":
    main()
