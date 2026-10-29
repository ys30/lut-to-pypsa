import pandas as pd
import pytest
from lut_to_pypsa.pipeline import load_tables, harmonize
from lut_to_pypsa.validation import validate_inputs, InputValidationError

@pytest.fixture
def tables():
    return load_tables("data/synthetic")

def test_synthetic_schema(tables):
    report = validate_inputs(*tables)
    assert report == {"regions": 3, "generators": 6, "snapshots": 24, "demand_rows": 72}

def test_units_gwh_to_mw(tables):
    _, _, demand, _ = harmonize(*tables)
    assert (demand.p_set_mw == demand.demand_gwh * 1000).all()

def test_unknown_region_rejected(tables):
    r,g,d = tables
    g = g.copy(); g.loc[0, "region"] = "unknown"
    with pytest.raises(InputValidationError, match="unknown region"):
        validate_inputs(r,g,d)

def test_duplicate_demand_rejected(tables):
    r,g,d = tables
    d = pd.concat([d,d.iloc[[0]]],ignore_index=True)
    with pytest.raises(InputValidationError, match="Duplicate"):
        validate_inputs(r,g,d)

def test_missing_region_snapshot_rejected(tables):
    r,g,d = tables
    with pytest.raises(InputValidationError, match="Incomplete"):
        validate_inputs(r,g,d.iloc[1:])

def test_network_inputs(tables):
    pytest.importorskip("pypsa")
    from lut_to_pypsa.pipeline import build_network
    n, _ = build_network(*tables)
    assert len(n.buses) == 3
    assert len(n.generators) == 6
    assert len(n.snapshots) == 24
    assert n.loads_t.p_set.shape == (24,3)
    assert n.loads_t.p_set.notna().all().all()
    # generators_t.p is a solution output, not required before optimization.
