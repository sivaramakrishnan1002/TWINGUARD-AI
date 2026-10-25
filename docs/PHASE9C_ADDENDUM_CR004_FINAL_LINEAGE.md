# Phase 9C addendum CR-004 lineage — final

Read-only sources: Phase 9B static feature table, unchanged Nov 2015 label parquet, buffered 3 km spatial-block raster, CMA mask, aligned 19 Oct 2015/24 Nov 2015 RTC validity and layover/shadow masks, WorldPop raster metadata, and two OpenCity KML files containing 945 source points.

Feature table SHA-256 and target SHA-256 are recorded in docs/PHASE9C_ADDENDUM_CR004_V6_MODEL_REGISTRY.json. The WorldPop raw raster was opened for metadata only. No raw data was changed.

Lane A code: pipelines/phase9c/addendum_cr004.py and pipelines/phase9c/build_phase10_cr004.py. Tests: tests/phase9c/test_addendum_cr004.py. Detailed metrics and dropped-cell audit: docs/PHASE9C_ADDENDUM_CR004_V6.json. Model registry: docs/PHASE9C_ADDENDUM_CR004_V6_MODEL_REGISTRY.json.

Model outputs: data/features/predictions/phase9c_addendum_cr004_v6/ (radar observability, apparent calibrated mean probability, apparent p05/p95 bands, physical-only layer and confidence flag). Final Phase 10 output: data/features/predictions/phase10_cr004_v9/radar_visible_plus_physical_composite.tif; full-CMA physical complement: data/features/predictions/phase9c_addendum_cr004_v7/physical_susceptibility_all_unobservable.tif.

Phase 9 labels were not changed. Prior experimental CR-004 drafts remain preserved in their distinct version folders and must not be treated as the final run.
