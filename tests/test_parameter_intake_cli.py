"""End-to-end checks for the parameter intake command-line gate."""
import pandas as pd
import pytest

from lut_to_pypsa.parameter_intake_cli import validate_intake


def write_intake(tmp_path, *, evidence_capacity=10.0, status="source_checked"):
    parameters = pd.DataFrame([{
        "lut_technology": "example_solar",
        "pypsa_component": "Generator",
        "capacity_mw": 10.0,
        "capacity_basis": "electrical nameplate MW",
        "source_reference": "https://example.org/illustrative-only",
        "data_year": 2020,
        "availability_fraction": 0.5,
        "marginal_cost_eur_per_mwh": 1.0,
    }])
    mapping = parameters[["lut_technology", "pypsa_component"]].copy()
    evidence = pd.DataFrame([{
        "lut_technology": "example_solar",
        "parameter_name": name,
        "parameter_value": value,
        "unit": unit,
        "source_document": "synthetic test fixture only",
        "source_location": "test fixture",
        "source_year": 2020,
        "geographic_scope": "synthetic",
        "evidence_status": status,
    } for name, value, unit in [
        ("capacity_mw", evidence_capacity, "MW"),
        ("availability_fraction", 0.5, "fraction"),
        ("marginal_cost_eur_per_mwh", 1.0, "EUR/MWh"),
    ]])
    paths = [tmp_path / name for name in ("parameters.csv", "evidence.csv", "mapping.csv")]
    for frame, path in zip((parameters, evidence, mapping), paths):
        frame.to_csv(path, index=False)
    return paths


def test_intake_accepts_complete_self_attested_contract(tmp_path):
    paths = write_intake(tmp_path)
    report = validate_intake(*paths)
    assert report["technologies"] == 1
    assert report["evidence_rows"] == 3
    assert report["status"] == "schema_and_self_attested_evidence_checked"


def test_intake_rejects_mismatched_evidence_value(tmp_path):
    paths = write_intake(tmp_path, evidence_capacity=11.0)
    with pytest.raises(ValueError, match="Evidence value mismatch"):
        validate_intake(*paths)


def test_intake_rejects_non_source_checked_evidence(tmp_path):
    paths = write_intake(tmp_path, status="synthetic_fixture")
    with pytest.raises(ValueError, match="Non-source-checked"):
        validate_intake(*paths)
