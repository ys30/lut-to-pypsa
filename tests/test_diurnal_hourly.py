"""Tests for synthetic daily shape with authentic annual-energy conservation."""
import numpy as np
import pandas as pd
import pytest
from lut_to_pypsa.hourly import hourly_diurnal, hourly_flat, check_energy_conservation


def test_diurnal_2020_preserves_five_region_annual_totals():
    annual = pd.read_csv("data/derived/lut_continents_2020_verified.csv")
    shaped = hourly_diurnal(annual, 2020, amplitude=0.2)
    flat = hourly_flat(annual, 2020)
    assert len(shaped) == len(flat) == 8784 * 5
    assert shaped.groupby("region").p_set_mw.nunique().min() > 1
    assert shaped.p_set_mw.min() > 0
    audit = check_energy_conservation(annual.loc[annual.year.eq(2020)], shaped)
    assert audit.difference_mwh.abs().max() < 0.01
    for region, group in shaped.groupby("region"):
        daily = group.loc[group.timestamp.dt.date.eq(pd.Timestamp("2020-01-01").date())]
        assert daily.loc[daily.timestamp.dt.hour.eq(18), "p_set_mw"].iloc[0] > daily.loc[
            daily.timestamp.dt.hour.eq(6), "p_set_mw"].iloc[0]


@pytest.mark.parametrize("amplitude", [-0.1, 1, np.nan, np.inf])
def test_diurnal_rejects_invalid_amplitude(amplitude):
    annual = pd.DataFrame({"region": ["A"], "year": [2020], "value_twh": [1.]})
    with pytest.raises(ValueError, match="Invalid diurnal amplitude"):
        hourly_diurnal(annual, 2020, amplitude=amplitude)


def test_zero_amplitude_matches_flat_profile():
    annual = pd.DataFrame({"region": ["A"], "year": [2020], "value_twh": [1.]})
    assert hourly_diurnal(annual, 2020, amplitude=0).equals(hourly_flat(annual, 2020))
