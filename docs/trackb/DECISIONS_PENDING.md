# Track B decisions pending

| ID | Options | Default | Reason | How to change |
|---|---|---|---|---|
| TB-01 | Target horizon 3/7/14 days | DEFAULT, to confirm: 7 days | Useful short warning horizon; sensitivity grid requested | Set `N` in analysis parameters and recompute the full sensitivity table |
| TB-02 | High capacity fraction 0.70/0.80/0.90 | DEFAULT, to confirm: 0.80 | Existing exploratory artifact uses 80% | Set fraction parameter and recompute labels/metrics |
| TB-03 | Container image tags | DEFAULT, to confirm: no tag selected | Avoid guessing unverified image versions | Confirm a tag for each service, set environment variables and pull using RUNBOOK commands |
| TB-04 | Kafka retention | DEFAULT, to confirm: rain 30d, reservoir 90d, twin 30d, alerts 365d | Operationally conservative initial proposal; undeployed | Change topic retention before deployment |
| TB-05 | Rule-level cutoffs and deterministic confidence | DEFAULT, to confirm: watch 70%, warning 80%, critical 90%; confidence is satisfied-indicator fraction | Transparent tie to capacity bands; score must not imply a calibrated probability | Change rule config, rerun held-out analysis, and retain the explicit confidence semantics |
