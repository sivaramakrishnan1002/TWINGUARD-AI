# Flood label strategy

## What flood references are available

| Event | Available reference | Coverage and timing | Limits |
|---|---|---|---|
| 2015 | UNOSAT vector layers for 12 Nov and 24 Nov; exploratory 30 m raster estimates from those vectors | 12 Nov extent: 84.78 km²; 24 Nov: 98.16 km²; union: 126.39 km². These dates do not cover the 1–8 Dec 2015 peak. | The November geometries are not December flood truth. The Sep 1 and Oct 14 layers are baseline-water references, not flood labels. |
| 2021 | NRSC map PDF(s) | PDFs require manual georeferencing and digitising before they can act as spatial labels. | Not yet a validated machine-readable extent; map scale, projection, legend and delineation uncertainty need recording. |
| 2023 | NRSC map PDF(s) | PDFs require manual georeferencing and digitising before they can act as spatial labels. | Not yet a validated machine-readable extent; map scale, projection, legend and delineation uncertainty need recording. |
| Regional 2015 comparison | Global Flood Database event 4309 | About 65.43 km² in the CMA by the existing nominal-area calculation. The event spans 10 Nov–4 Dec and its centroid is outside Chennai. | Coarse MODIS-scale regional comparison, not authoritative local flood truth. |

## Baseline-water idea to verify

Use the 1 Sep and 14 Oct 2015 UNOSAT layers as a possible reference for persistent/baseline water and inspect their agreement before using them to remove water from event extents. This is an **idea to verify**, not a validated correction. The repository's exploratory calculation subtracts the union of those two baseline masks from the November event union: 126.39 km² becomes 80.59 km². This large change shows that results are sensitive to the baseline rule. Saturated soil, seasonal water, differences in acquisition/date and map classification may be removed along with permanent water; do not describe 80.59 km² as ground-truth flood area.

## Options for the missing December 2015 peak labels

1. **Obtain and digitise December reference maps if they become available.** Georeference each map, document control points and residual error, record the legend interpretation, digitise only the event extent supported by the source, and keep an uncertainty margin.
2. **Use the existing Sentinel-1 scenes to derive an inundation candidate.** Thirteen raw ZIPs are available, including one scene dated 6 Dec 2015 within the 1–8 Dec period. These scenes have not been processed. Any derived extent is an algorithmic candidate affected by urban backscatter, wet soil, paddy, tide, layover/shadow and acquisition timing; it is not independent truth for model validation.
3. **Narrow validation scope to dates with defensible labels.** Evaluate only the 2015 November label dates and any later event once the 2021/2023 PDF maps have been digitised and checked. Explicitly state that this does not validate the December 2015 peak.

## Recommendation

For now, narrow validation to the dates and areas covered by the existing reference layers, and report the December 2015 event as lacking a direct label. Keep the September/October baseline subtraction as a sensitivity scenario only. In parallel, manually digitise the already-collected 2021 and 2023 PDFs with recorded georeferencing/digitising uncertainty. Process the 6 Dec 2015 Sentinel scene only as a supplementary candidate map and compare it with independent references when available; do not use Sentinel-derived labels as independent ground truth. This avoids implying that November-only vectors, coarse regional GFD pixels, or a radar threshold establish the unobserved Dec 1–8 extent.

## Source numbers and provenance

Numbers above are copied from the existing Phase 3 log and label inspection outputs: `docs/PHASE3_LOG.md`, `data/features/labels/` and the Global Flood Database event 4309 calculation documented there. No flood data were processed or changed for this strategy note.
