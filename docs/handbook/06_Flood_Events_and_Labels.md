# Flood events and labels

## What a label is

A flood label is a dated map layer that identifies which places were inundated. A label is not a forecast. Model evaluation depends on date-matched, spatially defensible labels; this is the main data risk for TwinGuard. [repo: `docs/PHASE3_PLAN.md`]

## Event evidence available

| Event | Evidence in the repository | What is missing or uncertain |
|---|---|---|
| 2015 Chennai floods | UNOSAT vectors dated 1 Sep, 14 Oct, 12 Nov and 24 Nov; OpenCity incident/hazard KMLs; Global Flood Database event 4309; a 6 Dec 2015 Sentinel-1 scene. [repo: `docs/PHASE3_LOG.md`, `docs/DATA_MANIFEST.csv`] | The UNOSAT vectors stop on 24 Nov and miss the 1–8 Dec peak. GFD ends 4 Dec, is coarse and its centroid is outside CMA. Dec 6 SAR is raw and unprocessed. [repo: `docs/PHASE3_LOG.md`] |
| 2021 Chennai floods | NRSC/NDEM PDF map; Sentinel acquisitions on 23 Oct, 4 Nov and 16 Nov. [repo: `docs/SENTINEL_VERIFICATION.md`, manifest] | PDF requires manual interpretation. The provisional peak is 7 Nov; 16 Nov is post-peak, not direct peak observation. Two 16 Nov slices together cover about 99.98% of the provisional CMA. [repo: `docs/SENTINEL_VERIFICATION.md`] |
| 2023 Michaung | NDEM 7 Dec 2023 preliminary PDF map, plus a separate 18 Dec Tuticorin sheet; Sentinel scenes on 18 and 30 Nov. [repo: manifest, `docs/SENTINEL_VERIFICATION.md`] | Map is a PDF and needs digitising. Sentinel scenes are before the provisional 4 Dec peak; no post-peak candidate was found in saved catalogue. Supplied NRSC Michaung URLs are not collected. [repo: `docs/SENTINEL_VERIFICATION.md`, `docs/MANUAL_TODO.md`] |

## 2015 exploratory label measurements

UNOSAT areas from the grid-based inspection are **46.4184 km²** (1 Sep reference), **51.7401 km²** (14 Oct reference), **84.7755 km²** (12 Nov), and **98.1603 km²** (24 Nov). The November union is **126.3915 km²**. Removing pixels in either September or October reference produces **80.5905 km²**, with 50,890 overlapping cells. This is only a test: baseline classes include detected water and possible saturated/wet soil, so the subtraction is not a validated water/flood distinction. [repo: `data/processed/labels_inspection/label_inspection_summary.json`]

The separate geometric coverage check reports **84.924564 km²** on 12 Nov and **98.313748 km²** on 24 Nov, with the corresponding flood polygons covering **7.151781%** and **8.279329%** of the 1,187.460287 km² CMA. Those figures use dissolved source geometries intersected with the CMA; they are not the rasterized areas above. No ground validation was performed. [repo: `docs/COVERAGE_2015.md`]

## Global Flood Database comparison

Event 4309 spans **10 Nov–4 Dec 2015**. The inspection counted **1,082** flooded-band pixel centres inside CMA, approximately **65.43 km²** using nominal local cell area. Nominal pixel scale is about **244 by 248 m** near Chennai, and the event centroid lies outside CMA. This is a regional cross-check only; it does not establish the local Dec 1–8 extent. The archive notes CC BY-NC 4.0. [repo: `data/processed/labels_inspection/label_inspection_summary.json`, `docs/DATA_MANIFEST.csv`]

## Recommended label discipline

The requested `docs/LABEL_STRATEGY.md` is **not present** in the repository. Do not claim a recommendation from it. The available plan recommends keeping observed, manually digitised and algorithm-derived labels separate; it says November 2015 is not a proxy for December and that baseline subtraction is only an idea to verify. [repo: `docs/PHASE3_PLAN.md`]

If December 2015 labels remain unavailable, the plan lists three fallback options: (1) digitise suitable NRSC PDFs with georeferencing error and uncertainty recorded; (2) derive a separately validated Sentinel-1 label; or (3) narrow validation to observed dates and explicitly state that the December peak is unvalidated. These options are not equivalent evidence. [repo: `docs/PHASE3_PLAN.md`]

