"""Convert annual LUT electricity ESD to hourly PyPSA loads.

Flat hourly shape and ESD-as-bus-load are explicit assumptions, not LUT outputs.
"""
import argparse
from pathlib import Path
import pandas as pd

def hourly_flat(annual, year):
    required={'region','year','value_twh'}
    if not required.issubset(annual.columns):
        raise ValueError('Missing required annual columns')
    selected=annual.loc[annual.year==year,['region','value_twh']]
    if selected.empty or selected.region.isna().any() or selected.region.duplicated().any():
        raise ValueError('Missing year, invalid or duplicate region')
    values=pd.to_numeric(selected.value_twh,errors='raise')
    if not values.map(lambda x: 0<=x<float('inf')).all():
        raise ValueError('Invalid annual energy')
    hours=pd.date_range(f'{year}-01-01',f'{year+1}-01-01',freq='h',inclusive='left')
    out=pd.concat([pd.DataFrame({'timestamp':hours,'region':r,
                                 'p_set_mw':float(twh)*1e6/len(hours)})
                   for r,twh in zip(selected.region,values)],ignore_index=True)
    check_energy_conservation(selected,out)
    return out

def check_energy_conservation(selected,hourly,tolerance_mwh=0.01):
    expected=selected.set_index('region').value_twh*1e6
    actual=hourly.groupby('region').p_set_mw.sum()
    if set(expected.index)!=set(actual.index):
        raise ValueError('Region coverage differs')
    check=pd.DataFrame({'expected_mwh':expected,'hourly_mwh':actual})
    check['difference_mwh']=check.hourly_mwh-check.expected_mwh
    if check.difference_mwh.abs().max()>tolerance_mwh:
        raise ValueError('Annual MWh not conserved')
    return check.reset_index()

def build_load_network(hourly):
    """Load-only network: no generators, lines, optimization or dispatch."""
    import pypsa
    if hourly.duplicated(['timestamp','region']).any():
        raise ValueError('Duplicate region/hour observations')
    wide=hourly.pivot(index='timestamp',columns='region',values='p_set_mw')
    if wide.isna().any().any():
        raise ValueError('Incomplete regional hourly coverage')
    n=pypsa.Network()
    n.set_snapshots(pd.DatetimeIndex(wide.index))
    for region in wide.columns:
        n.add('Bus',str(region),carrier='AC')
        n.add('Load',f'load_{region}',bus=str(region))
    n.loads_t.p_set=wide.rename(columns=lambda r:f'load_{r}').reindex(columns=n.loads.index)
    if hasattr(n,'consistency_check'):
        n.consistency_check()
    return n

def export_hourly(annual_csv,year,output_dir):
    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    annual=pd.read_csv(annual_csv)
    hourly=hourly_flat(annual,year)
    checks=check_energy_conservation(annual.loc[annual.year==year],hourly)
    hourly.to_csv(output_dir/f'pypsa_loads_flat_{year}.csv',index=False)
    checks.to_csv(output_dir/f'annual_energy_check_{year}.csv',index=False)
    return hourly,checks

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('annual_csv')
    p.add_argument('--year',type=int,default=2020)
    p.add_argument('--output',default='outputs/pypsa')
    args=p.parse_args()
    hourly,checks=export_hourly(args.annual_csv,args.year,args.output)
    print('Hourly records:',len(hourly),'Max MWh error:',checks.difference_mwh.abs().max())
