import pandas as pd
import pytest

from lut_to_pypsa.capacity_inputs import validate_capacity_inventory, run


def fixture():
    inventory = pd.DataFrame({
        "plant_id": ["US-1", "US-2"], "source_region": ["US", "US"],
        "technology": ["wind", "solar"], "capacity_mw": [100., 50.],
        "data_year": [2020, 2020], "source_dataset": ["example", "example"],
        "source_url": ["https://example.org/1", "https://example.org/2"],
    })
    mapping = pd.DataFrame({"source_region": ["US"], "lut_region": ["Americas"]})
    return inventory, mapping


def test_partial_geographic_coverage_is_explicit():
    inventory, mapping = fixture()
    regions = {"Africa", "Asia", "Australia / Oceania", "Europe", "Americas"}
    summary, coverage = validate_capacity_inventory(inventory, mapping, regions, 2020)
    assert summary.capacity_mw.sum() == pytest.approx(150.)
    assert len(coverage) == 5
    assert coverage.capacity_inventory_covered.sum() == 1
    assert coverage.loc[coverage.lut_region == "Americas", "capacity_inventory_covered"].all()


def test_reject_unknown_geography_and_bad_year():
    inventory, mapping = fixture()
    with pytest.raises(ValueError, match="Unknown LUT"):
        validate_capacity_inventory(inventory, mapping, {"Africa"}, 2020)
    with pytest.raises(ValueError, match="year mismatch"):
        validate_capacity_inventory(inventory.assign(data_year=2025), mapping, {"Americas"}, 2020)


def test_no_partial_global_capacity_claim(tmp_path):
    inventory, mapping = fixture()
    a = tmp_path / "inventory.csv"
    b = tmp_path / "mapping.csv"
    inventory.to_csv(a, index=False)
    mapping.to_csv(b, index=False)
    demand = "data/derived/lut_continents_2020_verified.csv"
    with pytest.raises(ValueError, match="Incomplete LUT geographic coverage"):
        run(a, b, demand, tmp_path / "out")
    coverage = run(a, b, demand, tmp_path / "out", allow_partial=True)
    assert coverage.capacity_inventory_covered.sum() == 1
    assert (tmp_path / "out" / "capacity_coverage_audit.csv").exists()