## Sentinel-1 acquisition inventory

All listed ZIPs passed CRC/integrity checks and SAFE filename/start-stop consistency checks. The role descriptions below are relative to provisional event timing; the scenes are not flood labels. Coverage numbers are from the verifier. [repo: `docs/SENTINEL_VERIFICATION.md`]

| Date | ZIP filename | Event role | Relative orbit / direction | CMA coverage | Size (bytes) | Verification |
|---|---|---|---|---:|---:|---|
| 2015-10-19 | `S1A_IW_GRDH_1SDV_20151019T003131_20151019T003200_008214_00B8EF_82E0.zip` | Pre-event reference | 92 / descending | 100.00% | 1,131,643,380 | PASS |
| 2015-11-24 | `S1A_IW_GRDH_1SDV_20151124T003120_20151124T003149_008739_00C723_AB80.zip` | November event-date context; not December peak | 92 / descending | 100.00% | 1,169,775,048 | PASS |
| 2015-12-06 | `S1A_IW_GRDH_1SDV_20151206T003120_20151206T003149_008914_00CC1F_BEF9.zip` | Acquisition within 1–8 Dec window | 92 / descending | 100.00% | 1,150,452,618 | PASS |
| 2021-10-23 | `S1A_IW_GRDH_1SDV_20211023T003148_20211023T003213_040239_04C461_42A6.zip` | Pre-event slice 1 | 92 / descending | 27.69% | 927,101,248 | PASS |
| 2021-10-23 | `S1A_IW_GRDH_1SDV_20211023T003213_20211023T003238_040239_04C461_000E.zip` | Pre-event slice 2 | 92 / descending | 72.28% | 957,157,303 | PASS |
| 2021-11-04 | `S1A_IW_GRDH_1SDV_20211104T003147_20211104T003212_040414_04CA78_AD56.zip` | Pre-peak slice 1 | 92 / descending | 27.64% | 949,221,959 | PASS |
| 2021-11-04 | `S1A_IW_GRDH_1SDV_20211104T003212_20211104T003237_040414_04CA78_20F6.zip` | Pre-peak slice 2 | 92 / descending | 72.33% | 971,508,991 | PASS |
| 2021-11-16 | `S1A_IW_GRDH_1SDV_20211116T003147_20211116T003212_040589_04D094_DB41.zip` | Post-peak slice 1 | 92 / descending | 27.65% | 950,601,405 | PASS |
| 2021-11-16 | `S1A_IW_GRDH_1SDV_20211116T003212_20211116T003237_040589_04D094_B07B.zip` | Post-peak slice 2 | 92 / descending | 72.32% | 968,021,659 | PASS |
| 2023-11-18 | `S1A_IW_GRDH_1SDV_20231118T003202_20231118T003227_051264_062F3A_F481.zip` | Pre-event slice 1 | 92 / descending | 86.51% | 1,718,019,055 | PASS |
| 2023-11-18 | `S1A_IW_GRDH_1SDV_20231118T003227_20231118T003252_051264_062F3A_94DE.zip` | Pre-event slice 2 | 92 / descending | 13.47% | 1,717,956,919 | PASS |
| 2023-11-30 | `S1A_IW_GRDH_1SDV_20231130T003201_20231130T003226_051439_06353D_343D.zip` | Pre-peak slice 1 | 92 / descending | 86.44% | 1,718,001,615 | PASS |
| 2023-11-30 | `S1A_IW_GRDH_1SDV_20231130T003226_20231130T003251_051439_06353D_9270.zip` | Pre-peak slice 2 | 92 / descending | 13.54% | 1,718,041,540 | PASS |

Counts by on-disk year folder: 2015 **3**, 2021 **6**, 2023 **4**. The repository’s raw-audit report says all 13 archives matched their logged sizes and hashes. The actual folder on disk is `sentinel1`; manifest rows and older notes say `senitnel1`. Preserve files; reconcile metadata paths without renaming the raw folder. [repo: `docs/SENTINEL_VERIFICATION.md`, `docs/PHASE3_LOG.md`, `docs/DATA_MANIFEST.csv`]
