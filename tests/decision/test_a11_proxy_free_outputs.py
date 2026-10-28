from __future__ import annotations

import pandas as pd
import pytest
import rasterio

from pipelines.decision.a11_proxy_free_outputs import (
    _write_hazard_rasters, hazard_cells, validate_products,
)


def _tables():
    hazard = pd.DataFrame([{
        "event_key": "2015-12-02", "scenario_key": "scenario_a", "horizon_hours": 6,
        "valid_at_utc": "2015-11-30T06:00:00Z", "grid_cell_id": 255,
        "threshold_m": 0.3, "passability_probability": 0.75, "depth_mean_m": 0.2,
        "depth_member_p05_m": 0.1, "depth_member_p95_m": 0.4,
        "depth_valid_member_count": 20, "member_count": 20, "qc": "DERIVED_SIMULATED",
        "flood_screen_probability": 0.25,
    }])
    exposure = pd.DataFrame([{"population_exposure_status": "PARTIAL",
                              "population_nodata_30m_cells": 12,
                              "population_coverage_fraction": 0.9,
                              "known_population_exposed_mean_people": 0.0}])
    access = pd.DataFrame([{"facility_count": 10, "reachable_count": 6,
                            "unreachable_count": 1, "unassessed_count": 3,
                            "access_loss_fraction": 0.1}])
    allocations = pd.DataFrame([{"qc_flags": ["CAPACITY_ASSUMPTION"]}])
    return hazard, exposure, access, allocations


def test_default_hazard_threshold_and_exceedance_probability():
    source = pd.DataFrame([
        {"event_key": "e", "scenario_key": "s", "valid_at_utc": "t", "horizon_hours": 6,
         "grid_cell_id": 1, "threshold_m": threshold, "passability_probability": value,
         "depth_mean_m": 0.2, "depth_member_p05_m": 0.1, "depth_member_p95_m": 0.3,
         "depth_valid_member_count": 20, "member_count": 20, "qc": "DERIVED"}
        for threshold, value in ((0.15, 0.4), (0.3, 0.7), (0.5, 0.9))
    ])
    out = hazard_cells(source)
    assert len(out) == 1
    assert out.iloc[0].threshold_m == 0.3
    assert out.iloc[0].flood_screen_probability == pytest.approx(0.3)


def test_hazard_no_data_and_separate_indicator_validation():
    tables = _tables()
    validate_products(*tables)
    # A known-data result of zero can coexist with source NoData, which remains explicit.
    assert tables[1].iloc[0].known_population_exposed_mean_people == 0.0
    assert tables[1].iloc[0].population_nodata_30m_cells == 12
    assert tables[1].iloc[0].population_exposure_status == "PARTIAL"


@pytest.mark.parametrize("field", ["vulnerability_class", "composite_score", "priority_rank"])
def test_forbidden_composite_or_vulnerability_schema_rejected(field):
    tables = list(_tables())
    tables[0][field] = 1
    with pytest.raises(ValueError, match="forbidden composite/vulnerability"):
        validate_products(*tables)


def test_unknown_is_not_zero_and_probability_ranges_are_checked():
    tables = list(_tables())
    tables[1]["population_exposure_status"] = "UNAVAILABLE"
    validate_products(*tables)
    tables[0].loc[0, "flood_screen_probability"] = 1.2
    with pytest.raises(ValueError, match=r"outside \[0,1\]"):
        validate_products(*tables)


def test_population_nodata_cannot_be_marked_available():
    tables = list(_tables())
    tables[1].loc[0, "population_exposure_status"] = "AVAILABLE"
    with pytest.raises(ValueError, match="cannot be marked fully available"):
        validate_products(*tables)


def test_duplicate_hazard_cell_key_rejected():
    tables = list(_tables())
    tables[0] = pd.concat([tables[0], tables[0]], ignore_index=True)
    with pytest.raises(ValueError, match="key is not unique"):
        validate_products(*tables)


def test_hazard_raster_preserves_grid_bands_and_nodata(tmp_path):
    hazard = _tables()[0]
    hazard["threshold_m"] = 0.3
    names = _write_hazard_rasters(hazard, tmp_path, "a" * 64)
    assert len(names) == 1
    with rasterio.open(tmp_path / names[0]) as ds:
        assert (ds.width, ds.height, ds.count) == (69, 88, 5)
        assert ds.crs.to_string() == "EPSG:32644"
        assert ds.transform.a == 600 and ds.transform.e == -600
        assert ds.nodata == -9999
        assert ds.descriptions == (
            "depth_mean_m", "depth_member_p05_m", "depth_member_p95_m",
            "flood_screen_probability", "depth_valid_member_count",
        )
        # Sparse linear A06 cell id 255 maps to row 3, column 48.
        assert ds.read(1)[3, 48] == pytest.approx(0.2)
        assert ds.read(1)[0, 0] == -9999
