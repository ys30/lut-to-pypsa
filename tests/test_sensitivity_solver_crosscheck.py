"""Cross-check PyPSA stressed dispatch against independent analytical predictions."""
from pathlib import Path
import pandas as pd
import pytest
pytest.importorskip("pypsa")

from lut_to_pypsa.hourly import hourly_flat, build_load_network
from lut_to_pypsa.benchmark import add_illustrative_supply
from lut_to_pypsa.regional_dispatch import solve_regional_dispatch
from lut_to_pypsa.analytical_sensitivity import expected_dispatch

SOURCE = Path(__file__).resolve().parents[1] / "data/derived/lut_continents_2020_verified.csv"

@pytest.mark.parametrize("factor", [1.0, 0.75, 0.5, 0.25])
def test_24h_solver_matches_closed_form_for_all_regions(factor):
    annual = pd.read_csv(SOURCE)
    hourly = hourly_flat(annual, 2020)
    day = hourly.loc[hourly.timestamp < pd.Timestamp("2020-01-02")]
    n = add_illustrative_supply(build_load_network(day), firm_capacity_factor=factor)
    solved, report, status, condition = solve_regional_dispatch(n)
    assert (status, condition) == ("ok", "optimal")
    reference = expected_dispatch(SOURCE, firm_capacity_factor=factor).set_index("region")
    weights = solved.snapshot_weightings["generators"]
    for region in reference.index:
        daily_demand = reference.at[region, "demand_mwh"] * 24 / 8784
        daily_firm = reference.at[region, "firm_generation_mwh"] * 24 / 8784
        daily_shortage = reference.at[region, "shortage_generation_mwh"] * 24 / 8784
        firm = float((solved.generators_t.p[f"firm_{region}"] * weights).sum())
        shortage = float((solved.generators_t.p[f"shortage_{region}"] * weights).sum())
        assert firm == pytest.approx(daily_firm, abs=1e-3)
        assert shortage == pytest.approx(daily_shortage, abs=1e-3)
        assert firm + shortage == pytest.approx(daily_demand, abs=1e-3)
    assert report.max_abs_balance_mw.max() < 1e-5
