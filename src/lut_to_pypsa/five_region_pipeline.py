"""Reproducible authentic-LUT-demand / assumed-supply five-region benchmark.

This is NOT empirical generation calibration: supply is illustrative.
"""
import argparse
from pathlib import Path
import pandas as pd
from .hourly import hourly_flat, hourly_diurnal, check_energy_conservation, build_load_network
from .benchmark import add_illustrative_supply
from .regional_dispatch import solve_regional_dispatch


def run(annual_csv, output_dir, *, year=2020, reserve_margin=0.10, firm_capacity_factor=1.0,
        load_profile="flat", diurnal_amplitude=0.20):
    if not 0 <= firm_capacity_factor <= 1 or pd.isna(firm_capacity_factor):
        raise ValueError("Invalid firm capacity factor")
    annual = pd.read_csv(annual_csv)
    if load_profile not in ("flat", "diurnal"):
        raise ValueError("Invalid load profile")
    hourly = (hourly_flat(annual, year) if load_profile == "flat"
              else hourly_diurnal(annual, year, amplitude=diurnal_amplitude))
    checks = check_energy_conservation(annual.loc[annual.year.eq(year)], hourly)
    network = add_illustrative_supply(build_load_network(hourly), reserve_margin=reserve_margin,
                                      firm_capacity_factor=firm_capacity_factor)
    solved, report, status, condition = solve_regional_dispatch(network)
    report = report.rename(columns={"bus": "region"})
    report["solver_status"] = status
    report["termination_condition"] = condition
    report["supply_provenance"] = "assumed_firm_and_shortage_generators"
    report["load_profile"] = load_profile
    report["diurnal_amplitude"] = diurnal_amplitude if load_profile == "diurnal" else 0.0
    report["assumed_reserve_margin"] = reserve_margin
    report["assumed_firm_capacity_factor"] = firm_capacity_factor
    weights = solved.snapshot_weightings["generators"].reindex(solved.snapshots)
    dispatch = solved.generators_t.p.reindex(index=solved.snapshots)
    for kind in ("firm", "shortage"):
        report[f"{kind}_generation_mwh"] = [
            float(dispatch[f"{kind}_{region}"].mul(weights).sum())
            for region in report.region
        ]
    report["illustrative_dispatch_cost"] = [
        float(sum(dispatch[g].mul(weights).sum() * solved.generators.at[g, "marginal_cost"]
                  for g in (f"firm_{region}", f"shortage_{region}")))
        for region in report.region
    ]
    report["shortage_fraction"] = (
        report.shortage_generation_mwh / report.demand_mwh.where(report.demand_mwh.ne(0))
    ).fillna(0.0)
    if ((report.firm_generation_mwh + report.shortage_generation_mwh
         - report.demand_mwh).abs() > 0.01).any():
        raise ValueError("Illustrative supply breakdown fails annual demand balance")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    checks.to_csv(output_dir / "annual_energy_check.csv", index=False)
    report.to_csv(output_dir / "regional_dispatch_audit.csv", index=False)
    solved.export_to_netcdf(output_dir / "illustrative_five_region_solved.nc")
    hourly.to_csv(output_dir / f"lut_hourly_{load_profile}_loads.csv", index=False)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annual", type=Path, default=Path("data/derived/lut_continents_2020_verified.csv"))
    parser.add_argument("--output", type=Path, default=Path("outputs/five_region"))
    parser.add_argument("--year", type=int, default=2020)
    parser.add_argument("--reserve-margin", type=float, default=0.10,
                        help="Illustrative firm capacity margin above each region peak")
    parser.add_argument("--firm-capacity-factor", type=float, default=1.0,
                        help="Fraction of assumed firm capacity retained (0 to 1)")
    parser.add_argument("--load-profile", choices=("flat", "diurnal"), default="flat",
                        help="Flat or synthetic daily-shaped annual-conserving demand")
    parser.add_argument("--diurnal-amplitude", type=float, default=0.20)
    args = parser.parse_args(argv)
    print(run(args.annual, args.output, year=args.year,
              reserve_margin=args.reserve_margin,
              firm_capacity_factor=args.firm_capacity_factor,
              load_profile=args.load_profile, diurnal_amplitude=args.diurnal_amplitude).to_string(index=False))


if __name__ == "__main__":
    main()
