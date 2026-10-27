# Stage 8 label dataset registry

All SAR-derived layers are **DERIVED**, never ground truth. The machine-readable inventory is `data/features/labels/label_registry.json`; it contains dates, sources, methods, validation results, tiers, limits and selected output paths.

## Tier definitions

- **A** — official vector product; not necessarily field-validated.
- **B** — SAR-derived and compared against an official product.
- **C** — SAR-derived with weak or incomplete validation.
- **D** — modelled, coarse, map-only or unavailable reference.

The Dec 1–8 2015 peak has no official vector flood layer among available data.

## Layers

| ID | Event/date | Source | Method | Tier | Validation and limits |
|---|---|---|---|---:|---|
| `unosat_2015-09-01` | 2015 Chennai / 2015-09-01 | UNOSAT 1039 vector archive | official vector baseline-water reference | A | official source layer; not an event flood label; limits: baseline water may include wet-soil class |
| `unosat_2015-10-14` | 2015 Chennai / 2015-10-14 | UNOSAT 1039 vector archive | official vector baseline-water reference | A | official source layer; not an event flood label; limits: baseline water may include wet-soil class |
| `unosat_2015-11-12` | 2015 Chennai / 2015-11-12 | UNOSAT 1039 vector archive | official vector flood reference | A | source product; not field-validated; limits: does not cover 1-8 Dec peak |
| `unosat_2015-11-24` | 2015 Chennai / 2015-11-24 | UNOSAT 1039 S1_20151124 vector layer | official vector flood reference | A | compared to SAR-derived pilot; possible same-scene source; limits: not ground truth; possible shared Sentinel acquisition |
| `derived_2015-11-24_change_otsu` | 2015 Chennai / 2015-11-24 | data/raw/satellite/hpy3_rtc/2015/S1A_IW_20151124T003120_DVP_RTC30_G_gpuned_37FC.zip | VV event-minus-reference dB; Otsu; Lee 5x5; permanent-water mask | C | difference-Otsu IoU 0.103, precision 0.103, recall 0.987, F1 0.187; potential same-scene comparison; limits: UNOSAT may derive from same scene; not field-validated |
| `derived_2015-11-24_event_otsu` | 2015 Chennai / 2015-11-24 | data/raw/satellite/hpy3_rtc/2015/S1A_IW_20151124T003120_DVP_RTC30_G_gpuned_37FC.zip | event VV dB Otsu; Lee 5x5; permanent-water mask | C | metric details in JSON registry; limits: UNOSAT may derive from same scene; not field-validated |
| `derived_2015-12-06_change_otsu` | 2015 Chennai December peak / 2015-12-06 | data/raw/satellite/hpy3_rtc/2015/S1A_IW_20151019T003131_DVP_RTC30_G_gpuned_5542.zip; data/raw/satellite/hpy3_rtc/2015/S1A_IW_20151124T003120_DVP_RTC30_G_gpuned_37FC.zip; data/raw/satellite/hpy3_rtc/2015/S1A_IW_20151206T003120_DVP_RTC30_G_gpuned_D367.zip | VV dB difference from linear mean of 19 Oct and 24 Nov references; Otsu | C | candidate area 482.38 km²; {'status': 'computed coarse spatial cross-check; dates differ (GFD ends 2015-12-04; SAR candidate is 2015-12-06)', 'member': 'DFO_4309_From_20151110_to_20151204.tif', 'band': 1, 'band_description': 'flooded', 'crs': 'EPSG:4326', 'native_resolution_degrees': [0.002245788210298804, 0.002245788210298804], 'cma_pixels_compared': 1190209, 'gfd_flood_pixels_in_cma': 32929, 'sar_candidate_pixels_in_cma': 532531, 'coarse_raster_iou': 0.03956700947534462}; limits: no official December 2015 vector; GFD ends 4 Dec; OpenCity dates unspecified |
| `derived_2021-11-16_change_otsu` | 2021 Chennai / 2021-11-16 | data/raw/satellite/hpy3_rtc/2021/S1A_IW_20211023T003148_DVP_RTC30_G_gpuned_5E62.zip; data/raw/satellite/hpy3_rtc/2021/S1A_IW_20211023T003213_DVP_RTC30_G_gpuned_9DBF.zip; data/raw/satellite/hpy3_rtc/2021/S1A_IW_20211104T003147_DVP_RTC30_G_gpuned_97D3.zip; data/raw/satellite/hpy3_rtc/2021/S1A_IW_20211104T003212_DVP_RTC30_G_gpuned_F95E.zip; data/raw/satellite/hpy3_rtc/2021/S1A_IW_20211116T003147_DVP_RTC30_G_gpuned_555C.zip; data/raw/satellite/hpy3_rtc/2021/S1A_IW_20211116T003212_DVP_RTC30_G_gpuned_576C.zip | VV dB difference from linear mean of 23 Oct and 4 Nov references; Otsu | C | candidate area 398.60 km²; not computed: local NRSC map is PDF-only and manual digitising is reserved as a QGIS validation task; limits: NRSC validation map is PDF-only and not digitised; OpenCity point dates do not match |
| `nrsc_2021-11-13-map` | 2021 Chennai / 2021-11-13 | data/raw/historical_floods/2021/ChennaiCity-ChennaiCorporationTaluk-4.pdf | map graphic; manual georeference/digitisation pending | D | not compared numerically; limits: PDF map only; map extent partial |
| `gfd_4309` | 2015 Chennai / 2015-11-10 to 2015-12-04 | DFO event 4309 MODIS coarse product | coarse cross-check | D | metric details in JSON registry; limits: nominal 250 m; event ends 4 Dec |
| `ndem_2023-12-07-map` | 2023 Michaung / 2023-12-07 06:00 IST | data/raw/historical_floods/2023/tncyclone50dsc07122023_0600hrs_map.pdf | map graphic only | D | not compared numerically; limits: not vector; manual digitising pending |
| `nrsc_2023-michaung-pdf` | 2023 Michaung / 2023 event | not downloaded; PDF map requested previously | none | D | unavailable; limits: no post-peak RTC scene; no label created |
| `derived_2023-michaung` | 2023 Michaung / 2023-12-03 to 2023-12-04 peak | none | no post-peak scene available | D | no SAR flood label created; limits: Nov 18 and Nov 30 RTC products precede the peak |
| `opencity_flows_10y` | Chennai flooding scenarios / modelled scenario | data/raw/historical_floods/2015/opencity_flood_points/1bfef958-d4cc-4e50-a926-445e65bac7a8.kml | modelled return period: 10 years | D | modelled hazard scenario; not an observed historical flood label; limits: modelled return-period/hazard layer; not observed event truth |
| `opencity_flows_200y` | Chennai flooding scenarios / modelled scenario | data/raw/historical_floods/2015/opencity_flood_points/61f1f06f-1fa1-4ef0-94c7-224d892efbef.kml | modelled return period: 200 years | D | modelled hazard scenario; not an observed historical flood label; limits: modelled return-period/hazard layer; not observed event truth |
| `opencity_hazard_zones` | Chennai flooding scenarios / modelled scenario | data/raw/historical_floods/2015/opencity_flood_points/7f29da20-6621-4b49-b0cf-28b9d1de232b.kml | modelled hazard-zone classification | D | modelled hazard scenario; not an observed historical flood label; limits: modelled return-period/hazard layer; not observed event truth |
| `opencity_inundation_depth_points` | 2015 / date not specified in KML title / not specified in source title | data/raw/historical_floods/2015/opencity_flood_points/814ca028-4c84-4bd0-aa67-6dbaeb9b6ba5.kml | observed inundation points with depth attribute | A | point overlap computed only where point geometry; event timestamp is unspecified or does not match the SAR candidate; sparse points do not describe full inundation extent; limits: not a complete event flood polygon; not time-matched physical validation |
| `opencity_flood_points_2015` | 2015 Chennai flood / 2015 | data/raw/historical_floods/2015/opencity_flood_points/93d2905a-a580-482d-96b0-4d9ccf5273ef.kml | observed flooding points | A | point overlap computed only where point geometry; event timestamp is unspecified or does not match the SAR candidate; sparse points do not describe full inundation extent; limits: not a complete event flood polygon; not time-matched physical validation |
| `opencity_flows_100y` | Chennai flooding scenarios / modelled scenario | data/raw/historical_floods/2015/opencity_flood_points/994a99a1-6104-40c7-ac10-2b7a7ab74437.kml | modelled return period: 100 years | D | modelled hazard scenario; not an observed historical flood label; limits: modelled return-period/hazard layer; not observed event truth |
| `opencity_flows_50y` | Chennai flooding scenarios / modelled scenario | data/raw/historical_floods/2015/opencity_flood_points/a6b20b7c-d771-4572-a2c7-9d8c125e6e5d.kml | modelled return period: 50 years | D | modelled hazard scenario; not an observed historical flood label; limits: modelled return-period/hazard layer; not observed event truth |
| `opencity_flows_25y` | Chennai flooding scenarios / modelled scenario | data/raw/historical_floods/2015/opencity_flood_points/a6b4f2b1-f2b4-4dbc-93da-37be6dc7a345.kml | modelled return period: 25 years | D | modelled hazard scenario; not an observed historical flood label; limits: modelled return-period/hazard layer; not observed event truth |
| `opencity_flows_5y` | Chennai flooding scenarios / modelled scenario | data/raw/historical_floods/2015/opencity_flood_points/ef3286de-1c9b-41a2-a5f2-a075863e26f6.kml | modelled return period: 5 years | D | modelled hazard scenario; not an observed historical flood label; limits: modelled return-period/hazard layer; not observed event truth |

