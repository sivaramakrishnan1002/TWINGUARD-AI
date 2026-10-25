# Model card — radar-visible flood susceptibility (CR-004)

## Intended use
Research-only comparison of relative susceptibility to the unchanged Phase 9 November 2015 SAR-derived flood label, for cells where the input radar observations can assess flooding. The model describes radar-visible flooding. It is not an operational forecast, evacuation clearance tool, flood-depth estimate, or field-validated map.

## Data and method
The target is the existing Nov 12/24 union-minus-baseline label from Phase 9; no labels were edited. Phase 9 eligibility contains 1,196,300 cells. WorldPop NoData is not a hazard eligibility mask and is not a hazard predictor; population is reserved for exposure analysis. Model assessment is limited to 574,018 radar-visible cells: valid reference/event RTC, no layover/shadow flag, built-up fraction <=0.50, valid slope <=15 degrees. Spatial validation uses five buffered 3 km folds, training-only preprocessing/calibration, and a fixed 3:1 negative sample during training.

The reference is default random forest, seed 20261025, with terrain/hydrology plus tree/crop/grass/bare/built-up fractions. It excludes population, road-node distance, and building density. No hyperparameter search was run. A default average tree ensemble remains an optional comparison, not the selected reference.

## Performance
At true evaluation prevalence 6.65%, the reference pooled PR-AUC is 0.219 (lift 3.29); fold mean PR-AUC 0.228 (SD 0.051; five-fold t interval 0.165–0.292), ROC-AUC 0.801 (SD 0.020), Brier 0.0577 (SD 0.0149), and fold ECE mean 0.034 (SD 0.023). It exceeded same-fold pooled PR-AUC for the elevation-only, named-waterway-distance-only, and random baselines. OpenCity points are dates-unclear and approximate: 99 points were scored in the radar-visible domain; top-share hits did not outperform matched chance overall.

Built-up-stratified spatial conformal outer-fold mean coverage was 91.6–91.9% in the three observable built-up strata; mean interval widths were 0.260–0.591. There is no observable-data coverage claim above built-up 0.50, because those cells were excluded.

## Uncertainty and urban limitation
The model does not assess dense built-up cells above 0.50, steep/missing-slope cells, or missing/layover/shadow radar cells. These locations are flagged unreliable from radar labels and shown with a distinct PHYSICAL complement (HAND, local depression depth, TWI, drainage distance); that score is not fitted to labels and is not a probability. OpenCity point dates are unknown. WorldPop NoData cell causes are not established by raster metadata.

## Leakage review
- No population, road-node-distance, or building-density predictors are used.
- Spatial folds are buffered; model fitting, sampling and calibration use training folds only.
- The label is derived from one SAR event and may share source observations with the radar features. This is a material label-leakage/measurement-dependence risk.
- Built-up fraction is included only in feature set C and may proxy radar visibility; the urban observability mask limits but does not eliminate this concern.
- The OpenCity points are spatially independent of the SAR label but have unclear dates and approximate locations; their hit rate was at or below matched chance.
- Full-data rasters are apparent maps; outer-fold metrics are the reported validation.

## Claims
Can: compare relative scores against this one SAR-derived label inside the stated observability domain.
Cannot: claim field truth, forecast skill, performance in dense urban/layover areas, generalisation across events, calibrated absolute flood probability for deployment, or safe/unsafe road status.

## Registry
See docs/PHASE9C_ADDENDUM_CR004_V6_MODEL_REGISTRY.json for parameters, seed, feature/label hashes, sampling and reproducible command. Metrics and detailed audit: docs/PHASE9C_ADDENDUM_CR004_V6.json.
