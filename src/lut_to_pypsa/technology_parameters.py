"""Audit physical and economic parameters before any LUT-to-PyPSA solve.

This module deliberately does not infer absent data or assign default costs.
"""
import math
import pandas as pd

REQUIRED = {
    "lut_technology", "pypsa_component", "capacity_mw",
    "capacity_basis", "source_reference", "data_year",
}
OPTIONAL = {
    "efficiency", "marginal_cost_eur_per_mwh",
    "capital_cost_eur_per_mw_year", "availability_fraction",
    "max_hours", "standing_loss_per_hour", "efficiency_basis",
}


def validate_technology_parameters(parameters, mapping):
    missing = REQUIRED - set(parameters.columns)
    if missing:
        raise ValueError(f"Missing parameter fields: {sorted(missing)}")
    if parameters.empty or parameters[list(REQUIRED)].isna().any().any():
        raise ValueError("Missing mandatory parameter value")
    if parameters.lut_technology.duplicated().any():
        raise ValueError("Duplicate technology parameter row")
    if parameters.capacity_basis.astype(str).str.strip().eq("").any():
        raise ValueError("Missing capacity basis")
    if not parameters.source_reference.astype(str).str.startswith(
        ("http://", "https://")
    ).all():
        raise ValueError("Invalid parameter source reference")
    if not pd.to_numeric(parameters.data_year, errors="raise").map(
        lambda x: math.isfinite(x) and x == int(x)
    ).all():
        raise ValueError("Invalid data year")
    expected = mapping[["lut_technology", "pypsa_component"]]
    if expected.lut_technology.duplicated().any():
        raise ValueError("Duplicate technology mapping")
    joined = parameters.merge(
        expected, on="lut_technology", how="left", validate="one_to_one",
        suffixes=("", "_expected"), indicator=True,
    )
    if not joined._merge.eq("both").all():
        raise ValueError("Parameter technology absent from mapping")
    if not joined.pypsa_component.eq(joined.pypsa_component_expected).all():
        raise ValueError("Component mismatch")
    if set(expected.lut_technology) != set(parameters.lut_technology):
        raise ValueError("Missing mapped technology parameters")
    numeric = {"capacity_mw": (0, None),
               "efficiency": (0, 1),
               "availability_fraction": (0, 1),
               "standing_loss_per_hour": (0, 1),
               "max_hours": (0, None),
               "marginal_cost_eur_per_mwh": (0, None),
               "capital_cost_eur_per_mw_year": (0, None)}
    for field, (lower, upper) in numeric.items():
        if field not in parameters:
            continue
        values = pd.to_numeric(parameters[field], errors="raise")
        if not values.dropna().map(
            lambda x: math.isfinite(x) and x >= lower
            and (upper is None or x <= upper)
        ).all():
            raise ValueError(f"Invalid numeric parameter: {field}")
    if "efficiency_basis" in parameters:
        basis = parameters["efficiency_basis"].dropna()
        if not basis.isin({"per_direction", "round_trip"}).all():
            raise ValueError("Invalid storage efficiency_basis")
    storage_rows = parameters.pypsa_component.eq("StorageUnit")
    if storage_rows.any():
        if "efficiency_basis" not in parameters or parameters.loc[storage_rows, "efficiency_basis"].isna().any():
            raise ValueError("StorageUnit requires efficiency_basis")
    if "efficiency" in parameters:
        values = pd.to_numeric(parameters.efficiency, errors="raise")
        if (values.dropna() <= 0).any():
            raise ValueError("Efficiency must be positive")
    if "max_hours" in parameters:
        storage = parameters.pypsa_component.eq("StorageUnit")
        if parameters.loc[storage, "max_hours"].isna().any():
            raise ValueError("StorageUnit requires max_hours")
        if (pd.to_numeric(parameters.loc[storage, "max_hours"]) <= 0).any():
            raise ValueError("StorageUnit max_hours must be positive")
    if "max_hours" not in parameters and parameters.pypsa_component.eq("StorageUnit").any():
        raise ValueError("StorageUnit requires max_hours")
    # Generator capacity is MW electrical; Store energy capacity is MWh.
    # Do not silently reuse MW as Store e_nom.
    if parameters.pypsa_component.eq("Store").any():
        raise ValueError("Store requires a separate MWh energy-capacity contract")
    return parameters.copy()