## Stage 8 output assets

Selected outputs: `{'2015-11-24_change': 'data/features/labels/label_2015-11-24_change_otsu_DERIVED_run_20261025_002401.tif', '2015-11-24_event': 'data/features/labels/label_2015-11-24_event_otsu_DERIVED_run_20261025_002401.tif', '2015-12-06_change': 'data/features/labels/label_2015-12-06_change_otsu_DERIVED_run_20261025_002401.tif', '2021-11-16_change': 'data/features/labels/label_2021-11-16_change_otsu_DERIVED_run_20261025_002401.tif'}`, dense-urban flag `data/features/labels/dense_urban_unreliable_flag_run_20261025_002401.tif`, vector GeoPackage `data/features/labels/derived_flood_polygons_run_20261025_002401.gpkg`, processing metadata `data/processed/sar_work/run_20261025_002401/phase8_processing_metadata.json`.

Master-grid rasters are 30 m EPSG:32644 UInt8 (255 means excluded/NoData); polygons are simplified by 30 m and clipped to the CMA. The separate PostGIS `labels.derived_flood_polygons` table contains 45,096 Stage 8 rows with DERIVED status and provenance.

No 2023 SAR flood label was created because all available RTC scenes precede the Michaung peak. The 2021 NRSC and 2023 NDEM PDFs, and any future December 2015 reference maps, need manual QGIS georeferencing/digitising; those steps are validation work only.

