# Phase 10 risk map — blocked pending an independent accepted label

**Status: BLOCKED; no risk classes, risk GeoTIFF, static risk map, or zonal summaries were generated.** Producing a visually complete map from the current model and calling it calibrated would violate the required held-out-date/event and uncertainty checks.

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
