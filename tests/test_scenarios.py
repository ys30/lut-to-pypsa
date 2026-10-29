import pandas as pd
import pytest

from lut_to_pypsa.scenarios import scale_annual_demand, summarize_scenarios


def test_scenarios_preserve_source_provenance():
    source = pd.read_csv("data/derived/lut_continents_2020_verified.csv")
    result = scale_annual_demand(source, {"low_demand": 0.9, "high_demand": 1.1})
    assert len(result) == 15
    assert set(result.scenario) == {"baseline", "low_demand", "high_demand"}
    for scenario, factor in [("baseline", 1), ("low_demand", .9), ("high_demand", 1.1)]:
        subset = result[result.scenario == scenario]
        assert subset.source_cell.tolist() == source.source_cell.tolist()
        assert subset.scenario_demand_twh.sum() == pytest.approx(source.value_twh.sum() * factor)
    summary = summarize_scenarios(result)
    assert summary.regions.eq(5).all()


def test_scenarios_reject_invalid_inputs():
    source = pd.DataFrame({"region": ["Africa"], "year": [2020], "value_twh": [1.]})
    with pytest.raises(ValueError, match="multiplier"):
        scale_annual_demand(source, {"bad": -1})
    with pytest.raises(ValueError, match="Duplicate"):
        scale_annual_demand(pd.concat([source, source]), {"high": 1.1})
