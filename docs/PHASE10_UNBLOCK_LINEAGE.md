# Phase 10 unblock: Lane A lineage

| Output | Inputs | Method | Status / caveat |
|---|---|---|---|
| `docs/PHASE9B_SAR_DIAGNOSTIC.json` and `.md` | `data/processed/labels_inspection/2015-11-24_EXPLORATORY_NOT_FINAL.tif`; Sep/Oct reference masks; Phase 9B v2 static table; RTC 24 Nov and 19 Oct VV/VH and quality rasters | Reproject-free sampling by cell-centre coordinates; exclude baseline/WorldCover water and bad RTC; match finite-HAND cells by dominant landcover and HAND bin; fixed-seed controls; one-feature AUC and depth-1 spatial-block stump; cardinal label shift test | Run completed. AUC is a label/scene diagnostic, not label acceptance. Strict finite-HAND match excludes 39,697 otherwise eligible positives because HAND is missing. |
| `docs/LABEL_STRATEGY_V2.md` | Existing UNOSAT, OpenCity and GFD inventory; Phase 9B/9C caveats | Training/validation hierarchy and tier rules | November UNOSAT Tier A remains training label; SAR-derived labels Tier D and excluded. |
| `docs/PDF_MAP_INSPECTION.json` | 2021 NRSC and 2023 Michaung NRSC/NDEM-branded PDFs in raw | pypdf inspection of PDF metadata, GeoPDF viewports/GPTS, page text and images; embedded images exported at original pixel dimensions to processed folder | Raw PDFs read-only. December map folder absent. 2021 GeoPDF WKT/GPTS conflict requires independent controls. |
| `data/processed/pdf_maps/extracted_images/` | Same two PDFs | Native embedded image pixel extraction; lossless PNG for images extracted as PNG; original dimensions retained | 30 image objects extracted (6 from 2021, 24 from 2023). Not committed as source/data output. |
| `data/processed/pdf_maps/previews/` | Same two PDFs | Poppler 90 dpi page previews for visual legend/frame inspection | Three preview pages; derived working files, not committed. |
| `data/processed/labels_manual/digitised_labels.gpkg` | No digitised map rows | Empty EPSG:32644 GeoPackage layer with requested attribute fields | Zero features. No database load performed. |
| `pipelines/labels/manual_map_loader.py` | User-filled digitised-label GeoPackage | Validates schema, CRS, polygon type/validity and RMSE; assigns B at <=30m, C above; optional idempotent insert into `labels.derived_flood_polygons` with pending review status and source provenance | Loader tests pass. Not invoked with `--load` because template is empty. |

Reproducible commands (run from project root):

- `.venv/Scripts/python.exe pipelines/labels/sar_diagnostic_v2.py`
- `.venv/Scripts/python.exe pipelines/labels/inspect_flood_pdfs.py`
- `.venv/Scripts/python.exe pipelines/labels/manual_map_loader.py`

All three commands are local-only. They do not download or modify raw data. PDF extraction/report generation refuses to replace non-matching existing outputs; template creation refuses to replace an existing GPKG.
