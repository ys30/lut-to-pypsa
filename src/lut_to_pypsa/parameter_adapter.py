"""Conservative PyPSA adapter for reviewed generator and storage parameters.

This constructs components only; it does not run optimization or claim LUT equivalence.
"""
import math

import pandas as pd

from .technology_parameters import validate_technology_parameters
from .parameter_evidence import check_parameter_evidence_coverage


def attach_reviewed_components(network, parameters, mapping, bus_by_technology, *, evidence=None, empirical=False):
    """Return a copy of network with explicitly parameterized Generator/StorageUnit.

    When evidence is supplied, every used parameter must match source-checked evidence.
    Set empirical=True to reject missing evidence. Without evidence, this is a
    fixture/illustrative adapter, not an empirical result.
    A scalar availability is a constant illustrative ceiling, not a weather profile.
    Costs are in EUR/MWh and EUR/MW-year; no currency conversion is inferred.
    """
    validated = validate_technology_parameters(parameters, mapping)
    if empirical and evidence is None:
        raise ValueError('Empirical mode requires source-checked parameter evidence')
    if evidence is not None:
        check_parameter_evidence_coverage(validated, evidence)
    if set(validated.lut_technology) != set(bus_by_technology):
        raise ValueError("Each mapped technology requires exactly one explicit bus")
    result = network.copy()
    proposed_names = {"lut_" + str(name) for name in validated.lut_technology}
    existing_names = set(result.generators.index) | set(result.storage_units.index)
    collisions = proposed_names & existing_names
    if collisions:
        raise ValueError(f"Existing PyPSA component name collision: {sorted(collisions)}")
    for row in validated.to_dict("records"):
        technology = row["lut_technology"]
        bus = bus_by_technology[technology]
        if bus not in result.buses.index:
            raise ValueError(f"Unknown PyPSA bus for {technology}: {bus}")
        component = row["pypsa_component"]
        if component not in {"Generator", "StorageUnit"}:
            raise ValueError(f"{component} requires a separate physical adapter")
        if "marginal_cost_eur_per_mwh" not in row or pd.isna(row["marginal_cost_eur_per_mwh"]):
            raise ValueError(f"Missing marginal cost for {technology}")
        if "availability_fraction" not in row or pd.isna(row["availability_fraction"]):
            raise ValueError(f"Missing availability for {technology}")
        if "capital_cost_eur_per_mw_year" in row and pd.notna(row["capital_cost_eur_per_mw_year"]):
            raise ValueError("Annualized investment cost cannot be attached without an explicit optimization-period convention")
        attrs = {
            "bus": bus,
            "p_nom": float(row["capacity_mw"]),
            "carrier": technology,
            "marginal_cost": float(row["marginal_cost_eur_per_mwh"]),
        }
        if component == "Generator":
            attrs["p_max_pu"] = float(row["availability_fraction"])
        else:
            if "efficiency" not in row or pd.isna(row["efficiency"]):
                raise ValueError("StorageUnit requires reviewed efficiency")
            if "standing_loss_per_hour" not in row or pd.isna(row["standing_loss_per_hour"]):
                raise ValueError("StorageUnit requires reviewed standing loss")
            # Symmetric charge/discharge efficiencies are an explicit modeling
            # assumption. Round-trip input is square-rooted for each direction.
            if "efficiency_basis" not in row or pd.isna(row["efficiency_basis"]):
                raise ValueError("StorageUnit requires explicit efficiency_basis")
            basis = row["efficiency_basis"]
            if basis not in {"per_direction", "round_trip"}:
                raise ValueError("Unsupported storage efficiency_basis")
            stated_efficiency = float(row["efficiency"])
            per_direction_efficiency = (math.sqrt(stated_efficiency)
                                        if basis == "round_trip" else stated_efficiency)
            attrs.update({
                "max_hours": float(row["max_hours"]),
                "efficiency_store": per_direction_efficiency,
                "efficiency_dispatch": per_direction_efficiency,
                "standing_loss": float(row["standing_loss_per_hour"]),
                "p_max_pu": float(row["availability_fraction"]),
            })
        result.add(component, f"lut_{technology}", **attrs)
    return result
