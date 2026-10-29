import pandas as pd
import pytest

from lut_to_pypsa.fixed_capacity import compare_fixed_capacity


def test_capacity_remains_fixed_and_high_demand_exposes_shortage():
    annual = pd.read_csv("data/derived/lut_continents_2020_verified.csv")
    result = compare_fixed_capacity(annual, hours=24)
    assert len(result) == 15
    capacity = result.pivot(index="region", columns="scenario",
                            values="baseline_firm_capacity_mw")
    assert (capacity.nunique(axis=1) == 1).all()
    baseline = result[result.scenario == "baseline"]
    low = result[result.scenario == "low_demand"]
    high = result[result.scenario == "high_demand"]
    assert baseline.unserved_energy_mwh.abs().max() < 1e-5
    assert low.unserved_energy_mwh.abs().max() < 1e-5
    # High demand of 110% equals baseline firm capacity with 10% reserve.
    assert high.unserved_energy_mwh.abs().max() < 1e-4
    assert result.balance_residual_mwh.abs().max() < 1e-4


def test_capacity_shortfall_above_reserve_margin():
    annual = pd.read_csv("data/derived/lut_continents_2020_verified.csv")
    result = compare_fixed_capacity(annual, multipliers={"stress": 1.25}, hours=24)
    stress = result[result.scenario == "stress"]
    assert stress.unserved_energy_mwh.sum() > 0
    assert stress.unserved_share.min() == pytest.approx(0.15 / 1.25, abs=1e-6)
    assert stress.balance_residual_mwh.abs().max() < 1e-4


def test_invalid_year_rejected():
    annual = pd.read_csv("data/derived/lut_continents_2020_verified.csv")
    with pytest.raises(ValueError, match="2020"):
        compare_fixed_capacity(annual.assign(year=2025))


def test_export_includes_actual_stress_scenario(tmp_path):
    from lut_to_pypsa.fixed_capacity import run
    result = run("data/derived/lut_continents_2020_verified.csv", tmp_path, hours=24)
    assert set(result.scenario) == {"baseline", "low_demand", "high_demand", "stress"}
    assert len(result) == 20
    stress = result[result.scenario == "stress"]
    assert stress.unserved_energy_mwh.sum() > 0
    assert stress.unserved_share.min() == pytest.approx(0.12, abs=1e-6)
    saved = pd.read_csv(tmp_path / "fixed_capacity_scenario_dispatch.csv")
    assert len(saved) == 20
