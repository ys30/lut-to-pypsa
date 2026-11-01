"""Synthetic two-region dispatch acceptance test (not empirical validation)."""
import pandas as pd
import pytest
pypsa = pytest.importorskip("pypsa")
from lut_to_pypsa.regional_dispatch import solve_regional_dispatch


def test_two_disconnected_regions_solve_and_balance():
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2020-01-01", periods=2, freq="h"))
    for bus, demand, cost in [("Africa", [2.0, 3.0], 10.0),
                              ("Europe", [4.0, 1.0], 20.0)]:
        network.add("Bus", bus)
        network.add("Generator", f"gen_{bus}", bus=bus, p_nom=10,
                    marginal_cost=cost)
        network.add("Load", f"load_{bus}", bus=bus, p_set=demand)
    solved, report, status, condition = solve_regional_dispatch(network)
    assert (status, condition) == ("ok", "optimal")
    assert set(report.bus) == {"Africa", "Europe"}
    assert report.demand_mwh.sum() == pytest.approx(10.0)
    assert report.generation_mwh.sum() == pytest.approx(10.0)
    assert report.max_abs_balance_mw.max() < 1e-5
    assert solved.generators_t.p["gen_Africa"].tolist() == pytest.approx([2, 3])


def test_regional_dispatch_rejects_interregional_link():
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2020-01-01", periods=1, freq="h"))
    for bus in ["a", "b"]:
        network.add("Bus", bus)
        network.add("Generator", f"g_{bus}", bus=bus, p_nom=5)
        network.add("Load", f"l_{bus}", bus=bus, p_set=1)
    network.add("Link", "transfer", bus0="a", bus1="b", p_nom=2)
    with pytest.raises(ValueError, match="excludes storage"):
        solve_regional_dispatch(network)


def test_shortage_proxy_activates_when_firm_capacity_is_insufficient():
    """A stressed scenario must show nonzero shortage-proxy dispatch."""
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2020-01-01", periods=2, freq="h"))
    network.add("Bus", "test")
    network.add("Generator", "firm_test", bus="test", p_nom=5,
                marginal_cost=50)
    network.add("Generator", "shortage_test", bus="test", p_nom=10,
                marginal_cost=10000)
    network.add("Load", "load_test", bus="test", p_set=[8, 10])
    solved, report, status, condition = solve_regional_dispatch(network)
    assert (status, condition) == ("ok", "optimal")
    assert solved.generators_t.p["firm_test"].tolist() == pytest.approx([5, 5])
    assert solved.generators_t.p["shortage_test"].tolist() == pytest.approx([3, 5])
    assert report.demand_mwh.iloc[0] == pytest.approx(18)
    assert report.generation_mwh.iloc[0] == pytest.approx(18)
    assert report.max_abs_balance_mw.max() < 1e-5


def test_capacity_derating_changes_shortage_dispatch():
    from lut_to_pypsa.benchmark import add_illustrative_supply
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2020-01-01", periods=2, freq="h"))
    network.add("Bus", "test")
    network.add("Load", "load_test", bus="test", p_set=[8, 10])
    add_illustrative_supply(network, reserve_margin=0.0, firm_capacity_factor=0.5)
    assert network.generators.at["firm_test", "p_nom"] == pytest.approx(5)
    solved, report, status, condition = solve_regional_dispatch(network)
    assert (status, condition) == ("ok", "optimal")
    assert solved.generators_t.p["shortage_test"].tolist() == pytest.approx([3, 5])
    assert report.max_abs_balance_mw.max() < 1e-5


@pytest.mark.parametrize("factor", [-0.1, 1.1, float("nan"), float("inf")])
def test_invalid_firm_capacity_factor_rejected(factor):
    from lut_to_pypsa.benchmark import add_illustrative_supply
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2020-01-01", periods=1, freq="h"))
    network.add("Bus", "test")
    network.add("Load", "load_test", bus="test", p_set=2)
    with pytest.raises(ValueError, match="Invalid reserve margin or costs"):
        add_illustrative_supply(network, firm_capacity_factor=factor)
