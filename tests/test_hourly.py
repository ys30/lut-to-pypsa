import pandas as pd
import pytest
from lut_to_pypsa.hourly import hourly_flat,check_energy_conservation,build_load_network

def test_leap_year_and_conservation():
    annual=pd.DataFrame({'region':['Africa','Europe'],'year':[2020,2020],'value_twh':[1.,2.]})
    hourly=hourly_flat(annual,2020)
    assert len(hourly)==17568
    assert hourly.p_set_mw.iloc[0]==pytest.approx(1e6/8784)
    assert check_energy_conservation(annual,hourly).difference_mwh.abs().max()<1e-6

def test_regular_year():
    annual=pd.DataFrame({'region':['Asia'],'year':[2025],'value_twh':[3.]})
    assert len(hourly_flat(annual,2025))==8760

def test_duplicate_region_rejected():
    annual=pd.DataFrame({'region':['Asia','Asia'],'year':[2025,2025],'value_twh':[3.,4.]})
    with pytest.raises(ValueError,match='duplicate'):
        hourly_flat(annual,2025)

def test_incomplete_hour_rejected():
    pytest.importorskip('pypsa')
    hourly=pd.DataFrame({'timestamp':pd.to_datetime(['2025-01-01','2025-01-01','2025-01-02']),
        'region':['Africa','Europe','Africa'],'p_set_mw':[1.,2.,3.]})
    with pytest.raises(ValueError,match='Incomplete'):
        build_load_network(hourly)

def test_pypsa_network():
    pytest.importorskip('pypsa')
    annual=pd.DataFrame({'region':['Africa','Europe'],'year':[2025,2025],'value_twh':[1.,2.]})
    n=build_load_network(hourly_flat(annual,2025))
    assert len(n.loads)==2
    assert len(n.snapshots)==8760
    assert n.loads_t.p_set.to_numpy().sum()==pytest.approx(3e6)