## Accepted label row and serialization (G0 C2 repair proposal)

This is a Lane A proposal for consumers of the existing `labels.v_usable_flood_labels` view. It does not change the view or freeze the shared C2 contract.

| JSON Feature property / view column | Type and rule |
|---|---|
| `label_key` | Required string; official rows are keyed `official:<feature_id>`, derived rows retain their stable `label_key`. |
| `event_date` | Required SQL `date`, JSON `YYYY-MM-DD`. It is the source map/reference date, not an exact onset time. For `reference_role=baseline_water`, it is the baseline observation date and must not be counted as a flood event. Do not synthesize a midnight timestamp. |
| `method` | Required string; source layer/method identifier as returned by the view. |
| `reference_role` | Required enum `event_flood` or `baseline_water`; baseline water is a reference mask, not a positive flood label. |
| `tier` | Required enum `A`, `B`, `C`; the accepted view excludes tier D and any non-`ACCEPTED` derived row. |
| `is_derived`, `is_valid`, `in_cma` | Required booleans. Each accepted feature has `is_valid=true` and `in_cma=true`; neither means field validation. |
| `geom` | Required non-null valid polygonal geometry in the database at SRID 32644. JSON/API serialization is a GeoJSON Feature with RFC 7946 WGS84 longitude/latitude coordinates (transform at export); preserve original geometry, which may extend outside the CMA. Clip/intersect for CMA-only analysis explicitly. |
| `source_id`, `source_sha256`, `loader`, `load_time` | Required provenance keys. SHA-256 is 64 lowercase hex when present. `load_time` is a timezone-aware processing/load instant serialized as ISO-8601 UTC with `Z`. The current SQL columns permit null metadata; preserve null explicitly and report provenance as incomplete rather than inventing values or omitting the keys. |

**Null rules:** a null, empty, invalid, or non-polygonal geometry cannot be serialized as an accepted row; exclude it from the accepted feature collection and retain its rejection reason in QA evidence. Do not emit `geometry: null` for a row claimed to be accepted. Nullable provenance values remain JSON `null` and make provenance incomplete. `source_properties` is not exposed by the current accepted view and must not be implied to be present. No source acquisition-time field exists in this view; `event_date` must remain date-only. A consumer needing a timestamp must use a separate, documented acquisition field from source evidence, or leave it unknown.

The current migration evidence is `database/migrations/014_stage8_label_hygiene.sql`: it selects repaired geometry when available, restricts derived labels to accepted tiers A/B/C, valid and in-CMA rows, and excludes Tier D/rejected candidates. It also preserves `source_id`, `source_sha256`, `loader`, and `load_time`. `twinguard.flood_references` stores `event_date` as SQL `date`; `load_time` is `timestamptz`.
