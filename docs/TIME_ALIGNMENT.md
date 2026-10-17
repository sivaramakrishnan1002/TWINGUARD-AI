# Phase 4 temporal alignment

## Event calendars

The master axis is hourly UTC with a corresponding IST timestamp. Event windows are inclusive local calendar dates, converted from `Asia/Kolkata` midnight to an exclusive UTC stop. Source time zones are read from source metadata; no hourly values are manufactured from daily or monthly observations.

| Event | Local-date window | UTC interval | Hours |
|---|---|---|---:|
| 2015 | 2015-11-01 to 2015-12-15 | 2015-10-31 18:30Z to 2015-12-15 18:30Z (exclusive stop) | 1,080 |
| 2021 | 2021-11-01 to 2021-11-20 | 2021-10-31 18:30Z to 2021-11-20 18:30Z (exclusive stop) | 480 |
| 2023 | 2023-11-25 to 2023-12-15 | 2023-11-24 18:30Z to 2023-12-15 18:30Z (exclusive stop) | 504 |

ERA5 feature inputs carry the `Asia/Kolkata` timezone in the Open-Meteo request metadata. NASA POWER's response metadata reports UTC. IMERG daily files are UTC calendar days; the 00:00 UTC boundary is 05:30 IST. Daily values are attached only to their native UTC-day boundary and remain daily observations. Kaggle reservoir values use a local date column but the observation time of day is not provided, so `timestamp_utc` stays missing and no time is inferred. Monthly OpenCity observations remain monthly.

The alignment script adds source-presence and missing flags and a common hourly event index. The requested `aligned_<year>.parquet` outputs and their data dictionary are **pending**: `.venv` has no `pyarrow` or `fastparquet`, no local wheel cache was available, and the request forbids network access. No partial Parquet output was written. Script: `pipelines/phase4/time_alignment.py`.

## Completion update — 2026-10-17

The user installed a local Parquet engine and test tools. Verified `.venv` versions: `pyarrow==26.0.0`, `pytest==9.1.1`. The three requested Parquet files now exist and are DERIVED:

| Output | Rows | Native source records / missing flags |
|---|---:|---|
| `data/features/events/aligned_2015.parquet` | 1,260 total: 1,080 hourly axis + 180 date-only reservoir rows | ERA5 present at all 1,080 hours; 45/45 daily POWER and 45/45 daily IMERG buckets present; 180/180 reservoir daily values present. |
| `data/features/events/aligned_2021.parquet` | 480 hourly rows | ERA5 present at all hours; 20/20 daily POWER and 20/20 daily IMERG buckets present; Kaggle reservoir series has no rows in this event window (stored series ends 2020-12-03). |
| `data/features/events/aligned_2023.parquet` | 504 hourly rows | ERA5 present at all hours; 21/21 daily POWER and 21/21 daily IMERG buckets present; Kaggle reservoir series has no rows in this event window (stored series ends 2020-12-03). |

Each hourly row includes UTC and IST timestamps, per-point ERA5 values and missing flags, plus flags for daily POWER/IMERG presence or absence. Daily values are populated only at their UTC day boundary (00:00 UTC / 05:30 IST); they are not interpolated. Reservoir values are separate date-only rows with null timestamps and an explicit unknown-time-of-day indicator. Since the source has no reservoir rows for 2021 or 2023, none were fabricated. The machine-readable window/convention metadata is in `data/features/events/aligned_data_dictionary.json`; the source variable and flag interpretation is documented in `FEATURE_DICTIONARY.md`.

Tests: all six Phase 4 tests pass with pytest, including the static table row-count check that was previously skipped. The exact command and overall Stage 4 result are in `STAGE_4_REPORT.md`.
