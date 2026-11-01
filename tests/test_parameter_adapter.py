import pandas as pd
import pytest

from lut_to_pypsa.parameter_adapter import attach_reviewed_components
from lut_to_pypsa.parameter_evidence import EXPECTED_UNITS


def fixture():
    import pypsa
    network = pypsa.Network()
    network.set_snapshots(pd.date_range("2020-01-01", periods=2, freq="h"))
    network.add("Bus", "region_a")
    mapping = pd.DataFrame({
        "lut_technology": ["solar", "battery"],
        "pypsa_component": ["Generator", "StorageUnit"],
    })
    parameters = pd.DataFrame({
        "lut_technology": ["solar", "battery"],
        "pypsa_component": ["Generator", "StorageUnit"],
        "capacity_mw": [100., 20.],
        "capacity_basis": ["electrical_nameplate", "power_rating"],
        "source_reference": ["https://example.org/a", "https://example.org/b"],
        "data_year": [2020, 2020],
        "marginal_cost_eur_per_mwh": [1., 2.],
        "availability_fraction": [.25, 1.],
        "efficiency": [1., .9],
        "efficiency_basis": ["per_direction", "per_direction"],
        "standing_loss_per_hour": [0., .01],
        "max_hours": [float("nan"), 4.],
    })
    return network, mapping, parameters


def test_reviewed_generator_and_storage_are_attached_without_solve():
    network, mapping, parameters = fixture()
    result = attach_reviewed_components(
        network, parameters, mapping, {"solar": "region_a", "battery": "region_a"})
    assert result.generators.loc["lut_solar", "p_nom"] == pytest.approx(100.)
    assert result.generators.loc["lut_solar", "p_max_pu"] == pytest.approx(.25)
    assert result.storage_units.loc["lut_battery", "max_hours"] == pytest.approx(4.)
    assert result.storage_units.loc["lut_battery", "efficiency_store"] == pytest.approx(.9)
    assert result.storage_units.loc["lut_battery", "standing_loss"] == pytest.approx(.01)
    assert network.generators.empty
    assert network.storage_units.empty


def test_reject_unknown_bus():
    network, mapping, parameters = fixture()
    with pytest.raises(ValueError, match="Unknown PyPSA bus"):
        attach_reviewed_components(
            network, parameters, mapping, {"solar": "unknown", "battery": "region_a"})


def test_reject_missing_operating_cost():
    network, mapping, parameters = fixture()
    parameters.loc[0, "marginal_cost_eur_per_mwh"] = float("nan")
    with pytest.raises(ValueError, match="Missing marginal cost"):
        attach_reviewed_components(
            network, parameters, mapping, {"solar": "region_a", "battery": "region_a"})


def test_reject_unconventioned_capital_cost():
    network, mapping, parameters = fixture()
    parameters["capital_cost_eur_per_mw_year"] = [100., 100.]
    with pytest.raises(ValueError, match="optimization-period convention"):
        attach_reviewed_components(
            network, parameters, mapping, {"solar": "region_a", "battery": "region_a"})


def test_empirical_evidence_gate_rejects_unchecked_values():
    network, mapping, parameters = fixture()
    rows = []
    for item in parameters.to_dict("records"):
        for name in ("capacity_mw", "marginal_cost_eur_per_mwh",
                     "availability_fraction", "efficiency",
                     "standing_loss_per_hour", "max_hours", "efficiency_basis"):
            if pd.notna(item[name]):
                rows.append({
                    "lut_technology": item["lut_technology"],
                    "parameter_name": name,
                    "parameter_value": item[name],
                    "unit": EXPECTED_UNITS[name],
                    "source_document": "fixture_only",
                    "source_location": "test",
                    "source_year": 2020,
                    "geographic_scope": "test",
                    "evidence_status": "synthetic_fixture",
                })
    evidence = pd.DataFrame(rows)
    with pytest.raises(ValueError, match="Non-source-checked"):
        attach_reviewed_components(
            network, parameters, mapping,
            {"solar": "region_a", "battery": "region_a"},
            evidence=evidence,
        )


def test_empirical_evidence_gate_rejects_value_mismatch():
    network, mapping, parameters = fixture()
    rows = []
    for item in parameters.to_dict("records"):
        for name in ("capacity_mw", "marginal_cost_eur_per_mwh",
                     "availability_fraction", "efficiency",
                     "standing_loss_per_hour", "max_hours", "efficiency_basis"):
            if pd.notna(item[name]):
                rows.append({
                    "lut_technology": item["lut_technology"],
                    "parameter_name": name,
                    "parameter_value": item[name],
                    "unit": EXPECTED_UNITS[name],
                    "source_document": "fixture_only",
                    "source_location": "test",
                    "source_year": 2020,
                    "geographic_scope": "test",
                    "evidence_status": "source_checked",
                })
    evidence = pd.DataFrame(rows)
    evidence.loc[evidence.parameter_name.eq("capacity_mw"), "parameter_value"] += 1.
    with pytest.raises(ValueError, match="Evidence value mismatch"):
        attach_reviewed_components(
            network, parameters, mapping,
            {"solar": "region_a", "battery": "region_a"},
            evidence=evidence,
        )


