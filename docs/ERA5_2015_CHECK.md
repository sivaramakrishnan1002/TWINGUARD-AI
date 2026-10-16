# ERA5 rainfall check — 2015 and event windows

## Source and calendar checks

The raw 2015 Open-Meteo ERA5 hourly JSON contains nine point requests. Its request metadata declares timezone **Asia/Kolkata** (UTC offset 19800 seconds) and precipitation units **mm**. Every point has hourly records from 2015-11-01 00:00 through 2015-12-15 23:00 local time; the target 1–2 Dec dates are present with 24 hourly records per date and no missing hourly values. The full 2015–2023 daily baseline JSON covers 2015-01-01 through 2023-12-31 at all nine points. [repo: `data/raw/weather/open_meteo_era5_2015_hourly.json`, `data/raw/weather/open_meteo_era5_2015-2023_daily_baseline.json`]

NASA POWER metadata declares PRECTOTCORR units **mm/day** and date time standard **UTC**. Therefore the four-day comparison below uses ERA5 hourly rainfall regrouped by UTC date to match NASA POWER's UTC daily buckets; this differs from the local-day ERA5 event tables. [repo: `data/raw/weather/nasa_power_daily_point_*.json`]

The saved peak summary searches the complete downloaded event-request windows, not just 1–8 Dec 2015. It reports 16 Nov because the 2015 request covers 1 Nov–15 Dec, and 16 Nov is the largest local-day nine-point mean in that full period. The raw timestamps parse in order and agree with the request timezone; the peak is not caused by a UTC/local date shift or malformed parsing. It is a window-selection issue: it is not a Dec 1–2 peak. [repo: `data/features/weather/event_peak_rainfall.json`, raw hourly JSON]

**Answer about 1–2 Dec:** ERA5 does show a substantial rain episode: local-day nine-point means are **49.82 mm on 1 Dec** and **57.10 mm on 2 Dec**. They rank **4th and 3rd**, respectively, among the 45 local dates in the stored 1 Nov–15 Dec 2015 request window. The same window's highest day is 16 Nov at **112.86 mm**. Thus the event is present in the series, but it is not the full-window maximum. ERA5 is a gridded reanalysis estimate, not gauge truth. [repo: source JSON; calculations in this report]

## Local daily totals for 28 Nov–4 Dec 2015

All values are millimetres per local calendar day (Asia/Kolkata). The individual point columns and nine-point mean are provided below.

| Local date | era5_01 | era5_02 | era5_03 | era5_04 | era5_05 | era5_06 | era5_07 | era5_08 | era5_09 | Mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2015-11-28 | 0.00 | 0.00 | 0.00 | 0.00 | 0.40 | 0.40 | 0.30 | 0.70 | 0.70 | 0.28 |
| 2015-11-29 | 18.20 | 14.70 | 14.70 | 16.20 | 17.50 | 17.50 | 18.10 | 18.50 | 18.50 | 17.10 |
| 2015-11-30 | 8.20 | 11.80 | 11.80 | 12.10 | 12.50 | 12.50 | 11.60 | 11.30 | 11.30 | 11.46 |
| 2015-12-01 | 60.20 | 66.10 | 66.10 | 41.30 | 48.80 | 48.80 | 34.90 | 41.10 | 41.10 | 49.82 |
| 2015-12-02 | 61.40 | 56.40 | 56.40 | 45.50 | 57.90 | 57.90 | 49.60 | 64.40 | 64.40 | 57.10 |
| 2015-12-03 | 23.80 | 37.20 | 37.20 | 13.60 | 22.90 | 22.90 | 14.20 | 23.50 | 23.50 | 24.31 |
| 2015-12-04 | 4.50 | 14.70 | 14.70 | 3.30 | 9.30 | 9.30 | 3.40 | 9.00 | 9.00 | 8.58 |

The 168-hour point-by-point rainfall series is in [`ERA5_2015_hourly_28Nov_04Dec.csv`]. Period totals and maximum single-hour amount per point are summarized below:

| Point | 168 h total (mm) | Max 1 h (mm) | Local timestamp of max |
|---|---:|---:|---|
| era5_01 | 176.30 | 8.50 | 2015-12-01 01:00:00 |
| era5_02 | 200.90 | 11.70 | 2015-12-01 01:00:00 |
| era5_03 | 200.90 | 11.70 | 2015-12-01 01:00:00 |
| era5_04 | 132.00 | 4.40 | 2015-12-02 10:00:00 |
| era5_05 | 169.30 | 5.40 | 2015-12-01 01:00:00 |
| era5_06 | 169.30 | 5.40 | 2015-12-01 01:00:00 |
| era5_07 | 132.10 | 4.50 | 2015-12-02 10:00:00 |
| era5_08 | 168.50 | 5.30 | 2015-12-02 05:00:00 |
| era5_09 | 168.50 | 5.30 | 2015-12-02 05:00:00 |
| Mean across 9 points | 168.64 | 5.67 | 2015-12-01 01:00:00 |

