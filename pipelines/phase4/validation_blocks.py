#!/usr/bin/env python
"""Create non-overlapping 3 km spatial blocks and document leakage-safe splits."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[2]
MASK = ROOT / "data/processed/grid/cma_mask.tif"
OUT = ROOT / "data/processed/alignment/spatial_blocks.tif"
DOC = ROOT / "docs/SPLIT_STRATEGY.md"
BLOCK_CELLS = 100


def make_blocks(mask: np.ndarray) -> np.ndarray:
    rows, cols = np.indices(mask.shape)
    n_block_cols = int(np.ceil(mask.shape[1] / BLOCK_CELLS))
    ids = (rows // BLOCK_CELLS) * n_block_cols + (cols // BLOCK_CELLS) + 1
    return np.where(mask == 1, ids, 0).astype("uint32")


def main() -> int:
    existing = [str(p) for p in (OUT, DOC) if p.exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite existing target(s): " + ", ".join(existing))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(MASK) as src:
        mask = src.read(1)
        profile = src.profile.copy()
        blocks = make_blocks(mask)
        valid_ids, counts = np.unique(blocks[mask == 1], return_counts=True)
        profile.update(driver="GTiff", dtype="uint32", count=1, nodata=0,
                       compress="DEFLATE", tiled=True, blockxsize=256, blockysize=256)
        with rasterio.open(OUT, "w", **profile) as dst:
            dst.write(blocks, 1)
            dst.set_band_description(1, "spatial_block_id")
            dst.update_tags(STATUS="DERIVED", block_size_m=3000,
                            block_size_cells=BLOCK_CELLS,
                            rule="fixed 100x100 master-grid cell blocks; 0 outside CMA")
    text = f"""# Spatial validation split strategy

This is a plan for later model evaluation, not a model run. `data/processed/alignment/spatial_blocks.tif` assigns each CMA cell a fixed block ID on the existing 30 m EPSG:32644 grid. A block is exactly {BLOCK_CELLS * 30:,} m × {BLOCK_CELLS * 30:,} m ({BLOCK_CELLS} × {BLOCK_CELLS} cells); cells outside the CMA mask are 0. Block IDs follow the master-grid origin, not the CMA boundary. The current raster has {len(valid_ids)} block IDs intersecting the CMA, with {int(counts.min())}–{int(counts.max())} CMA cells per block (edge blocks are partial).

## Evaluation rules

- Use leave-one-event-out evaluation across 2015, 2021 and 2023: hold out one event in full, train on the other available event(s), and repeat. Keep label tiers separate and do not treat modelled/coarse labels as equivalent to official vectors.
- Within an event, use spatial-block cross-validation: assign whole block IDs to folds so adjacent cells do not split randomly across train and test. Keep any temporal grouping intact as well.
- Fit scaling, normalization, imputation values and feature selection using training rows only; apply the fitted values unchanged to validation/test rows.
- Exclude any feature derived from the label raster, post-event imagery, future rainfall, or future reservoir observations from a forecast made before that time. Keep provenance and observation timestamps with every predictor.

## Leakage checklist

1. Temporal: predictor timestamps precede the target time; daily and hourly calendars use the source's recorded timezone; no later observations leak into earlier predictions.
2. Spatial: every cell in one spatial block stays in one fold; overlapping neighbourhood summaries do not cross the split unnoticed.
3. Label-derived: no flood extent, baseline subtraction, or digitised map attribute is reused as a predictor for the same label.
4. Preprocessing: normalization and any learned transformation are fitted only on training data.

Only three historical events are available, labels have uneven dates and confidence, the 2015 December peak lacks official vector truth, and the 2021/2023 references require PDF digitising. Scores will therefore have high sampling uncertainty and cannot establish general performance across all floods or years.
"""
    DOC.write_text(text, encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}; BLOCK_SIZE_M={BLOCK_CELLS * 30}; "
          f"CMA_BLOCKS={len(valid_ids)}; BLOCK_CELLS={int(counts.min())}..{int(counts.max())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
