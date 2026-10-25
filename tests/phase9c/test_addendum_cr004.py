import numpy as np
import pytest

from pipelines.phase9c.addendum_cr004 import (
    SETS, composite_bands, phase9c_eligibility, prlift,
)


def test_population_nodata_does_not_change_hazard_eligibility():
    eligible = np.array([True, True, False, True])
    population_nodata = np.array([False, True, False, True])
    assert np.array_equal(phase9c_eligibility(eligible, population_nodata), eligible)


def test_hazard_sets_exclude_exposure_proxies():
    banned = {"worldpop_2021", "distance_to_nearest_road_node_m", "building_density_per_km2"}
    assert all(not banned.intersection(features) for features in SETS.values())
    assert "built_up_fraction" not in SETS["ii_plus_landcover_no_built"]
    assert "built_up_fraction" in SETS["iii_plus_built_fraction"]


def test_pr_auc_lift_is_prevalence_normalized():
    y = np.array([0, 0, 1, 0, 1], dtype=np.uint8)
    p = np.array([.1, .2, .9, .3, .8])
    result = prlift(y, p, np.arange(len(y)))
    assert result["prevalence"] == pytest.approx(.4)
    assert result["lift"] == pytest.approx(result["pr_auc"] / .4)


def test_phase10_display_keeps_physical_and_radar_bands_separate():
    cma = np.array([[True, True, True], [False, True, True]])
    observed = np.array([[True, False, True], [False, False, False]])
    probability = np.array([[.8, .7, .2], [np.nan, np.nan, np.nan]])
    physical = np.array([[.3, .9, .4], [np.nan, .8, .5]])
    result = composite_bands(cma, observed, probability, physical)
    assert result.shape == (3, 2, 3)
    assert result[0, 0, 0] == 4
    assert result[0, 0, 1] == -9999
    assert result[1, 0, 0] == -9999
    assert result[1, 0, 1] == pytest.approx(.9)
    assert result[2, 0, 0] == 0
    assert result[2, 0, 1] == 1
    assert result[2, 1, 0] == -9999
