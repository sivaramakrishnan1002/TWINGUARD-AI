# SAR candidate application to 6 Dec 2015 and 16 Nov 2021

> **Superseded run:** this first application did not enforce the predeclared `eligible_for_model` mask. Keep these numbers only as run history; use [the corrected v2 report](SAR_CALIBRATED_LABELS_BATCH2_APPLIED_V2.md) and the rasters in `applied_v2/`.

The unchanged 24-Nov model passed its preregistered reproduction gate (spatially buffered OOF IoU 0.598 >= 0.25). This permits only a **Tier C candidate** for map reproduction; both later-event rasters remain **DERIVED Tier D pending independent validation**.

One OOF threshold of 0.40 was applied without retuning.

| Event | Valid CMA cells | Candidate area (km², 30 m grid approx.) | OpenCity top 1% / 5% / 10% / 20% hit share |
|---|---:|---:|---|
| 2015-12-06 | 1,103,964 | 19.36 | 0.00% (n=877) / 0.11% (n=877) / 0.23% (n=877) / 0.91% (n=877) |
| 2021-11-16 | 1,103,971 | 9.23 | 0.00% (n=877) / 0.00% (n=877) / 0.11% (n=877) / 0.91% (n=877) |

## Cross-checks and limits

The Global Flood Database event 4309 reference area is 65.43 km² and its event ends 4 Dec 2015, but no local GFD raster was found; therefore the only comparison available here is area context (not spatial overlap). The NRSC 2021 PDF was not used because its GeoPDF CRS ambiguity remains manual-needed. OpenCity point locations are approximate and dates unclear, so those hit shares are not event validation.

For 6 Dec 2015, dB-change inputs use 19 Oct 2015 to match the trained feature definition; 24 Nov is checked only as a prior-scene context. For 2021, 4 Nov is the model input baseline and 23 Oct is a second reference context only. These temporal differences limit transfer. The 24 Nov label may use the same event SAR scene, making the high reproduction score circular. No maps were loaded into the label database and no output is ground truth.
