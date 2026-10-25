# Batch 1 T3: Flood Rule v2 candidate

**Status:** DERIVED screening candidate only; not evaluated against an event label yet, not accepted, and not field-validated. The method consumes the frozen pre-event distribution defaults in `T2_PHYSICS_THRESHOLDS.json`. It does not read an event UNOSAT layer.

## Fixed rule

For each polarization, a pixel passes only when both the event backscatter is below its pre-event water/dry median-midpoint and event-minus-reference dB change is below the stable-dry mean-minus-2-SD screen:

| Parameter | VV | VH |
|---|---:|---:|
| Event water threshold | -12.933 dB | -19.959 dB |
| Change threshold | -3.001 dB | -1.805 dB |

Exactly one complete polarization pass is classed medium confidence; both are high. A candidate is either confidence class. Reference dates use the mean of the existing Lee-filtered RTC linear-power rasters, converted to dB after averaging. For this first test, 24 Nov 2015 is compared with 19 Oct 2015.

Eligibility masks: WorldCover class 80 or either official baseline-water layer is excluded; common CMA/SAR-valid and layover-shadow-valid cells only; cleaned-DEM edge-safe slope ≤5°; D8 HAND ≤5 m; built-up fraction ≤0.5; and an 8-connected 5-cell minimum component area (0.0045 km²). The stream definition is D8 accumulation ≥100 cells (0.09 km² upstream area). These terrain thresholds are **DEFAULT, to confirm**. The HAND calculation uses the first downstream cell at or above that accumulation threshold and the cleaned GLO-30 DSM.

## Pilot output before any acceptance comparison

| Quantity | Result |
|---|---:|
| CMA cells | 1,319,380 |
| Common-valid event/reference SAR cells inside CMA | 1,319,255 |
| Permanent-water cells excluded | 110,788 |
| Cells passing all eligibility masks | 13,533 (1.03% of CMA cells) |
| HAND-valid CMA cells | 25,196 (1.91%); 51,385 across the full valid terrain context |
| 8-connected candidate components before sieve | 24 |
| Components retained after 5-cell sieve | 14 |
| Candidate flood area | 0.2178 km² (242 cells) |
| Confidence | 175 high cells; 67 medium cells |

The low HAND coverage is a serious limitation of the available D8 flow product: 1,711,385 of 1,762,770 valid terrain cells do not reach a threshold stream under its directions. Accumulation ranges only to 682 cells, so a 1,000-cell stream definition generated no drainage cells; 100 was chosen before event-label evaluation because it yields 1,511 streams. This is an explicitly provisional response to the local accumulation range, not hydrologic calibration. Only 25,196 CMA cells (1.91%) have a HAND value and 13,533 (1.03%) pass all rule masks. The very small candidate area does not demonstrate the method is accurate.

The current candidate is saved as `data/features/labels/label_2015-11-24_rule_v2_20261025_03_DERIVED.tif` plus a confidence raster; the HAND intermediate is `data/processed/sar_work/hand_d8_100cells_20261025_03_DEFAULT.tif`. It is tier D after the preregistered T4 evaluation and is not returned by `labels.v_usable_flood_labels`. An initial 1,000-cell stream trial had no streams and zero eligible cells. Candidate run `20261025_02` was superseded after T4 found that finite slope NoData sentinel −9999 passed the ≤5° test. T3 now excludes it; the versioned `20261025_03` candidate is the valid run. The initial temporary T3 output path was reused during that in-task repair; later outputs use unique run ids and the script refuses overwrite. No raw files were involved.

## Limits

The cleaned GLO-30 surface is a DSM with building/tree returns; the lower-slope filter does not remove all urban artifacts. The HAND method depends on a D8 surface with many sinks/outlets. Current denominators are raster cells and are not independent observations. No model performance metric or ground-truth claim is made here. T4 must preregister the acceptance rule and then compare to UNOSAT; possible use of the same SAR scene means that comparison is not independent physical validation.

Reproduce with `.venv/Scripts/python.exe -m pipelines.phase8.flood_rule_v2 --run-id 20261025_03` (choose a fresh run id for subsequent runs; the script refuses to overwrite outputs). Numeric summary: `T3_FLOOD_RULE_V2_20261025_03.json`; implementation: `../pipelines/phase8/flood_rule_v2.py`.
