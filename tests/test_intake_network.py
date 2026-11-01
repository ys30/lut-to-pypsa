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


def test_intake_cli_writes_solved_netcdf_and_json(tmp_path):
    """Exercise the actual CLI entrypoint and its two user-facing artifacts."""
    import json
    from lut_to_pypsa.intake_network import main
    parameters, evidence, mapping = write_intake(tmp_path)
    buses, demand, snapshots = [tmp_path / name for name in
                               ("buses.csv", "demand.csv", "snapshots.csv")]
    times = pd.date_range("2020-01-01", periods=2, freq="h")
    pd.DataFrame({"lut_technology": ["example_solar"], "bus": ["test"]}).to_csv(buses, index=False)
    pd.DataFrame({"snapshot": times, "bus": ["test", "test"],
                  "demand_mw": [2.0, 3.0]}).to_csv(demand, index=False)
    pd.DataFrame({"snapshot": times}).to_csv(snapshots, index=False)
    output, summary_path = tmp_path / "network.nc", tmp_path / "summary.json"
    main(["--parameters", str(parameters), "--evidence", str(evidence),
          "--mapping", str(mapping), "--buses", str(buses),
          "--snapshots", str(snapshots), "--demand", str(demand),
          "--output", str(output), "--solve-illustrative",
          "--summary-json", str(summary_path)])
    assert output.is_file() and output.stat().st_size > 0
    report = json.loads(summary_path.read_text(encoding="utf-8"))
    assert report["solver_status"] == "ok"
    assert report["termination_condition"] == "optimal"
    assert report["demand_mwh"] == pytest.approx(5.0)
    assert report["operating_cost_eur"] == pytest.approx(5.0)


def test_intake_network_accepts_numeric_strings_and_utc_snapshots(tmp_path):
    """CSV numeric coercion and UTC normalization survive the full adapter."""
    parameters, evidence, mapping = write_intake(tmp_path)
    buses, demand = tmp_path / "buses.csv", tmp_path / "demand.csv"
    pd.DataFrame({"lut_technology": ["example_solar"], "bus": ["test"]}).to_csv(buses, index=False)
    times = ["2020-01-01T00:00:00Z", "2020-01-01T01:00:00Z"]
    pd.DataFrame({"snapshot": times, "bus": ["test", "test"],
                  "demand_mw": ["2.0", "3.0"]}).to_csv(demand, index=False)
    network = build_intake_network(parameters, evidence, mapping, buses,
                                   snapshots=times, demand_path=demand)
    assert network.snapshots.tz is None
    assert list(network.loads_t.p_set["load_test"]) == pytest.approx([2.0, 3.0])


def test_cli_rejects_missing_solve_arguments_before_export(tmp_path):
    """Invalid CLI invocation must not create misleading output files."""
    from lut_to_pypsa.intake_network import main
    parameters, evidence, mapping = write_intake(tmp_path)
    buses, snapshots = tmp_path / "buses.csv", tmp_path / "snapshots.csv"
    pd.DataFrame({"lut_technology": ["example_solar"], "bus": ["test"]}).to_csv(buses, index=False)
    pd.DataFrame({"snapshot": ["2020-01-01T00:00:00Z"]}).to_csv(snapshots, index=False)
    output = tmp_path / "should_not_exist.nc"
    with pytest.raises(SystemExit):
        main(["--parameters", str(parameters), "--evidence", str(evidence),
              "--mapping", str(mapping), "--buses", str(buses),
              "--snapshots", str(snapshots), "--output", str(output),
              "--solve-illustrative"])
    assert not output.exists()
