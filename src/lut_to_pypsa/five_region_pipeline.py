"""Reproducible authentic-LUT-demand / assumed-supply five-region benchmark.

This is NOT empirical generation calibration: supply is illustrative.
"""
import argparse
from pathlib import Path
import pandas as pd
from .hourly import hourly_flat, check_energy_conservation, build_load_network
from .benchmark import add_illustrative_supply
from .regional_dispatch import solve_regional_dispatch


def run(annual_csv, output_dir, *, year=2020, reserve_margin=0.10):
    annual = pd.read_csv(annual_csv)
    hourly = hourly_flat(annual, year)
    checks = check_energy_conservation(annual.loc[annual.year.eq(year)], hourly)
    network = add_illustrative_supply(build_load_network(hourly), reserve_margin=reserve_margin)
    solved, report, status, condition = solve_regional_dispatch(network)
    report = report.rename(columns={"bus": "region"})
    report["solver_status"] = status
    report["termination_condition"] = condition
    report["supply_provenance"] = "assumed_firm_and_shortage_generators"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    checks.to_csv(output_dir / "annual_energy_check.csv", index=False)
    report.to_csv(output_dir / "regional_dispatch_audit.csv", index=False)
    solved.export_to_netcdf(output_dir / "illustrative_five_region_solved.nc")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annual", type=Path, default=Path("data/derived/lut_continents_2020_verified.csv"))
    parser.add_argument("--output", type=Path, default=Path("outputs/five_region"))
    parser.add_argument("--year", type=int, default=2020)
    args = parser.parse_args(argv)
    print(run(args.annual, args.output, year=args.year).to_string(index=False))


if __name__ == "__main__":
    main()
