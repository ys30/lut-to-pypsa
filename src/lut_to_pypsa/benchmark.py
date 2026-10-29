"""Illustrative, solvable PyPSA benchmark for LUT-derived hourly loads.

NOT a LUT-ESTM replication: dispatchable firm supply and shortage penalty are
explicit assumptions, with no observed generation fleet or interties.
"""
from pathlib import Path
import argparse
import pandas as pd
from .hourly import build_load_network

def add_illustrative_supply(network, reserve_margin=0.10, firm_cost=50., shortage_cost=10000.):
    if reserve_margin < 0 or firm_cost < 0 or shortage_cost <= firm_cost:
        raise ValueError('Invalid reserve margin or costs')
    for load in network.loads.index:
        region=str(network.loads.at[load,'bus'])
        peak=float(network.loads_t.p_set[load].max())
        if not 0 <= peak < float('inf'):
            raise ValueError('Invalid peak demand')
        network.add('Generator',f'firm_{region}',bus=region,p_nom=peak*(1+reserve_margin),
                    marginal_cost=firm_cost,carrier='illustrative_firm')
        network.add('Generator',f'shortage_{region}',bus=region,p_nom=peak,
                    marginal_cost=shortage_cost,carrier='illustrative_shortage')
    return network

def solve_illustrative(hourly,solver_name='highs',reserve_margin=0.10):
    network=add_illustrative_supply(build_load_network(hourly),reserve_margin)
    status,condition=network.optimize(solver_name=solver_name)
    if status!='ok' or condition!='optimal':
        raise RuntimeError(f'Optimization failed: {status} / {condition}')
    generation=network.generators_t.p.sum(axis=0)
    records=[]
    for load in network.loads.index:
        region=str(network.loads.at[load,'bus'])
        expected=float(network.loads_t.p_set[load].sum())
        firm=float(generation[f'firm_{region}'])
        shortage=float(generation[f'shortage_{region}'])
        residual=firm+shortage-expected
        if abs(residual)>max(0.01,expected*1e-8):
            raise RuntimeError('Energy balance mismatch: '+region)
        records.append(dict(region=region,demand_mwh=expected,firm_generation_mwh=firm,
                            unserved_energy_mwh=shortage,balance_residual_mwh=residual,
                            illustrative_firm_capacity_mw=float(network.generators.at[f'firm_{region}','p_nom'])))
    return network,pd.DataFrame(records)

def run(csv,output,solver_name='highs'):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    hourly=pd.read_csv(csv,parse_dates=['timestamp'])
    network,summary=solve_illustrative(hourly,solver_name)
    summary.to_csv(out/'illustrative_dispatch_summary.csv',index=False)
    network.export_to_netcdf(out/'illustrative_solved_network.nc')
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('hourly_csv')
    p.add_argument('--output',default='outputs/illustrative')
    p.add_argument('--solver',default='highs')
    args=p.parse_args()
    print(run(args.hourly_csv,args.output,args.solver).to_string(index=False))
