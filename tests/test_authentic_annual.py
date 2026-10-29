"""Full-year, source-traced 2020 LUT demand audit.

This validates annual-to-hourly conversion, not historical hourly shape or
real-world generation/transmission. The input is a five-continent Excel-derived
fixture with source-cell identifiers.
"""
from pathlib import Path

import pandas as pd

from lut_to_pypsa.hourly import hourly_flat, check_energy_conservation


FIXTURE = Path(__file__).resolve().parents[1] / "data/derived/lut_continents_2020_verified.csv"


def test_authentic_lut_2020_full_year_energy_conservation():
    annual = pd.read_csv(FIXTURE)
    assert len(annual) == 5
    assert annual.year.eq(2020).all()
    assert annual.source_cell.tolist() == ["C11", "C12", "C13", "C14", "C15"]
    assert annual.region.nunique() == 5
    assert annual.value_twh.sum() > 20_000

    hourly = hourly_flat(annual, 2020)
    assert len(hourly) == 5 * 8784
    assert hourly.timestamp.nunique() == 8784
    assert hourly.groupby("region").size().eq(8784).all()
    assert hourly.p_set_mw.ge(0).all()

    audit = check_energy_conservation(annual, hourly)
    assert len(audit) == 5
    assert audit.difference_mwh.abs().max() < 0.01
    assert abs(hourly.p_set_mw.sum() - annual.value_twh.sum() * 1e6) < 0.01
