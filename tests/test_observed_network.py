import pandas as pd
import pytest

from lut_to_pypsa.observed_network import build_observed_capacity_network


def inputs():
    demand = pd.read_csv("data/derived/lut_continents_2020_verified.csv")
    inventory = pd.DataFrame({
        "plant_id": ["plant1"], "source_region": ["US"],
        "technology": ["solar"], "capacity_mw": [100.0],
        "data_year": [2020], "source_dataset": ["test_only"],
        "source_url": ["https://example.org/test"],
    })
    mapping = pd.DataFrame({"source_region": ["US"], "lut_region": ["Americas"]})
    return demand, inventory, mapping


def test_reject_incomplete_coverage():
    demand, inventory, mapping = inputs()
    with pytest.raises(ValueError, match="Incomplete geographic coverage"):
        build_observed_capacity_network(demand, inventory, mapping)


def test_explicit_partial_network_is_unsolved():
    demand, inventory, mapping = inputs()
    network, summary, coverage = build_observed_capacity_network(
        demand, inventory, mapping, allow_partial=True)
    assert set(network.buses.index) == {"Americas"}
    assert len(network.generators) == 1
    assert network.generators.p_nom.iloc[0] == pytest.approx(100)
    assert len(network.snapshots) == 8784
    assert summary.capacity_mw.sum() == pytest.approx(100)
    assert coverage.capacity_inventory_covered.sum() == 1
    assert network.generators_t.p.empty


def test_bad_inventory_year_rejected():
    demand, inventory, mapping = inputs()
    with pytest.raises(ValueError, match="year mismatch"):
        build_observed_capacity_network(
            demand, inventory.assign(data_year=2025), mapping, allow_partial=True)
