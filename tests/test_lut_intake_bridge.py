"""Bridge tests use synthetic loads; they do not verify LUT source values."""
import pandas as pd
import pytest
from lut_to_pypsa.lut_intake_bridge import convert_hourly_loads


def test_bridge_preserves_region_hour_and_energy():
    hourly = pd.DataFrame({
        "timestamp": ["2020-01-01 00:00", "2020-01-01 00:00",
                      "2020-01-01 01:00", "2020-01-01 01:00"],
        "region": ["Africa", "Europe", "Africa", "Europe"],
        "p_set_mw": [2.0, 3.0, 4.0, 5.0],
    })
    result = convert_hourly_loads(hourly)
    assert result.bus.unique().tolist() == ["Africa", "Europe"]
    assert result.groupby("bus").demand_mw.sum().to_dict() == {"Africa": 6.0, "Europe": 8.0}
    assert len(result) == 4


def test_bridge_rejects_missing_region_hour():
    hourly = pd.DataFrame({
        "timestamp": ["2020-01-01 00:00", "2020-01-01 00:00",
                      "2020-01-01 01:00"],
        "region": ["Africa", "Europe", "Africa"],
        "p_set_mw": [2, 3, 4],
    })
    with pytest.raises(ValueError, match="Incomplete regional coverage"):
        convert_hourly_loads(hourly)


def test_bridge_detects_whole_missing_hour_in_leap_year():
    # Every region may be present at every supplied timestamp, while an entire
    # calendar hour is missing. The explicit year contract must catch this.
    hourly = pd.DataFrame({
        "timestamp": ["2020-01-01 00:00", "2020-01-01 01:00"],
        "region": ["Africa", "Africa"], "p_set_mw": [2.0, 2.0],
    })
    with pytest.raises(ValueError, match="expected 8784"):
        convert_hourly_loads(hourly, expected_year=2020)


def test_bridge_accepts_complete_leap_year_calendar():
    times = pd.date_range("2020-01-01", "2021-01-01", freq="h", inclusive="left")
    hourly = pd.DataFrame({"timestamp": times, "region": "Africa", "p_set_mw": 2.0})
    result = convert_hourly_loads(hourly, expected_year=2020)
    assert len(result) == 8784
    assert result.demand_mw.sum() == pytest.approx(17568.0)
