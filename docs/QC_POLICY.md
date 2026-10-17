# Missing-data and outlier QC policy — Phase 4

This is a DERIVED screening report. Raw files and existing feature files were read only. Row-level flags are in `data/features/events/qc_flags.csv`; per-variable counts and ranges are in `data/features/events/qc_summary.json`.

## Rules

- Missing values stay missing. No variable was filled, interpolated, deleted, or clipped. A missingness flag is emitted for every numeric observation.
- Non-finite numbers are flagged separately. Broad physical screening intervals are applied only to ERA5 variables with known units: temperature −50 to 60 °C and wind speed 0 to 200 m/s are deliberately broad assumptions; relative humidity is screened at 0–100%; sea-level pressure at 800–1,100 hPa. Hourly precipitation must be nonnegative; no upper cut-off is imposed because extreme precipitation should not be silently rejected.
- Reservoir storage must be nonnegative, but no historical capacity upper bound is imposed. The recorded percent-of-capacity field is screened only for negative values because the denominator is a present-day capacity and historical capacity is not verified.
- Unmapped numeric variables are summarized but receive no invented range. Screened values are warnings for review, not automatic errors.
- IMERG units/daily support are described in `RAIN_SOURCES_COMPARISON.md`; the existing report records `mm/day` from product metadata. ERA5 is hourly precipitation in mm; NASA POWER is `mm/day`. All are estimates, not gauge observations.

## Outputs and limitations

The QC sidecar covers numeric columns in existing event ERA5, daily ERA5/POWER, Kaggle reservoir and OpenCity monthly feature tables. The aligned Parquet tables and their in-table QC columns are pending because the required Parquet engine is absent from `.venv` and network access is prohibited by this task. No values were filled. See the summary JSON for actual counts and observed ranges.


## Corrected screening pass (v2)

The first QC pass is preserved as `qc_flags.csv` and `qc_summary.json`. Use `qc_flags_v2.csv` and `qc_summary_v2.json` for this corrected pass. ERA5 `wind_speed_10m` is reported in km/h by the source metadata, not m/s; the v2 broad screen is 0–200 km/h (an assumption). Daily ERA5/POWER rainfall and rainfall columns named `rain_mm_*` also receive a nonnegative-only screen; there is no upper cutoff. The v1 outputs remain unchanged.
