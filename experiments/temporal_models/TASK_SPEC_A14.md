# A14 task specification — H1 modality comparison feasibility

## Registered scope

Assess the registered H1 comparison: weather/rainfall-only, terrain/hydrology-only, SAR-only where defensible, and combined inputs. Use one target and coverage rule with leakage-safe spatial and event splits. Score only accepted, date-matched labels. If independent accepted held-out-event labels are unavailable, report H1 as not testable and provide a feasibility analysis only.

## Fixed decisions for this run

- Target candidates are Tier A `event_flood` records on 2015-11-12 and 2015-11-24. The two dates belong to one 2015 episode; baselines on 2015-09-01 and 2015-10-14 are reference water, not positive events.
- No scoring uses Tier D SAR-derived candidates, undated/approximate OpenCity points, or the preliminary/undigitized 2021 and 2023 PDF map products.
- A future H1 run requires event-wise holdout and 3 km spatial blocks (100 × 100 master cells). A one-block spatial buffer is a provisional conservative choice and must be reviewed before scoring.
- Since only the 2015 episode has accepted flood extent labels, there are no independent held-out events. Do not fit models, select thresholds, or calculate metrics in this run.
- Record source hashes and the reserved reproducibility seed in `batch2_v1/experiment_config.json`. The seed is not consumed because no randomized experiment was run.
