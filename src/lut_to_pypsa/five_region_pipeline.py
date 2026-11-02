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
        load_profile="flat", diurnal_amplitude=0.20, capacity_reference="profile_peak",
        firm_availability_amplitude=0.0, availability_trough_hour=18):
    if not 0 <= firm_capacity_factor <= 1 or pd.isna(firm_capacity_factor):
        raise ValueError("Invalid firm capacity factor")
    if capacity_reference not in ("profile_peak", "flat_reference"):
        raise ValueError("Invalid capacity reference")
    import math
    if not math.isfinite(firm_availability_amplitude) or not 0 <= firm_availability_amplitude < 1:
        raise ValueError("Invalid firm availability amplitude")
    if not isinstance(availability_trough_hour, int) or not 0 <= availability_trough_hour <= 23:
        raise ValueError("Invalid availability trough hour")
    annual = pd.read_csv(annual_csv)
    if load_profile not in ("flat", "diurnal"):
        raise ValueError("Invalid load profile")
    hourly = (hourly_flat(annual, year) if load_profile == "flat"
              else hourly_diurnal(annual, year, amplitude=diurnal_amplitude))
    checks = check_energy_conservation(annual.loc[annual.year.eq(year)], hourly)
    network = add_illustrative_supply(build_load_network(hourly), reserve_margin=reserve_margin,
                                      firm_capacity_factor=firm_capacity_factor)
    if capacity_reference == "flat_reference":
        baseline = hourly_flat(annual, year)
        reference_peak = baseline.groupby("region").p_set_mw.max()
        for region, peak in reference_peak.items():
            network.generators.at[f"firm_{region}", "p_nom"] = (
                float(peak) * (1 + reserve_margin) * firm_capacity_factor)
    if firm_availability_amplitude:
        import numpy as np
        hours = network.snapshots.hour.to_numpy()
        availability = 1 - firm_availability_amplitude * (
            1 + np.cos(2 * np.pi * (hours - availability_trough_hour) / 24)) / 2
        network.generators_t.p_max_pu = pd.DataFrame(
            {f"firm_{region}": availability for region in network.buses.index},
            index=network.snapshots)
    solved, report, status, condition = solve_regional_dispatch(network)
    report = report.rename(columns={"bus": "region"})
    report["solver_status"] = status
    report["termination_condition"] = condition
    report["supply_provenance"] = "assumed_firm_and_shortage_generators"
    report["load_profile"] = load_profile
    report["capacity_reference"] = capacity_reference
    report["firm_availability_amplitude"] = firm_availability_amplitude
    report["availability_trough_hour"] = availability_trough_hour
    report["firm_capacity_mw"] = [float(solved.generators.at[f"firm_{region}", "p_nom"]) for region in report.region]
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
    parser.add_argument("--capacity-reference", choices=("profile_peak", "flat_reference"),
                        default="profile_peak", help="Choose profile-dependent or fixed flat-load reference capacity")
    parser.add_argument("--firm-availability-amplitude", type=float, default=0.0,
                        help="Synthetic 18:00 firm-availability dip (0=always available)")
    parser.add_argument("--availability-trough-hour", type=int, default=18,
                        help="Local synthetic daily hour of lowest firm availability (0-23)")
    args = parser.parse_args(argv)
    print(run(args.annual, args.output, year=args.year,
              reserve_margin=args.reserve_margin,
              firm_capacity_factor=args.firm_capacity_factor,
              load_profile=args.load_profile, diurnal_amplitude=args.diurnal_amplitude,
              capacity_reference=args.capacity_reference,
              firm_availability_amplitude=args.firm_availability_amplitude,
              availability_trough_hour=args.availability_trough_hour).to_string(index=False))


if __name__ == "__main__":
    main()
