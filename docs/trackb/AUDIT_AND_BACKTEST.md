# Track B audit, target, rule and backtest

## B1 — source coverage audit (DERIVED from the local project inputs)

### Reservoir storage

The Kaggle source archive contains `chennai_reservoir_levels.csv`. Daily coverage is 6,182 rows for each of Poondi, Cholavaram, Red Hills, and Chembarambakkam, from 2004-01-01 through 2020-12-03, with no missing per-reservoir rows in that date grid. Reported unit is mcft. The derived feature table has 24,728 reservoir-days. The observed daily series ends on 2020-12-03.

OpenCity source-derived monthly non-null values are: Chembarambakkam 228/228 months (2003-01 through 2021-12, no missing months); Cholavaram 228/228 (same bounds, no missing months); Poondi 228/228 (same); Red Hills/Puzhal 228/228 (same); Kannankottai 13/24 (2020-01 through 2021-12; missing 2020-01 through 2020-11); Veeranam 227/228 (2003-01 through 2021-12; missing 2020-04). Source metadata labels these values mcft. Monthly data cannot resolve daily operation or release timing.

### Rainfall

The Kaggle archive also contains `chennai_reservoir_rainfall.csv`, with 6,182 daily rows for each of the same four reservoirs over 2004-01-01–2020-12-03 and no missing numeric values. Its source does not declare a unit. In the matched 2015-01-01–2020-12-03 interval, the per-day four-reservoir mean has n=2,164 matched dates, mean 3.686 raw units, P95 22.0, maximum 319.35. The matched ERA5-area daily mean is 2.730 mm/day; NASA POWER-area mean is 3.452 mm/day. Pearson correlation of Kaggle mean with ERA5 is 0.560, and with NASA POWER is 0.511.

**INFERRED:** Kaggle rainfall's numeric scale is depth-like and broadly comparable in order to mm/day; the unit remains unverified. Correlation and scale comparison do not establish gauge truth. Spatial aggregation differs between reservoir values and the area-average gridded comparison, and daily tails can diverge substantially. Do not relabel the raw Kaggle unit as confirmed mm.

### IMERG, ERA5 and NASA POWER

Local IMERG holdings are selected daily files for event windows, not a continuous daily archive spanning the storage years. The local ERA5 daily comparison and all nine NASA POWER grid-point JSON files cover every day from 2015-01-01 through 2023-12-31 (3,287 dates per series); local ERA5 hourly holdings are event-window subsets for 2015, 2021, and 2023. Kaggle overlaps these full daily series on 2,164 dates from 2015-01-01 through its endpoint 2020-12-03. Full local daily availability is therefore partial; source-specific event coverage and peaks are detailed in `../RAIN_SOURCES_COMPARISON.md`. Products are estimates, not rain-gauge truth.

### Published capacities

Existing project analysis uses current published figures recorded from the [TN Smart basin-wise reservoir page](https://beta-tnsmart.rimes.int/index.php/Reservoir/basin_wise): Poondi 3,231; Cholavaram 1,081; Red Hills 3,300; Chembarambakkam 3,645 mcft; combined 11,257 mcft. These are published figures whose reported values have changed over time; this set is current-source denominators and does not verify historical capacity. Target labels using them are DERIVED under that capacity assumption.

## B2 — target and sensitivity

DEFAULT, to confirm: horizon N=7 days and capacity fraction=0.80. For each day, target=1 if storage reaches or exceeds the specified fraction on any of the following N daily observations; the current day is excluded. The final N days without complete future coverage are censored. Sensitivity evaluates N={3,7,14}, fraction={0.70,0.80,0.90}, each reservoir and the four-reservoir aggregate. Results and target prevalence are in `BACKTEST_RESULTS.json`.

Actual release decisions are not observed. The CAG-reported Chembarambakkam discharge range of 20,960–29,000 cusecs (29,000 cusecs for 21 hours) on 1–2 Dec 2015 is annotation only; it is not used as a label, feature, or continuous release series.

## B3 — rule and calibrated probabilistic comparators

The rule engine uses storage percent, 1-day and 3-day storage rise, and 3-day rainfall. Rise cutoffs are medians of positive rises in training years; rain cutoffs are training-period P75 and P90. Alert levels are transparent: Critical at >=90% capacity; Warning at >=80% with qualifying 3-day rise or P90 rain; Watch at >=70%, or qualifying 1-day rise plus P75 rain; otherwise Normal. DEFAULT, to confirm: storage cutoffs 70/80/90 percent. Per-alert `confidence` for rule alerts is the fraction of four rule indicators satisfied, not a probability. Learned thresholds are stored with results.

Logistic regression and histogram gradient boosting are fit on 2004–2014, Platt-calibrated on 2015–2017, and evaluated on the untouched 2018–2020 period. Rainfall-only logistic regression and current-storage persistence are comparators. Split boundaries are purged by N days to prevent future-target windows crossing between partitions. Reliability bins, Brier score, log loss, ROC-AUC, PR-AUC, and decision metrics are in the JSON result. These models forecast only the chosen future storage threshold target; they do not forecast floods or releases.

## B4 — held-out metrics and limits

`BACKTEST_RESULTS.json` reports per-reservoir and combined results, POD, false alarm ratio, CSI, event lead time, and year-block bootstrap 95% intervals for alerts. The held-out window is 2018-01-01 through 2020-12-03 (up to 1,061 labeled rows per entity after feature warmup and target censoring). Year-block bootstrap uses 300 replicates and seed 29. There are only three held-out year clusters, so bootstrap intervals are coarse and can be degenerate; do not treat them as stable operational uncertainty bounds. If a held-out target has no events, POD and some other ratios are undefined (JSON null), not zero.

The existing 2015 exploratory screen remains a separate case study: 11 combined-rule flags in its 2,162-day overlap; five on 20–24 Nov before the 1 Dec reference date, earliest 11 days before; six flags outside that target window. It used a pre-target 2015 P90 and is not the held-out rule/model evaluation above. Since daily storage ends 2020-12-03, 2021 and 2023 cannot be evaluated at daily storage resolution.

All performance is conditional on currently published capacity figures and this DERIVED storage target. None of these results validates flood warning performance, operational lead time, or release decisions.

## B5 — replay and persistence

JSONL schemas and source labels are in `MESSAGES.md`. The accelerated replay script uses learned earlier-period rule thresholds in `BACKTEST_RESULTS.json`; `--write-db` writes alerts to `trackb.alert_events`, `twin.alerts`, and their idempotency links after migration 100 is applied. Reservoir-state upsert and recompute-marker helpers are in `pipelines/trackb/persistence.py` and require a caller-supplied twin run id. No database migration was applied and no replay was persisted in this run.


