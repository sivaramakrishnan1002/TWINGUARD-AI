# Lane A addendum CR-004 — Phase 9C eligibility, hazard features, and Phase 10 mask

**Owner:** Lane A. **Task:** reopen existing A04b; preserve the committed Phase 9C run. **Date:** 2026-10-25.

## Constraints

- Keep `data/raw` read-only. Do not download/install packages, use Docker, or write to the database.
- Do not overwrite Phase 9, 9B, earlier Phase 9C, or existing Phase 10 products. Use `data/features/predictions/phase9c_addendum_cr004/` and `data/features/predictions/phase10_cr004/`.
- WorldPop is exposure only: it cannot define hazard-model eligibility or appear as a hazard predictor. Exclude road-node distance and building density from all hazard models.
- Use existing buffered 3 km spatial folds, one-block training buffer, training-only sampling and calibration, full-prevalence evaluation, fixed seeds, and no hyperparameter searches. Use default random forest as the reference and default average tree ensemble only as an option.
- Preserve the unchanged Phase 9 label. State clearly that the target is radar-visible flooding, based on a single SAR-derived November 2015 event, and not field truth or a forecast.
- Never display `.env`, environment variables or connection strings. No Docker commands.

## E1 eligibility audit

Explain the 25,551 positive cells removed by the earlier population-NoData mask. Report cell counts by dominant land-cover class, built-up bin, distance-to-water and coast bins, 3 km block, and within/outside radar observability. Inspect the source population raster and metadata in a read-only way; distinguish known NoData semantics from inference about why individual locations are missing. Do not infer settlement status solely from NoData. Rebuild model eligibility as unchanged Phase 9 target eligibility plus C1 observability, with population-NoData retained only as an exposure-data quality flag.

## E2/E3 hazard models and reporting

Compare fixed feature sets with default random forest on identical outer folds: (A) terrain and hydrology; (B) A plus tree/crop/grass/bare fractions, excluding built-up fraction; (C) B plus built-up fraction. Exclude WorldPop, distance to road nodes, building density, and all other exposure proxies. Keep the default tree average as a separately reported option; no tuning.

For every evaluation domain or stratum, report cell count, prevalence, PR-AUC and lift (`PR-AUC / prevalence`). Re-run dense-urban exclusion and compare lift. Within each built-up bin, report precision and recall in the top 1%, 2%, 5% and 10% of scored cells. Include fair same-fold baseline comparisons and fixed-seed details.

## E5 preserved checks

Keep the observability definition (dense urban, steep terrain, missing/layover/shadow radar), OpenCity validation with date/location caveats and matched-chance bootstrap, spatial-block built-up-stratified conformal recalibration, separate physical complement for unobservable cells, and updated model card. The model card must say “describes radar-visible flooding.” No observed truth or independent-event performance claim.

## E6 Phase 10 view

Create a new combined display raster: data-driven apparent hazard classes only inside the observability mask. Outside it, display the separate PHYSICAL complement and an explicit unreliable-from-labels flag. Keep the physical score separate from radar probability; do not blend or relabel it as probability. Retain existing Phase 10 outputs unchanged.

## Outputs and checks

- Metrics/report, registry and lineage under `docs/PHASE9C_ADDENDUM_CR004*` and `docs/MODEL_CARD_SUSCEPTIBILITY_CR004.md`.
- New model rasters under `data/features/predictions/phase9c_addendum_cr004/`.
- New Phase 10 composite display under `data/features/predictions/phase10_cr004/`.
- Script and tests under `pipelines/phase9c/` and `tests/phase9c/`.
- Tests must cover no exposure feature leakage, eligibility retaining population-NoData labels, prevalence/lift arithmetic, built-up top-share metrics and composite-mask routing.
- Refresh lineage and run raw audit. Commit Lane A-owned scripts/tests/docs only; no data outputs in Git.

