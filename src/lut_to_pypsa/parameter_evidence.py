"""Audit source-reviewed technology inputs before PyPSA component construction.

A URL or citation string is not independent verification of the numerical value.
This gate rejects synthetic fixtures from being presented as empirical inputs.
"""
import math

import pandas as pd

REQUIRED = {
    "lut_technology", "parameter_name", "parameter_value", "unit",
    "source_document", "source_location", "source_year",
    "geographic_scope", "evidence_status",
}
ALLOWED_STATUS = {"source_checked", "assumption", "synthetic_fixture"}
EXPECTED_UNITS = {
    "capacity_mw": "MW",
    "availability_fraction": "fraction",
    "marginal_cost_eur_per_mwh": "EUR/MWh",
    "capital_cost_eur_per_mw_year": "EUR/MW/year",
    "efficiency": "fraction",
    "max_hours": "hour",
    "standing_loss_per_hour": "fraction/hour",
    "efficiency_basis": "category",
}


def validate_parameter_evidence(evidence, *, require_source_checked=True):
    if not evidence.columns.is_unique:
        raise ValueError("Duplicate evidence column names")
    missing = REQUIRED - set(evidence.columns)
    if missing:
        raise ValueError(f"Missing evidence columns: {sorted(missing)}")
    if evidence.empty or evidence[list(REQUIRED)].isna().any().any():
        raise ValueError("Missing technology parameter evidence")
    for column in REQUIRED - {"parameter_value", "source_year"}:
        if evidence[column].astype(str).str.strip().eq("").any():
            raise ValueError(f"Blank evidence field: {column}")
    if evidence.duplicated(["lut_technology", "parameter_name"]).any():
        raise ValueError("Duplicate parameter evidence")
    invalid = set(evidence.evidence_status) - ALLOWED_STATUS
    if invalid:
        raise ValueError(f"Unknown evidence status: {sorted(invalid)}")
    for row in evidence.itertuples(index=False):
        expected_unit = EXPECTED_UNITS.get(row.parameter_name)
        if expected_unit is not None and row.unit != expected_unit:
            raise ValueError(f"Incorrect unit for {row.parameter_name}: expected {expected_unit}")
    if require_source_checked and not evidence.evidence_status.eq("source_checked").all():
        raise ValueError("Non-source-checked parameters cannot enter empirical adapter")
    basis = evidence.loc[evidence.parameter_name.eq("efficiency_basis"), "parameter_value"]
    if not basis.isin({"per_direction", "round_trip"}).all():
        raise ValueError("Invalid storage efficiency basis evidence")
    numeric_evidence = evidence.loc[~evidence.parameter_name.eq("efficiency_basis")]
    values = pd.to_numeric(numeric_evidence.parameter_value, errors="coerce")
    if values.isna().any() or not values.map(lambda x: math.isfinite(x)).all():
        raise ValueError("Nonfinite parameter evidence")
    years = pd.to_numeric(evidence.source_year, errors="coerce")
    if years.isna().any() or not years.map(
        lambda x: math.isfinite(x) and x == int(x)
    ).all():
        raise ValueError("Invalid evidence year")
    return evidence.copy()


def check_parameter_evidence_coverage(parameters, evidence):
    validated = validate_parameter_evidence(evidence)
    names = {
        "capacity_mw", "availability_fraction", "marginal_cost_eur_per_mwh",
        "efficiency", "max_hours", "standing_loss_per_hour",
        "capital_cost_eur_per_mw_year", "efficiency_basis",
    }
    needed = set()
    for row in parameters.to_dict("records"):
        for name in names:
            if name in row and pd.notna(row[name]):
                needed.add((row["lut_technology"], name))
    present = set(zip(validated.lut_technology, validated.parameter_name))
    if needed - present:
        raise ValueError(f"Missing source-checked parameter evidence: {sorted(needed - present)}")
    unexpected = present - needed
    if unexpected:
        raise ValueError(f"Unexpected parameter evidence: {sorted(unexpected)}")
    for row in validated.to_dict("records"):
        key = (row["lut_technology"], row["parameter_name"])
        if key in needed:
            supplied = parameters.loc[parameters.lut_technology.eq(row["lut_technology"]), row["parameter_name"]].iloc[0]
            if (str(supplied) != str(row["parameter_value"]) if row["parameter_name"] == "efficiency_basis"
                    else float(supplied) != float(row["parameter_value"])):
                raise ValueError(f"Evidence value mismatch: {key}")
    return True
