"""Demand growth scenarios derived from source-traced LUT annual demand.

Multipliers are researcher-specified sensitivities, NOT LUT model outputs.
"""
import argparse
from pathlib import Path
import math
import pandas as pd


def scale_annual_demand(annual, multipliers):
    """Return baseline and user-specified scenario annual demands in TWh."""
    required = {"region", "year", "value_twh"}
    if not required.issubset(annual.columns):
        raise ValueError("Annual demand requires region, year, value_twh")
    if annual.duplicated(["region", "year"]).any():
        raise ValueError("Duplicate region/year")
    if annual[["region", "year", "value_twh"]].isna().any().any():
        raise ValueError("Null region/year/demand")
    values = pd.to_numeric(annual.value_twh, errors="raise")
    if not values.map(lambda v: math.isfinite(v) and v >= 0).all():
        raise ValueError("Invalid annual demand")
    if not multipliers or "baseline" in multipliers:
        raise ValueError("Provide non-baseline scenario multipliers")
    for name, factor in multipliers.items():
        if not name or not math.isfinite(float(factor)) or float(factor) < 0:
            raise ValueError("Invalid scenario multiplier")
    frames = []
    for name, factor in [("baseline", 1.0), *multipliers.items()]:
        part = annual.copy()
        part["scenario"] = name
        part["assumed_multiplier"] = float(factor)
        part["scenario_demand_twh"] = values * float(factor)
        frames.append(part)
    return pd.concat(frames, ignore_index=True)


def summarize_scenarios(scaled):
    return (scaled.groupby(["scenario", "year"], as_index=False)
            .agg(total_demand_twh=("scenario_demand_twh", "sum"),
                 regions=("region", "nunique"),
                 assumed_multiplier=("assumed_multiplier", "first")))


def run(input_csv, output_dir, low=0.9, high=1.1):
    annual = pd.read_csv(input_csv)
    scaled = scale_annual_demand(annual, {"low_demand": low, "high_demand": high})
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    scaled.to_csv(out / "scenario_regional_annual.csv", index=False)
    summary = summarize_scenarios(scaled)
    summary.to_csv(out / "scenario_annual_summary.csv", index=False)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv")
    parser.add_argument("--output", default="outputs/scenarios")
    parser.add_argument("--low", type=float, default=0.9)
    parser.add_argument("--high", type=float, default=1.1)
    args = parser.parse_args()
    print(run(args.input_csv, args.output, args.low, args.high).to_string(index=False))
