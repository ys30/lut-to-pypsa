"""Fixed-baseline-capacity PyPSA stress test for authentic LUT demand.

All scenarios share exactly the same firm capacities derived from baseline
2020 demand. Shortage generators are feasibility slack, NOT real resources.
No real generator fleet, transmission, or hourly load shape is claimed.
"""
import argparse
from pathlib import Path

import pandas as pd

from .hourly import build_load_network
from .scenarios import scale_annual_demand


def compare_fixed_capacity(annual, multipliers=None, hours=24,
                           reserve_margin=0.10, solver_name="highs"):
    if not isinstance(hours, int) or not 1 <= hours <= 8784:
        raise ValueError("hours must be an integer between 1 and 8784")
    if annual.empty or annual.year.nunique() != 1 or int(annual.year.iloc[0]) != 2020:
        raise ValueError("Only 2020 annual demand is supported")
    if not 0 <= reserve_margin < 10:
        raise ValueError("Invalid reserve margin")
    scaled = scale_annual_demand(
        annual, multipliers if multipliers is not None
        else {"low_demand": 0.9, "high_demand": 1.1}
    )
    baseline = scaled[scaled.scenario == "baseline"]
    capacity = dict(zip(baseline.region,
                        baseline.scenario_demand_twh * 1e6 / 8784 * (1 + reserve_margin)))
    snapshots = pd.date_range("2020-01-01", periods=hours, freq="h")
    records = []
    for scenario, part in scaled.groupby("scenario", sort=False):
        hourly = pd.concat([
            pd.DataFrame({"timestamp": snapshots, "region": row.region,
                          "p_set_mw": float(row.scenario_demand_twh) * 1e6 / 8784})
            for row in part.itertuples(index=False)
        ], ignore_index=True)
        network = build_load_network(hourly)
        for region in capacity:
            network.add("Generator", f"firm_{region}", bus=region,
                        p_nom=float(capacity[region]), marginal_cost=50.0)
            # Sized to scenario peak only to ensure feasible optimization.
            # This generator represents unserved demand at a penalty.
            peak = float(hourly.loc[hourly.region == region, "p_set_mw"].max())
            network.add("Generator", f"shortage_{region}", bus=region,
                        p_nom=peak, marginal_cost=10000.0)
        status, condition = network.optimize(solver_name=solver_name)
        if status != "ok" or condition != "optimal":
            raise RuntimeError(f"Optimization failed: {scenario}: {status}/{condition}")
        dispatch = network.generators_t.p
        for row in part.itertuples(index=False):
            region = row.region
            demand = float(network.loads_t.p_set[f"load_{region}"].sum())
            firm = float(dispatch[f"firm_{region}"].sum())
            shortage = float(dispatch[f"shortage_{region}"].sum())
            residual = firm + shortage - demand
            if abs(residual) > max(0.01, demand * 1e-8):
                raise RuntimeError(f"Balance mismatch: {scenario}/{region}")
            records.append({
                "scenario": scenario, "region": region, "hours": hours,
                "assumed_multiplier": float(row.assumed_multiplier),
                "baseline_firm_capacity_mw": float(capacity[region]),
                "demand_mwh": demand, "firm_generation_mwh": firm,
                "unserved_energy_mwh": shortage,
                "unserved_share": shortage / demand if demand else 0.0,
                "balance_residual_mwh": residual,
                "illustrative_dispatch_cost": firm * 50 + shortage * 10000,
            })
    return pd.DataFrame(records)


def run(input_csv, output_dir, hours=24):
    results = compare_fixed_capacity(pd.read_csv(input_csv), hours=hours)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    results.to_csv(out / "fixed_capacity_scenario_dispatch.csv", index=False)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv")
    parser.add_argument("--output", default="outputs/fixed_capacity")
    parser.add_argument("--hours", type=int, default=24)
    args = parser.parse_args()
    print(run(args.input_csv, args.output, args.hours).to_string(index=False))
