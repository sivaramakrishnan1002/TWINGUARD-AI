# Flood-label strategy V2

## Decision

**Training target:** the official UNOSAT November 2015 event layers (12 Nov and 24 Nov), with the September and October reference-water layers and WorldCover water handled as permanent water. This is **Tier A: official mapped product**, not field ground truth. Use only the source-derived event labels; do not substitute the experimental SAR rules.

**SAR candidates:** every SAR-derived map remains **Tier D** in the present registry. Exclude these candidates from training and from `labels.v_usable_flood_labels`. Phase 9B/9C are one-event apparent analyses, not evidence that a derived layer is an accepted label. The diagnostic in `PHASE9B_SAR_DIAGNOSTIC.md` found strong one-variable separation for 24 Nov, but same-scene dependence and limited finite-HAND coverage mean it cannot establish independent flood detection.

## What can validate the model, in priority order

| Order | Source | What it can check | What it cannot establish |
|---|---|---|---|
| 1 | OpenCity observed flood points (945 points; dates unclear and locations approximate) | Whether mapped risk ranks locations where flooding was reported; compare hits by percentile and land-cover mix. | Event/date-specific accuracy, flooded extent, depth, absence of flooding at unmarked locations, or precise boundary accuracy. Treat as an independent spatial cross-check only. |
| 2 | Global Flood Database event 4309 (coarse MODIS product; event 10 Nov–4 Dec 2015) | Broad regional timing/extent consistency and a coarse cross-check for the November–early-December period. | Chennai street/block detail, a precise 1–8 Dec peak outline, or a comparable fine-grid pixel truth. Do not resample it and call it high-resolution ground truth. |
| 3 | Future digitized official map sheets, after georeferencing and QA | Spatial agreement with mapped flood extent for the event/date represented by each sheet. Assign Tier B only at RMS error <=30 m (one master cell); Tier C above 30 m or where map interpretation is materially uncertain. | Flood depth, unshown dry areas, or a different event date/peak. These remain map-derived and subject to scale, standing-water and digitising uncertainty. |

The 2021 NRSC map is dated 13 Nov 2021 and the available 2023 NRSC/NDEM-branded Michaung map is dated 7 Dec 2023. They are map-only sources and require manual digitising before event-specific validation. The 2015 December peak (1–8 Dec) still has no official vector layer in the supplied project files; the December map folder is absent. Keep out-of-event validation marked **pending digitised labels**.

## Label registry rules

- Tier A: supplied official UNOSAT 2015 November vector product, with source dates recorded; still not field-validated.
- Tier B: future official map digitisation whose independently checked georeferencing RMS is at most 30 m.
- Tier C: future official map digitisation with RMS above 30 m or documented interpretation uncertainty.
- Tier D: SAR-derived candidates, coarse cross-checks, modelled layers and map-only sources before accepted digitisation. They are not training targets.
- OpenCity points remain point observations with uncertain dates, not a complete negative/positive raster.

Use documented masks, record sources and uncertainty, and report the date and event represented by every evaluation. No layer is called ground truth.
