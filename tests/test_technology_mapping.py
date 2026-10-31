import pandas as pd
import pytest

from lut_to_pypsa.technology_mapping import (
    validate_technology_mapping, audit_inventory_technology_mapping,
)


def mapping():
    return pd.DataFrame({
        "lut_technology": ["solar", "battery"],
        "pypsa_component": ["Generator", "StorageUnit"],
        "pypsa_carrier": ["solar", "battery"],
        "mapping_basis": ["reviewed_test", "reviewed_test"],
        "source_reference": ["https://example.org/solar", "https://example.org/battery"],
    })


def test_mapping_audit_preserves_capacity_and_component_distinction():
    inventory = pd.DataFrame({
        "technology": ["solar", "solar", "battery"],
        "capacity_mw": [100., 50., 20.],
    })
    result = audit_inventory_technology_mapping(inventory, mapping())
    assert result.mapped_capacity_mw.sum() == pytest.approx(170.)
    assert dict(zip(result.lut_technology, result.pypsa_component)) == {
        "battery": "StorageUnit", "solar": "Generator"
    }
    assert result.plant_count.sum() == 3


@pytest.mark.parametrize("mutator,expected", [
    (lambda x: x.iloc[:1], "Unmapped LUT technologies"),
    (lambda x: pd.concat([x, x.iloc[:1]], ignore_index=True), "Duplicate LUT"),
    (lambda x: x.assign(pypsa_component="Bus"), "Unsupported PyPSA"),
    (lambda x: x.assign(source_reference=""), "Blank technology"),
])
def test_mapping_rejects_unverified_or_ambiguous_inputs(mutator, expected):
    with pytest.raises(ValueError, match=expected):
        validate_technology_mapping(mutator(mapping()), ["solar", "battery"])
