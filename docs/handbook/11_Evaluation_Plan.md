# Evaluation plan

This chapter proposes experiments; none has been run. Choose thresholds after observing baseline performance, and keep whole flood events separated between training and test wherever possible. With only three major event years, results will have high uncertainty and limited generalisation. [user]

| Claim | Experimental design and baseline | Candidate measures | Data needed / success definition |
|---|---|---|---|
| H1: Multiple modalities help. | Compare rainfall-only with terrain, land cover, SAR and combined inputs under the same event/time splits. | F1, intersection over union (IoU), critical success index (CSI), precision/recall, event-wise scores. | Date-matched labels and consistent coverage. Success means reproducible improvement on held-out events; set threshold after baseline. |
| H2: Explicit uncertainty improves calibration. | Compare point prediction with probabilistic or interval prediction. | Reliability diagrams, calibration error, Brier/log score where suitable, interval coverage and width. | Enough independent observations; define calibration bins/coverage before evaluation. |
| H3: Uncertainty-aware impacts support safer routes. | Compare routes from deterministic flood maps against route costs based on flood probability/uncertainty. | Route failure rate, expected exposed population, expected travel time and uncertainty. | Validated graph, dated road-flood intersections and realistic route outcomes. |
| H4: Horizon-aware routing reduces route failure. | Compare safest-now route against a route scored over expected journey duration. | Fraction of journeys with a closure, delay, exposure and arrival success. | Time-varying flood/closure evidence and plausible departure/duration model. |
| H5: Counterfactual twin improves decisions. | Compare static map decisions with structured alternatives: bridge closure, earlier departure, unavailable shelter. | Decision regret, people reaching safety, expected risk and time. | Explicit objective weights, scenario assumptions and user/operator review. |
| Track B warning lead | Retrospective storage/rain rule against event chronology; compare rainfall-only and storage-only rules. | Lead time, missed-event rate, false-alarm rate only when outcomes are labelled, precision. | Historic capacity and releases, complete daily outcome labels. Current report gives no validated false-alarm rate. |

## Validation rules

- Split by whole event or time block; never randomly mix adjacent hours from one event across train and test. [user]
- Preserve a final held-out event where feasible. “Leave-one-event-out” means train on two event years and test on the third, rotating which one is held out. With only three events this gives a small, fragile evidence base. [user]
- Report coverage and the dates/places that lack labels. A large map footprint is not proof that unlabelled cells were dry. [repo: `docs/COVERAGE_2015.md`]
- Compare against simple, interpretable baselines before Transformers, vision encoders or graph neural networks. [user]
- Report uncertainty and subgroup/area performance, not only one aggregate score. [user]
- Predefine the target event window and label semantics. November 2015 observations cannot stand in for the December peak. [repo: `docs/PHASE3_PLAN.md`]

Success thresholds remain **[TO BE FILLED]** after baselines. No metric result in this chapter is a measured project result. [user]
