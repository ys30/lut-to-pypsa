import json
import pandas as pd
import pytest

from lut_to_pypsa.input_acceptance import audit_lut_network_inputs, run


def test_authentic_2020_lut_input_acceptance(tmp_path):
    source = "data/derived/lut_continents_2020_verified.csv"
    report, metadata = run(source, tmp_path)
    assert len(report) == 5
    assert set(report.source_cell) == {"C11", "C12", "C13", "C14", "C15"}
    assert report.within_tolerance.all()
    assert metadata["snapshots"] == 8784
    assert metadata["regions"] == 5
    assert metadata["max_abs_error_mwh"] <= 0.01
    assert metadata["optimization_executed"] is False
    assert metadata["lut_estm_output_equivalence"] is False
    assert (tmp_path / "lut_pypsa_input_conservation.csv").exists()
    manifest = json.loads((tmp_path / "lut_pypsa_input_manifest.json").read_text())
    assert manifest["hourly_profile"] == "flat_assumption"


def test_reject_missing_source_cell():
    annual = pd.read_csv("data/derived/lut_continents_2020_verified.csv")
    annual.loc[0, "source_cell"] = ""
    with pytest.raises(ValueError, match="Missing LUT source cell"):
        audit_lut_network_inputs(annual)


def test_reject_non_esd_quantity():
    annual = pd.read_csv("data/derived/lut_continents_2020_verified.csv")
    annual.loc[0, "quantity_kind"] = "generation"
    with pytest.raises(ValueError, match="Unsupported LUT quantity"):
        audit_lut_network_inputs(annual)
