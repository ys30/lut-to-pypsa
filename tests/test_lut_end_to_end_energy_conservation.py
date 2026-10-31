"""Numerical LUT annual-to-hourly-to-PyPSA input acceptance, not model calibration."""
import pandas as pd
import pytest

from lut_to_pypsa.hourly import hourly_flat, build_load_network


def test_source_traced_2020_lut_energy_conserved_through_pypsa_network():
    annual = pd.read_csv("data/derived/lut_continents_2020_verified.csv")
    assert set(annual.source_cell) == {"C11", "C12", "C13", "C14", "C15"}
    assert set(annual.quantity_kind) == {"annual_energy_service_demand"}
    hourly = hourly_flat(annual, 2020)
    assert len(hourly) == 5 * 8784
    network = build_load_network(hourly)
    assert len(network.snapshots) == 8784
    assert set(network.buses.index) == set(annual.region)
    assert set(network.loads.bus) == set(annual.region)
    assert network.loads_t.p_set.shape == (8784, 5)
    for row in annual.itertuples(index=False):
        load_id = "load_" + row.region
        actual_mwh = float(network.loads_t.p_set[load_id].sum())
        expected_mwh = float(row.value_twh) * 1e6
        assert actual_mwh == pytest.approx(expected_mwh, abs=0.01)
    assert network.generators.empty
    assert network.lines.empty
    assert network.links.empty
