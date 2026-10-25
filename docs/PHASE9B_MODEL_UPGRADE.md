# Phase 9B model upgrade

The authoritative corrected run is the **v2** report: [PHASE9B_MODEL_UPGRADE_V2.md](PHASE9B_MODEL_UPGRADE_V2.md). It uses a new feature table with HAND drainage seeded by mapped OSM waterways/water bodies, reservoirs, WorldCover water and the >=100-cell flow-accumulation network. The original `cell_table_phase9b_v1.parquet` and v1 prediction maps were preserved unchanged. The first-pass HAND feature used accumulation streams only; v2 corrected this to match the requested combined drainage definition.

The unchanged Phase 9 label remains an official SAR-derived November 2015 product, not field-validated. The v2 metrics, model registry and apparent maps are linked from the v2 report.
