# Track B held-out backtest results

**DERIVED / ASSUMPTION:** This target is future reservoir storage reaching a fraction of current published capacity within N days. It is not flood occurrence or a release-decision target. Full outputs and reliability bins are in `BACKTEST_RESULTS.json`.

## Protocol

- Training observations: 2004–2014; calibration: 2015–2017; held-out test: 2018–2020. Exact per-entity dates are in the result JSON. Split boundaries are purged by N days.
- Main setting: DEFAULT, to confirm: N=7 days and fraction=0.80; full 3×3 target and alert sensitivity is in the JSON/CSV.
- Models: standardized logistic regression and histogram gradient boosting. Platt calibration is applied only where the calibration partition has both classes. Baselines are current-storage persistence and rainfall-only logistic regression.
- 95% intervals resample calendar-year blocks (300 replicates, seed 29); the test set contains only three year clusters, so intervals are coarse. Undefined rates are null, not zero.
- Compute used the existing CPU scikit-learn implementation; GPU runtime was not used.

## Held-out comparison

| Entity | Test prevalence | Rule POD / FAR / CSI | Persistence CSI | Rain-only CSI | Logistic CSI | Gradient boosting CSI | GB Brier |
|---|---:|---:|---:|---:|---:|---:|---:|
| POONDI | 0.006 | 0.333 / 0.957 / 0.040 | 0.000 | 0.000 | 0.000 | 0.000 | 0.007 |
| CHOLAVARAM | 0.000 | — / 1.000 / 0.000 | — | — | — | — | 0.000 |
| REDHILLS | 0.179 | 0.995 / 0.442 / 0.556 | 0.875 | 0.000 | 0.721 | 0.905 | 0.016 |
| CHEMBARAMBAKKAM | 0.015 | 0.875 / 0.741 / 0.250 | 0.375 | 0.000 | 0.875 | 0.625 | 0.006 |
| Combined | 0.006 | 0.500 / 0.963 / 0.036 | 0.000 | 0.000 | 0.333 | 0.333 | 0.003 |

These are storage-target metrics, not flood prediction scores. Class imbalance differs by reservoir. Per-model reliability bins, Brier/log loss, ROC-AUC/PR-AUC, event lead times, exact splits and bootstrap intervals are in the JSON.

## 2015 case study and limits

The legacy 2015 screen is reported separately in `BACKTEST_RESULTS.json`: 11 flags, five from 20–24 Nov before the 1 Dec reference date, earliest lead 11 days; six outside-window flags are not validated false alarms. It is not the held-out rule/model evaluation.

Capacity histories are not verified. Kaggle rainfall units remain INFERRED; gridded products disagree. Daily storage ends 2020-12-03, so 2021 and 2023 cannot be tested at daily storage resolution. Releases and actual decisions are unobserved. These metrics do not validate flood warning or operational release decisions.
