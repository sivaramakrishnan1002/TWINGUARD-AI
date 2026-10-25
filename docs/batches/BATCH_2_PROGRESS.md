# Batch 2 Lane A progress

| Task | Status | Commit | Notes |
|---|---|---|---|
| S0 Spec loading and dependency reconciliation | done | — | Specs/dependencies registered; protocol checks pending. |
| A04c / S1 Urban physical layer | done_with_caveats | e357478 | 1,175,660 CMA cells scored; 927 points scored; OpenCity points are undated/approximate. |
| A03d / S2 GeoPDF labels and 2023 out-of-event evaluation | done_with_caveats | b55ccb3 | 2023 WGS84 GeoPDF red class extracted/polygonised; preliminary only because exact OSM control-point RMS is not available. 2021 UTM45/GPTS CRS conflict is manual-needed; Dec 2015 maps absent. |
| A04d / S3 Calibrated SAR labels | done_with_caveats | pending commit | Pooled buffered OOF IoU 0.5977 permits a Tier C map-reproduction candidate only. VV-only slightly outperforms full features. The same-scene UNOSAT comparison may be circular; applied outputs are Tier D. v2 enforces eligibility; v1 preserved but superseded. |
| A06 / S4 2D simulation | blocked | — | Depends on A04c and A03d. |
| A05 / Forecast and hindcast wrapper | blocked | — | Depends on A06. |
| A07 / Impact | blocked | — | Depends on A05 and A06. |
| A08 / Time-dependent graph | blocked | — | Depends on A07. |
| A09 / Routing | blocked | — | Depends on A05 and A08. |
| A10 / Shelter allocation | blocked | — | Depends on A07, A08 and A09. |
| A11 / Priority zones | blocked | — | Depends on A07 and A10. |
| A12 / Explainability | blocked | — | Depends on A04, A04d and A06. |
| A13 / Decision lab | blocked | — | Depends on A05, A09, A10, A11 and A12. |

## Defaults and scope notes

- WorldPop NoData remains a missing-exposure flag; never use it to censor hazard eligibility.
- The urban physical layer is not fitted to flood labels.
- Physical simulation output is a calibration proxy, not hydraulic truth.
- New work preserves all previous model, label and map artifacts.

