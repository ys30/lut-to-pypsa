"""Explicit, conservative LUT technology -> PyPSA component mapping contract.

Mappings are researcher-reviewed configuration, never inferred from labels.
No dispatch parameters or empirical equivalence are asserted.
"""
import pandas as pd

REQUIRED = {"lut_technology", "pypsa_component", "pypsa_carrier",
            "mapping_basis", "source_reference"}
SUPPORTED = {"Generator", "StorageUnit", "Store", "Link"}


def validate_technology_mapping(mapping, required_technologies):
    missing = REQUIRED - set(mapping.columns)
    if missing:
        raise ValueError(f"Missing technology mapping columns: {sorted(missing)}")
    if mapping.empty or mapping[list(REQUIRED)].isna().any().any():
        raise ValueError("Technology mapping must be complete and nonempty")
    for col in REQUIRED:
        if mapping[col].astype(str).str.strip().eq("").any():
            raise ValueError(f"Blank technology mapping field: {col}")
    if mapping.lut_technology.duplicated().any():
        raise ValueError("Duplicate LUT technology mapping")
    invalid = set(mapping.pypsa_component) - SUPPORTED
    if invalid:
        raise ValueError(f"Unsupported PyPSA component: {sorted(invalid)}")
    required = set(required_technologies)
    present = set(mapping.lut_technology)
    if required - present:
        raise ValueError(f"Unmapped LUT technologies: {sorted(required - present)}")
    # A carrier is a classification, not proof of a technology's operating model.
    return mapping.loc[mapping.lut_technology.isin(required)].copy()


def audit_inventory_technology_mapping(inventory, mapping):
    if "technology" not in inventory.columns:
        raise ValueError("Inventory requires technology")
    selected = validate_technology_mapping(mapping, inventory.technology.unique())
    if "capacity_mw" not in inventory.columns:
        raise ValueError("Inventory requires capacity_mw")
    joined = inventory.merge(selected, left_on="technology",
                             right_on="lut_technology", validate="many_to_one")
    return (joined.groupby(["lut_technology", "pypsa_component", "pypsa_carrier",
                            "mapping_basis", "source_reference"], as_index=False)
            .agg(plant_count=("technology", "size"),
                 mapped_capacity_mw=("capacity_mw", "sum")))
