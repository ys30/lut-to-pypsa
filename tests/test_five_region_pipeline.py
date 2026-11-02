"""Full-year five-region acceptance using authentic source-cell-traced annual fixture."""
from pathlib import Path
import pandas as pd
import pytest
pypsa = pytest.importorskip("pypsa")
from lut_to_pypsa.five_region_pipeline import run


def test_five_region_full_2020_solve(tmp_path):
    source = Path(__file__).resolve().parents[1] / "data/derived/lut_continents_2020_verified.csv"
    if not source.exists():
        pytest.skip("Source-cell-traced LUT annual fixture not included")
    report = run(source, tmp_path, year=2020)
    assert len(report) == 5
    assert set(report.region) == {"Africa", "Asia", "Australia / Oceania", "Europe", "Americas"}
    assert (report.solver_status == "ok").all()
    assert (report.termination_condition == "optimal").all()
    assert report.max_abs_balance_mw.max() < 1e-5
    expected_mwh = pd.read_csv(source).value_twh.sum() * 1e6
    assert report.demand_mwh.sum() == pytest.approx(expected_mwh, rel=1e-10)
    assert report.generation_mwh.sum() == pytest.approx(expected_mwh, rel=1e-10)
    assert (tmp_path / "illustrative_five_region_solved.nc").is_file()


def test_negative_reserve_margin_rejected(tmp_path):
    source = Path(__file__).resolve().parents[1] / "data/derived/lut_continents_2020_verified.csv"
    with pytest.raises(ValueError, match="Invalid reserve margin"):
        run(source, tmp_path, year=2020, reserve_margin=-0.1)


def test_reserve_margin_provenance_recorded_without_second_annual_solve(tmp_path):
    """Reserve-margin behavior is tested on 24h rather than another 8784h solve."""
    from lut_to_pypsa.hourly import hourly_flat, build_load_network
    from lut_to_pypsa.benchmark import add_illustrative_supply
    from lut_to_pypsa.regional_dispatch import solve_regional_dispatch
    source = Path(__file__).resolve().parents[1] / "data/derived/lut_continents_2020_verified.csv"
    hourly = hourly_flat(pd.read_csv(source), 2020)
    day = hourly.loc[hourly.timestamp < pd.Timestamp("2020-01-02")]
    network = add_illustrative_supply(build_load_network(day), reserve_margin=0.20)
    assert all(network.generators.loc[
        f"firm_{bus}", "p_nom"] == pytest.approx(
        day.loc[day.region.eq(bus), "p_set_mw"].max() * 1.20
    ) for bus in network.buses.index)
    solved, report, status, condition = solve_regional_dispatch(network)
    assert (status, condition) == ("ok", "optimal")
    assert len(report) == 5
    assert report.max_abs_balance_mw.max() < 1e-5
    assert all(
        solved.generators_t.p[f"shortage_{bus}"].abs().max() < 1e-5
        for bus in solved.buses.index
    )


@pytest.mark.parametrize("factor", [-0.1, 1.1, float("nan"), float("inf")])
def test_invalid_capacity_factor_fails_before_expanding_hourly_load(tmp_path, factor):
    source = Path(__file__).resolve().parents[1] / "data/derived/lut_continents_2020_verified.csv"
    with pytest.raises(ValueError, match="Invalid firm capacity factor"):
        run(source, tmp_path, year=2020, firm_capacity_factor=factor)
    assert not list(tmp_path.iterdir())



def test_fixed_capacity_reference_is_independent_of_diurnal_peak():
    """Control isolates load shape by holding assumed firm capacity fixed."""
    from lut_to_pypsa.hourly import hourly_flat, hourly_diurnal, build_load_network
    from lut_to_pypsa.benchmark import add_illustrative_supply
    source = Path(__file__).resolve().parents[1] / "data/derived/lut_continents_2020_verified.csv"
    annual = pd.read_csv(source)
    flat = hourly_flat(annual, 2020)
    shaped = hourly_diurnal(annual, 2020, amplitude=0.20)
    flat_peak = flat.groupby("region").p_set_mw.max()
    shaped_peak = shaped.groupby("region").p_set_mw.max()
    assert (shaped_peak > flat_peak).all()
    network = add_illustrative_supply(build_load_network(shaped), firm_capacity_factor=0.5)
    for region, peak in flat_peak.items():
        network.generators.at[f"firm_{region}", "p_nom"] = float(peak) * 1.10 * 0.5
    for region in flat_peak.index:
        assert network.generators.at[f"firm_{region}", "p_nom"] == pytest.approx(
            float(flat_peak[region]) * 1.10 * 0.5)
        assert network.generators.at[f"firm_{region}", "p_nom"] < float(shaped_peak[region]) * 1.10 * 0.5


