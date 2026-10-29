import pandas as pd
import pytest
from lut_to_pypsa.benchmark import add_illustrative_supply, solve_illustrative
from lut_to_pypsa.hourly import build_load_network

@pytest.mark.parametrize('margin',[-0.1])
def test_invalid_margin(margin):
    pytest.importorskip('pypsa')
    hourly=pd.DataFrame({'timestamp':pd.date_range('2025-01-01',periods=2,freq='h'),
                         'region':['Africa']*2,'p_set_mw':[10.,10.]})
    with pytest.raises(ValueError):
        add_illustrative_supply(build_load_network(hourly),reserve_margin=margin)

def test_small_solved_dispatch():
    pytest.importorskip('pypsa')
    pytest.importorskip('highspy')
    hourly=pd.DataFrame({'timestamp':pd.date_range('2025-01-01',periods=3,freq='h'),
                         'region':['Africa']*3,'p_set_mw':[10.,12.,11.]})
    n,summary=solve_illustrative(hourly)
    assert summary.demand_mwh.iloc[0]==pytest.approx(33)
    assert summary.unserved_energy_mwh.iloc[0]==pytest.approx(0,abs=1e-5)
    assert summary.balance_residual_mwh.iloc[0]==pytest.approx(0,abs=1e-5)
    assert len(n.generators)==2
