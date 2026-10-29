"""Run illustrative PyPSA dispatch for source-traced demand sensitivity scenarios.

Annual LUT electricity ESD is mapped to flat hourly load as an explicit
assumption. Firm generation is sized independently for each scenario.
Costs are illustrative model units, not observed system costs.
"""
import argparse
from pathlib import Path

import pandas as pd

from .benchmark import solve_illustrative
from .scenarios import scale_annual_demand


def compare_dispatch(annual, multipliers=None, hours=24, solver_name="highs"):
    if not isinstance(hours, int) or not 1 <= hours <= 8784:
        raise ValueError("hours must be an integer in [1, 8784]")
    if annual.year.nunique() != 1 or int(annual.year.iloc[0]) != 2020:
        raise ValueError("This comparison currently supports only 2020")
    scaled = scale_annual_demand(
        annual, multipliers if multipliers is not None
        else {"low_demand": 0.9, "high_demand": 1.1}
    )
    snapshots = pd.date_range("2020-01-01", periods=hours, freq="h")
    records = []
    for scenario, part in scaled.groupby("scenario", sort=False):
        hourly = pd.concat([
            pd.DataFrame({
                "timestamp": snapshots,
                "region": row.region,
                "p_set_mw": float(row.scenario_demand_twh) * 1e6 / 8784,
            })
            for row in part.itertuples(index=False)
        ], ignore_index=True)
        network, summary = solve_illustrative(hourly, solver_name=solver_name)
        summary.insert(0, "scenario", scenario)
        summary["hours"] = hours
        summary["assumed_multiplier"] = float(part.assumed_multiplier.iloc[0])
        summary["illustrative_dispatch_cost"] = (
            summary.firm_generation_mwh * 50.0
            + summary.unserved_energy_mwh * 10000.0
        )
        expected = float(part.scenario_demand_twh.sum()) * 1e6 * hours / 8784
        actual = float(summary.demand_mwh.sum())
        if abs(actual - expected) > max(0.01, expected * 1e-9):
            raise RuntimeError(f"Demand reconciliation failed: {scenario}")
        if summary.unserved_energy_mwh.abs().max() > 1e-5:
            raise RuntimeError(f"Unexpected shortage: {scenario}")
        records.append(summary)
    return pd.concat(records, ignore_index=True)


def run(input_csv, output_dir, hours=24):
    annual = pd.read_csv(input_csv)
    results = compare_dispatch(annual, hours=hours)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    results.to_csv(out / "illustrative_scenario_dispatch.csv", index=False)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv")
    parser.add_argument("--output", default="outputs/scenario_dispatch")
    parser.add_argument("--hours", type=int, default=24)
    args = parser.parse_args()
    print(run(args.input_csv, args.output, args.hours).to_string(index=False))
