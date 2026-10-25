# Lane A task A04b — Phase 9C

**Title:** Phase 9C: urban label censoring, independent point validation, spatial conformal fix  
**Owner:** Lane A  
**Depends on:** A04 (Phase 9B model upgrade)  
**Change request:** CR-002  
**Status:** implemented with caveats; Lane A checks passed

## Constraints

- `data/raw` is read-only. No downloads, network access, package installs, credentials, Phase 10, database work, or edits to prior outputs.
- Keep Phase 9 target labels and Phase 9B model outputs unchanged. All new model outputs go under `data/features/predictions/phase9c/`; scripts and tests go under `pipelines/phase9c/` and `tests/phase9c/`.
- Use the same nested spatial folds, one-block spatial buffer, training-only sampling/calibration/thresholding, and same baselines as Phase 9B. Evaluate only eligible cells inside the defined radar observability mask.
- Outputs are susceptibility associations against the November 2015 SAR-derived target, not forecasts or field truth.

## Acceptance

1. Define and document an observability mask from the existing feature table and SAR quality masks: censor dense built-up cells at a stated cutoff, layover/shadow, and steep terrain at a stated slope cutoff. Outside it, report `not assessed from radar labels`. Record cell counts and reasons. Retrain/evaluate inside the mask with nested spatial CV and the same baselines, reporting PR-AUC, ROC-AUC, Brier, ECE, and block-bootstrap confidence intervals, plus comparison with Phase 9B.
2. Validate rankings against the 945 approximate, undated OpenCity observed flood points. Report point-hit shares in top 1%, 5%, 10%, and 20% risk cells overall and by built-up bin, with land-cover-mix-matched chance expectation and bootstrap confidence intervals. Describe the spatial/date limitations.
3. Apply spatial-block Mondrian conformal calibration stratified by built-up bin; report coverage and band width per stratum, plus pooled results. If coverage is below 88%, state it plainly.
4. Produce a separate physical susceptibility layer for cells outside the observability mask using HAND, local depression depth, TWI, and distance to drainage. Label it `PHYSICAL, NOT FITTED TO LABELS`; report the same point-validation hit rates.
5. Write `docs/MODEL_CARD_SUSCEPTIBILITY.md`, an updated model registry, metrics/report, tests, lineage, and audit evidence. Include intended use, data, performance, uncertainty, urban limits, leakage review, and claims/limits.

## Inputs and new outputs

- Inputs: Phase 9B v2 feature table, Phase 9 unchanged target and split definition, existing Sentinel quality masks/terrain and 945 OpenCity points, Phase 9B metrics/registry.
- New rasters and tabular metrics: `data/features/predictions/phase9c/`.
- Scripts: `pipelines/phase9c/`; tests: `tests/phase9c/`.
- Documentation: `docs/PHASE9C_*.md`, `docs/PHASE9C_*.json`, `docs/MODEL_CARD_SUSCEPTIBILITY.md`, and figures in `docs/figures/phase9c/`.

## Completion evidence

- `docs/PHASE9C_URBAN_CENSORING.md` documents the observability mask, nested CV, baseline comparisons, OpenCity points and matched chance intervals, stratum-specific conformal coverage, and the physical complement.
- `docs/MODEL_CARD_SUSCEPTIBILITY.md`, `docs/PHASE9C_METRICS.json`, `docs/PHASE9C_MODEL_REGISTRY.json`, and `docs/PHASE9C_LINEAGE.md` record intended use, metrics, parameters, hashes, provenance, and limitations.
- The new raster outputs are under `data/features/predictions/phase9c/`; no Phase 9 target or previous output was changed.
- OpenCity audit: 945 source points, 111 scored (99 radar and 12 physical-only), 834 unscored. Overall top 1/5/10/20% point hits are 0.0/0.0/0.9/2.7%, below matched chance rates 0.29/1.52/3.17/6.67%.
- Spatial Mondrian nominal 90% interval coverage is 93.4% mean across outer folds (mean band width 0.2464); high-built-up strata have no radar-assessed cells and therefore no coverage estimate.
- Phase 9C focused tests: 5 passed. Full repository suite: 69 passed, one warning. Raw audit: 157/157 hash matches, no mismatches. Canonical lineage refreshed with 243 derived files.
- Caveats: this is a single SAR-derived November 2015 event; OpenCity dates are unclear and locations approximate; only 111/945 points can be scored; the point-ranking result does not beat matched chance; physical complement support is limited to 14,440 of 597,351 eligible outside-mask cells.

