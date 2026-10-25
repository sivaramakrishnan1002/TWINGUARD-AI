# SAR candidate labels — Batch 2 lineage

| Output | Inputs / operation | Status |
|---|---|---|
| 24-Nov candidate CV metrics and maps | Master-grid VV/VH and dB changes (24 Nov minus 19 Oct), D8 HAND, slope, land cover, Nov 24 UNOSAT label, 3-km blocks; 5 outer / 3 inner spatial folds and one-block adjacency buffer | diagnostic map reproduction; possible same-scene circularity |
| v2 6-Dec and 16-Nov-2021 probability/class rasters | Frozen full-data model and threshold 0.40; 19 Oct baseline for Dec; 4 Nov baseline for 2021; `eligible_for_model` applied, other required predictors finite | DERIVED Tier D, no independent event validation |
| OpenCity point checks | 945 source points; 877 intersect valid raster cells; top percentile and landcover/built-up matched chance with 2,000 block-bootstrap replicates | dates unclear, approximate locations; spatial-only |
| Reproducibility | Source and v2 raster SHA-256 values in `SAR_CALIBRATED_LABELS_BATCH2_MODEL_REGISTRY.json` | raw inputs read-only |

No original files were modified. The 2021 NRSC map has unresolved GeoPDF CRS metadata; no local GFD raster was available.