def test_empirical_mode_requires_evidence():
    network, mapping, parameters = fixture()
    with pytest.raises(ValueError, match="Empirical mode requires"):
        attach_reviewed_components(
            network, parameters, mapping,
            {"solar": "region_a", "battery": "region_a"},
            empirical=True,
        )


def test_empirical_mode_accepts_complete_attested_evidence():
    network, mapping, parameters = fixture()
    rows = []
    for item in parameters.to_dict("records"):
        for name in ("capacity_mw", "marginal_cost_eur_per_mwh",
                     "availability_fraction", "efficiency",
                     "standing_loss_per_hour", "max_hours", "efficiency_basis"):
            if pd.notna(item[name]):
                rows.append({
                    "lut_technology": item["lut_technology"],
                    "parameter_name": name,
                    "parameter_value": item[name],
                    "unit": EXPECTED_UNITS[name],
                    "source_document": "synthetic_test_document",
                    "source_location": "test fixture",
                    "source_year": 2020,
                    "geographic_scope": "synthetic_test",
                    "evidence_status": "source_checked",
                })
    result = attach_reviewed_components(
        network, parameters, mapping,
        {"solar": "region_a", "battery": "region_a"},
        evidence=pd.DataFrame(rows), empirical=True,
    )
    assert "lut_solar" in result.generators.index
    assert "lut_battery" in result.storage_units.index


def test_storage_efficiency_is_per_direction_not_round_trip():
    network, mapping, parameters = fixture()
    result = attach_reviewed_components(
        network, parameters, mapping, {"solar": "region_a", "battery": "region_a"}
    )
    storage = result.storage_units.loc["lut_battery"]
    assert storage.efficiency_store == pytest.approx(.9)
    assert storage.efficiency_dispatch == pytest.approx(.9)
    assert storage.efficiency_store * storage.efficiency_dispatch == pytest.approx(.81)


def test_storage_round_trip_basis_is_converted_to_symmetric_efficiencies():
    network, mapping, parameters = fixture()
    parameters.loc[parameters.lut_technology.eq("battery"), "efficiency_basis"] = "round_trip"
    result = attach_reviewed_components(
        network, parameters, mapping, {"solar": "region_a", "battery": "region_a"}
    )
    storage = result.storage_units.loc["lut_battery"]
    assert storage.efficiency_store * storage.efficiency_dispatch == pytest.approx(.9)


def test_storage_rejects_missing_efficiency_basis():
    network, mapping, parameters = fixture()
    parameters = parameters.drop(columns="efficiency_basis")
    with pytest.raises(ValueError, match="efficiency_basis"):
        attach_reviewed_components(
            network, parameters, mapping, {"solar": "region_a", "battery": "region_a"}
        )


def test_storage_rejects_unknown_efficiency_basis():
    network, mapping, parameters = fixture()
    parameters.loc[parameters.lut_technology.eq("battery"), "efficiency_basis"] = "unspecified"
    with pytest.raises(ValueError, match="efficiency_basis"):
        attach_reviewed_components(
            network, parameters, mapping, {"solar": "region_a", "battery": "region_a"}
        )


def test_adapter_rejects_existing_component_name_collision():
    network, mapping, parameters = fixture()
    network.add("Generator", "lut_solar", bus="region_a", p_nom=1.0)
    with pytest.raises(ValueError, match="component name collision"):
        attach_reviewed_components(
            network, parameters, mapping,
            {"solar": "region_a", "battery": "region_a"},
        )
    assert network.generators.loc["lut_solar", "p_nom"] == pytest.approx(1.0)
    assert network.storage_units.empty


def test_adapter_rejects_network_without_snapshots(monkeypatch):
    network, mapping, parameters = fixture()
    # PyPSA refuses empty snapshots through its public setter. Patch the
    # public property on this network's class to test our defensive guard.
    monkeypatch.setattr(
        type(network), "snapshots",
        property(lambda self: pd.DatetimeIndex([])),
    )
    with pytest.raises(ValueError, match="requires network snapshots"):
        attach_reviewed_components(
            network, parameters, mapping,
            {"solar": "region_a", "battery": "region_a"},
        )

def test_adapter_rejects_cross_component_name_collision():
    network, mapping, parameters = fixture()
    network.add("Load", "lut_solar", bus="region_a", p_set=1.0)
    with pytest.raises(ValueError, match="component name collision"):
        attach_reviewed_components(
            network, parameters, mapping,
            {"solar": "region_a", "battery": "region_a"},
        )
    assert network.generators.empty
    assert network.storage_units.empty


@pytest.mark.parametrize("invalid_mapping", [None, [], {"solar": "", "battery": "region_a"}, {"solar": None, "battery": "region_a"}])
def test_adapter_rejects_invalid_bus_mapping(invalid_mapping):
    network, mapping, parameters = fixture()
    with pytest.raises(ValueError, match="Bus mapping"):
        attach_reviewed_components(network, parameters, mapping, invalid_mapping)