## Top 10 daily totals in each stored event window

Ranked by the nine-point mean, using each source request's Asia/Kolkata local dates. Individual point rankings are in [`ERA5_EVENT_TOP10_DAILY_BY_POINT.csv`](ERA5_EVENT_TOP10_DAILY_BY_POINT.csv); all daily point values are in [`ERA5_EVENT_DAILY_BY_POINT.csv`](ERA5_EVENT_DAILY_BY_POINT.csv). These are the stored request windows, not claims that each date is the verified event peak.

### 2015 — 2015-11-01 to 2015-12-15

| Rank | Local date | Nine-point mean (mm/day) |
|---:|---|---:|
| 1 | 2015-11-16 | 112.86 |
| 2 | 2015-11-09 | 78.73 |
| 3 | 2015-12-02 | 57.10 |
| 4 | 2015-12-01 | 49.82 |
| 5 | 2015-11-08 | 48.27 |
| 6 | 2015-11-15 | 47.37 |
| 7 | 2015-11-19 | 34.01 |
| 8 | 2015-12-03 | 24.31 |
| 9 | 2015-11-13 | 24.07 |
| 10 | 2015-11-01 | 18.42 |

### 2021 — 2021-11-01 to 2021-11-20

| Rank | Local date | Nine-point mean (mm/day) |
|---:|---|---:|
| 1 | 2021-11-11 | 89.20 |
| 2 | 2021-11-10 | 77.40 |
| 3 | 2021-11-18 | 65.66 |
| 4 | 2021-11-07 | 37.71 |
| 5 | 2021-11-17 | 32.80 |
| 6 | 2021-11-06 | 26.82 |
| 7 | 2021-11-01 | 25.59 |
| 8 | 2021-11-14 | 25.43 |
| 9 | 2021-11-08 | 17.12 |
| 10 | 2021-11-02 | 15.34 |

### 2023 — 2023-11-25 to 2023-12-15

| Rank | Local date | Nine-point mean (mm/day) |
|---:|---|---:|
| 1 | 2023-12-04 | 200.67 |
| 2 | 2023-12-03 | 42.18 |
| 3 | 2023-12-05 | 25.03 |
| 4 | 2023-11-30 | 18.98 |
| 5 | 2023-11-29 | 16.13 |
| 6 | 2023-12-02 | 13.57 |
| 7 | 2023-12-15 | 7.97 |
| 8 | 2023-12-08 | 5.97 |
| 9 | 2023-11-25 | 5.73 |
| 10 | 2023-11-26 | 5.58 |

## ERA5 versus NASA POWER, 30 Nov–3 Dec 2015

Four matched UTC daily buckets, each averaged across the same nine spatial points. The sample is only four days and is not a robust long-term agreement assessment.

| UTC date | ERA5 (mm/day) | NASA POWER (mm/day) | ERA5 − POWER (mm/day) |
|---|---:|---:|---:|
| 2015-11-30 | 32.21 | 64.67 | -32.46 |
| 2015-12-01 | 43.98 | 118.73 | -74.75 |
| 2015-12-02 | 54.60 | 35.82 | 18.78 |
| 2015-12-03 | 12.22 | 22.70 | -10.48 |

Pearson correlation: **0.383**; mean bias (ERA5 minus NASA POWER): **-24.73 mm/day**; n = 4 daily pairs. Since POWER reports UTC and the ERA5 source JSON is Asia/Kolkata, calendar-day comparisons without timezone alignment would compare different 24-hour periods. [repo: raw metadata; calculations in this report]

## Manual rainfall data tasks

1. Manually obtain GPM IMERG precipitation for the three event windows through NASA Earthdata (the user already has an account); keep credentials private, preserve original downloads, record product/version, UTC conventions, units, licence, size and SHA-256. No download was performed here.
2. Manually obtain the IMD gridded daily rainfall product covering Chennai and the same event periods; record its product version, grid, units, calendar/time convention and usage terms. No download was performed here.

## Provenance and limits

This report reads the existing raw JSON and derived CSV only. It does not modify raw or feature data. The three event request periods used here are exactly the stored JSON periods: 1 Nov–15 Dec 2015, 1–20 Nov 2021, and 25 Nov–15 Dec 2023. They should not be mistaken for independently verified flood-duration windows.
