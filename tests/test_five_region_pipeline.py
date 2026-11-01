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


def test_reserve_margin_provenance_recorded(tmp_path):
    source = Path(__file__).resolve().parents[1] / "data/derived/lut_continents_2020_verified.csv"
    report = run(source, tmp_path, year=2020, reserve_margin=0.20)
    assert (report.assumed_reserve_margin == 0.20).all()
    assert (report.shortage_generation_mwh.abs() < 0.01).all()
