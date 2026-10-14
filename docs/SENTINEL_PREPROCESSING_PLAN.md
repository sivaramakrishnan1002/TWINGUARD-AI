# Sentinel-1 preprocessing plan (not run in Phase 3)

## Available scenes and timing caveat

There are 13 user-acquired ASF Sentinel-1 GRD-HD ZIPs (three 2015, six 2021, four 2023); CRC verification and scene metadata are recorded in `SENTINEL_VERIFICATION.md`. The acquired dates include 19 Oct, 24 Nov, and 6 Dec 2015; 23 Oct, 4 Nov, and 16 Nov 2021; and 18 and 30 Nov 2023 (paired slices on some dates). The 6 Dec 2015 scene falls within the documented Dec 1–8 flood window and covers the CMA, but remains raw, unprocessed imagery rather than a flood map or label. The 16 Nov 2021 pair is post-peak relative to the provisional 7 Nov event date. Check 2021/2023 timing against authoritative reports before labeling.

## Availability check

Checked the project venv and common installation locations on 2026-10-14. ESA SNAP `gpt.exe`, SNAP Python bindings (`snappy`/`snapista`), pyroSAR, GDAL Python bindings (`osgeo`), GDAL CLI (`gdalinfo`, `gdalwarp`, `gdal_translate`), and NetworkX were not found. Rasterio is installed and includes GDAL functionality for the Phase 3 non-Sentinel rasters. No software was installed and no Sentinel ZIP was extracted or processed.

## Proposed workflow for a separately approved scene-processing task

1. Keep original ZIPs immutable. Read the verified ZIP inventory, product manifests, acquisition time, orbit direction, relative orbit, swath, polarization, and footprint. Pair compatible scenes and identify gaps before processing.
2. In a supported, version-pinned SNAP workflow, apply precise orbit files when available; thermal-noise removal; border-noise masking as appropriate; radiometric calibration to sigma-nought (VV/VH); and terrain correction using the Copernicus DEM. Record whether radiometric terrain flattening is used and why. Do not apply a blanket speckle filter without a comparison/validation rationale.
3. Export geocoded, masked VV/VH backscatter in linear units and dB, with consistent polarization, orbit direction, terrain correction, and nodata handling. Reproject and resample to the common EPSG:32644 30 m master grid using a documented continuous resampler. Keep scene footprints and original acquisition metadata.
4. Co-register only compatible acquisitions and assess residual displacement before change detection. Compare matched-orbit pre-event and event/post-event scenes; apply permanent-water and layover/shadow masks. Urban double-bounce, wet soil, paddy fields, and acquisition timing can cause false water changes.
5. Validate against the available independent dates/labels. The 2015 UNOSAT vector layers are November only, and 2021/2023 reference maps are PDFs not digitised in this phase. Report that label limitation, confusion matrices where defensible, area comparisons, and uncertainty; do not claim validation against unavailable peak-date truth.
6. Keep intermediate and final products under `data/processed/sentinel1` and `data/features/sentinel1`, never in `data/raw`. Estimate storage first. Before creating any individual output larger than 2 GB, report the estimate and available disk space.

## Risks and decisions required

- The installed environment has no SNAP/pyroSAR; choose an approved processing environment and pin versions before implementation.
- Temporal coverage remains sparse. One 6 Dec 2015 scene is in the 1–8 Dec window, but it has not been processed or validated as an inundation observation. There is no acquired scene during the provisional 6–11 Nov 2021 window or 3–5 Dec 2023 window.
- GRD is not analysis-ready water extent. Speckle, terrain, tides/coastal water, urban structures, paddy fields, and precipitation timing complicate thresholding.
- Flood labels are weak for event validation: November-only 2015 vectors; PDF-only 2021/2023 maps. Do not train/validate on Sentinel-derived labels as if they were independent ground truth.
- GLO-30 is a DSM with vegetation/buildings and may include artifacts. Flat coastal hydrology and vertical datum choices matter.
- Keep raw archives unmodified and do not redistribute ASF scenes until the data terms are confirmed.
