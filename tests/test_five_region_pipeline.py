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
