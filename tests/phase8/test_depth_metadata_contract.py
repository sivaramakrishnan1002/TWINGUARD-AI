from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio

from pipelines.phase8.repair_depth_metadata import (
    DEFAULT_OUTPUT_DIR,
    EXPECTED_FILES,
    REQUIRED_TAGS,
    SOURCE_DIR,
    band_role,
    run,
)


def test_band_roles_encode_mean_and_assumption_bounds():
    assert band_role("depth_mean_2015-11-12_UNOSAT_A_DERIVED.tif") == "mean_m"
    assert band_role("depth_p05_2015-11-12_UNOSAT_A_DERIVED.tif") == "lower_assumption_bound_m"
    assert band_role("depth_p95_2015-11-12_UNOSAT_A_DERIVED.tif") == "upper_assumption_bound_m"


def test_repaired_tiffs_have_required_metadata_and_identical_cells(tmp_path: Path):
    output_dir = tmp_path / "metadata_copy"
    manifest_path = run(output_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["results"]) == len(EXPECTED_FILES) == 6
    for filename, record in zip(EXPECTED_FILES, manifest["results"], strict=True):
        with rasterio.open(SOURCE_DIR / filename) as src, rasterio.open(output_dir / filename) as out:
            assert out.count == 1
            assert out.dtypes == ("float32",)
            assert out.crs.to_epsg() == 32644
            assert out.transform == src.transform
            assert out.transform.a == 30 and out.transform.e == -30
            assert out.nodata == -9999.0
            assert out.tags()["AREA_OR_POINT"] == "Area"
            assert out.descriptions[0] == band_role(filename)
            assert set(REQUIRED_TAGS).issubset(out.tags())
            assert out.tags()["acquisition_time_utc"].startswith("UNKNOWN")
            assert out.tags()["uncertainty_rule"] == (
                "lower=max(0,mean_m-4);upper=mean_m+4;not_calibrated_statistical_percentiles;DEFAULT_TO_CONFIRM"
            )
            assert out.tags()["status"] == "DERIVED_ASSUMPTION_NOT_OBSERVED"
            assert np.array_equal(src.read(1), out.read(1))
            assert np.array_equal(src.read_masks(1), out.read_masks(1))
            assert record["acquisition_time_utc"] is None
            assert record["cell_values_unchanged"] and record["mask_unchanged"]
            assert len(record["source_sha256"]) == len(record["output_sha256"]) == 64


def test_default_output_refuses_to_overwrite_existing_data(tmp_path: Path):
    output_dir = tmp_path / "existing"
    output_dir.mkdir()
    (output_dir / "keep.txt").write_text("keep", encoding="utf-8")
    try:
        run(output_dir)
    except FileExistsError as exc:
        assert "Refusing to overwrite" in str(exc)
    else:
        raise AssertionError("Expected overwrite refusal")


def test_output_path_is_new_and_source_batch_is_not_the_output():
    assert DEFAULT_OUTPUT_DIR != SOURCE_DIR