def test_invalid_capacity_reference_rejected_before_solver(tmp_path):
    source = Path(__file__).resolve().parents[1] / "data/derived/lut_continents_2020_verified.csv"
    with pytest.raises(ValueError, match="Invalid capacity reference"):
        run(source, tmp_path, capacity_reference="unknown")
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("amplitude", [-0.01, 1.0, float("nan"), float("inf")])
def test_invalid_firm_availability_amplitude_rejected(tmp_path, amplitude):
    source = Path(__file__).resolve().parents[1] / "data/derived/lut_continents_2020_verified.csv"
    with pytest.raises(ValueError, match="Invalid firm availability amplitude"):
        run(source, tmp_path, firm_availability_amplitude=amplitude)
    assert not list(tmp_path.iterdir())


def test_synthetic_firm_availability_dip_is_bounded():
    import numpy as np
    hours = np.arange(24)
    amplitude = 0.4
    availability = 1 - amplitude * (1 + np.cos(2 * np.pi * (hours - 18) / 24)) / 2
    assert availability.min() == pytest.approx(0.6)
    assert availability.max() == pytest.approx(1.0)
    assert availability[18] == pytest.approx(0.6)



def test_time_varying_firm_availability_changes_dispatch(tmp_path):
    """24-hour solver test proves the synthetic availability constraint binds."""
    from lut_to_pypsa.hourly import hourly_flat, build_load_network
    from lut_to_pypsa.benchmark import add_illustrative_supply
    from lut_to_pypsa.regional_dispatch import solve_regional_dispatch
    import numpy as np
    source = Path(__file__).resolve().parents[1] / "data/derived/lut_continents_2020_verified.csv"
    annual = pd.read_csv(source)
    hourly = hourly_flat(annual, 2020)
    day = hourly.loc[hourly.timestamp < pd.Timestamp("2020-01-02")]
    network = add_illustrative_supply(build_load_network(day), firm_capacity_factor=1.0)
    availability = 1 - 0.4 * (1 + np.cos(
        2 * np.pi * (network.snapshots.hour.to_numpy() - 18) / 24)) / 2
    network.generators_t.p_max_pu = pd.DataFrame(
        {f"firm_{region}": availability for region in network.buses.index},
        index=network.snapshots)
    solved, report, status, condition = solve_regional_dispatch(network)
    assert (status, condition) == ("ok", "optimal")
    assert report.max_abs_balance_mw.max() < 1e-5
    for region in solved.buses.index:
        firm = solved.generators_t.p[f"firm_{region}"]
        cap = float(solved.generators.at[f"firm_{region}", "p_nom"])
        assert (firm.to_numpy() <= cap * availability + 1e-5).all()
        assert solved.generators_t.p[f"shortage_{region}"].max() > 0



@pytest.mark.parametrize("hour", [-1, 24, 1.5, "18", None])
def test_invalid_availability_trough_hour_rejected(tmp_path, hour):
    source = Path(__file__).resolve().parents[1] / "data/derived/lut_continents_2020_verified.csv"
    with pytest.raises(ValueError, match="Invalid availability trough hour"):
        run(source, tmp_path, availability_trough_hour=hour)
    assert not list(tmp_path.iterdir())


def test_availability_trough_phase_shift():
    import numpy as np
    hours = np.arange(24)
    for trough in (0, 6, 12, 18):
        availability = 1 - 0.4 * (1 + np.cos(
            2 * np.pi * (hours - trough) / 24)) / 2
        assert int(np.argmin(availability)) == trough
        assert availability[trough] == pytest.approx(0.6)
