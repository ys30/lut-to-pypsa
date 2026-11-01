"""Closed-form sensitivity regression tests (no PyPSA dependency)."""
from pathlib import Path
import pytest
from lut_to_pypsa.analytical_sensitivity import expected_dispatch

SOURCE = Path(__file__).resolve().parents[1] / "data/derived/lut_continents_2020_verified.csv"

@pytest.mark.parametrize("factor,shortage_fraction", [
    (1.0, 0.0),
    (0.75, 0.175),
    (0.5, 0.45),
    (0.25, 0.725),
])
def test_five_region_capacity_sensitivity(factor, shortage_fraction):
    result = expected_dispatch(SOURCE, firm_capacity_factor=factor)
    assert len(result) == 5
    assert result.shortage_fraction.tolist() == pytest.approx([shortage_fraction] * 5)
    assert (result.firm_generation_mwh + result.shortage_generation_mwh
            - result.demand_mwh).abs().max() < 0.01
    assert result.demand_mwh.sum() == pytest.approx(22487656609.44438)

def test_invalid_factor_rejected():
    with pytest.raises(ValueError):
        expected_dispatch(SOURCE, firm_capacity_factor=1.1)
