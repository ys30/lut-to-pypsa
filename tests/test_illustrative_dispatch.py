"""A tiny reproducible fixed-capacity dispatch smoke test.

These synthetic inputs are not LUT data and must not be reported as empirical.
"""
import pandas as pd
import pytest
import pypsa

from lut_to_pypsa.illustrative_dispatch import solve_illustrative_dispatch


def test_synthetic_dispatch_balances_load():
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2020-01-01", periods=3, freq="h"))
    network.add("Bus", "test")
    network.add("Load", "synthetic_demand", bus="test", p_set=10.0)
    network.add("Generator", "synthetic_supply", bus="test", p_nom=20.0,
                marginal_cost=5.0)
    solved, status, condition = solve_illustrative_dispatch(network)
    assert (status, condition) == ("ok", "optimal")
    assert solved.generators_t.p["synthetic_supply"].to_numpy() == pytest.approx([10.0] * 3)
    assert network.generators_t.p.empty


def test_dispatch_rejects_missing_load():
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2020-01-01", periods=1, freq="h"))
    network.add("Bus", "test")
    network.add("Generator", "supply", bus="test", p_nom=20.0)
    with pytest.raises(ValueError, match="Load"):
        solve_illustrative_dispatch(network)
