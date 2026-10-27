import numpy as np
import pytest

from pipelines.phase11.run import distribute_daily_total, event_forcing, make_persistence_profile, rainfall_error_quantiles


def test_daily_scaling_preserves_imerG_total():
    actual = distribute_daily_total(np.arange(1, 25), 30.0)
    assert actual.shape == (24,)
    assert actual.sum() == pytest.approx(30.0)
    assert np.all(actual >= 0)


def test_scaling_rejects_positive_rain_with_zero_hourly_shape():
    with pytest.raises(ValueError, match="zero ERA5"):
        distribute_daily_total(np.zeros(24), 1.0)


def test_persistence_repeats_previous_day_without_changing_values():
    day = np.arange(24, dtype=float)
    out = make_persistence_profile(day)
    assert out.shape == (72,)
    assert np.array_equal(out[:24], out[24:48])
    assert np.array_equal(out[:24], out[48:])


def test_event_forcing_has_exact_72_utc_hours_and_daily_totals():
    imerg = {"2020-01-01": 1.0, "2020-01-02": 2.0, "2020-01-03": 3.0}
    profile = np.ones(24)
    forcing, rows = event_forcing(__import__("datetime").date(2020, 1, 3), imerg,
                                  {d: profile for d in imerg})
    assert forcing.shape == (72,)
    assert [r["scenario_hourly_sum_mm"] for r in rows] == pytest.approx([1, 2, 3])


def test_error_quantiles_use_daily_matched_differences():
    imerg = {f"2020-01-{i:02d}": float(i) for i in range(1, 11)}
    era = {d: np.full(24, imerg[d] / 24 + 2) for d in imerg}
    q = rainfall_error_quantiles(imerg, era)
    assert q["q50"] == pytest.approx(48.0)
