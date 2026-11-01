"""A tiny reproducible fixed-capacity dispatch smoke test.

These synthetic inputs are not LUT data and must not be reported as empirical.
"""
import pandas as pd
import pytest
import pypsa

from lut_to_pypsa.illustrative_dispatch import solve_illustrative_dispatch, summarize_illustrative_dispatch


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


def test_synthetic_dispatch_energy_and_cost_audit():
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2020-01-01", periods=3, freq="h"))
    network.add("Bus", "test")
    network.add("Load", "demand", bus="test", p_set=10.0)
    network.add("Generator", "supply", bus="test", p_nom=20.0, marginal_cost=5.0)
    solved, _, _ = solve_illustrative_dispatch(network)
    report = summarize_illustrative_dispatch(solved)
    assert report["demand_mwh"] == pytest.approx(30.0)
    assert report["generation_mwh"] == pytest.approx(30.0)
    assert report["imbalance_mwh"] == pytest.approx(0.0)
    assert report["operating_cost_eur"] == pytest.approx(150.0)
    assert report["scope"] == "synthetic_single_bus_generator_only"


def test_dispatch_audit_rejects_storage_scope():
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2020-01-01", periods=1, freq="h"))
    network.add("Bus", "test")
    network.add("Load", "demand", bus="test", p_set=1.0)
    network.add("Generator", "supply", bus="test", p_nom=2.0)
    network.add("StorageUnit", "battery", bus="test", p_nom=1.0, max_hours=2.0)
    with pytest.raises(ValueError, match="generator-only"):
        summarize_illustrative_dispatch(network)


def test_dispatch_audit_combines_static_and_hourly_loads():
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2020-01-01", periods=3, freq="h"))
    network.add("Bus", "test")
    network.add("Load", "constant", bus="test", p_set=4.0)
    network.add("Load", "varying", bus="test", p_set=pd.Series([2.0, 3.0, 4.0], index=network.snapshots))
    network.add("Generator", "supply", bus="test", p_nom=20.0, marginal_cost=5.0)
    solved, _, _ = solve_illustrative_dispatch(network)
    report = summarize_illustrative_dispatch(solved)
    assert report["demand_mwh"] == pytest.approx(21.0)
    assert report["generation_mwh"] == pytest.approx(21.0)
    assert report["operating_cost_eur"] == pytest.approx(105.0)


def test_dispatch_audit_respects_nonuniform_snapshot_weights():
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2020-01-01", periods=2, freq="h"))
    network.snapshot_weightings["generators"] = pd.Series([1.0, 2.0], index=network.snapshots, dtype=float)
    network.snapshot_weightings["objective"] = pd.Series([1.0, 2.0], index=network.snapshots, dtype=float)
    network.add("Bus", "test")
    network.add("Load", "demand", bus="test", p_set=10.0)
    network.add("Generator", "supply", bus="test", p_nom=20.0, marginal_cost=5.0)
    solved, _, _ = solve_illustrative_dispatch(network)
    report = summarize_illustrative_dispatch(solved)
    assert report["demand_mwh"] == pytest.approx(30.0)
    assert report["generation_mwh"] == pytest.approx(30.0)
    assert report["operating_cost_eur"] == pytest.approx(150.0)


def test_dispatch_audit_rejects_canceling_hourly_imbalances():
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2020-01-01", periods=2, freq="h"))
    network.add("Bus", "test")
    network.add("Load", "demand", bus="test", p_set=10.0)
    network.add("Generator", "supply", bus="test", p_nom=20.0, marginal_cost=5.0)
    solved, _, _ = solve_illustrative_dispatch(network)
    solved.generators_t.p.loc[:, "supply"] = [9.0, 11.0]
    with pytest.raises(ValueError, match="Hourly dispatch energy imbalance"):
        summarize_illustrative_dispatch(solved)


def test_dispatch_cost_uses_objective_not_generator_weights():
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2020-01-01", periods=2, freq="h"))
    network.snapshot_weightings["generators"] = pd.Series([1.0, 2.0], index=network.snapshots, dtype=float)
    network.snapshot_weightings["objective"] = pd.Series([2.0, 3.0], index=network.snapshots, dtype=float)
    network.add("Bus", "test")
    network.add("Load", "demand", bus="test", p_set=10.0)
    network.add("Generator", "supply", bus="test", p_nom=20.0, marginal_cost=5.0)
    solved, _, _ = solve_illustrative_dispatch(network)
    report = summarize_illustrative_dispatch(solved)
    assert report["generation_mwh"] == pytest.approx(30.0)
    assert report["operating_cost_eur"] == pytest.approx(250.0)


@pytest.mark.parametrize("bad_value", [float("inf"), float("-inf")])
def test_dispatch_audit_rejects_nonfinite_generation(bad_value):
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2020-01-01", periods=2, freq="h"))
    network.add("Bus", "test")
    network.add("Load", "demand", bus="test", p_set=10.0)
    network.add("Generator", "supply", bus="test", p_nom=20.0, marginal_cost=5.0)
    solved, _, _ = solve_illustrative_dispatch(network)
    solved.generators_t.p.loc[network.snapshots[0], "supply"] = bad_value
    with pytest.raises(ValueError, match="Nonfinite generator dispatch"):
        summarize_illustrative_dispatch(solved)


def test_dispatch_audit_rejects_generator_on_different_bus():
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2020-01-01", periods=1, freq="h"))
    network.add("Bus", "test")
    network.add("Load", "demand", bus="test", p_set=1.0)
    network.add("Generator", "supply", bus="test", p_nom=2.0)
    # A dangling reference must not be silently accepted as a single-bus model.
    network.generators.loc["supply", "bus"] = "nonexistent"
    with pytest.raises(ValueError, match="same bus"):
        summarize_illustrative_dispatch(network)


def test_dispatch_audit_rejects_load_on_different_bus():
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2020-01-01", periods=1, freq="h"))
    network.add("Bus", "test")
    network.add("Load", "demand", bus="test", p_set=1.0)
    network.add("Generator", "supply", bus="test", p_nom=2.0)
    network.loads.loc["demand", "bus"] = "nonexistent"
    with pytest.raises(ValueError, match="same bus"):
        summarize_illustrative_dispatch(network)


def test_dispatch_audit_supports_time_varying_marginal_costs():
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2020-01-01", periods=2, freq="h"))
    network.add("Bus", "test")
    network.add("Load", "demand", bus="test", p_set=10.0)
    network.add("Generator", "supply", bus="test", p_nom=20.0,
                marginal_cost=pd.Series([5.0, 10.0], index=network.snapshots))
    solved, _, _ = solve_illustrative_dispatch(network)
    report = summarize_illustrative_dispatch(solved)
    assert report["operating_cost_eur"] == pytest.approx(150.0)
    assert report["generation_mwh"] == pytest.approx(20.0)
