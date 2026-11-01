"""Synthetic end-to-end integration test; not empirical LUT validation."""
import pandas as pd
import pytest

from lut_to_pypsa.intake_network import build_intake_network
from lut_to_pypsa.illustrative_dispatch import solve_illustrative_dispatch, summarize_illustrative_dispatch
from test_parameter_intake_cli import write_intake


def test_reviewed_intake_builds_network_with_explicit_hourly_demand(tmp_path):
    parameters, evidence, mapping = write_intake(tmp_path)
    buses = tmp_path / "buses.csv"
    demand = tmp_path / "demand.csv"
    pd.DataFrame({"lut_technology": ["example_solar"], "bus": ["test"]}).to_csv(buses, index=False)
    times = pd.date_range("2020-01-01", periods=2, freq="h")
    pd.DataFrame({
        "snapshot": times, "bus": ["test", "test"], "demand_mw": [2.0, 3.0]
    }).to_csv(demand, index=False)
    network = build_intake_network(parameters, evidence, mapping, buses,
                                   snapshots=times, demand_path=demand)
    assert len(network.generators) == 1
    assert network.generators.at["lut_example_solar", "p_nom"] == pytest.approx(10.0)
    assert list(network.loads_t.p_set["load_test"]) == pytest.approx([2.0, 3.0])
    assert len(network.snapshots) == 2


def test_reviewed_intake_rejects_incomplete_hourly_demand(tmp_path):
    parameters, evidence, mapping = write_intake(tmp_path)
    buses = tmp_path / "buses.csv"
    demand = tmp_path / "demand.csv"
    pd.DataFrame({"lut_technology": ["example_solar"], "bus": ["test"]}).to_csv(buses, index=False)
    times = pd.date_range("2020-01-01", periods=2, freq="h")
    pd.DataFrame({
        "snapshot": [times[0]], "bus": ["test"], "demand_mw": [2.0]
    }).to_csv(demand, index=False)
    with pytest.raises(ValueError, match="Incomplete hourly bus demand coverage"):
        build_intake_network(parameters, evidence, mapping, buses,
                             snapshots=times, demand_path=demand)


def test_intake_network_runs_fixed_capacity_dispatch(tmp_path):
    """Synthetic bridge acceptance: CSV -> PyPSA -> HiGHS -> energy/cost audit."""
    parameters, evidence, mapping = write_intake(tmp_path)
    buses = tmp_path / "buses.csv"
    demand = tmp_path / "demand.csv"
    pd.DataFrame({"lut_technology": ["example_solar"], "bus": ["test"]}).to_csv(buses, index=False)
    times = pd.date_range("2020-01-01", periods=2, freq="h")
    pd.DataFrame({"snapshot": times, "bus": ["test", "test"],
                  "demand_mw": [2.0, 3.0]}).to_csv(demand, index=False)
    network = build_intake_network(parameters, evidence, mapping, buses,
                                   snapshots=times, demand_path=demand)
    solved, status, condition = solve_illustrative_dispatch(network)
    report = summarize_illustrative_dispatch(solved)
    assert (status, condition) == ("ok", "optimal")
    assert report["demand_mwh"] == pytest.approx(5.0)
    assert report["generation_mwh"] == pytest.approx(5.0)
    assert report["imbalance_mwh"] == pytest.approx(0.0, abs=1e-6)
    assert report["operating_cost_eur"] == pytest.approx(5.0)
