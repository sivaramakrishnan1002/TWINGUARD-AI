# Spatial validation split strategy

This is a plan for later model evaluation, not a model run. `data/processed/alignment/spatial_blocks.tif` assigns each CMA cell a fixed block ID on the existing 30 m EPSG:32644 grid. A block is exactly 3,000 m × 3,000 m (100 × 100 cells); cells outside the CMA mask are 0. Block IDs follow the master-grid origin, not the CMA boundary. The current raster has 164 block IDs intersecting the CMA, with 10–10000 CMA cells per block (edge blocks are partial).

## Evaluation rules

- Use leave-one-event-out evaluation across 2015, 2021 and 2023: hold out one event in full, train on the other available event(s), and repeat. Keep label tiers separate and do not treat modelled/coarse labels as equivalent to official vectors.
- Within an event, use spatial-block cross-validation: assign whole block IDs to folds so adjacent cells do not split randomly across train and test. Keep any temporal grouping intact as well.
- Fit scaling, normalization, imputation values and feature selection using training rows only; apply the fitted values unchanged to validation/test rows.
- Exclude any feature derived from the label raster, post-event imagery, future rainfall, or future reservoir observations from a forecast made before that time. Keep provenance and observation timestamps with every predictor.

## Leakage checklist

1. Temporal: predictor timestamps precede the target time; daily and hourly calendars use the source's recorded timezone; no later observations leak into earlier predictions.
2. Spatial: every cell in one spatial block stays in one fold; overlapping neighbourhood summaries do not cross the split unnoticed.
3. Label-derived: no flood extent, baseline subtraction, or digitised map attribute is reused as a predictor for the same label.
4. Preprocessing: normalization and any learned transformation are fitted only on training data.

Only three historical events are available, labels have uneven dates and confidence, the 2015 December peak lacks official vector truth, and the 2021/2023 references require PDF digitising. Scores will therefore have high sampling uncertainty and cannot establish general performance across all floods or years.
