import pandas as pd
import pytest

from lut_to_pypsa.parameter_evidence import (
    validate_parameter_evidence, check_parameter_evidence_coverage,
)


def fixtures():
    parameters = pd.DataFrame({
        "lut_technology": ["solar"],
        "capacity_mw": [100.],
        "availability_fraction": [.3],
    })
    evidence = pd.DataFrame({
        "lut_technology": ["solar", "solar"],
        "parameter_name": ["capacity_mw", "availability_fraction"],
        "parameter_value": [100., .3],
        "unit": ["MW", "fraction"],
        "source_document": ["example_document", "example_document"],
        "source_location": ["table 1", "table 2"],
        "source_year": [2020, 2020],
        "geographic_scope": ["example", "example"],
        "evidence_status": ["source_checked", "source_checked"],
    })
    return parameters, evidence


def test_complete_source_checked_evidence_contract():
    parameters, evidence = fixtures()
    assert check_parameter_evidence_coverage(parameters, evidence)


def test_reject_synthetic_evidence_for_empirical_inputs():
    _, evidence = fixtures()
    evidence.loc[0, "evidence_status"] = "synthetic_fixture"
    with pytest.raises(ValueError, match="Non-source-checked"):
        validate_parameter_evidence(evidence)


def test_reject_missing_parameter_provenance():
    parameters, evidence = fixtures()
    with pytest.raises(ValueError, match="Missing source-checked"):
        check_parameter_evidence_coverage(parameters, evidence.iloc[:1])


def test_reject_evidence_value_mismatch():
    parameters, evidence = fixtures()
    evidence.loc[0, "parameter_value"] = 101.
    with pytest.raises(ValueError, match="Evidence value mismatch"):
        check_parameter_evidence_coverage(parameters, evidence)


def test_reject_duplicate_evidence():
    _, evidence = fixtures()
    with pytest.raises(ValueError, match="Duplicate parameter evidence"):
        validate_parameter_evidence(pd.concat([evidence, evidence.iloc[:1]]))


def test_reject_evidence_for_unrequested_parameter():
    parameters, evidence = fixtures()
    extra = evidence.iloc[:1].copy()
    extra.loc[:, "parameter_name"] = "unrequested_cost"
    with pytest.raises(ValueError, match="Unexpected parameter evidence"):
        check_parameter_evidence_coverage(
            parameters, pd.concat([evidence, extra], ignore_index=True)
        )


def test_reject_nonfinite_evidence_value():
    _, evidence = fixtures()
    evidence.loc[0, "parameter_value"] = float("inf")
    with pytest.raises(ValueError, match="Nonfinite parameter evidence"):
        validate_parameter_evidence(evidence)


def test_reject_wrong_physical_unit():
    _, evidence = fixtures()
    evidence.loc[0, "unit"] = "MWh"
    with pytest.raises(ValueError, match="Incorrect unit"):
        validate_parameter_evidence(evidence)


def test_annualized_capital_cost_requires_source_evidence():
    parameters, evidence = fixtures()
    parameters["capital_cost_eur_per_mw_year"] = [150.]
    with pytest.raises(ValueError, match="Missing source-checked parameter evidence"):
        check_parameter_evidence_coverage(parameters, evidence)


def test_annualized_capital_cost_with_matching_evidence():
    parameters, evidence = fixtures()
    parameters["capital_cost_eur_per_mw_year"] = [150.]
    extra = evidence.iloc[:1].copy()
    extra.loc[:, "parameter_name"] = "capital_cost_eur_per_mw_year"
    extra.loc[:, "parameter_value"] = 150.
    extra.loc[:, "unit"] = "EUR/MW/year"
    assert check_parameter_evidence_coverage(
        parameters, pd.concat([evidence, extra], ignore_index=True)
    )


def test_reject_duplicate_evidence_column_labels():
    _, evidence = fixtures()
    evidence.columns = list(evidence.columns[:-1]) + ["parameter_name"]
    with pytest.raises(ValueError, match="Duplicate evidence column names"):
        validate_parameter_evidence(evidence)


def test_reject_unrecognized_evidence_parameter():
    _, evidence = fixtures()
    evidence.loc[0, "parameter_name"] = "unrecognized_parameter"
    with pytest.raises(ValueError, match="Unknown parameter evidence name"):
        validate_parameter_evidence(evidence)
