import pandas as pd
import pytest

from lut_to_pypsa.technology_parameters import validate_technology_parameters


def fixtures():
    mapping = pd.DataFrame({
        "lut_technology": ["solar", "battery"],
        "pypsa_component": ["Generator", "StorageUnit"],
    })
    params = pd.DataFrame({
        "lut_technology": ["solar", "battery"],
        "pypsa_component": ["Generator", "StorageUnit"],
        "capacity_mw": [100., 20.],
        "capacity_basis": ["electrical_nameplate", "power_rating"],
        "source_reference": ["https://example.org/a", "https://example.org/b"],
        "data_year": [2020, 2020],
        "efficiency": [1., .9],
        "efficiency_basis": ["per_direction", "per_direction"],
        "availability_fraction": [.25, 1.],
        "max_hours": [float("nan"), 4.],
    })
    return mapping, params


def test_valid_parameters_preserve_inputs():
    mapping, params = fixtures()
    result = validate_technology_parameters(params, mapping)
    assert result.capacity_mw.sum() == pytest.approx(120.)
    assert result.loc[result.lut_technology.eq("battery"), "max_hours"].iloc[0] == 4.


@pytest.mark.parametrize("column,value,match", [
    ("capacity_mw", -1, "Invalid numeric"),
    ("availability_fraction", 1.1, "Invalid numeric"),
    ("efficiency", 0, "Efficiency"),
    ("max_hours", 0, "max_hours"),
    ("source_reference", "unknown", "Invalid parameter source"),
])
def test_invalid_physical_or_provenance_parameters_rejected(column, value, match):
    mapping, params = fixtures()
    params.loc[1, column] = value
    with pytest.raises(ValueError, match=match):
        validate_technology_parameters(params, mapping)


def test_reject_store_without_explicit_energy_capacity_contract():
    mapping, params = fixtures()
    mapping.loc[1, "pypsa_component"] = "Store"
    params.loc[1, "pypsa_component"] = "Store"
    with pytest.raises(ValueError, match="Store requires"):
        validate_technology_parameters(params, mapping)


def test_storage_requires_reviewed_efficiency_at_intake():
    mapping, params = fixtures()
    params.loc[params.lut_technology.eq("battery"), "efficiency"] = float("nan")
    with pytest.raises(ValueError, match="StorageUnit requires reviewed efficiency"):
        validate_technology_parameters(params, mapping)


def test_storage_round_trip_basis_is_accepted_at_intake():
    mapping, params = fixtures()
    params.loc[params.lut_technology.eq("battery"), "efficiency_basis"] = "round_trip"
    result = validate_technology_parameters(params, mapping)
    assert result.loc[result.lut_technology.eq("battery"), "efficiency_basis"].iloc[0] == "round_trip"


@pytest.mark.parametrize("invalid_mapping", [
    pd.DataFrame(columns=["lut_technology", "pypsa_component"]),
    pd.DataFrame({"lut_technology": ["solar", None], "pypsa_component": ["Generator", "StorageUnit"]}),
    pd.DataFrame({"lut_technology": ["solar", "  "], "pypsa_component": ["Generator", "StorageUnit"]}),
    pd.DataFrame({"lut_technology": ["solar", "battery"], "pypsa_component": ["Generator", None]}),
])
def test_reject_incomplete_technology_mapping(invalid_mapping):
    _, params = fixtures()
    with pytest.raises(ValueError, match="(?i)technology mapping"):
        validate_technology_parameters(params, invalid_mapping)


@pytest.mark.parametrize("missing_column", ["lut_technology", "pypsa_component"])
def test_reject_missing_mapping_columns_with_validation_error(missing_column):
    mapping, params = fixtures()
    mapping = mapping.drop(columns=[missing_column])
    with pytest.raises(ValueError, match="Missing technology mapping columns"):
        validate_technology_parameters(params, mapping)


def test_reject_blank_mapping_component():
    mapping, params = fixtures()
    mapping.loc[1, "pypsa_component"] = "  "
    with pytest.raises(ValueError, match="Blank technology mapping component"):
        validate_technology_parameters(params, mapping)
