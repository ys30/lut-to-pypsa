"""Closed-form reference for the flat-load, disconnected-bus benchmark.

Independent of PyPSA. Valid only for two dispatchable generators per bus:
firm at cost 50, shortage proxy at cost 10000, no transmission or storage.
"""
import argparse
from pathlib import Path
import pandas as pd

def expected_dispatch(annual_csv, *, year=2020, reserve_margin=0.10,
                      firm_capacity_factor=1.0):
    if not (0 <= reserve_margin < float("inf")
            and 0 <= firm_capacity_factor <= 1):
        raise ValueError("Invalid scenario parameters")
    annual = pd.read_csv(annual_csv)
    annual = annual.loc[annual.year.eq(year), ["region", "value_twh"]].copy()
    if annual.empty or annual.region.isna().any() or annual.region.duplicated().any():
        raise ValueError("Invalid annual regions")
    hours = len(pd.date_range(f"{year}-01-01", f"{year+1}-01-01",
                              freq="h", inclusive="left"))
    demand = pd.to_numeric(annual.value_twh, errors="raise") * 1e6
    if demand.isna().any() or (demand < 0).any() or not (demand < float("inf")).all():
        raise ValueError("Invalid demand")
    firm_fraction = min(1.0, (1 + reserve_margin) * firm_capacity_factor)
    firm = demand * firm_fraction
    shortage = demand - firm
    return pd.DataFrame({
        "region": annual.region.to_numpy(),
        "demand_mwh": demand.to_numpy(),
        "firm_generation_mwh": firm.to_numpy(),
        "shortage_generation_mwh": shortage.to_numpy(),
        "shortage_fraction": (shortage / demand.where(demand.ne(0))).fillna(0).to_numpy(),
        "illustrative_dispatch_cost": (firm * 50 + shortage * 10000).to_numpy(),
        "assumed_reserve_margin": reserve_margin,
        "assumed_firm_capacity_factor": firm_capacity_factor,
        "source": "closed_form_analytical_expectation_not_solver_output",
    })

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--annual", type=Path, default=Path("data/derived/lut_continents_2020_verified.csv"))
    parser.add_argument("--output", type=Path, default=Path("outputs/five_region/analytical_sensitivity.csv"))
    parser.add_argument("--factors", type=float, nargs="+", default=[1.0, 0.75, 0.5, 0.25])
    args = parser.parse_args()
    results = pd.concat([expected_dispatch(args.annual, firm_capacity_factor=f)
                         for f in args.factors], ignore_index=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.output, index=False)
    print(results.to_string(index=False))

if __name__ == "__main__":
    main()
