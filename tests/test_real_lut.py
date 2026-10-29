from pathlib import Path
import pytest
from lut_to_pypsa.real_lut import extract_continent_demand, export
SOURCE=Path(__file__).resolve().parents[1]/'data'/'external'/'LUT-DEMAND_v1.1.xlsm'
@pytest.mark.skipif(not SOURCE.exists(),reason='Authentic workbook is not committed')
def test_authentic_continents():
    data,checks=extract_continent_demand(SOURCE)
    assert len(data)==35
    assert checks.difference_twh.abs().max()<1e-5
    assert data.loc[(data.region=='Africa')&(data.year==2020),'value_twh'].iloc[0]==pytest.approx(966.335736304755)
@pytest.mark.skipif(not SOURCE.exists(),reason='Authentic workbook is not committed')
def test_export(tmp_path):
    data,_=export(SOURCE,tmp_path)
    assert len(data)==35
    assert (tmp_path/'provenance.json').exists()
