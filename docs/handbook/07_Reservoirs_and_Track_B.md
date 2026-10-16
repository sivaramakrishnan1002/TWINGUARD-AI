# Reservoir data and Track B

## Why reservoirs are in the project

Reservoir operations may be relevant to flood decisions alongside extreme rainfall. The team wants reservoir data as an input, not as a predetermined explanation of the 2015 flood. Project notes say sources discuss the roles of rainfall and Chembarambakkam releases differently; the project should report evidence without taking a side. [user]

## What data exist

- Kaggle “Chennai Water Management” contains daily storage for Poondi, Cholavaram, Red Hills/Puzhal and Chembarambakkam, plus a rainfall table. The feature table has **24,728 reservoir-day rows**, dates **1 Jan 2004–3 Dec 2020** overall. Individual per-reservoir coverage has not been reported here. [repo: `docs/PHASE3_LOG.md`, `docs/FEATURE_DICTIONARY.md`]
- Six OpenCity lake CSVs provide monthly storage (page description says mcft), including Kannankottai. The feature output has **1,164 monthly values** total. Monthly cadence is not suitable for determining event-day releases. [repo: `docs/PHASE3_LOG.md`]
- A CWC advisory PDF is a single snapshot, not a time series. A CAG 2017 executive summary is present; it is not the full report. It records Chembarambakkam discharge as **20,960–29,000 cusecs** and **29,000 cusecs for 21 hours** on 1–2 Dec 2015, per the repository notes. These limited findings are not continuous reservoir data. [repo: `docs/MANUAL_TODO.md`]
- No complete historical outflow/release series was collected for the four named Chennai reservoirs. A storage increase or decrease is not a measured release. [repo: `docs/PHASE3_PLAN.md`, `docs/MANUAL_TODO.md`]

## Illustrative Track B screen

The retrospective rule flags a day only when combined storage is at least **80%** of present-day published combined capacity, storage is above its value **three days earlier**, and the **three-day average ERA5 rainfall** exceeds a pre-event 2015 **90th percentile (23.4689 mm)**. Current capacities total **11,257 mcft**; historical capacity changes are unverified. [repo: `data/features/reservoirs/illustrative_track_b_backtest.json`]

Across **2,162** overlapping storage/rainfall dates, it flags **11 days**. Five are **20–24 Nov 2015**; the earliest is **11 days before 1 Dec**. Six flags occur outside that target window. A false-alarm rate is **not computed**: complete daily flood outcomes are unavailable, so the six cannot be labelled false alarms. This is exploratory screening, not a validated warning model or release model. [repo: same JSON]

## Next evidence needed

Verify rainfall units and historical storage capacities. The user must obtain or request dated storage, inflow, release/outflow and gate-operation records for the event windows, with units, timezone and station identity. Do not send emails or records requests from an assistant. If reliable releases remain unavailable, keep them explicitly missing and avoid claiming Track B models releases. [repo: `docs/MANUAL_TODO.md`; user]
