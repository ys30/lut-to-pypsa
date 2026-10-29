"""Auditable LUT annual scenario comparisons; not a LUT-ESTM model-output comparison."""
from pathlib import Path
import argparse
import json
import pandas as pd

def compare_years(annual, base_year=2020, target_year=2050):
    required={'region','year','value_twh','source_cell','quantity_kind'}
    if not required.issubset(annual):
        raise ValueError('Missing provenance or demand columns')
    if annual.duplicated(['region','year']).any():
        raise ValueError('Duplicate region/year observations')
    if not annual.quantity_kind.eq('annual_energy_service_demand').all():
        raise ValueError('Unexpected source quantity')
    x=annual.loc[annual.year.isin([base_year,target_year])].copy()
    if x.region.isna().any() or x.value_twh.isna().any() or (x.value_twh<0).any():
        raise ValueError('Invalid demand records')
    base=x.loc[x.year==base_year].set_index('region')
    target=x.loc[x.year==target_year].set_index('region')
    if base.empty or set(base.index)!=set(target.index):
        raise ValueError('Incomplete base/target region coverage')
    result=pd.DataFrame({
        'region':sorted(base.index),
        'base_year':base_year,'target_year':target_year,
    }).set_index('region')
    result['base_twh']=base.value_twh
    result['target_twh']=target.value_twh
    result['change_twh']=result.target_twh-result.base_twh
    result['growth_pct']=result.change_twh.div(result.base_twh.where(result.base_twh!=0))*100
    result['base_source_cell']=base.source_cell
    result['target_source_cell']=target.source_cell
    return result.reset_index()

def validate_hourly(annual, hourly, year):
    from .hourly import check_energy_conservation
    selected=annual.loc[annual.year==year,['region','value_twh']]
    timestamps=pd.to_datetime(hourly.timestamp,errors='raise')
    expected=pd.date_range(f'{year}-01-01',f'{year+1}-01-01',freq='h',inclusive='left')
    if len(hourly)!=len(expected)*len(selected):
        raise ValueError('Incorrect number of region-hour records')
    if hourly.duplicated(['timestamp','region']).any():
        raise ValueError('Duplicate region-hour records')
    if set(timestamps.unique())!=set(expected):
        raise ValueError('Missing or out-of-year snapshots')
    if not hourly.p_set_mw.map(lambda v: 0<=v<float('inf')).all():
        raise ValueError('Invalid hourly MW')
    return check_energy_conservation(selected,hourly)

def report(annual_csv,output_dir,base_year=2020,target_year=2050,hourly_csv=None):
    annual=pd.read_csv(annual_csv)
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    comparison=compare_years(annual,base_year,target_year)
    comparison.to_csv(out/'scenario_comparison.csv',index=False)
    metadata={
        'comparison':'LUT-DEMAND annual electricity ESD, same model across years',
        'base_year':base_year,'target_year':target_year,
        'lut_estm_outputs_compared':False,
        'pypsa_optimization_outputs_compared':False,
        'cross_model_validation_status':'not_performed',
        'source_quantity':'annual_energy_service_demand',
        'annual_total_base_twh':float(comparison.base_twh.sum()),
        'annual_total_target_twh':float(comparison.target_twh.sum())
    }
    if hourly_csv:
        hourly=pd.read_csv(hourly_csv)
        checks=validate_hourly(annual,hourly,base_year)
        checks.to_csv(out/'hourly_input_reconciliation.csv',index=False)
        metadata['hourly_input_reconciliation_max_abs_mwh']=float(checks.difference_mwh.abs().max())
    (out/'validation_manifest.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    return comparison,metadata

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('annual_csv')
    p.add_argument('--output',default='outputs/comparison')
    p.add_argument('--base-year',type=int,default=2020)
    p.add_argument('--target-year',type=int,default=2050)
    p.add_argument('--hourly-csv')
    args=p.parse_args()
    comparison,metadata=report(args.annual_csv,args.output,args.base_year,args.target_year,args.hourly_csv)
    print(comparison.to_string(index=False))
    print(metadata)
