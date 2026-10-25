# Model card: Phase 9C urban-censored flood susceptibility

## Intended use

Exploratory relative susceptibility screening in the older Chennai Metropolitan Area, on the 30 m master grid. The model ranks where the unchanged November 2015 SAR-derived label is more likely under the observed feature patterns. It is not an operational alert, flood forecast, depth estimate, evacuation instruction, or field-validated flood map.

## Data and method

- Target: the existing Phase 9 union-minus-baseline November 2015 label. It was not changed. This remains a single-event SAR-derived target, not field truth.
- Features: the Phase 9B v2 static cell table and unchanged all-pilot feature set. Training used only assessed cells and the existing nested spatial block procedure, with train-only sampling/calibration and the existing seven single/terrain logistic baselines.
- Chosen model: simple average of tuned random forest, XGBoost and LightGBM probabilities. Five outer spatial folds; one 3 km block buffer; two inner spatial folds; 30 sampled configurations per tree family; seed 20261025. The exact per-fold settings and reproducible command are in [the registry](PHASE9C_MODEL_REGISTRY.json).
- Input SHA-256 values are recorded in [the metrics JSON](PHASE9C_METRICS.json) and registry: feature table `c54c21d8145adde7600d817169b80ebe2d936ce7edae59e2248e40a8280dbf86`; label table `f580f02a7626c2dbad329420d08176d8d19cd126e231846d2fa2c1b690b78052`; Phase 9B metrics `2bcd1ca955ae344d1846d34e73f0d4b8645c2bbaa97e9d1807cbfad8b695684a`.

## Observability and urban limitation

Radar-derived labels are assessed only where built-up fraction is at most 0.50, slope is at most 15 degrees, the reference and event RTC pixels are valid, layover/shadow bits are absent, and slope is available. Of 1,319,380 CMA grid cells, 481,244 are assessed and 838,136 are not assessed from radar labels. The `urban_confidence.tif` layer marks assessed support; excluded cells have no radar probability. Dense urban cells are deliberately censored because radar flood detection is unreliable there. This creates a real coverage gap and must not be read as low risk.

## Evaluation

The assessed set has 481,244 cells and 4.979% positive target prevalence. Nested outer-fold mean ± SD: PR-AUC 0.1945 ± 0.0464 (3 km block-bootstrap 95% CI 0.1212–0.2058), ROC-AUC 0.8219 ± 0.0301, Brier 0.0448 ± 0.0095, and 10-bin ECE 0.0268 ± 0.0188. Pooled OOF metrics are PR-AUC 0.1605, ROC-AUC 0.7538, Brier 0.0448, ECE 0.0071. The model improved paired fold metrics over the seven Phase 9B logistic baselines on the same masked folds, and over a random-prevalence baseline. Against Phase 9B v2, pooled ROC-AUC and PR-AUC are lower, Brier is higher, and ECE is lower; the prior model covered a larger domain (1,078,595 cells), so these are descriptive raw comparisons, not paired model-only effects.

Spatial Mondrian conformal intervals had 93.4% mean outer-fold coverage, with mean width 0.2464 probability units. Coverage was 92.7% for built-up 0–0.1, 96.3% for 0.1–0.3, and 96.1% for 0.3–0.5. There were no observable test cells above 0.5 built-up, so no empirical radar coverage is available for those strata. Overall coverage exceeded the 88% check, but spatial dependence weakens the usual exchangeability interpretation.

## Separate OpenCity point cross-check

The source contains 945 approximate flood points with unclear dates. The points were excluded from fitting, feature selection, calibration, and threshold selection. Only 111 points overlap a scored map (99 radar assessed and 12 physical-only); 834 have no score. Among those 111, the composite apparent rank hit shares in the top 1%, 5%, 10%, and 20% were 0.0%, 0.0%, 0.9%, and 2.7%, compared with chance rates of 0.29%, 1.52%, 3.17%, and 6.67%. Chance draws preserve each point's built-up bin and dominant class among the six land-cover fractions; this is dominant-class mix matching, not exact matching of every fractional composition. The physical-only 12 points had zero hits at each cutoff. This is a poor point-ranking result, not evidence that the risk map is validated. The physical-only screen has values for 14,440 of 597,351 outside-mask cells; the rest remain NoData. Full rates and block-bootstrap intervals by built-up bin are in [the Phase 9C report](PHASE9C_URBAN_CENSORING.md).

## Leakage review

OpenCity observations were not used to fit or tune the model. The flood target was unchanged. Outer test blocks were separated from training by the stated buffer; transformations, negative-cell sampling, tuning, and Mondrian quantiles were derived from training data/inner blocks. The point test is from a separate source but has unclear dates and approximate locations, and most points are not scorable. The flood target still represents one event; apparent full-data rasters are not held-out predictions. No independent event/date validation exists here.

## Claims and limits

This pilot can report spatial discrimination against its one SAR-derived 2015 target inside the radar-observable mask, plus a weak, date-unclear point cross-check on the 111 scorable points. It cannot establish field accuracy, urban flood detection, generalization to other events, future forecasting, causal effects, flood depth, or safe route accessibility. Areas marked not assessed require other observations or independent validation.
