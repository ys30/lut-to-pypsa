import json
import pandas as pd

from lut_to_pypsa.observed_network import run


def test_partial_observed_network_writes_explicit_unsolved_manifest(tmp_path):
    demand = pd.read_csv("data/derived/lut_continents_2020_verified.csv")
    inventory = pd.DataFrame({
        "plant_id": ["p1"], "source_region": ["US"],
        "technology": ["solar"], "capacity_mw": [100.0],
        "data_year": [2020], "source_dataset": ["test_fixture"],
        "source_url": ["https://example.org/test"],
    })
    mapping = pd.DataFrame({
        "source_region": ["US"], "lut_region": ["Americas"]
    })
    demand.to_csv(tmp_path / "demand.csv", index=False)
    inventory.to_csv(tmp_path / "inventory.csv", index=False)
    mapping.to_csv(tmp_path / "mapping.csv", index=False)
    out = tmp_path / "out"
    run(tmp_path / "demand.csv", tmp_path / "inventory.csv",
        tmp_path / "mapping.csv", out, allow_partial=True)
    manifest = json.loads((out / "network_scope_manifest.json").read_text())
    assert manifest["optimization_executed"] is False
    assert manifest["calibrated"] is False
    assert manifest["lut_estm_output_equivalence"] is False
    assert manifest["partial_geography_allowed"] is True
    assert manifest["complete_geographic_coverage_attested"] is False
    assert manifest["modeled_regions"] == ["Americas"]
    assert len(manifest["demand_regions"]) == 5
    assert manifest["mapped_generator_capacity_mw"] == 100.0
    assert manifest["hourly_load_shape"] == "flat_assumption"
