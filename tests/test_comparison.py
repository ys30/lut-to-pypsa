import pandas as pd
import pytest
from lut_to_pypsa.comparison import compare_years,validate_hourly
from lut_to_pypsa.hourly import hourly_flat

def sample():
    return pd.DataFrame({'region':['A','B','A','B'],'year':[2020,2020,2050,2050],
        'value_twh':[1.,2.,3.,4.],'source_cell':['C11','C12','I11','I12'],
        'quantity_kind':['annual_energy_service_demand']*4})

def test_compare():
    result=compare_years(sample())
    assert result.change_twh.sum()==pytest.approx(4)
    assert result.loc[result.region=='A','growth_pct'].iloc[0]==pytest.approx(200)

def test_incomplete_regions_rejected():
    with pytest.raises(ValueError,match='coverage'):
        compare_years(sample().iloc[:-1])

def test_hourly_2020_reconciliation():
    annual=sample()
    hourly=hourly_flat(annual,2020)
    checks=validate_hourly(annual,hourly,2020)
    assert checks.difference_mwh.abs().max()<1e-6

def test_missing_hour_rejected():
    annual=sample()
    hourly=hourly_flat(annual,2020).iloc[:-1]
    with pytest.raises(ValueError,match='number'):
        validate_hourly(annual,hourly,2020)
