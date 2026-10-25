# GeoPDF map inspection — Batch 2

## Findings

- 2023 Dec 7 Michaung map is a two-page NRSC rapid map based on RISAT-1A MRS SAR, pre-image 5 Nov 2023, post-image 7 Dec 2023. The first page contains a GeoPDF `/GEO` viewport with geographic `/GPTS` corners and WGS84 `/GCS`; automated placement in WGS84 is feasible. The red legend class is “Flood / Standing Water due to Rains.”
- Embedded images were extracted in native resolution beneath `data/processed/pdf_maps/batch2/`; a diagnostic map-frame render was thresholded and polygonised. The resulting raster/vector are explicitly **PRELIMINARY_NOT_ACCEPTED**. The map itself warns that it has no ground verification and may include rain accumulation, low-lying water or paddy standing water.
- Georeferencing residual against OSM is **not computed**: there is no graticule and no unambiguous OSM control point tied to an exact map-pixel coordinate. Therefore the polygon layer is not accepted as tier B/C and was not loaded into the label schema. Manual visual control-point QA is required first.
- 2021 NRSC PDF has a GeoPDF viewport, but its projected `/GCS` WKT says WGS 84 / UTM zone 45N while its `/GPTS` points locate Chennai near 80.25°E (zone 44 area). CRS ambiguity is unresolved; manual-needed.
- `tnflood50dsc12182023_1800hrs_vap1.pdf` is a 18 Dec 2023 Tuticorin district map, outside CMA; inspected and excluded from Chennai labels. No December 2015 maps were present under `data/raw/historical_floods/2015/december_maps`; skipped.

## QA and outputs

The map class was identified from the red legend swatch and extracted as a preliminary diagnostic. The rendered class was overlaid on the CMA boundary and OSM waterways for visual inspection; exact OSM control-point RMS could not be measured, so no map geometry was accepted for training. The native map-frame rendering is 2695 x 1775 pixels, approximately 75.5 m east-west by 77.3 m north-south near the map centre. Its red class produced 82,902 pixels and 14,443 connected polygons. The WGS84 GeoPDF viewport bbox, class pixel/polygon counts, and cross-check metrics are in `data/features/labels/map_batch2/nrsc_2023_dec07_diagnostic.json`. See `docs/figures/nrsc_2023_dec07_geopdf_overlay.png`.
