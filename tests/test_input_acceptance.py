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


@pytest.mark.parametrize("mutation,match", [
    (lambda x: x.assign(region=["Africa"] * len(x)), "Duplicate LUT region"),
    (lambda x: x.assign(source_cell=["C11"] * len(x)), "Duplicate LUT source cell"),
    (lambda x: x.assign(value_twh=[float("nan")] * len(x)), "Invalid LUT annual demand"),
    (lambda x: x.assign(value_twh=[float("inf")] * len(x)), "Invalid LUT annual demand"),
    (lambda x: x.assign(value_twh=[-1.] * len(x)), "Invalid LUT annual demand"),
])
def test_reject_ambiguous_or_nonphysical_lut_source(mutation, match):
    annual = pd.read_csv("data/derived/lut_continents_2020_verified.csv")
    with pytest.raises(ValueError, match=match):
        audit_lut_network_inputs(mutation(annual))


def test_report_rejects_missing_hourly_load_after_network_conversion(monkeypatch):
    import lut_to_pypsa.input_acceptance as acceptance
    original = acceptance.build_load_network

    def broken_network(hourly):
        network = original(hourly)
        network.loads_t.p_set.iloc[0, 0] = float("nan")
        return network

    monkeypatch.setattr(acceptance, "build_load_network", broken_network)
    annual = pd.read_csv("data/derived/lut_continents_2020_verified.csv")
    with pytest.raises(ValueError, match="Missing PyPSA hourly load"):
        acceptance.audit_lut_network_inputs(annual)


def test_report_rejects_missing_pypsa_snapshot(monkeypatch):
    import lut_to_pypsa.input_acceptance as acceptance
    original = acceptance.build_load_network

    def truncated_network(hourly):
        network = original(hourly)
        network.set_snapshots(network.snapshots[:-1])
        return network

    monkeypatch.setattr(acceptance, "build_load_network", truncated_network)
    annual = pd.read_csv("data/derived/lut_continents_2020_verified.csv")
    with pytest.raises(ValueError, match="Incomplete or misaligned PyPSA hourly snapshots"):
        acceptance.audit_lut_network_inputs(annual)


@pytest.mark.parametrize("invalid", [-1.0, float("inf")])
def test_report_rejects_nonphysical_pypsa_load(monkeypatch, invalid):
    import lut_to_pypsa.input_acceptance as acceptance
    original = acceptance.build_load_network

    def corrupted_network(hourly):
        network = original(hourly)
        network.loads_t.p_set.iloc[0, 0] = invalid
        return network

    monkeypatch.setattr(acceptance, "build_load_network", corrupted_network)
    annual = pd.read_csv("data/derived/lut_continents_2020_verified.csv")
    with pytest.raises(ValueError, match="Nonfinite or negative PyPSA hourly load"):
        acceptance.audit_lut_network_inputs(annual)
