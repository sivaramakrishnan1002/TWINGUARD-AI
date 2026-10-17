"""Phase 4 acceptance checks; runnable by pytest or unittest discovery."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

from pipelines.phase4.spatial_alignment import _grid_match
from pipelines.phase4.time_alignment import imerg_bucket_date, local_window_utc

ROOT = Path(__file__).resolve().parents[2]


class Phase4AlignmentTests(unittest.TestCase):
    def test_local_event_window_converts_ist_midnight_to_utc(self):
        start, stop = local_window_utc("2015-11-01", "2015-12-15")
        self.assertEqual(str(start), "2015-10-31 18:30:00+00:00")
        self.assertEqual(str(stop), "2015-12-15 18:30:00+00:00")
        self.assertEqual((stop - start).total_seconds() / 3600, 45 * 24)

    def test_imerg_date_uses_utc_bucket_not_local_date(self):
        self.assertEqual(imerg_bucket_date(__import__("pandas").Timestamp("2015-12-01T00:00:00Z")),
                         __import__("datetime").date(2015, 12, 1))

    def test_master_grid_registration(self):
        grid = json.loads((ROOT / "data/processed/grid/grid_definition.json").read_text())
        transform = Affine(30, 0, 390000, 0, -30, 1471620)
        aligned, offsets = _grid_match(transform, "EPSG:32644", 1370, 1760, grid)
        self.assertTrue(aligned)
        self.assertTrue(offsets["origin_offsets_whole_cells"])

    def test_nodata_is_distinct_from_zero(self):
        # Use the project workspace because the managed Windows sandbox may
        # deny writes to the system temporary directory.
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            path = Path(temp) / "tiny.tif"
            profile = {"driver": "GTiff", "width": 2, "height": 2, "count": 1,
                       "dtype": "int16", "crs": "EPSG:32644", "transform": Affine(30, 0, 0, 0, -30, 0),
                       "nodata": -9999}
            with rasterio.open(path, "w", **profile) as dst:
                dst.write(np.array([[0, -9999], [2, 3]], dtype="int16"), 1)
            with rasterio.open(path) as src:
                values = src.read(1)
                mask = src.read_masks(1) == 0
                self.assertEqual(values[0, 0], 0)
                self.assertFalse(mask[0, 0])
                self.assertTrue(mask[0, 1])

    def test_population_sum_within_documented_tolerance(self):
        registry = json.loads((ROOT / "data/processed/alignment/layer_registry_complete.json").read_text())
        check = registry["checks"]["population_sum_check"]
        self.assertTrue(check["within_tolerance"])
        self.assertLessEqual(check["relative_difference"], check["tolerance"])

    @unittest.skipUnless((ROOT / "data/features/static/cell_table.parquet").exists(),
                         "static Parquet table not created; pyarrow unavailable")
    def test_cell_table_rows_match_cma_mask(self):
        import pandas as pd
        frame = pd.read_parquet(ROOT / "data/features/static/cell_table.parquet")
        with rasterio.open(ROOT / "data/processed/grid/cma_mask.tif") as src:
            expected = int((src.read(1) == 1).sum())
        self.assertEqual(len(frame), expected)


if __name__ == "__main__":
    unittest.main()
