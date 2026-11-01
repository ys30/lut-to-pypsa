"""Independent analytical baseline audit; does not require PyPSA or a solver."""
from pathlib import Path
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
ANNUAL = ROOT / "data/derived/lut_continents_2020_verified.csv"
EXPECTED = ROOT / "data/derived/five_region_2020_analytical_expectations.csv"


def test_2020_expectations_match_source_and_explicit_assumptions():
    annual = pd.read_csv(ANNUAL)
    baseline = pd.read_csv(EXPECTED)
    assert len(annual) == len(baseline) == 5
    assert annual.region.is_unique and baseline.region.is_unique
    assert set(annual.region) == set(baseline.region)
    assert set(annual.year) == set(baseline.year) == {2020}
    joined = annual.merge(baseline, on=["region", "year"], validate="one_to_one")
    assert joined.source_demand_twh.tolist() == pytest.approx(joined.value_twh.tolist())
    assert joined.expected_flat_hourly_mw.tolist() == pytest.approx(
        (joined.value_twh * 1e6 / 8784).tolist(), rel=1e-12
    )
    assert joined.expected_annual_mwh.tolist() == pytest.approx(
        (joined.value_twh * 1e6).tolist(), rel=1e-12
    )
    assert joined.expected_illustrative_cost_units.tolist() == pytest.approx(
        (joined.value_twh * 1e6 * 50).tolist(), rel=1e-12
    )
    assert (joined.expected_shortage_mwh == 0).all()
    assert joined.value_twh.sum() == pytest.approx(22487.656609444377)
