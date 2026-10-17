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
