# Batch 1 defaults to confirm

| ID | Decision / options | Default used | Reason | How to change |
|---|---|---|---|---|
| B1-D1 | SAR water/dry threshold: distribution midpoint, Otsu, or another physical rule | Midpoint of sample medians per polarization; DERIVED screening threshold | Transparent, reproducible summary of class distributions without fitting to an event flood label | Replace the method and rerun `python -m pipelines.phase8.physics_thresholds`; preregister any evaluation gate before comparing against UNOSAT |
| B1-D2 | Stable-dry change bound k | k=2 standard deviations below the mean | Conventional descriptive lower-tail screen; not scientifically validated for Chennai | Select a different k before T3, document why, and rerun thresholds and downstream fixed-rule evaluation |
