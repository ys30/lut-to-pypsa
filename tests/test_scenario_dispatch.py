import pandas as pd
import pytest

from lut_to_pypsa.scenario_dispatch import compare_dispatch


def test_three_authentic_scenarios_solve_and_reconcile():
    source = pd.read_csv("data/derived/lut_continents_2020_verified.csv")
    result = compare_dispatch(source, hours=24)
    assert len(result) == 15
    assert set(result.scenario) == {"baseline", "low_demand", "high_demand"}
    assert result.groupby("scenario").region.nunique().eq(5).all()
    assert result.unserved_energy_mwh.abs().max() < 1e-5
    assert result.balance_residual_mwh.abs().max() < 1e-5
    sums = result.groupby("scenario").demand_mwh.sum()
    assert sums["low_demand"] == pytest.approx(sums["baseline"] * 0.9)
    assert sums["high_demand"] == pytest.approx(sums["baseline"] * 1.1)
    assert result.illustrative_dispatch_cost.ge(0).all()


def test_reject_non_2020_and_bad_hours():
    source = pd.read_csv("data/derived/lut_continents_2020_verified.csv")
    with pytest.raises(ValueError, match="hours"):
        compare_dispatch(source, hours=0)
    with pytest.raises(ValueError, match="2020"):
        compare_dispatch(source.assign(year=2025))
