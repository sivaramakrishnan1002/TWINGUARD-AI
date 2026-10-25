# Phase 10 risk map — prior status and CR-003 pilot update

**Historical status:** the earlier task was blocked because independent-event validation was unavailable. The following sections preserve that original rationale. A CR-003 apparent, single-event pilot has since been generated as a separate product; it does not satisfy independent-event validation and is not a forecast.

## Why this is blocked

The accepted-label view currently contains only tier A reference layers dated 2015-09-01 and 2015-10-14 (baseline water) and 2015-11-12 and 2015-11-24 (the two event maps from one November 2015 flood). The 6 Dec 2015 and 16 Nov 2021 fixed-rule candidates are tier D. The 2021 NRSC product is a PDF that has not been georeferenced/digitized; 2023 has only map/PDF references and no post-peak SAR-derived label. The coarse Global Flood Database product and date-uncertain OpenCity records are not accepted event labels.

The Phase 9 model trained on the 2015 union target, which includes both 12 and 24 November labels. It cannot be scored against either of those dates as an untouched holdout. Reusing its out-of-fold spatial scores or its full-data bootstrap maps as an out-of-event score would be leakage or a different evaluation question. No accepted A/B/C flood label exists for another date/event, so there is no defensible test set for Phase 10's required out-of-event evaluation.

## What Phase 9 does and does not establish

The Phase 9 blocked spatial CV reports that its selected random forest has PR-AUC 0.3415, ROC-AUC 0.8911, F1 0.3499, IoU 0.2143, Brier 0.0398 and ECE 0.0093 across the 2015 union target. It beats the reported PR-AUC baselines on those same splits: elevation-only 0.0515, river-distance-only 0.0465, and random 0.0512. Those results are one-event spatial holdout results, not a held-out date/event result.

The full-grid Phase 9 5th–95th percentile rasters are from a 20-fit bootstrap on the full 2015 union data. No coverage test against held-out labels is recorded. The intervals describe bootstrap model spread, not label, source, or event uncertainty; calibration for a new event is unverified. The Phase 9 report also notes that its threshold is selected on in-sample training-fold predictions, which may be optimistic. No Phase 10 calibrated risk classes are justified from these outputs.

## Unblocking steps

1. Georeference/digitize the NRSC 13 Nov 2021 map and the available 2023 map in a separate validation workspace. Record map coverage, georeferencing residuals, digitizing uncertainty, and dates. The December 2015 peak remains without an official vector layer.
2. Keep each new map-only layer tier D until its source and validation justify promotion. Obtain an accepted tier A/B/C extent for an event/date not used in the Phase 9 fit; the accepted view must expose that provenance and event date.
3. Retrain/revalidate with spatial blocks and a buffer, train-only preprocessing and sampling, full-prevalence evaluation, thresholds fixed on training data, same-split baselines, all required metrics, and a leakage/physical review. Evaluate on the independent accepted event/date.
4. Test the 5th–95th uncertainty interval's coverage on that held-out reference. If it under-covers, report that and do not label the output calibrated.
5. Only after those checks, define and document risk-class cut points, generate population/facility/road-length summaries, and make the map. Preserve WorldPop NoData as unknown and use 3 km blocks; the repository has no ward boundaries.

**Plain-language limit:** the existing model can rank some 2015 locations as more susceptible than others within this one mapped event. It has not shown that its probabilities or risk classes transfer to another flood, year, or live forecast.

## CR-003 update (2026-10-25)

The user approved a bounded Phase 10 pilot that explicitly leaves out-of-event validation pending. Two apparent class maps were generated from the Phase 9B v2 full-data probabilities and Phase 9C radar-observable probabilities, using fixed descriptive cut-points `<0.05`, `0.05–<0.10`, `0.10–<0.25`, and `>=0.25`. These are not operational alert thresholds. Phase 9C cells outside its radar-observability mask remain not assessed; its physical complement is kept separate from probability maps.

The machine-readable details, class-by-block zonal statistics, uncertainty layers, OpenCity point cross-check, and limitations are in [the CR-003 report](PHASE10_RISK_MAP_CR003_V3.md), [the summary JSON](PHASE10_RISK_MAP_CR003_V3.json), and [the lineage note](PHASE10_RISK_MAP_LINEAGE_CR003.md). The PNG is [phase10_risk_map_cr003_v3.png](figures/phase10_risk_map_cr003_v3.png). The 120 m generalized MVT tiles are under `data/processed/tiles/phase10_cr003_v3/`; 30 m analysis GeoTIFFs are under `data/features/predictions/phase10_cr003_v3/`.

The point cross-check remains weak: 111 of 945 approximate, undated OpenCity points had usable map scores; 0/111 fell in the top 1% or 5%, 1/111 in the top 10%, and 3/111 in the top 20% of the Phase 9C composite ordinal rank. This is not date-matched validation. Road length by zone uses whole-edge midpoint allocation and is approximate. Phase 9B's nominal 90% band under-covered (85.8%) in within-event blocked validation; Phase 9C reported 93.4%, also not independent-event coverage. No model or map is accepted for future-event or operational use. Digitised independent maps remain the next evidence needed.
